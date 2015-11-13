__FILENAME__ = bounds
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''
place_type = ''

# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Explicate write and read database settings
db_write_results = ''
db_write_unique_id = ''
db_read_unique_id = ''
db_read_placetype = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='Locality',
                  help='Valid WOE placetypes are Country, State, County, LocalAdmin, Town, and Suburb.')

(options, args) = parser.parse_args()



def load_photos( unique_id, place_filter={} ):
    cur.execute("""
        SELECT 
            longitude, latitude
        FROM 
            """ + db_photos + """
        WHERE 
            """ + db_read_unique_id + """ = """ + str(unique_id) )
    
    photos = cur.fetchall()
    
    #print '\t', len(photos), 'photos'
    
    return photos


def get_bbox_for_place( photos ):
    bbox = [180, 90, -180, -90]
    
    for pt in photos:
        for i in range(4):
            bbox[i] = min(bbox[i], pt[i%2]) if i<2 else max(bbox[i], pt[i%2])

    median = (numpy.median([pt[0] for pt in photos]),
              numpy.median([pt[1] for pt in photos]))

    return (bbox, median)

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            """ + db_write_unique_id + """, name
        FROM """ + db_table_name ) #+ 
#        """ WHERE """ + db_read_placetype + """ = '""" + place_type + """'""")
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s...' % (len(places), place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        unique_id, name = place
    
        if total_places > 10000:
            if counter % 1000 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, unique_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, unique_id)
    
        photos = load_photos( unique_id )
        total_photos = len(photos)

        if total_places > 10000:
            if counter % 1000 == 0:
                print '\t', total_photos, 'photos'
        else:
            print '\t', total_photos, 'photos'
            
        if total_photos > 0:
            bbox, median = get_bbox_for_place( photos )
            
            #print '\t%s: %s %s, %s %s' % (unique_id, bbox[0], bbox[1], bbox[2], bbox[3])
            #print '\t%s, %s' % (median[0], median[1])
            
            cur.execute("""
                UPDATE 
                    """ + db_write_results + """ gp
                SET 
                    centroid_lon = """ + str(median[0]) + """,
                    centroid_lat = """ + str(median[1]) + """,
                    x_min = """ + str(bbox[0]) + """,
                    y_min = """ + str(bbox[1]) + """,
                    x_max = """ + str(bbox[2]) + """,
                    y_max = """ + str(bbox[3]) + """,
                    photos = """ + str(len(photos)) + """
                WHERE gp.""" + db_write_unique_id + """ = """ + str(unique_id) )

            db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    place_type = options.place_type
    
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Country':
        db_photos = 'flickr_adm0_data'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Admin' or place_type == 'State':
        place_type = 'State'
        db_photos = 'flickr_adm1_data'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Admin2' or place_type == 'County':
        place_type = 'County'
        db_photos = 'flickr_adm2_data'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        print 'Admin3 is not supported at this time.'
        place_type = 'LocalAdmin'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Town' or place_type == 'Locality':
        place_type = 'Town'
        db_photos = 'flickr_locality_data'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Suburb' or place_type == 'Neighborhood':
        place_type = 'Suburb'
        db_photos = 'flickr_neighborhood_data'
        db_write_results = 'geoplanet_places'
        db_write_unique_id = 'woe_id'
        db_read_unique_id = 'woe_id'
        db_read_placetype = 'placetype'
    elif place_type == 'Geoname Locality':
        place_type = 'PPL'
        db_photos = 'checkins'
        db_write_results = 'geoname'
        db_write_unique_id = 'geonameid'
        db_read_unique_id = 'geoname_id'
        db_read_placetype = 'fcode'
    elif place_type == 'Geoname Population':
        place_type = 'P'
        db_photos = 'checkins'
        db_write_results = 'geoname'
        db_write_unique_id = 'geonameid'
        db_read_unique_id = 'geoname_id'
        db_read_placetype = 'fclass'
    elif place_type == 'Geoname Admin':
        place_type = 'A'
        db_photos = 'checkins'
        db_write_results = 'geoname'
        db_write_unique_id = 'geonameid'
        db_read_unique_id = 'geoname_id'
        db_read_placetype = 'fclass'
    
    print "Evaluating", place_type, "..."
    
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = bounds_backfill
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''
place_type = ''
# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='Locality',
                  help='Valid WOE placetypes are Country, State, County, LocalAdmin, Town, and Suburb.')

(options, args) = parser.parse_args()



def load_photos( woe_id, place_filter={} ):
    if place_type == 'Country':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_adm0 = %s
            """, (woe_id,))
    elif place_type == 'State':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_adm1 = %s
            """, (woe_id,))
    elif place_type == 'County':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_adm2 = %s
            """, (woe_id,))
    elif place_type == 'LocalAdmin':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_lau = %s
            """, (woe_id,))
    elif place_type == 'Town':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_locality = %s
            """, (woe_id,))
    elif place_type == 'Suburb':
        cur.execute("""
            SELECT 
                longitude, latitude, photo_id
            FROM """ + db_photos + """
            WHERE woe_locality = %s
            """, (woe_id,))
    
    photos = cur.fetchall()
    
    #print '\t', len(photos), 'photos'
    
    return photos
    
def load_bbox_fallback( woe_id, place_filter={} ):
    
    bbox = [1, 1, -1, -1]
    median = (0,0)
    accuracy = 'flickr null island'
    
    nesting_levels = 10
    level = 0 
    
    while level < nesting_levels:
        level += 1
        
        cur.execute("""
            SELECT 
                placetype, parent_id
            FROM 
                """ + db_table_name + """
            WHERE 
                woe_id = (%s);""", (woe_id,))
            
        try:
            placetype, parent_id = cur.fetchone()
        except:
            return (bbox, median, accuracy)
        
        #print placetype, parent_id
        
        cur.execute("""
            SELECT 
                x_min, y_min, x_max, y_max, centroid_lon, centroid_lat
            FROM """ + db_table_name + 
            """ WHERE woe_id = (%s)""", (parent_id,))

        try:
            x_min, y_min, x_max, y_max, centroid_lon, centroid_lat = cur.fetchone()
            #don't return junk
            if x_min is None or centroid_lon is None:
                return (bbox, median, accuracy)
            #print x_min, y_min, x_max, y_max, centroid_lon, centroid_lat
            break
        except:
            return (bbox, median, accuracy)
            
        #set us up for the next loop
        woe_id = parent_id

    #print '\t', len(photos), 'photos'
    
    bbox = [x_max, y_max, x_min, y_min]
    median = (centroid_lon, centroid_lat)

    try:
        cur.execute("""
            SELECT 
                placetype
            FROM 
                """ + db_table_name + """
            WHERE 
                woe_id = (%s);""", (parent_id,))
        
        accuracy_place_type = cur.fetchone()
    except:
        return (bbox, median, accuracy)
    
    if accuracy_place_type[0] == 'Town' or accuracy_place_type[0] == 'Suburb':
        accuracy = 'flickr aggreate ' + accuracy_place_type[0]
    else:
        accuracy = 'flickr parent ' + accuracy_place_type[0]
    
    return (bbox, median, accuracy)

def get_bbox_for_place( photos ):
    bbox = [180, 90, -180, -90]
    
    for pt in photos:
        for i in range(4):
            bbox[i] = min(bbox[i], pt[i%2]) if i<2 else max(bbox[i], pt[i%2])

    median = (numpy.median([pt[0] for pt in photos]),
              numpy.median([pt[1] for pt in photos]))

    return (bbox, median)

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            woe_id, name
        FROM """ + db_table_name + 
        """ WHERE placetype = (%s) AND photos IS NULL""", (place_type,))
        #""" WHERE placetype = (%s) AND photos = 0""", (place_type,))
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s...' % (len(places), place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        woe_id, name = place
    
        if total_places > 10000:
            if counter % 1000 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
    
        photos = load_photos( woe_id )
    
        total_photos = len(photos)
                
        if total_photos is None or total_photos == 0:
            bbox, median, accuracy = load_bbox_fallback( woe_id )
        else:
            bbox, median = get_bbox_for_place( photos )
            accuracy = 'flickr proxy locality-suburb'
        
        if total_places > 10000:
            if counter % 1000 == 0:
                print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
                print '\t%s, %s' % (median[0], median[1])
                print '\t%s' % (accuracy,)
        else:
            print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
            print '\t%s, %s' % (median[0], median[1])
            print '\t%s' % (accuracy,)
        
        cur.execute("""
            UPDATE 
                geoplanet_places gp
            SET 
                centroid_lon = """ + str(median[0]) + """,
                centroid_lat = """ + str(median[1]) + """,
                x_min = """ + str(bbox[0]) + """,
                y_min = """ + str(bbox[1]) + """,
                x_max = """ + str(bbox[2]) + """,
                y_max = """ + str(bbox[3]) + """,
                photos = -""" + str(len(photos)) + """,
                accuracy = '""" + accuracy + """'
            WHERE gp.woe_id = """ + str(woe_id) )

        db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    place_type = options.place_type
    
    #woe_locality | woe_lau  | woe_adm2 | woe_adm1 | woe_adm0
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Country':
        search_place_type = 'woe_adm0'
        db_photos = 'flickr_merged_data'
    elif place_type == 'Admin' or place_type == 'State':
        search_place_type = 'woe_adm1'
        place_type = 'State'
        db_photos = 'flickr_merged_data'
    elif place_type == 'Admin2' or place_type == 'County':
        search_place_type = 'woe_adm2'
        place_type = 'County'
        db_photos = 'flickr_merged_data'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        search_place_type = 'woe_lau'
        #print 'Admin3 is not supported at this time.'
        place_type = 'LocalAdmin'
        db_photos = 'flickr_merged_data'
    elif place_type == 'Town' or place_type == 'Locality':
        search_place_type = 'woe_locality'
        place_type = 'Town'
        db_photos = 'flickr_merged_data'
    elif place_type == 'Suburb' or place_type == 'Neighborhood':
        search_place_type = 'woe_locality'
        place_type = 'Suburb'
        db_photos = 'flickr_merged_data'
    
    print "Evaluating", place_type, "..."
    
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = bounds_backfill_woe_adjacent
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''
adjacency_db_table_name = ''
place_type = ''
# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-a', '--adjacency_db_table_name', dest='adjacency_db_table_name', default='geoplanet_adjacencies',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='County',
                  help='Valid WOE placetypes are County, LocalAdmin, Town.')

(options, args) = parser.parse_args()

    
def load_bbox_fallback( woe_id, orig_accuracy, place_filter={} ):
    
    bbox = [1, 1, -1, -1]
    median = (0,0)
    centroids = [median]
    accuracy = orig_accuracy
    
    cur.execute("""
        SELECT 
            neighbor_woe_id
        FROM 
            """ + adjacency_db_table_name + """
        WHERE 
            place_woe_id = (%s)""", (woe_id,))
    
    neighbors_list = cur.fetchall()
       
    if len(neighbors_list) > 0:                
        counter = 0
        accuracy_place_type = 'null'
    
        centroids = []
        
        for neighbor in neighbors_list:
            neighbor_id = neighbor[0]
            try:            
                cur.execute("""
                    SELECT 
                        placetype, woe_id, x_min, y_min, x_max, y_max, centroid_lon, centroid_lat
                    FROM 
                        """ + db_table_name + """
                    WHERE 
                        woe_id = (%s)
                        AND accuracy IN ('flickr aggregate Suburb','flickr aggregate Town', 'flickr median', 'geonames match', 'geonames match round 2')
                        AND gn_matchaccuracy NOT IN ('unknown', 'twofish bad checkins extent')
                        AND gn_matchaccuracy IS NOT NULL;""", (neighbor_id,))


                neighbor_details = cur.fetchone()
                #print '\t', len(children), 'children places'

                placetype, woe_id, x_min, y_min, x_max, y_max, centroid_lon, centroid_lat = neighbor_details
        
                #print x_min, y_min, x_max, y_max, centroid_lon, centroid_lat

                #don't return junk
                if x_min is None or centroid_lon is None:
                    return (bbox, median, accuracy)

                if counter is 0:
                    bbox = [x_max, y_max, x_min, y_min]
                    accuracy_place_type = placetype
                else:
                    bbox[0] = min(bbox[0], x_min)
                    bbox[1] = min(bbox[1], y_min)
                    bbox[2] = max(bbox[2], x_max)
                    bbox[3] = max(bbox[3], y_max)
                                    
                centroids.append( (centroid_lon,centroid_lat) )
        
                counter = counter + 1
            except:
                return (bbox, median, accuracy)

        # bbox is already set
        median = (numpy.median([pt[0] for pt in centroids]),
                  numpy.median([pt[1] for pt in centroids]))
        accuracy = 'flickr neighbor ' + accuracy_place_type
        
    return (bbox, median, accuracy)


def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            woe_id, name, accuracy
        FROM """ + db_table_name + 
        """ WHERE placetype = (%s) 
            AND accuracy IN ('flickr parent State','flickr parent Country', 'flickr parent County', 'flickr parent LocalAdmin', 'flickr null island', 'flickr proxy locality-suburb') 
        """, (place_type,))
        #""" WHERE placetype = (%s) AND photos = 0""", (place_type,))
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s...' % (len(places), place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        woe_id, name, orig_accuracy = place
    
        if total_places > 1000:
            if counter % 100 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
    
        bbox, median, accuracy = load_bbox_fallback( woe_id, orig_accuracy )
        
        if total_places > 1000:
            if counter % 100 == 0:
                print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
                print '\t%s, %s' % (median[0], median[1])
                print '\t%s' % (accuracy,)
        else:
            print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
            print '\t%s, %s' % (median[0], median[1])
            print '\t%s' % (accuracy,)
            
        if orig_accuracy != accuracy:
            cur.execute("""
                UPDATE 
                    geoplanet_places gp
                SET 
                    centroid_lon = """ + str(median[0]) + """,
                    centroid_lat = """ + str(median[1]) + """,
                    x_min = """ + str(bbox[0]) + """,
                    y_min = """ + str(bbox[1]) + """,
                    x_max = """ + str(bbox[2]) + """,
                    y_max = """ + str(bbox[3]) + """,
                    accuracy = '""" + accuracy + """'
                WHERE gp.woe_id = """ + str(woe_id) )

            db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    adjacency_db_table_name = options.adjacency_db_table_name
    place_type = options.place_type
    
    #woe_locality | woe_lau  | woe_adm2 | woe_adm1 | woe_adm0
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Admin1' or place_type == 'State':
        place_type = 'State'
    elif place_type == 'Admin2' or place_type == 'County':
        place_type = 'County'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        place_type = 'LocalAdmin'
    elif place_type == 'Town' or place_type == 'Locality':
        place_type = 'Town'
    
    print "Evaluating", place_type, "..."
    
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = bounds_backfill_woe_children
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''
place_type = ''
# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='County',
                  help='Valid WOE placetypes are County, LocalAdmin, Town.')

(options, args) = parser.parse_args()

    
def load_bbox_fallback( woe_id, orig_accuracy, place_filter={} ):
    
    bbox = [1, 1, -1, -1]
    median = (0,0)
    centroids = [median]
    accuracy = orig_accuracy
    
    cur.execute("""
        SELECT 
            placetype, woe_id, x_min, y_min, x_max, y_max, centroid_lon, centroid_lat
        FROM 
            """ + db_table_name + """
        WHERE 
            woe_adm2 = (%s)
            AND accuracy in ('flickr aggregate Suburb','flickr aggregate Town', 'flickr median', 'geonames match', 'geonames match round 2');""", (woe_id,))
    
    children = cur.fetchall()
    #print '\t', len(children), 'children places'
    
    counter = 0
    accuracy_place_type = 'null'
    
    if len(children) > 0:                
        centroids = []
        for child in children:
            try:
                placetype, woe_id, x_min, y_min, x_max, y_max, centroid_lon, centroid_lat = child
            
                #print x_min, y_min, x_max, y_max, centroid_lon, centroid_lat

                #don't return junk
                if x_min is None or centroid_lon is None:
                    return (bbox, median, accuracy)

                if counter is 0:
                    bbox = [x_max, y_max, x_min, y_min]
                    accuracy_place_type = placetype
                else:
                    bbox[0] = min(bbox[0], x_min)
                    bbox[1] = min(bbox[1], y_min)
                    bbox[2] = max(bbox[2], x_max)
                    bbox[3] = max(bbox[3], y_max)
                                        
                centroids.append( (centroid_lon,centroid_lat) )
            
                counter = counter + 1
            except:
                return (bbox, median, accuracy)

        # bbox is already set
        median = (numpy.median([pt[0] for pt in centroids]),
                  numpy.median([pt[1] for pt in centroids]))
        accuracy = 'flickr children ' + accuracy_place_type #+ ' round 2'
        
    return (bbox, median, accuracy)


def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            woe_id, name, accuracy
        FROM """ + db_table_name + 
        """ WHERE placetype = (%s) 
            AND accuracy IN ('flickr parent State','flickr parent Country', 'flickr parent County') 
        """, (place_type,))
        #""" WHERE placetype = (%s) AND photos = 0""", (place_type,))
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s...' % (len(places), place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        woe_id, name, orig_accuracy = place
    
        if total_places > 1000:
            if counter % 100 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
    
        bbox, median, accuracy = load_bbox_fallback( woe_id, orig_accuracy )
        
        if total_places > 1000:
            if counter % 100 == 0:
                print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
                print '\t%s, %s' % (median[0], median[1])
                print '\t%s' % (accuracy,)
        else:
            print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
            print '\t%s, %s' % (median[0], median[1])
            print '\t%s' % (accuracy,)
            
        if orig_accuracy != accuracy:
            cur.execute("""
                UPDATE 
                    geoplanet_places gp
                SET 
                    centroid_lon = """ + str(median[0]) + """,
                    centroid_lat = """ + str(median[1]) + """,
                    x_min = """ + str(bbox[0]) + """,
                    y_min = """ + str(bbox[1]) + """,
                    x_max = """ + str(bbox[2]) + """,
                    y_max = """ + str(bbox[3]) + """,
                    accuracy = '""" + accuracy + """'
                WHERE gp.woe_id = """ + str(woe_id) )

            db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    place_type = options.place_type
    
    #woe_locality | woe_lau  | woe_adm2 | woe_adm1 | woe_adm0
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Admin2' or place_type == 'County':
        place_type = 'County'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        place_type = 'LocalAdmin'
    elif place_type == 'Town' or place_type == 'Locality':
        place_type = 'Town'
    
    print "Evaluating", place_type, "..."
    
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = check_neighbors
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

from itertools import groupby

# Database details
user_name = ''
database_name = ''
table_name = ''
adjacency_db_table_name = ''
place_type = ''
search_buffer = 0.2

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-a', '--adjacency_db_table_name', dest='adjacency_db_table_name', default='geoplanet_adjacencies',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='Town',
                  help='Valid WOE placetypes are County, LocalAdmin, Town.')

parser.add_option('-c', '--compare_place_type', dest='compare_place_type', default='County',
                  help='Valid WOE placetypes are County, LocalAdmin, Town.')

parser.add_option('-b', '--search_buffer', dest='search_buffer', default=0.1,
                  help='Distance in map units (usually meters or decimal degrees) from the source place to the reference places to limit search to immediate neighborhood.')


(options, args) = parser.parse_args()

    
def evaluate_neighbors( woe_id ):    
    # Where is this place?
    cur.execute("""
        SELECT 
            ST_ASTEXT(the_geom),
            woe_adm2
        FROM 
            """ + db_table_name + """
        WHERE 
            woe_id = (%s)""", (woe_id,))
    
    this_woe_geom, reference_parent_id = cur.fetchone()
    
    # What does GeoPlanet say about this place's neighbors?
    cur.execute("""
        SELECT 
            neighbor_woe_id
        FROM 
            """ + adjacency_db_table_name + """
        WHERE 
            place_woe_id = (%s)""", (woe_id,))
    
    neighbors_list_raw = cur.fetchall()
    
    neighbors_list = []
    
    #tupples from fetch to basic list of ints
    for n in neighbors_list_raw:
        neighbors_list.append(n[0])
    
    #print "neighbors_list", neighbors_list
    
    # How many reference places should exist?
    neighbors_total = len(neighbors_list)
    
    limit = 20
    
    # Get all places within <search_buffer> meters of this place point for places of like type. 
    cur.execute("""
        select      woe_id,
                    {4}
        from        {0}
        where       ST_DWITHIN(
                        the_geom,
                        ST_SETSRID(ST_GEOMFROMTEXT('{1}'),4326),
                        {2}
                    )
        and         placetype = '{3}'
        and         woe_id != {6}
        order by    ST_DISTANCE(
                        the_geom,
                        ST_SETSRID(ST_GEOMFROMTEXT('{1}'),4326)
                    ) asc
        LIMIT {5};""".format(db_table_name, this_woe_geom, search_buffer, place_type, compare_place_type, limit, woe_id))

    ref_places = cur.fetchall()

    #Track how many spatial neighbors match expected database neighbors
    counter = 0
    parent_cohort_counter = 0
    
    parent_woes = []
    
    ref_places_len = len(ref_places)
    
    # Going nearest to farthest from the source point.
    for ref_place in ref_places:
        ref_woe_id, ref_parent_id = ref_place
        
        if ref_woe_id in neighbors_list:
            counter = counter + 1

        parent_woes.append( ref_parent_id )
        
    parent_cohort_counter = parent_woes.count(reference_parent_id)
    
    #print parent_woes, parent_cohort_counter, reference_parent_id

    accuracy = 'unknown'

    if neighbors_total > 0 and (counter is 0 and parent_cohort_counter is 0):
        accuracy = 'bad'

    if parent_cohort_counter > 1:
        if neighbors_total is 0:
            accuracy = 'good parents, null neighbors'
        else:
            accuracy = 'good parents'

    if counter > 0:
        accuracy = 'good neighbors'

    if counter > 0 and parent_cohort_counter > 0:
        accuracy = 'good neighbors and parents'

        if neighbors_total is not 0:
            fraction = float(counter) / neighbors_total

        if ref_places_len is not 0:
            parent_fraction = float(parent_cohort_counter) / ref_places_len
        
        if counter > 4 and fraction > .75 and parent_cohort_counter > 4 and parent_fraction > .75:
            accuracy = 'great neighbors and parents'
        
    #print '\t', accuracy

    #return (neighbors_total, counter, fraction, parent_cohort_counter, parent_fraction)
    
    return accuracy

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            woe_id, name
        FROM """ + db_table_name + 
        """ WHERE placetype = (%s) 
            AND accuracy = 'geonames match great'
            AND spatial_accuracy IS NULL
        ORDER BY woe_id
        LIMIT 37000
        OFFSET (37000 * 0)
        """, (place_type,))
        #""" WHERE placetype = (%s) AND photos = 0""", (place_type,))
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s for parent-type %s...' % (len(places), place_type, compare_place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        woe_id, name = place
    
        if total_places > 1000:
            if counter % 100 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
    
        accuracy = evaluate_neighbors( woe_id )
        
        if total_places > 1000:
            if counter % 100 == 0:
                print '\t%s' % (accuracy,)
        else:
            print '\t%s' % (accuracy,)
            
        cur.execute("""
            UPDATE 
                geoplanet_places
            SET 
                spatial_accuracy = '""" + accuracy + """'
            WHERE 
                woe_id = """ + str(woe_id) )

        db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    adjacency_db_table_name = options.adjacency_db_table_name
    place_type = options.place_type
    compare_place_type = options.compare_place_type
    search_buffer = options.search_buffer
    
    #woe_locality | woe_lau  | woe_adm2 | woe_adm1 | woe_adm0
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Admin1' or place_type == 'State':
        place_type = 'State'
    elif place_type == 'Admin2' or place_type == 'County':
        place_type = 'County'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        place_type = 'LocalAdmin'
    elif place_type == 'Town' or place_type == 'Locality':
        place_type = 'Town'
    elif place_type == 'Suburb' or place_type == 'Neighborhood':
        place_type = 'Suburb'
    
    if compare_place_type == 'Admin1' or compare_place_type == 'State':
        compare_place_type = 'woe_adm1'
    elif compare_place_type == 'Admin2' or compare_place_type == 'County':
        compare_place_type = 'woe_adm2'
    elif compare_place_type == 'Admin3' or compare_place_type == 'LocalAdmin' or compare_place_type == 'LAU':
        compare_place_type = 'woe_lau'
    else:
        print "Only Admin1, Admin2, and LocalAdmin are valid comparisions"
        exit (0)
    
    print "Evaluating", place_type, "..."
    
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = outliers
#!/usr/bin/env python
import sys
from time import time

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Outlier storage
MEDIAN_THRESHOLD = 5.0

# Database details
user_name = ''
database_name = ''
table_name = ''
place_type = ''
# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='geoplanet_places',
                  help='Name of table in Postgres database.')

parser.add_option('-p', '--place_type', dest='place_type', default='Locality',
                  help='Valid WOE placetypes are Country, State, County, LocalAdmin, Town, and Suburb.')

(options, args) = parser.parse_args()



def median_distances(pts, aggregate=numpy.median):
    median = (numpy.median([pt[0] for pt in pts]),
              numpy.median([pt[1] for pt in pts]))
    distances = []
    for pt in pts:
        dist = math.sqrt(((median[0]-pt[0])*math.cos(median[1]*math.pi/180.0))**2+(median[1]-pt[1])**2)
        distances.append((dist, pt))

    median_dist = aggregate([dist for dist, pt in distances])
    return (median_dist, distances, median)
    
def mean_distances(photos):
    return median_distances(photos, numpy.mean)

def load_photos( woe_id, place_filter={} ):
    cur.execute("""
        SELECT 
            longitude, latitude, photo_id
        FROM """ + db_photos + """
        WHERE woe_id = (%s)
        """, (woe_id,))
    
    photos = cur.fetchall()

    #print '\t', len(photos), 'photos'
    
    return photos

def discard_outliers(photos, threshold=MEDIAN_THRESHOLD):
    count = 0
    discarded = 0
    result = {}
    
    total_photos = len(photos)
    
    if chatty: 
        print '\tComputing outliers...'
    
    median_dist, distances, median = median_distances( photos )
    
    if chatty: 
        print '\tmedian_dist:', median_dist
    
    if median_dist > 0:
        keep = [pt for dist, pt in distances if dist < median_dist * threshold]
        discarded += total_photos - len(keep)

        if chatty: 
            print '\t%d photos discarded of %d total' % (discarded, total_photos)
        
        return (keep, median, discarded)
    else:
        if chatty: 
            print '\t%d photos discarded of %d total (dense cluster)' % (0, total_photos)

        return (photos, median, 0)

def get_bbox_for_place( photos ):
    bbox = [180, 90, -180, -90]
    
    for pt in photos:
        for i in range(4):
            bbox[i] = min(bbox[i], pt[i%2]) if i<2 else max(bbox[i], pt[i%2])
            
    return bbox

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            woe_id, name
        FROM """ + db_table_name + 
        """ WHERE placetype = (%s)""", (place_type,))
    
    places = cur.fetchall()
    
    print 'Evaluating %s places of type %s...' % (len(places), place_type)
    
    total_places = len(places)
    counter = 0
    for place in places:
        counter += 1
        
        woe_id, name = place
    
        if total_places > 10000:
            if counter % 1000 == 0:
                print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
        else:
            print '%s of %s: %s (%s)' % (counter, total_places, name, woe_id)
    
        photos = load_photos( woe_id )
        
        if len(photos) > 0:
            photos, median, discarded = discard_outliers( photos )
        
            bbox = get_bbox_for_place( photos )
            
            #print '\t%s: %s %s, %s %s' % (woe_id, bbox[0], bbox[1], bbox[2], bbox[3])
            #print '\t%s, %s' % (median[0], median[1])
            
            #Store result
            # Clear out the table first!
            #   DELETE FROM db_photos_clean;
            for photo in photos:            
                cur.execute("""
                    INSERT 
                    INTO """ + db_photos_clean + """
                        (photo_id, woe_id, longitude, latitude)
                    VALUES 
                        (""" + str(photo[2]) + """,""" 
                             + str(woe_id) + """,""" 
                             + str(photo[0]) + """,""" 
                             + str(photo[1]) + """)""" )

                db.commit()
                
            cur.execute("""
                UPDATE 
                    geoplanet_places gp
                SET 
                    centroid_lon = """ + str(median[0]) + """,
                    centroid_lat = """ + str(median[1]) + """,
                    x_min = """ + str(bbox[0]) + """,
                    y_min = """ + str(bbox[1]) + """,
                    x_max = """ + str(bbox[2]) + """,
                    y_max = """ + str(bbox[3]) + """,
                    photos = """ + str(len(photos)) + """,
                    outliers = """ + str(discarded) + """
                WHERE gp.woe_id = """ + str(woe_id) )

            db.commit()

        #if counter > 1000:
        #    break


if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    place_type = options.place_type
    
    # Normalize the WOE placetype and determine which table to read photos from
    if place_type == 'Country':
        db_photos = 'flickr_adm0_data'
    elif place_type == 'Admin' or place_type == 'State':
        place_type = 'State'
        db_photos = 'flickr_adm1_data'
    elif place_type == 'Admin2' or place_type == 'County':
        place_type = 'County'
        db_photos = 'flickr_adm2_data'
    elif place_type == 'Admin3' or place_type == 'LocalAdmin' or place_type == 'LAU':
        print 'Admin3 is not supported at this time.'
        place_type = 'LocalAdmin'
    elif place_type == 'Town' or place_type == 'Locality':
        place_type = 'Town'
        db_photos = 'flickr_locality_data'
    elif place_type == 'Suburb' or place_type == 'Neighborhood':
        place_type = 'Suburb'
        db_photos = 'flickr_neighborhood_data'
        
    db_photos_clean = db_photos + '_clean'

    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    main()
    
    app_time_end = time()
    app_time_total_minutes = round((app_time_end - app_time_start) / 1000 / 60, 1)
    
    print 'Outliers calculated in %s minutes.' % (app_time_total_minutes)
########NEW FILE########
__FILENAME__ = outliers_mark_ignore
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''

# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Explicate write and read database settings
db_write_results = ''
db_write_unique_id = ''
db_read_unique_id = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='quatroshapes_extras',
                  help='Name of table in Postgres database.')

parser.add_option('-c', '--count', dest='count', default=1,
                  help='How many neighbors must match to NOT be an outlier.')

(options, args) = parser.parse_args()



def load_parts( wkt, place_filter={} ):
    cur.execute("""
        SELECT 
            """ + db_write_unique_id + """ as id,
            COUNT(""" + db_write_unique_id + """) as neighbors
        FROM 
            """ + db_table_name + """
        WHERE 
            ST_Touches( poly_geom, ST_GeomFromText('""" + wkt + """', 4326) )
        GROUP BY 
            """ + db_write_unique_id + """
        ORDER BY 
            neighbors DESC;
        """)
    
    neighbors = cur.fetchall()
    #print '\t', len(neighbors), 'neighbors'
    
    return neighbors

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            """ + db_bounds_unique_id + """, """ + db_bounds_placename + """
            ST_AsText( db_bounds_geom_name ) as wkt
        FROM """ + db_bounds_table_name )
    
    places = cur.fetchall()
    
    print 'Evaluating %s places...' % (len(places),)
    
    total_places = len(places)
    counter = 0
    
    for place in places:
        counter += 1
        
        unique_id, name, zoom, row, col, wkt = place
    
        if total_places > 10000:
            if counter % 1000 == 0:
                print '%s of %s: %s (%s) at %s/%s/%s' % (counter, total_places, name, unique_id)
        else:
            print '%s of %s: %s (%s) at %s/%s/%s' % (counter, total_places, name, unique_id)
    
        parts = load_parts( unique_id )
        total_parts = len(parts)
            
        if total_parts > 0:
            
            # is at least one of the neighbors of the same id? if not:
            outlier = True
            c = 0
            
            #This should always be length of 8
            for n in parts:
                if n[0] == unique_id:
                    c = c + 1
                    
            if c >= count_threshold:
                outlier = False
            
            if outlier:
                cur.execute("""
                    UPDATE 
                        """ + db_write_results + """
                    SET 
                        """ + db_write_unique_id + """ = """ + str(neighbors[0][0]) + """
                    WHERE 
                        zoom = """ + str(zoom) + """ AND 
                        row = """ + str(row) + """ AND 
                        col = """ + str(col) )
                db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    count_threshold = options.count
    
    db_photos = 'quatroshapes_extras'
    db_write_results = 'quatroshapes_extras'
    db_write_unique_id = 'woe_id'
    db_read_unique_id = 'woe_id'
    db_bounds_table_name = 'geoname_checkin_counts'
    db_bounds_geom_name = 'poly_geom'
    db_bounds_unique_id = 'geoname_id'
    db_bounds_placename = 'gn_placename'
        
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = smooth
#!/usr/bin/env python
import sys
from time import time
from datetime import timedelta

import math
import numpy

from psycopg2 import connect
from optparse import OptionParser

# Database details
user_name = ''
database_name = ''
table_name = ''

# Assumed the photos table is stored in the same database as geoplanet
db_photos = ''
db_photos_clean = ''

# Explicate write and read database settings
db_write_results = ''
db_write_unique_id = ''
db_read_unique_id = ''

# Database connection using psycopg2
db = None
cur = None

chatty = False


parser = OptionParser(usage="""%prog [options]

For all places, find their photos and calculate if each photo is range in or an outlier.""")

parser.add_option('-u', '-U', '--db_user_name', dest='db_user_name', default='foursquare',
                  help='Name of Postgres user to connect as.')

parser.add_option('-d', '--db_name', dest='db_name', default='foursquare',
                  help='Name of Postgres database to connect to.')

parser.add_option('-t', '--db_table_name', dest='db_table_name', default='quatroshapes_extras',
                  help='Name of table in Postgres database.')

parser.add_option('-c', '--count', dest='count', default=1,
                  help='How many neighbors must match to NOT be an outlier.')

(options, args) = parser.parse_args()



def load_neighbors( wkt, place_filter={} ):
    cur.execute("""
        SELECT 
            """ + db_write_unique_id + """ as id,
            COUNT(""" + db_write_unique_id + """) as neighbors
        FROM 
            """ + db_table_name + """
        WHERE 
            ST_Touches( poly_geom, ST_GeomFromText('""" + wkt + """', 4326) )
        GROUP BY 
            """ + db_write_unique_id + """
        ORDER BY 
            neighbors DESC;
        """)
    
    neighbors = cur.fetchall()
    #print '\t', len(neighbors), 'neighbors'
    
    return neighbors

def main():
    #Get all the places of that placetype
    cur.execute("""
        SELECT 
            """ + db_write_unique_id + """, name, zoom, row, col,
            ST_AsText( poly_geom ) as wkt
        FROM """ + db_table_name )
    
    places = cur.fetchall()
    
    print 'Evaluating %s places...' % (len(places),)
    
    total_places = len(places)
    counter = 0
    
    for place in places:
        counter += 1
        
        unique_id, name, zoom, row, col, wkt = place
    
        if total_places > 10000:
            if counter % 1000 == 0:
                print '%s of %s: %s (%s) at %s/%s/%s' % (counter, total_places, name, unique_id, zoom, row, col)
        else:
            print '%s of %s: %s (%s) at %s/%s/%s' % (counter, total_places, name, unique_id, zoom, row, col)
    
        neighbors = load_neighbors( wkt )
        total_neighbors = len(neighbors)
            
        if total_neighbors > 0:
            
            # is at least one of the neighbors of the same id? if not:
            outlier = True
            c = 0
            
            #This should always be length of 8
            for n in neighbors:
                if n[0] == unique_id:
                    c = c + 1
                    
            if c >= count_threshold:
                outlier = False
            
            if outlier:
                cur.execute("""
                    UPDATE 
                        """ + db_write_results + """
                    SET 
                        """ + db_write_unique_id + """ = """ + str(neighbors[0][0]) + """
                    WHERE 
                        zoom = """ + str(zoom) + """ AND 
                        row = """ + str(row) + """ AND 
                        col = """ + str(col) )
                db.commit()
                
    return total_places

if __name__ == '__main__':
    app_time_start = time()

    db_user_name = options.db_user_name
    
    db_name = options.db_name
    db_table_name = options.db_table_name
    count_threshold = options.count
    
    db_photos = 'quatroshapes_extras'
    db_write_results = 'quatroshapes_extras'
    db_write_unique_id = 'woe_id'
    db_read_unique_id = 'woe_id'
        
    # Connect to the database        
    db = connect(user=db_user_name, database=db_name)
    cur = db.cursor()
    
    total_places = main()
        
    app_time_end = time()
    time_display = str( timedelta(seconds=(app_time_end - app_time_start)))
    app_time_total_minutes = round((app_time_end - app_time_start) / 60, 1)
    if app_time_total_minutes > 1: 
        ppm = round(float(total_places) / app_time_total_minutes)
    else:
        ppm = total_places
    
    print 'Caluclated %d bounds in %s (%s places per minute)' % (total_places, time_display, ppm)    
########NEW FILE########
__FILENAME__ = tilestache-seed
#!/usr/bin/env python
"""tilestache-seed.py will warm your cache.

This script is intended to be run directly. This example seeds the area around
West Oakland (http://sta.mn/ck) in the "osm" layer, for zoom levels 12-15:

    tilestache-seed.py -c ./config.json -l osm -b 37.79 -122.35 37.83 -122.25 -e png 12 13 14 15

See `tilestache-seed.py --help` for more information.
"""

from sys import stderr, path
from os.path import realpath, dirname
from optparse import OptionParser
from urlparse import urlparse
from urllib import urlopen
import itertools
from time import time
from datetime import timedelta
from math import pow

from ModestMaps.OpenStreetMap import Provider

from tilestacheexceptions import NothingMoreToSeeHere
from tilestacheexceptions import NothingToSeeHere

import imerge

try:
    from json import dump as json_dump
    from json import load as json_load
except ImportError:
    from simplejson import dump as json_dump
    from simplejson import load as json_load

osm = Provider()
coordinates = None

#
# Most imports can be found below, after the --include-path option is known.
#

parser = OptionParser(usage="""%prog [options] [zoom...]

Seeds a single layer in your TileStache configuration - no images are returned,
but TileStache ends up with a pre-filled cache. Bounding box is given as a pair
of lat/lon coordinates, e.g. "37.788 -122.349 37.833 -122.246". Output is a list
of tile paths as they are created.

Example:

    tilestache-seed.py -b 52.55 13.28 52.46 13.51 -c tilestache.cfg -l osm 11 12 13

Protip: extract tiles from an MBTiles tileset to a directory like this:

    tilestache-seed.py --from-mbtiles filename.mbtiles --output-directory dirname

Configuration, bbox, and layer options are required; see `%prog --help` for info.""")

defaults = dict(padding=0, verbose=True, enable_retries=False, reconnoiter=False, bbox=(37.777, -122.352, 37.839, -122.226))

parser.set_defaults(**defaults)

parser.add_option('-c', '--config', dest='config',
                  help='Path to configuration file, typically required.')

parser.add_option('-l', '--layer', dest='layer',
                  help='Layer name from configuration, typically required.')

parser.add_option('-b', '--bbox', dest='bbox',
                  help='Bounding box in floating point geographic coordinates: south west north east. Default value is %.3f, %.3f, %.3f, %.3f.' % defaults['bbox'],
                  type='float', nargs=4)

parser.add_option('-p', '--padding', dest='padding',
                  help='Extra margin of tiles to add around bounded area. Default value is %s (no extra tiles).' % repr(defaults['padding']),
                  type='int')

parser.add_option('-e', '--extension', dest='extension',
                  help='Optional file type for rendered tiles. Default value is "png" for most image layers and some variety of JSON for Vector or Mapnik Grid providers.')

parser.add_option('-f', '--progress-file', dest='progressfile',
                  help="Optional JSON progress file that gets written on each iteration, so you don't have to pay close attention.")

parser.add_option('-q', action='store_false', dest='verbose',
                  help='Suppress chatty output, --progress-file works well with this.')

parser.add_option('-i', '--include-path', dest='include_paths',
                  help="Add the following colon-separated list of paths to Python's include path (aka sys.path)")

parser.add_option('-d', '--output-directory', dest='outputdirectory',
                  help='Optional output directory for tiles, to override configured cache with the equivalent of: {"name": "Disk", "path": <output directory>, "dirs": "portable", "gzip": []}. More information in http://tilestache.org/doc/#caches.')

parser.add_option('--to-mbtiles', dest='mbtiles_output',
                  help='Optional output file for tiles, will be created as an MBTiles 1.1 tileset. See http://mbtiles.org for more information.')

parser.add_option('--to-s3', dest='s3_output',
                  help='Optional output bucket for tiles, will be populated with tiles in a standard Z/X/Y layout. Three required arguments: AWS access-key, secret, and bucket name.',
                  nargs=3)

parser.add_option('--from-mbtiles', dest='mbtiles_input',
                  help='Optional input file for tiles, will be read as an MBTiles 1.1 tileset. See http://mbtiles.org for more information. Overrides --extension, --bbox and --padding (this may change).')

parser.add_option('--tile-list', dest='tile_list',
                  help='Optional file of tile coordinates, a simple text list of Z/X/Y coordinates. Overrides --bbox and --padding.')

parser.add_option('--error-list', dest='error_list',
                  help='Optional file of failed tile coordinates, a simple text list of Z/X/Y coordinates. If provided, failed tiles will be logged to this file instead of stopping tilestache-seed.')

parser.add_option('--enable-retries', dest='enable_retries',
                  help='If true this will cause tilestache-seed to retry failed tile renderings up to (3) times. Default value is %s.' % repr(defaults['enable_retries']),
                  action='store_true')
                  
parser.add_option('--recon', '--reconnoiter', dest='reconnoiter',
                  help='If provided this will cause tilestache-seed to start with the first zoom and proceed to subsequent zooms, per tile, until the NothingMoreToSeeHere exception is raised. With this option, every tile is not guaranteed to render. Default value is %s.' % repr(defaults['reconnoiter']),
                  action='store_true')

parser.add_option('-x', '--ignore-cached', action='store_true', dest='ignore_cached',
                  help='Re-render every tile, whether it is in the cache already or not.')

parser.add_option('--jsonp-callback', dest='callback',
                  help='Add a JSONP callback for tiles with a json mime-type, causing "*.js" tiles to be written to the cache wrapped in the callback function. Ignored for non-JSON tiles.')

def generateCoordinates(ul, lr, zooms, padding):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Flood-fill coordinates based on two corners, a list of zooms and padding.
    """
    # start with a simple total of all the coordinates we will need.
    count = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)
        
        rows = lr_.row + 1 - ul_.row
        cols = lr_.column + 1 - ul_.column
        
        count += int(rows * cols)

    # now generate the actual coordinates.
    # offset starts at zero
    offset = 0
    
    for zoom in zooms:
        ul_ = ul.zoomTo(zoom).container().left(padding).up(padding)
        lr_ = lr.zoomTo(zoom).container().right(padding).down(padding)

        for row in range(int(ul_.row), int(lr_.row + 1)):
            for column in range(int(ul_.column), int(lr_.column + 1)):
                coord = Coordinate(row, column, zoom)
                
                yield (offset, count, coord)
                
                offset += 1

def generateSubquads2(coord, increment):
    increment = int(increment)
    origin = coord.zoomBy(increment)
    
    count = int(pow(2, increment) * pow(2, increment))
    offset = -1
    
    for a in range(0,int(pow(2, increment))):
        for b in range(0,int(pow(2, increment))):
            this = origin.right(a)
            this = this.down(b)
            offset += 1
            yield (offset, count, coord)
        
    

def generateSubquads(row, column, zoom):
    row0, col0, row1, col1, zoom1 \
        = row*2, column*2, row*2+1, column*2+1, zoom+1
    
    count = 4
    
    offset = 0

    for r in range(2):
        for c in range(2):
            if r==0 and c==0:
                coord = Coordinate(row0, col0, zoom1)
            if r==0 and c==1:
                coord = Coordinate(row0, col1, zoom1)
            if r==1 and c==0:
                coord = Coordinate(row1, col0, zoom1)
            if r==1 and c==1:
                coord = Coordinate(row1, col1, zoom1)
            
            #print coord
            
            # Ensure we only yield coords in the area of interest
            #if extentContainsCoord( render_bbox, coord ):
            #print '\t', coord
            yield (offset, count, coord)
            #else:
            #    continue

            offset += 1
            
def extentContainsCoord( container_extent, coord ):
    """ Tests contains extent of coordinate compared to  bounding box.
    """
    nw = osm.coordinateLocation(coord)
    se = osm.coordinateLocation(coord.right().down())

    coord_bounds = [ nw.lon, nw.lat, se.lon, se.lat ]
    
    # Assumes a cylindrical projection like Web Mercator with perpendicular latitudes and longitudes
    return not ( coord_bounds[0] > container_extent[2] 
                or coord_bounds[2] < container_extent[0]
                or coord_bounds[1] > container_extent[3]
                or coord_bounds[3] < container_extent[2]);
        
def listCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from a file with one Z/X/Y coordinate per line.
    """
    coords = (line.strip().split('/') for line in open(filename, 'r'))
    coords = (map(int, (row, column, zoom)) for (zoom, column, row) in coords)
    coords = [Coordinate(*args) for args in coords]
    
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield (offset, count, coord)

def tilesetCoordinates(filename):
    """ Generate a stream of (offset, count, coordinate) tuples for seeding.
    
        Read coordinates from an MBTiles tileset filename.
    """
    coords = MBTiles.list_tiles(filename)
    count = len(coords)
    
    for (offset, coord) in enumerate(coords):
        yield (offset, count, coord)

def parseConfigfile(configpath):
    """ Parse a configuration file and return a raw dictionary and dirpath.
    
        Return value can be passed to TileStache.Config.buildConfiguration().
    """
    config_dict = json_load(urlopen(configpath))
    
    scheme, host, path, p, q, f = urlparse(configpath)
    
    if scheme == '':
        scheme = 'file'
        path = realpath(path)
    
    dirpath = '%s://%s%s' % (scheme, host, dirname(path).rstrip('/') + '/')
    
    return config_dict, dirpath

def c():
    yield coordinates.next()

if __name__ == '__main__':
    options, zooms = parser.parse_args()

    if options.include_paths:
        for p in options.include_paths.split(':'):
            path.insert(0, p)

    from TileStache import getTile, Config
    from TileStache.Core import KnownUnknown
    from TileStache.Config import buildConfiguration
    from TileStache import MBTiles
    import TileStache
    
    from ModestMaps.Core import Coordinate
    from ModestMaps.Geo import Location

    try:
        # determine if we have enough information to prep a config and layer
        
        time_start = time()
        tiles_renderd = 0
        
        has_fake_destination = bool(options.outputdirectory or options.mbtiles_output)
        has_fake_source = bool(options.mbtiles_input)
        
        if has_fake_destination and has_fake_source:
            config_dict, config_dirpath = parseConfigfile(options.config)
            layer_dict = dict()
            
            config_dict['cache'] = dict(name='test')
            config_dict['layers'][options.layer or 'tiles-layer'] = layer_dict
        
        elif options.config is None:
            raise KnownUnknown('Missing required configuration (--config) parameter.')
        
        elif options.layer is None:
            raise KnownUnknown('Missing required layer (--layer) parameter.')
    
        else:
            config_dict, config_dirpath = parseConfigfile(options.config)
            
            if options.layer not in config_dict['layers']:
                raise KnownUnknown('"%s" is not a layer I know about. Here are some that I do know about: %s.' % (options.layer, ', '.join(sorted(config_dict['layers'].keys()))))
            
            layer_dict = config_dict['layers'][options.layer]
            layer_dict['write_cache'] = True # Override to make seeding guaranteed useful.
        
        # override parts of the config and layer if needed
        
        extension = options.extension

        if options.mbtiles_input:
            layer_dict['provider'] = dict(name='mbtiles', tileset=options.mbtiles_input)
            n, t, v, d, format, b = MBTiles.tileset_info(options.mbtiles_input)
            extension = format or extension
        
        # determine or guess an appropriate tile extension
        
        if extension is None:
            provider_name = layer_dict['provider'].get('name', '').lower()
            
            if provider_name == 'mapnik grid':
                extension = 'json'
            elif provider_name == 'vector':
                extension = 'geojson'
            else:
                extension = 'png'
        
        # override parts of the config and layer if needed
        
        tiers = []
        
        if options.mbtiles_output:
            tiers.append({'class': 'TileStache.MBTiles:Cache',
                          'kwargs': dict(filename=options.mbtiles_output,
                                         format=extension,
                                         name=options.layer)})
        
        if options.outputdirectory:
            tiers.append(dict(name='disk', path=options.outputdirectory,
                              dirs='portable', gzip=[]))

        if options.s3_output:
            access, secret, bucket = options.s3_output
            tiers.append(dict(name='S3', bucket=bucket,
                              access=access, secret=secret))
        
        if len(tiers) > 1:
            config_dict['cache'] = dict(name='multi', tiers=tiers)
        elif len(tiers) == 1:
            config_dict['cache'] = tiers[0]
        else:
            # Leave config_dict['cache'] as-is
            pass
        
        # create a real config object
        
        config = buildConfiguration(config_dict, config_dirpath)
        layer = config.layers[options.layer]
        
        # do the actual work
        
        lat1, lon1, lat2, lon2 = options.bbox
        south, west = min(lat1, lat2), min(lon1, lon2)
        north, east = max(lat1, lat2), max(lon1, lon2)
        
        render_bbox = [ west, north, east, south ]

        northwest = Location(north, west)
        southeast = Location(south, east)

        ul = layer.projection.locationCoordinate(northwest)
        lr = layer.projection.locationCoordinate(southeast)
                
        for (i, zoom) in enumerate(zooms):
            if not zoom.isdigit():
                raise KnownUnknown('"%s" is not a valid numeric zoom level.' % zoom)

            zooms[i] = int(zoom)
                    
        if options.padding < 0:
            raise KnownUnknown('A negative padding will not work.')

        padding = options.padding
        tile_list = options.tile_list
        error_list = options.error_list

    except KnownUnknown, e:
        parser.error(str(e))

    if tile_list:
        coordinates = listCoordinates(tile_list)
    elif options.mbtiles_input:
        coordinates = tilesetCoordinates(options.mbtiles_input)
    elif options.reconnoiter:
        #tiles_max_coverage = len(list(generateCoordinates(ul, lr, zooms, padding)))
        zoom_min = min(zooms)
        coordinates = generateCoordinates(ul, lr, [zoom_min], padding)
    else:
        coordinates = generateCoordinates(ul, lr, zooms, padding)
    
    coordinates = list(coordinates)
    
    for (offset, count, coord) in coordinates:
    #while coordinates:
        #offset, count, coord = coordinates.pop(0)
        
        path = '%s/%d/%d/%d.%s' % (layer.name(), coord.zoom, coord.column, coord.row, extension)

        progress = {"tile": path,
                    "offset": offset + 1,
                    "total": count}

        #
        # Fetch a tile.
        #
        
        attempts = options.enable_retries and 3 or 1
        rendered = False
        
        while not rendered:
            if options.verbose:
                print >> stderr, '%(offset)d of %(total)d...' % progress,
    
            try:
                mimetype, content = getTile(layer, coord, extension, options.ignore_cached)
                
                if 'json' in mimetype and options.callback:
                    js_path = '%s/%d/%d/%d.js' % (layer.name(), coord.zoom, coord.column, coord.row)
                    js_body = '%s(%s);' % (options.callback, content)
                    js_size = len(js_body) / 1024
                    
                    layer.config.cache.save(js_body, layer, coord, 'JS')
                    print >> stderr, '%s (%dKB)' % (js_path, js_size),
            
                elif options.callback:
                    print >> stderr, '(callback ignored)',
            
            except NothingMoreToSeeHere:
                #print 'NothingMoreToSeeHere'

                rendered = True
                #progress['size'] = '%dKB' % (len(content) / 1024)
    
                tiles_renderd = tiles_renderd + 1
            
                #if options.verbose:
                #    print >> stderr, '%(tile)s (%(size)s)' % progress
                #    print >> stderr, "Skipping tile %s's children." % (progress['tile'],)
            
                break

            except NothingToSeeHere:
                #print 'NothingToSeeHere'

                if options.verbose:
                    print >> stderr, "Skipping %s and all it's children." % (progress['tile'],)

                break

            except Exception as e:
                #
                # Something went wrong: try again? Log the error?
                #
                
                #if options.reconnoiter:
                #    break

                attempts -= 1

                if options.verbose:
                    print >> stderr, 'Failed %s, will try %s more.' % (progress['tile'], ['no', 'once', 'twice'][attempts])
            
                if attempts == 0:
                    if not error_list:
                        raise
                
                    fp = open(error_list, 'a')
                    fp.write('%(zoom)d/%(column)d/%(row)d\n' % coord.__dict__)
                    fp.close()
                    break
            
            else:
                #
                # Successfully got the tile.
                #
                rendered = True
                progress['size'] = '%dKB' % (len(content) / 1024)
                        
                if options.verbose:
                    print >> stderr, '%(tile)s (%(size)s)' % progress
                    
                if options.reconnoiter:
                    #print "got to reconnoiter..."
                    #if len(content) > 350:
                    if (coord.zoom+1) in zooms and (coord.zoom+1) <= max(zooms):
                        #coordinates.extend(generateSubquads2(coord, 2))
                        #coordinates = imerge(coordinates, generateSubquads2(coord, 1))
                        coordinates.extend( generateSubquads(coord.row, coord.column, coord.zoom) )
                        #coordinates = imerge(coordinates, generateSubquads(coord.row, coord.column, coord.zoom))
                        #coordinates = itertools.chain(coordinates, generateSubquads(coord.row, coord.column, coord.zoom))
                else:
                    tiles_renderd = tiles_renderd + 1            
                
        if options.progressfile:
            fp = open(options.progressfile, 'w')
            json_dump(progress, fp)
            fp.close()
            
    time_end = time()
    time_display = str( timedelta(seconds=(time_end - time_start)))
    time_total_minutes = round((time_end - time_start) / 60, 1)
    if time_total_minutes > 1: 
        tpm = round(float(tiles_renderd) / time_total_minutes)
    else:
        tpm = tiles_renderd
    
    print 'Stached %s tiles in %s (%s tpm)' % (tiles_renderd, time_display, tpm)

    #if options.reconnoiter:
    #    tiles_skipped = tiles_max_coverage - tiles_renderd
    #    print '\tSkipped %d tiles for a savings of %.2f%% over max coverage of %d tiles' % ( tiles_skipped, (float(tiles_skipped)/float(tiles_max_coverage)*100), tiles_max_coverage)
########NEW FILE########
__FILENAME__ = tilestacheexceptions
#!/usr/bin/env python

foo = 123

class NothingMoreToSeeHere(Exception):
    """ Don't recon any farther.
    
        This exception can be thrown in a provider to signal to
        TileStache.getTile() that the result tile should be returned,
        and saved in a cache, but no further child tiles should be rendered.
        Useful in cases where data is not well distributed geographically.
        
        The one constructor argument is an instance of PIL.Image or
        some other object with a save() method, as would be returned
        by provider renderArea() or renderTile() methods.
    """
    def __init__(self, tile):
        self.tile = tile
        Exception.__init__(self, tile)

class NothingToSeeHere(Exception):
    """ Don't recon any farther.
    
        This exception can be thrown in a provider to signal to
        TileStache.getTile() that the result tile should be returned,
        and but not saved in a cache and no further child tiles should be rendered.
        Useful in cases where data is not well distributed geographically.
    """
    def __init__(self):
        Exception.__init__(self)
########NEW FILE########
__FILENAME__ = tile_renderer_full_database
import csv, sys
from sys import argv, stdout, stderr
from subprocess import Popen
from os import stat, unlink

try:
    from json import JSONEncoder, loads as json_loads
except ImportError:
    from simplejson import JSONEncoder, loads as json_loads

import json

from stat import ST_SIZE
from time import time
from re import sub

from math import pow, log, floor, ceil

from psycopg2 import connect
#http://initd.org/psycopg/docs/usage.html#unicode-handling
import psycopg2.extensions

from PIL.ImageDraw import ImageDraw
from PIL import Image

from ModestMaps.Core import Coordinate
from ModestMaps.Tiles import toMicrosoft
from ModestMaps.Core import Coordinate
from ModestMaps.OpenStreetMap import Provider

from TileStache.Core import KnownUnknown
from TileStache.Vector import VectorResponse

from tilestacheexceptions import NothingMoreToSeeHere
from tilestacheexceptions import NothingToSeeHere

osm = Provider()

colors = [
    (0,0,0),
    (8,29,88),
    (37,52,148),
    (34,94,168),
    (29,145,192),
    (65,182,196),
    (127,205,187),
    (199,233,180),
    (237,248,177),
    (255,255,217)
    ]


cell_size = 8
min_size = 1
max_size = 1000000
log_base = (max_size - min_size) ** (1./len(colors))
method = "" 

fat_pixel_count = 32

input_field = ""
woe_field = ""

db_user_name = ""
db_read_name = ""
db_read_table_name = ""
db_write_name = ""
db_write_table_name = ""
        
db = None
cur = None


def size_color(size):
    """ Return an interpolated color for a given byte size.
    """
    index = 0
    if size > 0:
        index = 1
    if size > 29:
        index = 2
    if size > 49:
        index = 3
    if size > 74:
        index = 4
    if size > 99:
        index = 5
    if size > 199:
        index = 6
    if size > 499:
        index = 7
    if size > 999:
        index = 8
    if size > 1999:
        index = 9

    if( index > len(colors) ):
        index = len(colors) - 1
    if( index < 0 ):
        index = 0
            
    low_index = int(index)
    high_index = low_index + 1
    
    high_mix = index - low_index
    low_mix = 1 - high_mix
    
    r1, g1, b1 = colors[low_index]

    try:
        r2, g2, b2 = colors[high_index]
    except IndexError:
        return colors[-1]
    
    return (int(r1 * low_mix + r2 * high_mix),
            int(g1 * low_mix + g2 * high_mix),
            int(b1 * low_mix + b2 * high_mix))
            

def size_color_log(size):
    """ Return an interpolated color for a given byte size.
    """
    try:
        index = log(size - min_size) / log(log_base)
        if( index > len(colors) ):
            index = len(colors) - 1
        if( index < 0 ):
            index = 0
    except ValueError:
        index = 0
    
    low_index = int(index)
    high_index = low_index + 1
    
    high_mix = index - low_index
    low_mix = 1 - high_mix
    
    r1, g1, b1 = colors[low_index]

    try:
        r2, g2, b2 = colors[high_index]
    except IndexError:
        return colors[-1]
    
    return (int(r1 * low_mix + r2 * high_mix),
            int(g1 * low_mix + g2 * high_mix),
            int(b1 * low_mix + b2 * high_mix))


def size_color_unique_id(unique_id=999999999):
    """ Return an interpolated color for a given byte size.
    """
    #r1 = size[-3:]
    #g1 = size[-6:-3]
    #b1 = size[-9:-6]
    
    red = (unique_id >> 16) & 0xff
    green = (unique_id >> 8) & 0xff
    blue = unique_id & 0xff
    
    try:
        red = int( float(red) / 1000 * 255)
        green = int( float(green) / 1000 * 255)
        blue = int( float(blue) / 1000 * 255)
        return (red,green,blue)
    except:
        return (255,255,255)
        
def count_votes( self, coord ):
    cood_start_time = time()
    
    #Defaults
    woe_id_0, woe_lau_0, woe_adm2_0, woe_adm1_0, woe_adm0_0, name_0, photo_count_0 = [-1,-1,-1,-1,-1,u"-1",-1]
    woe_id_1, name_1, photo_count_1 = [-1,u"-1",-1]
    #woe_id_2, name_2, photo_count_2 = [-1,u"-1",-1]
    #woe_id_3, name_3, photo_count_3 = [-1,u"-1",-1]
    #woe_id_4, name_4, photo_count_4 = [-1,u"-1",-1]

    ne = osm.coordinateLocation(coord.right())
    sw = osm.coordinateLocation(coord.down())

    #print "db_user_name:", self.db_user_name, " db_read_name: ", self.db_read_name
    #self.db = connect(user=self.db_user_name, database=self.db_read_name)
    #curs = self.db.cursor()

    curs = self.db.cursor()
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, curs)

    curs.execute("""
        SELECT 
            """ + self.woe_field + """
        FROM """ + self.db_read_table_name + 
        """ WHERE photo_geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
        LIMIT 1
    """, (sw.lon, sw.lat, ne.lon, ne.lat))

        #AND
        #""" + self.db_read_table_name + """.""" + self.woe_field + """ NOT IN (1648473,1625084,1646678,1642911,1645524,1649378) AND 
        #""" + self.db_read_table_name + """.level IN (7,14,35)

    
    # if we have photos
    # if we've done the subquads for a quad who's WOE is only itself (identity)
    # if we've got some photos but not a lot of photos and we're at the minimum viable zoom
    # or we're at the max zoom
    
    is_saveable = False
    
    # Do we want to do the min_zoom + 1 logic again?
    try:
        photo_count_total = curs.fetchone()[0]

        curs.execute("""
            SELECT 
                COUNT(""" + self.db_read_table_name + """.latitude) as "photos"
            FROM """ + self.db_read_table_name + 
            """ WHERE photo_geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
        """, (sw.lon, sw.lat, ne.lon, ne.lat))
            
            #AND
            #""" + self.db_read_table_name + """.""" + self.woe_field + """ NOT IN (1648473,1625084,1646678,1642911,1645524,1649378) AND 
            #""" + self.db_read_table_name + """.level IN (7,14,35)

        photo_count_total = curs.fetchone()[0]

        if photo_count_total > 0:
            # Are we at the last requested zoom?
            if coord.zoom == self.max_zoom:
                is_saveable = True
            if (coord.zoom >= self.min_zoom): # and (photo_count_total <= self.min_size):
                is_saveable = True
    
    except:
        is_saveable = False
        photo_count_total = 0
    
    #print 'photo_count_total', photo_count_total, 'is_saveable', is_saveable

    if is_saveable:
        #sw = { 'lon':-123.04962, 'lat': 38.23387 }
        #ne = { 'lon': -121.81091, 'lat': 37.54675 }

        #SELECT
        #    flickr_locality_data.woe_id as "woe_id", geoplanet_places.name as "name", COUNT(flickr_locality_data.latitude) as "photos"
        #FROM
        #    flickr_locality_data, geoplanet_places
        #WHERE
        #    flickr_locality_data.woe_id = geoplanet_places.woe_id AND flickr_locality_data.photo_geom && ST_SetSRID(ST_MakeBox2D(ST_MakePoint(-123.04962, 38.23387), ST_MakePoint(-121.81091, 37.54675)), 4326) GROUP BY flickr_locality_data.woe_id, geoplanet_places.name ORDER BY photos DESC LIMIT 5;

        #curs.execute("""
            #SELECT 
            #    """ + self.db_read_table_name + """.""" + self.woe_field + """ as "woe_id", 
            #    """ + self.db_read_table_name + """.woe_lau as "woe_lau", 
            #    """ + self.db_read_table_name + """.woe_adm2 as "woe_adm2", 
            #    """ + self.db_read_table_name + """.woe_adm1 as "woe_adm1", 
            #    """ + self.db_read_table_name + """.woe_adm0 as "woe_adm0", 
            #    geoplanet_places.name as "name", 
            #    COUNT(""" + self.db_read_table_name + """.latitude) as "photos"
            #FROM
            #    """ + self.db_read_table_name + """, geoplanet_places
            #WHERE 
            #    """ + self.db_read_table_name + """.""" + self.woe_field + """ = geoplanet_places.woe_id AND 
            #    """ + self.db_read_table_name + """.photo_geom && 
            #    ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
            #GROUP BY 
            #    """ + self.db_read_table_name + """.""" + self.woe_field + """,
            #    """ + self.db_read_table_name + """.woe_lau,
            #    """ + self.db_read_table_name + """.woe_adm2,
            #    """ + self.db_read_table_name + """.woe_adm1,
            #    """ + self.db_read_table_name + """.woe_adm0,
            #    geoplanet_places.name ORDER BY photos DESC LIMIT 5;
            #""", (sw.lon, sw.lat, ne.lon, ne.lat))

        if self.woe_method == "woe":
            try:
                curs.execute("""
                    SELECT 
                        """ + self.db_read_table_name + """.""" + self.woe_field + """ as "woe_id", 
                        'lookup' as "name", 
                        COUNT(""" + self.db_read_table_name + """.latitude) as "photos"
                    FROM
                        """ + self.db_read_table_name + """
                    WHERE 
                        """ + self.db_read_table_name + """.photo_geom && 
                        ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
                    GROUP BY 
                        """ + self.db_read_table_name + """.""" + self.woe_field + """
                        ORDER BY photos DESC LIMIT 2;
                    """, (sw.lon, sw.lat, ne.lon, ne.lat))

                #curs.execute("""
                #    SELECT 
                #        """ + self.db_read_table_name + """.""" + self.woe_field + """ as "woe_id", 
                #        geoplanet_places.name as "name", 
                #        COUNT(""" + self.db_read_table_name + """.latitude) as "photos"
                #    FROM
                #        """ + self.db_read_table_name + """, geoplanet_places
                #    WHERE 
                #        """ + self.db_read_table_name + """.""" + self.woe_field + """ = geoplanet_places.woe_id AND 
                #        """ + self.db_read_table_name + """.photo_geom && 
                #        ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
                #    GROUP BY 
                #        """ + self.db_read_table_name + """.""" + self.woe_field + """,
                #        geoplanet_places.name ORDER BY photos DESC LIMIT 3;
                #    """, (sw.lon, sw.lat, ne.lon, ne.lat))

                #wait(dbs)
                #gevent_psycopg2.gevent_wait_callback(dbs)

                #result = curs.fetchall()
            except Exception, e:
                print e
                pass
        if self.woe_method == "checkins":
            woe_adm0_0 = -100
            try:
                curs.execute("""
                    SELECT 
                        """ + self.db_read_table_name + """.geoname_id as "woe_id", """
                        #""" + self.db_read_table_name + """.gn_placename as "name", 
                        """COUNT(""" + self.db_read_table_name + """.latitude) as "photos"
                    FROM
                        """ + self.db_read_table_name + """
                    WHERE 
                        """+ self.db_read_table_name + """.photo_geom && 
                        ST_SetSRID(ST_MakeBox2D(ST_MakePoint((%s), (%s)), ST_MakePoint((%s), (%s))), 4326)
                    GROUP BY 
                        """ + self.db_read_table_name + """.geoname_id
                    ORDER BY photos DESC LIMIT 2;
                    """, (sw.lon, sw.lat, ne.lon, ne.lat))

                        #""" + self.db_read_table_name + """.geoname_id NOT IN (1648473,1625084,1646678,1642911,1645524,1649378) AND 
                        #""" + self.db_read_table_name + """.level IN (7,14,35) AND 
                        #""" + self.db_read_table_name + """.gn_placename

                        #""" + self.db_read_table_name + """.level IN (8,9,10,12) AND 
                #wait(dbs)
                #gevent_psycopg2.gevent_wait_callback(dbs)

                #result = curs.fetchall()
            except Exception, e:
                print e
                pass
        
        try:
            #woe_id_0, woe_lau_0, woe_adm2_0, woe_adm1_0, woe_adm0_0, name_0, photo_count_0 = curs.fetchone()
            woe_id_0, photo_count_0 = curs.fetchone()
            name_0 = 'lookup'
        except Exception, e:
            #print 'oops', e
            woe_id_0, woe_lau_0, woe_adm2_0, woe_adm1_0, woe_adm0_0, name_0, photo_count_0 = [-1,-1,-1,-1,-1,u"-1",-1]
        
        try:
            #woe_id_1, woe_lau_1, woe_adm2_1, woe_adm1_1, woe_adm0_1, name_1, photo_count_1 = curs.fetchone()
            woe_id_1, photo_count_1 = curs.fetchone()
            name_1 = 'lookup'
        except Exception, e:
            #print 'oops', e
            woe_id_1, name_1, photo_count_1 = [-1,u"-1",-1]

        #try:
            #woe_id_2, woe_lau_2, woe_adm2_2, woe_adm1_2, woe_adm0_2, name_2, photo_count_2 = curs.fetchone()
        #    woe_id_2, name_2, photo_count_2 = curs.fetchone()
        #except:
        #    woe_id_2, name_2, photo_count_2 = [-1,u"-1",-1]

        #try:
            #woe_id_3, woe_lau_3, woe_adm2_3, woe_adm1_3, woe_adm0_3, name_3, photo_count_3 = curs.fetchone()
        #    woe_id_3, name_3, photo_count_3 = curs.fetchone()
        #except:
        #    woe_id_3, name_3, photo_count_3 = [-1,"-1",-1]

        #try:
            #woe_id_4, woe_lau_4, woe_adm2_4, woe_adm1_4, woe_adm0_4, name_4, photo_count_4 = curs.fetchone()
        #    woe_id_4, name_4, photo_count_4 = curs.fetchone()
        #except:
        #    woe_id_4, name_4, photo_count_4 = [-1,"-1",-1]
    
    
    if photo_count_0 > 0:
        margin = 1
    
    if photo_count_0 > 0 and photo_count_1 > 0:
        percent_0 = float(photo_count_0) / float(photo_count_total)
        percent_1 = float(photo_count_1) / float(photo_count_total)
        margin = percent_0 - percent_1
    
    if photo_count_1 == -1:
        margin = -1
        
    #print 'woe_id_0', woe_id_0, 'name_0', name_0, 'photo_count_0', photo_count_0
    
    result = {  "zoom":coord.zoom, 
                "column":coord.column, 
                "row":coord.row, 
                "time":(time() - cood_start_time), 
                "photo_count_total":photo_count_total, 
                "size":photo_count_total, # for compatibility
                "woe_id0":woe_id_0, 
                "woe_id0_lau":woe_lau_0, 
                "woe_id0_adm2":woe_adm2_0, 
                "woe_id0_adm1":woe_adm1_0, 
                "woe_id0_adm0":woe_adm0_0, 
                "name0":name_0, 
                "photo_count0":photo_count_0, 
                "margin0":margin
#                "woe_id1":woe_id_1, 
#                "name1":name_1, 
#                "photo_count1":photo_count_1, 
#                "woe_id2":woe_id_2, 
#                "name2":name_2, 
#                "photo_count2":photo_count_2 #, 
#                "woe_id3":woe_id_3, 
#                "name3":name_3, 
#                "photo_count3":photo_count_3, 
#                "woe_id4":woe_id_4, 
#                "name4":name_4, 
#                "photo_count4":photo_count_4
            }
            
    #print result

    return result

def getAdmins( woe_id ):
        # don't expect every coord to exist in the data file
        adm0_woe_id0, adm1_woe_id0, adm2_woe_id0, lau_woe_id0 = ["-1","-1","-1","-1"]
        
        #if neighborhood, then most often it's geoplanet_places.parent_id of that object?
        #SELECT
        #     geoplanet_admins.country_woe_id AS "country_woe_id", 
        #     geoplanet_admins.state_woe_id AS "state_woe_id", 
        #     geoplanet_admins.county_woe_id AS "county_woe_id", 
        #     geoplanet_admins.local_admin_woe_id AS "local_admin_woe_id"
        #FROM
        #    geoplanet_admins
        #WHERE
        #    geoplanet_admins.woe_id = 2355561;
                
        if db_read_table_name == 'flickr_neighborhood_data':
            cur.execute("""
                SELECT 
                    parent_id
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(woe_id) + """;""")
            locality = cur.fetchone()[0]
        else: 
            locality = woe_id
        
        locality = str(locality)

        if locality != "-1":
            cur.execute("""
                SELECT 
                    geoplanet_admins.country_woe_id,
                    geoplanet_admins.state_woe_id,
                    geoplanet_admins.county_woe_id,
                    geoplanet_admins.local_admin_woe_id
                FROM
                    geoplanet_admins
                WHERE 
                    woe_id = """ + locality + """;""")
            
            adm0_woe_id0, adm1_woe_id0, adm2_woe_id0, lau_woe_id0 = cur.fetchone()
        
        adm0_name0, adm1_name0, adm2_name0, lau_name0 = ["-1","-1","-1","-1"]
                
        if adm0_woe_id != "-1":
            cur.execute("""
                SELECT 
                    name
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(adm0_woe_id) + """;""")
            try:
                adm0_name = cur.fetchone()[0]
            except:
                pass
        
        if adm1_woe_id != "-1":
            cur.execute("""
                SELECT 
                    name
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(adm1_woe_id) + """;""")
            try:
                adm1_name = cur.fetchone()[0]
            except:
                pass
        
        if adm2_woe_id != "-1":
            cur.execute("""
                SELECT 
                    name
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(adm2_woe_id) + """;""")
            try:
                adm2_name = cur.fetchone()[0]
            except:
                pass
            
        if lau_woe_id != "-1":
            cur.execute("""
                SELECT 
                    name
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(lau_woe_id) + """;""")
            try:
                lau_name = cur.fetchone()[0]
            except:
                pass
        
        woe_name = '-1'
        
        if locality != "-1":
            cur.execute("""
                SELECT 
                    name
                FROM
                    geoplanet_places
                WHERE 
                    woe_id = """ + str(locality) + """;""")
            try:
                woe_name = cur.fetchone()[0]
            except:
                pass
        
        admins = {}
        
        admins['adm0_woe_id'] = str(adm0_woe_id)
        admins['adm1_woe_id'] = str(adm1_woe_id)
        admins['adm2_woe_id'] = str(adm2_woe_id)
        admins['lau_woe_id'] = str(lau_woe_id)
        admins['locality_woe_id'] = str(locality)
        
        admins['adm0_name'] = adm0_name
        admins['adm1_name'] = adm1_name
        admins['adm2_name'] = adm2_name
        admins['lau_name'] = lau_name
        admins['locality_name'] = woe_name
        
        #print 'admins', admins
        
        return admins

def saveTileToDatabase( self, interactivity_array ):
    for fat_pixel in interactivity_array:
        #if fat_pixel["woe_id"] == -1:
        #    continue
        
        #print 'getting admins...'
        #admins = getAdmins( fat_pixel["woe_id"] )        
        #print 'admins:', admins
                #(woe_id, name, photo_count, photo_count_total, latitude, longitude, woe_adm0, woe_adm1, woe_adm2, woe_lau, locality_lau, name_adm0, name_adm1, name_adm2, name_lau, name_locality, zoom)
        
        #print "saving...", fat_pixel
        #print "saving...", fat_pixel["photo_count"], " in ", fat_pixel["name"]
        
        curs = self.db.cursor()
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, curs)

        curs.execute("""
            INSERT 
            INTO """ + self.db_write_table_name + """
                (woe_id, name, photo_count, photo_count_total, margin, latitude, longitude, x1, y1, x2, y2, row, col, zoom)
            VALUES 
                (""" + str(fat_pixel["woe_id"]) + """,E'""" 
                     + sub("'", "\\'", fat_pixel["name"]) + """',""" 
                     + str(fat_pixel["photo_count"]) + """,""" 
                     + str(fat_pixel["photo_count_total"]) + """,""" 
                     + str(fat_pixel["margin"]) + ""","""
                     + str(fat_pixel["latitude"]) + """,""" 
                     + str(fat_pixel["longitude"]) + """,""" 
                     + fat_pixel["x1"] + """,""" 
                     + fat_pixel["y1"] + """,""" 
                     + fat_pixel["x2"] + """,""" 
                     + fat_pixel["y2"] + """,""" 
                     + fat_pixel["row"] + """,""" 
                     + fat_pixel["col"] + """,""" 
                     + str(fat_pixel["zoom"]) + """)""" )

                     #+ admins['adm0_woe_id'] + """,""" 
                     #+ admins['adm1_woe_id'] + """,""" 
                     #+ admins['adm2_woe_id'] + """,""" 
                     #+ admins['lau_woe_id'] + """,""" 
                     #+ admins['locality_woe_id'] + """,""" 
                     #+ admins['adm0_name'] + """,""" 
                     #+ admins['adm1_name'] + """,""" 
                     #+ admins['adm2_name'] + """,""" 
                     #+ admins['lau_name'] + """,""" 
                     #+ admins['locality_name'] + """,""" 

        self.db.commit()
                    
def create_utf_grid( self, interactivity_array ):
    # https://github.com/mapbox/utfgrid-spec/blob/master/1.2/utfgrid.md
    
    #3. Figure out how many unique WOEIDs you have present
    grid = []   # new "" string for each row, columns are by UTF chars; 
    keys = []   # keys in utf order as strings
    data = {}   # data that appears in the interactivity popup, key as in keys, value is arbitrary
    
    #4. Make a dictionary of attributes for those WOEIDs and populate it
    for fat_pixel in interactivity_array:
        if fat_pixel["woe_id"] == -1:
            character = ''
        else:
            character = str(fat_pixel["woe_id"])
        data[ character ] = fat_pixel["name"]
        # + "\n" + interactivity_array["name"] + "\n" + interactivity_array["photo_count"] + " of " interactivity_array["photo_count_total"] + "(" + int( float(interactivity_array["photo_count"]) / interactivity_array["photo_count_total"] * 100 ) + ") photos"
    
    for k, v in data.iteritems():
        #print k, v
        keys.append( k )
        
    #JSON doesn't allow control characters, " and \ to be encoded as their literal UTF-8 representation. 
    #Encoding an ID works as follows:
    #Add 32 to the key index. (avoiding gibberish 32 non-displaying characters at beginning of code page)
    #If the result is >= 34, add 1. (avoiding " quote character)
    #If the result is >= 92, add 1. (avoiding \ back-slash character)
    
    row_counter = 0
    row_content = ""
    
    for x in range(len(interactivity_array)):
        fat_pixel = interactivity_array[x]
        
        # find the index in the keys for this cell value
        try:
            code = keys.index( str(fat_pixel["woe_id"]) )
        except:
            code = 0

        code = code + 32
        if code >= 34: 
            code = code + 1
        if code >= 92:
            code = code + 1
        
        # are we at a new row, and not the first row?
        if x % fat_pixel_count == 0 and x > 0:
            grid.append( row_content )
            #print row_content
            row_content = ""
        else:
            row_content += unichr( code )
    
    utf_grid_result = { 'grid':grid, 'keys':keys, 'data':data } 
    
    #print "utf_grid_result: ", utf_grid_result
    
    return utf_grid_result

class Provider:
    
    def __init__(self,  layer, 
                        cell_size=8, #fatbits, yo
                        min_zoom=7, # min zoom before we start saving results
                        max_zoom=8, # or don't go any farther
                        input_field="size", 
                        woe_field="woe_id",
                        output_format="image", #or geojson, or interactivity
                        min_size=1, 
                        max_size=1000000, 
                        margin_percent=1,
                        method="size_log",
                        db_user_name="foursquare", 
                        db_read_name="foursquare",
                        db_read_table_name="flickr_locality_data",
                        db_write_name="",   #not used
                        db_write_table_name="", #not used
                        num_processes=1,
                        woe_method = "woe"
                        
                ):
        """
        """
        self.layer = layer
        self.cell_size = cell_size
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.min_size = min_size
        self.max_size = max_size
        self.margin_percent = margin_percent
        self.method = method 
        self.input_field = input_field
        self.woe_field = woe_field
        self.output_format = output_format
        self.woe_method = woe_method
        
        self.db_user_name = db_user_name
        self.db_read_name = db_read_name
        self.db_read_table_name = db_read_table_name
        self.db_write_name =db_write_name
        self.db_write_table_name = db_write_table_name
        self.num_processes = num_processes
        
        if len(self.db_write_name) > 0 and len(self.db_write_table_name) > 0:
            self.db_export = True
        
        self.log_base = (max_size - min_size) ** (1./len(colors))

        #print "db_user_name:", self.db_user_name, " db_read_name: ", self.db_read_name
        
        # Connect to the database        
        self.db = connect(user=self.db_user_name, database=self.db_read_name)
        self.cur = self.db.cursor()
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, self.cur)
        
    def renderTile(self, width, height, srs, coord):
        """
        """
        img = Image.new('RGB', (width, height), colors[0])
        draw = ImageDraw(img)
        
        interactivity_array = []
        
        base_zoom = coord.zoom
        base_row = coord.row
        base_column = coord.column
        
        #We're showing detail for three zooms in from here, as fat pixels (32 pix)
        #256 pixels / tile = 8 pixels / tile = 32 pixels (which is 2^5)

        tile_pixel_width = 256
        #print 'coord:', coord
        #print 'base_zoom:', base_zoom
        
        # 256 pixel tile == 2^8 pixel tile, so this is a constant
        tile_power_of_two = 8
        
        # we want 8x8 fatbits == 2^3 pixel fatbits
        #TODO: use self.cell_size to find log of 2 to x?
        pixel_power_of_two = int(log( self.cell_size, 2 ))
        
        fat_pixel_width = 2**pixel_power_of_two
        self.fat_pixel_count = 2**(tile_power_of_two - pixel_power_of_two)

        # adjust the coord to be the pixel zoom
        coord = coord.zoomBy(tile_power_of_two - pixel_power_of_two)
        
        #print "fat_pixel_count: ", fat_pixel_count
        #print "coord: ", coord       
        #print 'over_sample_zoom_tile_width: ', over_sample_zoom_tile_width
        
        #find the fat_pixel with the maximum photo count
        max_count = 0
        top_count = 0
        top_margin = 0
        
        #We should be seeing 64 cells (8x8) output image
        for row in range( self.fat_pixel_count ):
            for col in range( self.fat_pixel_count ):
                
                ul = coord.right(col).down(row)
                lr = ul.right().down()
                
                #Calculate key for the size dict
                subquad = Coordinate(ul.row, ul.column, ul.zoom)
                
                #print 'subquad:', subquad
                
                # these values should always be within (0, 256)
                x1 = col * fat_pixel_width
                x2 = (col + 1) * fat_pixel_width
                y1 = row * fat_pixel_width
                y2 = (row + 1) * fat_pixel_width
                
                #Draw fat pixel based on the returned color based on count (size) in that subquad in the dictionary
                #Implied that no-data is color[0], above where the img is instantiated
                
                enumeration = count_votes( self, subquad )
                                
                if max_count < enumeration["photo_count_total"]:
                    max_count = enumeration["photo_count_total"]
                
                if top_count < enumeration["photo_count0"]:
                    top_count = enumeration["photo_count0"]
                    
                if self.output_format == "utf_grid":
                    nw = osm.coordinateLocation(subquad)
                    se = osm.coordinateLocation(subquad.right().down())

                    lat = (nw.lat - se.lat) / 2 + se.lat
                    lon = (se.lon - nw.lon) / 2 + nw.lon
                                        
                    interactivity_array.append( {   "photo_count_total":enumeration["photo_count_total"], 
                                                    "woe_id":enumeration["woe_id0"], 
                                                    #"woe_id_lau":enumeration["woe_id0_lau"], 
                                                    #"woe_id_adm2":enumeration["woe_id0_adm2"], 
                                                    #"woe_id_adm1":enumeration["woe_id0_adm1"], 
                                                    "woe_id_adm0":enumeration["woe_id0_adm0"],
                                                    "name":enumeration["name0"], 
                                                    "photo_count":enumeration["photo_count0"],
                                                    "margin":enumeration["margin0"],
                                                    "latitude":lat,
                                                    "longitude":lon, 
                                                    "x1": str(nw.lon),
                                                    "y1": str(se.lat),
                                                    "x2": str(se.lon),
                                                    "y2": str(nw.lat),
                                                    "row":str(base_row + row),
                                                    "col":str(base_column + col),
                                                    "zoom": coord.zoom } )
                elif self.method == "size_log":
                    draw.rectangle((x1, y1, x2, y2), size_color_log(int( enumeration[self.input_field]) ))
                elif self.method == "size":
                    draw.rectangle((x1, y1, x2, y2), size_color(int( enumeration[self.input_field]) ))
                elif self.method == "unique_id":
                    draw.rectangle((x1, y1, x2, y2), size_color_unique_id(int( enumeration[self.input_field]) )) 

        if self.output_format == "utf_grid":
            #print "interactivity_array: ", interactivity_array
            #grid_utf = create_utf_grid( self, interactivity_array )
            grid_utf = { 'grid':['','.'] }
                
            if max_count == 0:
                raise NothingToSeeHere()
            
            is_saveable = False
            
            # Are we at the last requested zoom?
            if coord.zoom == self.max_zoom:
                is_saveable = True
            # Are we at the minimum viable zoom but with little to no data?
            if (coord.zoom >= self.min_zoom) and (max_count <= self.min_size):
                is_saveable = True
            # Are we viable zoom, viable count, and no ambiguity as to the 100% within margin the winner?
            if (coord.zoom >= (self.min_zoom + 2)) and (max_count > self.max_size) and ((top_count >= (max_count * self.margin_percent)) or ((max_count - top_count) < self.min_size)):
                is_saveable = True
            # Don't want to dig for needles
            #if coord.zoom == 17 and base_row == 50816 and base_column == 21045:
            #    print '(coord.zoom >= (self.min_zoom + 1)) and ((max_count - top_count) < self.min_size):'
            #    print coord.zoom,(self.min_zoom + 1),max_count, top_count, self.min_size
            if (coord.zoom >= (self.min_zoom + 1)) and ((max_count - top_count) < self.min_size):
            #(max_count > self.min_size) and 
                is_saveable = True

            # and (interactivity_array["margin"] >= self.margin_percent)

            if is_saveable:
                #print "should save to DB"
                #print "interactivity_array: ", interactivity_array                
                saveTileToDatabase( self, interactivity_array )
                raise NothingMoreToSeeHere( SaveableResponse(json.dumps(grid_utf)) )
            else:            
                return SaveableResponse(json.dumps(grid_utf))
                
        elif self.output_format == "geojson":
            grid_utf = create_utf_grid( self, interactivity_array )
            return SaveableResponse(json.dumps(grid_utf))
        else:
            return img
            
    def getTypeByExtension(self, extension):
        """ Get mime-type and format by file extension.

            This only accepts png (image), json (utf_grid interactivity), or geojson (vector)".
        """
        
        if self.output_format == "utf_grid":        
            if extension.lower() != 'json':
                raise KnownUnknown('FourSquare provider only makes .json tiles, not "%s"' % extension)

        if extension.lower() == 'json':
            return 'text/json', 'JSON'

        if extension.lower() == 'geojson':
            return 'text/json', 'GeoJSON'
        
        if extension.lower() == 'png':
            return 'image/png', 'PNG'
    
        raise KnownUnknown('FourSquare Provider only makes .geojson, .json, and .png tiles, not "%s"' % extension)

class SaveableResponse:
    """ Wrapper class for JSON response that makes it behave like a PIL.Image object.

        TileStache.getTile() expects to be able to save one of these to a buffer.
    """
    def __init__(self, content):
        self.content = content

    def save(self, out, format):
        #
        # Serialize
        #
        if format in ('GeoJSON'):
            #print "GeoJSON: ", self.content
            content = self.content
            
            #if 'wkt' in content['crs']:
            #    content['crs'] = {'type': 'link', 'properties': {'href': '0.wkt', 'type': 'ogcwkt'}}
            #else:
            #    del content['crs']

        elif format in ('PNG'):
            content = self.content
        
        else:
            raise KnownUnknown('FourSquare response only saves .png, .json, and .geojson tiles, not "%s"' % format)

        #
        # Encode
        #
        if format in ('GeoJSON'):
            #indent = self.verbose and 2 or None
            indent = 2
            
            encoded = JSONEncoder(indent=indent).iterencode(content)
            out.write(encoded)

        elif format in ('JSON'):
            out.write(content)

        elif format in ('PNG'):
            out.write(content)
    
if __name__ == '__main__':
    p = Provider(None)
            
    #This is done in an odd order where the Zoom is last
    p.renderTile(256, 256, '', Coordinate(3, 2, 3)).save('out.png')
########NEW FILE########
