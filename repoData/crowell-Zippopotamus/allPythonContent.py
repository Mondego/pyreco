__FILENAME__ = add
import sys
import os
import csv

from pymongo import Connection
from pymongo.database import Database

appendix_file = '../appendix/country.txt'
header_file = '../appendix/headers.txt'


def add(csv_file):
    
    # Generate N Records
    with open( csv_file , 'rb')  as f:
        reader = csv.reader( f , delimiter=',', quotechar='"') 
        headers = reader.next()
        for row in reader:
            record = dict()

            for ii in range(0, len(headers)):
                if 'ignore' not in headers[ii]:
                    record[ headers[ii] ] = unicode( row[ii], 'utf-8' )
            save(record)

    pass

def save( record ):
    db['global'].save(record)

if __name__ == "__main__" :
    
    if ( len(sys.argv) != 5 ):
        print "Usage: %s <username> <password> <url> <csv-files>" % sys.argv[0]

    username = sys.argv[1]
    password = sys.argv[2]
    url  =     sys.argv[3]
    file_list = sys.argv[4:]
    
    print username
    print password
    print len(file_list)

    if ( len(url) == 0 ):
        connection = Connection()              # Connect to localhost
    else:
        connection = Connection( url )         # Connect to remote db
        
    db = Database(connection,'zip')              # Get zip database
    db.authenticate(username,password)           # Authenticate
    

    for csv_file in file_list:  # Add all the files 
        add( csv_file )

    



########NEW FILE########
__FILENAME__ = remove
import sys
import os
import csv

from pymongo import Connection
from pymongo.database import Database

appendix_file = '../appendix/country.txt'
header_file = '../appendix/headers.txt'


def remove(csv_file):
    
    # Load Header File 
    with open(header_file, 'rb') as f:
        hfile = csv.reader( f, delimiter=',', quotechar='|')
        headers = hfile.next()
    
    
    # Load Country Appendix
    with  open(appendix_file, 'rb') as f:
        appendix = csv.reader( f,  delimiter=',', quotechar='|') 
        names = dict()
        for lines in appendix:
            if lines[0]!="":
                names[ lines[0] ] = lines[1]

    # Generate N Records
    with open( csv_file , 'rb')  as f:
        reader = csv.reader( f , delimiter=',', quotechar='|') 
        for row in reader:
            record = dict()
            record['country'] = unicode(names[row[0] ], 'utf-8')

            for ii in range(0, len(headers)):
                if 'ignore' not in headers[ii]:
                    record[ headers[ii] ] = unicode( row[ii], 'utf-8' )
            erase(record)

    pass

def erase( record ):
    db['global'].remove(record)

if __name__ == "__main__" :
    
    if ( len(sys.argv) != 4 ):
        print "Usage: %s <username> <password> <csv-files>" % sys.argv[0]

    username = sys.argv[1]
    password = sys.argv[2]
    csv_file = sys.argv[3]
    
    print username
    print password
    print csv_file

    connection = Connection()                   # Replace with mongo-url
    db = Database(connection,'zip')              # Get zip database
    db.authenticate(username,password)           # Authenticate
    
    remove( csv_file )

    



########NEW FILE########
__FILENAME__ = table
from pymongo import Connection
from pymongo.database import Database
import sys
import json
import sys
import os

 
'''
Generates Table and Information from MONGODB
'''
def build_table():
    
    
    # Keep track of country changes
    min_val = dict()
    names = dict()
    max_val = dict()
    total = dict()
    ccodes = set()
    
    print "Generating Files ... "

    for record in list(db['global'].find()) :
        
        # If not empty
        if record['country abbreviation'] != '':
            
            # Extract the country code
            cc = record['country abbreviation']
            
            # Print if we have moved onto a new country country
            if cc not in ccodes:
                print cc
                ccodes.add(cc)
                names[cc] = record['country']
                total[cc] = 1
                min_val[cc] = record['post code']
                max_val[cc] = record['post code']
            else:
                if max_val[cc] < record['post code']:
                    max_val[cc] = record['post code']
                if min_val[cc] > record['post code']:
                    min_val[cc] = record['post code']
                total[cc]+=1
    
    # Now I have min/max, ccodes, names and totals for all the countries
    
    html_string = ""
    sorted_codes = sorted( list(ccodes) )

    for cc in sorted_codes:
        
        # Make an information list and fill it
        info = list()
        
        # Country Name
        info.append( names[cc] )
        
        # Country code
        info.append( cc )

        # Min value       
        info.append( url_example( cc , min_val[cc] ) )
        
        # Min to Max range 
        info.append(  min_val[cc]+" : "+max_val[cc] )

        # totals
        info.append( total[cc] )

        html_string += html_row( info )+ "\n"

    print html_string

def url_example( cc, postcode ):
    span_end = "</span>"
    span_red = '<span style="color:darkred;">'
    span_blue = '<span style="color:darkblue;">'
    span_green = '<span style="color:darkgreen;">'

    # Generate Example with colors
    example = ""
    example += span_blue+"zippopotam.us"+span_end+"/"
    example += span_red+cc+span_end+"/"
    example += span_green+postcode+span_end
    
    return example

    
def html_row(info):
    
    end_row = "</tr>"
    start_row = "<tr>"
    
    row = ""
    row += start_row
    for ii in info:
        row +=  "<td>" + str(ii) +"</td>"

    row += end_row

    return row
    



if __name__ == "__main__":

    if ( len(sys.argv) != 2 ):
        print "Usage: %s <username> <password>" % sys.argv[0]

    username = sys.argv[1]
    password = sys.argv[2]
    
    print username
    print password

    connection = Connection()              # Specific url
    db = Database(connection,'zip')     # Get zip database
    db.authenticate(username,password)  # Authenticate
    
    build_table();



########NEW FILE########
