__FILENAME__ = geo_header_parser
#!/usr/bin/env python
"""
This script parses a Census geo header file and converts it to a csv. 
It's just a bare start. Hopefully it's the germ of something.
Eventually, it could be used to populate database tables instead.

Currently the sample AL files and the geo header are both from Census 2000:
http://www2.census.gov/census_2000/datasets/redistricting_file--pl_94-171/

The geo header fields for Census 2010 are slightly different, but the same approach will work for them if we update the data dictionary.

For the data dictionary, I created a pipe-delimited file from the text of the pdf documentation:
http://www.census.gov/prod/www/abs/pl94-171.pdf

The file layout is "description|fieldname|length|offset."
For example:
    File Identification|FILEID|6|1
    State/US-Abbreviation (USPS)|STUSAB|2|7
    Summary Level|SUMLEV|3|9

There are probably easier and more reusable ways of getting the fields for the data dictionary, such as parsing
the SAS script that comes with the files: 
http://www2.census.gov/census_2000/datasets/redistricting_file--pl_94-171/0File_Structure/SAS/pl_geohd.sas
or parsing the HTML File Structure README:
http://www2.census.gov/census_2000/datasets/redistricting_file--pl_94-171/0File_Structure/File_Structure_README.htm

I'm not sure, though, that these files will be available for 2010. (They're not included in the 2008 Redistricting Prototype files.)

The approach to parsing the fixed-width format here uses the "unpack" method from the struct module. This method accepts a format string, 
which describes the fixed-width format, and a string to unpack. It returns a tuple representing the parts of the unpacked string.

The format string is a series of single characters representing the data types of parts of the string we're unpacking.
The format character for string is 's'. It can be preceded by an integer representing the size of the string.

So, the pattern describing a five-character string would be '5s'. And if we wanted to match the words in the string "onetwothree" we could 
use '3s3s5s'. 
The result looks like this:

>>> from struct import *
>>> unpack('3s3s5s', 'onetwothree')
('one', 'two', 'three')

"""

from struct import *

# Set up empty arrays for the fieldnames and lengths of the fixed-width fields
fields = []
sizes = []

# Iterate through the data dictionary file, grabbing the fieldname and length of each field
for line in open('./config/geo_file_fields.csv'):
  values = line.split('|')   # Split the line on the pipe delimiter (returns a list or fields)
  fields.append(values[1])   # Grab the fieldname (second field in the row) and push it onto the fields list
  sizes.append(values[2])    # Grab the field size (third field in the row) and push it onto the sizes list

# Create a format string from the field lengths to be used in the unpack function from the struct module
field_pattern = "s".join(sizes) + "s"  # Join the list of field lengths with the format character 's' and add another 's' after the final length.

print ",".join(fields)  # Print out a comma-separated string of the fieldnames to create the header row of the csv

# Iterate through all the lines of a single geo header file (this one for Alabama)
# We could make this loop through all directories, generating output for each state.
for line in open('./data/al/algeo.upl'):
  bare_line = line.rstrip('\n')           # Take off the newline character at the end of the line
  row = unpack(field_pattern, bare_line)  # Use struct.unpack to break out the fields according to the field pattern created above
  print ",".join(row)                     # Print out a comma-separated string of the extracted values

########NEW FILE########
__FILENAME__ = LoadCensus2010RedistrictingData

'''
This script is used to import 2010 Census redisticting data
into a SQLite database.
Written using Python 2.7.

Prior to running this script, you should:
1 - Set the source directory (srcDir)
2 - Make sure your data files are in that directory.
3 - Set the names of your three SQLite tables (geotablename,
    data1tablename, data2tablename)

There are three types of files:
 * Geographic header files (*geo2010.pl)
 * Data files (first set) (*012010.pl)
 * Data files (second set) (*022010.pl)

The script will ignore any files that do not have a .pl extension.
Similarly, the program will stop if it finds a .pl file that does
not meet one of the above three criteria for valid files.

'''

# import modules
import os
import glob
import sqlite3
from struct import unpack

# Specify source directory
srcDir = 'C:\\Data\\Census\\'

# Specify path of SQLite database
dbpath = '\\\\asb-bus02\\userdata\\cschnaars\\SQLite\\CenRedistData2010.sqlite'

# Specify table names
geotablename = 'tblGeo'
data1tablename = 'tblData1'
data2tablename = 'tblData2'

# Create string to give field lengths
# for fixed-width geo header file
geofields = '6s2s3s2s3s2s7s1s1s2s3s2s2s5s2s2s5s2s2s6s1s4s2s5s2s2s4s5s2s1s3s5s2s6s1s5s2s5s2s5s3s5s2s5s3s1s1s5s2s1s1s2s3s3s6s1s3s5s5s2s5s5s5s14s14s90s1s1s9s9s11s12s2s1s6s5s8s8s8s8s8s8s8s8s8s2s2s2s3s3s3s3s3s3s2s2s2s1s1s5s18s'

# Connect to the sqlite database
db = sqlite3.connect(dbpath)

# Create a cursor
cursor = db.cursor()

# Run SQL scripts to create the data tables if they don't exist:
# --------------------------------------------------------------
# Geography Header table
SQL = 'CREATE TABLE IF NOT EXISTS "' + geotablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"SUMLEV" char(3) NOT NULL, "GEOCOMP" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL,
"REGION" char(1) NOT NULL, "DIVISION" char(1) NOT NULL,
"STATECODE" char(2) NOT NULL, "COUNTY" char(3), "COUNTYCC" char(2),
"COUNTYSC" char(2), "COUSUB" char(5), "COUSUBCC" char(2),
"COUSUBSC" char(2), "PLACE" char(5), "PLACECC" char(2),
"PLACESC" char(2), "TRACT" char(6), "BLKGRP" char(1), "BLOCK" char(4),
"IUC" char(2), "CONCIT" char(5), "CONCITCC" char(2), "CONCITSC" char(2),
"AIANHH" char(4), "AIANHHFP" char(5), "AIANHHCC" char(2),
"AIHHTLI" char(1), "AITSCE" char(3), "AITS" char(5), "AITSCC" char(2),
"TTRACT" char(6), "TBLKGRP" char(1), "ANRC" char(5), "ANRCCC" char(2),
"CBSA" char(5), "CBSASC" char(2), "METDIV" char(5), "CSA" char(3),
"NECTA" char(5), "NECTASC" char(2), "NECTADIV" char(5), "CNECTA" char(3),
"CBSAPCI" char(1), "NECTAPCI" char(1), "UA" char(5), "UASC" char(2),
"UATYPE" char(1), "UR" char(1), "CD" char(2), "SLDU" char(3),
"SLDL" char(3), "VTD" char(6), "VTDI" char(1), "RESERVE2" char(3),
"ZCTA5" char(5), "SUBMCD" char(5), "SUBMCDCC" char(2), "SDELM" char(5),
"SDSEC" char(5), "SDUNI" char(5), "AREALAND" char(14) NOT NULL,
"AREAWATR" char(14) NOT NULL, "AREANAME" varchar(90) NOT NULL,
"FUNCSTAT" char(1) NOT NULL, "GCUNI" char(1), "POP100" char(9) NOT NULL,
"HU100" char(9) NOT NULL, "INTPTLAT" char(11) NOT NULL,
"INTPTLON" char(12) NOT NULL, "LSADC" char(2) NOT NULL,
"PARTFLAG" char(1), "RESERVE3" char(6), "UGA" char(5),
"STATENS" char(8) NOT NULL, "COUNTYNS" char(8), "COUSUBNS" char(8),
"PLACENS" char(8), "CONCITNS" char(8), "AIANHHNS" char(8),
"AITSNS" char(8), "ANRCNS" char(8), "SUBMCDNS" char(8),
"CD113" char(2), "CD114" char(2), "CD115" char(2), "SLDU2" char(3),
"SLDU3" char(3), "SLDU4" char(3), "SLDL2" char(3), "SLDL3" char(3),
"SLDL4" char(3), "AIANHHSC" char(2), "CSASC" char(2), "CNECTASC" char(2),
"MEMI" char(1), "NMEMI" char(1), "PUMA" char(5), "RESERVED" char(18));'''

cursor.execute(SQL)

# Data Table 1
SQL = 'CREATE TABLE IF NOT EXISTS "' + data1tablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL, "P0010001" INTEGER, "P0010002" INTEGER,
"P0010003" INTEGER, "P0010004" INTEGER, "P0010005" INTEGER,
"P0010006" INTEGER, "P0010007" INTEGER, "P0010008" INTEGER,
"P0010009" INTEGER, "P0010010" INTEGER, "P0010011" INTEGER,
"P0010012" INTEGER, "P0010013" INTEGER, "P0010014" INTEGER,
"P0010015" INTEGER, "P0010016" INTEGER, "P0010017" INTEGER,
"P0010018" INTEGER, "P0010019" INTEGER, "P0010020" INTEGER,
"P0010021" INTEGER, "P0010022" INTEGER, "P0010023" INTEGER,
"P0010024" INTEGER, "P0010025" INTEGER, "P0010026" INTEGER,
"P0010027" INTEGER, "P0010028" INTEGER, "P0010029" INTEGER,
"P0010030" INTEGER, "P0010031" INTEGER, "P0010032" INTEGER,
"P0010033" INTEGER, "P0010034" INTEGER, "P0010035" INTEGER,
"P0010036" INTEGER, "P0010037" INTEGER, "P0010038" INTEGER,
"P0010039" INTEGER, "P0010040" INTEGER, "P0010041" INTEGER,
"P0010042" INTEGER, "P0010043" INTEGER, "P0010044" INTEGER,
"P0010045" INTEGER, "P0010046" INTEGER, "P0010047" INTEGER,
"P0010048" INTEGER, "P0010049" INTEGER, "P0010050" INTEGER,
"P0010051" INTEGER, "P0010052" INTEGER, "P0010053" INTEGER,
"P0010054" INTEGER, "P0010055" INTEGER, "P0010056" INTEGER,
"P0010057" INTEGER, "P0010058" INTEGER, "P0010059" INTEGER,
"P0010060" INTEGER, "P0010061" INTEGER, "P0010062" INTEGER,
"P0010063" INTEGER, "P0010064" INTEGER, "P0010065" INTEGER,
"P0010066" INTEGER, "P0010067" INTEGER, "P0010068" INTEGER,
"P0010069" INTEGER, "P0010070" INTEGER, "P0010071" INTEGER,
"P0020001" INTEGER, "P0020002" INTEGER, "P0020003" INTEGER,
"P0020004" INTEGER, "P0020005" INTEGER, "P0020006" INTEGER,
"P0020007" INTEGER, "P0020008" INTEGER, "P0020009" INTEGER,
"P0020010" INTEGER, "P0020011" INTEGER, "P0020012" INTEGER,
"P0020013" INTEGER, "P0020014" INTEGER, "P0020015" INTEGER,
"P0020016" INTEGER, "P0020017" INTEGER, "P0020018" INTEGER,
"P0020019" INTEGER, "P0020020" INTEGER, "P0020021" INTEGER,
"P0020022" INTEGER, "P0020023" INTEGER, "P0020024" INTEGER,
"P0020025" INTEGER, "P0020026" INTEGER, "P0020027" INTEGER,
"P0020028" INTEGER, "P0020029" INTEGER, "P0020030" INTEGER,
"P0020031" INTEGER, "P0020032" INTEGER, "P0020033" INTEGER,
"P0020034" INTEGER, "P0020035" INTEGER, "P0020036" INTEGER,
"P0020037" INTEGER, "P0020038" INTEGER, "P0020039" INTEGER,
"P0020040" INTEGER, "P0020041" INTEGER, "P0020042" INTEGER,
"P0020043" INTEGER, "P0020044" INTEGER, "P0020045" INTEGER,
"P0020046" INTEGER, "P0020047" INTEGER, "P0020048" INTEGER,
"P0020049" INTEGER, "P0020050" INTEGER, "P0020051" INTEGER,
"P0020052" INTEGER, "P0020053" INTEGER, "P0020054" INTEGER,
"P0020055" INTEGER, "P0020056" INTEGER, "P0020057" INTEGER,
"P0020058" INTEGER, "P0020059" INTEGER, "P0020060" INTEGER,
"P0020061" INTEGER, "P0020062" INTEGER, "P0020063" INTEGER,
"P0020064" INTEGER, "P0020065" INTEGER, "P0020066" INTEGER,
"P0020067" INTEGER, "P0020068" INTEGER, "P0020069" INTEGER,
"P0020070" INTEGER, "P0020071" INTEGER, "P0020072" INTEGER,
"P0020073" INTEGER);'''

cursor.execute(SQL)

# Data Table 2
SQL = 'CREATE TABLE IF NOT EXISTS "' + data2tablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL, "P0030001" INTEGER , "P0030002" INTEGER ,
"P0030003" INTEGER , "P0030004" INTEGER , "P0030005" INTEGER ,
"P0030006" INTEGER , "P0030007" INTEGER , "P0030008" INTEGER ,
"P0030009" INTEGER , "P0030010" INTEGER , "P0030011" INTEGER ,
"P0030012" INTEGER , "P0030013" INTEGER , "P0030014" INTEGER ,
"P0030015" INTEGER , "P0030016" INTEGER , "P0030017" INTEGER ,
"P0030018" INTEGER , "P0030019" INTEGER , "P0030020" INTEGER ,
"P0030021" INTEGER , "P0030022" INTEGER , "P0030023" INTEGER ,
"P0030024" INTEGER , "P0030025" INTEGER , "P0030026" INTEGER ,
"P0030027" INTEGER , "P0030028" INTEGER , "P0030029" INTEGER ,
"P0030030" INTEGER , "P0030031" INTEGER , "P0030032" INTEGER ,
"P0030033" INTEGER , "P0030034" INTEGER , "P0030035" INTEGER ,
"P0030036" INTEGER , "P0030037" INTEGER , "P0030038" INTEGER ,
"P0030039" INTEGER , "P0030040" INTEGER , "P0030041" INTEGER ,
"P0030042" INTEGER , "P0030043" INTEGER , "P0030044" INTEGER ,
"P0030045" INTEGER , "P0030046" INTEGER , "P0030047" INTEGER ,
"P0030048" INTEGER , "P0030049" INTEGER , "P0030050" INTEGER ,
"P0030051" INTEGER , "P0030052" INTEGER , "P0030053" INTEGER ,
"P0030054" INTEGER , "P0030055" INTEGER , "P0030056" INTEGER ,
"P0030057" INTEGER , "P0030058" INTEGER , "P0030059" INTEGER ,
"P0030060" INTEGER , "P0030061" INTEGER , "P0030062" INTEGER ,
"P0030063" INTEGER , "P0030064" INTEGER , "P0030065" INTEGER ,
"P0030066" INTEGER , "P0030067" INTEGER , "P0030068" INTEGER ,
"P0030069" INTEGER , "P0030070" INTEGER , "P0030071" INTEGER ,
"P0040001" INTEGER , "P0040002" INTEGER , "P0040003" INTEGER ,
"P0040004" INTEGER , "P0040005" INTEGER , "P0040006" INTEGER ,
"P0040007" INTEGER , "P0040008" INTEGER , "P0040009" INTEGER ,
"P0040010" INTEGER , "P0040011" INTEGER , "P0040012" INTEGER ,
"P0040013" INTEGER , "P0040014" INTEGER , "P0040015" INTEGER ,
"P0040016" INTEGER , "P0040017" INTEGER , "P0040018" INTEGER ,
"P0040019" INTEGER , "P0040020" INTEGER , "P0040021" INTEGER ,
"P0040022" INTEGER , "P0040023" INTEGER , "P0040024" INTEGER ,
"P0040025" INTEGER , "P0040026" INTEGER , "P0040027" INTEGER ,
"P0040028" INTEGER , "P0040029" INTEGER , "P0040030" INTEGER ,
"P0040031" INTEGER , "P0040032" INTEGER , "P0040033" INTEGER ,
"P0040034" INTEGER , "P0040035" INTEGER , "P0040036" INTEGER ,
"P0040037" INTEGER , "P0040038" INTEGER , "P0040039" INTEGER ,
"P0040040" INTEGER , "P0040041" INTEGER , "P0040042" INTEGER ,
"P0040043" INTEGER , "P0040044" INTEGER , "P0040045" INTEGER ,
"P0040046" INTEGER , "P0040047" INTEGER , "P0040048" INTEGER ,
"P0040049" INTEGER , "P0040050" INTEGER , "P0040051" INTEGER ,
"P0040052" INTEGER , "P0040053" INTEGER , "P0040054" INTEGER ,
"P0040055" INTEGER , "P0040056" INTEGER , "P0040057" INTEGER ,
"P0040058" INTEGER , "P0040059" INTEGER , "P0040060" INTEGER ,
"P0040061" INTEGER , "P0040062" INTEGER , "P0040063" INTEGER ,
"P0040064" INTEGER , "P0040065" INTEGER , "P0040066" INTEGER ,
"P0040067" INTEGER , "P0040068" INTEGER , "P0040069" INTEGER ,
"P0040070" INTEGER , "P0040071" INTEGER , "P0040072" INTEGER ,
"P0040073" INTEGER , "H0010001" INTEGER , "H0010002" INTEGER ,
"H0010003" INTEGER);'''

cursor.execute(SQL)

# Iterate through each file in the directory
for datafile in glob.glob(os.path.join(srcDir, '*.pl')):

    # Determine file type
    if datafile.endswith('geo2010.pl'):
        datatable = 'geo'
        datacount = 100     # 101 fields
    elif datafile.endswith('012010.pl'):
        datatable = data1tablename
        datacount = 148     # 149 fields
    elif datafile.endswith('022010.pl'):
        datatable = data2tablename
        datacount = 151     # 152 fields
    else:
        print 'File not recognized: ' + datafile
        break

    # Iterate through each line in the file
    if datatable == 'geo':
        # It's a geography header file
        for line in open(datafile, 'rb'):
            parseddata = unpack(geofields, line.rstrip('\n')) # Unpack the fields and copy to a list
            SQL = 'INSERT INTO "' + geotablename + '" VALUES(' + '?, ' * datacount + '?)'
            cursor.execute(SQL, parseddata)
    else:
        # It's a data file
        for line in open(datafile, 'rb'):
            parseddata = line.rstrip('\n').split(',')    # Copy the line to a list
            SQL = 'INSERT INTO "' + datatable + '" VALUES(' + '?, ' * datacount + '?)'
            cursor.execute(SQL, parseddata)

db.commit()

########NEW FILE########
__FILENAME__ = LoadCensus2010RedistrictingData_Mac

'''
This script is used to import 2010 Census redisticting data
into a SQLite database.
Written using Python 2.7.

Prior to running this script, you should:
1 - Set the source directory (srcDir)
2 - Make sure your data files are in that directory.
3 - Set the names of your three SQLite tables (geotablename,
    data1tablename, data2tablename)

There are three types of files:
 * Geographic header files (*geo2010.pl)
 * Data files (first set) (*012010.pl)
 * Data files (second set) (*022010.pl)

The script will ignore any files that do not have a .pl extension.
Similarly, the program will stop if it finds a .pl file that does
not meet one of the above three criteria for valid files.

'''

# import modules
import os
import glob
import sqlite3
from struct import unpack

# Specify source directory (defaults to home dir)
srcDir = '~/Census2010Data/'

# Specify path of SQLite database
dbpath = '~/Census2010Data/CenRedistData2010.sqlite'

# Specify table names
geotablename = 'tblGeo'
data1tablename = 'tblData1'
data2tablename = 'tblData2'

# Create string to give field lengths
# for fixed-width geo header file
geofields = '6s2s3s2s3s2s7s1s1s2s3s2s2s5s2s2s5s2s2s6s1s4s2s5s2s2s4s5s2s1s3s5s2s6s1s5s2s5s2s5s3s5s2s5s3s1s1s5s2s1s1s2s3s3s6s1s3s5s5s2s5s5s5s14s14s90s1s1s9s9s11s12s2s1s6s5s8s8s8s8s8s8s8s8s8s2s2s2s3s3s3s3s3s3s2s2s2s1s1s5s18s'

# Connect to the sqlite database
db = sqlite3.connect(dbpath)

# Create a cursor
cursor = db.cursor()

# Run SQL scripts to create the data tables if they don't exist:
# --------------------------------------------------------------
# Geography Header table
SQL = 'CREATE TABLE IF NOT EXISTS "' + geotablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"SUMLEV" char(3) NOT NULL, "GEOCOMP" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL,
"REGION" char(1) NOT NULL, "DIVISION" char(1) NOT NULL,
"STATECODE" char(2) NOT NULL, "COUNTY" char(3), "COUNTYCC" char(2),
"COUNTYSC" char(2), "COUSUB" char(5), "COUSUBCC" char(2),
"COUSUBSC" char(2), "PLACE" char(5), "PLACECC" char(2),
"PLACESC" char(2), "TRACT" char(6), "BLKGRP" char(1), "BLOCK" char(4),
"IUC" char(2), "CONCIT" char(5), "CONCITCC" char(2), "CONCITSC" char(2),
"AIANHH" char(4), "AIANHHFP" char(5), "AIANHHCC" char(2),
"AIHHTLI" char(1), "AITSCE" char(3), "AITS" char(5), "AITSCC" char(2),
"TTRACT" char(6), "TBLKGRP" char(1), "ANRC" char(5), "ANRCCC" char(2),
"CBSA" char(5), "CBSASC" char(2), "METDIV" char(5), "CSA" char(3),
"NECTA" char(5), "NECTASC" char(2), "NECTADIV" char(5), "CNECTA" char(3),
"CBSAPCI" char(1), "NECTAPCI" char(1), "UA" char(5), "UASC" char(2),
"UATYPE" char(1), "UR" char(1), "CD" char(2), "SLDU" char(3),
"SLDL" char(3), "VTD" char(6), "VTDI" char(1), "RESERVE2" char(3),
"ZCTA5" char(5), "SUBMCD" char(5), "SUBMCDCC" char(2), "SDELM" char(5),
"SDSEC" char(5), "SDUNI" char(5), "AREALAND" char(14) NOT NULL,
"AREAWATR" char(14) NOT NULL, "AREANAME" varchar(90) NOT NULL,
"FUNCSTAT" char(1) NOT NULL, "GCUNI" char(1), "POP100" char(9) NOT NULL,
"HU100" char(9) NOT NULL, "INTPTLAT" char(11) NOT NULL,
"INTPTLON" char(12) NOT NULL, "LSADC" char(2) NOT NULL,
"PARTFLAG" char(1), "RESERVE3" char(6), "UGA" char(5),
"STATENS" char(8) NOT NULL, "COUNTYNS" char(8), "COUSUBNS" char(8),
"PLACENS" char(8), "CONCITNS" char(8), "AIANHHNS" char(8),
"AITSNS" char(8), "ANRCNS" char(8), "SUBMCDNS" char(8),
"CD113" char(2), "CD114" char(2), "CD115" char(2), "SLDU2" char(3),
"SLDU3" char(3), "SLDU4" char(3), "SLDL2" char(3), "SLDL3" char(3),
"SLDL4" char(3), "AIANHHSC" char(2), "CSASC" char(2), "CNECTASC" char(2),
"MEMI" char(1), "NMEMI" char(1), "PUMA" char(5), "RESERVED" char(18));'''

cursor.execute(SQL)

# Data Table 1
SQL = 'CREATE TABLE IF NOT EXISTS "' + data1tablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL, "P0010001" INTEGER, "P0010002" INTEGER,
"P0010003" INTEGER, "P0010004" INTEGER, "P0010005" INTEGER,
"P0010006" INTEGER, "P0010007" INTEGER, "P0010008" INTEGER,
"P0010009" INTEGER, "P0010010" INTEGER, "P0010011" INTEGER,
"P0010012" INTEGER, "P0010013" INTEGER, "P0010014" INTEGER,
"P0010015" INTEGER, "P0010016" INTEGER, "P0010017" INTEGER,
"P0010018" INTEGER, "P0010019" INTEGER, "P0010020" INTEGER,
"P0010021" INTEGER, "P0010022" INTEGER, "P0010023" INTEGER,
"P0010024" INTEGER, "P0010025" INTEGER, "P0010026" INTEGER,
"P0010027" INTEGER, "P0010028" INTEGER, "P0010029" INTEGER,
"P0010030" INTEGER, "P0010031" INTEGER, "P0010032" INTEGER,
"P0010033" INTEGER, "P0010034" INTEGER, "P0010035" INTEGER,
"P0010036" INTEGER, "P0010037" INTEGER, "P0010038" INTEGER,
"P0010039" INTEGER, "P0010040" INTEGER, "P0010041" INTEGER,
"P0010042" INTEGER, "P0010043" INTEGER, "P0010044" INTEGER,
"P0010045" INTEGER, "P0010046" INTEGER, "P0010047" INTEGER,
"P0010048" INTEGER, "P0010049" INTEGER, "P0010050" INTEGER,
"P0010051" INTEGER, "P0010052" INTEGER, "P0010053" INTEGER,
"P0010054" INTEGER, "P0010055" INTEGER, "P0010056" INTEGER,
"P0010057" INTEGER, "P0010058" INTEGER, "P0010059" INTEGER,
"P0010060" INTEGER, "P0010061" INTEGER, "P0010062" INTEGER,
"P0010063" INTEGER, "P0010064" INTEGER, "P0010065" INTEGER,
"P0010066" INTEGER, "P0010067" INTEGER, "P0010068" INTEGER,
"P0010069" INTEGER, "P0010070" INTEGER, "P0010071" INTEGER,
"P0020001" INTEGER, "P0020002" INTEGER, "P0020003" INTEGER,
"P0020004" INTEGER, "P0020005" INTEGER, "P0020006" INTEGER,
"P0020007" INTEGER, "P0020008" INTEGER, "P0020009" INTEGER,
"P0020010" INTEGER, "P0020011" INTEGER, "P0020012" INTEGER,
"P0020013" INTEGER, "P0020014" INTEGER, "P0020015" INTEGER,
"P0020016" INTEGER, "P0020017" INTEGER, "P0020018" INTEGER,
"P0020019" INTEGER, "P0020020" INTEGER, "P0020021" INTEGER,
"P0020022" INTEGER, "P0020023" INTEGER, "P0020024" INTEGER,
"P0020025" INTEGER, "P0020026" INTEGER, "P0020027" INTEGER,
"P0020028" INTEGER, "P0020029" INTEGER, "P0020030" INTEGER,
"P0020031" INTEGER, "P0020032" INTEGER, "P0020033" INTEGER,
"P0020034" INTEGER, "P0020035" INTEGER, "P0020036" INTEGER,
"P0020037" INTEGER, "P0020038" INTEGER, "P0020039" INTEGER,
"P0020040" INTEGER, "P0020041" INTEGER, "P0020042" INTEGER,
"P0020043" INTEGER, "P0020044" INTEGER, "P0020045" INTEGER,
"P0020046" INTEGER, "P0020047" INTEGER, "P0020048" INTEGER,
"P0020049" INTEGER, "P0020050" INTEGER, "P0020051" INTEGER,
"P0020052" INTEGER, "P0020053" INTEGER, "P0020054" INTEGER,
"P0020055" INTEGER, "P0020056" INTEGER, "P0020057" INTEGER,
"P0020058" INTEGER, "P0020059" INTEGER, "P0020060" INTEGER,
"P0020061" INTEGER, "P0020062" INTEGER, "P0020063" INTEGER,
"P0020064" INTEGER, "P0020065" INTEGER, "P0020066" INTEGER,
"P0020067" INTEGER, "P0020068" INTEGER, "P0020069" INTEGER,
"P0020070" INTEGER, "P0020071" INTEGER, "P0020072" INTEGER,
"P0020073" INTEGER);'''

cursor.execute(SQL)

# Data Table 2
SQL = 'CREATE TABLE IF NOT EXISTS "' + data2tablename + '''" (
"FILEID" char(6) NOT NULL, "STUSAB" char(2) NOT NULL,
"CHARITER" char(3) NOT NULL, "CIFSN" char(2) NOT NULL,
"LOGRECNO" char(7) NOT NULL, "P0030001" INTEGER , "P0030002" INTEGER ,
"P0030003" INTEGER , "P0030004" INTEGER , "P0030005" INTEGER ,
"P0030006" INTEGER , "P0030007" INTEGER , "P0030008" INTEGER ,
"P0030009" INTEGER , "P0030010" INTEGER , "P0030011" INTEGER ,
"P0030012" INTEGER , "P0030013" INTEGER , "P0030014" INTEGER ,
"P0030015" INTEGER , "P0030016" INTEGER , "P0030017" INTEGER ,
"P0030018" INTEGER , "P0030019" INTEGER , "P0030020" INTEGER ,
"P0030021" INTEGER , "P0030022" INTEGER , "P0030023" INTEGER ,
"P0030024" INTEGER , "P0030025" INTEGER , "P0030026" INTEGER ,
"P0030027" INTEGER , "P0030028" INTEGER , "P0030029" INTEGER ,
"P0030030" INTEGER , "P0030031" INTEGER , "P0030032" INTEGER ,
"P0030033" INTEGER , "P0030034" INTEGER , "P0030035" INTEGER ,
"P0030036" INTEGER , "P0030037" INTEGER , "P0030038" INTEGER ,
"P0030039" INTEGER , "P0030040" INTEGER , "P0030041" INTEGER ,
"P0030042" INTEGER , "P0030043" INTEGER , "P0030044" INTEGER ,
"P0030045" INTEGER , "P0030046" INTEGER , "P0030047" INTEGER ,
"P0030048" INTEGER , "P0030049" INTEGER , "P0030050" INTEGER ,
"P0030051" INTEGER , "P0030052" INTEGER , "P0030053" INTEGER ,
"P0030054" INTEGER , "P0030055" INTEGER , "P0030056" INTEGER ,
"P0030057" INTEGER , "P0030058" INTEGER , "P0030059" INTEGER ,
"P0030060" INTEGER , "P0030061" INTEGER , "P0030062" INTEGER ,
"P0030063" INTEGER , "P0030064" INTEGER , "P0030065" INTEGER ,
"P0030066" INTEGER , "P0030067" INTEGER , "P0030068" INTEGER ,
"P0030069" INTEGER , "P0030070" INTEGER , "P0030071" INTEGER ,
"P0040001" INTEGER , "P0040002" INTEGER , "P0040003" INTEGER ,
"P0040004" INTEGER , "P0040005" INTEGER , "P0040006" INTEGER ,
"P0040007" INTEGER , "P0040008" INTEGER , "P0040009" INTEGER ,
"P0040010" INTEGER , "P0040011" INTEGER , "P0040012" INTEGER ,
"P0040013" INTEGER , "P0040014" INTEGER , "P0040015" INTEGER ,
"P0040016" INTEGER , "P0040017" INTEGER , "P0040018" INTEGER ,
"P0040019" INTEGER , "P0040020" INTEGER , "P0040021" INTEGER ,
"P0040022" INTEGER , "P0040023" INTEGER , "P0040024" INTEGER ,
"P0040025" INTEGER , "P0040026" INTEGER , "P0040027" INTEGER ,
"P0040028" INTEGER , "P0040029" INTEGER , "P0040030" INTEGER ,
"P0040031" INTEGER , "P0040032" INTEGER , "P0040033" INTEGER ,
"P0040034" INTEGER , "P0040035" INTEGER , "P0040036" INTEGER ,
"P0040037" INTEGER , "P0040038" INTEGER , "P0040039" INTEGER ,
"P0040040" INTEGER , "P0040041" INTEGER , "P0040042" INTEGER ,
"P0040043" INTEGER , "P0040044" INTEGER , "P0040045" INTEGER ,
"P0040046" INTEGER , "P0040047" INTEGER , "P0040048" INTEGER ,
"P0040049" INTEGER , "P0040050" INTEGER , "P0040051" INTEGER ,
"P0040052" INTEGER , "P0040053" INTEGER , "P0040054" INTEGER ,
"P0040055" INTEGER , "P0040056" INTEGER , "P0040057" INTEGER ,
"P0040058" INTEGER , "P0040059" INTEGER , "P0040060" INTEGER ,
"P0040061" INTEGER , "P0040062" INTEGER , "P0040063" INTEGER ,
"P0040064" INTEGER , "P0040065" INTEGER , "P0040066" INTEGER ,
"P0040067" INTEGER , "P0040068" INTEGER , "P0040069" INTEGER ,
"P0040070" INTEGER , "P0040071" INTEGER , "P0040072" INTEGER ,
"P0040073" INTEGER , "H0010001" INTEGER , "H0010002" INTEGER ,
"H0010003" INTEGER);'''

cursor.execute(SQL)

# Iterate through each file in the directory
for datafile in glob.glob(os.path.join(srcDir, '*.pl')):

    # Determine file type
    if datafile.endswith('geo2010.pl'):
        datatable = 'geo'
        datacount = 100     # 101 fields
    elif datafile.endswith('012010.pl'):
        datatable = data1tablename
        datacount = 148     # 149 fields
    elif datafile.endswith('022010.pl'):
        datatable = data2tablename
        datacount = 151     # 152 fields
    else:
        print 'File not recognized: ' + datafile
        break

    # Iterate through each line in the file
    if datatable == 'geo':
        # It's a geography header file
        for line in open(datafile, 'rb'):
            parseddata = unpack(geofields, line.rstrip('\n')) # Unpack the fields and copy to a list
            SQL = 'INSERT INTO "' + geotablename + '" VALUES(' + '?, ' * datacount + '?)'
            cursor.execute(SQL, parseddata)
    else:
        # It's a data file
        for line in open(datafile, 'rb'):
            parseddata = line.rstrip('\n').split(',')    # Copy the line to a list
            SQL = 'INSERT INTO "' + datatable + '" VALUES(' + '?, ' * datacount + '?)'
            cursor.execute(SQL, parseddata)

db.commit()

########NEW FILE########
__FILENAME__ = app
# Flask is what makes everything work. Import it.
from flask import Flask, render_template

# Import our bank model.
from models import Bank

# Flask needs to run! This gives it legs.
app = Flask(__name__)


# Routes!
@app.route('/', methods=['GET'])
def failed_banks_list():
    """
    This route is for a list of ALL banks.
    """

    # The context for this pages is just "banks", a list of all banks.
    context = {
        'banks': Bank.select()
    }

    # Render the template to list.html and with the context from above.
    return render_template('list.html', **context)


@app.route('/bank/<cert_num>/', methods=['GET'])
def failed_bank_detail(cert_num):
    """
    This route is for a single bank.
    We're going to do TWO things.
    a.) We're going to get the one bank.
    b.) We're going to get all banks EXCEPT this bank in the same state.
    """
    # a.) Get this bank.
    this_bank = Bank.select()\
        .where(Bank.cert_num == int(cert_num)).get()

    # b.) Get the other banks in this state.
    same_state_banks = Bank.select()\
        .where(Bank.state == this_bank.state)\
        .where(Bank.cert_num != int(cert_num))

    # Set up the context; include both this bank and other banks from this state.
    context = {
        'bank': this_bank,
        'same_state_banks': same_state_banks
    }

    # Render the template to detail.html and with that context.
    return render_template('detail.html', **context)

# Last bit! Just need to get flask to run when we run it.
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

########NEW FILE########
__FILENAME__ = models
# Import our library.
from peewee import *

# Connect to the DB.
db = SqliteDatabase('fdic.sqlite')


# Set up a bank.
class Bank(Model):
    """
    This defines a bank and all of the fields a bank has.
    """
    bank = CharField()
    city = CharField()
    state = CharField()
    cert_num = PrimaryKeyField()
    acq_inst = CharField()
    closed = DateField()
    updated = DateField()

    # What is this thing?
    class Meta:
        """
        It's a class INSIDE a class.
        Don't let that bother you.
        We need to attach this model to a database.
        Also, we need to point to Schnaars's table.
        """
        database = db
        db_table = 'failed_banks'

########NEW FILE########
__FILENAME__ = save_to_csv
"""
Save results of FDIC Scrape to a CSV file.

This module shows how to use the built-in csv module to 
easily write out data to a file.
"""
import csv
import os
from datetime import datetime

# Import our scraper function to get the data
from scraper import scrape_data

# Import our dynamically calculated project directory
# It's a bit of magic that makes this code work on Macs, Windows, and Linux :)
from settings import PROJECT_DIR

# Function to change date strings to YYYY-MM-DD format
def convertdatestring(datestring):
    try:
        dt = datetime.strptime(datestring, '%B %d, %Y')
        ret_date = dt.strftime('%Y-%m-%d')
    except ValueError:
        print("Can't convert %s to date. Setting to NULL." % datestring)
    return ret_date

# Results is a list that includes our column headers and a list of data
results = scrape_data()
headers = results[0]
data = results[1]

"""
The results are list of data rows that look like below:

data = [
    [
        'First Alliance',
        'Manchester',
        'NH',
        '34264',
        'Southern New Hampshire Bank & Trust',
        'February 15, 2013',
        'February 20, 2013',
        'http://www.fdic.gov/bank/individual/failed/firstalliance.html'
    ],
]
"""

# Let's mess up one row to demo try/except:
# data[0][5] = 'Jnauary 15, 2013'

# Iterate through each row of our data and verify data types valid
for row in data:
    # First, we'll convert cert_num to an integer
    try:
        row[3] = int(row[3])
    except ValueError:
        print("%s is not a valid integer. Setting to zero." % row[3])
        row[3] = 0

    # Now we'll look at the two date fields. This is a little more
    # complicated, so we'll create a function that we can use for
    # both fields. We need to convert them to YYYY-MM-DD format.
    try:
        row[5] = convertdatestring(row[5])
    except:
        row[5] = ''
    
    try:
        row[6] = convertdatestring(row[6])
    except:
        row[6] = ''


# Below are a few Python idioms you'll see often. 
# You're opening a file so that you can read data from it.
# Then, you use the csv module to help write data to the file.
#   http://docs.python.org/2/library/functions.html#open
#   http://docs.python.org/2/library/csv.html

filename = os.path.join(PROJECT_DIR, 'fdic.txt')
with open(filename, 'wb') as outputfile:
    wtr = csv.writer(outputfile, delimiter='|')

    # Add headers tooutput
    wtr.writerow(headers)
    
    # Write the data
    wtr.writerows(data)

########NEW FILE########
__FILENAME__ = save_to_db
"""
Load fdic data into sqlite
"""
import os
import sqlite3

from settings import PROJECT_DIR

from scraper import scrape_data

# Construct the file path to our (soon-to-be-created) SQLite database
db_file = os.path.join(PROJECT_DIR, 'fdic.sqlite')

# Now we're ready to create our database and open a connection to it
#   http://docs.python.org/2/library/sqlite3.html
conn = sqlite3.connect(db_file)

# Once we're connected, we need a database "cursor" so
# we can send SQL statements to the db
cur = conn.cursor()

# Here's the SQL to create our database table 
TBL_CREATE_STMT = """
    CREATE TABLE IF NOT EXISTS failed_banks (
        bank varchar (54) NOT NULL,
        city varchar (17) NOT NULL, 
        state varchar (4) NOT NULL,
        cert_num INTEGER NOT NULL, 
        acq_inst VARCHAR (65) NOT NULL,
        closed DATE NOT NULL, 
        updated DATE NOT NULL,
        url VARCHAR (100) NOT NULL
    )
"""

# Execute the create table sql
cur.execute(TBL_CREATE_STMT)
# Commit our change
conn.commit()

# Get results data (recall that it's a list of two elements [headers, data])
results = scrape_data()
data = results[1]

cur.executemany('INSERT INTO failed_banks (bank, city, state, cert_num, acq_inst, ' \
                'closed, updated, url) VALUES (?, ?, ?, ?, ?, ?, ?, ?);', data)
# Commit our inserts
conn.commit()
# Close db connection
conn.close()

########NEW FILE########
__FILENAME__ = scraper
#!/usr/bin/env python
"""
This scrape demonstrates some Python basics using the FDIC's Failed Banks List.
It contains a function that downloads a single web page, uses a 3rd-party library
to extract data from the HTML, and packages up the data into a reusable
list of data "row".

NOTE:

The original FDIC data is located at the below URL:

    http://www.fdic.gov/bank/individual/failed/banklist.html

In order to be considerate to the FDIC's servers, we're scraping 
a copy of the page stored on Amazon S3.
"""
# Import a built-in library for working with data on the Web
#   http://docs.python.org/library/urllib.html
import urllib

# Import a 3rd-party library to help extract data from raw HTML
#   http://www.crummy.com/software/BeautifulSoup/documentation.html  
from bs4 import BeautifulSoup

# Below is a re-usable data scraper function that can be imported and used by other code.
#   http://docs.python.org/2/tutorial/controlflow.html#defining-functions
def scrape_data():
    # URL of the page we're going to scrape (below is the real URL, but
    # we'll hit a dummy version to be kind to the FDIC)
    #URL = 'http://www.fdic.gov/bank/individual/failed/banklist.html'
    URL = 'https://s3.amazonaws.com/python-journos/FDIC_Failed_Bank_List.html'

    # Open a network connection using the "urlopen" method. 
    # This returns a network "object" 
    #   http://docs.python.org/library/urllib.html#high-level-interface
    web_cnx = urllib.urlopen(URL)

    # Use the network object to download, or "read", the page's HTML
    html = web_cnx.read() 

    # Parse the HTML into a form that's easy to use
    soup = BeautifulSoup(html)

    # Use BeautifulSoup's API to extract your data
    # 1) Fetch the table by ID
    table  = soup.find(id='table') 

    # 2) Grab the table's rows
    rows = table.findAll('tr')

    # Create a list to store our results
    results = []

    # 3) Process the data, skipping the initial header row
    for tr in rows[1:]:

        # Extract data points from the table row
        data = tr.findAll('td')

        # Pluck out the text of each field, and perform a bit of clean-up
        row = [
            data[0].text,
            data[1].text,
            data[2].text,
            data[3].text,
            data[4].text,
            data[5].text.strip(),
            data[6].text.strip(),
            'http://www.fdic.gov/bank/individual/failed/' + data[0].a['href'],
        ]
        # Add the list of data to our results list (we'll end up with a list of lists)
        results.append(row)

    # Let's package up the results with the field names
    headers = [
        'bank_name',
        'city',
        'state',
        'cert_num',
        'acq_inst',
        'closed',
        'updated',
        'url'
    ]
    return [headers, results]

if __name__ == '__main__':
    results = scrape_data()
    for row in results[1]:
        print row

########NEW FILE########
__FILENAME__ = settings
"""
This module contains code useful for general project-wide housekeeping.
"""
from os.path import abspath, dirname

# Use some Python magic to dynamically determine the project directory.
# __file__ is a special Python attribute that references the current 
# file. So in this case, we get the full path to "constants.py" (minus the actual file name)
# We'll use this later to build the path to our output csv.
PROJECT_DIR = abspath(dirname( __file__))

# Alternatively, you could hard-code the path:
# WINDOWS_PROJECT_DIR = 'C:\\Documents and Settings\janedoe\fdic'
# MAC_PROJECT_DIR = '/Users/janedoe/fdic'
# LINUX_PROJECT_DIR = '/home/janedoe/fdic'

########NEW FILE########
__FILENAME__ = address_parser
#!/usr/bin/env python
"""
Below are two techniques showing how to reformat an address.

The functions below check an address to see if it has a direction
at the end of the address; if so, they reformat the address so the
direction appears before the street name. 

The first function uses indexing and slice notation
to pull apart the address. The second function uses a 
regular expression to parse the address.


USAGE:

>>> parse_address("123 Main St N")
'123 N Main St'

>>> parse_address_with_regex("123 Main St N")   
'123 N Main St'

"""
import re


            #### Index/Slice Technique ####

def parse_address(address):
    """
    This function, courtesy of Brian Bowling, uses slice notation to parse and reformat an address.

    More info on slice notation is here:
       http://docs.python.org/tutorial/introduction.html#strings
    """
    # find the first and last spaces in the string
    last_space = len(address) - 1
    first_space = 0

    while address[last_space] != " ":
        last_space -= 1

    while address[first_space] != " ":
        first_space += 1
    
    # test to see if the characters following the last space are a direction
    if address[last_space + 1:] in ("N", "S", "E", "W", "NE", "NW", "SE", "SW"):
    # make the transformation
        new_address = address[:first_space] + address[last_space:] + address[first_space:last_space]
    else:
        new_address = address

    return new_address



            #### Regular Expression Technique ####

# Create a regular expression pattern, which we'll use to match address strings
address_pattern = re.compile(r'^(\w+)\s(.+?)\s(N|S|E|W|NW|NE|SW|SE)$')

def parse_address_with_regex(address_string):
    """
    This function uses a regular expression to parse and reformat an address.

    More info on regular expressions are here:
        http://docs.python.org/library/re.html
    """
    # Try matching the address_string against the address_pattern
    regex_match = address_pattern.match(address_string.strip()) 

    if regex_match:
        # If there's a match, then assign the address components to variables
        number, address, direction = regex_match.groups()
        # Reformat the address components into a new string
        new_address = "%s %s %s" % (number, direction, address)
    else:
        new_address = address_string

    return new_address


if __name__ == '__main__':
    # The "doctest" code at the bottom of this program is boilerplate syntax
    # to help run tests inside of Python docstrings. 
    
    # Doctests not only help ensure that your code works as expected, 
    # but they help demonstrate to others how to properly use your code.

    # These tests resemble the code from a session in the Python 
    # interactive interpreter, and in fact, you can copy and paste code from
    # such sessions directly into your Python program.
    # 
    # The doctests in this program are at the top of the file, right beneath 
    # the "Usage" line. To run the doctests in this program, execute the 
    # following command from your shell or terminal:
    #     python address_parser.py -v

    # More info on doctests can be found here:
    #     http://docs.python.org/library/doctest.html
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = convert_json_to_csv
"""
This script performs a Twitter search on Egypt, for English language tweets.  Using the Twitter JSON API, it takes those tweets, iterates through returned JSON files
and pulls key information into a CSV.  Could be adapted to transform other JSON APIs into structured data in spreadsheet or database form.
"""

#To put this into a CSV, csv code adapted from this recipe (http://www.palewire.com/posts/2009/03/03/django-recipe-dump-your-queryset-out-as-a-csv-file/) of Ben Welsh at the LAT (who taught me much of this while I interned over there):


# IMPORTS


#Make Python understand how to read things on the Internet
import urllib2

#Make Python understand the stuff in a page on the Internet is JSON
import json

# Make Python understand csvs
import csv

# Make Python know how to take a break so we don't hammer API and exceed rate limit
from time import sleep

# tell computer where to put CSV
outfile_path='/Users/MichelleMinkoff/Desktop/test.csv'

# open it up, the w means we will write to it
writer = csv.writer(open(outfile_path, 'w'))

#create a list with headings for our columns
headers = ['user', 'date_created','tweet_text','latitude', 'longitude']

#write the row of headings to our CSV file
writer.writerow(headers)


# GET JSON AND PARSE IT INTO DICTIONARY

# We need a loop because we have to do this for every JSON file we grab

#set a counter telling us how many times we've gone through the loop, this is the first time, so we'll set it at 1
i=1

#loop through pages of JSON returned, if you have 100 tweets per pg, and there's 1500 tweet limit on searches, 15 pages will do it
while i<=15:
    #print out what number loop we are on, which will make it easier to track down problems when they appear
    print i
    #create the URL of the JSON file we want.  We search for 'egypt', want English tweets, and set the number of tweets per JSON file to the max of 100, so we have to do as little looping as possible
    url = urllib2.Request('http://search.twitter.com/search.json?q=egypt&lang=en&rpp=100&page=' + str(i))
    #use the JSON library to turn this file into a Pythonic data structure
    parsed_json = json.load(urllib2.urlopen(url))    
    #now you have a giant dictionary.  Type in parsed_json here to get a better look at this.  You'll see the bulk of the cotent is contained inside the value that goes with the key, or label "results".  Refer to results as an index.  Just like list[1] refers to the second item in a list, dict['results'] refers to values associated with the key 'results'.  I'll do a better job explaining for next week.
    print parsed_json


#TRANSFORM JSON INTO STRUCTURED ROWS THAT FORM OUR CSV


    #run through each item in results, and jump to an item in that dictionary, in this case, the text of the tweet    
    for tweet in parsed_json['results']:
            #initialize the row
            row = []
            #add every 'cell' to the row list, identifying the item just like an index in a list
            row.append(str(tweet['from_user'].encode('utf-8')))           
            row.append(str(tweet['created_at'].encode('utf-8')))
            row.append(str(tweet['text'].encode('utf-8')))
            #Often, no geo info comes with the tweet.  Python can't grab nothing, so it'll choke.
            #We help the computer out by putting on a condition: Only do the following, if there's a value to go with the geo key.
            if tweet['geo']:
                #We need to dig into the geo object, which is yet ANOTHER dictionary, to get to the coordinates list.
                #Then separate that list into two separate columns, so we can deal w/lat + long separately.
                # We use the index to specify which item in the list we care about.
                row.append(str(tweet['geo']['coordinates'][0]).encode('utf-8'))
                row.append(str(tweet['geo']['coordinates'][1]).encode('utf-8'))
           # Wait!  What if there's no geo information?  Let's fill those cells in with empty strings.
           #It's not a big deal here, but if we had more columns after the blank ones, without something in these cells, the next cells would be two columns off.
           #The list structure takes positions very literally, so I've found it to be good practice to fill in cells with an else condition to avoid mistakes.
            else:
                row.append("")
                row.append("")
            #once you have all the cells in there, write the row to your csv
            writer.writerow(row)
    #increment our loop counter, now we're on the next time through the loop
    i = i +1
    #tell Python to rest for 5 secs, so we don't exceed our rate limit
    sleep(5)
########NEW FILE########
__FILENAME__ = guessing_game
"""
This script demonstrates statement concepts in Chapter 10
of Learning Python, 4th Edition, by Mark Lutz.
Script adapted from a game in http://inventwithpython.com/chapter4.html
"""

# A guess-the-number game.

# Module for generating random numbers
import random

# Init variables to count guesses and for a number to be guessed
guessesTaken = 0
number = random.randint(1, 20)

# Get the player's name. 
# Also, use a newline character (\n) to pretty up the screen
myName = raw_input('\nHello! What is your name? ')

print "\nLet's play a game, " + myName + '. I am thinking of a number between 1 and 20.'

# Here's our while loop. The player gets six tries.
# Note that we can nest if/else statements in others
while guessesTaken < 6:

# If it's the player's first try, print one statement; on subsequent tries, print 'another'
    if guessesTaken == 0:
        print 'Take a guess: ' 
    else: print 'Take another guess: '  # Note the alternate to indenting
    
# Retrieve the guess and increment the counter by 1
    guess = raw_input()
    guessesTaken = guessesTaken + 1

# Here we use a try/except statement to catch errors that occur if the player
# types in a string or a decimal instead of a whole number.
#
# In the "try" portion, we attempt to convert the input to an integer.
# If that fails, the "except" block is triggered and we print a warning.
#
# If conversion succeeds, the "else" block executes and we give hints. Again,
# nested if/else statements are used to provide levels of hints. Ultimately,
# if the player guesses the number or if the number of attempts maxes out, 
# we exit the loop.
    try:
        guess = int(guess)
    except:
        print 'Whole numbers only, please!'
    else:     
        if guess < number:
            if guess == number - 1:
                print "You're low but real close!"
            else:
                print 'Your guess is too low.' 
        elif guess > number:
            if guess == number + 1:
                print "You're high but real close!"
            else: 
                print 'Your guess is too high.'
        elif guess == number:
            break

# Finally, two blocks to display success or failure.
if guess == number:
    guessesTaken = str(guessesTaken)
    print '\nYou got it, ' + myName + '! You guessed my number in ' + guessesTaken + ' tries!'

if guess != number:
    number = str(number)
    print '\nOut of luck! The number I was thinking of was ' + number


########NEW FILE########
__FILENAME__ = csv_module_tutorial
#!/usr/bin/env python
"""
This script shows how to read and write data using Python's built-in csv module.
The csv module is smart enough to handle fields that contain apostrophes, 
commas and other common field delimiters. In this tutorial, we'll show how to:
 * use csv to read data
 * work with CSV column headers
 * read data as a stream 
 * write data back out using csv

The official Python docs for the csv module can be found here:
  http://docs.python.org/library/csv.html

For this tutorial, we're using a subset of the FDIC failed banks list:
  http://www.fdic.gov/bank/individual/failed/banklist.html

"""
import csv
from datetime import datetime


"""
            Why the CSV module? 

With simple CSV data, you can often get away with reading data
from a file and "manually" handling the process of splitting up
lines into appropriate columns. 

But the manual approach is tricky and error-prone when dealing with
all but the simplest source data.

In the bank data, for instance, we see that the manual approach 
of splitting on commas will not work because the first bank 
-- "San Luis Trust Bank, FSB " -- contains a comma in its name.

"""

print "\n\nExample 1: Split lines manually\n"

for line in open('data/banklist_sample.csv'):
    clean_line = line.strip()
    data_points = clean_line.split(',')
    print data_points

"""
Splitting on a comma caused "San Luis Trust Bank, FSB " 
to become two fields: "San Luis Trust Bank" and "FSB".

In a case like this, it's much easier to let Python's 
built-in csv module handle the field parsing for you.



            Introducing the CSV module

We already imported the csv module at the top of this script.
Now we create a csv "reader" object, capable of stepping through
each line of the file and smartly parsing the fields.

The reader object is created by passing an open file to csv's 
reader function.

"""

print "\n\nExample 2: Read file with the CSV module\n"

bank_file = csv.reader(open('data/banklist_sample.csv', 'rb'))

for record in bank_file:
    print record 

"""
Notice that in the above example, csv is smart enough to handle 
the comma inside the first bank name. So instead of two fields,
it gives us "San Luis Trust Bank, FSB" as a single field.


            Customizing the Delimiters

By default, csv assumes the file is comma-delimited.  You can 
customize the delimiters, quote characters, and a number of 
other options by setting additional parameters when you create 
the reader object. More details on the avaiable options are here:
  http://docs.python.org/library/csv.html#dialects-and-formatting-parameters

Below, we set the field delimiter to a tab so that we can read a version 
of the bank data formatted as a "tsv" (tab-separated values).

"""

print "\n\nExample 3: Read tab-delimited data\n"

bank_file = csv.reader(open('data/banklist_sample.tsv', 'rb'), delimiter='\t')

for record in bank_file:
    print record

"""
        Working with Column Headers


Text files often come with column headers that you'll want to retain as labels
for your data. There are a number of ways to do this, and the approach
can vary depending on the number of columns and size of the file.

The simplest approach is to read all of the data into memory as a list,
and then grab the column headers from the beginning of the list.

"""

print "\n\nExample 4: Extracting Column Headers and Writing Out Data\n"

# Read all lines using a list comprehension
bank_records = [line for line in csv.reader(open('data/banklist_sample.tsv', 'rb'), delimiter='\t')]

# Pop header from the start of the list and save it
header = bank_records.pop(0) 
print header

# Open a new file object
outfile = open('data/banklist_sample_reformatted_dates.tsv', 'wb')

# Create a writer object
outfileWriter = csv.writer(outfile, delimiter='\t')

# Write out the header row
outfileWriter.writerow(header) 

# Now process and output the remaining lines. 
for record in bank_records:
    # Do some basic processing and then write the data back out

    # Below, we use Python's built-in datetime library to reformat 
    # the Closing and Update dates. 

    # First, we use the "strptime" method to parse dates formatted 
    # as "23-Feb-11" into a native Python datetime object.

    # Then we apply the "strftime" method to the resulting datetime
    # object to create a date formatted as YYYY-MM-DD.
    record[-1] = datetime.strptime(record[-1], '%d-%b-%y')
    record[-1] = record[-1].strftime('%Y-%m-%d')

    # We can combine the above steps into a single line
    record[-2] = datetime.strptime(record[-2], '%d-%b-%y').strftime('%Y-%m-%d')

    # Print to the shell and write data out to file
    print record
    outfileWriter.writerow(record)

# Closing the file ensures your data flushes out of the buffer 
# and writes to the output file
outfile.close()


"""

When working with large files, it's often wise to avoid reading the 
entire file into memory. Instead, you can read the data as a stream,
plucking each line from the file object as needed.

The way to do this is by calling a file object's "next" method. This is
what Python does implicitly when stepping through the lines of a file
in a "for" loop. We'll use the same method to extract our header line,
before continuing to process the file as a stream.

More details on file objects and the next method are here:
    http://docs.python.org/library/stdtypes.html#file.next

"""
print "\n\nExample 5: Reading Large Files as a Stream\n"

# Create a csv file object
bank_file = csv.reader(open('data/banklist_sample.tsv', 'rb'), delimiter='\t')

# Grab the header line from the file by calling the file object's next method
header = bank_file.next() 
print header

# Now proceed to process the remaining lines as normal
for record in bank_file:
    print record

########NEW FILE########
__FILENAME__ = cmte_parser
#!/usr/bin/env python
"""
This script demonstrates how to use column metadata to extract data 
points from a fixed-width text file.

Details such as the start and end positions of columns, 
when known in advance, can allow us to code a more flexible 
application. This lets us avoid having to update lots of hard-coded
start and end positions if the structure of our source data changes.

For this example, we're using the Federal Election Commission's master 
list of campaign committees:

  ftp://ftp.fec.gov/FEC/cm_dictionary.txt
  ftp://ftp.fec.gov/FEC/cm12.zip

The data dictionary describes the fields in the "foiacm.dta" file, 
contained in cm12.zip. It contains info such as the field's name,
start and end positions, and length.

Below, we've hard-coded the header values from the data dictionary. 
Ideally, in a real-world application, these header values would be 
extracted dynamically from an external source such as the data dictionary. 

See below for additional ideas on how to improve and extend this code sample.

        ####  Additional Exercises #### 

 - Create a function that performs additional clean-up on each
   data point, such as stripping extra white space, converting
   strings to integers, etc.

 - Update the parse_data function to accept a file argument, rather
   than hard-coding a path to a file 

 - Write a new function that uses the length of a column, rather than
   its offsets, to extract each field from a line

 - Write a function that can parse the FEC data dictionary and dynamically
   extract the column header info
"""

# Below are three data points from our data dictionary:
#     name, start-end position, number of characters
headers = [
  ("Committee Identification",      "1-9",     "9"),
  ("Committee Name",                "10-99",   "90"),
  ("Treasurer's Name",              "100-137", "38"),
  ("Street One",                    "138-171", "34"),
  ("Street Two",                    "172-205", "34"),
  ("City or Town",                  "206-223", "18"),
  ("State",                         "224-225", "2"),
  ("Zip Code",                      "226-230", "5"),
  ("Committee Designation",         "231-231", "1"),
  ("Committee TypeType",            "232-232", "1"),
  ("Committee Party",               "233-235", "3"),
  ("Filing Frequency",              "236-236", "1"),
  ("Interest Group Category",       "237-237", "1"),
  ("Connected Organiz's NameError", "238-275", "38"),
  ("Candidate Identification",      "276-284", "9"),
]

def get_column_offsets(headers):
    """
    Two key rules to remember when using the slice notation
      1) Values are zero-indexed, so you start counting from 0 instead of 1
      2) The first index in slice notation is *inclusive* and the second is *exclusive*
    
    >>> x = 'Python'
    >>> x[0:2] # get the first two letters (positions 0 and 1)
    'Py'
    """ 
    column_offsets = []
    for header in headers:
        # We do a bunch of work in one line below:
        #  Extract the second item from the tuple
        #  Split that item on the dash into two values 
        #  Assign those values to the start_value and end_value variables
        start_value, end_value = header[1].split('-')
        # Before storing our indexes, we convert the strings values to integers 
        # and "zero-index" our start position by subtracting 1 
        column_offsets.append( (int(start_value) - 1, int(end_value)) )
    # Finally, we return our list of column offsets
    return column_offsets


def parse_data():
    """
    This function returns a list of parsed campaign committee records.
    It relies on the get_column_offsets function to extract the data
    points from each line.
    """
    column_offsets = get_column_offsets(headers)
    
    # Set up a list to store our parsed committee records
    committees_data = []
    
    # Extract the data using our offsets
    for line in open('foiacm.dta'):
        # For each line, create a record to store the various data points
        record = []
        
        # Now, step through each of our column_offsets
        # and use them to extract the fields from our
        # line. Recall that the values in the column_offsets
        # list are just tuples like (0-9).
        for start, end in column_offsets:
            # ADDITIONAL DATA CLEANING HERE
            # Below, we're just appending each column
            # to a list and then returning that list. 
            # In a real application, this would be a good place
            # to do some additional data clean-up,
            # such as calling the strip method on each 
            # value, converting strings to integers as appropriate, etc.
            record.append(line[start:end])
        committees_data.append(record)
    
    # Return our parsed records
    return committees_data

# The below code snippet ("if __name__ == '__main__') is a very common
# convention used in Python programs. Basically, it tells Python to run 
# the ensuing code whenever the program is called from the command line.
if __name__ == '__main__':
    # Generate our data points, and then print the first 10 records
    data = parse_data()
    for item in data[:10]:
        print item

########NEW FILE########
__FILENAME__ = contributions_parser
#!/usr/bin/env python
"""
This script demonstrates an alternative method for flexibly parsing 
fixed-width text.

In cmte_parser.py, we extracted each data point using the start and 
end points for each column (based on column descriptions in a data 
dictionary).

This time, we'll use Python's "struct" module to extract the columns.  
This built-in module lets you parse a string according to a pre-determined
format. For more details on the struct module, see:
  
  http://docs.python.org/library/struct.html


For this example, we'll use the Federal Election Commission's 
committee-to-committee, itemized contributions:

  ftp://ftp.fec.gov/FEC/DATA_DICTIONARIES/oth_dictionary.txt
  ftp://ftp.fec.gov/FEC/oth12.zip

The data dictionary describes the fields in the "itoth.dta" file, 
contained in itoth12.zip. It contains info such as the field's name,
start and end positions, and data type and length.
"""
from struct import unpack

# Below, we've hard-coded the FEC's field format codes, but ideally, these
# would be extracted dynamically from the data dictionary or another
# external file
FEC_FORMAT_CODES = ['9s', '1s', '3s', '1s', '11s', '3s', '34s', '18s', '2s', 
                    '5s', '35s', '2d', '2d', '2d', '2d', '7n', '9s', '7s',]


def get_header_format(format_codes):
    """
    This function returns a string format for use with the struct module.
    It requires a list of format codes extracted from a Data Dictionary.
    """
    # Below, we use a list comprehension to step through the FEC format codes.
    # Inside the list comp, we use slice notation to extract all but the last
    # the letter of each format code. This last letter represents the FEC's 
    # data-type specifier, which we can use elsewhere to properly convert our
    # data types. 
    # Finally, we use the "join" function to combine the list of format strings
    # and return that string.
    return "".join(["%ss" % format_code[0:-1] for format_code in FEC_FORMAT_CODES])

if __name__ == '__main__':
    format = get_header_format(FEC_FORMAT_CODES)
    for line in open('itoth.dta'):
        print unpack(format, line.strip())

########NEW FILE########
__FILENAME__ = glob_usage_example
#!/usr/bin/env python
"""
 This script shows how to use the glob module to grab a list of 
 filenames in a directory.  This is a convenient way to quickly 
 generate a list of files for additional processing.

 More info on the glob module can be found at:

    http://docs.python.org/library/glob.html
"""
import glob

# Use glob's asterisk wild-card to get a list of all '.csv'
# files in the iterables directory. Note that we're using 
# the glob function inside the identically named glob module,
# hence the "glob.glob" syntax below. 
my_filenames = glob.glob('data/iterables/*.csv')

# Now loop through the files and read the data
for infile in my_filenames:
    a = open(infile)
    print a.read() 
    a.close() # it's always wise to close your files after use :-)


# Alternatively, you can combine the "for" loop and glob
# into a single line of code
for infile in glob.glob('data/iterables/*.csv'):
    a = open(infile)
    print a.read()
    a.close()

########NEW FILE########
__FILENAME__ = read_data_from_CSV_1
#!/usr/bin/env python
"""
Below is a bare-bones example showing how to read data from a CSV.

We combine a "for" loop with the "open" function to read each line
and print it to the command-line screen.
 
The "open" function accepts a number of extra options, but in 
in its most basic form can simply be called with the path to a file.
"""

# Note to Windows users: When specifying a file path, be sure you
# set the file path appropriately with back-slashes
for line in open('data/SmokeFreeComplaints_tab_delimited.csv'):
    print line

########NEW FILE########
__FILENAME__ = sales_data_parser
#!/usr/bin/env python
"""
 This program shows how to read data from a CSV, perform some basic processing 
 on a column in that data, and then write the data out to a new file. 
 
 We first define an address-parsing function at the top of the file.
 Then we jump into the "main" portion of the program, which applies the
 address function to each row of data before writing it out to a new file.
"""
# We begin by importing the csv module, which helps you easily 
# parse tabular data that you'd normally work with in a
# spreadsheet program like Excel.
import csv

# Next, we define a function -- a reusable piece of code -- that will reformat 
# our address. This function checks to see if a direction (N, S, E, W, etc.) is 
# present at the end of an address. If so, it places the direction right before
# the street name: "123 Main St N" --> "123 N Main St"

# We'll apply this function to each address farther down in the  program,  
# when we loop through each line of our source data (below function is 
# courtesy of Brian Bowling).

def parse_address(address):
    # find the first and last spaces in the string
    last_space = len(address) - 1
    first_space = 0

    while address[last_space] != " ":
        last_space -= 1

    while address[first_space] != " ":
        first_space += 1
    
    # Test if the characters following the last space are a direction
    if address[last_space + 1:] in ("N", "S", "E", "W", "NE", "NW", "SE", "SW"):
    # Reformat the address 
        new_address = address[:first_space] + address[last_space:] + address[first_space:last_space]
    else:
        new_address = address

    return new_address


# The "main" function below is where the action happens. It's where we open
# the file, read in the data, apply our function to reformat the address, 
# and then write our data back out to a file. 

def main():

    # Open a file using the csv module
    source_data = csv.reader(open('data/SalesSnippet.csv','rb'))

    # Grab the column names from the first line
    header = source_data.next() # PRICE, ADDRESS, CITY, STATE, ZIP, ORIG

    # Open an output file and add the column headers
    output_file = csv.writer(open('data/SalesSnippet_output.csv','wb')) 
    output_file.writerow(header)

    # Now process the data in the input file
    for row in source_data:
        # Here's where "csv" is really helpful. It automatically parses
        # our columns into a list of data points. All we have to do is 
        # assign these data points to some variables, and then we can 
        # do some additional processing on each one. Below, we use
        # a technique known as "sequence unpacking" to assign the data 
        # points in the "row" variable, which is a list, to a 
        # bunch of variables.
        price, address, city, state, zipcode, orig = row

        # Now we can apply the code to reformat the address
        clean_address = parse_address(address)
        
        # Finally, we write out our new line with the clean address. Note
        # that the "writerow" method requires a list of data
        output_file.writerow([price, clean_address, city, state, zipcode, orig])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = failed_banks_scrape
#!/usr/bin/env python
"""
This scrape demonstrates some Python basics using the FDIC's Failed Banks List.
It downloads a single web page and shows how to use a 3rd-party library
to extract data from the HTML.

USAGE:

You can run this scrape by going to command line, navigating to the
directory containing this script, and typing the below command:

    python failed_banks_scrape.py

NOTE:

The original FDIC data is located at the below URL:

    http://www.fdic.gov/bank/individual/failed/banklist.html

In order to be considerate to the FDIC's servers, we're scraping 
a copy of the page stored on Amazon S3.
"""

# Import a built-in library for working with data on the Web
# DOCS: http://docs.python.org/library/urllib.html
import urllib

# import a 3rd-party to help extract data from raw HTML
# DOCS: http://www.crummy.com/software/BeautifulSoup/documentation.html  
from BeautifulSoup import BeautifulSoup

# URL of the page we're going to scrape (below is the real URL, but
# we'll hit a dummy version to be kind to the FDIC)
URL = 'https://s3.amazonaws.com/python-journos/FDIC_Failed_Bank_List.html'

# Open a network connection using the "urlopen" method. 
# This returns a network "object" 
# http://docs.python.org/library/urllib.html#high-level-interface
web_cnx = urllib.urlopen(URL)

# Use the network object to download, or "read", the page's HTML
html = web_cnx.read() 

# Parse the HTML into a form that's easy to use
soup = BeautifulSoup(html)

# Use BeautifulSoup's API to extract your data
# 1) Fetch the table by ID
table  = soup.find(id='table') 

# 2) Grab the table's rows
rows = table.findAll('tr')

# 3) Get header names from first row
headers = rows[0].findAll('th')

# Extract the column names and add them to a list
columns = []
for header in headers:
    columns.append(header.text)

# Use the tab character's "join" method to concatenate
# the column names into a single, tab-separated string.
# Then print out the header column.
print '\t'.join(columns)

# 4) Process the data, skipping the initial header row
for row in rows[1:]:

    # Extract data points from the table row
    data = row.findAll('td')

    # Pluck out the text of each field and store in a separate variable
    bank_name = data[0].text    
    city = data[1].text
    state = data[2].text
    cert_num = data[3].text
    ai =  data[4].text
    closed_on = data[5].text 
    updated = data[6].text

    print "\t".join([bank_name, city, state, cert_num, ai, closed_on, updated])

########NEW FILE########
__FILENAME__ = fec_efiles_scrape
#!/usr/bin/env python
"""
This scrape demonstrates how to "fill out" an
online form to fetch data from a remote server.

More accurately, we'll show how to make a POST request
to fetch a list of links for campaign finance reports
from the Federal Election Election Commission.

We'll then use these links to download campaign finance data
(in CSV format) for a specific committee.

The electronic filings/form we're using in this script can be found at:

    http://fec.gov/finance/disclosure/efile_search.shtml

USAGE:

You can run this scrape by going to command line, navigating to the
directory containing this script, and typing the below command:

    python fec_efiles_scrape.py


HELPFUL LINKS:

 Python Modules used in this script:
 * BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/documentation.html
 * CSV:           http://docs.python.org/library/csv.html
 * requests:      http://docs.python-requests.org/en/latest/user/quickstart/
 * sys:           http://docs.python.org/library/sys.html

 HTTP codes
 * http://en.wikipedia.org/wiki/List_of_HTTP_status_codes

"""
import csv
import sys

import requests
from BeautifulSoup import BeautifulSoup

# Build a dictionary containing our form field values
# http://docs.python.org/tutorial/datastructures.html#dictionaries
form_data = {
    'name':'Romney', # committee name field
    'type':'P',      # committee type is P for Presidential
    'frmtype':'F3P', # form type
}

# Make the POST request with the form dictionary. This should
# return a response object containing the status of the request -- ie
# whether or not it was successful -- and raw HTML for the returned page.
response = requests.post('http://query.nictusa.com/cgi-bin/dcdev/forms/', data=form_data)

# If the request was successful, then process the HTML
if response.status_code == 200:

    # The raw HTML is stored in the response object's "text" attribute
    soup = BeautifulSoup(response.text)
    links = soup.findAll('a')

    # Extract the download links
    download_links = []
    for link in links:
        if link.text == 'Download':
            download_links.append(link)

    """
    NOTE: We could replace the 4 lines of code above with the single line below:

    download_links = soup.findAll('a', href=lambda path: path.startswith('/cgi-bin/dcdev/forms/DL/'))

    This one-liner leverages one of BeautifulSoup's more advanced features -- specifically, the
    ability to filter the "findAll" method's results by applying regular expressions or
    lambda functions.

    Above, we used a lambda function to filter for links with "href"
    attributes starting with a certain URL path.

    To learn more:

    * http://www.crummy.com/software/BeautifulSoup/documentation.html
    * http://stackoverflow.com/questions/890128/python-lambda-why
    * http://docs.python.org/howto/regex.html
    """

    # Now that we have our target links, we can download CSVs for further processing.

    # Below is the base URL for FEC Filing CSV downloads.
    # Notice the "%s" format character at the end.
    BASE_URL =  'http://query.nictusa.com/comma/%s.fec'

    # To get at the raw data for each filing, we'll combine the above BASE_URL with
    # unique FEC report numbers (found in the download_links that we extracted above).


    for link in download_links:

        # Below, we use a single line of code to extract the unique FEC report number:
        fec_num = link.get('href').strip('/').split('/')[-1]

        # The one-liner above uses "method chaining" to:
        # 1) Extract the "href" attribute from the link and return it as a string
        # 2) Strip the slashes from either end of returned URL path string
        # 3) Split the resulting string on slashes, which returns a list of URL path components
        # 4) Extract the last element of the list (denoted by "-1"), which should be the FEC number

        # Use string interpolation to build the final download link
        # http://docs.python.org/library/stdtypes.html#string-formatting-operations
        csv_download_link =  BASE_URL % fec_num

        # Fetch the CSV data
        response = requests.get(csv_download_link)

        # Create a list of data rows by splitting on the line terminator character
        data_rows = response.text.split('\n')

        # Use the CSV module to parse the comma-separated rows of data. Calling
        # the built-in "list" function causes csv to parse our data strings
        # into lists of distinct data points (the same as if it they were
        # in a spreadsheet or database table).
        # http://docs.python.org/library/csv.html
        data = list(csv.reader(data_rows))

        # The first row in the FEC data contains useful info about the format of
        # the remaining rows in the file.
        # However, after the initial creation of this scraper, there is at least one bad
        # link that we have to handle.

        # First we try to extract the version. If it is successful, then continue.
        # If not, we moves to the exception handling section.
        try:
            version = data[0][2] # e.g., 8.0
        # This exception handling section looks for our bad link which causes the program
        # to throw an IndexError. We going to define a special url for this case.

        except IndexError:
            # If you look at the code below, you will notice that it repeats what we had above.
            # However, the csv_download link is redefined.
            # For the best practice, we would pull out this pattern into a function.
            # Then we would call the function above then again if the error occurs.
            # We encourage you to try to turn this piece of code into a function that is
            # called twice.
            ALT_BASE_URL = 'http://query.nictusa.com/showcsv/nicweb26502/%s.fec'
            csv_download_link =  ALT_BASE_URL % fec_num
            response = requests.get(csv_download_link)
            data_rows = response.text.split('\n')
            data = list(csv.reader(data_rows))
            version = data[0][2] # e.g., 8.0
            # If the program has another index error at this point, this means that our
            # catch/fix didn't work. More troubleshooting and exception handling might
            # be needed.

        print "Downloaded Electronic filing with File Format Version %s" % version

        ### WHAT'S NEXT? ###
        # In a normal script you would use the version number to fetch the
        # the appropriate file formats, which could then be used to process
        # the remaining data in the file.

        # But we know you get the picture -- and we want to be kind to
        # the FEC's servers -- so we'll exit the program early and assign
        # the rest of the script as homework :-)
        sys.exit("Exited script after processing one link.")

else:
    # Gracefully exit the program if response code is not 200
    sys.exit("Response code not OK: %s" % response.status_code)

########NEW FILE########
__FILENAME__ = la_election_scrape
#!/usr/bin/env python
"""
This scrape demonstrates how to 'page through' links and build on other
scripts in the PyJournos webscraping tutorial folder located here:

    https://github.com/PythonJournos/LearningPython/tree/master/tutorials/webscraping101

The site that we are using for this example can be found here:

    http://staticresults.sos.la.gov/


USAGE:

You can run this scrape by going to command line, navigating to the
directory containing this script, and typing the below command:

    python la_election_scrape.py

This script assumes that you learned about the requests library from the
fec_efiles_scrape.py file. Also, please note, that this script can take more than
30 seconds to run. Be patient.

HELPFUL LINKS:

 Python Modules used in this script:
 * BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/documentation.html
 * CSV:           http://docs.python.org/library/csv.html
 * requests:      http://docs.python-requests.org/en/latest/user/quickstart/

 HTTP codes
 * http://en.wikipedia.org/wiki/List_of_HTTP_status_codes

"""
import csv
import requests

from BeautifulSoup import BeautifulSoup

URL = 'http://staticresults.sos.la.gov/'

response = requests.get(URL)

# Create an empty link to identify bad links & race links
bad_links = []
races_links = []
date_links = []

if response.status_code == 200:

    # Parse the HTML into a form that's easy to use
    soup = BeautifulSoup(response.text)

    # Use BeautifulSoup's API to extract your data
    # This page is clean & simple. All links are links we want to crawl.
    # So, let's grab them all.

    for tag in soup.table:

        # soup.table is made of h1 tags & links.
        # only save links, which have a name equal to 'a'
        if tag.name == 'a':

            # 'href' is an attribute of item
            relative_link = tag['href']

            # the election date the text, so let's grab that to associate
            # with the link
            date = tag.text

            # we need a complete link to follow, so let's create that
            absolute_link = URL + relative_link

            # now we add the date & abs link to our list
            date_links.append((date, absolute_link))

'''
Note: at this point, we have a list links that looks something like this:
[
(u'04051986', u'http://staticresults.sos.la.gov/04051986/Default.html')
(u'02011986', u'http://staticresults.sos.la.gov/02011986/Default.html')
(u'01181986', u'http://staticresults.sos.la.gov/01181986/Default.html')
(u'03301985', u'http://staticresults.sos.la.gov/03301985/Default.html')
...
]
'''

# Now, we would apply the same logic as we are approaching the first page,
# except for now, we would apply that logic to each link in a for loop.
# Let's pull out links all of the race types on each page

for item in date_links:

    # to clarify which item is which in each tuple
    # this is extra code for demo purposes
    # Example item: (u'03301985', u'http://staticresults.sos.la.gov/03301985/Default.html')
    date = item[0]
    link = item[1]

    # this looks familar
    response = requests.get(link)

    # while we do not explain functions in this demo, this would be a good use
    # if you are feeling adventurous, you should try to turn & the code at
    # the start of the script into a funciton, then call that function

    if response.status_code == 200:
        soup = BeautifulSoup(response.text)

        # more familar stuff
        races_tags = soup.table.findAll('a')
        for races_tag in races_tags:
            relative_link = races_tag['href']
            absolute_link = URL + relative_link

            # now let's add the date, races_type, and races_link to the tuple
            races_type = races_tag.text
            races_links.append((date, races_type, absolute_link))

    else:
        bad_links.append((response.status_code, link))


################################################################################

# THE RESULTS:
# This is for easy viewing of the new list & not required for this script
count = 0
while count < 20:  # The number 50 is used to limit the output.
    for link in races_links:
        print "Election date: %s, Races link type: %s, Link: %s" % (link[0], link[1], link[2])
        count+=1

# Let's see which links failed
for bad_link in bad_links:
    print "Response code: %s, Link: %s" % (bad_link[0], bad_link[1])


'''
End Result looks something like this:
[
(u'10/22/2011', u'All Races in a Parish', u'http://staticresults.sos.la.gov/10222011_Parishes.html')
(u'07/16/2011', u'All Races in a Parish', u'http://staticresults.sos.la.gov/07162011_Parishes.html')
(u'04/30/2011', u'LA Legislature Races', u'http://staticresults.sos.la.gov/04302011_Legislative.html')
(u'04/30/2011', u'Multi-Parish Races', u'http://staticresults.sos.la.gov/04302011_MultiParish.html')
....
]

These are the bad links that came back:
[(404, u'http://staticresults.sos.la.gov/11021982/Default.html'),
(404, u'http://staticresults.sos.la.gov/09111982/Default.html')]
'''

########NEW FILE########
