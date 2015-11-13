__FILENAME__ = cliargs
# Geodict
# Copyright (C) 2010 Pete Warden <pete@petewarden.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, string

def print_usage_and_exit(cliargs):
	print "Usage:"
	
	for long, arginfo in cliargs.items():
		short = arginfo['short']
		type = arginfo['type']
		required = (type=='required')
		optional = (type=='optional')
		description = arginfo['description']
		
		output = '-'+short+'/--'+long+' '

		if optional or required:
			output += '<value> '

		output += ': '+description

		if required:
			output += ' (required)'

		print output
	
	exit()

def get_options(cliargs):

    options = {'unnamed': [] }
    skip_next = False
    for index in range(1, len(sys.argv)):
        if skip_next:
            skip_next = False
            continue
    
        currentarg = sys.argv[index].lower()
        argparts = currentarg.split('=')
        namepart = argparts[0]

        if namepart.startswith('--'):
            longname = namepart[2:]
        elif namepart.startswith('-'):
            shortname = namepart[1:]
            longname = shortname
            for name, info in cliargs.items():
                if shortname==info['short']:
                    longname = name
                    break
        else:
            longname = 'unnamed'

        if longname=='unnamed':
            options['unnamed'].append(namepart)
        else:
            if longname not in cliargs:
                print "Unknown argument '"+longname+"'"
                print_usage_and_exit(cliargs)
            
            arginfo = cliargs[longname]
            argtype = arginfo['type']
            if argtype=='switch':
                value = True
            elif len(argparts) > 1:
                value = argparts[1]
            elif (index+1) < len(sys.argv):
                value = sys.argv[index+1]
                skip_next = True
            else:
                print "Missing value after '"+longname+"'"
                print_usage_and_exit(cliargs)

            options[longname] = value

    for longname, arginfo in cliargs.items():
        type = arginfo['type']

        if longname not in options:
            if type == 'required':
                print "Missing required value for '"+longname+"'"
                print_usage_and_exit(cliargs)
            elif type == 'optional':
                if not 'default' in arginfo:
                    die('Missing default value for '+longname)
                options[longname] = arginfo['default']
            elif type == 'switch':
                options[longname] = False
            else:
                die('Unknown type "'+type+'" for '+longname)

    return options

########NEW FILE########
__FILENAME__ = geodict
#!/usr/bin/env python

# Geodict
# Copyright (C) 2010 Pete Warden <pete@petewarden.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import csv, os, os.path, MySQLdb, sys, json, csv
import geodict_lib, cliargs
import cProfile

args = {
    'input': {
        'short': 'i',
        'type': 'optional',
        'description': 'The name of the input file to scan for locations. If none is set, will read from STDIN',
        'default': '-'
    },
    'output': {
        'short': 'o',
        'type': 'optional',
        'description': 'The name of the file to write the location data to. If none is set, will write to STDOUT',
        'default': '-'
    },
    'format': {
        'short': 'f',
        'type': 'optional',
        'description': 'The format to use to output information about any locations found. By default it will write out location names separated by newlines, but specifying "json" will give more detailed information',
        'default': 'text'
    }
};

options = cliargs.get_options(args)

input = options['input']
output = options['output']
format = options['format']

if input is '-':
    input_handle = sys.stdin
else:
    try:
        input_handle = open(input, 'rb')
    except:
        die("Couldn't open file '"+input+"'")
        
if output is '-':
    output_handle = sys.stdout
else:
    try:
        output_handle = open(output, 'wb')
    except:
        die("Couldn't write to file '"+output+"'")
        
text = input_handle.read()

#cProfile.run('locations = geodict_lib.find_locations_in_text(text)')

locations = geodict_lib.find_locations_in_text(text)

output_string = ''
if format.lower() == 'json':
    output_string = json.dumps(locations)
    output_handle.write(output_string)
elif format.lower() == 'text':
    for location in locations:
        found_tokens = location['found_tokens']
        start_index = found_tokens[0]['start_index']
        end_index = found_tokens[len(found_tokens)-1]['end_index']
        output_string += text[start_index:(end_index+1)]
        output_string += "\n"
    output_handle.write(output_string)
elif format.lower() == 'csv':
    writer = csv.writer(output_handle)
    writer.writerow(['location', 'type', 'lat', 'lon'])
    for location in locations:
        found_tokens = location['found_tokens']
        start_index = found_tokens[0]['start_index']
        end_index = found_tokens[len(found_tokens)-1]['end_index']
        name = text[start_index:(end_index+1)]
        type = found_tokens[0]['type'].lower()
        lat = found_tokens[0]['lat']
        lon = found_tokens[0]['lon']
        writer.writerow([name, type, lat, lon])
else:
    print "Unknown output format '"+format+"'"
    exit()
    

########NEW FILE########
__FILENAME__ = geodict_config
# Geodict
# Copyright (C) 2010 Pete Warden <pete@petewarden.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# The location of the source data to be loaded into your database
source_folder = './source_data/'

# Your MySQL user credentials
user = 'root'
password = ''

# The address and port number of your database server
host = 'localhost'
port = 0

# The name of the database to create
database = 'geodict'

# The maximum number of words in any name
word_max = 3

# Words that provide evidence that what follows them is a location
location_words = {
    'at': True,
    'in': True
}
########NEW FILE########
__FILENAME__ = geodict_lib
# Geodict
# Copyright (C) 2010 Pete Warden <pete@petewarden.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import MySQLdb, string, StringIO
import geodict_config
from tempfile import TemporaryFile
from struct import unpack, pack, calcsize

# The main entry point. This function takes an unstructured text string and returns a list of all the
# fragments it could identify as locations, together with lat/lon positions
def find_locations_in_text(text):

    try:
        cursor = get_database_connection()
    except:
        print "Database connection failed. Have you set up geodict_config.py with your credentials?"
        return None

    current_index = len(text)-1
    result = []

    setup_countries_cache(cursor)
    setup_regions_cache(cursor)
    
    # This loop goes through the text string in *reverse* order. Since locations in English are typically
    # described with the broadest category last, preceded by more and more specific designations towards
    # the beginning, it simplifies things to walk the string in that direction too
    while current_index>=0:

        current_word, pulled_index, ignored_skipped = pull_word_from_end(text, current_index)
        lower_word = current_word.lower()
        could_be_country = lower_word in countries_cache
        could_be_region = lower_word in regions_cache
        
        if not could_be_country and not could_be_region:
            current_index = pulled_index
            continue

        # This holds the results of the match function for the final element of the sequence. This lets us
        # optimize out repeated calls to see if the end of the current string is a country for example
        match_cache = {}
    
        # These 'token sequences' describe patterns of discrete location elements that we'll look for.
        for token_sequence in token_sequences:
            
            # The sequences are specified in the order they'll occur in the text, but since we're walking
            # backwards we need to reverse them and go through the sequence in that order too
            token_sequence = token_sequence[::-1]
    
            # Now go through the sequence and see if we can match up all the tokens in it with parts of
            # the string
            token_result = None
            token_index = current_index
            for token_position, token_name in enumerate(token_sequence):
            
                # The token definition describes how to recognize part of a string as a match. Typical
                # tokens include country, city and region names
                token_definition = token_definitions[token_name]  
                match_function = token_definition['match_function']
                
                # This logic optimizes out repeated calls to the same match function
                if token_position == 0 and token_name in match_cache:
                    token_result = match_cache[token_name]
                else:
                    # The meat of the algorithm, checks the ending of the current string against the
                    # token testing function, eg seeing if it matches a country name
                    token_result = match_function(cursor, text, token_index, token_result)
                    if token_position == 0:
                        match_cache[token_name] = token_result
                
                if token_result is None:
                    # The string doesn't match this token, so the sequence as a whole isn't a match
                    break
                else:
                    # The current token did match, so move backwards through the string to the start of
                    # the matched portion, and see if the preceding words match the next required token
                    token_index = token_result['found_tokens'][0]['start_index']-1
            
            # We got through the whole sequence and all the tokens match, so we have a winner!
            if token_result is not None:
                break
            
        if token_result is None:
            # None of the sequences matched, so back up a word and start over again
            ignored_word, current_index, end_skipped = pull_word_from_end(text, current_index)
        else:
            # We found a matching sequence, so add the information to the result
            result.append(token_result)
            found_tokens = token_result['found_tokens']
            current_index = found_tokens[0]['start_index']-1
    
    # Reverse the result so it's in the order that the locations occured in the text
    result = result[::-1]
    
    return result

# Functions that look at a small portion of the text, and try to identify any location identifiers

# Caches the countries and regions tables in memory
countries_cache = {}

def setup_countries_cache(cursor):
    select = 'SELECT * FROM countries;'
    cursor.execute(select)
    candidate_rows = cursor.fetchall()
    
    for candidate_row in candidate_rows:
        candidate_dict = get_dict_from_row(cursor, candidate_row)
        last_word = candidate_dict['last_word'].lower()
        if last_word not in countries_cache:
            countries_cache[last_word] = []
        countries_cache[last_word].append(candidate_dict)

regions_cache = {}

def setup_regions_cache(cursor):
    select = 'SELECT * FROM regions;'
    cursor.execute(select)
    candidate_rows = cursor.fetchall()
    
    for candidate_row in candidate_rows:
        candidate_dict = get_dict_from_row(cursor, candidate_row)
        last_word = candidate_dict['last_word'].lower()
        if last_word not in regions_cache:
            regions_cache[last_word] = []
        regions_cache[last_word].append(candidate_dict)

# Matches the current fragment against our database of countries
def is_country(cursor, text, text_starting_index, previous_result):
        
    current_word = ''
    current_index = text_starting_index
    pulled_word_count = 0
    found_row = None

    # Walk backwards through the current fragment, pulling out words and seeing if they match
    # the country names we know about
    while pulled_word_count < geodict_config.word_max:
        pulled_word, current_index, end_skipped = pull_word_from_end(text, current_index)
        pulled_word_count += 1
        if current_word == '':
            # This is the first time through, so the full word is just the one we pulled
            current_word = pulled_word
            # Make a note of the real end of the word, ignoring any trailing whitespace
            word_end_index = (text_starting_index-end_skipped)
            
            # We've indexed the locations by the word they end with, so find all of them
            # that have the current word as a suffix
            last_word = pulled_word.lower()
            if last_word not in countries_cache:
                break
            candidate_dicts = countries_cache[last_word]
#            select = 'SELECT * FROM countries WHERE last_word=%s;'
#            values = (pulled_word, )
##            print "Calling '"+(select % values)+"'"
#            cursor.execute(select, values)
#            candidate_rows = cursor.fetchall()
#            # Nothing ended with this word, so we can skip the rest of the testing
#            if len(candidate_rows) < 1:
#                break
            
            name_map = {}
            for candidate_dict in candidate_dicts:
#                candidate_dict = get_dict_from_row(cursor, candidate_row)
                name = candidate_dict['country'].lower()
                name_map[name] = candidate_dict
        else:
            #
            current_word = pulled_word+' '+current_word

        # This happens if we've walked backwards all the way to the start of the string
        if current_word == '':
            return None

        # If the first letter of the name is lower case, then it can't be the start of a country
        # Somewhat arbitrary, but for my purposes it's better to miss some ambiguous ones like this
        # than to pull in erroneous words as countries (eg thinking the 'uk' in .co.uk is a country)
        if current_word[0:1].islower():
            continue

        name_key = current_word.lower()
        if name_key in name_map:
            found_row = name_map[name_key]

        if found_row is not None:
            # We've found a valid country name
            break
        if current_index < 0:
            # We've walked back to the start of the string
            break
    
    if found_row is None:
        # We've walked backwards through the current words, and haven't found a good country match
        return None
    
    # Were there any tokens found already in the sequence? Unlikely with countries, but for
    # consistency's sake I'm leaving the logic in
    if previous_result is None:
        current_result = {
            'found_tokens': [],
        }
    else:
        current_result = previous_result
                                        
    country_code = found_row['country_code']
    lat = found_row['lat']
    lon = found_row['lon']

    # Prepend all the information we've found out about this location to the start of the 'found_tokens'
    # array in the result
    current_result['found_tokens'].insert(0, {
        'type': 'COUNTRY',
        'code': country_code,
        'lat': lat,
        'lon': lon,
        'matched_string': current_word,
        'start_index': (current_index+1),
        'end_index': word_end_index 
    })
    
    return current_result

# Looks through our database of 2 million towns and cities around the world to locate any that match the
# words at the end of the current text fragment
def is_city(cursor, text, text_starting_index, previous_result):
    
    # If we're part of a sequence, then use any country or region information to narrow down our search
    country_code = None
    region_code = None
    if previous_result is not None:
        found_tokens = previous_result['found_tokens']
        for found_token in found_tokens:
            type = found_token['type']
            if type == 'COUNTRY':
                country_code = found_token['code']
            elif type == 'REGION':
                region_code = found_token['code']
    
    current_word = ''
    current_index = text_starting_index
    pulled_word_count = 0
    found_row = None
    while pulled_word_count < geodict_config.word_max:
        pulled_word, current_index, end_skipped = pull_word_from_end(text, current_index)
        pulled_word_count += 1
        
        if current_word == '':
            current_word = pulled_word
            word_end_index = (text_starting_index-end_skipped)

            select = 'SELECT * FROM cities WHERE last_word=%s'
            values = (pulled_word, )

            if country_code is not None:
                select += ' AND country=%s'

            if region_code is not None:
                select += ' AND region_code=%s'

            # There may be multiple cities with the same name, so pick the one with the largest population
            select += ' ORDER BY population;'
            
            # Unfortunately tuples are immutable, so I have to use this logic to set up the correct ones
            if country_code is None and region_code is None:
                values = (current_word, )
            elif country_code is not None and region_code is None:
                values = (current_word, country_code)
            elif country_code is None and region_code is not None:
                values = (current_word, region_code)
            else:
                values = (current_word, country_code, region_code)

#            print "Calling '"+(select % values)+"'"
            cursor.execute(select, values)
            candidate_rows = cursor.fetchall()
            if len(candidate_rows) < 1:
                break
            
            name_map = {}
            for candidate_row in candidate_rows:
                candidate_dict = get_dict_from_row(cursor, candidate_row)
                name = candidate_dict['city'].lower()
                name_map[name] = candidate_dict
        else:
            current_word = pulled_word+' '+current_word

        if current_word == '':
            return None
        
        if current_word[0:1].islower():
            continue

        name_key = current_word.lower()
        if name_key in name_map:
            found_row = name_map[name_key]

        if found_row is not None:
            break
        if current_index < 0:
            break
    
    if found_row is None:
        return None
    
    if previous_result is None:
        current_result = {
            'found_tokens': [],
        }
    else:
        current_result = previous_result
                                        
    lat = found_row['lat']
    lon = found_row['lon']
                
    current_result['found_tokens'].insert(0, {
        'type': 'CITY',
        'lat': lat,
        'lon': lon,
        'matched_string': current_word,
        'start_index': (current_index+1),
        'end_index': word_end_index 
    })
    
    return current_result

# This looks for sub-regions within countries. At the moment the only values in the database are for US states
def is_region(cursor, text, text_starting_index, previous_result):

    # Narrow down the search by country, if we already have it
    country_code = None
    if previous_result is not None:
        found_tokens = previous_result['found_tokens']
        for found_token in found_tokens:
            type = found_token['type']
            if type == 'COUNTRY':
                country_code = found_token['code']
    
    current_word = ''
    current_index = text_starting_index
    pulled_word_count = 0
    found_row = None
    while pulled_word_count < geodict_config.word_max:
        pulled_word, current_index, end_skipped = pull_word_from_end(text, current_index)
        pulled_word_count += 1
        if current_word == '':
            current_word = pulled_word
            word_end_index = (text_starting_index-end_skipped)
            
            last_word = pulled_word.lower()
            if last_word not in regions_cache:
                break
            all_candidate_dicts = regions_cache[last_word]
            if country_code is not None:
                candidate_dicts = []
                for possible_dict in all_candidate_dicts:
                    candidate_country = possible_dict['country_code']
                    if candidate_country.lower() == country_code.lower():
                        candidate_dicts.append(possible_dict)
            else:
                candidate_dicts = all_candidate_dicts
            
            name_map = {}
            for candidate_dict in candidate_dicts:
                name = candidate_dict['region'].lower()
                name_map[name] = candidate_dict
        else:
            current_word = pulled_word+' '+current_word

        if current_word == '':
            return None

        if current_word[0:1].islower():
            continue

        name_key = current_word.lower()
        if name_key in name_map:
            found_row = name_map[name_key]
        
        if found_row is not None:
            break
        if current_index < 0:
            break
    
    if found_row is None:
        return None
    
    if previous_result is None:
        current_result = {
            'found_tokens': [],
        }
    else:
        current_result = previous_result

    region_code = found_row['region_code']
    lat = found_row['lat']
    lon = found_row['lon']
                
    current_result['found_tokens'].insert(0, {
        'type': 'REGION',
        'code': region_code,
        'lat': lat,
        'lon': lon,
        'matched_string': current_word,
        'start_index': (current_index+1),
        'end_index': word_end_index 
    })
    
    return current_result

# A special case - used to look for 'at' or 'in' before a possible location word. This helps me be more certain
# that it really is a location in this context. Think 'the New York Times' vs 'in New York' - with the latter
# fragment we can be pretty sure it's talking about a location
def is_location_word(cursor, text, text_starting_index, previous_result):

    current_index = text_starting_index
    current_word, current_index, end_skipped = pull_word_from_end(text, current_index)
    word_end_index = (text_starting_index-end_skipped)
    if current_word == '':
        return None

    current_word = current_word.lower()
    
    if current_word not in geodict_config.location_words:
        return None

    return previous_result

# Utility functions

def get_database_connection():

    db=MySQLdb.connect(host=geodict_config.host,user=geodict_config.user,passwd=geodict_config.password,port=geodict_config.port)
    cursor=db.cursor()
    cursor.execute('USE '+geodict_config.database+';')

    return cursor


# Characters to ignore when pulling out words
whitespace = set(string.whitespace+"'\",.-/\n\r<>")

tokenized_words = {}

# Walks backwards through the text from the end, pulling out a single unbroken sequence of non-whitespace
# characters, trimming any whitespace off the end
def pull_word_from_end(text, index, use_cache=True):

    if use_cache and index in tokenized_words:
        return tokenized_words[index]

    found_word = ''
    current_index = index
    end_skipped = 0
    while current_index>=0:
        current_char = text[current_index]
        current_index -= 1
        
        char_as_set = set(current_char)
        
        if char_as_set.issubset(whitespace):
            if found_word is '':
                end_skipped += 1
                continue
            else:
                current_index += 1
                break
        
        found_word += current_char
    
    # reverse the result (since we're appending for efficiency's sake)
    found_word = found_word[::-1]
    
    result = (found_word, current_index, end_skipped)
    tokenized_words[index] = result

    return result

# Converts the result of a MySQL fetch into an associative dictionary, rather than a numerically indexed list
def get_dict_from_row(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Types of locations we'll be looking for
token_definitions = {
    'COUNTRY': {
        'match_function': is_country
    },
    'CITY': {
        'match_function': is_city
    },
    'REGION': {
        'match_function': is_region
    },
    'LOCATION_WORD': {
        'match_function': is_location_word
    }
}

# Particular sequences of those location words that give us more confidence they're actually describing
# a place in the text, and aren't coincidental names (eg 'New York Times')
token_sequences = [
    [ 'CITY', 'COUNTRY' ],
    [ 'CITY', 'REGION' ],
    [ 'REGION', 'COUNTRY' ],
    [ 'COUNTRY' ],
    [ 'LOCATION_WORD', 'REGION' ], # Regions are too common as words to use without additional evidence
];
########NEW FILE########
__FILENAME__ = populate_database
#!/usr/bin/env python

import csv, os, os.path, MySQLdb
import geodict_config
from geodict_lib import *

def wipe_and_init_database(cursor):
    cursor.execute("""DROP DATABASE geodict;""")
    cursor.execute("""CREATE DATABASE geodict;""")
    cursor.execute("""USE geodict;""")

def load_cities(cursor):
    cursor.execute("""CREATE TABLE IF NOT EXISTS cities (
        city VARCHAR(80),
        country CHAR(2),
        PRIMARY KEY(city, country),
        region_code CHAR(2),
        population INT,
        lat FLOAT,
        lon FLOAT,
        last_word VARCHAR(32),
        INDEX(last_word(10)));
    """)
    
    reader = csv.reader(open(geodict_config.source_folder+'worldcitiespop.csv', 'rb'))
    
    for row in reader:
        try:
            country = row[0]
            city = row[1]
            region_code = row[3]
            population = row[4]
            lat = row[5]
            lon = row[6]
        except:
            continue

        if population is '':
            population = 0

        city = city.strip()

        last_word, index, skipped = pull_word_from_end(city, len(city)-1, False)

        cursor.execute("""
            INSERT IGNORE INTO cities (city, country, region_code, population, lat, lon, last_word)
                values (%s, %s, %s, %s, %s, %s, %s)
            """,
            (city, country, region_code, population, lat, lon, last_word))

def load_countries(cursor):
    cursor.execute("""CREATE TABLE IF NOT EXISTS countries (
        country VARCHAR(64),
        PRIMARY KEY(country),
        country_code CHAR(2),
        lat FLOAT,
        lon FLOAT,
        last_word VARCHAR(32),
        INDEX(last_word(10)));
    """)
    
    reader = csv.reader(open(geodict_config.source_folder+'countrypositions.csv', 'rb'))
    country_positions = {}

    for row in reader:
        try:
            country_code = row[0]
            lat = row[1]
            lon = row[2]
        except:
            continue

        country_positions[country_code] = { 'lat': lat, 'lon': lon }
        
    reader = csv.reader(open(geodict_config.source_folder+'countrynames.csv', 'rb'))

    for row in reader:
        try:
            country_code = row[0]
            country_names = row[1]
        except:
            continue    

        country_names_list = country_names.split(' | ')
        
        lat = country_positions[country_code]['lat']
        lon = country_positions[country_code]['lon']
        
        for country_name in country_names_list:
        
            country_name = country_name.strip()
            
            last_word, index, skipped = pull_word_from_end(country_name, len(country_name)-1, False)

            cursor.execute("""
                INSERT IGNORE INTO countries (country, country_code, lat, lon, last_word)
                    values (%s, %s, %s, %s, %s)
                """,
                (country_name, country_code, lat, lon, last_word))
        

def load_regions(cursor):
    cursor.execute("""CREATE TABLE IF NOT EXISTS regions (
        region VARCHAR(64),
        PRIMARY KEY(region),
        region_code CHAR(4),
        country_code CHAR(2),
        lat FLOAT,
        lon FLOAT,
        last_word VARCHAR(32),
        INDEX(last_word(10)));
    """)

    reader = csv.reader(open(geodict_config.source_folder+'us_statepositions.csv', 'rb'))
    us_state_positions = {}

    for row in reader:
        try:
            region_code = row[0]
            lat = row[1]
            lon = row[2]
        except:
            continue

        us_state_positions[region_code] = { 'lat': lat, 'lon': lon }
    
    reader = csv.reader(open(geodict_config.source_folder+'us_statenames.csv', 'rb'))

    country_code = 'US'

    for row in reader:
        try:
            region_code = row[0]
            state_names = row[2]
        except:
            continue    

        state_names_list = state_names.split('|')
        
        lat = us_state_positions[region_code]['lat']
        lon = us_state_positions[region_code]['lon']
        
        for state_name in state_names_list:
    
            state_name = state_name.strip()
            
            last_word, index, skipped = pull_word_from_end(state_name, len(state_name)-1, False)
        
            cursor.execute("""
                INSERT IGNORE INTO regions (region, region_code, country_code, lat, lon, last_word)
                    values (%s, %s, %s, %s, %s, %s)
                """,
                (state_name, region_code, country_code, lat, lon, last_word))
    
cursor = get_database_connection()

wipe_and_init_database(cursor)

load_cities(cursor)
load_countries(cursor)
load_regions(cursor)


########NEW FILE########
