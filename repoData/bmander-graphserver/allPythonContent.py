__FILENAME__ = dedupe
# eliminate duplicate service periods from a GTFS database

from graphserver.ext.gtfs.gtfsdb import GTFSDatabase

import sys
from optparse import OptionParser

def main():
    usage = """usage: python dedupe.py <graphdb_filename>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]    
    
    gtfsdb = GTFSDatabase( graphdb_filename )

    query = """
    SELECT count(*), monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date 
    FROM calendar
    GROUP BY monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date"""

    duped_periods = gtfsdb.execute( query )

    equivilants = []

    for count, m,t,w,th,f,s,su,start_date,end_date in duped_periods:
        # no need to check for dupes if there's only one
        if count==1:
            continue
        
        #print count, m, t, w, th, f, s, su, start_date, end_date
        
        # get service_ids for this dow/start_date/end_date combination
        service_ids = [x[0] for x in list(  gtfsdb.execute( "SELECT service_id FROM calendar where monday=? and tuesday=? and wednesday=? and thursday=? and friday=? and saturday=? and sunday=? and start_date=? and end_date=?", (m,t,w,th,f,s,su,start_date,end_date) ) ) ]
        
        # group by service periods with the same set of exceptions
        exception_set_grouper = {}
        for service_id in service_ids:
            exception_set = list(gtfsdb.execute( "SELECT date, exception_type FROM calendar_dates WHERE service_id=?", (service_id,) ) )
            exception_set.sort()
            exception_set = tuple(exception_set)
            
            exception_set_grouper[exception_set] = exception_set_grouper.get(exception_set,[])
            exception_set_grouper[exception_set].append( service_id )
        
        # extend list of equivilants
        for i, exception_set_group in enumerate( exception_set_grouper.values() ):
            equivilants.append( ("%d%d%d%d%d%d%d-%s-%s-%d"%(m,t,w,th,f,s,su,start_date,end_date,i), exception_set_group) )
        
    for new_name, old_names in equivilants:
        for old_name in old_names:
            print old_name, new_name
            
            c = gtfsdb.conn.cursor()
            
            c.execute( "UPDATE calendar SET service_id=? WHERE service_id=?", (new_name, old_name) )
            c.execute( "UPDATE calendar_dates SET service_id=? WHERE service_id=?", (new_name, old_name) )
            c.execute( "UPDATE trips SET service_id=? WHERE service_id=?", (new_name, old_name) )

            gtfsdb.conn.commit()
            
            c.close()
            
if __name__=='__main__':
    main()
    

########NEW FILE########
__FILENAME__ = gdb_import_gtfs
from graphserver.core import Graph, TripBoard, HeadwayBoard, HeadwayAlight, Crossing, TripAlight, Timezone, Street, Link, ElapseTime
from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase, parse_gtfs_date
import sys
import pytz
from tools import service_calendar_from_timezone
import datetime

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

class GTFSGraphCompiler:
    def __init__(self, gtfsdb, agency_namespace, agency_id=None, reporter=None):
        self.gtfsdb = gtfsdb
        self.agency_namespace = agency_namespace
        self.reporter = reporter

        # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
        timezone_name = gtfsdb.agency_timezone_name(agency_id)
        self.tz = Timezone.generate( timezone_name )
        if reporter: reporter.write( "constructing service calendar for timezone '%s'\n"%timezone_name )
        self.sc = service_calendar_from_timezone(gtfsdb, timezone_name )

    def bundle_to_boardalight_edges(self, bundle, service_id):
        """takes a bundle and yields a bunch of edges"""
        
        stop_time_bundles = bundle.stop_time_bundles(service_id)
        
        n_trips = len(bundle.trip_ids)
            
        # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
        if len(stop_time_bundles)<2:
            return
            
        # If there are no stop_times in a bundle on this service day, there is nothing to load
        if n_trips==0:
            return
            
        if self.reporter: self.reporter.write( "inserting %d trips with %d stop_time bundles on service_id '%s'\n"%(len(stop_time_bundles[0]),len(stop_time_bundles),service_id) )

        #add board edges
        for i, stop_time_bundle in enumerate(stop_time_bundles[:-1]):
            
            trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
            
            if arrival_time != departure_time:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart"%(self.agency_namespace,bundle.pattern.pattern_id,i,service_id)
                
                # construct the board/alight/dwell triangle for this patternstop
                patternstop_arrival_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(self.agency_namespace,bundle.pattern.pattern_id,i,service_id)
                
                dwell_crossing = Crossing()
                for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
                    dwell_crossing.add_crossing_time( trip_id, departure_time-arrival_time )
                
                yield (patternstop_arrival_vx_name, 
                           patternstop_vx_name,
                           dwell_crossing)
                
            else:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(self.agency_namespace,bundle.pattern.pattern_id,i,service_id)
            
            b = TripBoard(service_id, self.sc, self.tz, 0)
            for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
                b.add_boarding( trip_id, departure_time, stop_sequence )
                
            yield ( "sta-%s"%stop_id, patternstop_vx_name, b )
            
        #add alight edges
        for i, stop_time_bundle in enumerate(stop_time_bundles[1:]):

            trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
            
            if arrival_time != departure_time:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(self.agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
            else:
                patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(self.agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
            
            al = TripAlight(service_id, self.sc, self.tz, 0)
            for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
                al.add_alighting( trip_id.encode('ascii'), arrival_time, stop_sequence )
                
            yield ( patternstop_vx_name, "sta-%s"%stop_id, al )
        
        # add crossing edges
        for i, (from_stop_time_bundle, to_stop_time_bundle) in enumerate(cons(stop_time_bundles)):
            
            trip_id, from_arrival_time, from_departure_time, stop_id, stop_sequence, stop_dist_traveled = from_stop_time_bundle[0]
            trip_id, to_arrival_time, to_departure_time, stop_id, stop_sequence, stop_dist_traveled = to_stop_time_bundle[0]
            
            if from_arrival_time!=from_departure_time:
                from_patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart"%(self.agency_namespace,bundle.pattern.pattern_id,i,service_id)
            else:
                from_patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(self.agency_namespace,bundle.pattern.pattern_id,i,service_id)
                
            if to_arrival_time!=to_departure_time:
                to_patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(self.agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
            else:
                to_patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(self.agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
            
            crossing = Crossing()
            for i in range( len( from_stop_time_bundle ) ):
                trip_id, from_arrival_time, from_departure_time, stop_id, stop_sequence, stop_dist_traveled = from_stop_time_bundle[i]
                trip_id, to_arrival_time, to_departure_time, stop_id, stop_sequence, stop_dist_traveled = to_stop_time_bundle[i]
                crossing.add_crossing_time( trip_id, (to_arrival_time-from_departure_time) )
            
            yield ( from_patternstop_vx_name, 
                    to_patternstop_vx_name, 
                    crossing )

    def gtfsdb_to_scheduled_edges(self, maxtrips=None, service_ids=None):
        
        # compile trip bundles from gtfsdb
        if self.reporter: self.reporter.write( "Compiling trip bundles...\n" )
        bundles = self.gtfsdb.compile_trip_bundles(maxtrips=maxtrips, reporter=self.reporter)
        
        # load bundles to graph
        if self.reporter: self.reporter.write( "Loading trip bundles into graph...\n" )
        n_bundles = len(bundles)
        for i, bundle in enumerate(bundles):
            if self.reporter: self.reporter.write( "%d/%d loading %s\n"%(i+1, n_bundles, bundle) )
            
            for service_id in [x.encode("ascii") for x in self.gtfsdb.service_ids()]:
                if service_ids is not None and service_id not in service_ids:
		    continue

                for fromv_label, tov_label, edge in self.bundle_to_boardalight_edges(bundle, service_id):
                    yield fromv_label, tov_label, edge

    def gtfsdb_to_headway_edges( self, maxtrips=None ):

        # load headways
        if self.reporter: self.reporter.write( "Loading headways trips to graph...\n" )
        for trip_id, start_time, end_time, headway_secs in self.gtfsdb.execute( "SELECT * FROM frequencies" ):
            service_id = list(self.gtfsdb.execute( "SELECT service_id FROM trips WHERE trip_id=?", (trip_id,) ))[0][0]
            service_id = service_id.encode('utf-8')
            
            hb = HeadwayBoard( service_id, self.sc, self.tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
            ha = HeadwayAlight( service_id, self.sc, self.tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
            
            stoptimes = list(self.gtfsdb.execute( "SELECT * FROM stop_times WHERE trip_id=? ORDER BY stop_sequence", (trip_id,)) )
            
            #add board edges
            for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[:-1]:
                yield ( "sta-%s"%stop_id, "hwv-%s-%s-%s"%(self.agency_namespace,stop_id, trip_id), hb )
                
            #add alight edges
            for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[1:]:
                yield ( "hwv-%s-%s-%s"%(self.agency_namespace,stop_id, trip_id), "sta-%s"%stop_id, ha )
            
            #add crossing edges
            for (trip_id1, arrival_time1, departure_time1, stop_id1, stop_sequence1, stop_dist_traveled1), (trip_id2, arrival_time2, departure_time2, stop_id2, stop_sequence2,stop_dist_traveled2) in cons(stoptimes):
                cr = Crossing()
                cr.add_crossing_time( trip_id1, (arrival_time2-departure_time1) )
                yield ( "hwv-%s-%s-%s"%(self.agency_namespace,stop_id1, trip_id1), "hwv-%s-%s-%s"%(self.agency_namespace,stop_id2, trip_id2), cr )

    def gtfsdb_to_transfer_edges( self ):
                
        # load transfers
        if self.reporter: self.reporter.write( "Loading transfers to graph...\n" )
        
        # keep track to avoid redundancies
        # this assumes that transfer relationships are bi-directional.
        # TODO this implementation is also incomplete - it's theoretically possible that
        # a transfers.txt table could contain "A,A,3,", which would mean you can't transfer
        # at A.
        seen = set([]) 
        for stop_id1, stop_id2, conn_type, min_transfer_time in self.gtfsdb.execute( "SELECT * FROM transfers" ):            
            s1 = "sta-%s"%stop_id1
            s2 = "sta-%s"%stop_id2
            
            # TODO - what is the semantics of this? see note above
            if s1 == s2:
                continue
            
            key = ".".join(sorted([s1,s2]))
            if key not in seen:
                seen.add(key)
            else:
                continue
            
            assert conn_type == None or type(conn_type) == int
            if conn_type in (0, None): # This is a recommended transfer point between two routes
                if min_transfer_time in ("", None):
                    yield (s1, s2, Link())
                    yield (s2, s1, Link())
                else:
                    yield (s1, s2, ElapseTime(int(min_transfer_time)))
                    yield (s2, s1, ElapseTime(int(min_transfer_time)))
            elif conn_type == 1: # This is a timed transfer point between two routes
                yield (s1, s2, Link())
                yield (s2, s1, Link())
            elif conn_type == 2: # This transfer requires a minimum amount of time
                yield (s1, s2, ElapseTime(int(min_transfer_time)))
                yield (s2, s1, ElapseTime(int(min_transfer_time)))
            elif conn_type == 3: # Transfers are not possible between routes at this location. 
                print "WARNING: Support for no-transfer (transfers.txt transfer_type=3) not implemented."

    def gtfsdb_to_edges( self, maxtrips=None, service_ids=None ):
        for edge_tuple in self.gtfsdb_to_scheduled_edges(maxtrips, service_ids=service_ids):
            yield edge_tuple

        for edge_tuple in self.gtfsdb_to_headway_edges(maxtrips):
            yield edge_tuple 

        for edge_tuple in self.gtfsdb_to_transfer_edges():
            yield edge_tuple

def gdb_load_gtfsdb(gdb, agency_namespace, gtfsdb, cursor, agency_id=None, maxtrips=None, sample_date=None, reporter=sys.stdout):

    # determine which service periods run on the given day, if a day is given
    if sample_date is not None:
        sample_date = datetime.date( *parse_gtfs_date( sample_date ) )
	acceptable_service_ids = gtfsdb.service_periods( sample_date )
	print "Importing only service periods operating on %s: %s"%(sample_date, acceptable_service_ids)
    else:
        acceptable_service_ids = None

    compiler = GTFSGraphCompiler( gtfsdb, agency_namespace, agency_id, reporter )
    c = gdb.get_cursor()
    v_added = set([])
    for fromv_label, tov_label, edge in compiler.gtfsdb_to_edges( maxtrips, service_ids=acceptable_service_ids ):
        if fromv_label not in v_added:
            gdb.add_vertex( fromv_label, c )
            v_added.add(fromv_label)
        if tov_label not in v_added:
            gdb.add_vertex( tov_label, c )
            v_added.add(tov_label)
        gdb.add_edge( fromv_label, tov_label, edge, c )
    gdb.commit()

def graph_load_gtfsdb( agency_namespace, gtfsdb, agency_id=None, maxtrips=None, reporter=sys.stdout ):
    compiler = GTFSGraphCompiler( gtfsdb, agency_namespace, agency_id, reporter )

    gg = Graph()

    for fromv_label, tov_label, edge in compiler.gtfsdb_to_edges( maxtrips ):
        gg.add_vertex( fromv_label )
        gg.add_vertex( tov_label )
        gg.add_edge( fromv_label, tov_label, edge )

    return gg
        
def main():
    usage = """usage: python gdb_import_gtfs.py [options] <graphdb_filename> <gtfsdb_filename> [<agency_id>]"""
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--namespace", dest="namespace", default="0",
                      help="agency namespace")
    parser.add_option("-m", "--maxtrips", dest="maxtrips", default=None, help="maximum number of trips to load")
    parser.add_option("-d", "--date", dest="sample_date", default=None, help="only load transit running on a given day. YYYYMMDD" )
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.print_help()
        exit(-1)
    
    graphdb_filename = args[0]
    gtfsdb_filename  = args[1]
    agency_id        = args[2] if len(args)==3 else None
    
    print "importing from gtfsdb '%s' into graphdb '%s'"%(gtfsdb_filename, graphdb_filename)
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    gdb = GraphDatabase( graphdb_filename, overwrite=False )
    
    maxtrips = int(options.maxtrips) if options.maxtrips else None
    gdb_load_gtfsdb( gdb, options.namespace, gtfsdb, gdb.get_cursor(), agency_id, maxtrips=maxtrips, sample_date=options.sample_date)
    gdb.commit()
    
    print "done"

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = gdb_import_ned
from graphserver.graphdb import GraphDatabase
from graphserver.ext.osm.profiledb import ProfileDB
from graphserver.core import Street

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def get_rise_and_fall( profile ):
    rise=0
    fall=0
    
    if profile is not None:
        for (d1, e1), (d2, e2) in cons(profile):
            diff = e2-e1
            if diff>0:
                rise += diff
            elif diff<0:
                fall -= diff
            
    return rise, fall

from sys import argv

def main():
    if len(argv) < 2:
        print "usage: python import_ned.py graphdb_filename profiledb_filename"
        return
        
    graphdb_filename = argv[1]
    profiledb_filename = argv[2]
        
    gdb = GraphDatabase( graphdb_filename )
    profiledb = ProfileDB( profiledb_filename )
    
    n = gdb.num_edges()

    for i, (oid, vertex1, vertex2, edge) in enumerate( list(gdb.all_edges(include_oid=True)) ):
        if i%500==0: print "%s/%s"%(i,n)
        
        if isinstance( edge, Street ):
            rise, fall = get_rise_and_fall( profiledb.get( edge.name ) )
            edge.rise = rise
            edge.fall = fall
            
            gdb.remove_edge( oid )
            gdb.add_edge( vertex1, vertex2, edge )
            
if __name__=='__main__':
    main()
            


########NEW FILE########
__FILENAME__ = gdb_import_osm
from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
import os
from graphserver.core import Street
from graphserver.ext.osm.osmdb import OSMDB
import sys
from graphserver.ext.osm.profiledb import ProfileDB
from gdb_import_ned import get_rise_and_fall

def edges_from_osmdb(osmdb, vertex_namespace, slogs, profiledb=None):
    """generates (vertex1_label, vertex2_label, edgepayload) from osmdb"""
    
    street_id_counter = 0
    street_names = {}
    
    # for each edge in the osmdb
    for i, (id, parent_id, node1, node2, distance, geom, tags) in enumerate( osmdb.edges() ):
            
        # Find rise/fall of edge, if profiledb is given
        rise=0
        fall=0
        if profiledb:
            profile = profiledb.get( id )
            if profile:
                rise, fall = get_rise_and_fall( profile )
        
        # insert end vertices of edge to graph
        vertex1_label = "%s-%s"%(vertex_namespace,node1)
        vertex2_label = "%s-%s"%(vertex_namespace,node2)
                
        # create ID for the way's street
        street_name = tags.get("name")
        if street_name is None:
            street_id_counter += 1
            street_id = street_id_counter
        else:
            if street_name not in street_names:
                street_id_counter += 1
                street_names[street_name] = street_id_counter
            street_id = street_names[street_name]
        
        # Create edges to be inserted into graph
        s1 = Street( id, distance, rise, fall )
        s2 = Street( id, distance, fall, rise, reverse_of_source=True )
        s1.way = street_id
        s2.way = street_id
        
        # See if the way's highway tag is penalized with a 'slog' value; if so, set it in the edges
        slog = slogs.get( tags.get("highway") )
        if slog:
            s1.slog = s2.slog = slog
        
        # Add the forward edge and the return edge if the edge is not oneway
	yield vertex1_label, vertex2_label, s1

        oneway = tags.get("oneway")
        if oneway != "true" and oneway != "yes":
	    yield vertex2_label, vertex1_label, s2

def gdb_import_osm(gdb, osmdb, vertex_namespace, slogs, profiledb=None):
    cursor = gdb.get_cursor()
	
    n_edges = osmdb.count_edges()*2   # two edges for each bidirectional edge
    
    # for each edge in the osmdb
    for i, (vertex1_label, vertex2_label, edge ) in enumerate( edges_from_osmdb( osmdb, vertex_namespace, slogs, profiledb ) ):
        
        if i%(n_edges//100+1)==0: sys.stdout.write( "%d/~%d edges loaded\r\n"%(i, n_edges))
            
        gdb.add_vertex( vertex1_label, cursor )
        gdb.add_vertex( vertex2_label, cursor )
                
        gdb.add_edge( vertex1_label, vertex2_label, edge, cursor )
            
    gdb.commit()
    
    print "indexing vertices..."
    gdb.index()

def main():
    usage = """usage: python gdb_import_osm.py <graphdb_filename> <osmdb_filename>"""
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--namespace", dest="namespace", default="osm",
                      help="prefix all imported vertices with namespace string")
    parser.add_option("-s", "--slog",
                      action="append", dest="slog_strings", default=[],
                      help="specify slog for highway type, in highway_type:slog form. For example, 'motorway:10.5'")
    parser.add_option("-p", "--profiledb", dest="profiledb_filename", default=None,
                      help="specify profiledb to annotate streets with rise/fall data")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.print_help()
        exit(-1)
        
    slogs = {}
    for slog_string in options.slog_strings:
        highway_type,slog_penalty = slog_string.split(":")
        slogs[highway_type] = float(slog_penalty)
    print "slog values: %s"%slogs
        
    graphdb_filename = args[0]
    osmdb_filename = args[1]
    
    print "importing osmdb '%s' into graphdb '%s'"%(osmdb_filename, graphdb_filename)
    
    profiledb = ProfileDB( options.profiledb_filename ) if options.profiledb_filename else None
    osmdb = OSMDB( osmdb_filename )
    gdb = GraphDatabase( graphdb_filename, overwrite=False )
    
    gdb_import_osm(gdb, osmdb, options.namespace, slogs, profiledb);
    
    print "done"

if __name__ == '__main__':
    main()

    

########NEW FILE########
__FILENAME__ = gdb_link_gtfs_gtfs
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.graphdb import GraphDatabase
from graphserver.core import Link, Street
from graphserver.vincenty import vincenty

import sys
from optparse import OptionParser

def main():
    usage = """usage: python gdb_link_gtfs_gtfs.py <graphdb_filename> <gtfsdb_filename> <range>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 3:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]
    gtfsdb_filename  = args[1]
    range = float(args[2])
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    gdb = GraphDatabase( graphdb_filename )

    n_stops = gtfsdb.count_stops()

    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        print "%d/%d %s"%(i,n_stops,stop_id),
        
        station_vertex_id = "sta-%s"%stop_id
        
        for link_stop_id, link_stop_name, link_stop_lat, link_stop_lon in gtfsdb.nearby_stops( stop_lat, stop_lon, range ):
            if link_stop_id == stop_id:
                continue
            
            print ".",
            
            link_length = vincenty( stop_lat, stop_lon, link_stop_lat, link_stop_lon)
            link_station_vertex_id = "sta-%s"%link_stop_id
            gdb.add_edge( station_vertex_id, link_station_vertex_id, Street("link", link_length) )
            
        print ""

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = gdb_link_osm_gtfs
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.graphdb import GraphDatabase
from graphserver.core import Link

import sys
from optparse import OptionParser

def main():
    usage = """usage: python gdb_link_osm_gtfs.py <graphdb_filename> <osmdb_filename> <gtfsdb_filename>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 3:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]
    osmdb_filename   = args[1]
    gtfsdb_filename  = args[2]
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    osmdb = OSMDB( osmdb_filename )
    gdb = GraphDatabase( graphdb_filename )

    n_stops = gtfsdb.count_stops()

    c = gdb.get_cursor()
    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        print "%d/%d"%(i,n_stops)
        
        nd_id, nd_lat, nd_lon, nd_dist = osmdb.nearest_node( stop_lat, stop_lon )
        station_vertex_id = "sta-%s"%stop_id
        osm_vertex_id = "osm-%s"%nd_id
        
        print station_vertex_id, osm_vertex_id
        
        gdb.add_edge( station_vertex_id, osm_vertex_id, Link(), c )
        gdb.add_edge( osm_vertex_id, station_vertex_id, Link(), c )
    
    gdb.commit()
    
if __name__=='__main__':
    main()
########NEW FILE########
__FILENAME__ = gdb_new
from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
import os

def main():
    usage = """usage: python new_gdb.py [options] <graphdb_filename> """
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--overwrite",
                      action="store_true", dest="overwrite", default=False,
                      help="overwrite any existing database")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.print_help()
        exit(-1)
    
    graphdb_filename = args[0]
    
    if not os.path.exists(graphdb_filename) or options.overwrite:
        print "Creating graph database '%s'"%graphdb_filename
        
        graphdb = GraphDatabase( graphdb_filename, overwrite=options.overwrite )
    else:
        print "Graph database '%s' already exists. Use -o to overwrite"%graphdb_filename

if __name__=='__main__':
    main()
########NEW FILE########
__FILENAME__ = tools
from graphserver.core import ServiceCalendar
import pytz
from datetime import timedelta, datetime, time
from graphserver.util import TimeHelpers

def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)
    
def service_calendar_from_timezone(gtfsdb, timezone_name):

    MAX_CALENDAR_SIZE = 1024
    sc_count = list(gtfsdb.execute( "SELECT DISTINCT count(*) FROM (SELECT service_id FROM calendar_dates UNION SELECT service_id FROM calendar )" ))[0][0]
    if sc_count > MAX_CALENDAR_SIZE:
        raise Exception( "Service period count %d is greater than the maximum of %d"%(sc_count, MAX_CALENDAR_SIZE) )
    
    timezone = pytz.timezone( timezone_name )

    # grab date, day service bounds
    start_date, end_date = gtfsdb.date_range()

    # init empty calendar
    cal = ServiceCalendar()

    # for each day in service range, inclusive
    for currdate in iter_dates(start_date, end_date):
        
        # get and encode in utf-8 the service_ids of all service periods running thos date
        service_ids = [x.encode('utf8') for x in gtfsdb.service_periods( currdate )]
        
        # figure datetime.datetime bounds of this service day
        currdate_start = datetime.combine(currdate, time(0))
        currdate_local_start = timezone.localize(currdate_start)
        service_period_begins = timezone.normalize( currdate_local_start )
        service_period_ends = timezone.normalize( currdate_local_start + timedelta(hours=24)  )

        # enter as entry in service calendar
        cal.add_period( TimeHelpers.datetime_to_unix(service_period_begins), TimeHelpers.datetime_to_unix(service_period_ends), service_ids )

    return cal


########NEW FILE########
__FILENAME__ = core
try:
    from graphserver.gsdll import libc, lgs, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
except ImportError:
    #so I can run this script from the same folder
    from gsdll import libc, lgs, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p, py_object, c_float
from ctypes import Structure, pointer, cast, POINTER, addressof
from _ctypes import Py_INCREF, Py_DECREF
from time import asctime, gmtime
from time import time as now
import pytz
import calendar
from util import TimeHelpers
from vector import Vector


def indent( a, n ):
    return "\n".join( [" "*n+x for x in a.split("\n")] )
        
#TODO this is probably defined somewhere else, too
def unparse_secs(secs):
    return "%02d:%02d:%02d"%(secs/3600, (secs%3600)/60, secs%60)
    
"""

These classes map C structs to Python Ctypes Structures.

"""


class Walkable:
    """ Implements the walkable interface. """
    def walk(self, state, walk_options):
        return State.from_pointer(self._cwalk(self.soul, state.soul, walk_options.soul))
        
    def walk_back(self, state, walk_options):
        return State.from_pointer(self._cwalk_back(self.soul, state.soul, walk_options.soul))

"""

CType Definitions

"""

ServiceIdType = c_int

"""

Class Definitions

"""

class Path(Structure):
    """Represents a path of vertices and edges as returned by ShortestPathTree.path()"""
    
    _fields_ = [("vertices", POINTER(Vector)),
                ("edges", POINTER(Vector))]
                
    def __new__(cls, origin, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = lgs.pathNew( origin.soul, init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, origin, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        pass
        
    def addSegment(self, vertex, edge):
        lgs.pathAddSegment( addressof(self), vertex.soul, edge.soul )
        
    def getVertex( self, i ):
        vertex_soul = lgs.pathGetVertex( addressof(self), i )
        
        # reinterpret the error code as an exception
        if vertex_soul is None:
            raise IndexError("%d is out of bounds"%i)
        
        return SPTVertex.from_pointer( vertex_soul )
        
    def getEdge( self, i ):
        edge_soul = lgs.pathGetEdge( addressof(self), i )
        
        # reinterpret the error code as an exception
        if edge_soul is None:
            raise IndexError("%d is out of bounds"%i)
            
        return Edge.from_pointer( edge_soul )
        
    def destroy( self ):
        lgs.pathDestroy( addressof(self) )
        
    @property
    def num_elements(self):
        return self.edges.contents.num_elements
        
    def __repr__(self):
        return "<Path shadowing %s with %d segments>"%(hex(addressof(self)), self.num_elements)

#=============================================================================#
# Core Graph Classes                                                          #
#=============================================================================#

class Graph(CShadow):
    
    size = cproperty(lgs.gSize, c_long)
    
    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies #a central point that keeps track of how large the list of calendards need ot be in the state variables.
        
    def destroy(self, free_vertex_payloads=1, free_edge_payloads=1):
        #void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self.check_destroyed()
        
        self._cdel(self.soul, free_vertex_payloads, free_edge_payloads)
        self.soul = None
            
    def add_vertex(self, label):
        #Vertex* gAddVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cadd_vertex(self.soul, label)
        
    def remove_vertex(self, label, free_edge_payloads=True):
        #void gRemoveVertex( Graph* this, char *label, int free_vertex_payload, int free_edge_payloads );
        
        return self._cremove_vertex(self.soul, label, free_edge_payloads)
        
    def get_vertex(self, label):
        #Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)
        
    def add_edge( self, fromv, tov, payload ):
        #Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()
        
        e = self._cadd_edge( self.soul, fromv, tov, payload.soul )
        
        if e != None: return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)
        
    def set_vertex_enabled( self, vertex_label, enabled ):
        #void gSetVertexEnabled( Graph *this, char *label, int enabled );
        self.check_destroyed()
        
        lgs.gSetVertexEnabled( self.soul, vertex_label, enabled )
        
    @property
    def vertices(self):
        self.check_destroyed()
        
        count = c_long()
        p_va = lgs.gVertices(self.soul, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p)) # a bit of necessary voodoo
        for i in range(count.value):
            v = Vertex.from_pointer(arr[i])
            verts.append(v)
        del arr
        libc.free(p_va)
        return verts
    
    def add_vertices(self, vs):
        a = (c_char_p * len(vs))()
        for i, v in enumerate(vs):
            a[i] = str(v)
        lgs.gAddVertices(self.soul, a, len(vs))
    
    @property
    def edges(self):
        self.check_destroyed()
        
        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o: continue
            for e in o:
                edges.append(e)
        return edges    
    
    def shortest_path_tree(self, fromv, tov, initstate, walk_options=None, maxtime=2000000000, hoplimit=1000000, weightlimit=2000000000):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not tov:
            tov = "*bogus^*^vertex*"
        
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime), c_int(hoplimit), c_long(weightlimit) )
            walk_options.destroy()
        else:
            ret = self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime), c_int(hoplimit), c_long(weightlimit) )
        
        if ret is None:
	  raise Exception( "Could not create shortest path tree" ) # this shouldn't happen; TODO: more descriptive error

	return ret

    def shortest_path_tree_retro(self, fromv, tov, finalstate, walk_options=None, mintime=0, hoplimit=1000000, weightlimit=2000000000):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not fromv:
            fromv = "*bogus^*^vertex*"
            
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime), c_int(hoplimit), c_long(weightlimit) )
            walk_options.destroy()
        else:
            ret = self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime), c_int(hoplimit), c_long(weightlimit) )

        if ret is None:
	  raise Exception( "Could not create shortest path tree" ) # this shouldn't happen; TODO: more descriptive error

        return ret

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"
        
    def get_contraction_hierarchies( self, walk_options, search_limit=1 ):
        return self._get_ch( self.soul, walk_options.soul, search_limit )
        
class ContractionHierarchy(CShadow):
    
    upgraph = cproperty(lgs.chUpGraph, c_void_p, Graph)
    downgraph = cproperty(lgs.chDownGraph, c_void_p, Graph)
    
    def __init__(self):
        self.soul = lgs.chNew( )
        
    def shortest_path(self, fromv_label, tov_label, init_state, walk_options ):
        # GET UPGRAPH AND DOWNGRAPH SPTS
        sptup = self.upgraph.shortest_path_tree( fromv_label, None, init_state, walk_options )
        sptdown = self.downgraph.shortest_path_tree_retro( None, tov_label, State(0,10000000), walk_options )
        
        # FIND SMALLEST MEETUP VERTEX
        meetup_vertices = []
        for upvv in sptup.vertices:
            downvv = sptdown.get_vertex( upvv.label )
            if downvv is not None:
                meetup_vertices.append( (upvv.state.weight + downvv.state.weight, upvv.label ) )
        min_meetup = min(meetup_vertices)[1]
        
        # GET AND JOIN PATHS TO MEETUP VERTEX
        upvertices, upedges = sptup.path( min_meetup )
        downvertices, downedges = sptdown.path_retro( min_meetup )
        
        vertices = upvertices+downvertices[1:]
        edges = upedges+downedges
        
        ret = [ee.payload for ee in edges]
                
        sptup.destroy()
        sptdown.destroy()
            
        return ret

class ShortestPathTree(CShadow):
    
    size = cproperty(lgs.sptSize, c_long)
    
    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies #a central point that keeps track of how large the list of calendards need ot be in the state variables.
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
            
    def add_vertex(self, shadow, hop=0):
        #Vertex* sptAddVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()
        
        return self._cadd_vertex(self.soul, shadow.soul, hop)
        
    def remove_vertex(self, label):
        #void sptRemoveVertex( ShortestPathTree* this, char *label, int free_vertex_payload, int free_edge_payloads );
        
        return self._cremove_vertex(self.soul, label)
        
    def get_vertex(self, label):
        #Vertex* sptGetVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)
        
    def add_edge( self, fromv, tov, payload ):
        #Edge* sptAddEdge( ShortestPathTree* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()
        
        e = self._cadd_edge( self.soul, fromv, tov, payload.soul )
        
        if e != None: return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)
        
    @property
    def vertices(self):
        self.check_destroyed()
        
        count = c_long()
        p_va = lgs.sptVertices(self.soul, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p)) # a bit of necessary voodoo
        for i in range(count.value):
            v = SPTVertex.from_pointer(arr[i])
            verts.append(v)
        return verts
    
    @property
    def edges(self):
        self.check_destroyed()
        
        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o: continue
            for e in o:
                edges.append(e)
        return edges    

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"
    
    def path(self, destination):
        path_vertices, path_edges = self.path_retro(destination)
        
        if path_vertices is None:
            return (None,None)
        
        path_vertices.reverse()
        path_edges.reverse()
        
        return (path_vertices, path_edges)
        
    def path_retro(self,origin):
        self.check_destroyed()
        
        path_pointer = lgs.sptPathRetro( self.soul, origin )
        
        if path_pointer is None:
	    raise Exception( "A path to %s could not be found"%origin )
            
        path = Path.from_address( path_pointer )
        
        vertices = [path.getVertex( i ) for i in range(path.num_elements+1)]
        edges = [path.getEdge( i ) for i in range(path.num_elements)]
            
        path.destroy()
        
        return (vertices, edges)

class EdgePayload(CShadow, Walkable):
    def __init__(self):
        if self.__class__ == EdgePayload:
            raise "EdgePayload is an abstract type."
    
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
        
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()
        return "<abstractedgepayload type='%s'/>" % self.type
    
    type = cproperty(lgs.epGetType, c_int)
    external_id = cproperty(lgs.epGetExternalId, c_long, setter=lgs.epSetExternalId)
    
    @classmethod
    def from_pointer(cls, ptr):
        """ Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        
        payloadtype = EdgePayload._subtypes[EdgePayload._cget_type(ptr)]
        if payloadtype is GenericPyPayload:
            p = lgs.cpSoul(ptr)
            # this is required to prevent garbage collection of the object
            Py_INCREF(p)
            return p
        ret = instantiate(payloadtype)
        ret.soul = ptr
        return ret

class State(CShadow):
    
    def __init__(self, n_agencies, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(n_agencies, long(time))
        
    def service_period(self, agency):
        soul = lgs.stateServicePeriod( self.soul, agency )
        return ServicePeriod.from_pointer( soul )
        
    def set_service_period(self, agency, sp):
        if agency>self.num_agencies-1:
            raise Exception("Agency index %d out of bounds"%agency)
        
        lgs.stateSetServicePeriod( self.soul, c_int(agency), sp.soul)
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
    
    def __copy__(self):
        self.check_destroyed()
        
        return self._ccopy(self.soul)
    
    def clone(self):
        self.check_destroyed()
        
        return self.__copy__()
    
    def __str__(self):
        self.check_destroyed()
        
        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()  
        
        ret = "<state time='%d' weight='%s' dist_walked='%s' " \
              "num_transfers='%s' trip_id='%s' stop_sequence='%s'>" % \
               (self.time,
               self.weight,
               self.dist_walked,
              self.num_transfers,
               self.trip_id,
               self.stop_sequence)
        for i in range(self.num_agencies):
            if self.service_period(i) is not None:
                ret += self.service_period(i).to_xml()
        return ret + "</state>"
    
    # the state does not keep ownership of the trip_id, so the state
    # may not live longer than whatever object set its trip_id
    def dangerous_set_trip_id( self, trip_id ):
        lgs.stateDangerousSetTripId( self.soul, trip_id )
        
    time           = cproperty(lgs.stateGetTime, c_long, setter=lgs.stateSetTime)
    weight         = cproperty(lgs.stateGetWeight, c_long, setter=lgs.stateSetWeight)
    dist_walked    = cproperty(lgs.stateGetDistWalked, c_double, setter=lgs.stateSetDistWalked)
    num_transfers  = cproperty(lgs.stateGetNumTransfers, c_int, setter=lgs.stateSetNumTransfers)
    prev_edge      = cproperty(lgs.stateGetPrevEdge, c_void_p, EdgePayload, setter=lgs.stateSetPrevEdge )
    num_agencies     = cproperty(lgs.stateGetNumAgencies, c_int)
    trip_id          = cproperty(lgs.stateGetTripId, c_char_p)
    stop_sequence    = cproperty(lgs.stateGetStopSequence, c_int)
    
class WalkOptions(CShadow):
    
    def __init__(self):
        self.soul = self._cnew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
        
    @classmethod
    def from_pointer(cls, ptr):
        """ Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
 
    transfer_penalty = cproperty(lgs.woGetTransferPenalty, c_int, setter=lgs.woSetTransferPenalty)
    turn_penalty = cproperty(lgs.woGetTurnPenalty, c_int, setter=lgs.woSetTurnPenalty)
    walking_speed = cproperty(lgs.woGetWalkingSpeed, c_float, setter=lgs.woSetWalkingSpeed)
    walking_reluctance = cproperty(lgs.woGetWalkingReluctance, c_float, setter=lgs.woSetWalkingReluctance)
    uphill_slowness = cproperty(lgs.woGetUphillSlowness, c_float, setter=lgs.woSetUphillSlowness)
    downhill_fastness = cproperty(lgs.woGetDownhillFastness, c_float, setter=lgs.woSetDownhillFastness)
    hill_reluctance = cproperty(lgs.woGetHillReluctance, c_float, setter=lgs.woSetHillReluctance)
    max_walk = cproperty(lgs.woGetMaxWalk, c_int, setter=lgs.woSetMaxWalk)
    walking_overage = cproperty(lgs.woGetWalkingOverage, c_float, setter=lgs.woSetWalkingOverage)

class Edge(CShadow, Walkable):
    def __init__(self, from_v, to_v, payload):
        #Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
        self.soul = self._cnew(from_v.soul, to_v.soul, payload.soul)
    
    def __str__(self):
        return self.to_xml()
        
    def to_xml(self):
        return "<Edge>%s</Edge>" % (self.payload)
        
    @property
    def from_v(self):
        return self._cfrom_v(self.soul)
        
    @property
    def to_v(self):
        return self._cto_v(self.soul)
        
    @property
    def payload(self):
        return self._cpayload(self.soul)
        
    def walk(self, state, walk_options):
        return self._cwalk(self.soul, state.soul, walk_options.soul)
        
    enabled = cproperty(lgs.eGetEnabled, c_int, setter=lgs.eSetEnabled)
    
class SPTEdge(Edge):
    def to_xml(self):
        return "<SPTEdge>%s</SPTEdge>" % (self.payload)

class Vertex(CShadow):
    
    label = cproperty(lgs.vGetLabel, c_char_p)
    degree_in = cproperty(lgs.vDegreeIn, c_int)
    degree_out = cproperty(lgs.vDegreeOut, c_int)
    edgeclass = Edge
    
    def __init__(self,label):
        self.soul = self._cnew(label)
        
    def destroy(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?
        
        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None
    
    def to_xml(self):
        self.check_destroyed()
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (self.degree_out, self.degree_in, self.label)
    
    def __str__(self):
        self.check_destroyed()
        return self.to_xml()

    @property
    def outgoing(self):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges)
        
    @property
    def incoming(self):
        self.check_destroyed()
        return self._edges(self._cincoming_edges)

    def _edges(self, method, index = -1):
        self.check_destroyed()
        e = []
        node = method(self.soul)
        if not node: 
            if index == -1:
                return e
            else: 
                return None
        i = 0
        while node:
            if index != -1 and i == index:
                return node.data(edgeclass=self.edgeclass)
            e.append(node.data(edgeclass=self.edgeclass))
            node = node.next
            i = i+1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self,i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, i)
        
    def get_incoming_edge(self,i):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, i)
        
    def __hash__(self):
        return int(self.soul)
        
class SPTVertex(CShadow):
    
    label = cproperty(lgs.sptvGetLabel, c_char_p)
    degree_in = cproperty(lgs.sptvDegreeIn, c_int)
    degree_out = cproperty(lgs.sptvDegreeOut, c_int)
    hop = cproperty(lgs.sptvHop, c_int)
    mirror = cproperty(lgs.sptvMirror, c_void_p, Vertex )
    edgeclass = SPTEdge
    
    def __init__(self,mirror,hop=0):
        self.soul = self._cnew(mirror.soul,hop)
        
    def destroy(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?
        
        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None
    
    def to_xml(self):
        self.check_destroyed()
        return "<SPTVertex degree_out='%s' degree_in='%s' label='%s'/>" % (self.degree_out, self.degree_in, self.label)
    
    def __str__(self):
        self.check_destroyed()
        return self.to_xml()

    @property
    def outgoing(self):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges)
        
    @property
    def incoming(self):
        self.check_destroyed()
        return self._edges(self._cincoming_edges)
    
    @property
    def state(self):
        self.check_destroyed()
        return self._cstate(self.soul)

    def _edges(self, method, index = -1):
        self.check_destroyed()
        e = []
        node = method(self.soul)
        if not node: 
            if index == -1:
                return e
            else: 
                return None
        i = 0
        while node:
            if index != -1 and i == index:
                return node.data(edgeclass=self.edgeclass)
            e.append(node.data(edgeclass=self.edgeclass))
            node = node.next
            i = i+1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self,i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, i)
        
    def get_incoming_edge(self,i):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, i)
        
    def __hash__(self):
        return int(self.soul)



class ListNode(CShadow):
    
    def data(self, edgeclass=Edge):
        return edgeclass.from_pointer( lgs.liGetData(self.soul) )
    
    @property
    def next(self):
        return self._cnext(self.soul)

def failsafe(return_arg_num_on_failure):
    """ Decorator to prevent segfaults during failed callbacks."""
    def deco(func):
        def safe(*args):
            try:
                return func(*args)
            except:
                import traceback, sys            
                sys.stderr.write("ERROR: Exception during callback ")
                try:
                    sys.stderr.write("%s\n" % (map(str, args)))
                except:
                    pass
                traceback.print_exc()
                return args[return_arg_num_on_failure]
        return safe
    return deco

class GenericPyPayload(EdgePayload):
    """ This class is the base type for custom payloads created in Python.  
        Subclasses can override the *_impl methods, which will be invoked through
        C callbacks. """
        
    def __init__(self):
        """ Children MUST call this method to properly 
            register themselves in C world. """
        self.soul = self._cnew(py_object(self),self._cmethods)
        self.name = self.__class__.__name__
        # required to keep this object around in the C world
        Py_INCREF(self)

    def to_xml(self):
        return "<pypayload type='%s' class='%s'/>" % (self.type, self.__class__.__name__)

    """ These methods are the public interface, BUT should not be overridden by subclasses 
        - subclasses should override the *_impl methods instead.""" 
    @failsafe(1)
    def walk(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_impl(s, walkoptions)
    
    @failsafe(1)
    def walk_back(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_back_impl(s, walkoptions)
     
    """ These methods should be overridden by subclasses as deemed fit. """
    def walk_impl(self, state, walkoptions):
        return state

    def walk_back_impl(self, state, walkoptions):
        return state

    """ These methods provide the interface from the C world to py method implementation. """
    def _cwalk(self, stateptr, walkoptionsptr):
        return self.walk(State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)).soul

    def _cwalk_back(self, stateptr, walkoptionsptr):
        return self.walk_back(State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)).soul

    def _cfree(self):
        #print "Freeing %s..." % self
        # After this is freed in the C world, this can be freed
        Py_DECREF(self)
        self.soul = None
        
        
        
    _cmethodptrs = [PayloadMethodTypes.destroy(_cfree),
                    PayloadMethodTypes.walk(_cwalk),
                    PayloadMethodTypes.walk_back(_cwalk_back)]

    _cmethods = lgs.defineCustomPayloadType(*_cmethodptrs)

 
class NoOpPyPayload(GenericPyPayload):
    def __init__(self, num):
        self.num = num
        super(NoOpPyPayload,self).__init__()
    
    """ Dummy class."""
    def walk_impl(self, state, walkopts):
        print "%s walking..." % self
        
    def walk_back_impl(self, state, walkopts):
        print "%s walking back..." % self
        
        
    def to_xml(self):
        return "<NoOpPyPayload type='%s' num='%s'/>" % (self.type, self.num)
    
#=============================================================================#
# Edge Type Support Classes                                                   #
#=============================================================================#

class ServicePeriod(CShadow):   

    begin_time = cproperty(lgs.spBeginTime, c_long)
    end_time = cproperty(lgs.spEndTime, c_long)

    def __init__(self, begin_time, end_time, service_ids):
        n, sids = ServicePeriod._py2c_service_ids(service_ids)
        self.soul = self._cnew(begin_time, end_time, n, sids)
    
    @property
    def service_ids(self):
        count = c_int()
        ptr = lgs.spServiceIds(self.soul, byref(count))
        ptr = cast(ptr, POINTER(ServiceIdType))
        ids = []
        for i in range(count.value):
            ids.append(ptr[i])
        return ids
    
    @property
    def previous(self):
        return self._cprev(self.soul)

    @property
    def next(self):
        return self._cnext(self.soul)

    def rewind(self):
        return self._crewind(self.soul)
        
    def fast_forward(self):
        return self._cfast_forward(self.soul)
    
    def __str__(self):
        return self.to_xml()
    
    def to_xml(self, cal=None):
        if cal is not None:
            sids = [cal.get_service_id_string(x) for x in self.service_ids]
        else:
            sids = [str(x) for x in self.service_ids]

        return "<ServicePeriod begin_time='%d' end_time='%d' service_ids='%s'/>" %( self.begin_time, self.end_time, ",".join(sids))
    
    def datum_midnight(self, timezone_offset):
        return lgs.spDatumMidnight( self.soul, timezone_offset )
    
    def normalize_time(self, timezone_offset, time):
        return lgs.spNormalizeTime(self.soul, timezone_offset, time)
        
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.service_ids)
        
    def __setstate__(self, state):
        self.__init__(*state)
        
    def __repr__(self):
        return "(%s %s->%s)"%(self.service_ids, self.begin_time, self.end_time)
        
    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)

class ServiceCalendar(CShadow):
    """Calendar provides a set of convient methods for dealing with the wrapper class ServicePeriod, which
       wraps a single node in the doubly linked list that represents a calendar in Graphserver."""
    head = cproperty( lgs.scHead, c_void_p, ServicePeriod )
       
    def __init__(self):
        self.soul = lgs.scNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    
    def get_service_id_int( self, service_id ):
        if type(service_id)!=type("string"):
            raise TypeError("service_id is supposed to be a string")
        
        return lgs.scGetServiceIdInt( self.soul, service_id );
        
    def get_service_id_string( self, service_id ):
        if type(service_id)!=type(1):
            raise TypeError("service_id is supposed to be an int, in this case")
        
        return lgs.scGetServiceIdString( self.soul, service_id )
        
    def add_period(self, begin_time, end_time, service_ids):
        sp = ServicePeriod( begin_time, end_time, [self.get_service_id_int(x) for x in service_ids] )
        
        lgs.scAddPeriod(self.soul, sp.soul)

    def period_of_or_after(self,time):
        soul = lgs.scPeriodOfOrAfter(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    def period_of_or_before(self,time):
        soul = lgs.scPeriodOfOrBefore(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    @property
    def periods(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next
            
    def to_xml(self):
        ret = ["<ServiceCalendar>"]
        for period in self.periods:
            ret.append( period.to_xml(self) )
        ret.append( "</ServiceCalendar>" )
        return "".join(ret)
        
    def __getstate__(self):
        ret = []
        max_sid = -1
        curs = self.head
        while curs:
            start, end, sids = curs.__getstate__()
            for sid in sids:
                max_sid = max(max_sid, sid)
            sids = [self.get_service_id_string(sid) for sid in sids]

            ret.append( (start,end,sids) )
            curs = curs.next
        sids_list = [self.get_service_id_string(sid) for sid in range(max_sid+1)]
        return (sids_list, ret)
        
    def __setstate__(self, state):
        self.__init__()
        sids_list, periods = state
        for sid in sids_list:
            self.get_service_id_int(sid)
            
        for p in periods:
            self.add_period( *p )
            
    def __repr__(self):
        return "<ServiceCalendar periods=%s>"%repr(list(self.periods))
        
    def expound(self, timezone_name):
        periodstrs = []
        
        for period in self.periods:
            begin_time = TimeHelpers.unix_to_localtime( period.begin_time, timezone_name )
            end_time = TimeHelpers.unix_to_localtime( period.end_time, timezone_name )
            service_ids = dict([(id,self.get_service_id_string(id)) for id in period.service_ids])
            periodstrs.append( "sids:%s active from %d (%s) to %d (%s)"%(service_ids, period.begin_time, begin_time, period.end_time, end_time) )
        
        return "\n".join( periodstrs )
    
class TimezonePeriod(CShadow):
    begin_time = cproperty(lgs.tzpBeginTime, c_long)
    end_time = cproperty(lgs.tzpEndTime, c_long)
    utc_offset = cproperty(lgs.tzpUtcOffset, c_long)
    
    def __init__(self, begin_time, end_time, utc_offset):
        self.soul = lgs.tzpNew(begin_time, end_time, utc_offset)
    
    @property
    def next_period(self):
        return TimezonePeriod.from_pointer( lgs.tzpNextPeriod( self.soul ) )
        
    def time_since_midnight(self, time):
        return lgs.tzpTimeSinceMidnight( self.soul, c_long(time) )
        
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.utc_offset)
    
    def __setstate__(self, state):
        self.__init__(*state)
                
        
class Timezone(CShadow):
    head = cproperty( lgs.tzHead, c_void_p, TimezonePeriod )
    
    def __init__(self):
        self.soul = lgs.tzNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    def add_period(self, timezone_period):
        lgs.tzAddPeriod( self.soul, timezone_period.soul)
        
    def period_of(self, time):
        tzpsoul = lgs.tzPeriodOf( self.soul, time )
        return TimezonePeriod.from_pointer( tzpsoul )
        
    def utc_offset(self, time):
        ret = lgs.tzUtcOffset( self.soul, time )
        
        if ret==-360000:
            raise IndexError( "%d lands within no timezone period"%time )
            
        return ret
        
    def time_since_midnight(self, time):
        ret = lgs.tzTimeSinceMidnight( self.soul, c_long(time) )
        
        if ret==-1:
            raise IndexError( "%d lands within no timezone period"%time )
            
        return ret
        
    @classmethod
    def generate(cls, timezone_string):
        ret = Timezone()
        
        timezone = pytz.timezone(timezone_string)
        tz_periods = zip(timezone._utc_transition_times[:-1],timezone._utc_transition_times[1:])
            
        #exclude last transition_info entry, as it corresponds with the last utc_transition_time, and not the last period as defined by the last two entries
        for tz_period, (utcoffset,dstoffset,periodname) in zip( tz_periods, timezone._transition_info[:-1] ):
            period_begin, period_end = [calendar.timegm( (x.year, x.month, x.day, x.hour, x.minute, x.second) ) for x in tz_period]
            period_end -= 1 #period_end is the last second the period is active, not the first second it isn't
            utcoffset = utcoffset.days*24*3600 + utcoffset.seconds
            
            ret.add_period( TimezonePeriod( period_begin, period_end, utcoffset ) )
        
        return ret
        
    def __getstate__(self):
        ret = []
        curs = self.head
        while curs:
            ret.append( curs.__getstate__() )
            curs = curs.next_period
        return ret
        
    def __setstate__(self, state):
        self.__init__()
        for tzpargs in state:
            self.add_period( TimezonePeriod(*tzpargs) )
            
    def expound(self):
        return "Timezone"
    
#=============================================================================#
# Edge Types                                                                  #
#=============================================================================#
    
class Link(EdgePayload):
    name = cproperty(lgs.linkGetName, c_char_p)
    
    def __init__(self):
        self.soul = self._cnew()

    def to_xml(self):
        self.check_destroyed()
        
        return "<Link name='%s'/>" % (self.name)
        
    def __getstate__(self):
        return tuple([])
        
    def __setstate__(self, state):
        self.__init__()
        
    @classmethod
    def reconstitute(self, state, resolver):
        return Link()
    
class Street(EdgePayload):
    length = cproperty(lgs.streetGetLength, c_double)
    name   = cproperty(lgs.streetGetName, c_char_p)
    rise = cproperty(lgs.streetGetRise, c_float, setter=lgs.streetSetRise)
    fall = cproperty(lgs.streetGetFall, c_float, setter=lgs.streetSetFall)
    slog = cproperty(lgs.streetGetSlog, c_float, setter=lgs.streetSetSlog)
    way = cproperty(lgs.streetGetWay, c_long, setter=lgs.streetSetWay)
    
    def __init__(self,name,length,rise=0,fall=0,reverse_of_source=False):
        self.soul = self._cnew(name, length, rise, fall,reverse_of_source)
            
    def to_xml(self):
        self.check_destroyed()
        
        return "<Street name='%s' length='%f' rise='%f' fall='%f' way='%ld' reverse='%s'/>" % (self.name, self.length, self.rise, self.fall, self.way,self.reverse_of_source)
        
    def __getstate__(self):
        return (self.name, self.length, self.rise, self.fall, self.slog, self.way, self.reverse_of_source)
        
    def __setstate__(self, state):
        name, length, rise, fall, slog, way, reverse_of_source = state
        self.__init__(name, length, rise, fall, reverse_of_source)
        self.slog = slog
        self.way = way
        
    def __repr__(self):
        return "<Street name='%s' length=%f rise=%f fall=%f way=%ld reverse=%s>"%(self.name, self.length, self.rise, self.fall, self.way,self.reverse_of_source)
        
    @classmethod
    def reconstitute(self, state, resolver):
        name, length, rise, fall, slog, way, reverse_of_source = state
        ret = Street( name, length, rise, fall, reverse_of_source )
        ret.slog = slog
        ret.way = way
        return ret
        
    @property
    def reverse_of_source(self):
        return lgs.streetGetReverseOfSource(self.soul)==1

class Egress(EdgePayload):
    length = cproperty(lgs.egressGetLength, c_double)
    name   = cproperty(lgs.egressGetName, c_char_p)
    
    def __init__(self,name,length):
        self.soul = self._cnew(name, length)
            
    def to_xml(self):
        self.check_destroyed()
        
        return "<Egress name='%s' length='%f' />" % (self.name, self.length)
        
    def __getstate__(self):
        return (self.name, self.length)
        
    def __setstate__(self, state):
        self.__init__(*state)
        
    def __repr__(self):
        return "<Egress name='%s' length=%f>"%(self.name, self.length)
        
    @classmethod
    def reconstitute(self, state, resolver):
        return Egress( *state )


class Wait(EdgePayload):
    end = cproperty(lgs.waitGetEnd, c_long)
    timezone = cproperty(lgs.waitGetTimezone, c_void_p, Timezone)
    
    def __init__(self, end, timezone):
        self.soul = self._cnew( end, timezone.soul )
        
    def to_xml(self):
        self.check_destroyed()
        
        return "<Wait end='%ld' />"%(self.end)
        
    def __getstate__(self):
        return (self.end, self.timezone.soul)

class ElapseTime(EdgePayload):
    seconds = cproperty(lgs.elapseTimeGetSeconds, c_long)
    
    def __init__(self, seconds):
        self.soul = self._cnew( seconds )
        
    def to_xml(self):
        self.check_destroyed()
        
        return "<ElapseTime seconds='%ld' />"%(self.seconds)
        
    def __getstate__(self):
        return self.seconds
    
    @classmethod
    def reconstitute(cls, state, resolver):
        return cls(state)



class Headway(EdgePayload):
    
    begin_time = cproperty( lgs.headwayBeginTime, c_int )
    end_time = cproperty( lgs.headwayEndTime, c_int )
    wait_period = cproperty( lgs.headwayWaitPeriod, c_int )
    transit = cproperty( lgs.headwayTransit, c_int )
    trip_id = cproperty( lgs.headwayTripId, c_char_p )
    calendar = cproperty( lgs.headwayCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.headwayTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.headwayAgency, c_int )
    int_service_id = cproperty( lgs.headwayServiceId, c_int )
    
    def __init__(self, begin_time, end_time, wait_period, transit, trip_id, calendar, timezone, agency, service_id):
        if type(service_id)!=type('string'):
            raise TypeError("service_id is supposed to be a string")
            
        int_sid = calendar.get_service_id_int( service_id )
        
        self.soul = lgs.headwayNew(begin_time, end_time, wait_period, transit, trip_id.encode("ascii"),  calendar.soul, timezone.soul, c_int(agency), ServiceIdType(int_sid))
        
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
        
    def to_xml(self):
        return "<Headway begin_time='%d' end_time='%d' wait_period='%d' transit='%d' trip_id='%s' agency='%d' int_service_id='%d' />"% \
                       (self.begin_time,
                        self.end_time,
                        self.wait_period,
                        self.transit,
                        self.trip_id,
                        self.agency,
                        self.int_service_id)
    
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.wait_period, self.transit, self.trip_id, self.calendar.soul, self.timezone.soul, self.agency, self.calendar.get_service_id_string(self.int_service_id))
        
class TripBoard(EdgePayload):
    calendar = cproperty( lgs.tbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.tbGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.tbGetAgency, c_int )
    int_service_id = cproperty( lgs.tbGetServiceId, c_int )
    num_boardings = cproperty( lgs.tbGetNumBoardings, c_int )
    overage = cproperty( lgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
    
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
    
    def add_boarding(self, trip_id, depart, stop_sequence):
        self._cadd_boarding( self.soul, trip_id, depart, stop_sequence )
        
    def get_boarding(self, i):
        trip_id = lgs.tbGetBoardingTripId(self.soul, c_int(i))
        depart = lgs.tbGetBoardingDepart(self.soul, c_int(i))
        stop_sequence = lgs.tbGetBoardingStopSequence(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, depart, stop_sequence)
        
    def get_boarding_by_trip_id( self, trip_id ):
        boarding_index = lgs.tbGetBoardingIndexByTripId( self.soul, trip_id )
        
        if boarding_index == -1:
            return None
        
        return self.get_boarding( boarding_index )
    
    def search_boardings_list(self, time):
        return lgs.tbSearchBoardingsList( self.soul, c_int(time) )
        
    def get_next_boarding_index(self, time):
        return lgs.tbGetNextBoardingIndex( self.soul, c_int(time) )
        
    def get_next_boarding(self, time):
        i = self.get_next_boarding_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_boarding( i )
            
    def to_xml(self):
        return "<TripBoard />"
        
    def __repr__(self):
        return "<TripBoard int_sid=%d sid=%s agency=%d calendar=%s timezone=%s boardings=%s>"%(self.int_service_id, self.calendar.get_service_id_string(self.int_service_id), self.agency, hex(self.calendar.soul),hex(self.timezone.soul),[self.get_boarding(i) for i in range(self.num_boardings)])
        
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        boardings = []
        for i in range(self.num_boardings):
            boardings.append( self.get_boarding( i ) )
        state['boardings'] = boardings
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        
        ret = TripBoard(int_sid, calendar, timezone, agency)
        
        for trip_id, depart, stop_sequence in state['boardings']:
            ret.add_boarding( trip_id, depart, stop_sequence )
            
        return ret
        
    def expound(self):
        boardingstrs = []
        
        for i in range(self.num_boardings):
            trip_id, departure_secs, stop_sequence = self.get_boarding(i)
            boardingstrs.append( "on trip id='%s' at %s, stop sequence %s"%(trip_id, unparse_secs(departure_secs), stop_sequence) )
        
        ret = """TripBoard
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   boardings:
%s"""%( self.agency,
        self.int_service_id,
        indent( self.calendar.expound("America/Chicago"), 6 ),
        indent( self.timezone.expound(), 6 ),
        indent( "\n".join(boardingstrs), 6 ) )

        return ret
        
        
class HeadwayBoard(EdgePayload):
    calendar = cproperty( lgs.hbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.hbGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.hbGetAgency, c_int )
    int_service_id = cproperty( lgs.hbGetServiceId, c_int )
    trip_id = cproperty( lgs.hbGetTripId, c_char_p )
    start_time = cproperty( lgs.hbGetStartTime, c_int )
    end_time = cproperty( lgs.hbGetEndTime, c_int )
    headway_secs = cproperty( lgs.hbGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayBoard calendar=%s timezone=%s agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(hex(self.calendar.soul),
                                                                                                                                          hex(self.timezone.soul),
                                                                                                                                          self.agency,
                                                                                                                                          self.int_service_id,
                                                                                                                                          self.trip_id,
                                                                                                                                          self.start_time,
                                                                                                                                          self.end_time,
                                                                                                                                          self.headway_secs)

    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
                                                                                                                                      
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        state['trip_id'] = self.trip_id
        state['start_time'] = self.start_time
        state['end_time'] = self.end_time
        state['headway_secs'] = self.headway_secs
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        trip_id = state['trip_id']
        start_time = state['start_time']
        end_time = state['end_time']
        headway_secs = state['headway_secs']
        
        ret = HeadwayBoard(int_sid, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs)
            
        return ret
        
class HeadwayAlight(EdgePayload):
    calendar = cproperty( lgs.haGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.haGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.haGetAgency, c_int )
    int_service_id = cproperty( lgs.haGetServiceId, c_int )
    trip_id = cproperty( lgs.haGetTripId, c_char_p )
    start_time = cproperty( lgs.haGetStartTime, c_int )
    end_time = cproperty( lgs.haGetEndTime, c_int )
    headway_secs = cproperty( lgs.haGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayAlight calendar=%s timezone=%s agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(hex(self.calendar.soul),
                                                                                                                                          hex(self.timezone.soul),
                                                                                                                                          self.agency,
                                                                                                                                          self.int_service_id,
                                                                                                                                          self.trip_id,
                                                                                                                                          self.start_time,
                                                                                                                                          self.end_time,
                                                                                                                                          self.headway_secs)
                                                                                                                                          
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        state['trip_id'] = self.trip_id
        state['start_time'] = self.start_time
        state['end_time'] = self.end_time
        state['headway_secs'] = self.headway_secs
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        trip_id = state['trip_id']
        start_time = state['start_time']
        end_time = state['end_time']
        headway_secs = state['headway_secs']
        
        ret = HeadwayAlight(int_sid, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs)
            
        return ret
    
class Crossing(EdgePayload):
    
    def __init__(self):
        self.soul = self._cnew()
        
    def add_crossing_time(self, trip_id, crossing_time):
        lgs.crAddCrossingTime( self.soul, trip_id, crossing_time )
        
    def get_crossing_time(self, trip_id):
        ret = lgs.crGetCrossingTime( self.soul, trip_id )
        if ret==-1:
            return None
        return ret
        
    def get_crossing(self, i):
        trip_id = lgs.crGetCrossingTimeTripIdByIndex( self.soul, i )
        crossing_time = lgs.crGetCrossingTimeByIndex( self.soul, i )
        
        if crossing_time==-1:
            return None
        
        return (trip_id, crossing_time)
    
    @property
    def size(self):
        return lgs.crGetSize( self.soul )
    
    def get_all_crossings(self):
        for i in range(self.size):
            yield self.get_crossing( i )
        
    def to_xml(self):
        return "<Crossing size=\"%d\"/>"%self.size
        
    def __getstate__(self):
        return list(self.get_all_crossings())
        
    @classmethod
    def reconstitute(cls, state, resolver):
        ret = Crossing()
        
        for trip_id, crossing_time in state:
            ret.add_crossing_time( trip_id, crossing_time )
        
        return ret
        
    def expound(self):
        ret = []
        
        ret.append( "Crossing" )
        
        for trip_id, crossing_time in self.get_all_crossings():
            ret.append( "%s: %s"%(trip_id, crossing_time) )
            
        return "\n".join( ret )

    def __repr__(self):
        return "<Crossing %s>"%list(self.get_all_crossings())
        
class Combination(EdgePayload):
    
    n = cproperty( lgs.comboN, c_int )
    
    def __init__(self, cap):
        self.soul = self._cnew(cap)
        
    def add(self, ep):
        lgs.comboAdd( self.soul, ep.soul )
        
    def get(self, i):
        return EdgePayload.from_pointer( lgs.comboGet( self.soul, i ) )
        
    def to_xml(self):
        self.check_destroyed()
        return "<Combination n=%d />"%self.n
        
    def __getstate__(self):
        return [ self.get( i ).soul for i in range(self.n) ]
    
    @classmethod
    def reconstitute(cls, state, graphdb):
        components = [ graphdb.get_edge_payload( epid ) for epid in state ]
        
        ret = Combination(len(components))
        
        for component in components:
            ret.add( component )
            
        return ret
        
    @property
    def components(self):
        for i in range(self.n):
            yield self.get( i )
        
    def unpack(self):
        components_unpacked = []
        for component_to_unpack in self.components:
            if component_to_unpack.__class__ == Combination:
                components_unpacked.append( component_to_unpack.unpack() )
            else:
                components_unpacked.append( [component_to_unpack] )
        return reduce( lambda x,y:x+y, components_unpacked )
        
    def expound(self):
        return "\n".join( [str(x) for x in self.unpack()] )
        
class TripAlight(EdgePayload):
    calendar = cproperty( lgs.alGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.alGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.alGetAgency, c_int )
    int_service_id = cproperty( lgs.alGetServiceId, c_int )
    num_alightings = cproperty( lgs.alGetNumAlightings, c_int )
    overage = cproperty( lgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
        
    def add_alighting(self, trip_id, arrival, stop_sequence):
        lgs.alAddAlighting( self.soul, trip_id, arrival, stop_sequence )
        
    def get_alighting(self, i):
        trip_id = lgs.alGetAlightingTripId(self.soul, c_int(i))
        arrival = lgs.alGetAlightingArrival(self.soul, c_int(i))
        stop_sequence = lgs.alGetAlightingStopSequence(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, arrival, stop_sequence)
    
    @property
    def alightings(self):
        for i in range(self.num_alightings):
            yield self.get_alighting( i )
        
    def search_alightings_list(self, time):
        return lgs.alSearchAlightingsList( self.soul, c_int(time) )
        
    def get_last_alighting_index(self, time):
        return lgs.alGetLastAlightingIndex( self.soul, c_int(time) )
        
    def get_last_alighting(self, time):
        i = self.get_last_alighting_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_alighting( i )
            

    def get_alighting_by_trip_id( self, trip_id ):
        alighting_index = lgs.alGetAlightingIndexByTripId( self.soul, trip_id )
        
        if alighting_index == -1:
            return None
        
        return self.get_alighting( alighting_index )
        
    def to_xml(self):
        return "<TripAlight/>"
        
    def __repr__(self):
        return "<TripAlight int_sid=%d agency=%d calendar=%s timezone=%s alightings=%s>"%(self.int_service_id, self.agency, hex(self.calendar.soul),hex(self.timezone.soul),[self.get_alighting(i) for i in range(self.num_alightings)])
        
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        alightings = []
        for i in range(self.num_alightings):
            alightings.append( self.get_alighting( i ) )
        state['alightings'] = alightings
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        
        ret = TripAlight(int_sid, calendar, timezone, agency)
        
        for trip_id, arrival, stop_sequence in state['alightings']:
            ret.add_alighting( trip_id, arrival, stop_sequence )
            
        return ret
        
    def expound(self):
        alightingstrs = []
        
        for i in range(self.num_alightings):
            trip_id, arrival_secs, stop_sequence = self.get_alighting(i)
            alightingstrs.append( "on trip id='%s' at %s, stop sequence %s"%(trip_id, unparse_secs(arrival_secs), stop_sequence) )
        
        ret = """TripAlight
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   alightings:
%s"""%( self.agency,
        self.int_service_id,
        indent( self.calendar.expound("America/Chicago"), 6 ),
        indent( self.timezone.expound(), 6 ),
        indent( "\n".join(alightingstrs), 6 ) )

        return ret

class VertexNotFoundError(Exception): pass

Graph._cnew = lgs.gNew
Graph._cdel = lgs.gDestroy
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)
Graph._cremove_vertex = lgs.gRemoveVertex
Graph._cget_vertex = ccast(lgs.gGetVertex, Vertex)
Graph._cadd_edge = ccast(lgs.gAddEdge, Edge)
Graph._cshortest_path_tree = ccast(lgs.gShortestPathTree, ShortestPathTree)
Graph._cshortest_path_tree_retro = ccast(lgs.gShortestPathTreeRetro, ShortestPathTree)
Graph._get_ch = ccast( lgs.get_contraction_hierarchies, ContractionHierarchy )

ShortestPathTree._cnew = lgs.sptNew
ShortestPathTree._cdel = lgs.sptDestroy
ShortestPathTree._cadd_vertex = ccast(lgs.sptAddVertex, SPTVertex)
ShortestPathTree._cremove_vertex = lgs.sptRemoveVertex
ShortestPathTree._cget_vertex = ccast(lgs.sptGetVertex, SPTVertex)
ShortestPathTree._cadd_edge = ccast(lgs.sptAddEdge, Edge)

Vertex._cnew = lgs.vNew
Vertex._cdel = lgs.vDestroy
Vertex._coutgoing_edges = ccast(lgs.vGetOutgoingEdgeList, ListNode)
Vertex._cincoming_edges = ccast(lgs.vGetIncomingEdgeList, ListNode)

SPTVertex._cnew = lgs.sptvNew
SPTVertex._cdel = lgs.sptvDestroy
SPTVertex._coutgoing_edges = ccast(lgs.sptvGetOutgoingEdgeList, ListNode)
SPTVertex._cincoming_edges = ccast(lgs.sptvGetIncomingEdgeList, ListNode)
SPTVertex._cstate = ccast(lgs.sptvState, State)

Edge._cnew = lgs.eNew
Edge._cfrom_v = ccast(lgs.eGetFrom, Vertex)
Edge._cto_v = ccast(lgs.eGetTo, Vertex)
Edge._cpayload = ccast(lgs.eGetPayload, EdgePayload)
Edge._cwalk = ccast(lgs.eWalk, State)
Edge._cwalk_back = lgs.eWalkBack

SPTEdge._cnew = lgs.eNew
SPTEdge._cfrom_v = ccast(lgs.eGetFrom, SPTVertex)
SPTEdge._cto_v = ccast(lgs.eGetTo, SPTVertex)
SPTEdge._cpayload = ccast(lgs.eGetPayload, EdgePayload)
SPTEdge._cwalk = ccast(lgs.eWalk, State)
SPTEdge._cwalk_back = lgs.eWalkBack

EdgePayload._subtypes = {0:Street,1:None,2:None,3:Link,4:GenericPyPayload,5:None,
                         6:Wait,7:Headway,8:TripBoard,9:Crossing,10:TripAlight,
                         11:HeadwayBoard,12:Egress,13:HeadwayAlight,14:ElapseTime,15:Combination}
EdgePayload._cget_type = lgs.epGetType
EdgePayload._cwalk = lgs.epWalk
EdgePayload._cwalk_back = lgs.epWalkBack

ServicePeriod._cnew = lgs.spNew
ServicePeriod._crewind = ccast(lgs.spRewind, ServicePeriod)
ServicePeriod._cfast_forward = ccast(lgs.spFastForward, ServicePeriod)
ServicePeriod._cnext = ccast(lgs.spNextPeriod, ServicePeriod)
ServicePeriod._cprev = ccast(lgs.spPreviousPeriod, ServicePeriod)

ServiceCalendar._cnew = lgs.scNew
ServiceCalendar._cdel = lgs.scDestroy
ServiceCalendar._cperiod_of_or_before = ccast(lgs.scPeriodOfOrBefore, ServicePeriod)
ServiceCalendar._cperiod_of_or_after = ccast(lgs.scPeriodOfOrAfter, ServicePeriod)

Timezone._cdel = lgs.tzDestroy

State._cnew = lgs.stateNew
State._cdel = lgs.stateDestroy
State._ccopy = ccast(lgs.stateDup, State)

ListNode._cdata = ccast(lgs.liGetData, Edge)
ListNode._cnext = ccast(lgs.liGetNext, ListNode)

Street._cnew = lgs.streetNewElev
Street._cdel = lgs.streetDestroy
Street._cwalk = lgs.streetWalk
Street._cwalk_back = lgs.streetWalkBack

Egress._cnew = lgs.egressNew
Egress._cdel = lgs.egressDestroy
Egress._cwalk = lgs.egressWalk
Egress._cwalk_back = lgs.egressWalkBack

Link._cnew = lgs.linkNew
Link._cdel = lgs.linkDestroy
Link._cwalk = lgs.epWalk
Link._cwalk_back = lgs.linkWalkBack

Wait._cnew = lgs.waitNew
Wait._cdel = lgs.waitDestroy
Wait._cwalk = lgs.waitWalk
Wait._cwalk_back = lgs.waitWalkBack

ElapseTime._cnew = lgs.elapseTimeNew
ElapseTime._cdel = lgs.elapseTimeDestroy
ElapseTime._cwalk = lgs.elapseTimeWalk
ElapseTime._cwalk_back = lgs.elapseTimeWalkBack

Combination._cnew = lgs.comboNew
Combination._cdel = lgs.comboDestroy
Combination._cwalk = lgs.comboWalk
Combination._cwalk_back = lgs.comboWalkBack

TripBoard._cnew = lgs.tbNew
TripBoard._cdel = lgs.tbDestroy
TripBoard._cadd_boarding = lgs.tbAddBoarding
TripBoard._cwalk = lgs.epWalk

Crossing._cnew = lgs.crNew
Crossing._cdel = lgs.crDestroy

TripAlight._cnew = lgs.alNew
TripAlight._cdel = lgs.alDestroy

HeadwayBoard._cnew = lgs.hbNew
HeadwayBoard._cdel = lgs.hbDestroy
HeadwayBoard._cwalk = lgs.epWalk

HeadwayAlight._cnew = lgs.haNew
HeadwayAlight._cdel = lgs.haDestroy
HeadwayAlight._cwalk = lgs.epWalk

WalkOptions._cnew = lgs.woNew
WalkOptions._cdel = lgs.woDestroy

GenericPyPayload._cnew = lgs.cpNew
GenericPyPayload._cdel = lgs.cpDestroy

########NEW FILE########
__FILENAME__ = graphcrawler
from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys

def string_spt_vertex(vertex, level=0):
    ret = ["  "*level+str(vertex)]
    
    for edge in vertex.outgoing:
        ret.append( "  "*(level+1)+"%s"%(edge) )
        ret.append( string_spt_vertex( edge.to_v, level+1 ) )
    
    return "\n".join(ret)

class GraphCrawler(Servable):
    def __init__(self, graphdb_filename):
        self.graphdb = GraphDatabase( graphdb_filename )
    
    def vertices(self, like=None):
        if like:
            return "\n".join( ["<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><br>"%(vl[0], vl[0]) 
                               for vl in self.graphdb.execute("SELECT label from vertices where label like ? order by label", (like,)) ])
        else:
            return "\n".join( ["<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><br>"%(vl[0], vl[0]) 
                               for vl in self.graphdb.execute("SELECT label from vertices order by label") ])
    vertices.mime = "text/html"
    
    def vertex(self, label, currtime=None, hill_reluctance=1.5, walking_speed=0.85):
        currtime = currtime or int(time.time())
        
        ret = []
        ret.append( "<h1>%s</h1>"%label )
        
        wo = WalkOptions()
        ret.append( "<h3>walk options</h3>" )
        ret.append( "<li>transfer_penalty: %s</li>"%wo.transfer_penalty )
        ret.append( "<li>turn_penalty: %s</li>"%wo.turn_penalty )
        ret.append( "<li>walking_speed: %s</li>"%wo.walking_speed )
        ret.append( "<li>walking_reluctance: %s</li>"%wo.walking_reluctance )
        ret.append( "<li>uphill_slowness: %s</li>"%wo.uphill_slowness )
        ret.append( "<li>downhill_fastness: %s</li>"%wo.downhill_fastness )
        ret.append( "<li>hill_reluctance: %s</li>"%wo.hill_reluctance )
        ret.append( "<li>max_walk: %s</li>"%wo.max_walk )
        ret.append( "<li>walking_overage: %s</li>"%wo.walking_overage )
        
        
        ret.append( "<h3>incoming from:</h3>" )
        for i, (vertex1, vertex2, edgetype) in enumerate( self.graphdb.all_incoming( label ) ):
            s1 = State(1,int(currtime))
            wo = WalkOptions()
            wo.hill_reluctance=hill_reluctance
            wo.walking_speed=walking_speed
            s0 = edgetype.walk_back( s1, wo )
            
            if s0:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;&currtime=%d\">%s@%d</a>"%(vertex1, s0.time, vertex1, s1.time)
            else:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a>"%(vertex1, vertex1)
            
            ret.append( "%s<br><pre>&nbsp;&nbsp;&nbsp;via %s (<a href=\"/incoming?label=&quot;%s&quot;&edgenum=%d\">details</a>)</pre>"%(toterm, cgi.escape(repr(edgetype)), vertex2, i) )
            
            if s0:
                ret.append( "<pre>&nbsp;&nbsp;&nbsp;%s</pre>"%cgi.escape(str(s0)) )
            
            
        ret.append( "<h3>outgoing to:</h3>" )
        for i, (vertex1, vertex2, edgetype) in enumerate( self.graphdb.all_outgoing( label ) ):
            s0 = State(1,int(currtime))
            wo = WalkOptions()
            wo.hill_reluctance=hill_reluctance
            wo.walking_speed=walking_speed
            s1 = edgetype.walk( s0, wo )
            
            if s1:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;&currtime=%d\">%s@%d</a>"%(vertex2, s1.time, vertex2, s1.time)
            else:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a>"%(vertex2, vertex2)
            
            ret.append( "%s<br><pre>&nbsp;&nbsp;&nbsp;via %s (<a href=\"/outgoing?label=&quot;%s&quot;&edgenum=%d\">details</a>)</pre>"%(toterm, cgi.escape(repr(edgetype)), vertex1, i) )
            
            if s1:
                ret.append( "<pre>&nbsp;&nbsp;&nbsp;%s</pre>"%cgi.escape(str(s1)) )
        
        wo.destroy()
        
        return "".join(ret)
    vertex.mime = "text/html"
    
    def outgoing(self, label, edgenum):
        all_outgoing = list( self.graphdb.all_outgoing( label ) )
        
        fromv, tov, edge = all_outgoing[edgenum]
        
        return edge.expound()
        
    def incoming(self, label, edgenum):
        all_incoming = list( self.graphdb.all_incoming( label ) )
        
        fromv, tov, edge = all_incoming[edgenum]
        
        return edge.expound()
    
    def str(self):
        return str(self.graphdb)

def main():
    from sys import argv
    usage = "python graphcrawler.py graphdb_filename [port]"
    if len(argv)<2:
      print usage
      exit()

    graphdb_filename = argv[1]
    if len(argv) == 3:
        port = int(argv[2])
    else: port = 8081
    gc = GraphCrawler(graphdb_filename)
    print "serving on port %d" % port
    gc.run_test_server(port=port)
            

if __name__ == '__main__':
    from sys import argv
    usage = "python graphcrawler.py graphdb_filename"
    if len(argv)<2:
      print usage
      exit()

    graphdb_filename = argv[1]

    gc = GraphCrawler(graphdb_filename)
    gc.run_test_server(8081)

########NEW FILE########
__FILENAME__ = gtfsdb
import csv
import sqlite3
import sys
import os
from zipfile import ZipFile
from codecs import iterdecode
import datetime
from graphserver.util import withProgress

class UTF8TextFile(object):
    def __init__(self, fp):
        self.fp = fp
        
    def next(self):
        nextline = self.fp.next()
        return nextline.encode( "ascii", "ignore" )
        
    def __iter__(self):
        return self

def between(n, a, b):
    return n >= a and n<=b

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])
        
def parse_gtfs_time(timestr):
    return (lambda x:int(x[0])*3600+int(x[1])*60+int(x[2]))(timestr.split(":")) #oh yes I did
    
def parse_gtfs_date(datestr):
    return (int(datestr[0:4]), int(datestr[4:6]), int(datestr[6:8]))

def create_table(cc, gtfs_basename, header):
    # Create stoptimes table
    sqlite_field_definitions = ["%s %s"%(field_name, field_type if field_type else "TEXT") for field_name, field_type, field_converter in header]
    cc.execute("create table %s (%s)"%(gtfs_basename,",".join(sqlite_field_definitions)))

def load_gtfs_table_to_sqlite(fp, gtfs_basename, cc, header=None, verbose=False):
    """header is iterable of (fieldname, fieldtype, processing_function). For example, (("stop_sequence", "INTEGER", int),). 
    "TEXT" is default fieldtype. Default processing_function is lambda x:x"""
    
    ur = UTF8TextFile( fp )
    rd = csv.reader( ur )

    # create map of field locations in gtfs header to field locations as specified by the table definition
    gtfs_header = [x.strip() for x in rd.next()]

    print(gtfs_header)
    
    gtfs_field_indices = dict(zip(gtfs_header, range(len(gtfs_header))))
    
    field_name_locations = [gtfs_field_indices[field_name] if field_name in gtfs_field_indices else None for field_name, field_type, field_converter in header]
    field_converters = [field_definition[2] for field_definition in header]
    field_operator = list(zip(field_name_locations, field_converters))

    # populate stoptimes table
    insert_template = 'insert into %s (%s) values (%s)'%(gtfs_basename,",".join([x[0] for x in header]), ",".join(["?"]*len(header)))
    print( insert_template )
    for i, line in withProgress(enumerate(rd), 5000):
        # carry on quietly if there's a blank line in the csv
        if line == []:
            continue
        
        _line = []
        for i, converter in field_operator:
            if i<len(line) and i is not None and line[i].strip() != "":
                if converter:
                    _line.append( converter(line[i].strip()) )
                else:
                    _line.append( line[i].strip() )
            else:
                _line.append( None )
                
        cc.execute(insert_template, _line)
        
class Pattern:
    def __init__(self, pattern_id, stop_ids, dwells):
        self.pattern_id = pattern_id
        self.stop_ids = stop_ids
        self.dwells = dwells
    
    @property
    def signature(self):
        return (tuple(self.stops), tuple(self.dwells))

class TripBundle:
    def __init__(self, gtfsdb, pattern):
        self.gtfsdb = gtfsdb
        self.pattern = pattern
        self.trip_ids = []
        
    def add_trip(self, trip_id):
        self.trip_ids.append( trip_id )
        
    def stop_time_bundle( self, stop_id, service_id ):
        c = self.gtfsdb.conn.cursor()
        
        query = """
SELECT stop_times.* FROM stop_times, trips 
  WHERE stop_times.trip_id = trips.trip_id 
        AND trips.trip_id IN (%s) 
        AND trips.service_id = ? 
        AND stop_times.stop_id = ?
        AND arrival_time NOT NULL
        AND departure_time NOT NULL
  ORDER BY departure_time"""%(",".join(["'%s'"%x for x in self.trip_ids]))
      
        c.execute(query, (service_id,str(stop_id)))
        
        return list(c)
    
    def stop_time_bundles( self, service_id ):
        
        c = self.gtfsdb.conn.cursor()
        
        query = """
        SELECT stop_times.trip_id, 
               stop_times.arrival_time, 
               stop_times.departure_time, 
               stop_times.stop_id, 
               stop_times.stop_sequence, 
               stop_times.shape_dist_traveled 
        FROM stop_times, trips
        WHERE stop_times.trip_id = trips.trip_id
        AND trips.trip_id IN (%s)
        AND trips.service_id = ?
        AND arrival_time NOT NULL
        AND departure_time NOT NULL
        ORDER BY stop_sequence"""%(",".join(["'%s'"%x for x in self.trip_ids]))
            
        #bundle queries by trip_id
        
        trip_id_sorter = {}
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, shape_dist_traveled in c.execute(query, (service_id,)):
            if trip_id not in trip_id_sorter:
                trip_id_sorter[trip_id] = []
                
            trip_id_sorter[trip_id].append( (trip_id, arrival_time, departure_time, stop_id, stop_sequence, shape_dist_traveled) )
        
        return zip(*(trip_id_sorter.values()))
            
    def __repr__(self):
        return "<TripBundle n_trips: %d n_stops: %d>"%(len(self.trip_ids), len(self.pattern.stop_ids))

class GTFSDatabase:
    AGENCIES_DEF = ("agencies", (("agency_id",   None, None),
                                 ("agency_name",    None, None),
                                 ("agency_url", None, None),
                                 ("agency_timezone", None, None)))
    TRIPS_DEF = ("trips", (("route_id",   None, None),
                           ("trip_id",    None, None),
                           ("service_id", None, None),
                           ("shape_id", None, None),
                           ("trip_headsign", None, None)))
    ROUTES_DEF = ("routes", (("agency_id", None, None),
                             ("route_id", None, None),
                             ("route_short_name", None, None),
                             ("route_long_name", None, None),
                             ("route_type", "INTEGER", None)))
    STOP_TIMES_DEF = ("stop_times", (("trip_id", None, None), 
                                     ("arrival_time", "INTEGER", parse_gtfs_time),
                                     ("departure_time", "INTEGER", parse_gtfs_time),
                                     ("stop_id", None, None),
                                     ("stop_sequence", "INTEGER", None),
                                     ("shape_dist_traveled", "FLOAT", None)))
    STOPS_DEF = ("stops", (("stop_id", None, None),
                           ("stop_name", None, None),
                           ("stop_lat", "FLOAT", None),
                           ("stop_lon", "FLOAT", None)) )
    CALENDAR_DEF = ("calendar", (("service_id", None, None),
                                 ("monday", "INTEGER", None),
                                 ("tuesday", "INTEGER", None),
                                 ("wednesday", "INTEGER", None),
                                 ("thursday", "INTEGER", None),
                                 ("friday", "INTEGER", None),
                                 ("saturday", "INTEGER", None),
                                 ("sunday", "INTEGER", None),
                                 ("start_date", None, None),
                                 ("end_date", None, None)) )
    CAL_DATES_DEF = ("calendar_dates", (("service_id", None, None),
                                        ("date", None, None),
                                        ("exception_type", "INTEGER", None)) )
    AGENCY_DEF = ("agency", (("agency_id", None, None),
                             ("agency_name", None, None),
                             ("agency_url", None, None),
                             ("agency_timezone", None, None)) )
                             
    FREQUENCIES_DEF = ("frequencies", (("trip_id", None, None),
                                       ("start_time", "INTEGER", parse_gtfs_time),
                                       ("end_time", "INTEGER", parse_gtfs_time),
                                       ("headway_secs", "INTEGER", None)) )
    TRANSFERS_DEF = ("transfers", (("from_stop_id", None, None),    
                                       ("to_stop_id", None, None),
                                       ("transfer_type", "INTEGER", None),
                                       ("min_transfer_time", "FLOAT", None)))
    SHAPES_DEF = ("shapes", (("shape_id", None, None),
                               ("shape_pt_lat", "FLOAT", None),
                               ("shape_pt_lon", "FLOAT", None),
                               ("shape_pt_sequence", "INTEGER", None),
                               ("shape_dist_traveled", "FLOAT", None)))
    
    GTFS_DEF = (TRIPS_DEF, 
                STOP_TIMES_DEF, 
                STOPS_DEF, 
                CALENDAR_DEF, 
                CAL_DATES_DEF, 
                AGENCY_DEF, 
                FREQUENCIES_DEF, 
                ROUTES_DEF, 
                TRANSFERS_DEF,
                SHAPES_DEF)
    
    def __init__(self, sqlite_filename, overwrite=False):
        self.dbname = sqlite_filename
        
        if overwrite:
            try:
                os.remove(sqlite_filename)
            except:
                pass
        
        self.conn = sqlite3.connect( sqlite_filename )
        
    def get_cursor(self):
        # Attempts to get a cursor using the current connection to the db. If we've found ourselves in a different thread
        # than that which the connection was made in, re-make the connection.
        
        try:
            ret = self.conn.cursor()
        except sqlite3.ProgrammingError:
            self.conn = sqlite3.connect(self.dbname)
            ret = self.conn.cursor()
            
        return ret

    def load_gtfs(self, gtfs_filename, tables=None, reporter=None, verbose=False):
        c = self.get_cursor()

        if not os.path.isdir( gtfs_filename ):
            zf = ZipFile( gtfs_filename )

        for tablename, table_def in self.GTFS_DEF:
            if tables is not None and tablename not in tables:
                print( "skipping table %s - not included in 'tables' list"%tablename )
                continue

            print( "creating table %s\n"%tablename )
            create_table( c, tablename, table_def )
            print( "loading table %s\n"%tablename )
            
            try:
                if not os.path.isdir( gtfs_filename ):
                    trips_file = iterdecode( zf.read(tablename+".txt").split("\n"), "utf-8" )
                else:
                    trips_file = iterdecode( open( os.path.join( gtfs_filename, tablename+".txt" ) ), "utf-8" )
                load_gtfs_table_to_sqlite(trips_file, tablename, c, table_def, verbose=verbose)
            except (KeyError, IOError):
                print( "NOTICE: GTFS feed has no file %s.txt, cannot load\n"%tablename )
    
        self._create_indices(c)
        self.conn.commit()
        c.close()

    def _create_indices(self, c):
        
        c.execute( "CREATE INDEX stop_times_trip_id ON stop_times (trip_id)" )
        c.execute( "CREATE INDEX stop_times_stop_id ON stop_times (stop_id)" )
        c.execute( "CREATE INDEX trips_trip_id ON trips (trip_id)" )
        c.execute( "CREATE INDEX stops_stop_lat ON stops (stop_lat)" )
        c.execute( "CREATE INDEX stops_stop_lon ON stops (stop_lon)" )
        c.execute( "CREATE INDEX route_route_id ON routes (route_id)" )
        c.execute( "CREATE INDEX trips_route_id ON trips (route_id)" )

    def stops(self):
        c = self.get_cursor()
        
        c.execute( "SELECT * FROM stops" )
        ret = list(c)
        
        c.close()
        return ret
        
    def stop(self, stop_id):
        c = self.get_cursor()
        c.execute( "SELECT * FROM stops WHERE stop_id = ?", (stop_id,) )
        ret = c.next()
        c.close()
        return ret
        
    def count_stops(self):
        c = self.get_cursor()
        c.execute( "SELECT count(*) FROM stops" )
        
        ret = c.next()[0]
        c.close()
        return ret

    def compile_trip_bundles(self, maxtrips=None, reporter=None):
        
        c = self.get_cursor()

        patterns = {}
        bundles = {}

        c.execute( "SELECT count(*) FROM trips" )
        n_trips = c.next()[0]
        
        if maxtrips is not None and maxtrips < n_trips:
            n_trips = maxtrips;

        if maxtrips is not None:
            c.execute( "SELECT trip_id FROM trips LIMIT ?", (maxtrips,) )
        else:
            c.execute( "SELECT trip_id FROM trips" )
            
        for i, (trip_id,) in enumerate(c):
            if reporter and i%(n_trips//50+1)==0: reporter.write( "%d/%d trips grouped by %d patterns\n"%(i,n_trips,len(bundles)))
            
            d = self.get_cursor()
            d.execute( "SELECT trip_id, arrival_time, departure_time, stop_id FROM stop_times WHERE trip_id=? AND arrival_time NOT NULL AND departure_time NOT NULL ORDER BY stop_sequence", (trip_id,) )
            
            stop_times = list(d)
            
            stop_ids = [stop_id for trip_id, arrival_time, departure_time, stop_id in stop_times]
            dwells = [departure_time-arrival_time for trip_id, arrival_time, departure_time, stop_id in stop_times]
            pattern_signature = (tuple(stop_ids), tuple(dwells))
            
            if pattern_signature not in patterns:
                pattern = Pattern( len(patterns), stop_ids, dwells )
                patterns[pattern_signature] = pattern
            else:
                pattern = patterns[pattern_signature]
                
            if pattern not in bundles:
                bundles[pattern] = TripBundle( self, pattern )
            
            bundles[pattern].add_trip( trip_id )

        c.close()
        
        return bundles.values()
        
    def nearby_stops(self, lat, lng, range):
        c = self.get_cursor()
        
        c.execute( "SELECT * FROM stops WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? And ?", (lat-range, lat+range, lng-range, lng+range) )
        
        for row in c:
            yield row

    def extent(self):
        c = self.get_cursor()
        
        c.execute( "SELECT min(stop_lon), min(stop_lat), max(stop_lon), max(stop_lat) FROM stops" )
        
        ret = c.next()
        c.close()
        return ret
        
    def execute(self, query, args=None):
        
        c = self.get_cursor()
        
        if args:
            c.execute( query, args )
        else:
            c.execute( query )
            
        for record in c:
            yield record
        c.close()
        
    def agency_timezone_name(self, agency_id_or_name=None):

        if agency_id_or_name is None:
            agency_timezone_name = list(self.execute( "SELECT agency_timezone FROM agency LIMIT 1" ))
        else:
            agency_timezone_name = list(self.execute( "SELECT agency_timezone FROM agency WHERE agency_id=? OR agency_name=?", (agency_id_or_name,agency_id_or_name) ))
        
        return agency_timezone_name[0][0]
        
    def day_bounds(self):
        daymin = list( self.execute("select min(departure_time) from stop_times") )[0][0]
        daymax = list( self.execute("select max(arrival_time) from stop_times") )[0][0]
        
        return (daymin, daymax)
        
    def date_range(self):
        start_date, end_date = list( self.execute("select min(start_date), max(end_date) from calendar") )[0]
        
        start_date = start_date or "99999999" #sorted greater than any date
        end_date = end_date or "00000000" #sorted earlier than any date
        
        first_exception_date, last_exception_date = list( self.execute("select min(date), max(date) from calendar_dates WHERE exception_type=1") )[0]
          
        first_exception_date = first_exception_date or "99999999"
        last_exceptoin_date = last_exception_date or "00000000"
        
        start_date = min(start_date, first_exception_date)
        end_date = max(end_date, last_exception_date )

        return datetime.date( *parse_gtfs_date(start_date) ), datetime.date( *parse_gtfs_date(end_date) )
    
    DOWS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    DOW_INDEX = dict(zip(range(len(DOWS)),DOWS))
    
    def service_periods(self, sample_date):
        datetimestr = sample_date.strftime( "%Y%m%d" ) #sample_date to string like "20081225"
        datetimeint = int(datetimestr)              #int like 20081225. These ints have the same ordering as regular dates, so comparison operators work
        
        # Get the gtfs date range. If the sample_date is out of the range, no service periods are in effect
        start_date, end_date = self.date_range()
        if sample_date < start_date or sample_date > end_date:
            return []
        
        # Use the day-of-week name to query for all service periods that run on that day
        dow_name = self.DOW_INDEX[sample_date.weekday()]
        service_periods = list( self.execute( "SELECT service_id, start_date, end_date FROM calendar WHERE %s=1"%dow_name ) )
         
        # Exclude service periods whose range does not include this sample_date
        service_periods = [x for x in service_periods if (int(x[1]) <= datetimeint and int(x[2]) >= datetimeint)]
        
        # Cut service periods down to service IDs
        sids = set( [x[0] for x in service_periods] )
            
        # For each exception on the given sample_date, add or remove service_id to the accumulating list
        
        for exception_sid, exception_type in self.execute( "select service_id, exception_type from calendar_dates WHERE date = ?", (datetimestr,) ):
            if exception_type == 1:
                sids.add( exception_sid )
            elif exception_type == 2:
                if exception_sid in sids:
                    sids.remove( exception_sid )
                
        return list(sids)
        
    def service_ids(self):
        query = "SELECT DISTINCT service_id FROM (SELECT service_id FROM calendar UNION SELECT service_id FROM calendar_dates)"
        
        return [x[0] for x in self.execute( query )]
    
    def shape(self, shape_id):
        query = "SELECT shape_pt_lon, shape_pt_lat, shape_dist_traveled from shapes where shape_id = ? order by shape_pt_sequence"
        
        return list(self.execute( query, (shape_id,) ))
    
    def shape_from_stops(self, trip_id, stop_sequence1, stop_sequence2):
        query = """SELECT stops.stop_lon, stop_lat 
                   FROM stop_times as st, stops 
                   WHERE trip_id=? and st.stop_id=stops.stop_id and stop_sequence between ? and ? 
                   ORDER by stop_sequence"""
                   
        return list(self.execute( query, (trip_id, stop_sequence1, stop_sequence2) ))
    
    def shape_between(self, trip_id, stop_sequence1, stop_sequence2):
        # get shape_id of trip
        shape_id = list(self.execute( "SELECT shape_id FROM trips WHERE trip_id=?", (trip_id,) ))[0][0]
        
        if shape_id is None:
            return self.shape_from_stops( trip_id, stop_sequence1, stop_sequence2 )
        
        query = """SELECT min(shape_dist_traveled), max(shape_dist_traveled)
                     FROM stop_times
                     WHERE trip_id=? and (stop_sequence = ? or stop_sequence = ?)"""
        t_min, t_max = list(self.execute( query, (trip_id, stop_sequence1, stop_sequence2) ))[0]
        
        if t_min is None or \
           ( hasattr(t_min,"strip") and t_min.strip()=="" ) or \
           t_max is None or \
           ( hasattr(t_max,"strip") and t_max.strip()=="" ) :
            return self.shape_from_stops( trip_id, stop_sequence1, stop_sequence2 )
                
        ret = []
        for (lon1, lat1, dist1), (lon2, lat2, dist2) in cons(self.shape(shape_id)):
            if between( t_min, dist1, dist2 ):
                percent_along = (t_min-dist1)/float((dist2-dist1)) if dist2!=dist1 else 0
                lat = lat1+percent_along*(lat2-lat1)
                lon = lon1+percent_along*(lon2-lon1)
                ret.append( (lon, lat) )

            if between( dist2, t_min, t_max ):
                ret.append( (lon2, lat2) )
                
            if between( t_max, dist1, dist2):
                percent_along = (t_max-dist1)/float((dist2-dist1)) if dist2!=dist1 else 0
                lat = lat1+percent_along*(lat2-lat1)
                lon = lon1+percent_along*(lon2-lon1)
                ret.append( (lon, lat) )
                
        return ret
                

def main_inspect_gtfsdb():
    from sys import argv
    
    if len(argv) < 2:
        print("usage: python gtfsdb.py gtfsdb_filename [query]")
        exit()
    
    gtfsdb_filename = argv[1]
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    
    if len(argv) == 2:
        for table_name, fields in gtfsdb.GTFS_DEF:
            print("Table: %s"%table_name)
            for field_name, field_type, field_converter in fields:
                print("\t%s %s"%(field_type, field_name))
        exit()
    
    query = argv[2]
    for record in gtfsdb.execute( query ):
        print(record)
    
    #for stop_id, stop_name, stop_lat, stop_lon in gtfsdb.stops():
    #    print( stop_lat, stop_lon )
    #    gtfsdb.nearby_stops( stop_lat, stop_lon, 0.05 )
    #    break
    
    #bundles = gtfsdb.compile_trip_bundles()
    #for bundle in bundles:
    #    for departure_set in bundle.iter_departures("WKDY"):
    #        print( departure_set )
    #    
    #    #print( len(bundle.trip_ids) )
    #    sys.stdout.flush()

    pass

from optparse import OptionParser

def main_compile_gtfsdb():
    parser = OptionParser()
    parser.add_option("-t", "--table", dest="tables", action="append", default=[], help="copy over only the given tables")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="make a bunch of noise" )

    (options, args) = parser.parse_args()
    if len(options.tables)==0:
        options.tables=None

    if len(args) < 2:
        print("Converts GTFS file to GTFS-DB, which is super handy\nusage: python process_gtfs.py gtfs_filename gtfsdb_filename")
        exit()
    
    gtfsdb_filename = args[1]
    gtfs_filename = args[0]
 
    gtfsdb = GTFSDatabase( gtfsdb_filename, overwrite=True )
    gtfsdb.load_gtfs( gtfs_filename, options.tables, reporter=sys.stdout, verbose=options.verbose )


if __name__=='__main__': 
    main_compile_gtfsdb()

########NEW FILE########
__FILENAME__ = gtfsdb_stats
from gtfsdb import GTFSDatabase
import sys

if __name__=='__main__':
  if len(sys.argv) < 2:
    print "usage: python gtfsdb_stats.py gtfsdb_filename"
    exit() 
 
  db = GTFSDatabase( sys.argv[1] )
  print "extent: %s"%(db.extent(),)
  print "stop count: %d"%db.count_stops()
   
  print "date range: %s"%(db.date_range(),)
########NEW FILE########
__FILENAME__ = process_gtfs
from gtfsdb import main_compile_gtfsdb
import sys

if __name__=='__main__': main_compile_gtfsdb()

########NEW FILE########
__FILENAME__ = elevation
import os
import re
import struct
from math import floor
from graphserver.vincenty import vincenty

def floatrange(start, stop, step):
    i = start
    while i <= stop:
        yield i
        i += step
        
def cons(ary):
    for i in range(len(ary)-1):
        yield ary[i], ary[i+1]

def split_line_segment(lng1, lat1, lng2, lat2, max_section_length):
    # Split line segment defined by (x1, y1, x2, y2) into a set of points 
    # (x,y,displacement) spaced less than max_section_length apart
    
    if lng1==lng2 and lat1==lat2:
        yield [lng1, lat1, 0]
        yield [lng2, lat2, 0]
        return
    
    street_len = vincenty(lat1, lng1, lat2, lng2)
    n_sections = int(street_len/max_section_length)+1
    
    geolen = ((lat2-lat1)**2 + (lng2-lng1)**2)**0.5
    section_len = geolen/n_sections
    street_vector = (lng2-lng1, lat2-lat1)
    unit_vector = [x/geolen for x in street_vector]
    
    for i in range(n_sections+1):
        vec = [x*section_len*i for x in unit_vector]
        vec = [lng1+vec[0], lat1+vec[1], (street_len/n_sections)*i]
        yield vec
        
def split_line_string(points, max_section_length):
    
    #Split each line segment in the linestring into segment smaller than max_section_length
    split_segs = []
    for (lng1, lat1), (lng2,lat2) in cons(points):
        split_seg = list(split_line_segment(lng1, lat1, lng2, lat2, max_section_length))
        split_segs.append( split_seg )
    
    #String together the sub linestrings into a single linestring
    ret = []
    segstart_s = 0
    for i, split_seg in enumerate(split_segs):
        for x, y, s in split_seg[:-1]:
            ret.append( (x, y, s+segstart_s) )
        
        if i==len(split_segs)-1:
            x, y, s = split_seg[-1]
            ret.append( (x, y, s+segstart_s) )
        
        segstart_s += split_seg[-1][2]
            
    return ret

class GridFloat:
    def __init__(self, basename):
        self._read_header( basename + ".hdr" )
        self.fp = open( basename + ".flt", "rb" )
        
    def _read_header(self, filename):
        fp = open( filename, "r" )
        
        self.ncols      = int( fp.readline()[14:].strip() )
        self.nrows      = int( fp.readline()[14:].strip() )
        self.xllcorner  = float( fp.readline()[14:].strip() )
        self.yllcorner  = float( fp.readline()[14:].strip() )
        self.cellsize   = float( fp.readline()[14:].strip() )
        self.NODATA_value = int( fp.readline()[14:].strip() )
        self.byteorder  = "<" if fp.readline()[14:].strip()=="LSBFIRST" else ">"
        
        self.left = self.xllcorner
        self.right = self.xllcorner + (self.ncols-1)*self.cellsize
        self.bottom = self.yllcorner
        self.top = self.yllcorner + (self.nrows-1)*self.cellsize
    
    @property
    def extent(self):
        return ( self.xllcorner, 
                 self.yllcorner, 
                 self.xllcorner+self.cellsize*(self.ncols-1), 
                 self.yllcorner+self.cellsize*(self.nrows-1) )
                 
    def contains(self, lng, lat):
        return not( lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top )
    
    def allcells(self):
        self.fp.seek(0)
        return struct.unpack( "%s%df"%(self.byteorder, self.nrows*self.ncols), self.fp.read())
        
    def extremes(self):
        mem = self.allcells()
        return (min(mem), max(mem))
    
    def cell( self, x, y ):
        position = (y*self.ncols+x)*4
        self.fp.seek(position)
        return struct.unpack( "%sf"%(self.byteorder), self.fp.read( 4 ) )[0]
        
    def elevation( self, lng, lat, interpolate=True ):
        if lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top:
            return None
        
        x = (lng-self.left)/self.cellsize
        y = (self.top-lat)/self.cellsize
        
        ulx = int(floor(x))
        uly = int(floor(y))
        
        ul = self.cell( ulx, uly )
        if not interpolate:
            return ul
        ur = self.cell( ulx+1, uly ) 
        ll = self.cell( ulx, uly+1 )
        lr = self.cell( ulx+1, uly+1 )
        
        cellleft = x%1
        celltop = y%1
        um = (ur-ul)*cellleft+ul #uppermiddle
        lm = (lr-ll)*cellleft+ll #lowermiddle
        
        return (lm-um)*celltop+um
        
    def profile(self, points, resolution=10):
        return [(s, self.elevation( lng, lat )) for lng, lat, s in split_line_string(points, resolution)]
            
class BIL:
    def __init__(self, basename):
        self._read_header( basename + ".hdr" )
        self.fp = open( basename + ".bil", "rb" )
        
    def _read_header(self, filename):
        HCW = 15 #header column width
        
        fp = open( filename, "r" )
        
        raw_header = dict([x.strip().split() for x in fp.read().strip().split("\n")])
        
        self.byteorder     = "<" if raw_header['BYTEORDER']=="I" else ">"
        self.layout        = raw_header['LAYOUT']
        self.ncols         = int( raw_header['NCOLS'] )
        self.nrows         = int( raw_header['NROWS'] )
        self.nbands        = int( raw_header['NBANDS'] )
        self.nbits         = int( raw_header['NBITS'] )
        self.bandrowbytes  = int( raw_header['BANDROWBYTES'] )
        self.totalrowbytes = int( raw_header['TOTALROWBYTES'] )
        self.pixeltype     = raw_header['PIXELTYPE']
        self.ulxmap        = float( raw_header['ULXMAP'] )
        self.ulymap        = float( raw_header['ULYMAP'] )
        self.xdim          = float( raw_header['XDIM'] )
        self.ydim          = float( raw_header['YDIM'] )
        self.nodata        = float( raw_header['NODATA'] )
        
        self.left = self.ulxmap
        self.right = self.ulxmap + (self.ncols-1)*self.xdim
        self.bottom = self.ulymap - (self.nrows-1)*self.ydim
        self.top = self.ulymap
    
    @property
    def extent(self):
        return ( self.left, 
                 self.bottom, 
                 self.right, 
                 self.top )
                 
    def contains(self, lng, lat):
        return not( lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top )
    
    def allcells(self):
        self.fp.seek(0)
        return struct.unpack( "%s%df"%(self.byteorder, self.nrows*self.ncols), self.fp.read())
        
    def extremes(self):
        mem = self.allcells()
        return (min(mem), max(mem))
    
    def cell( self, x, y ):
        position = (y*self.ncols+x)*4
        self.fp.seek(position)
        return struct.unpack( "%sf"%(self.byteorder), self.fp.read( 4 ) )[0]
        
    def elevation( self, lng, lat, interpolate=True ):
        if lng < self.left or lng >= self.right or lat <= self.bottom or lat > self.top:
            return None
        
        x = (lng-self.left)/self.xdim
        y = (self.top-lat)/self.ydim
        
        ulx = int(floor(x))
        uly = int(floor(y))
        
        ul = self.cell( ulx, uly )
        if not interpolate:
            return ul
        ur = self.cell( ulx+1, uly ) 
        ll = self.cell( ulx, uly+1 )
        lr = self.cell( ulx+1, uly+1 )
        
        cellleft = x%1
        celltop = y%1
        um = (ur-ul)*cellleft+ul #uppermiddle
        lm = (lr-ll)*cellleft+ll #lowermiddle
        
        return (lm-um)*celltop+um
        
    def profile(self, points, resolution=10):
        return [(s, self.elevation( lng, lat )) for lng, lat, s in split_line_string(points, resolution)]
            
class ElevationPile:
    def __init__(self):
        self.tiles = []
        
    def add(self, dem_basename):
        base_basename = "".join(dem_basename.split(".")[0:-1])
        format = dem_basename.split(".")[-1]
        if format == "flt":
            dem = GridFloat( base_basename )
        elif format == "bil":
            dem = BIL( base_basename )
        else:
            raise Exception( "Unknown DEM format '%s'"%format )
            
        self.tiles.append( dem )
        
    def elevation(self, lng, lat, interpolate=True):
        for tile in self.tiles:
            if tile.contains( lng, lat ):
                return tile.elevation( lng, lat, interpolate )
                
    def profile(self, points, resolution=10):
        return [(s, self.elevation( lng, lat )) for lng, lat, s in split_line_string(points, resolution)]

def selftest():
    BASENAME = "64883885"
    HOMEAREA = "./data/"+BASENAME
    
    gf = GridFloat(HOMEAREA, BASENAME)
    
    print gf
    print gf.extent
    
    toprow = [gf.cell(x, 0) for x in range(gf.ncols)]
    assert gf.elevation( gf.left, gf.top )==toprow[0]
    assert round(gf.elevation( gf.right-0.00000000001, gf.top ),5)==round(toprow[-1],5)
    
    bottomrow = [gf.cell(x,gf.nrows-2) for x in range(gf.ncols)]
    assert gf.elevation( gf.left, gf.bottom+0.000000001 ) == bottomrow[0]
    assert gf.elevation( gf.right-0.00000001, gf.bottom+0.00000001 ) == bottomrow[-2]
    
    assert gf.extremes() == (4.7509551048278809, 144.3404541015625)
    
    assert round(gf.elevation( (gf.right-gf.left)/2+gf.left, (gf.top-gf.bottom)/2+gf.bottom ),6) == round(89.278957367,6)

def create_elev_circles():
    from renderer.processing import MapRenderer
    
    BASENAME = "64883885"
    HOMEAREA = "./data/"+BASENAME
    
    gf = GridFloat(HOMEAREA, BASENAME)
    mr = MapRenderer("./renderer/application.linux/renderer")
    mr.start( gf.left, gf.bottom, gf.right, gf.top, 2000 )
    mr.smooth()
    mr.fill(250,230,230)
    mr.background(255,255,255)
    mr.strokeWeight(0.00007)
    
    for y in floatrange( gf.bottom, gf.top, (gf.top-gf.bottom)/50 ):
        for x in floatrange( gf.left, gf.right, (gf.right-gf.left)/50 ):
            elev = gf.elevation( x, y )
            mr.ellipse( x, y, elev*0.00001, elev*0.00001 )

    mr.saveLocal( "elevs.png" )
    mr.stop()
    
if __name__=='__main__':
    #selftest()
    
    BASENAME = "83892907"
    HOMEAREA = "./data/"+BASENAME
    
    gf = GridFloat( HOMEAREA, BASENAME )
    for x in gf.extent:
        print x

########NEW FILE########
__FILENAME__ = profile
from graphserver.ext.osm.osmdb import OSMDB
from elevation.elevation import ElevationPile, GridFloat, BIL
from graphserver.ext.osm.profiledb import ProfileDB

OSMDB_NAME = "./data/osm/map2.osmdb"
ELEV_BASENAME = "./data/83892907/83892907"
PROFILEDB_NAME = "profile.db"

def compress(ary, ratio):
    yield ary[0]
    for i in range(1, len(ary)-1, ratio):
        yield ary[i]
    yield ary[-1]

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

class Profile(object):
    def __init__(self):
        self.segs = []
        
    def add(self, seg):
        self.segs.append( seg )
        
    def concat(self, npoints=None):
        ret = []
        s = 0
        
        for seg in self.segs:
            if len(seg)<2:
                continue
            
            s0, e0 = seg[0]
            ret.append( (s, e0) )
            for (s0, e0), (s1, e1) in cons(seg):
                s += abs(s1-s0)
                ret.append( (s, e1) )
                
        if npoints is not None:
            compression = int(len(ret)/float(npoints))
            if compression <= 1:
                return ret
            
            return list(compress(ret,compression))
                
        return ret

def populate_profile_db( osmdb_name, profiledb_name, dem_basenames, resolution ):

    ddb = OSMDB( osmdb_name )
    elevs = ElevationPile()
    for dem_basename in dem_basenames:
        elevs.add( dem_basename )
    pdb = ProfileDB( profiledb_name, overwrite=True )

    n = ddb.count_edges()
    print "Profiling %d way segments"%n
    
    for i, (id, parent_id, node1, node2, dist, geom, tags) in enumerate( ddb.edges() ):
        if i%1000==0: print "%d/%d"%(i,n)
        
        raw_profile = elevs.profile( geom, resolution )
        profile = []
        
        tunnel = tags.get('tunnel')
        bridge = tags.get('bridge')
        if tunnel == 'yes' or tunnel == 'true' or bridge == 'yes' or bridge == 'true':
            if len(raw_profile) > 0:
                ss, ee = raw_profile[0]
                if ee is not None: profile.append( (ss,ee) )
            if len(raw_profile) > 1:
                ss, ee = raw_profile[-1]
                if ee is not None: profile.append( (ss,ee) )
        else:
            for ss, ee in raw_profile:
                if ee is not None: profile.append( (ss,ee) )
                
        pdb.store( id, profile )
        
    pdb.conn.commit()

from sys import argv
def main():
    usage = "python profile.py osmdb_name profiledb_name resolution dem_basename "
    if len(argv) < 5:
        print usage
        exit()

    osmdb_name = argv[1]
    profiledb_name = argv[2]
    resolution = int(argv[3])
    dem_basenames = argv[4:]

    print "osmdb name:", osmdb_name
    print "profiledb name:", profiledb_name
    print "resolution:", resolution
    print "dem_basenames:", dem_basenames
    
    populate_profile_db(osmdb_name, profiledb_name, dem_basenames, resolution)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = profiledb
from graphserver.ext.osm.profiledb import main

if __name__=='__main__':
    main()
########NEW FILE########
__FILENAME__ = graph
import time
from osm import OSM, dist
import sys

sys.path.append('../../..')
from graphserver.core import Graph, Street, State


class OSMGraph(Graph):
        
    def __init__(self, filename_osmobject_or_stream, projection):
        """ Builds an OSM graph based on a filename or filehandle.  Projection is used for calculating lengths.
        Subclasses can override the is_valid_way and create_edgepayload methods to filter path types and 
        create alternative payloads."""
        
        super(OSMGraph, self).__init__()
        self.projection = projection
        
        t0 = time.time()
        if filename_osmobject_or_stream.__class__ == OSM:
            self.osm = filename_osmobject_or_stream
            osm = self.osm
        else:
            print "parsing OSM file"
            osm = OSM(filename_osmobject_or_stream)
            self.osm = osm
            t1 = time.time()
            print "parsing took: %f"%(t1-t0)
            t0 = t1

        print "load vertices into memory"
        for nodeid in osm.nodes.keys():
            self.add_vertex( str(nodeid) )

        print "load edges into memory"
        for way in osm.ways.values():
            if self.is_valid_way(way):
                # need two copies of the payload
                self.add_edge( str(way.fromv), str(way.tov), self.create_edgepayload(way) )
                self.add_edge( str(way.tov), str(way.fromv), self.create_edgepayload(way) )
        t1 = time.time()
        print "populating graph took: %f"%(t1-t0)
    
    def is_valid_way(self, way):
        return 'highway' in way.tags
    
    def create_edgepayload(self, way):
        len = way.length()
        return Street( way.id, len )
            
    def shortest_path_tree(self, from_v, to_v, state):
        t0 = time.time()
        spt = super(OSMGraph, self).shortest_path_tree( from_v, to_v, state)
        t1 = time.time()
        print "shortest_path_tree took: %f"%(t1-t0)
        return spt
    
    def write_graph(self, fp, format="%(from)s:%(to)s:%(points)s\n", reproject=True, point_delim=","):
        for edge in self.edges:
            osmway = self.osm.ways[ edge.payload.name ]
            if reproject:
                points = osmway.get_projected_points(self.projection)
            else:
                points = osmway.get_projected_points()
            fp.write( format % {'from':edge.from_v.label,
                                'to':edge.to_v.label,
                                'name':osmway.tags.get('name',''),
                                'length':edge.payload.length,
                                'points':point_delim.join( [" ".join([str(c) for c in p]) for p in points] )})
            
    
    def write_spt(self, fp, spt, format="%(from)s:%(to)s:%(length)f:%(weight)d:%(points)s\n", 
                  reproject=True, point_delim=","):
        """ Writes out a shortest path tree. """
        for edge in spt.edges:
            osmway = self.osm.ways[ edge.payload.name ]
            state = edge.to_v.payload
            if reproject:
                points = osmway.get_projected_points(self.projection)
            else:
                points = osmway.get_projected_points()
            length = edge.payload.length #osmway.length(osm.nodes)
            elapsed = state.time
            num_transfers = state.num_transfers
            
            fp.write( format % {'from':edge.from_v.label,
                                'to':edge.to_v.label,
                                'length':length,
                                'weight':state.weight,
                                'state':state,
                                'time':state.time,
                                'dist_walked':state.dist_walked,
                                'num_transfers':state.num_transfers,
                                'points':point_delim.join( [" ".join([str(c) for c in p]) for p in points] )} )
    
    def find_nearest_vertex(self, lng, lat):
        return self.osm.find_nearest_node(lng, lat).id

########NEW FILE########
__FILENAME__ = load_osm
from osm import OSM,Node,Way
import sys
sys.path.append('../../..')
from graphserver.core import Graph, Street

class OSMLoadable:
    def load_osm(self, osm_filename_or_object, projection, multipliers=[], prefix="osm"):
        """multipliers is a dict of highway types to edge weight multipliers (highwaytype,multiplier) which effect the
           preferential weighting of a kind of edge. For example, {'cycleway':0.333} makes cycleways three
           times easier to traverse"""

        if type(osm_filename_or_object) == str:
            osm = OSM(osm_filename_or_object)
        else:
            osm = osm_filename_or_object

        for way in osm.ways.values():
            # Nodes will be added to the vertex twice. That's not a problem: the second time, nothing happens.
            # Do this instead of adding each osm.nodes.keys(), because not all nodes are connected to other nodes
            self.add_vertex( prefix+str(way.fromv) )
            self.add_vertex( prefix+str(way.tov) )

        for wayid, way in osm.ways.iteritems():
            if 'highway' in way.tags:
                #len = way.length(projection)
                # distance is not dependant on projection since osm nodes always use the same srs
                len = way.length_haversine()

                if way.tags['highway'] in multipliers:
                    len = len*multipliers[way.tags['highway']]

                self.add_edge( prefix+str(way.fromv), prefix+str(way.tov), Street( wayid, len ) )
                self.add_edge( prefix+str(way.tov), prefix+str(way.fromv), Street( wayid, len ) )

########NEW FILE########
__FILENAME__ = osm
import xml.sax
import copy
from math import *
from graphserver.vincenty import vincenty

INFINITY = float('inf')

def download_osm(left,bottom,right,top):
    """ Return a filehandle to the downloaded data."""
    from urllib.request import urlopen
    fp = urlopen( "http://api.openstreetmap.org/api/0.5/map?bbox=%f,%f,%f,%f"%(left,bottom,right,top) )
    return fp

def dist(x1,y1,x2,y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5

def dist_haversine(x0,y0,x1,y1):
    # Use spherical geometry to calculate the surface distance, in meters
    # between two geodesic points. Uses Haversine formula:
    # http://en.wikipedia.org/wiki/Haversine_formula
    radius = 6371000 # Earth mean radius in m
    lon0 = x0 * PI / 180 #rad
    lat0 = y0 * PI / 180 #rad
    lon1 = x1 * PI / 180 #rad
    lat1 = y1 * PI / 180 #rad
    dLat = (lat1 - lat0) #rad
    dLon = (lon1 - lon0) #rad
    a = sin(dLat/2) * sin(dLat/2) + cos(lat0) * cos(lat1) * sin(dLon/2) * sin(dLon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return radius * c

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}

    def __repr__(self):
        return "<Node id='%s' (%s, %s) n_tags=%d>"%(self.id, self.lon, self.lat, len(self.tags))
        
class Way:
    def __init__(self, id, osm, tolerant=False):
        self.osm = osm
        self.id = id
        self.nd_ids = []
        self.tags = {}
        self.tolerant = tolerant #skip over dangling nd references
    
    @property
    def nds(self):
        for nd_id in self.nd_ids:
            try:
                yield self.osm.nodes[nd_id]
            except KeyError:
                if self.tolerant:
                    pass
                else:
                    raise KeyError( "Way references undefined node '%s'"%nd_id )
    @property
    def geom(self):
        return [(nd.lon, nd.lat) for nd in self.nds]
            
    @property
    def bbox(self):
        l = INFINITY
        b = INFINITY
        r = -INFINITY
        t = -INFINITY
        for x,y in self.geom:
            l = min(l,x)
            r = max(r,x)
            b = min(b,y)
            t = max(t,y)
        return (l,b,r,t)
    
    def split(self, dividers):
        # slice the node-array using this nifty recursive function
        def slice_array(ar, dividers):
            for i in range(1,len(ar)-1):
                if dividers[ar[i]]>1:
                    #print "slice at %s"%ar[i]
                    left = ar[:i+1]
                    right = ar[i:]

                    rightsliced = slice_array(right, dividers)

                    return [left]+rightsliced
            return [ar]

        slices = slice_array(self.nd_ids, dividers)

        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nd_ids = slice
            ret.append( littleway )
            i += 1

        return ret

    def get_projected_points(self, reprojection_func=lambda x,y:(x,y)):
        """nodedir is a dictionary of nodeid->node objects. If reprojection_func is None, returns unprojected points"""
        ret = []

        for nodeid in self.nd_ids:
            node = self.osm.nodes[ nodeid ]
            ret.append( reprojection_func(node.lon,node.lat) )

        return ret

    def to_canonical(self, srid, reprojection_func=None):
        """Returns canonical string for this geometry"""

        return "SRID=%d;LINESTRING(%s)"%(srid, ",".join( ["%f %f"%(x,y) for x,y in self.get_projected_points()] ) )


    def length(self):
        """nodedir is a dictionary of nodeid->node objects"""
        ret = 0

        for i in range(len(self.nd_ids)-1):
            thisnode = self.osm.nodes[ self.nd_ids[i] ]
            nextnode = self.osm.nodes[ self.nd_ids[i+1] ]

            ret += vincenty(thisnode.lat, thisnode.lon, nextnode.lat, nextnode.lon)

        return ret

    def length_haversine(self):
        ret = 0

        for i in range(len(self.nds)-1):
            thisnode = self.osm.nodes[ self.nds[i] ]
            nextnode = self.osm.nodes[ self.nds[i+1] ]
            ret += dist(thisnode.lon,thisnode.lat,nextnode.lon,nextnode.lat)

        return ret

    @property
    def fromv(self):
        return self.nd_ids[0]

    @property
    def tov(self):
        return self.nd_ids[-1]
        
    def __repr__(self):
        return "<Way id='%s' n_nds=%d n_tags=%d>"%(self.id, len(self.nd_ids), len(self.tags))

class OSM:

    def __init__(self, filename_or_stream, tolerant=False):
        """ File can be either a filename or stream/file object."""
        nodes = {}
        ways = {}

        superself = self

        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass

            @classmethod
            def startDocument(self):
                pass

            @classmethod
            def endDocument(self):
                pass

            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'], superself, tolerant)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nd_ids.append( attrs['ref'] )

            @classmethod
            def endElement(self,name):
                if name=='node':
                    nodes[self.currElem.id] = self.currElem
                elif name=='way':
                    ways[self.currElem.id] = self.currElem

            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(filename_or_stream, OSMHandler)

        self.nodes = nodes
        self.ways = ways

        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        
        todel = []
        for way in self.ways.values():
            if len(way.nd_ids) < 2:       #if a way has only one node, delete it out of the osm collection
                todel.append( way.id )
        #have to do it in two passes, or else you change the size of dict during iteration
        for way_id in todel:
            del self.ways[way_id]

        for way in self.ways.values():
            for node in way.nd_ids:
                try:
                    node_histogram[node] += 1
                except KeyError:
                    node_histogram[node] = 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.items():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways

    @property
    def connecting_nodes(self):
        """List of nodes that are the endpoint of one or more ways"""

        ret = {}
        for way in self.ways.values():
            ret[way.fromv] = self.nodes[way.fromv]
            ret[way.tov] = self.nodes[way.tov]

        return ret.values()

    @classmethod
    def download_from_bbox(cls, left, bottom, right, top ):
        """ Retrieve remote OSM data."""
        fp = download_osm(left, bottom, right, top)
        osm = cls(fp)
        fp.close()
        return osm

    def find_nearest_node(self, lng, lat):
        """ Brute force effort to find the nearest start or end node based on lat/lng distances."""
        best = self.nodes[self.ways[self.ways.keys()[0]].nd_ids[0]]
        bdist = dist(best.lon, best.lat, lng, lat)
        for id, way in self.ways.iteritems():
            for i in (0,-1):
                nd = self.nodes[way.nd_ids[i]]
                d = dist(lng, lat, nd.lon, nd.lat)
                if d < bdist:
                    bdist = d
                    best = nd
        return best
    
    @property
    def bbox(self):
        l = INFINITY
        b = INFINITY
        r = -INFINITY
        t = -INFINITY
        
        for way in self.ways.values():
            ll, bb, rr, tt = way.bbox
            l = min(l,ll)
            b = min(b,bb)
            r = max(r,rr)
            t = max(t,tt)
            
        return (l,b,r,t)
        

########NEW FILE########
__FILENAME__ = osmdb
import sqlite3
import os
try:
    import json
except ImportError:
    import simplejson as json
import sys
import xml.sax
import binascii
from graphserver.vincenty import vincenty
from struct import pack, unpack
from rtree import Rtree

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def pack_coords(coords):
    return binascii.b2a_base64( "".join([pack( "ff", *coord ) for coord in coords]) )
        
def unpack_coords(str):
    bin = binascii.a2b_base64( str )
    return [unpack( "ff", bin[i:i+8] ) for i in range(0, len(bin), 8)]

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}

    def __repr__(self):
        return "<Node id='%s' (%s, %s) n_tags=%d>"%(self.id, self.lon, self.lat, len(self.tags))
        
class Way:
    def __init__(self, id):
        self.id = id
        self.nd_ids = []
        self.tags = {}
        
    def __repr__(self):
        return "<Way id='%s' n_nds=%d n_tags=%d>"%(self.id, len(self.nd_ids), len(self.tags))

class WayRecord:
    def __init__(self, id, tags, nds):
        self.id = id
        
        if type(tags)==unicode:
            self.tags_str = tags
            self.tags_cache = None
        else:
            self.tags_cache = tags
            self.tags_str = None
            
        if type(nds)==unicode:
            self.nds_str = nds
            self.nds_cache = None
        else:
            self.nds_cache = nds
            self.nds_str = None
        
    @property
    def tags(self):
        self.tags_cache = self.tags_cache or json.loads(self.tags_str)
        return self.tags_cache
        
    @property
    def nds(self):
        self.nds_cache = self.nds_cache or json.loads(self.nds_str)
        return self.nds_cache
        
    def __repr__(self):
        return "<WayRecord id='%s'>"%self.id

class OSMDB:
    def __init__(self, dbname,overwrite=False,rtree_index=True):
        self.dbname = dbname
        
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if rtree_index:
            self.index = Rtree( dbname )
        else:
            self.index = None
        
        if overwrite:
            self.setup()
            
    def get_cursor(self):
        # Attempts to get a cursor using the current connection to the db. If we've found ourselves in a different thread
        # than that which the connection was made in, re-make the connection.
        
        try:
            ret = self.conn.cursor()
        except sqlite3.ProgrammingError:
            self.conn = sqlite3.connect(self.dbname)
            ret = self.conn.cursor()
            
        return ret
        
    def setup(self):
        c = self.get_cursor()
        c.execute( "CREATE TABLE nodes (id TEXT UNIQUE, tags TEXT, lat FLOAT, lon FLOAT, endnode_refs INTEGER DEFAULT 1)" )
        c.execute( "CREATE TABLE ways (id TEXT UNIQUE, tags TEXT, nds TEXT)" )
        self.conn.commit()
        c.close()
        
    def create_indexes(self):
        c = self.get_cursor()
        c.execute( "CREATE INDEX nodes_id ON nodes (id)" )
        c.execute( "CREATE INDEX nodes_lon ON nodes (lon)" )
        c.execute( "CREATE INDEX nodes_lat ON nodes (lat)" )
        c.execute( "CREATE INDEX ways_id ON ways (id)" )
        self.conn.commit()
        c.close()
        
    def populate(self, osm_filename, dryrun=False, accept=lambda tags: True, reporter=None, create_indexes=True):
        print "importing %s osm from XML to sqlite database" % osm_filename
        
        c = self.get_cursor()
        
        self.n_nodes = 0
        self.n_ways = 0
        
        superself = self

        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass

            @classmethod
            def startDocument(self):
                pass

            @classmethod
            def endDocument(self):
                pass

            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'])
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nd_ids.append( attrs['ref'] )

            @classmethod
            def endElement(self,name):
                if name=='node':
                    if superself.n_nodes%5000==0:
                        print "node %d"%superself.n_nodes
                    superself.n_nodes += 1
                    if not dryrun: superself.add_node( self.currElem, c )
                elif name=='way':
                    if superself.n_ways%5000==0:
                        print "way %d"%superself.n_ways
                    superself.n_ways += 1
                    if not dryrun and accept(self.currElem.tags): superself.add_way( self.currElem, c )

            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(osm_filename, OSMHandler)
        
        self.conn.commit()
        c.close()
        
        if not dryrun and create_indexes:
            print "indexing primary tables...",
            self.create_indexes()
        
        print "done"
        
    def set_endnode_ref_counts( self ):
        """Populate ways.endnode_refs. Necessary for splitting ways into single-edge sub-ways"""
        
        print "counting end-node references to find way split-points"
        
        c = self.get_cursor()
        
        endnode_ref_counts = {}
        
        c.execute( "SELECT nds from ways" )
        
        print "...counting"
        for i, (nds_str,) in enumerate(c):
            if i%5000==0:
                print i
                
            nds = json.loads( nds_str )
            for nd in nds:
                endnode_ref_counts[ nd ] = endnode_ref_counts.get( nd, 0 )+1
        
        print "...updating nodes table"
        for i, (node_id, ref_count) in enumerate(endnode_ref_counts.items()):
            if i%5000==0:
                print i
            
            if ref_count > 1:
                c.execute( "UPDATE nodes SET endnode_refs = ? WHERE id=?", (ref_count, node_id) )
            
        self.conn.commit()
        c.close()
    
    def index_endnodes( self ):
        print "indexing endpoint nodes into rtree"
        
        c = self.get_cursor()
        
        #TODO index endnodes if they're at the end of oneways - which only have one way ref, but are still endnodes
        c.execute( "SELECT id, lat, lon FROM nodes WHERE endnode_refs > 1" )
        
        for id, lat, lon in c:
            self.index.add( int(id), (lon, lat, lon, lat) )
            
        c.close()
    
    def create_and_populate_edges_table( self, tolerant=False ):
        self.set_endnode_ref_counts()
        self.index_endnodes()
        
        print "splitting ways and inserting into edge table"
        
        c = self.get_cursor()
        
        c.execute( "CREATE TABLE edges (id TEXT, parent_id TEXT, start_nd TEXT, end_nd TEXT, dist FLOAT, geom TEXT)" )
        
        for i, way in enumerate(self.ways()):
            try:
                if i%5000==0:
                    print i
                
                subways = []
                curr_subway = [ way.nds[0] ] # add first node to the current subway
                for nd in way.nds[1:-1]:     # for every internal node of the way
                    curr_subway.append( nd )
                    if self.node(nd)[4] > 1: # node reference count is greater than one, node is shared by two ways
                        subways.append( curr_subway )
                        curr_subway = [ nd ]
                curr_subway.append( way.nds[-1] ) # add the last node to the current subway, and store the subway
                subways.append( curr_subway );
                
                #insert into edge table
                for i, subway in enumerate(subways):
                    coords = [(lambda x:(x[3],x[2]))(self.node(nd)) for nd in subway]
                    packt = pack_coords( coords )
                    dist = sum([vincenty(lat1, lng1, lat2, lng2) for (lng1, lat1), (lng2, lat2) in cons(coords)])
                    c.execute( "INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)", ("%s-%s"%(way.id, i),
                                                                               way.id,
                                                                               subway[0],
                                                                               subway[-1],
                                                                               dist,
                                                                               packt) )
            except IndexError:
                if tolerant:
                    continue
                else:
                    raise
        
        print "indexing edges...",
        c.execute( "CREATE INDEX edges_id ON edges (id)" )
        c.execute( "CREATE INDEX edges_parent_id ON edges (parent_id)" )
        print "done"
        
        self.conn.commit()
        c.close()
        
    def edge(self, id):
        c = self.get_cursor()
        
        c.execute( "SELECT edges.*, ways.tags FROM edges, ways WHERE ways.id = edges.parent_id AND edges.id = ?", (id,) )
        
        try:
            ret = c.next()
            way_id, parent_id, from_nd, to_nd, dist, geom, tags = ret
            return (way_id, parent_id, from_nd, to_nd, dist, unpack_coords( geom ), json.loads(tags))
        except StopIteration:
            c.close()
            raise IndexError( "Database does not have an edge with id '%s'"%id )
            
        c.close()
        return ret
        
    def edges(self):
        c = self.get_cursor()
        
        c.execute( "SELECT edges.*, ways.tags FROM edges, ways WHERE ways.id = edges.parent_id" )
        
        for way_id, parent_id, from_nd, to_nd, dist, geom, tags in c:
            yield (way_id, parent_id, from_nd, to_nd, dist, unpack_coords(geom), json.loads(tags))
            
        c.close()
        
        
    def add_way( self, way, curs=None ):
        if curs is None:
            curs = self.get_cursor()
            close_cursor = True
        else:
            close_cursor = False
            
        curs.execute("INSERT OR IGNORE INTO ways (id, tags, nds) VALUES (?, ?, ?)", (way.id, json.dumps(way.tags), json.dumps(way.nd_ids) ))
        
        if close_cursor:
            self.conn.commit()
            curs.close()
            
    def add_node( self, node, curs=None ):
        if curs is None:
            curs = self.get_cursor()
            close_cursor = True
        else:
            close_cursor = False
            
        curs.execute("INSERT OR IGNORE INTO nodes (id, tags, lat, lon) VALUES (?, ?, ?, ?)", ( node.id, json.dumps(node.tags), node.lat, node.lon ) )
        
        if close_cursor:
            self.conn.commit()
            curs.close()
        
    def nodes(self):
        c = self.get_cursor()
        
        c.execute( "SELECT * FROM nodes" )
        
        for node_row in c:
            yield node_row
            
        c.close()
        
    def node(self, id):
        c = self.get_cursor()
        
        c.execute( "SELECT * FROM nodes WHERE id = ?", (id,) )
        
        try:
            ret = c.next()
        except StopIteration:
            c.close()
            raise IndexError( "Database does not have node with id '%s'"%id )
            
        c.close()
        return ret
    
    def nearest_node(self, lat, lon, range=0.005):
        c = self.get_cursor()
        
        if self.index:
            #print "YOUR'RE USING THE INDEX"
            id = list(self.index.nearest( (lon, lat), 1 ))[0]
            #print "THE ID IS %d"%id
            c.execute( "SELECT id, lat, lon FROM nodes WHERE id = ?", (id,) )
        else:
            c.execute( "SELECT id, lat, lon FROM nodes WHERE endnode_refs > 1 AND lat > ? AND lat < ? AND lon > ? AND lon < ?", (lat-range, lat+range, lon-range, lon+range) )
        
        dists = [(nid, nlat, nlon, ((nlat-lat)**2+(nlon-lon)**2)**0.5) for nid, nlat, nlon in c]
            
        if len(dists)==0:
            return (None, None, None, None)
            
        return min( dists, key = lambda x:x[3] )

    def nearest_of( self, lat, lon, nodes ):
        c = self.get_cursor()
        
        c.execute( "SELECT id, lat, lon FROM nodes WHERE id IN (%s)"%",".join([str(x) for x in nodes]) )
        
        dists = [(nid, nlat, nlon, ((nlat-lat)**2+(nlon-lon)**2)**0.5) for nid, nlat, nlon in c]
            
        if len(dists)==0:
            return (None, None, None, None)
            
        return min( dists, key = lambda x:x[3] )
        
    def way(self, id):
        c = self.get_cursor()
        
        c.execute( "SELECT id, tags, nds FROM ways WHERE id = ?", (id,) )
       
        try: 
          id, tags_str, nds_str = c.next()
          ret = WayRecord(id, tags_str, nds_str)
        except StopIteration:
          raise Exception( "OSMDB has no way with id '%s'"%id )
        finally:
          c.close()
        
        return ret
        
    def way_nds(self, id):
        c = self.get_cursor()
        c.execute( "SELECT nds FROM ways WHERE id = ?", (id,) )
        
        (nds_str,) = c.next()
        c.close()
        
        return json.loads( nds_str )
        
    def ways(self):
        c = self.get_cursor()
        
        c.execute( "SELECT id, tags, nds FROM ways" )
        
        for id, tags_str, nds_str in c:
            yield WayRecord( id, tags_str, nds_str )
            
        c.close()
        
    def count_ways(self):
        c = self.get_cursor()
        
        c.execute( "SELECT count(*) FROM ways" )
        ret = c.next()[0]
        
        c.close()
        
        return ret
        
    def count_edges(self):
        c = self.get_cursor()
        
        c.execute( "SELECT count(*) FROM edges" )
        ret = c.next()[0]
        
        c.close()
        
        return ret
        
    def delete_way(self, id):
        c = self.get_cursor()
        
        c.execute("DELETE FROM ways WHERE id = ?", (id,))
        
        c.close()
        
    def bounds(self):
        c = self.get_cursor()
        c.execute( "SELECT min(lon), min(lat), max(lon), max(lat) FROM nodes" )
        
        ret = c.next()
        c.close()
        return ret
    
    def execute(self,sql,args=None):
        c = self.get_cursor()
        if args:
            for row in c.execute(sql,args):
                yield row
        else:
            for row in c.execute(sql):
                yield row
        c.close()
    
    def cursor(self):
        return self.get_cursor()    

def test_wayrecord():
    wr = WayRecord( "1", {'highway':'bumpkis'}, ['1','2','3'] )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']
    
    wr = WayRecord( "1", "{\"highway\":\"bumpkis\"}", "[\"1\",\"2\",\"3\"]" )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']

def osm_to_osmdb(osm_filenames, osmdb_filename, tolerant=False, skipload=False):
    osmdb = OSMDB( osmdb_filename, overwrite=True )

    if isinstance(osm_filenames, basestring):
        osm_filenames = [osm_filenames]

    for osm_filename in osm_filenames:
        if not skipload:
            osmdb.populate( osm_filename, accept=lambda tags: 'highway' in tags, reporter=sys.stdout, create_indexes=False )

    if not skipload:
        print "indexing primary tables...",
        osmdb.create_indexes()
        
    osmdb.create_and_populate_edges_table(tolerant)
    if osmdb.count_edges() == 0:
        print "WARNING: osmdb has no edges!"

from optparse import OptionParser
def main():
    from sys import argv
    
    parser = OptionParser(usage="%prog [options] osm_filename [osm_filename ...] osmdb_filename")
    parser.add_option( "-t", "--tolerant", dest="tolerant",
                       action="store_true" )
    parser.add_option( "-d", "--dryrun", dest="dryrun", help="Just read the OSM file; don't copy anything to a database", action="store_true" )
    
    (options, args) = parser.parse_args()
    
    if len(args) < 2:
        parser.error("incorrect number of arguments")
    osmdb_filename = args.pop()

    osm_to_osmdb(args, osmdb_filename, options.tolerant, options.dryrun)

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = osmfilters
from graphserver.core import Graph, Link, Street, State
from osmdb import OSMDB
import time
from graphserver.vincenty import vincenty as dist_earth
try:
  import json
except ImportError:
  import simplejson as json

class OSMDBFilter(object):
    def setup(self, db, *args):
        pass
    
    def filter(self, db, *args):
        pass
    
    def teardown(self, db):
        pass
    
    def run(self,db, *args):
        self.setup(db, *args)
        self.filter(db, *args)

    def rerun(self,db, *args):
        self.teardown(db)
        self.run(db)
        
    def visualize(self, db, *args):
        pass

class CalculateWayLengthFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        try:
            c.execute("ALTER TABLE ways ADD column length FLOAT")
            db.conn.commit()
        except: pass
        c.close()

    def filter(self, db):
        way_length = {}
        print "Calculating length."
        for way in db.ways():
            g = way.geom
            l = 0
            for i in range(0, len(g)-1):
                l += dist_earth(g[i][1], g[i][0], g[i+1][1], g[i+1][0])
            way_length[way.id] = l

        print "Updating %s ways" % len(way_length)
        c = db.cursor()
        for w,l in way_length.items():
            c.execute("UPDATE ways set length = ? where id = ?", (l,w))
        db.conn.commit()
        c.close()
        print "Done"

class AddFromToColumnsFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        try:
            c.execute("ALTER TABLE ways ADD column from_v TEXT")
            c.execute("ALTER TABLE ways ADD column to_v TEXT")
            db.conn.commit()
        except: pass
        c.close()

    def filter(self, db):
        add_list = []
        for way in db.ways():
            add_list.append((way.nds[0], way.nds[-1], way.id))

        print "Updating %s ways" % len(add_list)
        c = db.cursor()
        for a in add_list:
            c.execute("UPDATE ways set from_v = ?, to_v = ? where id = ?", a)
        db.conn.commit()
        c.close()
        print "Done"

class DeleteHighwayTypesFilter(OSMDBFilter):
    def run(self, db, *types):
        print "Types",types
        purge_list = []
        for way in db.ways():
            if 'highway' in way.tags and way.tags['highway'] in types:
                purge_list.append(way.id)
        
        c = db.cursor()
        for i in range(0,len(purge_list),100):
            query = "DELETE from ways WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted all %s highway types (%s ways)" % (", ".join(types), len(purge_list))
        DeleteOrphanNodesFilter().run(db,None)
        
class DeleteOrphanNodesFilter(OSMDBFilter):
    def run(self, db, *args):
        node_ids = {}
        for nid in db.execute("SELECT id from nodes"):
            node_ids[nid[0]] = 0
        
        for way in db.ways():
            node_ids[way.nds[0]] += 1
            node_ids[way.nds[-1]] += 1
        
        purge_list = []
        for n,c in node_ids.items():
            if c == 0:
                purge_list.append(n)
        c = db.cursor()
        for i in range(0,len(purge_list),100):
            query = "DELETE from nodes WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted %s nodes of %d" % (len(purge_list), len(node_ids))
        

class PurgeDisjunctGraphsFilter(OSMDBFilter):
    def filter(self, db, threshold=None):
        f = FindDisjunctGraphsFilter()
        try:
            f.teardown(db)
        except: pass
        
        f.run(db,*[])
        
        node_ids = {}

        if not threshold:
            largest = next(db.execute("SELECT graph_num, count(*) as cnt FROM graph_nodes GROUP BY graph_num ORDER BY cnt desc"))[0]
                    
            for x in db.execute("SELECT node_id FROM graph_nodes where graph_num != ?", (largest,)):
                node_ids[x[0]] = 1
        else: 
            for x in db.execute("""SELECT node_id FROM graph_nodes where graph_num in
                                (SELECT a.graph_num FROM 
                                  (SELECT graph_num, count(*) as cnt FROM graph_nodes GROUP BY graph_num HAVING cnt < %s) as a)""" % threshold):
                node_ids[x[0]] = 1

        c = db.cursor()

        purge_list = []
        for way in db.ways():
            if way.nds[0] in node_ids or way.nds[-1] in node_ids:
                purge_list.append(way.id)

        for i in range(0,len(purge_list),100):
            query = "DELETE from ways WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted %s ways" % (len(purge_list))
        DeleteOrphanNodesFilter().run(db,*[])
                
        f.teardown(db)
        
class StripOtherTagsFilter(OSMDBFilter):
    def filter(self, db, feature_type, *keep_tags):
        keep_tags = dict([(t,1) for t in keep_tags])

        update_list = {}
        if feature_type == 'nodes':
            query = "SELECT id,tags FROM nodes"
        else:
            query = "SELECT id,tags FROM ways"
            
        c = db.cursor()
        c.execute(query)
        for id, tags in c:
            tags = json.loads(tags)
            for k in tags.keys():
                if k not in keep_tags:
                    del tags[k]
            
            update_list[id] = json.dumps(tags)
        
        for id, tags in update_list.items():
            c.execute("UPDATE ways set tags = ? WHERE id = ?",(id,tags))

        db.conn.commit()
        c.close()

class FindDisjunctGraphsFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        c.execute("CREATE table graph_nodes (graph_num INTEGER, node_id TEXT)")
        c.execute("CREATE index graph_nodes_node_indx ON graph_nodes(node_id)")
        c.close()

    def teardown(self, db):
        c = db.cursor()
        c.execute("DROP table graph_nodes")
        c.close()
        
    def filter(self, osmdb, *args):
        g = Graph()
        t0 = time.time()
        
        vertices = {}
        print "load vertices into memory"
        for row in osmdb.execute("SELECT id from nodes"):
            g.add_vertex(str(row[0]))
            vertices[str(row[0])] = 0

        print "load ways into memory"
        for way in osmdb.ways():
            g.add_edge(way.nds[0], way.nds[-1], Link())
            g.add_edge(way.nds[-1], way.nds[0], Link())

        t1 = time.time()
        print "populating graph took: %f"%(t1-t0)
        t0 = t1
        
        iteration = 1
        c = osmdb.cursor()
        while True:
            #c.execute("SELECT id from nodes where id not in (SELECT node_id from graph_nodes) LIMIT 1")
            try:
                vertex, dummy = vertices.popitem()
            except:
                break
            spt = g.shortest_path_tree(vertex, None, State(1,0))
            for v in spt.vertices:
                vertices.pop(v.label, None)
                c.execute("INSERT into graph_nodes VALUES (?, ?)", (iteration, v.label))
            spt.destroy()
            
            t1 = time.time()
            print "pass %s took: %f"%(iteration, t1-t0)
            t0 = t1
            iteration += 1
        c.close()
        
        osmdb.conn.commit()
        g.destroy()
        # audit
        for gnum, count in osmdb.execute("SELECT graph_num, count(*) FROM graph_nodes GROUP BY graph_num"):
            print "FOUND: %s=%s" % (gnum, count)
        
    def visualize(self, db, out_filename, renderer="/usr/local/bin/prender/renderer"):
        
        from prender import processing
        c = db.conn.cursor()
        
        group_color = {}
        group_weight = {}
        group_count = {}
        colors = [(255,128,255), (255,0,255), (255,255,128), (0,255,0), (255,0,0)]
        cnum = 0
        for num, count in db.execute("SELECT graph_num, count(*) FROM graph_nodes GROUP BY graph_num"):
            group_count[num] = count
            group_color[num] = colors[cnum]
            if count < 50:
                 group_weight[num] = 2
            elif count < 100:
                 group_weight[num] = 1.5
            else:
                 group_weight[num] = 1
                 
            cnum = (cnum + 1) % len(colors)
        
        largest_group = max(group_count, key=lambda x: group_count[x])
        group_color[largest_group] = (0,0,0)
        group_weight[largest_group] = 0.5
        
        node_group = {}
        for gn, ni in db.execute("SELECT graph_num, node_id FROM graph_nodes"):
            node_group[ni] = gn
        
        # setup the drawing
        l,b,r,t = db.bounds()
        mr = processing.MapRenderer(renderer)
        WIDTH = 3000
        mr.start(l,b,r,t,WIDTH) #left,bottom,right,top,width
        mr.background(255,255,255)
        mr.smooth()
        width = float(r-l)/WIDTH
    
        for i, w in enumerate(db.ways()):
            if i%1000==0: print "way %d"%i
            
            g = w.geom
            group = node_group[w.nds[0]]
            color = group_color[group]
            mr.strokeWeight( group_weight[group] * width )
            mr.stroke(*color)                            
            mr.line(g[0][0],g[0][1],g[-1][0],g[-1][1])

        mr.strokeWeight(width*10)
        mr.stroke(255,0,0)
        for ct, lat, lon in db.execute("SELECT count(*) as cnt, lat, lon from nodes GROUP BY lat, lon HAVING cnt > 1"):
            if ct>1:
                mr.point( lon, lat )

        mr.saveLocal(out_filename)
        mr.stop()
        print "Done"
        
class StitchDisjunctGraphs(OSMDBFilter):
    
    def filter(self, osmdb, *args):
        alias = {}
        
        # for each location that appears more than once
        for nds, ct, lat, lon in osmdb.execute("SELECT group_concat(id), count(*) as cnt, lat, lon from nodes GROUP BY lat, lon HAVING cnt > 1"):
            
            # get all the nodes that appear at that location
            #ids = map(lambda x:x[0], osmdb.execute("SELECT id FROM nodes WHERE lat=? AND lon=?", (lat,lon)))
            #print nds
            nds = nds.split(",")
            first = nds.pop(0)
            alias[nds] = nds
            # alias the duplicate node to an identical node
            #for id in ids:
            # if id != ids[0]:
            # alias[id] = ids[0]
                    
        # delete all duplicate nodes
        dupes = alias.keys()
        print "%d dupe nodes"%len(dupes)
        print "Deleting dupe nodes"
        query = "DELETE FROM nodes WHERE id IN (%s)"%(",".join(dupes),)
        c = osmdb.cursor()
        c.execute(query)
        osmdb.conn.commit()
        c.close()
        
        print "Replacing references to dupe nodes"
        c = osmdb.cursor()
        # replace reference in nd lists
        for i, (id, nds_str) in enumerate( osmdb.execute("SELECT id, nds FROM ways") ):
            if i%1000==0: print "way %d"%i
            
            nds = json.loads(nds_str)
            if nds[0] in alias:
                nds[0] = alias[nds[0]]
                print "replace header"
            if nds[-1] in alias:
                nds[-1] = alias[nds[-1]]
                print "replace footer"
            
            
            c.execute( "UPDATE ways SET nds=? WHERE id=?", (json.dumps(nds), id) )
        osmdb.conn.commit()
        c.close()

def stitch_and_visualize(dbname,mapname):
    osmdb = OSMDB( dbname )
    ff = StitchDisjunctGraphs()
    ff.filter( osmdb )
    
    ff = FindDisjunctGraphsFilter()
    ff.run( osmdb )
    ff.visualize( osmdb, mapname )

def main():
    from sys import argv
    if len(argv) < 4:
        print "%s <Filter Name> <run|rerun|visualize> <osmdb_file> [<filter args> ...]" % argv[0]
        print "Filters:"
        for k,v in globals().items():
            if type(v) == type and issubclass(v,OSMDBFilter):
                print " -- %s" % k
        exit()
    
    filter_cls, mode, osmdb_file = argv[1:4]
    
    try:
        f = globals()[filter_cls]()
    except KeyError, e:
        raise Exception("Filter not found.")
    
    db = OSMDB(osmdb_file)
 
    if len(argv) > 4:
        extra = argv[4:]
    else:
        extra = []
    
    if mode == 'run':
        f.run(db, *extra)
    elif mode == 'rerun':
        f.rerun(db, *extra)
    elif mode == 'visualize':
        f.visualize(db, *extra)
    else:
        raise Exception("Unknown mode.")
    
if __name__ == '__main__':
    main()
 

########NEW FILE########
__FILENAME__ = profiledb
#A little encapsulated databse for storing elevation profiles of OSM ways

import os
import sqlite3
try:
    import json
except ImportError:
    import simplejson as json
import binascii
from struct import pack, unpack
    
def pack_coords(coords):
    return binascii.b2a_base64( "".join([pack( "ff", *coord ) for coord in coords]) )
        
def unpack_coords(str):
    bin = binascii.a2b_base64( str )
    return [unpack( "ff", bin[i:i+8] ) for i in range(0, len(bin), 8)]

class ProfileDB:
    def __init__(self, dbname,overwrite=False):
        self.dbname = dbname
        
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if overwrite:
            self.setup()
            
    def get_cursor(self):
        # Attempts to get a cursor using the current connection to the db. If we've found ourselves in a different thread
        # than that which the connection was made in, re-make the connection.
        
        try:
            ret = self.conn.cursor()
        except sqlite3.ProgrammingError:
            self.conn = sqlite3.connect(self.dbname)
            ret = self.conn.cursor()
            
        return ret
            
    def setup(self):
        c = self.get_cursor()
        c.execute( "CREATE TABLE profiles (id TEXT, profile TEXT)" )
        c.execute( "CREATE INDEX profile_id ON profiles (id)" )
        self.conn.commit()
        c.close()
        
    def store(self, id, profile):
        c = self.get_cursor()
        
        c.execute( "INSERT INTO profiles VALUES (?, ?)", (id, pack_coords( profile )) )
        
        c.close()
        
    def get(self, id):
        c = self.get_cursor()
        c.execute( "SELECT profile FROM profiles WHERE id = ?", (id,) )
        
        try:
            (profile,) = c.next()
        except StopIteration:
            return None
        finally:
            c.close()
        
        return unpack_coords( profile )
        
    def execute(self,sql,args=None):
        c = self.get_cursor()
        if args:
            for row in c.execute(sql,args):
                yield row
        else:
            for row in c.execute(sql):
                yield row
        c.close()

from sys import argv
def main():
    if len(argv) > 1:
        pdb = ProfileDB( argv[1] )
        
        if len(argv) > 2:
            print pdb.get( argv[2] )
        else:
            for (id,) in list( pdb.execute( "SELECT id from profiles" ) ):
                print id
    else:
        print "python profiledb.py profiledb_filename [profile_id]"

if __name__ == '__main__':
    main()
        
            

########NEW FILE########
__FILENAME__ = simplify_osm
from osm import OSM, Node, Way

osm = OSM( "map.osm" )

fp = open("nodes.csv", "w")
for nodeid in osm.nodes.keys():
    fp.write( "%s\n"%nodeid )
fp.close()

fp = open("map.csv", "w")

for wayid, way in osm.ways.iteritems():
    if 'highway' in way.tags:
        fp.write("%s,%s,%s,%f\n"%(wayid, way.fromv, way.tov, way.length(osm.nodes)))
        
fp.close()
########NEW FILE########
__FILENAME__ = visitors

from osmdb import OSMDB
try:
    import json
except ImportError:
    import simplejson as json


class Visitor(object):
    """ Basic interface for an OSM visitor."""
    def visit(self, db, *args):
        pass
    
class UniqueTagNames(object):
    def visit(self, db, feature_type):
        tag_names = {}
        if feature_type == 'nodes':
            query = "SELECT tags FROM nodes"
        else:
            query = "SELECT tags FROM ways"

        for row in db.execute(query):
            t = json.loads(row[0])
            for k in t.keys():
                if k not in tag_names:
                    tag_names[k] = 1
                    
        for k in tag_names.keys():
            print "KEY: %s" % k

class UniqueTagValues(object):
    def visit(self, db, feature_type, tag_name):
        tag_values = {}
        if feature_type == 'nodes':
            query = "SELECT tags FROM nodes"
        else:
            query = "SELECT tags FROM ways"

        for row in db.execute(query):
            t = json.loads(row[0])
            if tag_name in t:
                tag_values[t[tag_name]] = 1
                    
        for k in tag_values.keys():
            print "TAG VALUE: %s" % k            
        
def main():
    from sys import argv
    visitor_cls, osmdb_file = argv[1:3]
    try:
        visitor = globals()[visitor_cls]()
    except KeyError, e:
        raise Exception("Visitor not found.")
    
    db = OSMDB(osmdb_file)

    if len(argv) > 3:
        extra = argv[3:]
    else:
        extra = []
    #print extra
    visitor.visit(db, *extra)
    
if __name__ == '__main__':
    main()
            

########NEW FILE########
__FILENAME__ = events
from graphserver.util import TimeHelpers
import graphserver.core
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
try:
    import json
except ImportError:
    import simplejson as json

class NarrativeEvent:
    def __init__(self, what, where, when, geom):
        self.what = what
        self.where = where
        self.when = when
        self.geom = geom
        
    def to_jsonable(self):
        return  {'what':self.what,
                 'where':self.where,
                 'when':self.when,
                 'geom':self.geom}

class BoardEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
    
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.TripBoard)
    
    def __call__(self, vertex1, edge, vertex2, context):
        
        event_time = vertex2.state.time
        trip_id = vertex2.state.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = "-".join([str(x) for x in list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0]])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class DescribeCrossingAtAlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        # if the stop_sequence is the same before and after the TripAlight was crossed, it means the algorithm crossed in the forward
        # direction - because the stop_sequence doesn't get set on a forward alight. If this is true then this is the appropriate time
        # to describe the transit trip that led to this alighting
        return edge is not None \
               and isinstance(edge.payload, graphserver.core.TripAlight) \
               and vertex1.state.stop_sequence == vertex2.state.stop_sequence
        
    def __call__(self, vertex1, edge, vertex2, context):
        
        stop_sequence_of_boarding = vertex1.state.stop_sequence
        trip_id = vertex1.state.trip_id
        alighting_trip_id, alighting_time, alighting_stop_sequences = edge.payload.get_alighting_by_trip_id( trip_id )
        
        what = "Ride trip %s from stop_seq %s to stop_seq %s"%(trip_id, vertex1.state.stop_sequence, alighting_stop_sequences)
        where = None
        when = None
        geom = self.gtfsdb.shape_between( trip_id, vertex1.state.stop_sequence, alighting_stop_sequences )
        return NarrativeEvent(what, where, when, geom)

class AlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.TripAlight)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex1.state.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class HeadwayBoardEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayBoard)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex2.state.time
        trip_id = vertex2.state.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = "-".join(list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class HeadwayAlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayAlight)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex1.state.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class StreetEvent:
    def __init__(self, osmdb_filename, timezone_name="America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Street)
    
    def __call__(self, vertex1, edge, vertex2, context):
        # adds to the variable set up by the StreetStartEvent
        geometry_chunk = self.osmdb.edge( edge.payload.name )[5]
      
        if edge.payload.reverse_of_source:
	    context['streetgeom'].extend( reversed( geometry_chunk ) )
	else:
	    context['streetgeom'].extend( geometry_chunk )
            
        context['sumlength'] += edge.payload.length
        context['sumrise'] += edge.payload.rise
        context['sumfall'] += edge.payload.fall
        
        return None
        
class CrossingEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Crossing)
        
    def __call__(self, v1, e, v2, context):
        trip_id = v1.state.trip_id
        return (str(v1.state), str(e), str(v2.state))

from math import asin, acos, degrees

def mag(vec):
    return sum([a**2 for a in vec])**0.5
 
def vector_angle( p1, p2, p3, p4 ):
    a = ((p2[0]-p1[0]),(p2[1]-p1[1]))
    b = ((p4[0]-p3[0]),(p4[1]-p3[1]))
    
    a_cross_b = a[0]*b[1] - a[1]*b[0]
    a_dot_b = a[0]*b[0] + a[1]*b[1]
    
    sin_theta = a_cross_b/(mag(a)*mag(b))
    cos_theta = a_dot_b/(mag(a)*mag(b))
    
    # if the dot product is positive, the turn is forward, else, backwards
    if a_dot_b >= 0:
        return -degrees(asin(sin_theta))
    else:
        # if the cross product is negative, the turn is to the right, else, left
        if a_cross_b <= 0:
            return degrees(acos(cos_theta))
        else:
            return -degrees(acos(cos_theta))
            
def angle_from_north( p3, p4 ):
    p1 = [0,0]
    p2 = [0,1]
    
    return vector_angle( p1, p2, p3, p4 )
    
def description_from_north( p3, p4 ):
    afn = angle_from_north( p3, p4 )
    if afn > -22.5 and afn <= 22.5:
        return "north"
    if afn > 22.5 and afn <= 67.5:
        return "northeast"
    if afn > 67.5 and afn <= 112.5:
        return "east"
    if afn > 112.5 and afn <= 157.5:
        return "southeast"
    if afn > 157.5:
        return "south"
        
    if afn < -22.5 and afn >= -67.5:
        return "northwest"
    if afn < -67.5 and afn >= -112.5:
        return "west"
    if afn < -112.5 and afn >= -157.5:
        return "southwest"
    if afn < -157.5:
        return "south"
            
def test_vector_angle():
    assert vector_angle( (0,0), (0,1), (0,1), (0,2) ) == 0.0
    assert round(vector_angle( (0,0), (0,1), (0,1), (5,10) ),4) == 29.0546
    assert vector_angle( (0,0), (0,1), (0,1), (1,1)) == 90
    assert round(vector_angle( (0,0), (0,1), (0,1), (1,0.95) ),4) == 92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (0,0) ) == 180
    assert round(vector_angle( (0,0), (0,1), (0,1), (-1, 0.95) ),4) == -92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (-1, 1) ) == -90
    assert round( vector_angle( (0,0), (0,1), (0,1), (-5,10) ), 4 ) == -29.0546
 
def turn_narrative( p1, p2, p3, p4 ):
    angle = vector_angle( p1, p2, p3, p4 )
    turn_mag = abs(angle)
    
    if turn_mag < 7:
        return "continue"
    elif turn_mag < 20:
        verb = "slight"
    elif turn_mag < 120:
        verb = ""
    else:
        verb = "sharp"
        
    if angle > 0:
        direction = "right"
    else:
        direction = "left"
        
    return ("%s %s"%(verb, direction)).strip()
        
class StreetStartEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge1 is None or not isinstance(edge1.payload, graphserver.core.Street)) and \
               (edge2 and isinstance(edge2.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):
        context['streetgeom'] = []
        context['sumlength'] = 0
        context['sumrise'] = 0
        context['sumfall'] = 0
        context['lastturntime'] = vertex.state.time
        
        osm_way2 = edge2.payload.name.split("-")[0]
        street_name2 = self.osmdb.way( osm_way2 ).tags.get('name', "unnamed")
        
        osm_id = vertex.label.split("-")[1]
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        osm_edge2 = self.osmdb.edge( edge2.payload.name )
        osm_edge2_startnode = osm_edge2[2]
        osm_edge2_geom = osm_edge2[5]
        if osm_id != osm_edge2_startnode:
            osm_edge2_geom.reverse()
        startseg = osm_edge2_geom[:2]
        direction = description_from_north( startseg[0], startseg[1] )
        
        what = "start walking"
        where = "on %s facing %s"%(street_name2, direction)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = [osm_node_lon, osm_node_lat]
        return NarrativeEvent(what,where,when,geom)
        
class StreetEndEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge2 is None or not isinstance(edge2.payload, graphserver.core.Street)) and \
               (edge1 and isinstance(edge1.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):
        osm_way1 = edge1.payload.name.split("-")[0]
        street_name1 = self.osmdb.way( osm_way1 ).tags.get('name', "unnamed")
        
        osm_id = vertex.label.split("-")[1]
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        average_speed = context['sumlength']/(vertex.state.time-context['lastturntime']) if vertex.state.time-context['lastturntime']>0 else 100000000
        what = "arrive walking after %dm, %0.1f rise, %0.1f fall (%0.1fm/s)"%(context['sumlength'], context['sumrise'], context['sumfall'], average_speed)
        where = "on %s"%(street_name1)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = [osm_node_lon, osm_node_lat]
        return NarrativeEvent(what,where,when,geom)
        
class GeomAtStreetEndEvent:
    def __init__(self, timezone_name = "America/Los_Angeles"):
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge2 is not a street and edge1 is
        return (edge2 is None or not isinstance(edge2.payload, graphserver.core.Street)) and \
               (edge1 and isinstance(edge1.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):        
        what = "walk a bunch"
        where = None
        when = None
        geom = context['streetgeom']
        return NarrativeEvent(what,where,when,geom)
        
class StreetTurnEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        return edge1 and edge2 and isinstance(edge1.payload, graphserver.core.Street) and isinstance(edge2.payload, graphserver.core.Street) \
               and edge1.payload.way != edge2.payload.way
    
    def __call__(self, edge1, vertex, edge2, context):
        
        osm_id = vertex.label.split("-")[1]
        
        # figure out which direction to turn
        osm_way_id1 = edge1.payload.name.split("-")[0]
        osm_way_id2 = edge2.payload.name.split("-")[0]
        
        osm_edge1 = self.osmdb.edge( edge1.payload.name )
        osm_edge2 = self.osmdb.edge( edge2.payload.name )
        
        osm_edge1_endnode = osm_edge1[3]
        osm_edge2_startnode = osm_edge2[2]
        
        osm_edge1_geom = osm_edge1[5]
        osm_edge2_geom = osm_edge2[5]
        
        if osm_id != osm_edge1_endnode:
            osm_edge1_geom.reverse()
             
        if osm_id != osm_edge2_startnode:
            osm_edge2_geom.reverse()
            
        endseg = osm_edge1_geom[-2:]
        startseg = osm_edge2_geom[:2]
        
        direction = turn_narrative( endseg[0], endseg[1], startseg[0], startseg[1] )
                
        street_name1 = self.osmdb.way( osm_way_id1 ).tags.get("name", "unnamed")
        street_name2 = self.osmdb.way( osm_way_id2 ).tags.get("name", "unnamed")
        
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        average_speed = context['sumlength']/(vertex.state.time-context['lastturntime']) if vertex.state.time-context['lastturntime']>0 else 100000000
        what = "%s onto %s after %dm, %0.1fm rise, %0.1fm fall (%0.1fm/s)"%(direction, street_name2, context['sumlength'], context['sumrise'], context['sumfall'], average_speed)
        where = "%s & %s"%(street_name1, street_name2)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = (osm_node_lon, osm_node_lat)
        
        context['sumlength'] = 0
        context['sumrise'] = 0
        context['sumfall'] = 0
        context['lastturntime'] = vertex.state.time
        return NarrativeEvent(what,where,when,geom)
    
class AllVertexEvent:
    def __init__(self):
        pass
        
    @staticmethod
    def applies_to(e1, v, e2):
        return True
        
    def __call__(self, e1, v, e2, context):
        return NarrativeEvent("vertex", str(e1), str(v), str(e2))
        
class AllEdgeEvent:
    def __init__(self):
        pass
        
    @staticmethod
    def applies_to(v1, e, v2):
        return True
        
    def __call__(self, v1, e, v2, context):
        return NarrativeEvent("edge", str(v1), str(e), str(v2))

########NEW FILE########
__FILENAME__ = fcgi
# Copyright (c) 2002, 2003, 2005, 2006 Allan Saddi <allan@saddi.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# $Id$

"""
fcgi - a FastCGI/WSGI gateway.

For more information about FastCGI, see <http://www.fastcgi.com/>.

For more information about the Web Server Gateway Interface, see
<http://www.python.org/peps/pep-0333.html>.

Example usage:

  #!/usr/bin/env python
  from myapplication import app # Assume app is your WSGI application object
  from fcgi import WSGIServer
  WSGIServer(app).run()

See the documentation for WSGIServer/Server for more information.

On most platforms, fcgi will fallback to regular CGI behavior if run in a
non-FastCGI context. If you want to force CGI behavior, set the environment
variable FCGI_FORCE_CGI to "Y" or "y".
"""

__author__ = 'Allan Saddi <allan@saddi.com>'
__version__ = '$Revision$'

import sys
import os
import signal
import struct
import cStringIO as StringIO
import select
import socket
import errno
import traceback

try:
    import thread
    import threading
    thread_available = True
except ImportError:
    import dummy_thread as thread
    import dummy_threading as threading
    thread_available = False

# Apparently 2.3 doesn't define SHUT_WR? Assume it is 1 in this case.
if not hasattr(socket, 'SHUT_WR'):
    socket.SHUT_WR = 1

__all__ = ['WSGIServer']

# Constants from the spec.
FCGI_LISTENSOCK_FILENO = 0

FCGI_HEADER_LEN = 8

FCGI_VERSION_1 = 1

FCGI_BEGIN_REQUEST = 1
FCGI_ABORT_REQUEST = 2
FCGI_END_REQUEST = 3
FCGI_PARAMS = 4
FCGI_STDIN = 5
FCGI_STDOUT = 6
FCGI_STDERR = 7
FCGI_DATA = 8
FCGI_GET_VALUES = 9
FCGI_GET_VALUES_RESULT = 10
FCGI_UNKNOWN_TYPE = 11
FCGI_MAXTYPE = FCGI_UNKNOWN_TYPE

FCGI_NULL_REQUEST_ID = 0

FCGI_KEEP_CONN = 1

FCGI_RESPONDER = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER = 3

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN = 1
FCGI_OVERLOADED = 2
FCGI_UNKNOWN_ROLE = 3

FCGI_MAX_CONNS = 'FCGI_MAX_CONNS'
FCGI_MAX_REQS = 'FCGI_MAX_REQS'
FCGI_MPXS_CONNS = 'FCGI_MPXS_CONNS'

FCGI_Header = '!BBHHBx'
FCGI_BeginRequestBody = '!HB5x'
FCGI_EndRequestBody = '!LB3x'
FCGI_UnknownTypeBody = '!B7x'

FCGI_EndRequestBody_LEN = struct.calcsize(FCGI_EndRequestBody)
FCGI_UnknownTypeBody_LEN = struct.calcsize(FCGI_UnknownTypeBody)

if __debug__:
    import time

    # Set non-zero to write debug output to a file.
    DEBUG = 0
    DEBUGLOG = '/tmp/fcgi.log'

    def _debug(level, msg):
        if DEBUG < level:
            return

        try:
            f = open(DEBUGLOG, 'a')
            f.write('%sfcgi: %s\n' % (time.ctime()[4:-4], msg))
            f.close()
        except:
            pass

class InputStream(object):
    """
    File-like object representing FastCGI input streams (FCGI_STDIN and
    FCGI_DATA). Supports the minimum methods required by WSGI spec.
    """
    def __init__(self, conn):
        self._conn = conn

        # See Server.
        self._shrinkThreshold = conn.server.inputStreamShrinkThreshold

        self._buf = ''
        self._bufList = []
        self._pos = 0 # Current read position.
        self._avail = 0 # Number of bytes currently available.

        self._eof = False # True when server has sent EOF notification.

    def _shrinkBuffer(self):
        """Gets rid of already read data (since we can't rewind)."""
        if self._pos >= self._shrinkThreshold:
            self._buf = self._buf[self._pos:]
            self._avail -= self._pos
            self._pos = 0

            assert self._avail >= 0

    def _waitForData(self):
        """Waits for more data to become available."""
        self._conn.process_input()

    def read(self, n=-1):
        if self._pos == self._avail and self._eof:
            return ''
        while True:
            if n < 0 or (self._avail - self._pos) < n:
                # Not enough data available.
                if self._eof:
                    # And there's no more coming.
                    newPos = self._avail
                    break
                else:
                    # Wait for more data.
                    self._waitForData()
                    continue
            else:
                newPos = self._pos + n
                break
        # Merge buffer list, if necessary.
        if self._bufList:
            self._buf += ''.join(self._bufList)
            self._bufList = []
        r = self._buf[self._pos:newPos]
        self._pos = newPos
        self._shrinkBuffer()
        return r

    def readline(self, length=None):
        if self._pos == self._avail and self._eof:
            return ''
        while True:
            # Unfortunately, we need to merge the buffer list early.
            if self._bufList:
                self._buf += ''.join(self._bufList)
                self._bufList = []
            # Find newline.
            i = self._buf.find('\n', self._pos)
            if i < 0:
                # Not found?
                if self._eof:
                    # No more data coming.
                    newPos = self._avail
                    break
                else:
                    # Wait for more to come.
                    self._waitForData()
                    continue
            else:
                newPos = i + 1
                break
        if length is not None:
            if self._pos + length < newPos:
                newPos = self._pos + length
        r = self._buf[self._pos:newPos]
        self._pos = newPos
        self._shrinkBuffer()
        return r

    def readlines(self, sizehint=0):
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines

    def __iter__(self):
        return self

    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration
        return r

    def add_data(self, data):
        if not data:
            self._eof = True
        else:
            self._bufList.append(data)
            self._avail += len(data)

class MultiplexedInputStream(InputStream):
    """
    A version of InputStream meant to be used with MultiplexedConnections.
    Assumes the MultiplexedConnection (the producer) and the Request
    (the consumer) are running in different threads.
    """
    def __init__(self, conn):
        super(MultiplexedInputStream, self).__init__(conn)

        # Arbitrates access to this InputStream (it's used simultaneously
        # by a Request and its owning Connection object).
        lock = threading.RLock()

        # Notifies Request thread that there is new data available.
        self._lock = threading.Condition(lock)

    def _waitForData(self):
        # Wait for notification from add_data().
        self._lock.wait()

    def read(self, n=-1):
        self._lock.acquire()
        try:
            return super(MultiplexedInputStream, self).read(n)
        finally:
            self._lock.release()

    def readline(self, length=None):
        self._lock.acquire()
        try:
            return super(MultiplexedInputStream, self).readline(length)
        finally:
            self._lock.release()

    def add_data(self, data):
        self._lock.acquire()
        try:
            super(MultiplexedInputStream, self).add_data(data)
            self._lock.notify()
        finally:
            self._lock.release()

class OutputStream(object):
    """
    FastCGI output stream (FCGI_STDOUT/FCGI_STDERR). By default, calls to
    write() or writelines() immediately result in Records being sent back
    to the server. Buffering should be done in a higher level!
    """
    def __init__(self, conn, req, type, buffered=False):
        self._conn = conn
        self._req = req
        self._type = type
        self._buffered = buffered
        self._bufList = [] # Used if buffered is True
        self.dataWritten = False
        self.closed = False

    def _write(self, data):
        length = len(data)
        while length:
            toWrite = min(length, self._req.server.maxwrite - FCGI_HEADER_LEN)

            rec = Record(self._type, self._req.requestId)
            rec.contentLength = toWrite
            rec.contentData = data[:toWrite]
            self._conn.writeRecord(rec)

            data = data[toWrite:]
            length -= toWrite

    def write(self, data):
        assert not self.closed

        if not data:
            return

        self.dataWritten = True

        if self._buffered:
            self._bufList.append(data)
        else:
            self._write(data)

    def writelines(self, lines):
        assert not self.closed

        for line in lines:
            self.write(line)

    def flush(self):
        # Only need to flush if this OutputStream is actually buffered.
        if self._buffered:
            data = ''.join(self._bufList)
            self._bufList = []
            self._write(data)

    # Though available, the following should NOT be called by WSGI apps.
    def close(self):
        """Sends end-of-stream notification, if necessary."""
        if not self.closed and self.dataWritten:
            self.flush()
            rec = Record(self._type, self._req.requestId)
            self._conn.writeRecord(rec)
            self.closed = True

class TeeOutputStream(object):
    """
    Simple wrapper around two or more output file-like objects that copies
    written data to all streams.
    """
    def __init__(self, streamList):
        self._streamList = streamList

    def write(self, data):
        for f in self._streamList:
            f.write(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        for f in self._streamList:
            f.flush()

class StdoutWrapper(object):
    """
    Wrapper for sys.stdout so we know if data has actually been written.
    """
    def __init__(self, stdout):
        self._file = stdout
        self.dataWritten = False

    def write(self, data):
        if data:
            self.dataWritten = True
        self._file.write(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def __getattr__(self, name):
        return getattr(self._file, name)

def decode_pair(s, pos=0):
    """
    Decodes a name/value pair.

    The number of bytes decoded as well as the name/value pair
    are returned.
    """
    nameLength = ord(s[pos])
    if nameLength & 128:
        nameLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    valueLength = ord(s[pos])
    if valueLength & 128:
        valueLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    name = s[pos:pos+nameLength]
    pos += nameLength
    value = s[pos:pos+valueLength]
    pos += valueLength

    return (pos, (name, value))

def encode_pair(name, value):
    """
    Encodes a name/value pair.

    The encoded string is returned.
    """
    nameLength = len(name)
    if nameLength < 128:
        s = chr(nameLength)
    else:
        s = struct.pack('!L', nameLength | 0x80000000L)

    valueLength = len(value)
    if valueLength < 128:
        s += chr(valueLength)
    else:
        s += struct.pack('!L', valueLength | 0x80000000L)

    return s + name + value
    
class Record(object):
    """
    A FastCGI Record.

    Used for encoding/decoding records.
    """
    def __init__(self, type=FCGI_UNKNOWN_TYPE, requestId=FCGI_NULL_REQUEST_ID):
        self.version = FCGI_VERSION_1
        self.type = type
        self.requestId = requestId
        self.contentLength = 0
        self.paddingLength = 0
        self.contentData = ''

    def _recvall(sock, length):
        """
        Attempts to receive length bytes from a socket, blocking if necessary.
        (Socket may be blocking or non-blocking.)
        """
        dataList = []
        recvLen = 0
        while length:
            try:
                data = sock.recv(length)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([sock], [], [])
                    continue
                else:
                    raise
            if not data: # EOF
                break
            dataList.append(data)
            dataLen = len(data)
            recvLen += dataLen
            length -= dataLen
        return ''.join(dataList), recvLen
    _recvall = staticmethod(_recvall)

    def read(self, sock):
        """Read and decode a Record from a socket."""
        try:
            header, length = self._recvall(sock, FCGI_HEADER_LEN)
        except:
            raise EOFError

        if length < FCGI_HEADER_LEN:
            raise EOFError
        
        self.version, self.type, self.requestId, self.contentLength, \
                      self.paddingLength = struct.unpack(FCGI_Header, header)

        if __debug__: _debug(9, 'read: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))
        
        if self.contentLength:
            try:
                self.contentData, length = self._recvall(sock,
                                                         self.contentLength)
            except:
                raise EOFError

            if length < self.contentLength:
                raise EOFError

        if self.paddingLength:
            try:
                self._recvall(sock, self.paddingLength)
            except:
                raise EOFError

    def _sendall(sock, data):
        """
        Writes data to a socket and does not return until all the data is sent.
        """
        length = len(data)
        while length:
            try:
                sent = sock.send(data)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([], [sock], [])
                    continue
                else:
                    raise
            data = data[sent:]
            length -= sent
    _sendall = staticmethod(_sendall)

    def write(self, sock):
        """Encode and write a Record to a socket."""
        self.paddingLength = -self.contentLength & 7

        if __debug__: _debug(9, 'write: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))

        header = struct.pack(FCGI_Header, self.version, self.type,
                             self.requestId, self.contentLength,
                             self.paddingLength)
        self._sendall(sock, header)
        if self.contentLength:
            self._sendall(sock, self.contentData)
        if self.paddingLength:
            self._sendall(sock, '\x00'*self.paddingLength)
            
class Request(object):
    """
    Represents a single FastCGI request.

    These objects are passed to your handler and is the main interface
    between your handler and the fcgi module. The methods should not
    be called by your handler. However, server, params, stdin, stdout,
    stderr, and data are free for your handler's use.
    """
    def __init__(self, conn, inputStreamClass):
        self._conn = conn

        self.server = conn.server
        self.params = {}
        self.stdin = inputStreamClass(conn)
        self.stdout = OutputStream(conn, self, FCGI_STDOUT)
        self.stderr = OutputStream(conn, self, FCGI_STDERR, buffered=True)
        self.data = inputStreamClass(conn)

    def run(self):
        """Runs the handler, flushes the streams, and ends the request."""
        try:
            protocolStatus, appStatus = self.server.handler(self)
        except:
            traceback.print_exc(file=self.stderr)
            self.stderr.flush()
            if not self.stdout.dataWritten:
                self.server.error(self)

            protocolStatus, appStatus = FCGI_REQUEST_COMPLETE, 0

        if __debug__: _debug(1, 'protocolStatus = %d, appStatus = %d' %
                             (protocolStatus, appStatus))

        self._flush()
        self._end(appStatus, protocolStatus)

    def _end(self, appStatus=0L, protocolStatus=FCGI_REQUEST_COMPLETE):
        self._conn.end_request(self, appStatus, protocolStatus)
        
    def _flush(self):
        self.stdout.close()
        self.stderr.close()

class CGIRequest(Request):
    """A normal CGI request disguised as a FastCGI request."""
    def __init__(self, server):
        # These are normally filled in by Connection.
        self.requestId = 1
        self.role = FCGI_RESPONDER
        self.flags = 0
        self.aborted = False
        
        self.server = server
        self.params = dict(os.environ)
        self.stdin = sys.stdin
        self.stdout = StdoutWrapper(sys.stdout) # Oh, the humanity!
        self.stderr = sys.stderr
        self.data = StringIO.StringIO()
        
    def _end(self, appStatus=0L, protocolStatus=FCGI_REQUEST_COMPLETE):
        sys.exit(appStatus)

    def _flush(self):
        # Not buffered, do nothing.
        pass

class Connection(object):
    """
    A Connection with the web server.

    Each Connection is associated with a single socket (which is
    connected to the web server) and is responsible for handling all
    the FastCGI message processing for that socket.
    """
    _multiplexed = False
    _inputStreamClass = InputStream

    def __init__(self, sock, addr, server):
        self._sock = sock
        self._addr = addr
        self.server = server

        # Active Requests for this Connection, mapped by request ID.
        self._requests = {}

    def _cleanupSocket(self):
        """Close the Connection's socket."""
        try:
            self._sock.shutdown(socket.SHUT_WR)
        except:
            return
        try:
            while True:
                r, w, e = select.select([self._sock], [], [])
                if not r or not self._sock.recv(1024):
                    break
        except:
            pass
        self._sock.close()
        
    def run(self):
        """Begin processing data from the socket."""
        self._keepGoing = True
        while self._keepGoing:
            try:
                self.process_input()
            except EOFError:
                break
            except (select.error, socket.error), e:
                if e[0] == errno.EBADF: # Socket was closed by Request.
                    break
                raise

        self._cleanupSocket()

    def process_input(self):
        """Attempt to read a single Record from the socket and process it."""
        # Currently, any children Request threads notify this Connection
        # that it is no longer needed by closing the Connection's socket.
        # We need to put a timeout on select, otherwise we might get
        # stuck in it indefinitely... (I don't like this solution.)
        while self._keepGoing:
            try:
                r, w, e = select.select([self._sock], [], [], 1.0)
            except ValueError:
                # Sigh. ValueError gets thrown sometimes when passing select
                # a closed socket.
                raise EOFError
            if r: break
        if not self._keepGoing:
            return
        rec = Record()
        rec.read(self._sock)

        if rec.type == FCGI_GET_VALUES:
            self._do_get_values(rec)
        elif rec.type == FCGI_BEGIN_REQUEST:
            self._do_begin_request(rec)
        elif rec.type == FCGI_ABORT_REQUEST:
            self._do_abort_request(rec)
        elif rec.type == FCGI_PARAMS:
            self._do_params(rec)
        elif rec.type == FCGI_STDIN:
            self._do_stdin(rec)
        elif rec.type == FCGI_DATA:
            self._do_data(rec)
        elif rec.requestId == FCGI_NULL_REQUEST_ID:
            self._do_unknown_type(rec)
        else:
            # Need to complain about this.
            pass

    def writeRecord(self, rec):
        """
        Write a Record to the socket.
        """
        rec.write(self._sock)

    def end_request(self, req, appStatus=0L,
                    protocolStatus=FCGI_REQUEST_COMPLETE, remove=True):
        """
        End a Request.

        Called by Request objects. An FCGI_END_REQUEST Record is
        sent to the web server. If the web server no longer requires
        the connection, the socket is closed, thereby ending this
        Connection (run() returns).
        """
        rec = Record(FCGI_END_REQUEST, req.requestId)
        rec.contentData = struct.pack(FCGI_EndRequestBody, appStatus,
                                      protocolStatus)
        rec.contentLength = FCGI_EndRequestBody_LEN
        self.writeRecord(rec)

        if remove:
            del self._requests[req.requestId]

        if __debug__: _debug(2, 'end_request: flags = %d' % req.flags)

        if not (req.flags & FCGI_KEEP_CONN) and not self._requests:
            self._cleanupSocket()
            self._keepGoing = False

    def _do_get_values(self, inrec):
        """Handle an FCGI_GET_VALUES request from the web server."""
        outrec = Record(FCGI_GET_VALUES_RESULT)

        pos = 0
        while pos < inrec.contentLength:
            pos, (name, value) = decode_pair(inrec.contentData, pos)
            cap = self.server.capability.get(name)
            if cap is not None:
                outrec.contentData += encode_pair(name, str(cap))

        outrec.contentLength = len(outrec.contentData)
        self.writeRecord(outrec)

    def _do_begin_request(self, inrec):
        """Handle an FCGI_BEGIN_REQUEST from the web server."""
        role, flags = struct.unpack(FCGI_BeginRequestBody, inrec.contentData)

        req = self.server.request_class(self, self._inputStreamClass)
        req.requestId, req.role, req.flags = inrec.requestId, role, flags
        req.aborted = False

        if not self._multiplexed and self._requests:
            # Can't multiplex requests.
            self.end_request(req, 0L, FCGI_CANT_MPX_CONN, remove=False)
        else:
            self._requests[inrec.requestId] = req

    def _do_abort_request(self, inrec):
        """
        Handle an FCGI_ABORT_REQUEST from the web server.

        We just mark a flag in the associated Request.
        """
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.aborted = True

    def _start_request(self, req):
        """Run the request."""
        # Not multiplexed, so run it inline.
        req.run()

    def _do_params(self, inrec):
        """
        Handle an FCGI_PARAMS Record.

        If the last FCGI_PARAMS Record is received, start the request.
        """
        req = self._requests.get(inrec.requestId)
        if req is not None:
            if inrec.contentLength:
                pos = 0
                while pos < inrec.contentLength:
                    pos, (name, value) = decode_pair(inrec.contentData, pos)
                    req.params[name] = value
            else:
                self._start_request(req)

    def _do_stdin(self, inrec):
        """Handle the FCGI_STDIN stream."""
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.stdin.add_data(inrec.contentData)

    def _do_data(self, inrec):
        """Handle the FCGI_DATA stream."""
        req = self._requests.get(inrec.requestId)
        if req is not None:
            req.data.add_data(inrec.contentData)

    def _do_unknown_type(self, inrec):
        """Handle an unknown request type. Respond accordingly."""
        outrec = Record(FCGI_UNKNOWN_TYPE)
        outrec.contentData = struct.pack(FCGI_UnknownTypeBody, inrec.type)
        outrec.contentLength = FCGI_UnknownTypeBody_LEN
        self.writeRecord(rec)
        
class MultiplexedConnection(Connection):
    """
    A version of Connection capable of handling multiple requests
    simultaneously.
    """
    _multiplexed = True
    _inputStreamClass = MultiplexedInputStream

    def __init__(self, sock, addr, server):
        super(MultiplexedConnection, self).__init__(sock, addr, server)

        # Used to arbitrate access to self._requests.
        lock = threading.RLock()

        # Notification is posted everytime a request completes, allowing us
        # to quit cleanly.
        self._lock = threading.Condition(lock)

    def _cleanupSocket(self):
        # Wait for any outstanding requests before closing the socket.
        self._lock.acquire()
        while self._requests:
            self._lock.wait()
        self._lock.release()

        super(MultiplexedConnection, self)._cleanupSocket()
        
    def writeRecord(self, rec):
        # Must use locking to prevent intermingling of Records from different
        # threads.
        self._lock.acquire()
        try:
            # Probably faster than calling super. ;)
            rec.write(self._sock)
        finally:
            self._lock.release()

    def end_request(self, req, appStatus=0L,
                    protocolStatus=FCGI_REQUEST_COMPLETE, remove=True):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self).end_request(req, appStatus,
                                                           protocolStatus,
                                                           remove)
            self._lock.notify()
        finally:
            self._lock.release()

    def _do_begin_request(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_begin_request(inrec)
        finally:
            self._lock.release()

    def _do_abort_request(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_abort_request(inrec)
        finally:
            self._lock.release()

    def _start_request(self, req):
        thread.start_new_thread(req.run, ())

    def _do_params(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_params(inrec)
        finally:
            self._lock.release()

    def _do_stdin(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_stdin(inrec)
        finally:
            self._lock.release()

    def _do_data(self, inrec):
        self._lock.acquire()
        try:
            super(MultiplexedConnection, self)._do_data(inrec)
        finally:
            self._lock.release()
        
class Server(object):
    """
    The FastCGI server.

    Waits for connections from the web server, processing each
    request.

    If run in a normal CGI context, it will instead instantiate a
    CGIRequest and run the handler through there.
    """
    request_class = Request
    cgirequest_class = CGIRequest

    # Limits the size of the InputStream's string buffer to this size + the
    # server's maximum Record size. Since the InputStream is not seekable,
    # we throw away already-read data once this certain amount has been read.
    inputStreamShrinkThreshold = 102400 - 8192

    def __init__(self, handler=None, maxwrite=8192, bindAddress=None,
                 umask=None, multiplexed=False):
        """
        handler, if present, must reference a function or method that
        takes one argument: a Request object. If handler is not
        specified at creation time, Server *must* be subclassed.
        (The handler method below is abstract.)

        maxwrite is the maximum number of bytes (per Record) to write
        to the server. I've noticed mod_fastcgi has a relatively small
        receive buffer (8K or so).

        bindAddress, if present, must either be a string or a 2-tuple. If
        present, run() will open its own listening socket. You would use
        this if you wanted to run your application as an 'external' FastCGI
        app. (i.e. the webserver would no longer be responsible for starting
        your app) If a string, it will be interpreted as a filename and a UNIX
        socket will be opened. If a tuple, the first element, a string,
        is the interface name/IP to bind to, and the second element (an int)
        is the port number.

        Set multiplexed to True if you want to handle multiple requests
        per connection. Some FastCGI backends (namely mod_fastcgi) don't
        multiplex requests at all, so by default this is off (which saves
        on thread creation/locking overhead). If threads aren't available,
        this keyword is ignored; it's not possible to multiplex requests
        at all.
        """
        if handler is not None:
            self.handler = handler
        self.maxwrite = maxwrite
        if thread_available:
            try:
                import resource
                # Attempt to glean the maximum number of connections
                # from the OS.
                maxConns = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            except ImportError:
                maxConns = 100 # Just some made up number.
            maxReqs = maxConns
            if multiplexed:
                self._connectionClass = MultiplexedConnection
                maxReqs *= 5 # Another made up number.
            else:
                self._connectionClass = Connection
            self.capability = {
                FCGI_MAX_CONNS: maxConns,
                FCGI_MAX_REQS: maxReqs,
                FCGI_MPXS_CONNS: multiplexed and 1 or 0
                }
        else:
            self._connectionClass = Connection
            self.capability = {
                # If threads aren't available, these are pretty much correct.
                FCGI_MAX_CONNS: 1,
                FCGI_MAX_REQS: 1,
                FCGI_MPXS_CONNS: 0
                }
        self._bindAddress = bindAddress
        self._umask = umask

    def _setupSocket(self):
        if self._bindAddress is None: # Run as a normal FastCGI?
            isFCGI = True

            sock = socket.fromfd(FCGI_LISTENSOCK_FILENO, socket.AF_INET,
                                 socket.SOCK_STREAM)
            try:
                sock.getpeername()
            except socket.error, e:
                if e[0] == errno.ENOTSOCK:
                    # Not a socket, assume CGI context.
                    isFCGI = False
                elif e[0] != errno.ENOTCONN:
                    raise

            # FastCGI/CGI discrimination is broken on Mac OS X.
            # Set the environment variable FCGI_FORCE_CGI to "Y" or "y"
            # if you want to run your app as a simple CGI. (You can do
            # this with Apache's mod_env [not loaded by default in OS X
            # client, ha ha] and the SetEnv directive.)
            if not isFCGI or \
               os.environ.get('FCGI_FORCE_CGI', 'N').upper().startswith('Y'):
                req = self.cgirequest_class(self)
                req.run()
                sys.exit(0)
        else:
            # Run as a server
            oldUmask = None
            if type(self._bindAddress) is str:
                # Unix socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    os.unlink(self._bindAddress)
                except OSError:
                    pass
                if self._umask is not None:
                    oldUmask = os.umask(self._umask)
            else:
                # INET socket
                assert type(self._bindAddress) is tuple
                assert len(self._bindAddress) == 2
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind(self._bindAddress)
            sock.listen(socket.SOMAXCONN)

            if oldUmask is not None:
                os.umask(oldUmask)

        return sock

    def _cleanupSocket(self, sock):
        """Closes the main socket."""
        sock.close()

    def _installSignalHandlers(self):
        self._oldSIGs = [(x,signal.getsignal(x)) for x in
                         (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)]
        signal.signal(signal.SIGHUP, self._hupHandler)
        signal.signal(signal.SIGINT, self._intHandler)
        signal.signal(signal.SIGTERM, self._intHandler)

    def _restoreSignalHandlers(self):
        for signum,handler in self._oldSIGs:
            signal.signal(signum, handler)
        
    def _hupHandler(self, signum, frame):
        self._hupReceived = True
        self._keepGoing = False

    def _intHandler(self, signum, frame):
        self._keepGoing = False

    def run(self, timeout=1.0):
        """
        The main loop. Exits on SIGHUP, SIGINT, SIGTERM. Returns True if
        SIGHUP was received, False otherwise.
        """
        web_server_addrs = os.environ.get('FCGI_WEB_SERVER_ADDRS')
        if web_server_addrs is not None:
            web_server_addrs = map(lambda x: x.strip(),
                                   web_server_addrs.split(','))

        sock = self._setupSocket()

        self._keepGoing = True
        self._hupReceived = False

        # Install signal handlers.
        self._installSignalHandlers()

        while self._keepGoing:
            try:
                r, w, e = select.select([sock], [], [], timeout)
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                raise

            if r:
                try:
                    clientSock, addr = sock.accept()
                except socket.error, e:
                    if e[0] in (errno.EINTR, errno.EAGAIN):
                        continue
                    raise

                if web_server_addrs and \
                       (len(addr) != 2 or addr[0] not in web_server_addrs):
                    clientSock.close()
                    continue

                # Instantiate a new Connection and begin processing FastCGI
                # messages (either in a new thread or this thread).
                conn = self._connectionClass(clientSock, addr, self)
                thread.start_new_thread(conn.run, ())

            self._mainloopPeriodic()

        # Restore signal handlers.
        self._restoreSignalHandlers()

        self._cleanupSocket(sock)

        return self._hupReceived

    def _mainloopPeriodic(self):
        """
        Called with just about each iteration of the main loop. Meant to
        be overridden.
        """
        pass

    def _exit(self, reload=False):
        """
        Protected convenience method for subclasses to force an exit. Not
        really thread-safe, which is why it isn't public.
        """
        if self._keepGoing:
            self._keepGoing = False
            self._hupReceived = reload

    def handler(self, req):
        """
        Default handler, which just raises an exception. Unless a handler
        is passed at initialization time, this must be implemented by
        a subclass.
        """
        raise NotImplementedError, self.__class__.__name__ + '.handler'

    def error(self, req):
        """
        Called by Request if an exception occurs within the handler. May and
        should be overridden.
        """
        import cgitb
        req.stdout.write('Content-Type: text/html\r\n\r\n' +
                         cgitb.html(sys.exc_info()))

class WSGIServer(Server):
    """
    FastCGI server that supports the Web Server Gateway Interface. See
    <http://www.python.org/peps/pep-0333.html>.
    """
    def __init__(self, application, environ=None, umask=None,
                 multithreaded=True, **kw):
        """
        environ, if present, must be a dictionary-like object. Its
        contents will be copied into application's environ. Useful
        for passing application-specific variables.

        Set multithreaded to False if your application is not MT-safe.
        """
        if kw.has_key('handler'):
            del kw['handler'] # Doesn't make sense to let this through
        super(WSGIServer, self).__init__(**kw)

        if environ is None:
            environ = {}

        self.application = application
        self.environ = environ
        self.multithreaded = multithreaded

        # Used to force single-threadedness
        self._app_lock = thread.allocate_lock()

    def handler(self, req):
        """Special handler for WSGI."""
        if req.role != FCGI_RESPONDER:
            return FCGI_UNKNOWN_ROLE, 0

        # Mostly taken from example CGI gateway.
        environ = req.params
        environ.update(self.environ)

        environ['wsgi.version'] = (1,0)
        environ['wsgi.input'] = req.stdin
        if self._bindAddress is None:
            stderr = req.stderr
        else:
            stderr = TeeOutputStream((sys.stderr, req.stderr))
        environ['wsgi.errors'] = stderr
        environ['wsgi.multithread'] = not isinstance(req, CGIRequest) and \
                                      thread_available and self.multithreaded
        # Rationale for the following: If started by the web server
        # (self._bindAddress is None) in either FastCGI or CGI mode, the
        # possibility of being spawned multiple times simultaneously is quite
        # real. And, if started as an external server, multiple copies may be
        # spawned for load-balancing/redundancy. (Though I don't think
        # mod_fastcgi supports this?)
        environ['wsgi.multiprocess'] = True
        environ['wsgi.run_once'] = isinstance(req, CGIRequest)

        if environ.get('HTTPS', 'off') in ('on', '1'):
            environ['wsgi.url_scheme'] = 'https'
        else:
            environ['wsgi.url_scheme'] = 'http'

        self._sanitizeEnv(environ)

        headers_set = []
        headers_sent = []
        result = None

        def write(data):
            assert type(data) is str, 'write() argument must be string'
            assert headers_set, 'write() before start_response()'

            if not headers_sent:
                status, responseHeaders = headers_sent[:] = headers_set
                found = False
                for header,value in responseHeaders:
                    if header.lower() == 'content-length':
                        found = True
                        break
                if not found and result is not None:
                    try:
                        if len(result) == 1:
                            responseHeaders.append(('Content-Length',
                                                    str(len(data))))
                    except:
                        pass
                s = 'Status: %s\r\n' % status
                for header in responseHeaders:
                    s += '%s: %s\r\n' % header
                s += '\r\n'
                req.stdout.write(s)

            req.stdout.write(data)
            req.stdout.flush()

        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        # Re-raise if too late
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None # avoid dangling circular ref
            else:
                assert not headers_set, 'Headers already set!'

            assert type(status) is str, 'Status must be a string'
            assert len(status) >= 4, 'Status must be at least 4 characters'
            assert int(status[:3]), 'Status must begin with 3-digit code'
            assert status[3] == ' ', 'Status must have a space after code'
            assert type(response_headers) is list, 'Headers must be a list'
            if __debug__:
                for name,val in response_headers:
                    assert type(name) is str, 'Header names must be strings'
                    assert type(val) is str, 'Header values must be strings'

            headers_set[:] = [status, response_headers]
            return write

        if not self.multithreaded:
            self._app_lock.acquire()
        try:
            try:
                result = self.application(environ, start_response)
                try:
                    for data in result:
                        if data:
                            write(data)
                    if not headers_sent:
                        write('') # in case body was empty
                finally:
                    if hasattr(result, 'close'):
                        result.close()
            except socket.error, e:
                if e[0] != errno.EPIPE:
                    raise # Don't let EPIPE propagate beyond server
        finally:
            if not self.multithreaded:
                self._app_lock.release()

        return FCGI_REQUEST_COMPLETE, 0

    def _sanitizeEnv(self, environ):
        """Ensure certain values are present, if required by WSGI."""
        if not environ.has_key('SCRIPT_NAME'):
            environ['SCRIPT_NAME'] = ''
        if not environ.has_key('PATH_INFO'):
            environ['PATH_INFO'] = ''

        # If any of these are missing, it probably signifies a broken
        # server...
        for name,default in [('REQUEST_METHOD', 'GET'),
                             ('SERVER_NAME', 'localhost'),
                             ('SERVER_PORT', '80'),
                             ('SERVER_PROTOCOL', 'HTTP/1.0')]:
            if not environ.has_key(name):
                environ['wsgi.errors'].write('%s: missing FastCGI param %s '
                                             'required by WSGI!\n' %
                                             (self.__class__.__name__, name))
                environ[name] = default
            
if __name__ == '__main__':
    def test_app(environ, start_response):
        """Probably not the most efficient example."""
        import cgi
        start_response('200 OK', [('Content-Type', 'text/html')])
        yield '<html><head><title>Hello World!</title></head>\n' \
              '<body>\n' \
              '<p>Hello World!</p>\n' \
              '<table border="1">'
        names = environ.keys()
        names.sort()
        for name in names:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                name, cgi.escape(`environ[name]`))

        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ,
                                keep_blank_values=1)
        if form.list:
            yield '<tr><th colspan="2">Form data</th></tr>'

        for field in form.list:
            yield '<tr><td>%s</td><td>%s</td></tr>\n' % (
                field.name, field.value)

        yield '</table>\n' \
              '</body></html>\n'

    WSGIServer(test_app).run()

########NEW FILE########
__FILENAME__ = geocoders
from graphserver.ext.osm.osmdb import OSMDB

class OSMReverseGeocoder:
    def __init__(self, osmdb_filename):
        self.osmdb = OSMDB( osmdb_filename )
        
    def __call__(self, lat, lon):
        nearby_vertex = list(self.osmdb.nearest_node(lat, lon))
        return "osm-%s"%(nearby_vertex[0])
        
    def bounds(self):
        """return tuple representing bounding box of reverse geocoder with form (left, bottom, right, top)"""
        
        return self.osmdb.bounds()
########NEW FILE########
__FILENAME__ = routeserver
from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
try:
    import json
except ImportError:
    import simplejson as json
import yaml
import os
from fcgi import WSGIServer
    
from events import BoardEvent, AlightEvent, HeadwayBoardEvent, HeadwayAlightEvent, StreetEvent, StreetTurnEvent

class SelfEncoderHelper(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_jsonable"):
            return obj.to_jsonable()
        return json.JSONEncoder.default(self, obj)

def postprocess_path_raw(vertices, edges):
    retbuilder = []
    
    retbuilder.append("vertices")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex)) )
    
    retbuilder.append("")
    retbuilder.append("states")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex.state)) )
    
    retbuilder.append("")
    retbuilder.append("edges")
    for i, edge in enumerate(edges):
        retbuilder.append( "%d %s"%(i, str(edge.payload)) )
        
    return "\n".join(retbuilder)
    
def postprocess_path(vertices, edges, vertex_events, edge_events):
    context = {}
    
    for edge1,vertex1,edge2,vertex2 in zip( [None]+edges, vertices, edges+[None], vertices[1:]+[None,None] ):
        #fire vertex events
        for handler in vertex_events:
            if handler.applies_to( edge1, vertex1, edge2 ):
                event = handler( edge1, vertex1, edge2, context=context )
                if event is not None:
                    yield handler.__class__.__name__, event
        
        #fire edge events
        for handler in edge_events:
            if handler.applies_to( vertex1, edge2, vertex2 ):
                event = handler( vertex1, edge2, vertex2, context=context )
                if event is not None:
                    yield handler.__class__.__name__, event

class RouteServer(Servable):
    def __init__(self, graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.vertex_events = vertex_events
        self.edge_events = edge_events
        self.vertex_reverse_geocoders = vertex_reverse_geocoders
        
    def bounds(self, jsoncallback=None):
        """returns bounding box that encompases the bounding box from all member reverse geocoders"""
        
        l, b, r, t = None, None, None, None
        
        for reverse_geocoder in self.vertex_reverse_geocoders:
            gl, gb, gr, gt = reverse_geocoder.bounds()
            l = min(l,gl) if l else gl
            b = min(b,gb) if b else gb
            r = max(r,gr) if r else gr
            t = max(t,gt) if t else gt
        
        if jsoncallback is None:
            return json.dumps([l,b,r,t])
        else:
            return "%s(%s)"%(jsoncallback,json.dumps([l,b,r,t]))
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"
    
    def get_vertex_id_raw( self, lat, lon ):
        for reverse_geocoder in self.vertex_reverse_geocoders:
            ret = reverse_geocoder( lat, lon )
            if ret is not None:
                return ret
                
        return None
        
    def get_vertex_id( self, lat, lon ):
        return json.dumps( self.get_vertex_id_raw( lat, lon ) )

    def path(self, 
             origin, 
             dest,
             currtime=None, 
             time_offset=None, 
             transfer_penalty=0, 
             walking_speed=1.0,
             hill_reluctance=1.5,
             turn_penalty=None,
             walking_reluctance=None,
             max_walk=None,
             jsoncallback=None):
        
        performance = {}
        
        if currtime is None:
            currtime = int(time.time())
            
        if time_offset is not None:
            currtime += time_offset
        
        # time path query
        t0 = time.time()
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        wo.hill_reluctance=hill_reluctance
        if turn_penalty is not None:
            wo.turn_penalty = turn_penalty
        if walking_reluctance is not None:
            wo.walking_reluctance = walking_reluctance
        if max_walk is not None:
            wo.max_walk = max_walk
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
       
        try:
          vertices, edges = spt.path( dest )
	except Exception, e:
	  return json.dumps( {'error':str(e)} )

        performance['path_query_time'] = time.time()-t0
        
        t0 = time.time()
        narrative = list(postprocess_path(vertices, edges, self.vertex_events, self.edge_events))
        performance['narrative_postprocess_time'] = time.time()-t0
        
        t0 = time.time()
        wo.destroy()
        spt.destroy()
        performance['cleanup_time'] = time.time()-t0
        
        ret = {'narrative':narrative, 'performance':performance}
        
        if jsoncallback is None:
            return json.dumps(ret, indent=2, cls=SelfEncoderHelper)
        else:
            return "%s(%s)"%(jsoncallback,json.dumps(ret, indent=2, cls=SelfEncoderHelper))
            
    def geompath(self, lat1,lon1,lat2,lon2, 
                 currtime=None, 
                 time_offset=None, 
                 transfer_penalty=0, 
                 walking_speed=1.0, 
                 hill_reluctance=1.5,
                 turn_penalty=None,
                 walking_reluctance=None,
                 max_walk=None,
                 jsoncallback=None):
        origin_vertex_label = self.get_vertex_id_raw( lat1, lon1 )
        dest_vertex_label = self.get_vertex_id_raw( lat2, lon2 )
        
        if origin_vertex_label is None:
            raise Exception( "could not find a vertex near (%s,%s)"%(lat1,lon1) )
        if dest_vertex_label is None:
            raise Exception( "could not find a vertex near (%s,%s)"%(lat2,lon2) )
            
        return self.path( origin_vertex_label,
                     dest_vertex_label,
                     currtime,
                     time_offset,
                     transfer_penalty,
                     walking_speed,
                     hill_reluctance,
                     turn_penalty,
                     walking_reluctance,
                     max_walk,
                     jsoncallback )
        
    def path_retro(self, origin, dest, currtime=None, time_offset=None, transfer_penalty=0, walking_speed=1.0):
        if currtime is None:
            currtime = int(time.time())
            
        if time_offset is not None:
            currtime += time_offset
        
        wo = WalkOptions()
        wo.transfer_penalty = transfer_penalty
        wo.walking_speed = walking_speed
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = list(postprocess_path(vertices, edges, self.vertex_events, self.edge_events))
        
        spt.destroy()
        
        return json.dumps(ret, indent=2, cls=SelfEncoderHelper)

    def path_raw(self, origin, dest, currtime=None):
        if currtime is None:
            currtime = int(time.time())
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = postprocess_path_raw(vertices, edges)
    
        spt.destroy()
        
        return ret
        
    def path_raw_retro(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = postprocess_path_raw(vertices, edges)

        spt.destroy()
        
        return ret
        
def import_class(handler_class_path_string):
    sys.path.append( os.getcwd() )
    
    handler_class_path = handler_class_path_string.split(".")
    
    class_name = handler_class_path[-1]
    package_name = ".".join(handler_class_path[:-1])
    
    package = __import__(package_name, fromlist=[class_name])
    
    try:
        handler_class = getattr( package, class_name )
    except AttributeError:
        raise AttributeError( "Can't find %s. Only %s"%(class_name, dir(package)) )
    
    return handler_class
    
def get_handler_instances( handler_definitions, handler_type ):
    if handler_definitions is None:
        return
    
    if handler_type not in handler_definitions:
        return
    
    for handler in handler_definitions[handler_type]:
        handler_class = import_class( handler['name'] )
        handler_instance = handler_class(**handler.get("args", {}))
        
        yield handler_instance
        

from optparse import OptionParser
def main():
    
    # get command line input
    usage = """python routeserver.py graphdb_filename config_filename"""
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--port", dest="port", default="8080",
                      help="Port to serve HTTP, if serving as a standalone server")
    parser.add_option("-s", "--socket", dest="socket", default=None, 
                      help="Socket on which serve fastCGI. If both port and socket are specified, serves as an fastCGI backend.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.print_help()
        exit(-1)
        
    graphdb_filename, config_filename = args
    
    # get narrative handler classes
    handler_definitions = yaml.load( open(config_filename).read() )
    
    edge_events = list(get_handler_instances( handler_definitions, 'edge_handlers' ) )
    vertex_events = list(get_handler_instances( handler_definitions, 'vertex_handlers' ) )
    vertex_reverse_geocoders = list(get_handler_instances( handler_definitions, 'vertex_reverse_geocoders' ) )
    
    # explain to the nice people which handlers were loaded
    print "edge event handlers:"
    for edge_event in edge_events:
        print "   %s"%edge_event
    print "vertex event handlers:"
    for vertex_event in vertex_events:
        print "   %s"%vertex_event
    print "vertex reverse geocoders:"
    for vertex_reverse_geocoder in vertex_reverse_geocoders:
        print "   %s"%vertex_reverse_geocoder
    
    # start up the routeserver
    gc = RouteServer(graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders)
    
    # serve as either an HTTP server or an fastCGI backend
    if options.socket:
        print "Starting fastCGI backend serving at %s"%options.socket
        WSGIServer(gc.wsgi_app(), bindAddress = options.socket).run()
    else:
        gc.run_test_server(port=int(options.port))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = graphdb
import os
import sqlite3
import cPickle
from graphserver.core import State, Graph, Combination
from graphserver import core
from sys import argv
import sys

class GraphDatabase:
    
    def __init__(self, sqlite_filename, overwrite=False):
        if overwrite:
            if os.path.exists(sqlite_filename):
                os.remove( sqlite_filename )
        elif not os.path.exists(sqlite_filename):
            overwrite = True # force an init of the tables
                
        self.conn = sqlite3.connect(sqlite_filename)
        
        if overwrite:
            self.setup()
            
        self.resources_cache = {}
        self.payloads_cache = {}
        
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE vertices (label)" )
        c.execute( "CREATE TABLE payloads (id TEXT UNIQUE ON CONFLICT IGNORE, type TEXT, state TEXT)" )
        c.execute( "CREATE TABLE edges (vertex1 TEXT, vertex2 TEXT, epid TEXT)" )
        c.execute( "CREATE TABLE resources (name TEXT UNIQUE ON CONFLICT IGNORE, image TEXT)" )
    
        self.conn.commit()
        c.close()
        
    def put_edge_payload(self, edgepayload, cc):
        
        if edgepayload.__class__ == Combination:
            for component in edgepayload.components:
                self.put_edge_payload( component, cc )
        
        cc.execute( "INSERT INTO payloads VALUES (?, ?, ?)", ( str(edgepayload.soul), cPickle.dumps( edgepayload.__class__ ), cPickle.dumps( edgepayload.__getstate__() ) ) )
        
        return str(edgepayload.soul)
        
    def get_edge_payload(self, id):
        queryresult = list(self.execute( "SELECT id, type, state FROM payloads WHERE id=?", (id,) ))
        if len(queryresult)==0:
            return None
        
        id, type, state = queryresult[0]
        
        if id in self.payloads_cache:
            return self.payloads_cache[id]
        
        typeclass = cPickle.loads( str(type) )
        ret = typeclass.reconstitute( cPickle.loads( str(state) ), self )
        ret.external_id = int(id)
        self.payloads_cache[id] = ret
        return ret
        
    def populate(self, graph, reporter=None):
        c = self.conn.cursor()
        
        n = len(graph.vertices)
	nseg = max(n,100)
        for i, vv in enumerate( graph.vertices ):
            if reporter and i%(nseg//100)==0: reporter.write( "%d/%d vertices dumped\n"%(i,n) )
            
            c.execute( "INSERT INTO vertices VALUES (?)", (vv.label,) )
            for ee in vv.outgoing:
                epid = self.put_edge_payload( ee.payload, c )
                c.execute( "INSERT INTO edges VALUES (?, ?, ?)", (ee.from_v.label, ee.to_v.label, epid) )
                
                if hasattr(ee.payload, "__resources__"):
                    for name, resource in ee.payload.__resources__():
                        self.store( name, resource, c )
        
        self.conn.commit()
        c.close()
        
        self.index()
        
    def get_cursor(self):
        return self.conn.cursor()
    def commit(self):
        self.conn.commit()
        
    def add_vertex(self, vertex_label, outside_c=None):
        c = outside_c or self.conn.cursor()
        
        c.execute( "INSERT INTO vertices VALUES (?)", (vertex_label,) )
        
        if outside_c is None:
            self.conn.commit()
            c.close()
            
    def remove_edge( self, oid, outside_c=None ):
        c = outside_c or self.conn.cursor()
        
        c.execute( "DELETE FROM edges WHERE oid=?", (oid,) )
        
        if outside_c is None:
            self.conn.commit()
            c.close()
        
    def add_edge(self, from_v_label, to_v_label, payload, outside_c=None):
        c = outside_c or self.conn.cursor()
    
        epid = self.put_edge_payload( payload, c )
        c.execute( "INSERT INTO edges VALUES (?, ?, ?)", (from_v_label, to_v_label, epid) )
    
        if hasattr(payload, "__resources__"):
            for name, resource in payload.__resources__():
                self.store( name, resource )
    
        if outside_c is None:
            self.conn.commit()
            c.close()
        
    def execute(self, query, args=None):
        
        c = self.conn.cursor()
        
        if args:
            c.execute( query, args )
        else:
            c.execute( query )
            
        for record in c:
            yield record
        c.close()
        
    def all_vertex_labels(self):
        for vertex_label, in self.execute( "SELECT DISTINCT label FROM (SELECT vertex1 AS label FROM edges UNION SELECT vertex2 AS label FROM edges)" ):
            yield vertex_label
    
    def all_edges(self):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges" ):
            ep = self.get_edge_payload( epid )
            
            yield vertex1, vertex2, ep
    
    def all_outgoing(self, vertex1_label):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges WHERE vertex1=?", (vertex1_label,) ):
            yield vertex1, vertex2, self.get_edge_payload( epid )
    
    def all_incoming(self, vertex2_label):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges WHERE vertex2=?", (vertex2_label,) ):
            yield vertex1, vertex2, self.get_edge_payload( epid )
    
            
    def store(self, name, obj, c=None):
        cc = self.conn.cursor() if c is None else c
        resource_count = list(cc.execute( "SELECT count(*) FROM resources WHERE name = ?", (name,) ))[0][0]
        if resource_count == 0:
            cc.execute( "INSERT INTO resources VALUES (?, ?)", (name, cPickle.dumps( obj )) )
            if not c: self.conn.commit()
        if not c: cc.close()
        
    def resolve(self, name):
        if name in self.resources_cache:
            return self.resources_cache[name]
        else:
            image = list(self.execute( "SELECT image FROM resources WHERE name = ?", (str(name),) ))[0][0]
            resource = cPickle.loads( str(image) )
            self.resources_cache[name] = resource
            return resource
        
    def resources(self):
        for name, image in self.execute( "SELECT name, image from resources" ):
            yield name, cPickle.loads( str(image) )
            
    def index(self):
        c = self.conn.cursor()
        c.execute( "CREATE INDEX vertices_label ON vertices (label)" )
        c.execute( "CREATE INDEX ep_ids ON payloads (id)" )
        self.conn.commit()
        c.close()
        
    def num_vertices(self):
        return list(self.execute( "SELECT count(*) from vertices" ))[0][0]
        
    def num_edges(self):
        return list(self.execute( "SELECT count(*) from edges" ))[0][0]
        
    def incarnate(self, reporter=sys.stdout):
        g = Graph()
        num_vertices = self.num_vertices()
        
        for i, vertex_label in enumerate( self.all_vertex_labels() ):
            if reporter and i%5000==0: 
                reporter.write("\r%d/%d vertices"%(i,num_vertices) ) 
                reporter.flush()
            g.add_vertex( vertex_label )
        
        if reporter: reporter.write("\rLoaded %d vertices %s\n" % (num_vertices, " "*10))
        
        num_edges = self.num_edges()
        for i, (vertex1, vertex2, edgetype) in enumerate( self.all_edges() ):
            if i%5000==0: 
                reporter.write("\r%d/%d edges"%(i,num_edges) ) 
                reporter.flush()
            g.add_edge( vertex1, vertex2, edgetype )
        if reporter: reporter.write("\rLoaded %d edges %s\n" % (num_edges, " "*10))
        
        return g
        

def main():
    if len(argv) < 2:
        print "usage: python graphdb.py [vertex1, [vertex2]]"
        return
    
    graphdb_filename = argv[1]
    graphdb = GraphDatabase( graphdb_filename )
    
    if len(argv) == 2:
        print "vertices:"
        for vertex_label in sorted( graphdb.all_vertex_labels() ):
            print vertex_label
        print "resources:"
        for name, resource in graphdb.resources():
            print name, resource
        return
    
    vertex1 = argv[2]
    for vertex1, vertex2, edgetype in graphdb.all_outgoing( vertex1 ):
        print "%s -> %s\n\t%s"%(vertex1, vertex2, repr(edgetype))
        
        if len(argv) == 4:
            s0 = State(1,int(argv[3]))
            print "\t"+str(edgetype.walk( s0 ))

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = gsdll
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_float, c_size_t, c_char_p, c_double, c_void_p, py_object
from ctypes import c_int8, c_int16, c_int32, c_int64, sizeof
from ctypes import Structure, pointer, cast, POINTER, addressof
from ctypes.util import find_library

import os
import sys

# The libgraphserver.so object:
lgs = None

# Try loading from the source tree. If that doesn't work, fall back to the installed location.
_dlldirs = [os.path.dirname(os.path.abspath(__file__)),
            os.path.dirname(os.path.abspath(__file__)) + '/../../core',
            '/usr/lib',
            '/usr/local/lib']

for _dlldir in _dlldirs:
    _dllpath = os.path.join(_dlldir, 'libgraphserver.so')
    if os.path.exists(_dllpath):
        lgs = PyDLL( _dllpath )
        break

if not lgs:
    raise ImportError("unable to find libgraphserver shared library in the usual locations: %s" % "\n".join(_dlldirs))

libc = cdll.LoadLibrary(find_library('c'))

class _EmptyClass(object):
    pass

def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = _EmptyClass()
    ret.__class__ = cls
    return ret

def cleanup():
    """ Perform any necessary cleanup when the library is unloaded."""
    pass

atexit.register(cleanup)

class CShadow(object):
    """ Base class for all objects that shadow a C structure."""
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
        
    def check_destroyed(self):
        if self.soul is None:
            raise Exception("You are trying to use an instance that has been destroyed")

def _declare(fun, restype, argtypes):
    fun.argtypes = argtypes
    fun.restype = restype
    fun.safe = True

class LGSTypes:
    ServiceId = c_int
    EdgePayload = c_void_p
    State = c_void_p
    WalkOptions = c_void_p
    Vertex = c_void_p
    Edge = c_void_p
    ListNode = c_void_p
    Graph = c_void_p
    Path = c_void_p
    Vector = c_void_p
    SPTVertex = c_void_p
    ShortestPathTree = c_void_p
    ServicePeriod = c_void_p
    ServiceCalendar = c_void_p
    Timezone = c_void_p
    TimezonePeriod = c_void_p
    Link = c_void_p
    Street = c_void_p
    Egress = c_void_p
    Wait = c_void_p
    ElapseTime = c_void_p
    Headway = c_void_p
    TripBoard = c_void_p
    HeadwayBoard = c_void_p
    HeadwayAlight = c_void_p
    Crossing = c_void_p
    Alight = c_void_p
    PayloadMethods = c_void_p
    CustomPayload = c_void_p
    TripAlight = c_void_p
    Combination = c_void_p
    CHPath = c_void_p
    CH = c_void_p
    Heap = c_void_p
    HeapNode = c_void_p
    edgepayload_t = c_int
    class ENUM_edgepayload_t:
        PL_STREET = 0
        PL_TRIPHOPSCHED_DEPRIC = 1
        PL_TRIPHOP_DEPRIC = 2
        PL_LINK = 3
        PL_EXTERNVALUE = 4
        PL_NONE = 5
        PL_WAIT = 6
        PL_HEADWAY = 7
        PL_TRIPBOARD = 8
        PL_CROSSING = 9
        PL_ALIGHT = 10
        PL_HEADWAYBOARD = 11
        PL_EGRESS = 12
        PL_HEADWAYALIGHT = 13
        PL_ELAPSE_TIME = 14
        PL_COMBINATION = 15

LGSTypes.edgepayload_t = {1:c_int8, 2:c_int16, 4:c_int32, 8:c_int64}[c_size_t.in_dll(lgs, "EDGEPAYLOAD_ENUM_SIZE").value]
declarations = [\
    (lgs.chpNew, LGSTypes.CHPath, [c_int, c_long]),
    (lgs.chpLength, c_int, [LGSTypes.CHPath]),
    (lgs.chpCombine, LGSTypes.CHPath, [LGSTypes.CHPath, LGSTypes.CHPath]),
    (lgs.chpDestroy, None, [LGSTypes.CHPath]),
    (lgs.dist, LGSTypes.CHPath, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.WalkOptions, c_int, c_int]),
    (lgs.get_shortcuts, POINTER(LGSTypes.CHPath), [LGSTypes.Graph, LGSTypes.Vertex, LGSTypes.WalkOptions, c_int, POINTER(c_int)]),
    (lgs.init_priority_queue, LGSTypes.Heap, [LGSTypes.Graph, LGSTypes.WalkOptions, c_int]),
    (lgs.pqPush, None, [LGSTypes.Heap, LGSTypes.Vertex, c_long]),
    (lgs.pqPop, LGSTypes.Vertex, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.get_contraction_hierarchies, LGSTypes.CH, [LGSTypes.Graph, LGSTypes.WalkOptions, c_int]),
    (lgs.chNew, LGSTypes.CH, []),
    (lgs.chUpGraph, LGSTypes.Graph, [LGSTypes.CH]),
    (lgs.chDownGraph, LGSTypes.Graph, [LGSTypes.CH]),
    (lgs.epNew, LGSTypes.EdgePayload, [LGSTypes.edgepayload_t, c_void_p]),
    (lgs.epDestroy, None, [LGSTypes.EdgePayload]),
    (lgs.epGetType, LGSTypes.edgepayload_t, [LGSTypes.EdgePayload]),
    (lgs.epGetExternalId, c_long, [LGSTypes.EdgePayload]),
    (lgs.epSetExternalId, None, [LGSTypes.EdgePayload, c_long]),
    (lgs.epWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.epWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.gNew, LGSTypes.Graph, []),
    (lgs.gDestroyBasic, None, [LGSTypes.Graph, c_int]),
    (lgs.gDestroy, None, [LGSTypes.Graph]),
    (lgs.gAddVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (lgs.gRemoveVertex, None, [LGSTypes.Graph, c_char_p, c_int]),
    (lgs.gGetVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (lgs.gAddVertices, None, [LGSTypes.Graph, POINTER(c_char_p), c_int]),
    (lgs.gAddEdge, LGSTypes.Edge, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (lgs.gVertices, POINTER(LGSTypes.Vertex), [LGSTypes.Graph, POINTER(c_long)]),
    (lgs.gShortestPathTree, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gShortestPathTreeRetro, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gShortestPath, LGSTypes.State, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, c_int, POINTER(c_long), LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gSize, c_long, [LGSTypes.Graph]),
    (lgs.gSetVertexEnabled, None, [LGSTypes.Graph, c_char_p, c_int]),
    (lgs.sptNew, LGSTypes.ShortestPathTree, []),
    (lgs.sptDestroy, None, [LGSTypes.ShortestPathTree]),
    (lgs.sptAddVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, LGSTypes.Vertex, c_int]),
    (lgs.sptRemoveVertex, None, [LGSTypes.ShortestPathTree, c_char_p]),
    (lgs.sptGetVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, c_char_p]),
    (lgs.sptAddEdge, LGSTypes.Edge, [LGSTypes.ShortestPathTree, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (lgs.sptVertices, POINTER(LGSTypes.SPTVertex), [LGSTypes.ShortestPathTree, POINTER(c_long)]),
    (lgs.sptSize, c_long, [LGSTypes.ShortestPathTree]),
    (lgs.sptPathRetro, LGSTypes.Path, [LGSTypes.Graph, c_char_p]),
    (lgs.vNew, LGSTypes.Vertex, [c_char_p]),
    (lgs.vDestroy, None, [LGSTypes.Vertex, c_int]),
    (lgs.vLink, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.vSetParent, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.vGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (lgs.vGetIncomingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (lgs.vRemoveOutEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.vRemoveInEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.vGetLabel, c_char_p, [LGSTypes.Vertex]),
    (lgs.vDegreeOut, c_int, [LGSTypes.Vertex]),
    (lgs.vDegreeIn, c_int, [LGSTypes.Vertex]),
    (lgs.sptvNew, LGSTypes.SPTVertex, [LGSTypes.Vertex, c_int]),
    (lgs.sptvDestroy, None, [LGSTypes.SPTVertex]),
    (lgs.sptvLink, LGSTypes.Edge, [LGSTypes.SPTVertex, LGSTypes.SPTVertex, LGSTypes.EdgePayload]),
    (lgs.sptvSetParent, LGSTypes.Edge, [LGSTypes.SPTVertex, LGSTypes.SPTVertex, LGSTypes.EdgePayload]),
    (lgs.sptvGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.SPTVertex]),
    (lgs.sptvGetIncomingEdgeList, LGSTypes.ListNode, [LGSTypes.SPTVertex]),
    (lgs.sptvRemoveOutEdgeRef, None, [LGSTypes.SPTVertex, LGSTypes.Edge]),
    (lgs.sptvRemoveInEdgeRef, None, [LGSTypes.SPTVertex, LGSTypes.Edge]),
    (lgs.sptvGetLabel, c_char_p, [LGSTypes.SPTVertex]),
    (lgs.sptvDegreeOut, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvDegreeIn, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvState, LGSTypes.State, [LGSTypes.SPTVertex]),
    (lgs.sptvHop, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvGetParent, LGSTypes.Edge, [LGSTypes.SPTVertex]),
    (lgs.sptvMirror, LGSTypes.Vertex, [LGSTypes.SPTVertex]),
    (lgs.eNew, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.eDestroy, None, [LGSTypes.Edge, c_int]),
    (lgs.eWalk, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.eWalkBack, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.eGetFrom, LGSTypes.Vertex, [LGSTypes.Edge]),
    (lgs.eGetTo, LGSTypes.Vertex, [LGSTypes.Edge]),
    (lgs.eGetPayload, LGSTypes.EdgePayload, [LGSTypes.Edge]),
    (lgs.eGetEnabled, c_int, [LGSTypes.Edge]),
    (lgs.eSetEnabled, None, [LGSTypes.Edge, c_int]),
    (lgs.heapNew, LGSTypes.Heap, [c_int]),
    (lgs.heapDestroy, None, [LGSTypes.Heap]),
    (lgs.heapInsert, None, [LGSTypes.Heap, c_void_p, c_long]),
    (lgs.heapEmpty, c_int, [LGSTypes.Heap]),
    (lgs.heapMin, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.heapPop, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.liNew, LGSTypes.ListNode, [LGSTypes.Edge]),
    (lgs.liInsertAfter, None, [LGSTypes.ListNode, LGSTypes.ListNode]),
    (lgs.liRemoveAfter, None, [LGSTypes.ListNode]),
    (lgs.liRemoveRef, None, [LGSTypes.ListNode, LGSTypes.Edge]),
    (lgs.liGetData, LGSTypes.Edge, [LGSTypes.ListNode]),
    (lgs.liGetNext, LGSTypes.ListNode, [LGSTypes.ListNode]),
    (lgs.pathNew, LGSTypes.Path, [LGSTypes.Vertex, c_int, c_int]),
    (lgs.pathDestroy, None, [LGSTypes.Path]),
    (lgs.pathGetVertex, LGSTypes.Vertex, [LGSTypes.Path, c_int]),
    (lgs.pathGetEdge, LGSTypes.Edge, [LGSTypes.Path, c_int]),
    (lgs.pathAddSegment, None, [LGSTypes.Path, LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.scNew, LGSTypes.ServiceCalendar, []),
    (lgs.scAddServiceId, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (lgs.scGetServiceIdString, c_char_p, [LGSTypes.ServiceCalendar, c_int]),
    (lgs.scGetServiceIdInt, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (lgs.scAddPeriod, None, [LGSTypes.ServiceCalendar, LGSTypes.ServicePeriod]),
    (lgs.scPeriodOfOrAfter, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (lgs.scPeriodOfOrBefore, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (lgs.scHead, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar]),
    (lgs.scDestroy, None, [LGSTypes.ServiceCalendar]),
    (lgs.spNew, LGSTypes.ServicePeriod, [c_long, c_long, c_int, POINTER(LGSTypes.ServiceId)]),
    (lgs.spDestroyPeriod, None, [LGSTypes.ServicePeriod]),
    (lgs.spPeriodHasServiceId, c_int, [LGSTypes.ServicePeriod, LGSTypes.ServiceId]),
    (lgs.spRewind, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spFastForward, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spPrint, None, [LGSTypes.ServicePeriod]),
    (lgs.spPrintPeriod, None, [LGSTypes.ServicePeriod]),
    (lgs.spNormalizeTime, c_long, [LGSTypes.ServicePeriod, c_int, c_long]),
    (lgs.spBeginTime, c_long, [LGSTypes.ServicePeriod]),
    (lgs.spEndTime, c_long, [LGSTypes.ServicePeriod]),
    (lgs.spServiceIds, POINTER(LGSTypes.ServiceId), [LGSTypes.ServicePeriod, POINTER(c_int)]),
    (lgs.spNextPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spPreviousPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spDatumMidnight, c_long, [LGSTypes.ServicePeriod, c_int]),
    (lgs.stateNew, LGSTypes.State, [c_int, c_long]),
    (lgs.stateDestroy, None, [LGSTypes.State]),
    (lgs.stateDup, LGSTypes.State, [LGSTypes.State]),
    (lgs.stateGetTime, c_long, [LGSTypes.State]),
    (lgs.stateGetWeight, c_long, [LGSTypes.State]),
    (lgs.stateGetDistWalked, c_double, [LGSTypes.State]),
    (lgs.stateGetNumTransfers, c_int, [LGSTypes.State]),
    (lgs.stateGetPrevEdge, LGSTypes.EdgePayload, [LGSTypes.State]),
    (lgs.stateGetTripId, c_char_p, [LGSTypes.State]),
    (lgs.stateGetStopSequence, c_int, [LGSTypes.State]),
    (lgs.stateGetNumAgencies, c_int, [LGSTypes.State]),
    (lgs.stateServicePeriod, LGSTypes.ServicePeriod, [LGSTypes.State, c_int]),
    (lgs.stateSetServicePeriod, None, [LGSTypes.State, c_int, LGSTypes.ServicePeriod]),
    (lgs.stateSetTime, None, [LGSTypes.State, c_long]),
    (lgs.stateSetWeight, None, [LGSTypes.State, c_long]),
    (lgs.stateSetDistWalked, None, [LGSTypes.State, c_double]),
    (lgs.stateSetNumTransfers, None, [LGSTypes.State, c_int]),
    (lgs.stateDangerousSetTripId, None, [LGSTypes.State, c_char_p]),
    (lgs.stateSetPrevEdge, None, [LGSTypes.State, LGSTypes.EdgePayload]),
    (lgs.tzNew, LGSTypes.Timezone, []),
    (lgs.tzAddPeriod, None, [LGSTypes.Timezone, LGSTypes.TimezonePeriod]),
    (lgs.tzPeriodOf, LGSTypes.TimezonePeriod, [LGSTypes.Timezone, c_long]),
    (lgs.tzUtcOffset, c_int, [LGSTypes.Timezone, c_long]),
    (lgs.tzTimeSinceMidnight, c_int, [LGSTypes.Timezone, c_long]),
    (lgs.tzHead, LGSTypes.TimezonePeriod, [LGSTypes.Timezone]),
    (lgs.tzDestroy, None, [LGSTypes.Timezone]),
    (lgs.tzpNew, LGSTypes.TimezonePeriod, [c_long, c_long, c_int]),
    (lgs.tzpDestroy, None, [LGSTypes.TimezonePeriod]),
    (lgs.tzpUtcOffset, c_int, [LGSTypes.TimezonePeriod]),
    (lgs.tzpTimeSinceMidnight, c_int, [LGSTypes.TimezonePeriod, c_long]),
    (lgs.tzpBeginTime, c_long, [LGSTypes.TimezonePeriod]),
    (lgs.tzpEndTime, c_long, [LGSTypes.TimezonePeriod]),
    (lgs.tzpNextPeriod, LGSTypes.TimezonePeriod, [LGSTypes.TimezonePeriod]),
    (lgs.vecNew, LGSTypes.Vector, [c_int, c_int]),
    (lgs.vecDestroy, None, [LGSTypes.Vector]),
    (lgs.vecAdd, None, [LGSTypes.Vector, c_void_p]),
    (lgs.vecGet, c_void_p, [LGSTypes.Vector, c_int]),
    (lgs.vecExpand, None, [LGSTypes.Vector, c_int]),
    (lgs.woNew, LGSTypes.WalkOptions, []),
    (lgs.woDestroy, None, [LGSTypes.WalkOptions]),
    (lgs.woGetTransferPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTransferPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingSpeed, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingSpeed, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetWalkingReluctance, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetUphillSlowness, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetUphillSlowness, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetDownhillFastness, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetDownhillFastness, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetHillReluctance, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetHillReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.comboNew, LGSTypes.Combination, [c_int]),
    (lgs.comboAdd, None, [LGSTypes.Combination, LGSTypes.EdgePayload]),
    (lgs.comboDestroy, None, [LGSTypes.Combination]),
    (lgs.comboWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.comboWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.comboGet, LGSTypes.EdgePayload, [LGSTypes.Combination, c_int]),
    (lgs.comboN, c_int, [LGSTypes.Combination]),
    (lgs.crNew, LGSTypes.Crossing, []),
    (lgs.crDestroy, None, [LGSTypes.Crossing]),
    (lgs.crAddCrossingTime, None, [LGSTypes.Crossing, c_char_p, c_int]),
    (lgs.crGetCrossingTime, c_int, [LGSTypes.Crossing, c_char_p]),
    (lgs.crGetCrossingTimeTripIdByIndex, c_char_p, [LGSTypes.Crossing, c_int]),
    (lgs.crGetCrossingTimeByIndex, c_int, [LGSTypes.Crossing, c_int]),
    (lgs.crGetSize, c_int, [LGSTypes.Crossing]),
    (lgs.crWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.crWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
#   For reasons presently opaque to me, argtypes for this function are set to None to make this work.
#   Old comment says: args are not specified to allow for None - therefore, setting to none
#    (lgs.defineCustomPayloadType, LGSTypes.PayloadMethods, [CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions)]),
    (lgs.defineCustomPayloadType, LGSTypes.PayloadMethods, None),
    (lgs.undefineCustomPayloadType, None, [LGSTypes.PayloadMethods]),
    (lgs.cpNew, LGSTypes.CustomPayload, [py_object, LGSTypes.PayloadMethods]),
    (lgs.cpDestroy, None, [LGSTypes.CustomPayload]),
    (lgs.cpSoul, py_object, [LGSTypes.CustomPayload]),
    (lgs.cpMethods, LGSTypes.PayloadMethods, [LGSTypes.CustomPayload]),
    (lgs.cpWalk, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.cpWalkBack, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressNew, LGSTypes.Egress, [c_char_p, c_double]),
    (lgs.egressDestroy, None, [LGSTypes.Egress]),
    (lgs.egressWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressGetName, c_char_p, [LGSTypes.Egress]),
    (lgs.egressGetLength, c_double, [LGSTypes.Egress]),
    (lgs.elapse_time_and_service_period_forward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (lgs.elapse_time_and_service_period_backward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (lgs.elapseTimeNew, LGSTypes.ElapseTime, [c_long]),
    (lgs.elapseTimeDestroy, None, [LGSTypes.ElapseTime]),
    (lgs.elapseTimeWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.elapseTimeWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.elapseTimeGetSeconds, c_long, [LGSTypes.ElapseTime]),
    (lgs.headwayNew, LGSTypes.Headway, [c_int, c_int, c_int, c_int, c_char_p, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, LGSTypes.ServiceId]),
    (lgs.headwayDestroy, None, [LGSTypes.Headway]),
    (lgs.headwayWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.headwayWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.headwayBeginTime, c_int, [LGSTypes.Headway]),
    (lgs.headwayEndTime, c_int, [LGSTypes.Headway]),
    (lgs.headwayWaitPeriod, c_int, [LGSTypes.Headway]),
    (lgs.headwayTransit, c_int, [LGSTypes.Headway]),
    (lgs.headwayTripId, c_char_p, [LGSTypes.Headway]),
    (lgs.headwayCalendar, LGSTypes.ServiceCalendar, [LGSTypes.Headway]),
    (lgs.headwayTimezone, LGSTypes.Timezone, [LGSTypes.Headway]),
    (lgs.headwayAgency, c_int, [LGSTypes.Headway]),
    (lgs.headwayServiceId, LGSTypes.ServiceId, [LGSTypes.Headway]),
    (lgs.haNew, LGSTypes.HeadwayAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (lgs.haDestroy, None, [LGSTypes.HeadwayAlight]),
    (lgs.haGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayAlight]),
    (lgs.haGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayAlight]),
    (lgs.haGetAgency, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayAlight]),
    (lgs.haGetTripId, c_char_p, [LGSTypes.HeadwayAlight]),
    (lgs.haGetStartTime, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetEndTime, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetHeadwaySecs, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.haWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.hbNew, LGSTypes.HeadwayBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (lgs.hbDestroy, None, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetAgency, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetTripId, c_char_p, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetStartTime, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetEndTime, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetHeadwaySecs, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.hbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkNew, LGSTypes.Link, []),
    (lgs.linkDestroy, None, [LGSTypes.Link]),
    (lgs.linkWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkGetName, c_char_p, [LGSTypes.Link]),
    (lgs.streetNew, LGSTypes.Street, [c_char_p, c_double, c_int]),
    (lgs.streetNewElev, LGSTypes.Street, [c_char_p, c_double, c_float, c_float, c_int]),
    (lgs.streetDestroy, None, [LGSTypes.Street]),
    (lgs.streetWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.streetWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.streetGetName, c_char_p, [LGSTypes.Street]),
    (lgs.streetGetLength, c_double, [LGSTypes.Street]),
    (lgs.streetGetRise, c_float, [LGSTypes.Street]),
    (lgs.streetGetFall, c_float, [LGSTypes.Street]),
    (lgs.streetSetRise, None, [LGSTypes.Street, c_float]),
    (lgs.streetSetFall, None, [LGSTypes.Street, c_float]),
    (lgs.streetGetWay, c_long, [LGSTypes.Street]),
    (lgs.streetSetWay, None, [LGSTypes.Street, c_long]),
    (lgs.streetGetSlog, c_float, [LGSTypes.Street]),
    (lgs.streetSetSlog, None, [LGSTypes.Street, c_float]),
    (lgs.streetGetReverseOfSource, c_int, [LGSTypes.Street]),
    (lgs.alNew, LGSTypes.TripAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (lgs.alDestroy, None, [LGSTypes.TripAlight]),
    (lgs.alGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripAlight]),
    (lgs.alGetTimezone, LGSTypes.Timezone, [LGSTypes.TripAlight]),
    (lgs.alGetAgency, c_int, [LGSTypes.TripAlight]),
    (lgs.alGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripAlight]),
    (lgs.alGetNumAlightings, c_int, [LGSTypes.TripAlight]),
    (lgs.alAddAlighting, None, [LGSTypes.TripAlight, c_char_p, c_int, c_int]),
    (lgs.alGetAlightingTripId, c_char_p, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetAlightingArrival, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetAlightingStopSequence, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alSearchAlightingsList, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetLastAlightingIndex, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetOverage, c_int, [LGSTypes.TripAlight]),
    (lgs.alGetAlightingIndexByTripId, c_int, [LGSTypes.TripAlight, c_char_p]),
    (lgs.alWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.alWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbNew, LGSTypes.TripBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (lgs.tbDestroy, None, [LGSTypes.TripBoard]),
    (lgs.tbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripBoard]),
    (lgs.tbGetTimezone, LGSTypes.Timezone, [LGSTypes.TripBoard]),
    (lgs.tbGetAgency, c_int, [LGSTypes.TripBoard]),
    (lgs.tbGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripBoard]),
    (lgs.tbGetNumBoardings, c_int, [LGSTypes.TripBoard]),
    (lgs.tbAddBoarding, None, [LGSTypes.TripBoard, c_char_p, c_int, c_int]),
    (lgs.tbGetBoardingTripId, c_char_p, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetBoardingDepart, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetBoardingStopSequence, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbSearchBoardingsList, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetNextBoardingIndex, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetOverage, c_int, [LGSTypes.TripBoard]),
    (lgs.tbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbGetBoardingIndexByTripId, c_int, [LGSTypes.TripBoard, c_char_p]),
    (lgs.waitNew, LGSTypes.Wait, [c_long, LGSTypes.Timezone]),
    (lgs.waitDestroy, None, [LGSTypes.Wait]),
    (lgs.waitWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.waitWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.waitGetEnd, c_long, [LGSTypes.Wait]),
    (lgs.waitGetTimezone, LGSTypes.Timezone, [LGSTypes.Wait])
]

for d in declarations:
    _declare(*d)

def caccessor(cfunc, restype, ptrclass=None):
    """Wraps a C data accessor in a python function.
       If a ptrclass is provided, the result will be converted to by the class' from_pointer method."""
    # Leaving this the the bulk declare process
    #cfunc.restype = restype
    #cfunc.argtypes = [c_void_p]
    if ptrclass:
        def prop(self):
            self.check_destroyed()
            ret = cfunc( c_void_p( self.soul ) )
            return ptrclass.from_pointer(ret)
    else:
        def prop(self):
            self.check_destroyed()
            return cfunc( c_void_p( self.soul ) )
    return prop

def cmutator(cfunc, argtype, ptrclass=None):
    """Wraps a C data mutator in a python function.  
       If a ptrclass is provided, the soul of the argument will be used."""
    # Leaving this to the bulk declare function
    #cfunc.argtypes = [c_void_p, argtype]
    #cfunc.restype = None
    if ptrclass:
        def propset(self, arg):
            cfunc( self.soul, arg.soul )
    else:
        def propset(self, arg):
            cfunc( self.soul, arg )
    return propset

def cproperty(cfunc, restype, ptrclass=None, setter=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    if not setter:
        return property(caccessor(cfunc, restype, ptrclass))
    return property(caccessor(cfunc, restype, ptrclass),
                    cmutator(setter, restype, ptrclass))

def ccast(func, cls):
    """Wraps a function to casts the result of a function (assumed c_void_p)
       into an object using the class's from_pointer method."""
    func.restype = c_void_p
    def _cast(self, *args):
        return cls.from_pointer(func(*args))
    return _cast

#CUSTOM TYPE API
class PayloadMethodTypes:
    """ Enumerates the ctypes of the function pointers."""
    destroy = CFUNCTYPE(c_void_p, py_object)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)

# 
import sys
class SafeWrapper(object):
    def __init__(self, lib, name):
        self.lib = lib
        self.name = name

    def __getattr__(self, attr):
        v = getattr(self.lib, attr)
        if not getattr(v, 'safe', False):
            raise Exception("Using unsafe method %s - you must declare the ctypes restype and argtypes in gsdll.py to ensure 64-bit compatibility." % attr)
        return SafeWrapper(v, name=self.name + "." + attr)

    def __call__(self, *args):
        """Very useful for debugging bogus calls to the DLL which result in segfaluts."""
        sys.stderr.write( ">%s %s(%s)\n" % (self.lib.restype and self.lib.restype.__name__ or None, self.name, ",".join(map(repr, args))))
        sys.stderr.flush()

        return self.lib(*args)

if 'GS_VERBOSE_CTYPES' in os.environ:
    lgs = SafeWrapper(lgs,'lgs')

########NEW FILE########
__FILENAME__ = util
import pytz
from datetime import datetime
import time
import sys

import calendar

SECS_IN_MINUTE = 60
SECS_IN_HOURS = 60*SECS_IN_MINUTE
SECS_IN_DAYS = 24*SECS_IN_HOURS

class TimeHelpers:
    
    @classmethod
    def unix_time(cls,year,month,day,hour,minute,second,offset=0):
        """When it is midnight in London, it is 4PM in Seattle: The offset is eight hours. In order
           to find the unix time of a local time in Seattle, take the unix time for the time in London.
           Then, increase the unix time by eight hours. At this time, it is 4PM in Seattle. Because
           Seattle is "behind" London, you will need to subtract the negative number in order to obtain
           the unix time of the local number. Thus:
           
           unix_time(local_time,offset) = london_unix_time(hours(local_time))-offset"""
        return calendar.timegm( (year,month,day,hour,minute,second) ) - offset
        
    @classmethod
    def localtime_to_unix(cls,year,month,day,hour,minute,second,timezone):
        dt = pytz.timezone(timezone).localize(datetime(year,month,day,hour,minute,second)).astimezone(pytz.utc)
        return calendar.timegm( (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) )
        
    @classmethod
    def datetime_to_unix(cls, dt):
        dt = dt.astimezone(pytz.utc)
        return calendar.timegm( (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) )
        
    @classmethod
    def create_localtime(cls,year,month,day,hour,minute,second,timezone):
        return pytz.timezone(timezone).localize(datetime(year,month,day,hour,minute,second))
        
    @classmethod
    def unix_to_localtime(cls,unixtime, timezone):
        tt = time.gmtime( unixtime )
        dt = pytz.utc.localize(datetime(tt[0],tt[1],tt[2],tt[3],tt[4],tt[5]))
        return dt.astimezone( pytz.timezone(timezone) )
        
    @classmethod
    def timedelta_to_seconds(cls,td):
        return td.days*SECS_IN_DAYS+td.seconds+td.microseconds/1000000.0
        
    @classmethod
    def unixtime_to_daytimes(cls,unixtime,timezone):
        dt = cls.unix_to_localtime(unixtime,timezone)
        ret = dt.hour*3600+dt.minute*60+dt.second
        return ret, ret+24*3600, ret+2*24*3600
        
def withProgress(seq, modValue=100):
    c = -1

    for c, v in enumerate(seq):
        if (c+1) % modValue == 0: 
            sys.stdout.write("%s\r" % (c+1)) 
            sys.stdout.flush()
        yield v

    print("\nCompleted %s" % (c+1))

########NEW FILE########
__FILENAME__ = vector
from gsdll import CShadow, lgs

from ctypes import Structure, c_int, c_void_p, pointer, addressof, byref

class Vector(Structure):
    _fields_ = [("num_elements", c_int),
                ("num_alloc", c_int),
                ("expand_delta", c_int),
                ("elements", c_void_p)]
                
    def __new__(cls, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = lgs.vecNew( init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        
        pass
        
    def expand(self, amount):
        lgs.vecExpand( addressof(self), amount )
        
    def add(self, element):
        lgs.vecAdd( addressof(self), element )
        
    def get(self, index):
        return lgs.vecGet( addressof(self), index )
        
    def __repr__(self):
        return "<Vector shadow of %s (%d/%d)>"%(hex(addressof(self)),self.num_elements, self.num_alloc)

    
    
    
    
########NEW FILE########
__FILENAME__ = vincenty
"""
822 	OpenLayers.Util.distVincenty=function(p1, p2) {
823 	    var a = 6378137, b = 6356752.3142,  f = 1/298.257223563;
824 	    var L = OpenLayers.Util.rad(p2.lon - p1.lon);
825 	    var U1 = Math.atan((1-f) * Math.tan(OpenLayers.Util.rad(p1.lat)));
826 	    var U2 = Math.atan((1-f) * Math.tan(OpenLayers.Util.rad(p2.lat)));
827 	    var sinU1 = Math.sin(U1), cosU1 = Math.cos(U1);
828 	    var sinU2 = Math.sin(U2), cosU2 = Math.cos(U2);
829 	    var lambda = L, lambdaP = 2*Math.PI;
830 	    var iterLimit = 20;
831 	    while (Math.abs(lambda-lambdaP) > 1e-12 && --iterLimit>0) {
832 	        var sinLambda = Math.sin(lambda), cosLambda = Math.cos(lambda);
833 	        var sinSigma = Math.sqrt((cosU2*sinLambda) * (cosU2*sinLambda) +
834 	        (cosU1*sinU2-sinU1*cosU2*cosLambda) * (cosU1*sinU2-sinU1*cosU2*cosLambda));
835 	        if (sinSigma==0) {
836 	            return 0;  // co-incident points
837 	        }
838 	        var cosSigma = sinU1*sinU2 + cosU1*cosU2*cosLambda;
839 	        var sigma = Math.atan2(sinSigma, cosSigma);
840 	        var alpha = Math.asin(cosU1 * cosU2 * sinLambda / sinSigma);
841 	        var cosSqAlpha = Math.cos(alpha) * Math.cos(alpha);
842 	        var cos2SigmaM = cosSigma - 2*sinU1*sinU2/cosSqAlpha;
843 	        var C = f/16*cosSqAlpha*(4+f*(4-3*cosSqAlpha));
844 	        lambdaP = lambda;
845 	        lambda = L + (1-C) * f * Math.sin(alpha) *
846 	        (sigma + C*sinSigma*(cos2SigmaM+C*cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)));
847 	    }
848 	    if (iterLimit==0) {
849 	        return NaN;  // formula failed to converge
850 	    }
851 	    var uSq = cosSqAlpha * (a*a - b*b) / (b*b);
852 	    var A = 1 + uSq/16384*(4096+uSq*(-768+uSq*(320-175*uSq)));
853 	    var B = uSq/1024 * (256+uSq*(-128+uSq*(74-47*uSq)));
854 	    var deltaSigma = B*sinSigma*(cos2SigmaM+B/4*(cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)-
855 	        B/6*cos2SigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2SigmaM*cos2SigmaM)));
856 	    var s = b*A*(sigma-deltaSigma);
857 	    var d = s.toFixed(3)/1000; // round to 1mm precision
858 	    return d;
859 	};
"""

from math import sin, cos, tan, atan, radians, pi, sqrt, atan2, asin

def vincenty(lat1,lon1, lat2, lon2):
    """returns distance in meters between any points earth"""
    
    a = 6378137
    b = 6356752.3142
    f = 1/298.257223563
    
    L = radians( lon2-lon1 )
    U1 = atan( (1-f) * tan( radians(lat1) ) )
    U2 = atan( (1-f) * tan( radians(lat2) ) )
    sinU1 = sin(U1); cosU1 = cos(U1)
    sinU2 = sin(U2); cosU2 = cos(U2)
    lmbda = L; lmbdaP = 2*pi
    
    iterLimit = 20
    
    while( iterLimit > 0 ):
        if abs(lmbda-lmbdaP) < 1E-12:
            break
        
        sinLambda = sin(lmbda); cosLambda = cos(lmbda)
        sinSigma = sqrt((cosU2*sinLambda) * (cosU2*sinLambda) + \
            (cosU1*sinU2-sinU1*cosU2*cosLambda) * (cosU1*sinU2-sinU1*cosU2*cosLambda))
        if sinSigma==0:
            return 0  # co-incident points

        cosSigma = sinU1*sinU2 + cosU1*cosU2*cosLambda
        sigma = atan2(sinSigma, cosSigma)
        alpha = asin(cosU1 * cosU2 * sinLambda / sinSigma)
        cosSqAlpha = cos(alpha) * cos(alpha)
        cos2SigmaM = cosSigma - 2*sinU1*sinU2/cosSqAlpha
        C = f/16*cosSqAlpha*(4+f*(4-3*cosSqAlpha))
        lmbdaP = lmbda;
        lmbda = L + (1-C) * f * sin(alpha) * \
            (sigma + C*sinSigma*(cos2SigmaM+C*cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)))
            
        iterLimit -= 1
            
    if iterLimit==0:
        return None  # formula failed to converge

    uSq = cosSqAlpha * (a*a - b*b) / (b*b);
    A = 1 + uSq/16384*(4096+uSq*(-768+uSq*(320-175*uSq)))
    B = uSq/1024 * (256+uSq*(-128+uSq*(74-47*uSq)))
    deltaSigma = B*sinSigma*(cos2SigmaM+B/4*(cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)-
            B/6*cos2SigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2SigmaM*cos2SigmaM)))
    s = b*A*(sigma-deltaSigma)
    
    return s
    
    
if __name__=='__main__':
    import time
    t0 = time.time()
    for i in range(10000):
        d = vincenty(47.68382,-122.376709, 47.683155,-122.376666)
    t1 = time.time()
    print( t1-t0 )
    print vincenty(47.68382,-122.376709, 47.68408,-122.375722)    
########NEW FILE########
__FILENAME__ = stress_test
from stress_utils import get_mem_usage
import sys
sys.path.append("..")
from graphserver.core import *

def grind(func, n, threshold=10):
    mperc, m0 = get_mem_usage()

    g = Graph()
    for i in xrange(n):
        func()
        
    mperc, m1 = get_mem_usage()
    
    print m0, m1
    assert m1 <= m0+threshold

import unittest
class StressTest(unittest.TestCase):

    def test_state_destroy(self):
        """State picks up after itself"""
        def func():
            s = State(1,0)
            s.destroy()
            
        grind(func, 1000000)
        
    def test_simple_vertex_destroy(self):
        """A simple Vertex object picks up after itself"""
        
        def func():
            s = Vertex("bogus")
            s.destroy()
            
        grind(func, 1000000)
        
    def test_street_destroy(self):
        """Street.destroy() completely destroys Street"""
        
        def func():
            s = Street("bogus", 1.1)
            s.destroy()
            
        grind(func, 1000000)
        
    def test_link_destroy(self):
        """Link.destroy() completely destroys Link"""
        
        def func():
            s = Link()
            s.destroy()
            
        grind(func, 1000000)
    
    def test_trip_board_destroy(self):
        """TripBoard.destroy() completely destroys TripBoard"""
        
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        def func():
            tb = TripBoard( "WKDY", sc, tz, 0 )
            tb.add_boarding( "1111", 50, 0 )
            tb.add_boarding( "2222", 100, 0 )
            tb.add_boarding( "3333", 200, 0 )
            
            tb.destroy()
            
        grind( func, 100000 )
        
    def test_crossing_destroy(self):
        def func():
            cr = Crossing()
            cr.destroy()
            
        grind( func, 100000 )
        
    def test_alight_destroy(self):
        tz = Timezone()                    
        cal = ServiceCalendar()            
                                       
        def func():                        
            al = TripAlight(0, cal,tz, 0)      
            al.destroy()                   
                                       
        grind( func, 100000 )           
        tz.destroy()                    
        cal.destroy()                   
        
    def test_minimal_graph_delete(self):
        """Graph.destroy() completely destroys minimal Graph"""
        
        def func():
            s = Graph()
            s.destroy()
            
        grind( func, 1000000 )
        
    def test_min_vertex_graph_delete(self):
        """Graph.destroy() completely destroys Graph with vertices"""
        
        def func():
            s = Graph()
            s.add_vertex("A")
            s.add_vertex("B")
            s.destroy()
            
        grind(func, 100000)
        
    def test_minimal_spt_delete(self):
        """ShortestPathTree.destroy() completely destroys the spt for a minimal tree"""
        
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("B")
        s.add_vertex("C")
        s.add_edge("A","B",Street("1", 1.1))
        s.add_edge("B","A",Street("1", 1.1))
        s.add_edge("B","C",Street("2", 2.2))
        
        def func():
            spt = s.shortest_path_tree("A", "C", State(1,0))
            spt.destroy()
            
        grind( func, 100000 )
        
    def test_shortest_path_grind(self):
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("B")
        s.add_vertex("C")
        s.add_edge("A","B",Street("1", 1.1))
        s.add_edge("B","A",Street("1", 1.1))
        s.add_edge("B","C",Street("2", 2.2))
        
        def func():
            spt = s.shortest_path_tree("A","C", State(1,0))
            sp = spt.path("C")
            spt.destroy()
            
        grind(func, 50000)

class WaitStressTest(unittest.TestCase):
    def test_wait_destroy(self):
        """Wait.destroy() completely destroys Wait"""
        
        tz = Timezone.generate( "America/Los_Angeles" )
        
        def func():
            s = Wait(60, tz)
            s.destroy()
            
        grind(func, 1000000)

from random import randint
def random_graph(nvertices, nedges):
    """generates random graph. useful for stress testing"""
    
    vertices = [str(x) for x in range(nvertices)]
    
    g = Graph()
    
    for vertex in vertices:
        g.add_vertex(vertex)
        
    for i in range(nedges):
        a = vertices[ randint( 0, len(vertices)-1 ) ]
        b = a
        while b==a:
            b = vertices[ randint( 0, len(vertices)-1 ) ]
            
        g.add_edge(a,b,Link())
    
    return g
    
if __name__=='__main__':
    tl = unittest.TestLoader()
    
    testables = [\
                 StressTest,
                 WaitStressTest,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = stress_utils
import os
import sys

def get_mem_usage():
    """returns percentage and vsz mem usage of this script"""
    pid = os.getpid()
    psout = os.popen( "ps u -p %s"%pid ).read()
    
    parsed_psout = psout.split("\n")[1].split()
    
    return float(parsed_psout[3]), int( parsed_psout[4] )
########NEW FILE########
__FILENAME__ = test_ch
import unittest
from graphserver.core import *

class TestCH( unittest.TestCase ):
    def test_basic(self):
        ch = ContractionHierarchy()
        assert ch.soul
        
        assert ch.upgraph.soul
        assert ch.downgraph.soul

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCH)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_combination
import unittest
from graphserver.core import *

class TestCombination(unittest.TestCase):
    def test_basic(self):
        s1 = Street( "A", 1 )
        c0 = Combination( 1 )
        c0.add( s1 )
        
        assert c0.__class__ == Combination
        assert c0.get( -1 ) == None
        assert c0.get( 0 ).__class__ == Street
        assert c0.get( 1 ) == None
        
        assert c0.walk( State(0,0), WalkOptions() ).weight == 0
        
        s2 = Street( "B", 2 )
        c1 = Combination( 2 )
        c1.add( s1 )
        c1.add( s2 )
        
        assert c1.__class__ == Combination
        assert c1.get( -1 ) == None
        assert c1.get( 0 ).__class__ == Street
        assert c1.get( 0 ).name == "A"
        assert c1.get( 1 ).__class__ == Street
        assert c1.get( 1 ).name == "B"
        assert c1.get( 2 ) == None
        
        assert c1.walk( State(0,0), WalkOptions() ).weight == 0
        assert c1.walk_back( State(0, 100), WalkOptions() ).weight == 0
        
        s3 = Street( "C", 3 )
        
        c2 = Combination( 3 )
        c2.add( s1 )
        c2.add( s2 )
        c2.add( s3 )
        
        assert c2.walk( State(0,0), WalkOptions() ).weight == 0
        assert c2.walk_back( State(0,100), WalkOptions() ).weight == 0
        
        c3 = Combination( 2 )
        c3.add( c1 )
        c3.add( s3 )
        
        assert c3.walk( State(0,0), WalkOptions() ).weight == 0
        assert c3.walk_back( State(0,100), WalkOptions() ).weight == 0
        
        s1.destroy()
        s2.destroy()
        s3.destroy()
        c1.destroy()
        c2.destroy()
        

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCombination)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_crossing
import unittest
from graphserver.core import *

class TestCrossing(unittest.TestCase):
    
    def test_basic(self):
        
        cr = Crossing()
        
        assert cr
        assert cr.soul
        assert cr.size == 0
        assert cr.get_crossing_time( "1" ) == None
        assert cr.get_crossing( 0 ) == None
        
    def test_add_crossing(self):
        cr = Crossing()
        
        cr.add_crossing_time( "1", 10 )
        
        assert cr.size == 1
        assert cr.get_crossing_time( "1" ) == 10
        assert cr.get_crossing( 0 ) == ("1", 10)
        
        cr.add_crossing_time( "2", 20 )
        cr.add_crossing_time( "3", 30 )
        
        assert cr.size == 3
        assert cr.get_crossing_time( "1" ) == 10
        assert cr.get_crossing_time( "2" ) == 20
        
        assert cr.get_crossing( 0 ) == ('1', 10)
        assert cr.get_crossing( 1 ) == ('2', 20)
        assert cr.get_crossing( 2 ) == ('3', 30)
        
    def test_pickle_and_reconstitute(self):
        cr = Crossing()
        
        cr.add_crossing_time( "1", 10 )
        cr.add_crossing_time( "2", 20 )
        cr.add_crossing_time( "3", 30 )
        
        state = cr.__getstate__()
        
        cr2 = Crossing.reconstitute(state, None)
        
        assert cr2.size==3
        assert cr.get_crossing( 0 ) == ('1', 10)
        assert cr.get_crossing( 1 ) == ('2', 20)
        assert cr.get_crossing( 2 ) == ('3', 30)
        
    def test_walk(self):
        
        cr = Crossing()
        cr.add_crossing_time("1", 10)
        
        s = State(1, 0)
        ret = cr.walk(s,WalkOptions())
        
        # state has no trip_id, shouldn't evaluate at all
        assert ret == None
        
        s.dangerous_set_trip_id( "1" )
        s1 = cr.walk(s,WalkOptions())
        assert s1.time == 10
        assert s1.weight == 10
        
    def test_walk_back(self):
        
        cr = Crossing()
        cr.add_crossing_time("1", 10)
        
        s = State(1, 10)
        ret = cr.walk_back(s, WalkOptions())
        assert ret == None
        
        s.dangerous_set_trip_id( "1" )
        s1 = cr.walk_back(s, WalkOptions())
        assert s1.time == 0
        assert s1.weight == 10
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCrossing)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_edge
import unittest
from graphserver.core import *

class TestEdge(unittest.TestCase):
    def test_basic(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        assert e1.enabled == True
        
        e1.enabled = False
        assert e1.enabled == False
        
    def test_walk(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        assert e1.walk( State(0,0), wo ) is not None
        assert e1.walk( State(0,0), wo ).weight == 10
        
    def test_disable(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
    
        assert e1.walk( State(0,0), wo ) is not None
        assert e1.walk( State(0,0), wo ).weight == 10
        
        e1.enabled = False
        
        assert e1.walk( State(0,0), WalkOptions() ) == None
        
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        heavy = Street( "Heavy", 100 )
        light = Street( "Light", 1 )
        gg.add_edge( "A", "B", heavy )
        gg.add_edge( "A", "B", light )
        
        assert gg.shortest_path_tree( "A", "B", State(0,0), WalkOptions() ).path("B")[1][0].payload.name == "Light"
        
        lightedge = gg.get_vertex("A").outgoing[0]
        lightedge.enabled = False
        
        assert gg.shortest_path_tree( "A", "B", State(0,0), WalkOptions() ).path("B")[1][0].payload.name == "Heavy"
        
    def test_disable_vertex(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_vertex( "D" )
        gg.add_edge( "A", "B", Street( "atob", 1 ) )
        gg.add_edge( "B", "D", Street( "btod", 1 ) )
        gg.add_edge( "A", "C", Street( "atoc", 1 ) )
        gg.add_edge( "C", "D", Street( "ctod", 1 ) )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == True
            
        gg.set_vertex_enabled( "B", False )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == False
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == False
            
        for edge in gg.get_vertex("C").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("C").incoming:
            assert edge.enabled == True
            
        gg.set_vertex_enabled( "B", True )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == True
            
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestEdge)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_egress
from graphserver.core import *
import unittest

class TestEgress(unittest.TestCase):
    def test_street(self):
        s = Egress("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<Egress name='mystreet' length='1.100000' />"
        
    def test_destroy(self):
        s = Egress("mystreet", 1.1)
        s.destroy()
        
        assert s.soul==None
        
    def test_street_big_length(self):
        s = Egress("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Egress name='longstreet' length='240000.000000' />"
        
    def test_walk(self):
        s = Egress("longstreet", 10)
        wo = WalkOptions()
        wo.walking_reluctance = 1
        after = s.walk(State(0,0),wo)
        wo.destroy()
        self.assertEqual( after.time , 9 )
        self.assertEqual( after.weight , 9 )
        self.assertEqual( after.dist_walked , 10 )
        self.assertEqual( after.prev_edge.__class__ , Egress )
        self.assertEqual( after.prev_edge.name , "longstreet" )
        self.assertEqual( after.num_agencies , 0 )
        
    def test_walk_back(self):
        s = Egress("longstreet", 10)
        
        before = s.walk_back(State(0,100),WalkOptions())
        self.assertEqual( before.time , 100 - (9) )
        self.assertEqual( before.weight , 9 )
        self.assertEqual( before.dist_walked , 10.0 )
        self.assertEqual( before.prev_edge.type , 12 )
        self.assertEqual( before.prev_edge.name , "longstreet" )
        self.assertEqual( before.num_agencies , 0 )
        
    def test_getstate(self):
        s = Egress("longstreet", 2)
        
        assert s.__getstate__() == ('longstreet', 2)
        
    def test_graph(self):
        g = Graph()
        g.add_vertex("E")
        g.add_vertex("S")
        g.add_edge("E", "S", Egress("E2S",10))
        
        spt = g.shortest_path_tree("E", "S", State(0,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("S").state.dist_walked==10

        spt.destroy()
        g.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestEgress)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_elapsetime
from graphserver.core import *
import unittest

class TestElapseTime(unittest.TestCase):
    def test_new(self):
        s = ElapseTime(120)
        assert s.seconds == 120
        assert s.to_xml() == "<ElapseTime seconds='120' />"
        
    def test_destroy(self):
        s = ElapseTime(1)
        s.destroy()
        
        assert s.soul==None
        
    def test_big_seconds(self):
        s = ElapseTime(240000)
        assert s.seconds == 240000

        assert s.to_xml() == "<ElapseTime seconds='240000' />"
        
    def test_walk(self):
        s = ElapseTime(2)
        
        after = s.walk(State(0,0),WalkOptions())
        assert after.time == 2
        assert after.weight == 2
        assert after.dist_walked == 0
        assert after.prev_edge.type == 14
        assert after.num_agencies == 0
        
    def test_walk_back(self):
        s = ElapseTime(2)
        
        before = s.walk_back(State(0,100),WalkOptions())
        
        assert before.time == 98
        assert before.weight == 2
        assert before.dist_walked == 0
        assert before.prev_edge.type == 14
        assert before.num_agencies == 0
        
    def test_getstate(self):
        s = ElapseTime(2)
        
        assert s.__getstate__() == 2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestElapseTime)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_graph
import unittest
from graphserver.core import *
import time


class TestGraph(unittest.TestCase):
    
    def test_basic(self):
        g = Graph()
        assert g
        
        g.destroy()
        
    def test_empty_graph(self):
        g = Graph()
        assert g.vertices == []
        
        g.destroy()
        
    def test_add_vertex(self):
        g = Graph()
        v = g.add_vertex("home")
        assert v.label == "home"
        
        g.destroy()
        
    def test_remove_vertex(self):
        g = Graph()
        g.add_vertex( "A" )
        g.get_vertex( "A" ).label == "A"
        g.remove_vertex( "A" )
        assert g.get_vertex( "A" ) == None
        
    def test_double_add_vertex(self):
        g = Graph()
        v = g.add_vertex("double")
        assert v.label == "double"
        assert g.size == 1
        v = g.add_vertex("double")
        assert g.size == 1
        assert v.label == "double"
        
        g.destroy()
        
    def test_get_vertex(self):
        g = Graph()
        
        g.add_vertex("home")
        v = g.get_vertex("home")
        assert v.label == "home"
        v = g.get_vertex("bogus")
        assert v == None
        
        g.destroy()
        
    def test_add_edge(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        assert e
        assert e.from_v.label == "home"
        assert e.to_v.label == "work"
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/></Edge>"
        
        g.destroy()
    
    def test_add_edge_effects_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert fromv.degree_out==1
        assert tov.degree_in==1
        
        g.destroy()
    
    def test_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        assert g.vertices
        assert len(g.vertices)==2
        assert g.vertices[0].label == 'home'
        
        g.destroy()
    
    def test_shortest_path_tree(self):
        g = Graph()
        
        # add two vertices, home and work
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        # add two street edges, one going in each direction
        g.add_edge("home", "work", Street( "helloworld", 10 ))
        g.add_edge("work", "home", Street("backwards",10) )
        
        # get the shortest path tree
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("home").state.weight==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        self.assertTrue( spt.get_vertex("work").state.weight > 0 )
        
        spt.destroy()
        g.destroy()
        
    def test_bogus_origin(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        self.assertRaises(Exception, g.shortest_path_tree, "bogus", "work", State(g.numagencies,0), WalkOptions())
        
        self.assertRaises(Exception, g.shortest_path_tree_retro, "home", "bogus", State(g.numagencies,0), WalkOptions())
        
    def test_spt_retro(self):
        
        g = Graph()
        
        # add two vertices
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        # hook them to each other
        g.add_edge("home", "work", Street( "helloworld", 100 ))
        g.add_edge("work", "home", Street("backwards",100 ) )
        
        # find the path from work to home to arrive at work at 100
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,100), WalkOptions())
        
        assert spt
        assert spt.__class__ == ShortestPathTree
        self.assertEqual( spt.get_vertex("home").degree_out , 0 )
        self.assertEqual( spt.get_vertex("home").degree_in , 1 )
        self.assertTrue( spt.get_vertex("home").state.weight > 0 )
        self.assertEqual( spt.get_vertex("work").degree_in , 0 )
        self.assertEqual( spt.get_vertex("work").degree_out , 1 )
        self.assertEqual( spt.get_vertex("work").state.weight , 0 )
        
        spt.destroy()
        g.destroy()
        
    def test_spt_retro_chain(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        
        g.add_edge( "A", "B", Street( "AB", 1 ) )
        g.add_edge( "B", "C", Street( "BC", 1 ) )
        g.add_edge( "C", "D", Street( "CD", 1 ) )
        
        spt = g.shortest_path_tree_retro( "A", "D", State(g.numagencies,1000), WalkOptions() )
        
        assert spt.get_vertex( "A" ).state.time
        
        spt.destroy()
        
        
    def test_shortst_path_tree_link(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("work").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
        spt.destroy()
        g.destroy()
        
    def test_spt_link_retro(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("work").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
        
    def test_walk_longstreet(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 24000 )
        e = g.add_edge("home", "work", s)
        
        wo = WalkOptions()
        sprime = e.walk(State(g.numagencies,0), wo)
        
        self.assertTrue( sprime.time > 0 )
        self.assertTrue( sprime.weight > 0 )
        self.assertEqual( sprime.dist_walked, 24000.0 )
        self.assertEqual( sprime.num_transfers, 0 )
        
        wo.destroy()

        g.destroy()
        
    def xtestx_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0))
        
        assert spt.get_vertex("home").degree_out == 1
        
        spt.destroy()
        g.destroy()
            
    def test_shortest_path_tree_retro(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
    
    def test_shortest_path(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies), WalkOptions())
        sp = spt.path("work")
        
        assert sp
        
    def xtestx_shortest_path_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State(g.numagencies))
        
        assert sp
        
    def test_add_link(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = g.add_edge("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
        g.destroy()
        
    def test_basic(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        g.add_vertex( "E" )
        g.add_edge( "A", "B", Street("atob", 10) )
        g.add_edge( "A", "C", Street("atoc", 10) )
        g.add_edge( "C", "D", Street("ctod", 10) )
        g.add_edge( "B", "D", Street("btod", 10) )
        g.add_edge( "D", "E", Street("btoe", 10) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
        spt = g.shortest_path_tree( "A", None, State(1,0), wo )

    def test_hop_limit(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_vertex( "D" )
        gg.add_vertex( "E" )
        gg.add_edge( "A", "B", Street( "AB", 1 ) )
        gg.add_edge( "B", "C", Street( "BC", 1 ) )
        gg.add_edge( "C", "D", Street( "CD", 1 ) )
        gg.add_edge( "D", "E", Street( "DE", 1 ) )
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions() )
        assert spt.get_vertex( "E" ).state.weight == 0
        spt.destroy()
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions(), hoplimit=1 )
        assert spt.get_vertex("A") != None
        assert spt.get_vertex("B") != None
        assert spt.get_vertex("C") == None
        assert spt.get_vertex("D") == None
        assert spt.get_vertex("E") == None
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions(), hoplimit=3 )
        assert spt.get_vertex("A") != None
        assert spt.get_vertex("B") != None
        assert spt.get_vertex("C") != None
        assert spt.get_vertex("D") != None
        assert spt.get_vertex("E") == None
        
    def test_traverse(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_edge( "A", "B", Street("AB", 1) )
        gg.add_edge( "A", "C", Street("AC", 1) )
        
        vv = gg.get_vertex( "A" )
        assert [ee.payload.name for ee in vv.outgoing] == ["AC", "AB"]
            
    def test_ch(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        ab = gg.add_edge( "A", "B", Street( "AB", 1 ) )
        ba = gg.add_edge( "B", "A", Street( "BA", 1 ) )
        
        absoul = gg.get_vertex("A").outgoing[0].payload.soul
        basoul = gg.get_vertex("B").outgoing[0].payload.soul
        
        ch = gg.get_contraction_hierarchies( WalkOptions() )
        
        assert ch.upgraph.get_vertex("A").outgoing[0].payload.soul == absoul
        assert ch.downgraph.get_vertex("B").outgoing[0].payload.soul == basoul

if __name__ == '__main__':    
    unittest.main()

########NEW FILE########
__FILENAME__ = test_graph_database
import unittest
from graphserver.core import Graph, Link, Street, WalkOptions, Combination
from graphserver.graphdb import GraphDatabase
import os

def glen(gen):
    return len(list(gen))

class TestGraphDatabase(unittest.TestCase):
    def test_basic(self):
        g = Graph()
        g.add_vertex("A")
        g.add_vertex("B")
        g.add_edge("A", "B", Link())
        g.add_edge("A", "B", Street("foo", 20.0))
        gdb_file = os.path.dirname(__file__) + "unit_test.db"
        if os.path.exists(gdb_file):
            os.remove(gdb_file)        
        gdb = GraphDatabase(gdb_file)
        gdb.populate(g)
        
        list(gdb.execute("select * from resources"))
        assert "A" in list(gdb.all_vertex_labels())
        assert "B" in list(gdb.all_vertex_labels())
        assert glen(gdb.all_edges()) == 2
        assert glen(gdb.all_outgoing("A")) == 2
        assert glen(gdb.all_outgoing("B")) == 0
        assert glen(gdb.all_incoming("A")) == 0
        assert glen(gdb.all_incoming("B")) == 2
        assert glen(gdb.resources()) == 0
        assert gdb.num_vertices() == 2
        assert gdb.num_edges() == 2
        
        g.destroy()
        g = gdb.incarnate()
        
        list(gdb.execute("select * from resources"))
        assert "A" in list(gdb.all_vertex_labels())
        assert "B" in list(gdb.all_vertex_labels())
        assert glen(gdb.all_edges()) == 2
        assert glen(gdb.all_outgoing("A")) == 2
        assert glen(gdb.all_outgoing("B")) == 0
        assert glen(gdb.all_incoming("A")) == 0
        assert glen(gdb.all_incoming("B")) == 2
        assert glen(gdb.resources()) == 0
        assert gdb.num_vertices() == 2
        assert gdb.num_edges() == 2
        
        os.remove( gdb_file )

    def test_ch(self):
        g = Graph()

	g.add_vertex( "A" )
	g.add_vertex( "B" )
        g.add_vertex( "C" )
	g.add_edge( "A", "B", Street( "foo", 10 ) )
	g.add_edge( "B", "C", Street( "bar", 10 ) )
	g.add_edge( "C", "A", Street( "baz", 10 ) )

        wo = WalkOptions()
	ch = g.get_contraction_hierarchies(wo)

        gdb_file = os.path.dirname(__file__) + "unit_test.db"
        gdb = GraphDatabase( gdb_file )
	gdb.populate( ch.upgraph )

	laz = gdb.incarnate()

        combo = laz.edges[1]
	self.assertEqual( combo.payload.get(0).name, "baz" )
	self.assertEqual( combo.payload.get(1).name, "foo" )

	os.remove( gdb_file )
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestGraphDatabase)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_headway
from graphserver.core import *
import unittest

class TestHeadway(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 0, 1*3600*24, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        assert headway.begin_time == 0
        assert headway.end_time == 1*3600*24
        assert headway.wait_period == 60
        assert headway.transit == 120
        assert headway.trip_id == "HEADWAY"
        assert headway.calendar.soul == sc.soul
        assert headway.timezone.soul == tz.soul
        assert headway.agency == 0
        assert headway.int_service_id == 0
        assert headway.service_id == "WKDY"
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 3600, 2*3600, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = headway.walk( s,WalkOptions() )
        assert ret == None
        
        #before headway
        s = State(1, 0)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 3720
        assert ret.weight == 3720
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #right at beginning of headway
        s = State(1, 3600)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 3720
        assert ret.weight == 120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #in the middle of the headway
        s = State(1, 4000)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 4000+60+120
        assert ret.weight == 60+120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #the last second of the headway
        s = State(1, 2*3600)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 2*3600+60+120
        assert ret.weight == 60+120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #no-transfer
        s = State(1, 4000)
        s.prev_edge = headway = Headway( 3600, 2*3600, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 4000+120
        assert ret.weight == 120
        assert ret.num_transfers == 0
        assert ret.prev_edge.type == 7
        assert ret.prev_edge.trip_id == "HEADWAY"
        
    def test_getstate(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 0, 1*3600*24, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        assert headway.__getstate__() == (0, 1*3600*24, 60, 120, "HEADWAY", sc.soul, tz.soul, 0, "WKDY")
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadway)
    unittest.TextTestRunner(verbosity=2).run(suite)
    
########NEW FILE########
__FILENAME__ = test_headwayalight
import unittest
from graphserver.core import *

class TestHeadwayAlight(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "hwtrip1", 0, 1000, 100)
        
        assert ha.calendar.soul == sc.soul
        assert ha.timezone.soul == tz.soul
        
        assert ha.agency == 0
        assert ha.int_service_id == 0
        
        assert ha.trip_id == "hwtrip1"
        
        assert ha.start_time == 0
        assert ha.end_time == 1000
        assert ha.headway_secs == 100
        
        ha.destroy()
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        # 200 after end of headway
        s0 = State(1,1200)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 1000
        assert s1.weight == 201
        
        # at very end of the headway
        s0 = State(1,1000)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 1000
        assert s1.weight == 1
        
        # in the middle of headway period
        s0 = State(1, 500)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 500
        assert s1.weight == 1
        
        # at the very beginning of the headway period
        s0 = State(1, 200)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 200
        assert s1.weight == 1
        
        # before beginning of headway period
        s0 = State(1, 199)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1 == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = ha.walk(s0, WalkOptions())
        assert s1.trip_id == None
        
    def test_headwayalight_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        ha = HeadwayAlight( "WKDY", sc, tz, 0, "owl", 23*3600, 26*3600, 100 )
        
        # just past the end
        s0 = State(1, 26*3600+100)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        # right at the end
        s0 = State(1, 26*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        # in the middle, over midnight
        s0 = State(1, 25*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        # in the middle, at midnight
        s0 = State(1, 24*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        #before midnight, at the beginning
        s0 = State(1, 23*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 23*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600-1)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1 == None
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadwayAlight)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_headwayboard
import unittest
from graphserver.core import *

class TestHeadwayBoard(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "hwtrip1", 0, 1000, 100)
        
        assert hb.calendar.soul == sc.soul
        assert hb.timezone.soul == tz.soul
        
        assert hb.agency == 0
        assert hb.int_service_id == 0
        
        assert hb.trip_id == "hwtrip1"
        
        assert hb.start_time == 0
        assert hb.end_time == 1000
        assert hb.headway_secs == 100
        
        hb.destroy()
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 250
        assert s1.weight == 251
        
        s0 = State(1,200)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 250
        assert s1.weight == 51
        
        s0 = State(1, 500)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 550
        assert s1.weight == 51
        
        s0 = State(1, 1000)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 1050
        assert s1.weight == 51
        
        s0 = State(1, 1001)
        s1 = hb.walk(s0,WalkOptions())
        assert s1 == None
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = hb.walk(s0, WalkOptions())
        s2 = hb.walk_back(s1, WalkOptions())
        assert s2.trip_id == None
        
    def test_tripboard_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        hb = HeadwayBoard( "WKDY", sc, tz, 0, "owl", 23*3600, 26*3600, 100 )
        
        s0 = State(1, 0)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 82901
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 25*3600+100
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 26*3600+100
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = hb.walk(s0,WalkOptions())
        assert s1 == None
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadwayBoard)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_link
from graphserver.core import Link, State, WalkOptions
import unittest

class TestLink(unittest.TestCase):
    def link_test(self):
        l = Link()
        assert l
        assert str(l)=="<Link name='LINK'/>"
        
    def test_destroy(self):
        l = Link()
        l.destroy()
        
        assert l.soul==None
        
    def test_name(self):
        l = Link()
        assert l.name == "LINK"
        
    def test_walk(self):
        l = Link()
        
        after = l.walk(State(1,0), WalkOptions())
        
        assert after.time==0
        assert after.weight==0
        assert after.dist_walked==0
        assert after.prev_edge.type == 3
        assert after.prev_edge.name == "LINK"
        assert after.num_agencies == 1
        
    def test_walk_back(self):
        l = Link()
        
        before = l.walk_back(State(1,0), WalkOptions())
        
        assert before.time == 0
        assert before.weight == 0
        assert before.dist_walked == 0.0
        assert before.prev_edge.type == 3
        assert before.prev_edge.name == "LINK"
        assert before.num_agencies == 1
        
    def test_getstate(self):
        l = Link()
        assert l.__getstate__() == tuple([])
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestLink)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_listnode
from graphserver.core import *
import unittest

class TestListNode(unittest.TestCase):
    def test_list_node(self):
        l = ListNode()
                
        assert l
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestListNode)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_path
from graphserver.core import Vertex, Edge, Link, Street, Path
import unittest
from graphserver.gsdll import lgs
from ctypes import addressof

class TestPathCreate(unittest.TestCase):
    def test_path_new(self):
        """Create a path object without crashing"""
        path = Path( Vertex("A") )
        
        self.assertTrue( path )
        
    def test_path_empty(self):
        """Path is empty right after first created"""
        pp = Path( Vertex("A") )
        
        self.assertEqual( pp.num_elements, 0 )
        
class TestPathSize(unittest.TestCase):
    def setUp(self):
        self.aa = Vertex("AA")
        self.path = Path( self.aa )
        
    def test_zero(self):
        """getSize returns zero on an empty path"""
        self.assertEquals( self.path.num_elements, 0 )
    
    def test_one(self):
        """getSize returns one after one entry"""
        
        bb = Vertex("BB")
        ee = Edge(self.aa, bb, Link())
        
        self.path.addSegment( bb, ee )
        
        self.assertEqual( self.path.num_elements, 1 )
        
    def test_ten(self):
        """getSize returns ten after ten entries"""
        
        for i in range(10):
            aa = Vertex("AA")
            bb = Vertex("BB")
            payload = Link()
            self.path.addSegment( bb, Edge(aa, bb, payload) )
            
        self.assertEquals( self.path.num_elements, 10 )
        
class TestAddAndGetSegments(unittest.TestCase):
    def setUp(self):
        self.aa = Vertex("A")
        self.bb = Vertex("B")
        self.ep = Link()
        self.path = Path(self.aa)
        
    def test_none(self):
        """behave appropriately when asking for an out-of-bounds index"""
        
        # test out of bounds values
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getVertex, 1 )
        self.assertRaises( IndexError, self.path.getVertex, 10 )
        
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        self.assertRaises( IndexError, self.path.getEdge, 0 )
        self.assertRaises( IndexError, self.path.getEdge, 1 )
        self.assertRaises( IndexError, self.path.getEdge, 10 )
        
        # if you don't add any segments, there's still a single vertex in the path
        self.assertEquals( self.path.getVertex( 0 ).soul, self.aa.soul )
        
    def test_one(self):
        """get a vertex, edge after adding a single segment"""
        
        ee = Edge(self.aa, self.bb, self.ep)
        self.path.addSegment( self.bb, ee )
        
        # out of bounds
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        
        # vertices in bounds
        self.assertEqual( self.path.getVertex(0).soul, self.aa.soul )
        self.assertEqual( self.path.getVertex(1).soul, self.bb.soul )
        
        # edges in bounds
        self.assertEqual( self.path.getEdge(0).soul, ee.soul )
        
        # out of bounds again
        self.assertRaises( IndexError, self.path.getVertex, 2 )
        self.assertRaises( IndexError, self.path.getEdge, 1 )
        
    def test_two(self):
        """get a vertex, edge after adding two segments"""
        
        ee1 = Edge(self.aa, self.bb, Link())
        ee2 = Edge(self.bb, self.aa, Link())
        self.path.addSegment( self.bb, ee1 )
        self.path.addSegment( self.aa, ee2 )
        
        # out of bounds
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        
        # vertices in bounds
        self.assertEqual( self.path.getVertex(0).soul, self.aa.soul )
        self.assertEqual( self.path.getVertex(1).soul, self.bb.soul )
        self.assertEqual( self.path.getVertex(2).soul, self.aa.soul )
        
        # edges in bounds
        self.assertEqual( self.path.getEdge(0).soul, ee1.soul )
        self.assertEqual( self.path.getEdge(1).soul, ee2.soul )
        
        # out of bounds again
        self.assertRaises( IndexError, self.path.getVertex, 3 )
        self.assertRaises( IndexError, self.path.getEdge, 2 )
        
    def test_expand(self):
        """vertices gettable after resizing"""
        
        # the path length right before a vector expansion
        pathlen = 50
        
        # make a bunch of fake segments
        segments = []
        for i in range(pathlen):
            vv = Vertex(str(i))
            ee = Edge( vv, vv, Link() )
            segments.append( (vv, ee) )
        
        # add those segments to the path
        for vv, ee in segments:
            self.path.addSegment( vv, ee ) 
            
        # check that they're alright
        # check the odd-duck vertex
        self.assertEqual( self.path.getVertex(0).label, "A" )
        
        # check the bunch of fake segments added
        for i in range(1, pathlen+1):
            self.assertEqual( i-1, int(self.path.getVertex(i).label) )
            
        #
        # getting towards the real test - add a segment after the vectors have
        # been expanded
        #
        
        # add it
        vv = Vertex("B")
        ee = Edge(vv, vv, Link())
        self.path.addSegment( vv, ee )
        
        # get it
        self.assertEqual( self.path.getVertex( 51 ).label, "B" )
        
        
if __name__ == '__main__':

    unittest.main()
########NEW FILE########
__FILENAME__ = test_pypayload
from graphserver.core import *
import unittest
import StringIO
import sys

class TestPyPayload(unittest.TestCase):
    def _minimal_graph(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        return g
    
    def test_basic(self):
        p = NoOpPyPayload(1.1)
        
    def test_cast(self):
        g = self._minimal_graph()
        e = NoOpPyPayload(1.2)
        
        ed = g.add_edge( "Seattle", "Portland", e )
        assert e == ed.payload
        ep = ed.payload # uses EdgePayload.from_pointer internally.
        assert e == ep
        assert ep.num == 1.2
    
        
    
    def test_walk(self):
        class IncTimePayload(GenericPyPayload):
            def walk_impl(self, state, walkopts):
                state.time = state.time + 10
                state.weight = 5
                return state
            
            def walk_back_impl(self, state, walkopts):
                state.time = state.time - 10
                state.weight = 0
                return state
            
        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", IncTimePayload())
        assert(isinstance(ed.payload,IncTimePayload))
        s = State(1,1)
        assert s.time == 1
        s1 = ed.walk(s, WalkOptions())
        assert s1
        assert s.time == 1
        assert s1.soul != s.soul
        assert s1.time == 11
        assert s1.weight == 5
        s2 = ed.walk_back(s1, WalkOptions())
        assert s2
        assert s2.time == 1
        assert s2.weight == 0
        g.destroy()
        
    def test_failures(self):
        class ExceptionRaiser(GenericPyPayload):
            def walk_bad_stuff(self, state, walkopts):
                raise Exception("I am designed to fail.")
            walk_impl = walk_bad_stuff
            walk_back_impl = walk_bad_stuff

        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", ExceptionRaiser())
                
        # save stdout so we can set it back the way we found it
        stderrsave = sys.stderr
        
        # get a string-file to catch things placed into stdout
        stderr_catcher = StringIO.StringIO()
        
        sys.stderr = stderr_catcher
                
        # this will barf into stdout
        ed.walk(State(1,0), WalkOptions())
        
        # the last line of the exception traceback just blurted out should be ...
        stderr_catcher.seek(0)
        self.assertEqual( stderr_catcher.read().split("\n")[-2] , "Exception: I am designed to fail." )

        # set up a new buffer to catch a traceback
        stderr_catcher = StringIO.StringIO()
        sys.stderr = stderr_catcher
        
        # blurt into it
        ed.walk_back(State(1,0), WalkOptions())
        
        # check that the last line of the traceback looks like we expect
        stderr_catcher.seek(0)
        self.assertEqual( stderr_catcher.read().split("\n")[-2] , "Exception: I am designed to fail." )
        
        g.destroy()
        
        sys.stderr = stderrsave
        
    def test_basic_graph(self):
        class MovingWalkway(GenericPyPayload):
            def walk_impl(self, state, walkopts):
                state.time = state.time + 10
                state.weight = 5
                return state
            
            def walk_back_impl(self, state, walkopts):
                state.time = state.time - 10
                state.weight = 0
                return state
        
        g = self._minimal_graph()
        g.add_edge( "Seattle", "Portland", MovingWalkway())
        spt = g.shortest_path_tree("Seattle", "Portland", State(0,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("Portland").state.weight==5
        assert spt.get_vertex("Portland").state.time==10

        spt.destroy()
        g.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestPyPayload)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_servicecalendar
from graphserver.core import *
import unittest
import pickle

class TestServiceCalendar(unittest.TestCase):
    def test_basic(self):
        c = ServiceCalendar()
        assert( c.head == None )
        
        assert( c.period_of_or_before(0) == None )
        assert( c.period_of_or_after(0) == None )
        
    def test_get_service_id_int(self):
        c = ServiceCalendar()
        assert c.get_service_id_int( "A" ) == 0
        assert c.get_service_id_int( "A" ) == 0
        assert c.get_service_id_int( "B" ) == 1
        try:
            c.get_service_id_int( 1 )
            assert False
        except TypeError:
            pass
        
        c.add_period(0,1000,["B"])
        
        import pickle
        from cStringIO import StringIO
        src = StringIO()
        p = pickle.Pickler(src)        
        
        p.dump(c)
        datastream = src.getvalue()
        dst = StringIO(datastream)

        upc = pickle.Unpickler(dst).load()
        print c.expound("America/Los_Angeles")
        print upc.expound("America/Los_Angeles")
        assert c.expound("America/Los_Angeles") == upc.expound("America/Los_Angeles"), upc
        for _c in [c, upc]:
            assert _c.get_service_id_string( -1 ) == None
            assert _c.get_service_id_string( 0 ) == "A", _c.to_xml()
            assert _c.get_service_id_string( 1 ) == "B"
            assert _c.get_service_id_string( 2 ) == None
            try:
                _c.get_service_id_string( "A" )
                assert False
            except TypeError:
                pass
        
    def test_single(self):
        c = ServiceCalendar()
        c.add_period( 0,1000,["A","B","C"] )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [0,1,2]
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(500).begin_time==0
        assert c.period_of_or_before(1000).begin_time==0
        assert c.period_of_or_before(50000).begin_time==0
        
        assert c.period_of_or_after(-1).begin_time==0
        assert c.period_of_or_after(0).begin_time==0
        assert c.period_of_or_after(500).begin_time==0
        assert c.period_of_or_after(1000)==None
        assert c.period_of_or_after(1001) == None
        
    def test_overlap_a_little(self):
        
        c = ServiceCalendar()
        c.add_period( 0, 1000, ["A"] )
        c.add_period( 1000, 2000, ["B"] )
        
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(999).begin_time==0
        assert c.period_of_or_before(1000).begin_time==1000
        
        c = ServiceCalendar()
        c.add_period(1000,2000,["B"])
        c.add_period(0,1000,["A"])
        
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(999).begin_time==0
        assert c.period_of_or_before(1000).begin_time==1000
        
        #--==--
    
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['A'])
        sc.add_period(1*3600*24,2*3600*24, ['B'])
        
        assert sc.period_of_or_after( 1*3600*24 ).begin_time == 86400
        
        
    def test_multiple(self):
        c = ServiceCalendar()
        # out of order
        c.add_period( 1001,2000,["C","D","E"] )
        c.add_period( 0,1000,["A","B","C"] )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [3,4,0]
        
        assert c.head.previous == None
        assert c.head.next.begin_time == 1001
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time == 0
        assert c.period_of_or_before(1000).begin_time == 0
        assert c.period_of_or_before(1001).begin_time == 1001
        assert c.period_of_or_before(2000).begin_time == 1001
        assert c.period_of_or_before(2001).begin_time == 1001
        
        assert c.period_of_or_after(-1).begin_time == 0
        assert c.period_of_or_after(0).begin_time == 0
        assert c.period_of_or_after(1000).begin_time == 1001
        assert c.period_of_or_after(1001).begin_time == 1001
        assert c.period_of_or_after(2000) == None
        assert c.period_of_or_after(2001) == None
        
    def test_add_three(self):
        c = ServiceCalendar()
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["C","D","E"] )
        c.add_period( 11,15,["E","F","G"] )
        
        
        assert c.head.next.next.begin_time == 16
        
    def test_periods(self):
        c = ServiceCalendar()
        
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["E","F","G"] )
        c.add_period( 11,15,["C","D","E"] )
        
        assert [x.begin_time for x in c.periods] == [0,11,16]
            
    def test_to_xml(self):
        c = ServiceCalendar()
        
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["D","E","F"] )
        c.add_period( 11,15,["C","D","E"] )
        
        assert c.to_xml() == "<ServiceCalendar><ServicePeriod begin_time='0' end_time='10' service_ids='A,B,C'/><ServicePeriod begin_time='11' end_time='15' service_ids='C,D,E'/><ServicePeriod begin_time='16' end_time='20' service_ids='D,E,F'/></ServiceCalendar>"

    def test_pickle(self):
        cc = ServiceCalendar()
        cc.add_period( 0, 100, ["A","B"] )
        cc.add_period( 101, 200, ["C","D"] )
        cc.add_period( 201, 300, ["E","F"] )
        
        ss = pickle.dumps( cc )
        laz = pickle.loads( ss )
        
        assert cc.__getstate__() == laz.__getstate__()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestServiceCalendar)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_serviceperiod
from graphserver.core import *
import unittest
import pickle

class TestServicePeriod(unittest.TestCase):
    def test_service_period(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        assert(c.begin_time == 0)
        assert(c.end_time == 1*3600*24)
        assert(len(c.service_ids) == 2)
        assert(c.service_ids == [1,2])
        
    def test_fast_forward_rewind(self):
        cc = ServiceCalendar()
        cc.add_period( 0, 100, ["A","B"] )
        cc.add_period( 101, 200, ["C","D"] )
        cc.add_period( 201, 300, ["E","F"] )
        
        hh = cc.head
        ff = hh.fast_forward()
        assert ff.begin_time==201
        pp = ff.rewind()
        assert pp.begin_time==0
        
    def test_midnight_datum(self):
        c = ServicePeriod( 0, 1*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 500, 1000, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 1*3600*24, 2*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        assert c.datum_midnight(timezone_offset=3600) == 82800
        
        c = ServicePeriod( 1*3600*24+50, 1*3600*24+60, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        
    def test_normalize_time(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        
        assert c.normalize_time( 0, 0 ) == 0
        assert c.normalize_time( 0, 100 ) == 100
        
    def test_pickle(self):
        cc = ServicePeriod(0, 100, [1,2,3,4,5])
        
        ss = pickle.dumps( cc )
        laz = pickle.loads( ss )
        
        assert laz.__getstate__() == cc.__getstate__()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestServicePeriod)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_spt
from graphserver.core import *
import unittest
import time

class TestShortestPathTree(unittest.TestCase):
    def setUp(self):
        self.gg = Graph()
        self.A = self.gg.add_vertex( "A" )
        self.B = self.gg.add_vertex( "B" )
        self.a = self.gg.add_edge( "A", "B", Street("a", 10) )

        self.spt = self.gg.shortest_path_tree( "A", "B", State(0) )

    def test_path_retro_basic(self):
        """ShortestPathTree.path_retro works on a trivial graph"""
        
        vertices, edges = self.spt.path_retro( "B" )

        self.assertEqual( vertices[0].label , self.B.label )
        self.assertEqual( vertices[1].label , self.A.label )
        self.assertEqual( edges[0].payload.name , self.a.payload.name )
        
    def test_basic(self):
        spt = ShortestPathTree()
        assert spt
        
        spt.destroy()
        
    def test_empty_graph(self):
        spt = ShortestPathTree()
        assert spt.vertices == []
        
        spt.destroy()
        
    def test_add_vertex(self):
        spt = ShortestPathTree()
        v = spt.add_vertex( Vertex("home") )
        assert v.label == "home"
        
        spt.destroy()
        
    def test_remove_vertex(self):
        spt = ShortestPathTree()
        spt.add_vertex( Vertex("A") )
        spt.get_vertex( "A" ).label == "A"
        spt.remove_vertex( "A" )
        assert spt.get_vertex( "A" ) == None
        
        spt.add_vertex( Vertex("A") )
        spt.add_vertex( Vertex("B") )
        pl = Street( "AB", 1 )
        spt.add_edge( "A", "B", pl )
        spt.remove_vertex( "A" )
        assert pl.name == "AB"
        assert spt.get_vertex( "A" ) == None
        assert spt.get_vertex( "B" ).label == "B"
        
    def test_double_add_vertex(self):
        spt = ShortestPathTree()
        v = spt.add_vertex( Vertex("double") )
        assert v.label == "double"
        assert spt.size == 1
        v = spt.add_vertex( Vertex("double") )
        assert spt.size == 1
        assert v.label == "double"
        
        spt.destroy()
        
    def test_get_vertex(self):
        spt = ShortestPathTree()
        
        spt.add_vertex( Vertex("home") )
        v = spt.get_vertex("home")
        assert v.label == "home"
        v = spt.get_vertex("bogus")
        assert v == None
        
        spt.destroy()
        
    def test_add_edge(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.add_edge("home", "work", s)
        assert e
        assert e.from_v.label == "home"
        assert e.to_v.label == "work"
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/></Edge>"
        
        spt.destroy()
    
    def test_add_edge_effects_vertices(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.add_edge("home", "work", s)
        
        assert fromv.degree_out==1
        assert tov.degree_in==1
        
        spt.destroy()
    
    def test_vertices(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        
        assert spt.vertices
        assert len(spt.vertices)==2
        assert spt.vertices[0].label == 'home'
        
        spt.destroy()

        
    def test_walk_longstreet(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 24000 )
        e = spt.add_edge("home", "work", s)
        
        wo = WalkOptions()
        sprime = e.walk(State(spt.numagencies,0), wo)
        wo.destroy()
        print str(sprime)
        assert str(sprime)=="<state time='3953' weight='5538153' dist_walked='24000.0' num_transfers='0' trip_id='None' stop_sequence='-1'></state>"

        spt.destroy()
    
        
    def test_add_link(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.add_edge("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = spt.add_edge("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
        spt.destroy()
        
    def test_edgeclass(self):
        spt = ShortestPathTree()
        spt.add_vertex( Vertex("A") )
        spt.add_vertex( Vertex("B") )
        spt.add_edge( "A", "B", Street("AB", 1) )
        
        vv = spt.get_vertex( "A" )
        assert vv.__class__ == SPTVertex
        assert vv.outgoing[0].__class__ == SPTEdge
        assert vv.outgoing[0].to_v.__class__ == SPTVertex
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sptvertex
import unittest
from graphserver.core import *

class TestSPTVertex(unittest.TestCase):
    def test_basic(self):
        vv = Vertex("home")
        v=SPTVertex( vv )

	assert v.mirror.soul == vv.soul
        assert v

    def test_init_hop(self):
        v = SPTVertex( Vertex("A") )
	assert v.hop == 0

	v = SPTVertex( Vertex("B"), 1 )
	assert v.hop == 1
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        v=SPTVertex( Vertex("home") )
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        v=SPTVertex( Vertex("home") )
        print v.label
        assert v.label == "home"
    
    def test_incoming(self):
        v=SPTVertex( Vertex("home") )
        assert v.incoming == []
        assert v.degree_in == 0
        
    def test_outgoing(self):
        v=SPTVertex( Vertex("home") )
        assert v.outgoing == []
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        v = SPTVertex( Vertex("home") )
        assert v.to_xml() == "<SPTVertex degree_out='0' degree_in='0' label='home'/>"


if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestSPTVertex)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_state
from graphserver.core import *
import unittest

class TestState(unittest.TestCase):
    def test_basic(self):
        s = State(1,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge == None
        assert s.num_agencies == 1
        assert s.service_period(0) == None
        assert s.trip_id == None
        assert s.stop_sequence == -1
        
    def test_basic_multiple_calendars(self):
        s = State(2,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge == None
        assert s.num_agencies == 2
        assert s.service_period(0) == None
        assert s.service_period(1) == None
        assert s.stop_sequence == -1

    def test_set_cal(self):
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        
        try:
            s.set_calendar_day(1, cal)
            assert False #should have failed by now
        except:
            pass
        
        s.set_service_period(0, sp)
        
        spout = s.service_period(0)
        
        assert spout.begin_time == 0
        assert spout.end_time == 86400
        assert spout.service_ids == [1,2]
        
    def test_destroy(self):
        s = State(1)
        
        s.destroy() #did we segfault?
        
        try:
            print s.time
            assert False #should have popped exception by now
        except:
            pass
        
        try:
            s.destroy()
            assert False
        except:
            pass
        
    def test_clone(self):
        
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        s.set_service_period(0,sp)
        
        s2 = s.clone()
        
        s.clone()
        
        assert s2.time == 0
        assert s2.weight == 0
        assert s2.dist_walked == 0
        assert s2.num_transfers == 0
        assert s2.prev_edge == None
        assert s2.num_agencies == 1
        assert s2.service_period(0).to_xml() == "<ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/>"
        assert s2.stop_sequence == -1
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestState)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_street
from graphserver.core import *
import unittest

class TestStreet(unittest.TestCase):
    def test_street(self):
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.rise == 0
        assert s.fall == 0
        assert s.slog == 1
        assert s.way == 0
	assert s.external_id == 0
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' rise='0.000000' fall='0.000000' way='0' reverse='False'/>"

	s.external_id = 15
	assert Street.from_pointer( s.soul ).external_id == 15
        
        s.slog = 2500
        s.way = 232323
        assert s.slog == 2500
        assert s.way == 232323
        
    def test_street_elev(self):
        s = Street("mystreet", 1.1, 24.5, 31.2)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert round(s.rise,3) == 24.5
        assert round(s.fall,3) == 31.2
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' rise='24.500000' fall='31.200001' way='0' reverse='False'/>"
        
    def test_destroy(self):
        s = Street("mystreet", 1.1)
        s.destroy()
        
        assert s.soul==None
        
    def test_street_big_length(self):
        s = Street("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Street name='longstreet' length='240000.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/>"
        
    def test_walk(self):
        s = Street("longstreet", 2)
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        after = s.walk(State(0,0),wo)
        assert after.time == 2
        assert after.weight == 2
        assert after.dist_walked == 2
        assert after.prev_edge.type == 0
        assert after.prev_edge.name == "longstreet"
        assert after.num_agencies == 0
        
    def test_walk_slog(self):
        s = Street("longstreet", 2)
        s.slog = 10
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        after = s.walk(State(0,0),wo)
        assert after.time == 2
        assert after.weight == 20
        assert after.dist_walked == 2
        assert after.prev_edge.type == 0
        assert after.prev_edge.name == "longstreet"
        assert after.num_agencies == 0
        
    def test_walk_back(self):
        s = Street("longstreet", 2)
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        before = s.walk_back(State(0,100),wo)
        
        assert before.time == 98
        assert before.weight == 2
        assert before.dist_walked == 2.0
        assert before.prev_edge.type == 0
        assert before.prev_edge.name == "longstreet"
        assert before.num_agencies == 0
        
    def test_street_turn(self):
        wo = WalkOptions()
        wo.turn_penalty = 20
        wo.walking_speed = 1

        e0 = Street("a1", 10)
        e0.way = 42
        e1 = Street("a2", 10)
        e1.way = 43
        s0 = State(0,0)
        s0.prev_edge = e0
        
        s1 = e1.walk(s0, wo)
        assert s1.weight == 30
        
        
    def test_getstate(self):
        s = Street("longstreet", 2)
        
        assert s.__getstate__() == ('longstreet', 2.0, 0.0, 0.0, 1.0,0,False)
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestStreet)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_timezone
import unittest
from graphserver.core import *
from graphserver import util
import pickle

class TestTimezone(unittest.TestCase):
    def test_basic(self):
        tz = Timezone()
        
        assert tz
        assert tz.head == None
        
    def test_add_timezone(self):
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 100, -8*3600) )
        
        period = tz.head
        assert period.begin_time == 0
        assert period.end_time == 100
        assert period.utc_offset == -8*3600
        
    def test_period_of(self):
        tz = Timezone()
        tzp = TimezonePeriod(0, 100, -8*3600)
        tz.add_period( tzp )
        
        assert tz.period_of(-1) == None
        
        tzpprime = tz.period_of(0)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(50)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(100)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(101)
        assert tzpprime == None
    
    def test_utc_offset(self):
        tz = Timezone()
        tzp = TimezonePeriod(0, 100, -8*3600)
        tz.add_period( tzp )
        
        try:
            tz.utc_offset( -1 )
            raise Exception("never make it this far")
        except Exception, ex:
            assert str(ex) == "-1 lands within no timezone period"
            
        assert tz.utc_offset(0) == -8*3600
        assert tz.utc_offset(50) == -8*3600
        assert tz.utc_offset(100) == -8*3600
        
        try:
            tz.utc_offset( 101 )
            raise Exception("never make it this far")
        except Exception, ex:
            assert str(ex) == "101 lands within no timezone period"
            
    def test_add_multiple(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(100, 199, -7*3600)
        p3 = TimezonePeriod(200, 299, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        assert tz.head.soul == p1.soul
        assert tz.head.next_period.soul == p2.soul
        assert tz.head.next_period.next_period.soul == p3.soul
        
        assert tz.period_of(-1) == None
        assert tz.period_of(0).soul == p1.soul
        assert tz.period_of(99).soul == p1.soul
        assert tz.period_of(100).soul == p2.soul
        assert tz.period_of(199).soul == p2.soul
        assert tz.period_of(200).soul == p3.soul
        assert tz.period_of(299).soul == p3.soul
        assert tz.period_of(300) == None
        
    def test_add_multiple_gaps_and_out_of_order(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p2 )
        tz.add_period( p1 )
        tz.add_period( p3 )
        
        assert tz.period_of(-1) == None
        assert tz.period_of(0).soul == p1.soul
        assert tz.period_of(99).soul == p1.soul
        assert tz.period_of(100) == None
        assert tz.period_of(150) == None
        assert tz.period_of(200).soul == p2.soul
        assert tz.period_of(300) == None
        assert tz.period_of(550).soul == p3.soul
        assert tz.period_of(600) == None
        
    def test_utc_offset_with_gaps(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        try:
            tz.utc_offset(-1)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "-1 lands within no timezone period"
            
        assert tz.utc_offset(0) == -8*3600
        assert tz.utc_offset(99) == -8*3600
        
        try:
            tz.utc_offset(150)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "150 lands within no timezone period"
            
        assert tz.utc_offset(550) == -8*3600
        
        try:
            tz.utc_offset(600)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "600 lands within no timezone period"
            
    def test_generate(self):
        
        tz = Timezone.generate("America/Los_Angeles")
        
        assert tz.utc_offset(1219863600) == -7*3600 #august 27, 2008, noon America/Los_Angeles
        assert tz.utc_offset(1199217600) == -8*3600 #january 1, 2008, noon America/Los_Angeles
        
        print tz.utc_offset(1205056799) == -8*3600 #second before DST
        print tz.utc_offset(1205056800) == -7*3600 #second after DST
        
    def test_pickle(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        assert tz.__getstate__() == [(0, 99, -28800), (200, 299, -25200), (500, 599, -28800)]
        
        ss = pickle.dumps( tz )
        laz = pickle.loads( ss )
        assert laz.period_of( 50 ).__getstate__() == (0, 99, -8*3600)
        assert laz.period_of( 250 ).__getstate__() == (200, 299, -7*3600)
        assert laz.period_of( 550 ).__getstate__() == (500, 599, -8*3600)
        
    def test_time_since_midnight(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 24*3600*256, -8*3600)
        tz.add_period( p1 )
        
        assert tz.time_since_midnight( 8*3600 ) == 0
        
        tz = Timezone()
        summer_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,6,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,9,1,0,0,0, "America/Los_Angeles" ),
                                     -7*3600 )
        tz.add_period( summer_tzp )
                                     
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
        tz = Timezone()
        winter_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,1,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,4,1,0,0,0, "America/Los_Angeles" ),
                                     -8*3600 )
        tz.add_period( winter_tzp )
                                     
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTimezone)
    unittest.TextTestRunner(verbosity=2).run(suite)
    
########NEW FILE########
__FILENAME__ = test_timezoneperiod
import unittest
from graphserver.core import *
from graphserver import util
import pickle

class TestTimezonePeriod(unittest.TestCase):
    def test_basic(self):
        tzp = TimezonePeriod(0, 100, -10)
        
        assert tzp
        assert tzp.begin_time == 0
        assert tzp.end_time == 100
        assert tzp.utc_offset == -10
        
    def test_dict(self):
        tzp = TimezonePeriod(3, 7, -11)
        
        assert tzp.__getstate__() == (3, 7, -11)
        
        ss = pickle.dumps( tzp )
        laz = pickle.loads( ss )
        assert laz.begin_time == 3
        assert laz.end_time == 7
        assert laz.utc_offset == -11
        
    def test_time_since_midnight(self):
        tzp = TimezonePeriod(0, 24*3600*256, -8*3600)
        
        assert tzp.time_since_midnight( 8*3600 ) == 0
        
        summer_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,6,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,9,1,0,0,0, "America/Los_Angeles" ),
                                     -7*3600 )
                                     
        assert summer_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert summer_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
        winter_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,1,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,4,1,0,0,0, "America/Los_Angeles" ),
                                     -8*3600 )
                                     
        assert winter_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert winter_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTimezonePeriod)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_tripalight
import unittest
from graphserver.core import *
from random import randint

class TestTripAlight(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.int_service_id == 0
        assert al.timezone.soul == tz.soul
        assert al.calendar.soul == sc.soul
        assert al.agency == 0
        assert al.overage == 0
        
        assert al.num_alightings == 0
        
        assert al.type == 10
        assert al.soul
        al.destroy()
        assert al.soul == None
        
    def test_get_alighting_by_trip_id( self ):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        al.add_alighting( "trip1", 0, 0 )
        al.get_alighting_by_trip_id( "trip1" ) == ("trip1", 0, 0)
        assert al.get_alighting_by_trip_id( "bogus" ) == None
        
        al.add_alighting( "trip2", 1, 1 )
        
        assert al.get_alighting_by_trip_id( "trip1" ) == ("trip1", 0, 0 )
        assert al.get_alighting_by_trip_id( "trip2" ) == ("trip2", 1, 1 )
        assert al.get_alighting_by_trip_id( "bogus" ) == None


    def test_overage(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.overage == 0
        
        al.add_alighting( "midnight", 24*3600, 0 )
        
        assert al.overage == 0
        
        al.add_alighting( "nightowl1", 24*3600+1, 0 )
        
        assert al.overage == 1
        
        al.add_alighting( "nightowl2", 24*3600+3600, 0 )
        
        assert al.overage == 3600

    def test_alight_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "eleven", 23*3600, 0 )
        al.add_alighting( "midnight", 24*3600, 0 )
        al.add_alighting( "one", 25*3600, 0 )
        al.add_alighting( "two", 26*3600, 0 )
        
        s0 = State(1, 0)
        s1 = al.walk_back(s0,WalkOptions())
        assert s1 == None
        
        s0 = State(1, 23*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 2
        assert s1.service_period(0).service_ids == [1]

    def test_add_single_trip(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "morning", 0, 0 )
        
        assert al.num_alightings == 1
        
        assert al.get_alighting( 0 ) == ("morning", 0, 0)
        
        try:
            al.get_alighting( -1 )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 1 )
        except Exception, ex:
            assert str(ex) == "Index 1 out of bounds"

    def test_add_several_in_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "first", 0, 0 )
        
        assert al.num_alightings == 1
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        
        al.add_alighting( "second", 50, 0 )
        assert al.num_alightings == 2
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        al.add_alighting( "third", 150, 0 )
        assert al.num_alightings == 3
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
            
        al.add_alighting( "fourth", 150, 0 )
        assert al.num_alightings == 4
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0) or al.get_alighting( 2 ) == ('fourth', 150, 0)
        assert al.get_alighting( 3 ) == ('third', 150, 0) or al.get_alighting( 3 ) == ('fourth', 150, 0)

    def test_add_several_out_of_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "fourth", 150, 0 )
        
        assert al.num_alightings == 1
        assert al.get_alighting( 0 ) == ('fourth', 150, 0)
        
        al.add_alighting( "first", 0, 0 )
        assert al.num_alightings == 2
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('fourth', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        al.add_alighting( "third", 150, 0 )
        assert al.num_alightings == 3
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('third', 150, 0)
        assert al.get_alighting( 2 ) == ('fourth', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
        
        al.add_alighting( "second", 50, 0 )
        assert al.num_alightings == 4
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0) or al.get_alighting( 2 ) == ('fourth', 150, 0)
        assert al.get_alighting( 3 ) == ('third', 150, 0) or al.get_alighting( 3 ) == ('fourth', 150, 0)

    def test_add_several_random(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        for i in range(1000):
            al.add_alighting( str(i), randint(0,10000), 0 )
            
        last_arrival = -1
        for i in range(al.num_alightings):
            trip_id, arrival, stop_sequence = al.get_alighting(i)
            assert last_arrival <= arrival
            last_arrival = arrival
            

    
    def test_search_boardings_list_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.search_alightings_list(0) == 0
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.search_alightings_list(5) == 0
        assert al.search_alightings_list(15) == 0
        assert al.search_alightings_list(20) == 1
        

        
    def test_get_last_alighting_index_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting_index(0) == -1
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.get_last_alighting_index(5) == -1
        assert al.get_last_alighting_index(15) == 0
        assert al.get_last_alighting_index(20) == 0
        
    def test_get_last_alighting_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting(0) == None
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "morning", 15, 0 )
        assert al.get_last_alighting(20) == ( "morning", 15, 0 )

    def test_get_last_alighting_several(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting(0) == None
        
        al.add_alighting( "1", 15, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "1", 15, 0 )
        assert al.get_last_alighting(20) == ( "1", 15, 0 )
        
        al.add_alighting( "2", 25, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "1", 15, 0 )
        assert al.get_last_alighting(20) == ( "1", 15, 0 )
        assert al.get_last_alighting(25) == ( "2", 25, 0 )
        assert al.get_last_alighting(30) == ( "2", 25, 0 )
    

    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "1", 50, 0 )
        al.add_alighting( "2", 100, 0 )
        al.add_alighting( "3", 200, 0 )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = al.walk_back( s,WalkOptions() )
        assert ret == None
        
        s = State(1, 250)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 51
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 248)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 49
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 200)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 100)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 100
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 50)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 49)
        ret = al.walk_back(s,WalkOptions())
        assert ret == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "1", 50, 0 )
        al.add_alighting( "2", 100, 0 )
        al.add_alighting( "3", 200, 0 )
        
        s = State(1,100)
        ret = al.walk( s, WalkOptions() )
        assert ret.time == 100
        assert ret.weight == 0
        
    def test_check_yesterday(self):
        """check the previous day for viable departures"""
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 2*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        # one alighting - one second before midnight
        al.add_alighting( "1", 86400-1, 0 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be one second after the last alighting 
        s1 = al.walk_back( s0, WalkOptions() )
        self.assertEquals( s1.time, 86399 )
        
    def test_check_today(self):
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 2*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        # one boarding - noon
        al.add_alighting( "1", 43200, 1 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # this should put us in noon the previous day
        s1 = al.walk_back( s0, WalkOptions() )
        
        self.assertEquals( s1.time, 43200 )
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTripAlight)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_tripboard
import unittest
from graphserver.core import *
from random import randint

class TestTripBoard(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.int_service_id == 0
        assert tb.timezone.soul == tz.soul
        assert tb.calendar.soul == sc.soul
        assert tb.agency == 0
        assert tb.overage == -1
        
        assert tb.num_boardings == 0
        
        assert tb.type==8
        assert tb.soul
        tb.destroy()
        try:
            print tb
            raise Exception( "should have failed by now" )
        except:
            pass
            
    def test_get_boarding_by_trip_id(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        tb.add_boarding( "trip1", 0, 0 )
        
        assert tb.get_boarding_by_trip_id( "trip1" ) == ("trip1", 0, 0)
        assert tb.get_boarding_by_trip_id( "bogus" ) == None
        
        tb.add_boarding( "trip2", 1, 1 )
        
        assert tb.get_boarding_by_trip_id( "trip1" ) == ("trip1", 0, 0 )
        assert tb.get_boarding_by_trip_id( "trip2" ) == ("trip2", 1, 1 )
        assert tb.get_boarding_by_trip_id( "bogus" ) == None
        
            
    def test_overage(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.overage == -1
        
        tb.add_boarding( "midnight", 24*3600, 0 )
        
        assert tb.overage == 0
        
        tb.add_boarding( "nightowl1", 24*3600+1, 0 )
        
        assert tb.overage == 1
        
        tb.add_boarding( "nightowl2", 24*3600+3600, 0 )
        
        assert tb.overage == 3600
        
    def test_tripboard_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "eleven", 23*3600, 0 )
        tb.add_boarding( "midnight", 24*3600, 0 )
        tb.add_boarding( "one", 25*3600, 0 )
        tb.add_boarding( "two", 26*3600, 0 )
        
        s0 = State(1, 0)
        s1 = tb.walk(s0,WalkOptions())
        self.assertEqual( s1.weight , 82801 )
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = tb.walk(s0,WalkOptions())
        print s1
        self.assertEqual( s1 , None )
        
        
    def test_tripboard_over_midnight_without_hope(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        sc.add_period(2*3600*24,3*3600*24, ['SUN'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,3*3600*24,0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "eleven", 23*3600, 0 )
        tb.add_boarding( "midnight", 24*3600, 0 )
        tb.add_boarding( "one", 25*3600, 0 )
        tb.add_boarding( "two", 26*3600, 0 )
        
        s0 = State(1,3*3600*24) #midnight sunday
        s1 = tb.walk(s0,WalkOptions())
        assert s1 == None
            
    def test_add_single_trip(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "morning", 0, 0 )
        
        assert tb.num_boardings == 1
        
        assert tb.get_boarding( 0 ) == ("morning", 0, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 1 out of bounds"
            
    def test_add_several_in_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "first", 0, 0 )
        
        assert tb.num_boardings == 1
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        
        tb.add_boarding( "second", 50, 0 )
        assert tb.num_boardings == 2
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        tb.add_boarding( "third", 150, 0 )
        assert tb.num_boardings == 3
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
            
        tb.add_boarding( "fourth", 150, 0 )
        assert tb.num_boardings == 4
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0) or tb.get_boarding( 2 ) == ('fourth', 150, 0)
        assert tb.get_boarding( 3 ) == ('third', 150, 0) or tb.get_boarding( 3 ) == ('fourth', 150, 0)
            
    def test_add_several_out_of_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "fourth", 150, 0 )
        
        assert tb.num_boardings == 1
        assert tb.get_boarding( 0 ) == ('fourth', 150, 0)
        
        tb.add_boarding( "first", 0, 0 )
        assert tb.num_boardings == 2
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('fourth', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        tb.add_boarding( "third", 150, 0 )
        assert tb.num_boardings == 3
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('third', 150, 0)
        assert tb.get_boarding( 2 ) == ('fourth', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
        
        tb.add_boarding( "second", 50, 0 )
        assert tb.num_boardings == 4
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0) or tb.get_boarding( 2 ) == ('fourth', 150, 0)
        assert tb.get_boarding( 3 ) == ('third', 150, 0) or tb.get_boarding( 3 ) == ('fourth', 150, 0)
        
    def test_add_several_random(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        for i in range(1000):
            tb.add_boarding( str(i), randint(0,10000), 0 )
            
        last_depart = -1
        for i in range(tb.num_boardings):
            trip_id, depart, stop_sequence = tb.get_boarding(i)
            assert last_depart <= depart
            last_depart = depart
    
    def test_search_boardings_list_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.search_boardings_list(0) == 0
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.search_boardings_list(5) == 0
        assert tb.search_boardings_list(15) == 0
        assert tb.search_boardings_list(20) == 1
        
    def test_get_next_boarding_index_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding_index(0) == -1
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.get_next_boarding_index(5) == 0
        assert tb.get_next_boarding_index(15) == 0
        assert tb.get_next_boarding_index(20) == -1
        
    def test_get_next_boarding_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding(0) == None
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.get_next_boarding(5) == ( "morning", 15, 0 )
        assert tb.get_next_boarding(15) == ( "morning", 15, 0 )
        assert tb.get_next_boarding(20) == None
        
    def test_get_next_boarding_several(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding(0) == None
        
        tb.add_boarding( "1", 15, 0 )
        
        assert tb.get_next_boarding(5) == ( "1", 15, 0 )
        assert tb.get_next_boarding(15) == ( "1", 15, 0 )
        assert tb.get_next_boarding(20) == None
        
        tb.add_boarding( "2", 25, 0 )
        
        assert tb.get_next_boarding(5) == ( "1", 15, 0 )
        assert tb.get_next_boarding(15) == ( "1", 15, 0 )
        assert tb.get_next_boarding(20) == ( "2", 25, 0 )
        assert tb.get_next_boarding(25) == ( "2", 25, 0 )
        assert tb.get_next_boarding(30) == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "1", 50, 0 )
        tb.add_boarding( "2", 100, 0 )
        tb.add_boarding( "3", 200, 0 )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = tb.walk( s,WalkOptions() )
        assert ret == None
        
        s = State(1, 0)
        ret = tb.walk(s,WalkOptions())
        self.assertEqual( ret.time , 50 )
        self.assertEqual( ret.weight , 51 )
        self.assertEqual( ret.num_transfers , 1 )
        self.assertEqual( ret.dist_walked , 0.0 )
        
        s = State(1, 2)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 49
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 50)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 100)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 100
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 200)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 201)
        ret = tb.walk(s,WalkOptions())
        assert ret == None
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "1", 50, 0 )
        tb.add_boarding( "2", 100, 0 )
        tb.add_boarding( "3", 200, 0 )
        
        s = State(1,100)
        ret = tb.walk_back( s, WalkOptions() )
        assert ret.time == 100
        assert ret.weight == 0
        
    def test_check_yesterday(self):
        """check the previous day for viable departures"""
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 2*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        tb = TripBoard( "WKDY", sc, tz, 0 )
        
        # one boarding - one second after midnight
        tb.add_boarding( "1", 86400+1, 0 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be one second until the next boarding
        s1 = tb.walk( s0, WalkOptions() )
        self.assertEquals( s1.time, 86401 )
        
    def test_check_today(self):
        """given a schedule that runs two consecutive days, find a departure
           given a state on midnight between the two days"""
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        tb = TripBoard( "WKDY", sc, tz, 0 )
        
        # one boarding - pretty early in the morning
        tb.add_boarding( "21SFO1", 26340, 1 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be early morning on the second day
        s1 = tb.walk( s0, WalkOptions() )
        
        self.assertEquals( s1.time, 26340+86400 )
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTripBoard)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
__FILENAME__ = test_util
import unittest
from graphserver.util import TimeHelpers

class TestUtil(unittest.TestCase): 
    
    def test_basic(self):
	assert TimeHelpers.localtime_to_unix(2008,10,12,6,0,0,"Europe/Paris") == 1223784000
	assert str(TimeHelpers.unix_to_localtime(1199181360, "America/New_York")) == "2008-01-01 04:56:00-05:00"
	assert TimeHelpers.unixtime_to_daytimes(1219834260, "America/Los_Angeles") == (13860, 100260, 186660)
	assert str(TimeHelpers.unix_to_localtime(1221459000, "America/Chicago")) == "2008-09-15 01:10:00-05:00" 
	assert TimeHelpers.unixtime_to_daytimes(1230354000, "America/Chicago") == (82800, 169200, 255600)
	assert TimeHelpers.unix_time(2008,8,27,12,0,0,-7*3600) == 1219863600
	assert TimeHelpers.localtime_to_unix(2008,8,27,12,0,0,"America/Los_Angeles") == 1219863600
	assert str(TimeHelpers.unix_to_localtime(1219863600, "America/Los_Angeles")) == "2008-08-27 12:00:00-07:00"

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestUtil)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_vector
from graphserver.vector import Vector
import unittest

class TestVector(unittest.TestCase):
    def test_basic(self):
        # basic test
        vec = Vector(expand_delta=40)

        assert vec.num_elements == 0
        assert vec.num_alloc == 50
        assert vec.expand_delta == 40

        vec.expand( 50 )

        assert vec.num_alloc == 100

        vec.add( 11 )
        assert vec.get( 0 ) == 11
        vec.add( 15 )
        assert vec.get( 0 ) == 11
        assert vec.get( 1 ) == 15

        del(vec)

    def test_expand(self):
        # expand test

        vec = Vector(init_size=1, expand_delta=10)
        assert vec.num_alloc == 1
        assert vec.num_elements == 0

        vec.add( 3 )
        assert vec.num_alloc == 1
        assert vec.num_elements == 1
        assert vec.get(0) == 3

        vec.add( 5 )
        assert vec.num_alloc == 11
        assert vec.num_elements == 2
        assert vec.get(0) == 3
        assert vec.get(1) == 5
        
if __name__ == '__main__':

    unittest.main()
########NEW FILE########
__FILENAME__ = test_vertex
from graphserver.core import *
import unittest

class TestVertex(unittest.TestCase):
    def test_basic(self):
        """create a vertex"""
        v=Vertex("home")
        assert v
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        """destroy a vertex"""
        v=Vertex("home")
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        """set the vertex label"""
        v=Vertex("home")
        assert v.label == "home"
    
    def test_incoming(self):
        """new vertex has no incoming edges"""
        v=Vertex("home")
        assert v.incoming == []
        assert v.degree_in == 0
        
    def test_outgoing(self):
        """new vertex has no outgoing edges"""
        v=Vertex("home")
        assert v.outgoing == []
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        """vertex can output itself to xml"""
        v = Vertex("home")
        assert v.to_xml() == "<Vertex degree_out='0' degree_in='0' label='home'/>"
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestVertex)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_wait
from graphserver.core import Wait, Timezone, TimezonePeriod, State, WalkOptions
import unittest

class TestWait(unittest.TestCase):
    def test_wait(self):
        waitend = 100
        tz = Timezone()
        tz.add_period(TimezonePeriod(0,100000,0))
        w = Wait(waitend, tz)
        assert w.end == waitend
        assert w.timezone.soul == tz.soul
        assert w.to_xml() == "<Wait end='100' />"

        s = State(1,0)
        sprime = w.walk(s, WalkOptions())
        assert sprime.time == 100
        assert sprime.weight == 100

        s = State(1, 150)
        sprime = w.walk_back(s, WalkOptions())
        assert sprime.time == 100
        assert sprime.weight == 50
        
        s = State(1, 86400)
        sprime = w.walk(s, WalkOptions())
        assert sprime.time == 86500
        assert sprime.weight == 100

        w.destroy()
        
        tz = Timezone()
        tz.add_period(TimezonePeriod(0,100000,-20))
        w = Wait(100, tz)
        assert w.end == 100
        assert w.timezone.soul == tz.soul
        s = State(1, 86400)
        sprime = w.walk(s, WalkOptions())
        assert sprime.weight == 120
        
    def test_august(self):
        # noon, -7 hours off UTC, as America/Los_Angeles in summer
        tz = Timezone.generate("America/Los_Angeles")
        w = Wait(43200, tz)
        
        # one calendar, noon august 27, America/Los_Angeles
        s = State(1, 1219863600)
        
        assert w.walk(s, WalkOptions()).time == 1219863600
        
        # one calendar, 11:55 AM August 27 2008, America/Los_Angeles
        s = State(1, 1219863300)
        assert w.walk(s, WalkOptions()).time == 1219863600
        assert w.walk(s, WalkOptions()).weight == 300
        
    def test_getstate(self):
        # noon, -7 hours off UTC, as America/Los_Angeles in summer
        tz = Timezone.generate("America/Los_Angeles")
        w = Wait(43200, tz)
        
        assert w.__getstate__() == (43200, tz.soul)
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestWait)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_walkoptions
import unittest
from graphserver.core import *

class TestWalkOptions(unittest.TestCase):
    def test_basic(self):
        wo = WalkOptions()
        
        assert wo
        
        assert wo.transfer_penalty == 0
        assert wo.turn_penalty == 0
        assert wo.walking_speed*100//1 == 607.0
        assert wo.walking_reluctance == 1.0
        assert wo.max_walk == 10000
        assert round(wo.walking_overage,3) == 0.1
        
        wo.transfer_penalty = 50
        assert wo.transfer_penalty == 50
        
        wo.turn_penalty = 3
        assert wo.turn_penalty == 3
        
        wo.walking_speed = 1.05
        assert round(wo.walking_speed*100) == 105.0
        
        wo.walking_reluctance = 2.0
        assert wo.walking_reluctance == 2.0
        
        wo.max_walk = 100
        assert wo.max_walk == 100
        
        wo.walking_overage = 1.0
        assert wo.walking_overage == 1.0
        
        wo.uphill_slowness = 1.5
        assert wo.uphill_slowness == 1.5
        
        wo.downhill_fastness = 3.4
        assert round(wo.downhill_fastness,3) == 3.4
        
        wo.hill_reluctance = 1.4
        assert round(wo.hill_reluctance,3) == 1.4
        
        wo.destroy()
        assert wo.soul == None
        
    def test_from_ptr(self):
        wo = WalkOptions()
        wo.transfer_penalty = 10
        wo1 = WalkOptions.from_pointer(wo.soul)
        assert wo.transfer_penalty == wo1.transfer_penalty
        assert wo1.soul == wo.soul
        wo.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestWalkOptions)
    unittest.TextTestRunner(verbosity=2).run(suite)
########NEW FILE########
