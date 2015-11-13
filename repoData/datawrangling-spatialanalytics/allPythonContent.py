__FILENAME__ = parse_geonames
#!/usr/bin/env python
# encoding: utf-8
"""
parse_geonames.py

$ grep PPL allCountries.txt | grep US > data/allUSCities.txt
$ cat data/allUSCities.txt | ./parse_geonames.py > output/standard_us_cities.txt
$ wc -l standard_us_cities.txt 
   25451 standard_us_cities.txt


state.txt from http://www.census.gov/geo/www/ansi/state.txt
-----------------------
STATE|STUSAB|STATE_NAME|STATENS
01|AL|Alabama|01779775
02|AK|Alaska|01785533
04|AZ|Arizona|01779777

allCountries.zip from http://download.geonames.org/export/dump/
The main 'geoname' table has the following fields :
---------------------------------------------------
1 geonameid         : integer id of record in geonames database
2 name              : name of geographical point (utf8) varchar(200)
5 latitude          : latitude in decimal degrees (wgs84)
6 longitude         : longitude in decimal degrees (wgs84)
9 country code      : ISO-3166 2-letter country code, 2 characters
10 cc2               : alternate country codes, comma separated, ISO-3166 2-letter country code, 60 characters
11 admin1 code       : fipscode (subject to change to iso code), see exceptions below, see file admin1Codes.txt for 
12 admin2 code       : code for the second administrative division, a county in the US, see file admin2Codes.txt; 
15 population        : bigint (4 byte int)

Created by Peter Skomoroch on 2010-03-25.
Copyright (c) 2010 Data Wrangling LLC. All rights reserved.
"""

import sys
import os
import csv
import time

infile = 'data/state.txt'
StateReader = csv.DictReader(open(infile, 'r'), delimiter='|')

state_fips ={}
state_name = {}
for data in StateReader:
  state_fips[data['STUSAB']]=data['STATE']
  state_name[data['STUSAB']]=data['STATE_NAME']
  
fips_corrections = {'5128581':'36061'}  
  

primary_key = {}

def main():
  for line in sys.stdin: 
    fields = line.strip().split('\t')
    for i, x in enumerate(fields):
      if len(x) == 0:
        fields[i] = ' '
    geonameid = fields[0]
    name = fields[1]
    latitude = fields[4]
    longitude = fields[5]
    country_code = fields[8]
    cc2 = fields[9]
    fipscode = fields[10]
    county = fields[11]
    population = fields[14]
    if int(population) > 0:
      # construct lower case "city,state abbrev."
      standard_name = name + ', ' + fipscode
      try:
        primary_key[standard_name]
      except:
        primary_key[standard_name] = 1  
        full_standard_name = name + ', ' + state_name[fipscode]
        # construct county fips code
        try:
          countyfips = fips_corrections[geonameid]
        except:  
          countyfips = state_fips[fipscode] + county          
        print '\t'.join([geonameid,name, latitude,longitude,country_code,
          cc2,fipscode,county,population, countyfips, standard_name.lower(), full_standard_name.lower()])


if __name__ == '__main__':
  main()


########NEW FILE########
__FILENAME__ = parse_turk_responses
#!/usr/bin/env python
# encoding: utf-8
"""
parse_turk_responses.py

Created by Peter Skomoroch on 2010-03-26.
Copyright (c) 2010 __MyCompanyName__. All rights reserved.
"""

import sys
import getopt
import os
import csv
from collections import defaultdict

help_message = '''
Usage: $ ./parse_turk_responses.py -f data/Batch_213923_result.csv > output/location_geo_mapping.txt
'''

# manual overrides for a few bad turk geonameid responses
override_file = 'data/overrides.csv'
OverrideReader = csv.DictReader(open(override_file, 'rU'), delimiter=',')
overrides ={}
for data in OverrideReader:
  overrides[data['location']]=data['geonameid']


class Usage(Exception):
  def __init__(self, msg):
    self.msg = msg


def main(argv=None):
  if argv is None:
    argv = sys.argv
  try:
    try:
      opts, args = getopt.getopt(argv[1:], "hf:v", ["help", "file="])
    except getopt.error, msg:
      raise Usage(msg)
  
    # option processing
    for option, value in opts:
      if option == "-v":
        verbose = True
      if option in ("-h", "--help"):
        raise Usage(help_message)
      if option in ("-f", "--file"):
        infile = value
        
    # outfile = open(infile.replace('result', 'parsed'), 'w')
    reader = csv.DictReader(open(infile, 'r'), delimiter=',', quotechar='"')
    
    # construct hash of geoids for each location
    # return geoid with max frequency
    
    geonameids = {}
    locations = []
    
    for data in reader:
      location = data['Input.location']      
      category = data['Answer.Q1Category']
      geonameid = data['Answer.Q2GeonameID']
      display_string = data['Input.display_string']
      time_zone = data['Input.time_zone']
      user_count = data['Input.user_count'] 
      comment = data['Answer.comment']
      if category == 'city':
        try:
          geonameids[location]
        except:   
          geonameids[location] = defaultdict(int)
        geonameids[location][geonameid] += 1
        
    geonameid_mapping={}    
    for loc in geonameids.keys():
      d = geonameids[loc]
      try:
        idnum = int(max(d, key=d.get))
        try: 
          geonameid_mapping[loc] = overrides[loc]
        except:  
          geonameid_mapping[loc] = str(idnum)
        
        output = ("\t".join([loc, str(idnum)])).encode('utf8')
        print output
      except:
        pass            

  
  except Usage, err:
    print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
    print >> sys.stderr, "\t for help use --help"
    return 2


if __name__ == "__main__":
  sys.exit(main())

########NEW FILE########
__FILENAME__ = state_blacklist
#!/usr/bin/env python
# encoding: utf-8
"""
city_blacklist.py

Exclude known larger entities like countries and states
 with potentially overlapping names

http://download.geonames.org/export/dump/countryInfo.txt

Created by Peter Skomoroch on 2010-03-28.
Copyright (c) 2010 Data Wrangling LLC. All rights reserved.
"""

import sys
import os
import csv

statefile = 'data/state.txt'
countryfile = 'data/countryInfo.txt'
outfile = open('output/blacklist_states.txt', 'w') 
StateReader = csv.DictReader(open(statefile, 'r'), delimiter='|')
CountryReader = csv.DictReader(open(countryfile, 'r'), delimiter='\t')

for data in CountryReader:
  country = (data['Country']).lower()
  if country not in []:
    print >> outfile, country


for data in StateReader:
  state = (data['STATE_NAME']).lower()
  if state not in ['district of columbia', 'new york']:
    print >> outfile, state

outfile.close()  

 



########NEW FILE########
__FILENAME__ = construct_wikiphrases
#!/usr/bin/env python
# encoding: utf-8
"""
construct_wikiphrases.py

The file s3://wher20demo/pages-20100316.txt.gz was constructed from
trendingtopics.org data as follows:

s3cmd get --config=/root/.s3cfg -r s3://trendingtopics/archive/20100316/pages/ pages
cat pages/* | sed 's/\x01/\t/g' > pages-20100316.txt
gzip pages-20100316.txt

For the Where 2.0 workshop, instead of using this map side dictionary, we will join to the following table in Pig
cut -f 1 page_lookups.txt | sed 's/\_/\ /g' > wikipedia_dictionary.txt

This script constructs a python dictionary for use in tokenizing tweets
using the Wikipedia page trend data

Created by Peter Skomoroch on 2010-03-11.
Copyright (c) 2010 Data Wrangling LLC. All rights reserved.
"""

import sys
import os
import csv
import cPickle as pickle

def main():
  wikiphrases = {}
  reader = csv.reader(open('page_lookups.txt', "rb"), delimiter='\t', quoting=csv.QUOTE_NONE)
  
  #phrase std_phrase  page_from page_to
  #Barack_Obama_"Progress"_poster  Barack Obama "Hope" poster      21129442        276142252
  for i, row in enumerate(reader):
    phrase, std_phrase = row[0], row[1]
    wikiphrases[phrase.lower().replace('_',' ')] = 1
    if i % 100000 == 0:
      print i
  
  print "Done, saving pickle"
  output = open('wikiphrases.pkl','wb')
  pickle.dump(wikiphrases, output, -1)
  output.close()

  print "test loading pickle"
  pkl_file = open('wikiphrases.pkl', 'rb')
  wikiphrases = pickle.load(pkl_file)
  
  print wikiphrases['gossip girl']
  print wikiphrases['obama']

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = tweet_tokenizer
#!/usr/bin/env python
# encoding: utf-8
"""
tweet_tokenizer.py

sample input format:
-- 31055 5074472 Wed Feb 10 04:59:42 +0000 2010  thanks for coming to pub quiz steph jess ali and stacey!
-- 06073 5391811 Wed Feb 10 04:50:26 +0000 2010  looooooooost!!

sample output format
-- i know	25025	4930956	2010-02-10	4
-- people	36061	5128581	2010-02-10	2
-- read	36061	5128581	2010-02-10	2


Created by Peter Skomoroch on 2010-03-29.
Copyright (c) 2010 Data Wrangling LLC. All rights reserved.
"""

import sys
import os
import zipimport
import cPickle as pickle
import rfc822
import time
import datetime
import re

# Pattern for fully-qualified URLs:
url_pattern = re.compile('''["']http://[^+]*?['"]''')

# load NLTK from distributed cache
importer = zipimport.zipimporter('nltkandyaml.mod')
yaml = importer.load_module('yaml')
nltk = importer.load_module('nltk')

# load stopword list
stopwords = open('stopwords.txt','r').readlines()
stopwords = [word.strip() for word in stopwords]

def gethour(timestamp):
  ''' convert timestamp of form: "Mon Mar 22 02:23:53 +0000 2010" '''
  rftime = rfc822.parsedate(timestamp)
  return str(rftime[3])

def getdate(timestamp):
  ''' convert timestamp of form: "Mon Mar 22 02:23:53 +0000 2010" '''
  rftime = rfc822.parsedate(timestamp)
  dateval = datetime.date(rftime[0], rftime[1], rftime[2])
  return dateval.isoformat()

def tokenize(text):
  tokenizer = nltk.tokenize.punkt.PunktWordTokenizer()
  tokens = tokenizer.tokenize(text)
  return tokens

def find_ngrams(seq, n):
  '''Use python list comprehension to generate ngrams'''
  ngram_list = [seq[i:i+n] for i in range(1+len(seq)-n)]
  return [' '.join(ngram) for ngram in ngram_list]
  
def emit_phrases(ngrams, fipscode, geonameid, date, hour):
  '''Validate ngrams against wikipedia phrases and emit to stdout'''
  for ngram in ngrams:
    try:
      #exclude numbers
      int(ngram)
    except:  
      #exclude special chars
      if len(ngram.strip()) > 1:
        print '\t'.join([ngram, fipscode, geonameid, date, hour])  

for line in sys.stdin:
  try:
    fipscode, geonameid, timestamp, tweet_text = line.strip().split('\t')
    date = getdate(timestamp)
    hour = gethour(timestamp)
    
    unigrams = tokenize(tweet_text)
    filtered_unigrams = list(set(unigrams) - set(stopwords))
    emit_phrases(filtered_unigrams, fipscode, geonameid, date, hour)  
     
    bigrams = find_ngrams(unigrams, 2)
    emit_phrases(bigrams, fipscode, geonameid, date, hour)  
    
    trigrams = find_ngrams(unigrams, 3)
    emit_phrases(trigrams, fipscode, geonameid, date, hour)
    
    fourgrams = find_ngrams(unigrams, 4)
    emit_phrases(fourgrams, fipscode, geonameid, date, hour)    
    
  except:
    pass


########NEW FILE########
__FILENAME__ = parse_stream
#!/usr/bin/env python
# encoding: utf-8
"""
parse_stream.py

Parses Twitter streaming API JSON tweets into un-nested tab delimited format

TODO: reverse geocode iPhone: lat lon pairs in location field to nearest city

ÜT: -23.639481,-46.610946	1
ÜT: 18.494521,-69.936517	1
ÜT: 34.096677,-118.100306	1
iPhone: 36.866623,-76.176041	1
ÜT: 40.654919,-73.746026	1
iPhone: 39.949680,-75.143860	1

6.41 percent have explicit lat lon...
0.69 percent have bounding boxes

21 percent have no location at all
Around 7 percent have explicit geo latlon or bounding box
Of remaining 72 percent, how many are real locations we can standardize?

Try exact match of lower case on city, state, country combinations.... see how far that gets us.

Handle unicode
# export LC_ALL=en_US.UTF-8; cat tweets.2010-03-21 | python ./parse_stream.py > locations.txt
# export LC_ALL=en_US.UTF-8; cat locations.txt | sort | uniq -c | sort -nr > ranked_locations.txt
# export LC_ALL=en_US.UTF-8; cat ranked_locations.txt | head -101 | tail -100 > top_100_twitter_locations.txt 
# file -bi top_100_twitter_locations.txt 
text/plain; charset=utf-8

Fields:
user_screen_name, tweet_id, tweet_created_at, tweet_text,
  user_id, user_name, user_description, user_profile_image_url, user_url,
  user_followers_count, user_friends_count, user_statuses_count, 
  user_location, user_lang, user_time_zone, place_id, place_name,
  place_full_name, place_type, place_country_code, place_bounding_box_coordinates
  

Example:
steve_arnett	10850933009	Mon Mar 22 02:23:53 +0000 2010	Other than issues with tickets & a long line, Steamfest 2010 was one of the most relaxing days of my life. Snagged 5 of 6 geocaches too!	17638525	Steve Arnett	Hi. I'm Steve. I'm a photographer in the bay area.	http://a3.twimg.com/profile_images/402082941/Copy_of_sf-steve-rachel-0055_normal.jpg	http://www.SteveArnett.com	137	171437	Pleasant Hill, CA	en	Pacific Time (US & Canada)	d70cebab5f549266	Pleasant Hill	Pleasant Hill, CA	city	US	[[[-122.104417, 37.925260000000002], [-122.049491, 37.925260000000002], [-122.049491, 37.982315999999997], [-122.104417, 37.982315999999997]]]


Created by Peter Skomoroch on 2010-03-21.
Copyright (c) 2010 Data Wrangling LLC. All rights reserved.
"""

import sys
import os
import simplejson

def clean(x):
  if x is None:
    return "NULL"
  if type(x) == type(' '):    
    x = x.replace('\t', ' ').replace('\n',' ')
  elif type(x) == type(1):
    x = str(x)
  return x.strip()

def main():
  for line in sys.stdin: 
    try:
      # tweet level info
      tweet_id = "NULL" #d70cebab5f549266
      tweet_created_at = "NULL" #"Mon Mar 22 02:23:53 +0000 2010",
      tweet_text = "NULL" # "hello world!"
      # user information
      # tweet['user']
      user_id = "NULL" #17638525,    
      user_screen_name = "NULL" #steve_arnett",
      user_name = "NULL" #:"Steve Arnett",    
      user_description = "NULL" #"Hi. I'm Steve. I'm a photographer in the bay area.",
      user_profile_image_url = "NULL" #:"http://a3.twimg.com/profile_images/402082941/Copy_of_sf-steve-rachel-0055_normal.jpg",
      user_url = "NULL" #:"http://www.SteveArnett.com",
      user_followers_count = "0" #137,
      user_friends_count = "0" #172,    
      user_statuses_count = "0" #1437,    
      user_geo_enabled = "NULL" #true,
      user_location = "NULL" #"Pleasant Hill, CA",    
      user_lang = "NULL" #en,
      user_time_zone = "NULL" #:"Pacific Time (US & Canada)",
      # place information available infrequently
      # tweet['place']
      place_id = "NULL"
      place_name = "NULL"
      place_full_name = "NULL"
      place_type = "NULL"
      place_country_code = "NULL"
      # tweet['place']['bounding_box']    
      place_bounding_box_coordinates = "NULL"    

      # try:
      tweet = simplejson.loads(line.strip())   

      if tweet.has_key('id'):
        tweet_id = str(tweet['id']) #d70cebab5f549266
        tweet_created_at = tweet['created_at'] #"Mon Mar 22 02:23:53 +0000 2010",
        tweet_text = clean(tweet['text']) # "hello world!"

      if tweet.has_key('user'):
        user = tweet['user']
        user_screen_name = user['screen_name']
        user_id = str(user['id'])  
        user_name = clean(user['name'])  
        if user.has_key('description'):  
          user_description = clean(user['description']) 
        if user.has_key('profile_image_url'):  
          user_profile_image_url = clean(user['profile_image_url'])
        if user.has_key('url'):    
          user_url = clean(user['url'])
        user_followers_count = clean(user['followers_count'])
        user_friends_count = clean(user['friends_count']) 
        user_statuses_count = clean(user['statuses_count'])
        if user.has_key('geo_enabled'):           
          user_geo_enabled = user['geo_enabled']
        if user.has_key('url'):       
          user_location = clean(user['location'])
        if user.has_key('lang'):  
          user_lang = clean(user['lang'])
        if user.has_key('time_zone'): 
          user_time_zone = clean(user['time_zone'])

      if tweet.has_key('place'): 
        place = tweet['place'] 
        if place is not None:
          place_id = str(place['id'])
          place_name = clean(place['name'])
          place_full_name = clean(place['full_name'])
          place_type = str(place['place_type'])
          place_country_code = str(place['country_code'])
          # tweet['place']['bounding_box']    
          place_bounding_box_coordinates = str(place['bounding_box']['coordinates'])      

      data = [user_screen_name, tweet_id, tweet_created_at, tweet_text,
        user_id, user_name, user_description, user_profile_image_url, user_url,
        user_followers_count, user_friends_count, user_statuses_count, 
        user_location, user_lang, user_time_zone, place_id, place_name,
        place_full_name, place_type, place_country_code, place_bounding_box_coordinates]

      data = [x.replace('\t', ' ') for x in data] 

      if len(data) == 21:
        output = ("\t".join(data)).replace('\n',' ').encode('utf8')
        print output      
      
    except:
      pass  
         



if __name__ == '__main__':
  main()


########NEW FILE########
__FILENAME__ = colorize_svg
#!/usr/bin/env pythonw
# encoding: utf-8
# requires BeautifulSoup
# based on Flowing Data blog post: 
# http://flowingdata.com/2009/11/12/how-to-make-a-us-county-thematic-map-using-free-tools/
#
# Usage:
# $ ./colorize_svg.py -f county_counts.txt > twitter_users.svg
#
# Expects a file of county_counts containing two columns:
# fipscode, count (integers)
#
# 51770   1
# 13089   1
# 54011   1
# 54039   3
# 12117   2
#
# Also require a baseline svg file in the same directory called counties.svg
#
 
import csv
from BeautifulSoup import BeautifulSoup, Tag
from math import log
import time 
import getopt
import os, sys

class Usage(Exception):
  def __init__(self, msg):
    self.msg = msg

def load_intensities(filename):
  intensities = {}
  reader = csv.reader(open(filename), delimiter="\t")
  for row in reader:
    try:
      fips = row[0]
      intensities[fips] = int(row[1])
    except:
      pass
  return intensities
  
def generate_heatmap(intensities):
  # Load the SVG map
  svg = open('counties.svg', 'r').read()
  # Load into Beautiful Soup
  soup = BeautifulSoup(svg, selfClosingTags=['defs','sodipodi:namedview'])
  # Find counties
  paths = soup.findAll('path')
  colors = ["#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B"]
  min_value = min(intensities.values())
  max_value = max(intensities.values())
  scalefactor = (len(colors)-1)/(log(max_value +1)-log(min_value +1))
  # County style
  path_style = 'font-size:12px;fill-rule:nonzero;stroke:#FFFFFF;stroke-opacity:1;stroke-width:0.1;stroke-miterlimit:4;stroke-dasharray:none;stroke-linecap:butt;marker-start:none;stroke-linejoin:bevel;fill:'
  # we will append this hover tooltip after each county path
  hover_text = '''<text id="popup-%s" x="%s" y="%s" font-size="10" fill="black" visibility="hidden">%s (%s)<set attributeName="visibility" from="hidden" to="visible" begin="%s.mouseover" end="%s.mouseout"/></text>'''
  for p in paths:
    if p['id'] not in ["State_Lines", "separator"]:
      try:
        count = intensities[p['id']]
      except: 
        count = 0
      x, y = (p['d'].split()[1]).split(',')
      # insert a new text tag for the county hover tooltip...
      p.parent.insert(0, Tag(soup, 'text', [("id", 'popup-'+p['id'])]))
      hover = soup.find("text", { "id" :  'popup-'+p['id'] })
      hover.insert(1, "%s (%s)" % (p['inkscape:label'], str(count)))
      # add attributes to that text tag...
      hover['x'] = 250
      hover['y'] = 20
      hover['font-size'] = "20"
      hover['fill'] = "black"
      hover['visibility'] = "hidden"
      hover.insert(0, Tag(soup, 'set', [("begin", p['id']+'.mouseover')]))
      set_tag = soup.find("set", { "begin" :  p['id']+'.mouseover' })
      set_tag['attributeName'] = "visibility" 
      set_tag['from'] = "hidden" 
      set_tag['to'] = "visible" 
      set_tag['end'] = p['id']+'.mouseout'
      color_class = min(int(scalefactor*log(count +1)), len(colors)-1)  
      # color_class = int((float(len(colors)-1) * float(count - min_value)) / float(max_value - min_value))
      # if count > 0:
      #   print color_class
      color = colors[color_class]
      p['style'] = path_style + color    
  print soup.prettify()

def main(argv=None):
  if argv is None:
    argv = sys.argv
  try:
    try:
      opts, args = getopt.getopt(argv[1:], "hf:v", ["help", "filename="])
    except getopt.error, msg:
      raise Usage(msg)

    # option processing
    for option, value in opts:
      if option == "-v":
        verbose = True
      if option in ("-h", "--help"):
        raise Usage(help_message)
      if option in ("-f", "--filename"):
        filename = value
  
    # main processing
    intensities = load_intensities(filename)
    generate_heatmap(intensities)    

  except Usage, err:
    print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
    print >> sys.stderr, "\t for help use --help"
    return 2


if __name__ == "__main__":
  sys.exit(main())



########NEW FILE########
