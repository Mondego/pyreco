__FILENAME__ = parse
#! env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import logging
import os
import re

# TODO look for a better way to enforce it
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# The "APH" airport code corresponds to the Jacksonville International
# Airport in Jacksonville, FL, United Sates.

# Limit the entries to the code (e.g. 'JAX' ) and the airport name +
# 'code' (e.g. 'Jacksonville International Airport code'). The latter
# being a redirect to the former. We could also include one with the
# word 'airport' removed (e.g. 'Jacksonville International code').
# Having the result for the city name would cover too many searches
# that aren't looking for the airport code.

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

OUTPUT_FILE = 'output.txt'
INDEXES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
WIKIPEDIA_URL = 'https://wikipedia.org'
WIKIPEDIA_LIST_URL = 'https://en.wikipedia.org/wiki/List_of_airports_by_IATA_code:_'

def append_period(text):
	""" Append a period at the end of the sentence"""
	if text[-1] == '\"':
		return text[0:-1]+'.\"'
	return text

def getFields(name,linetype,abstract=''):
	return [name,	  # $unique_name
			linetype, # $type 
			'',	 # $redirect
			'',	 # $otheruses
			'',	 # $categories
			'',	 # $references
			'',	 # $see_also
			'',	 # $further_reading
			'',	 # $external_links
			'',	 # $disambiguation
			'',	 # images
			abstract,	 # abstract
			''] # source link

class Airport(object):
	iata_abstract_format	 = 'The "{0}" IATA airport code corresponds to {2} in {3}'
	icao_abstract_format	 = 'The "{1}" ICAO airport code corresponds to {2} in {3} and the IATA code is "{0}"'
	name_abstract_format	 = 'The IATA code for the {2} is "{0}"'
	location_abstract_format = 'The IATA code for the {2} near {3} is "{0}"'
	abstract_icao_format	 = ' and the ICAO code is "{1}"'

	""" Contains informations about an Airport"""
	def __init__(self, name, iata, icao, location, index_letter):
		self.name = name
		self.iata = iata
		self.icao = icao
		self.location = location
		self._index_letter = index_letter
		self.international_airport_name = None
		self.name_with_airport = None 

		self.abstract_icao_part = ''
		if self.icao != '':
			self.abstract_icao_part = self._format(Airport.abstract_icao_format)

		# Put name with airport and international airport
		self.name_with_airport = self.name
		if self.name_with_airport.find('Airport') < 0:
			self.name_with_airport += ' Airport'

		index = self.name_with_airport.rfind(' International Airport')
		if index > 0:
			self.international_airport_name = self.name_with_airport

		self.airport_location_name = None
		if self.location != None:
			location_names = self.location.split(',')
			if len(location_names) > 0:
				self.airport_location_name = location_names[0]+' Airport'
				if self.airport_location_name == self.name:
					self.airport_location_name = None

		# remove redundancy in airports/location names
		if self.name_with_airport != None and self.name_with_airport.find('airports in ') != -1:
			self.name_with_airport = 'airports'

	def _format(self,string):
		return string.format(self.iata,self.icao,self.name_with_airport,self.location)

	def add_iata(self,output):
		abstract = self._format(Airport.iata_abstract_format)+self.abstract_icao_part
		if self.iata != None and len(self.iata) != 0:
			fields = self._getFields(self.iata,'A',append_period(abstract))
			output.append('%s' % ('\t'.join(fields)))

	def add_icao(self,output):
		abstract = self._format(Airport.icao_abstract_format)
		if self.icao != None and len(self.icao) != 0:
			fields = self._getFields(self.icao,'A',append_period(abstract))
			output.append('%s' % ('\t'.join(fields)))

	def add_name(self,output):
		abstract = self._format(Airport.name_abstract_format)+self.abstract_icao_part
		if self.name_with_airport != None and len(self.name_with_airport) != "":
			fields = self._getFields(self.name_with_airport,'A',append_period(abstract))
			output.append('%s' % ('\t'.join(fields)))

	def add_location(self,output):
		abstract = self._format(Airport.location_abstract_format)+self.abstract_icao_part
		if self.airport_location_name != None:
			fields = self._getFields(self.airport_location_name,'A',append_period(abstract))
			output.append('%s' % ('\t'.join(fields)))

	def add_redirects(self,output,withRedirect):
		if self.international_airport_name == None:
			return
		fields	   = self._getFields(self.international_airport_name[0:-len("Airport")-1],'R')
		fields[2]  = self.international_airport_name
		fields[12] = ''
		output.append('%s' % ('\t'.join(fields)))

		if withRedirect:
			fields = self._getFields(self.name_with_airport,'R')
			fields[2] = self.iata
			fields[12] = ''
			output.append('%s' % ('\t'.join(fields)))

	def _getFields(self,name,linetype,abstract=''):
		fields = getFields(name,linetype,abstract)
		fields[12] = WIKIPEDIA_LIST_URL+self._index_letter
		return fields
	
	def __str__(self):
		return self.name_with_airport+';'+self.iata+';'+self.icao+';'+self.location+';'+self._index_letter


class Parser(object):
	""" Parses a HTML file to get all the airports codes """
	def __init__(self, index_letter):
		self.soup = BeautifulSoup(open('download/'+index_letter), "html5lib", from_encoding='utf-8')
		self.index_letter = index_letter

	def get_airports(self):
		self.airports = []
		table = self.soup.find_all('table')[1]
		line_number = 0

		for row in table.find_all('tr')[1::]:
			line_number+=1
			data = row.find_all('td')
			if len(data) != 4: # partial table heading
				continue

			# check if data[3] has no link look in 
			airport_link = data[2].find('a')
			if airport_link == None:
				airport_link = data[3].find('a')
			if airport_link != None:
				airport_name = airport_link.getText()

			#logger.debug(data)
			self.airports.append(
				Airport(
					airport_name.strip(),
					data[0].getText().strip(),	# IATA
					data[1].getText().strip(),	# ICAO
					data[3].getText().strip(),
					self.index_letter)) # Name

def addDisambituation(value,airport,disambiguations):
	if value != None and value in disambiguations:
		if not any(map(lambda x: x.iata == airport.iata,disambiguations[value])):
			disambiguations[value].append(airport)
	else:
		disambiguations[value] = [airport]

def findAndMarkDisambiguations(airports):
	disambiguations = {}
	for airport in airports:
		addDisambituation(airport.name_with_airport,airport,disambiguations)
		addDisambituation(airport.airport_location_name,airport,disambiguations)
		addDisambituation(airport.international_airport_name,airport,disambiguations)

	for airport in airports:
		if airport.icao != None and len(airport.icao) > 0 and airport.icao in disambiguations:
			disambiguations[airport.icao].append(airport)
		else:
			disambiguations[airport.icao] = [airport]
	return disambiguations

def print_disambiguation((key,airports)):
	fields = getFields(key,'D') 
	for airport in airports:
		string = '*';
		string += '[['+airport.iata+']] '
		fields[9] += string+airport.name+' in '+airport.location+'\\n'
	ret = '%s' % ('\t'.join(fields))+'\n'
	if re.match('.*Airport',key):
		fields = getFields(key,'R')
		fields[2] = fields[0]
		fields[12] = ''
		fields[0] = fields[0]+'s'
		ret = ret + '%s' % ('\t'.join(fields))+'\n'
	return ret

if __name__ == '__main__':
	with open(OUTPUT_FILE, 'w') as output:
		airports = []

		# parse all
		for i in INDEXES:
			parser = Parser(i)
			logger.debug("Index: "+i)
			parser.get_airports()
			airports += parser.airports

		disambiguations = findAndMarkDisambiguations(airports)

		# print all the rest
		for airport in airports:
			strings = []
			airport.add_iata(strings)
			if len(disambiguations[airport.icao]) == 1:
				airport.add_icao(strings)
			if airport.international_airport_name != None and len(disambiguations[airport.international_airport_name]) == 1:
				airport.add_redirects(strings,not airport.name_with_airport in disambiguations) 
			if len(disambiguations[airport.name_with_airport]) == 1:
				airport.add_name(strings)
			if len(disambiguations[airport.airport_location_name]) == 1:
				airport.add_location(strings)
			output.write('\n'.join(strings)+'\n')

		# print disambiguations
		map(output.write,map(print_disambiguation,
				filter(lambda (x,y): len(y) > 1,
					disambiguations.items())))


########NEW FILE########
__FILENAME__ = parse
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import logging
import os
import re
from unidecode import unidecode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def replace_all(text, terms):
    """ Replaces all terms contained
    in a dict """
    for _from, _to in terms.items():
        text = text.replace(_from, _to)
    return text


class Package(object):
    """ Contains informations about an Arch package"""
    def __init__(self, name, info, reference, arch):
        self.name = name
        
        info = unidecode(info)

        if info[1].islower() or info[1] == ' ':
            info = info[0].lower() + info[1:]

        self.info = "Package description: %s." % (info)
        self.reference = reference
        self.arch = arch
        
    def __str__(self):
        fields = [
                self.name,              # $page
                '',                     # $namespace
                self.reference,         # $url
                self.info,              # $description
                '',                     # $synopsis (code)
                '',                     # $details
                'A',                    # $type
                ''                      # $lang
                ]

        output = '%s' % ('\t'.join(fields))

        return output


class Parser(object):
    """ Parses a HTML file to get
    all packages from it"""

    ARCHLINUX_URL = 'https://www.archlinux.org'
    
    def __init__(self, input='download/index.html?limit=all'):
        self.soup = BeautifulSoup(open(input), from_encoding='utf-8')

    def get_packages(self):
        """ """
        self.packages = []

        table = self.soup.find('table')

        for row in table.find_all('tr')[1::]:
            data = row.find_all('td')

            name = data[2].a.getText()
            reference = self.ARCHLINUX_URL + data[2].a['href']
            info = data[4].getText()
            arch = data[0].getText()

            package = Package(name, info, reference, arch)
            self.packages.append(package)

            # removing duplicates
            if len(self.packages) >= 2:
                if self.packages[-1].name == self.packages[-2].name: 
                    del self.packages[-1]

            #logger.info('Parsed package %s' % name)
       
if __name__ == '__main__':
    parser = Parser()
    parser.get_packages()

    with open('output.txt', 'w') as output:
        for package in parser.packages:
            output.write(package.__str__().encode('utf-8') + '\n')
            #logger.info('Package added to output: %s' % package.name)

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python2
import csv

reader = csv.reader(open("download/kjv.txt", "rb"), delimiter="\t")
output = open("output.txt", "wb")

abv = {
"genesis": "Gen", "exodus": "Exd", "leviticus": "Lev", "numbers": "Num", "deuteronomy": "Deu", "joshua": "Jos", "judges": "Jdg", "ruth": "Rth", "1 samuel": "1Sa", "2 samuel": "2Sa", "1 kings": "1Ki", "2 kings": "2Ki", "1 chronicles": "1Ch", "2 chronicles": "2Ch", "ezra": "Ezr", "nehemiah": "Neh", "esther": "Est", "job": "Job", "psalms": "Psa", "proverbs": "Pro", "ecclesiastes": "Ecc", "song of solomon": "Sgs", "isaiah": "Isa", "jeremiah": "Jer", "lamentations": "Lam", "ezekiel": "Eze", "daniel": "Dan", "hosea": "Hsa", "joel": "Joe", "amos": "Amo", "obadiah": "Oba", "jonah": "Jon", "micah": "Mic", "nahum": "Nah", "habakkuk": "Hab", "zephaniah": "Zep", "haggai": "Hag", "zechariah": "Zec", "malachi": "Mal", "matthew": "Mat", "mark": "Mar", "luke": "Luk", "john": "Jhn", "acts": "Act", "romans": "Rom", "1 corinthians": "1Cr", "2 corinthians": "2Cr", "galatians": "Gal", "ephesians": "Eph", "philippians": "Phl", "colossians": "Col", "1 thessalonians": "1Th", "2 thessalonians": "2Th", "1 timothy": "1Ti", "2 timothy": "2Ti", "titus": "Tts", "philemon": "Phm", "hebrews": "Hbr", "james": "Jam", "1 peter": "1Pe", "2 peter": "2Pe", "1 john": "1Jo", "2 john": "2Jo", "3 john": "3Jo", "jude": "Jud", "revelation": "Rev"

}

def newStr(name, theType, redirect, category, verse, url):
    """ Update string formatting.
    """
    ddgStr = [      name,                   # name
                    theType,                # type
                    redirect,               # redirect
                    "",                     # otheruses
                    category,               # categories
                    "",                     # references
                    "",                     # see_also
                    "",                     # further_reading
                    "",                     # external_links
                    "",                     # disambiguation
                    "",                     # images
                    verse,                  # abstract
                    url+"\n"                # source_url
             ]
    return "%s" % ("\t".join(ddgStr))

for row in reader:
     book = row[0] # e.g. Genesis
     chapter = "{0}:{1}".format(row[1],row[2]) # e.g. 1:23
     name = "{0} {1}".format(book, chapter)
     verse = row[3]
     url = "http://blb.org/search/preSearch.cfm?Criteria={0}+{1}".format(book,chapter)

     chapterSpace = "{0} {1}".format(row[1],row[2]) # e.g. 1 23
     nameSpace = "{0} {1}".format(book, chapterSpace)

     temp = newStr(name, "A", "", "Bible Verses\\n", verse, url) + \
            newStr(nameSpace, "R", name, "", "", "")

     output.write(temp)

     if book != "Job":
          abvBook = abv[book.lower()] # e.g. Gen
          abvName = "{0} {1}".format(abvBook, chapter)
          abvUrl = "http://blb.org/search/preSearch.cfm?Criteria={0}".format(abvName)
          abvNameSpace = "{0} {1}".format(abvBook, chapterSpace)
          temp = newStr(abvName, "R", name, "", "", "") + \
                 newStr(abvNameSpace, "R", name, "", "", "")

          output.write(temp)

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python2

from BeautifulSoup import BeautifulSoup, NavigableString
import urllib
import string
import re


class Entry(object):
    def __init__(self, name, value, description, url):
        self.name = name
        self.value = value
        self.description = description
        self.url = url

    def __str__(self):
        fields = [
                self.name,              # title
                'A',                    # type
                '',                     # redirect
                '',                     # otheruses
                '',                     # categories
                '',                     # references
                '',                     # see_also
                '',                     # further_reading
                '',                     # external_links
                '',                     # disambiguation
                '',                     # images
                self.description,       # abstract
                self.url                # source_url
                ]
        return '%s' % ('\t'.join(fields))


class Parser(object):
    def __init__(self, input='download/About:config_entries'):
        self.soup = BeautifulSoup(open(input))
        # Requires trailing / for relative link replacement
        self.baseURL = "http://kb.mozillazine.org/"

    def findEntries(self):
        self.entries = []
        headers = map(lambda x: x.string, self.soup.findAll('h1')[2:])
        table = self.soup.findAll('div', id="bodyContent")[0]
        for table in table.findAll('table'):
            header = True
            for tr in table.findAll('tr'):
                if header:
                    header = False
                    continue
                i = 0
                for th in tr.findAll('td'):
                    description = ''
                    if i == 0:
                        name = ''.join(th.b.findAll(text=True)).replace(' ','')
                        anchor = string.capitalize(urllib.quote(name.split('.')[0])) + "."
                        if anchor in headers:
                            url = self.baseURL + 'About:config_entries#' + anchor
                        else:
                            url = self.baseURL + 'About:config_entries'
                    elif i == 1:
                        value = th.text
                    elif i == 2:
                        if value:
                            article = 'a'
                            if value[0] == 'I': article += 'n'
                            optionType = "it accepts " + article + " " + value.lower() + "."
                        synopsis = '"' + name + '"'  + ' is a configuration option ' \
                                'for the Firefox web browser; ' + optionType + "<br>"
                        for tag in th.findAll('br'):
                            tag.insert(0, NavigableString("\n"))
                        description = ''.join(th.findAll(text=True))
                        description = description.rstrip().replace('\n', '<br>').strip()
                        expandedURL = 'href="' + self.baseURL
                        description = description.replace('href="/', expandedURL)
                        description = re.sub('<\s*b\s*>', '<i>', description)
                        description = re.sub('<\s*/\s*b\s*>', '</i>', description)
                        description = '<blockquote>' + description + '</blockquote>'
                        description = synopsis + description
                        i = -1
                        self.entries.append(Entry(name, value, description.strip(), url))
                    i += 1


if __name__ == "__main__":
    parser = Parser()
    parser.findEntries()
    with open('output.txt', 'w') as file:
        for entry in parser.entries:
            file.write(entry.__str__().encode('UTF-8') + '\n')

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv, logging, os, glob


class HelloWorldItem:
  def __init__(self, language, filename, source):
    self.language = language
    self.filename = filename
    self.source = source

  def __str__(self):
    # a few problems:
     # 1. self.source may contain tabs
     # 2. should type or lang be non-empty?
    fields = [ "hello world (%s)" % self.language,
               "", # namespace
               "https://github.com/leachim6/hello-world",
               "Hello World in %s (%s)" % (self.language, self.filename),
               self.source, # synposis (code)
               "", # details
               "", # type
               "", # lang
             ]

    output = "%s\n" % ("\t".join(fields))
#    fields[0] = '%s hello world' % self.language
#    output += "%s\n" % ("\t".join(fields))
#    fields[0] = 'hello world in %s' % self.language
#    output += "%s\n" % ("\t".join(fields))
    return output


if __name__ == "__main__":
    # setup logger
    logging.basicConfig(level=logging.INFO,format="%(message)s")
    logger = logging.getLogger()
    
    # dump config items
    count = 0
    with open("output.txt", "wt") as output_file:
        for filepath in glob.glob('download/*/*'):
            _,filename = os.path.split(filepath)
            # ignore some "languages"
            if filename not in ['ls.ls', 'readlink.readlink', 'piet.png']:
                # fix brainfuck name
                if filename == 'brainf*ck.bf':
                    filename = 'brainfuck.bf'

                language,_ = os.path.splitext(filename)
                with open(filepath, 'r') as f:
                    source = f.read()
                source = source.replace('\\n', '~~~n')
                source = source.replace('\n', '\\n')
                source = source.replace('~~~n', '\\\\n')
                source = source.replace('\t', '\\t')
                    
                item = HelloWorldItem(language, filename, source)
                if count % 10 == 0:
                    logger.info("%d languages processed" % count )

                count += 1
                output_file.write(str(item))
    logger.info("Parsed %d domain rankings successfully" % count)


########NEW FILE########
__FILENAME__ = parse
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import logging
import cgi
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def replace_all(text, terms):
    """ Replaces all terms contained
    in a dict """
    for _from, _to in terms.items():
        text = text.replace(_from, _to)
    return text


class Tag(object):
    """ Contains informations about
    a HTML tag """
    def __init__(self, name, info, reference, example):
        self.name = name
        self.info = info
        self.reference = reference
        
        # Remove excess padding around synopsis
        self.example = re.sub('^\\n', '', example)
        self.example = re.sub('\\n$', '', self.example)

        self.example = replace_all(self.example, {'\n': '\\n',
                                             '\t': '\\t',
                                             '\r': ''})

    def __str__(self):
        fields = [
                self.name,              # $page
                '',                     # $namespace
                self.reference,         # $url
                self.info,              # $description
                self.example,  # $synopsis (code)
                '',                     # $details
                'A',                     # $type
                ''                      # $lang
                ]

        output = '%s' % ('\t'.join(fields))

        return output


class Parser(object):
    """ Parses a HTML file to get
    all tag informations inside it """
    def __init__(self, input='download/index.html'):
        self.soup = BeautifulSoup(open(input), from_encoding='utf-8')

    def get_tags(self):
        """ Gets all tags defined in 'dl' tags """
        self.tags = []
        for tag in self.soup.find_all('dl'):
            name = tag.dt.contents[0]

            # getting info about tag
            info = ''
            for p in tag.dd.find_all('p'):
                info += p.getText() + ' '

            # getting reference link and code snippet
            a_tags = tag.dd.find_all('a')
            example_id = a_tags[1]['href'].replace('#', '')  # code snippet
            example = self.soup.find('div', {'id': example_id}).getText()

            # url reference (from HTML5Doctor if exists)
            reference = ''
            try:
                reference = tag.dt.span.a['href']  # url for HTML5Doctor
            except:
                reference = a_tags[0]['href']  # url for W3C

            reference = 'http://html5doctor.com/element-index/#' + name
            new_tag = Tag(name, info, reference, example)
            self.tags.append(new_tag)
            logger.info('Tag parsed: %s' % new_tag.name)


if __name__ == '__main__':
    parser = Parser()
    parser.get_tags()

    with open('output.txt', 'w') as file:
        for tag in parser.tags:
            file.write(tag.__str__().encode('utf-8') + '\n')
            logger.info('Tag added to output: %s' % tag.name)

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Released under the GPL v2 license 
# https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

import lxml.etree, lxml.html
import re

from unidecode import unidecode

url = "http://www.iso.org/iso/list-en1-semic-3.txt"
title = "ISO 3166 Country Codes"
article_type = "A"

outp = "output.txt"
inp = "download/raw.data"

#Open input file
input_file = open( inp, "r" )

#Read and throw out first line
input_file.readline()

output_file = open( outp, "w")

#Loop thru the remainder of the file, format each line
#and print it to the output file.
for line in input_file.readlines() :
	line = line.strip();
	pair = line.split( ';' );
	if len( pair ) < 2 :
		continue;

        pair[0] = unidecode(pair[0])
        
        abstract = "\"" + pair[1] + "\" is the ISO 3166 country code for \"" + pair[0].title() + ".\""
	
        output_file.write( "\t".join([
            pair[1],        # Title
            article_type,   # Type
            '',             # Redirect
            '',             # Other uses
            '',             # Categories
            '',             # References
            '',             # See also
            '',             # Further reading
            '',             # External links
            '',             # Disambiguation
            '',             # Images
            abstract,       # Abstract
            url,            # Source URL
            ] ))

        output_file.write( "\n" );

input_file.close();
output_file.close();


########NEW FILE########
__FILENAME__ = parse
import os
import re
from BeautifulSoup import BeautifulSoup
import sys
import string


def findindex(haystack, needle):
  count = 0
  for line in haystack:
    if needle in line:
      return count
    count += 1


def getsection(fd, start, end):
  html = ''
  for i in fd[start:end]:
    html = "%s\r\n%s" % (html, i)
  return html


def getall(fd):
  html = ''
  for i in fd:
    html = "%s\r\n%s" % (html, i)
  return html


r1 = re.compile(r'<.*?>', re.DOTALL)
findtr = re.compile(r'<TR .*?>.*?</TR>', re.DOTALL)
findtd = re.compile(r'<TD>.*?</TD>', re.DOTALL)
findtable = re.compile(r'<TABLE .*?</TABLE>', re.DOTALL)
findp = re.compile(r'<P>.*?<P>', re.DOTALL)
findpre = re.compile(r'<PRE>.*?</PRE>', re.DOTALL)
findh2 = re.compile(r'<H2>.*?</H2>', re.DOTALL)
findh3 = re.compile(r'<H3>.*?</H3>', re.DOTALL)
findcode = re.compile(r'<code>.*?</code>', re.DOTALL)
findcodeupper = re.compile(r'<CODE>.*?</CODE>', re.DOTALL)
findmethoddetail = re.compile(r'<A NAME.*?<HR>', re.DOTALL)
finda = re.compile(r'<A NAME.*?>', re.DOTALL)
findb = re.compile(r'<B>.*?</B>', re.DOTALL)
findddtop = re.compile(r'<DD.*?<P>', re.DOTALL)
findinherit = re.compile(r'<B>Methods inherited from.*?</TABLE>',
                         re.DOTALL)
findopenclosetags = re.compile(r'<.*?>|</.*?>', re.DOTALL)
spaces = re.compile(r'\s+', re.DOTALL)

# java javax and org


#get all the files here
dirList = []


dir = "./docs/java/en/api/java/"

for (path, dirs, files) in os.walk(dir):
  if 'class-use' not in path:
    for f in files:
      dirList.append("%s/%s" % (path, f))

dir = "./docs/java/en/api/javax/"

for (path, dirs, files) in os.walk(dir):
  if 'class-use' not in path:
    for f in files:
      dirList.append("%s/%s" % (path, f))


first = True

for fname in dirList:
  fd = []

  #if fname == 'XmlAnyElement.html':
  #if fname  == 'RandomAccess.html': # interface
  if fname.endswith('.html') and 'package-' not in fname \
        and 'doc-files' not in fname:
    for line in open("%s" % fname):
      line = line.strip().replace("'", '')
      line = ''.join(filter(lambda x: x in string.printable, line))
      fd.append(line)

    start = findindex(fd, "START OF CLASS DATA")
    consum = findindex(fd, "CONSTRUCTOR SUMMARY")
    methsum = findindex(fd, "METHOD SUMMARY")
    condet = findindex(fd, "CONSTRUCTOR DETAIL")
    methdet = findindex(fd, "METHOD DETAIL")
    end = findindex(fd, "END OF CLASS DATA")

    #finds the name and namespace
    np = findh2.findall(getall(fd))[0]
    np = np.split('<BR>')
    namespace = r1.sub('', np[0]).strip()
    classtype = r1.sub('', np[1]).strip()

    #if its an interface skip it
    if 'interface' in classtype.lower():
      continue

    #finds the description which is the large text at the beginning
    desc = findp.findall(getall(fd))[0]

    # print the object

    name = fname.split('/')[-1].replace('.html', '')
    url = "http://download.oracle.com/javase/6/docs/%s" \
        % (fname.replace('./docs/java/en/', ''))
    description = spaces.sub(' ', findopenclosetags.sub('', desc).strip())

    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (name, namespace, url,
                                              description, '', '',
                                              'java', 'en')

    #finds all inherited methods
    for i in findinherit.findall(getall(fd)):
      description = spaces.sub(' ',
                               findopenclosetags.sub('', 
                                                     findb.findall(i)[0].replace('Methods','Method').replace('<B>','').replace('</B>','')
                                                     )
                               )
      #print detail
      for j in findcodeupper.findall(i)[0].replace('<CODE>', '').replace('</CODE>', '').split('>, '):
        #synopsis = j.strip().replace('</A','</A>').replace('>>','>')
        synopsis = ''
        methodname =  r1.sub('', j).replace('</A', '').strip()
        url = 'http://download.oracle.com/javase/6/docs/%s#%s' % ( fname.replace('./docs/java/en/',''), methodname)
        namespaceinherited = "%s.%s" % (namespace, name)

        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (methodname,
                                                  namespaceinherited, url,
                                                  description, synopsis, '', 
                                                  'java', 'en')


    #finds all methoddetailinfo
    for meth in findmethoddetail.findall("%s<HR>" % (findtable.sub('', getsection(fd, methdet, end)).replace('<A NAME="method_detail"><!-- --></A>', ''))):
      try:
        methodname = r1.sub('', findh3.findall(meth)[0]).strip()
        methodurl = finda.findall(meth)[0]
        methodurl = methodurl.replace('<A NAME="', '').replace('">', '')
        url = 'http://download.oracle.com/javase/6/docs/%s#%s'%(fname.replace('./docs/java/en/', ''),methodurl)
        synopsis = findopenclosetags.sub('',findpre.findall(meth)[0].replace('<PRE>', '').replace('</PRE>', '').replace("\r\n", '').strip())
        description = spaces.sub(' ',findopenclosetags.sub('', findddtop.findall(meth)[0].replace('<DD>', '').replace('<P>', '')))
        namespaceinherited = "%s.%s" % (namespace, name)

        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methodname, namespaceinherited,
                                                url, description, synopsis,
                                                '','java','en')
      except:
        pass

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# We do nothing here because the fetch.sh is actually grabbing something in the correct format.
########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, os, urllib.parse
import lxml.etree

# Python code used to generate the site is freely available (http://cateee.net/sources/lkddb/)
# but it's a lot more maintainable to scrape their site than to hack around their kernel parsing code


class KernelConfigItem:

  def __init__(self, url, name, shorthelp, help, type, depends, defined, kernelversions, modules):
    self.url = url
    self.name = name
    self.shorthelp = shorthelp
    self.help = help
    self.type = type
    self.depends = depends
    self.defined = defined
    self.kernelversions = kernelversions
    self.modules = modules

  def __str__(self):
    redirect = "%s\tR\t%s\t\t\t\t\t\t\t\t\t\t" % (self.name.split("_", 1)[1], self.name)
    if self.help:
      snippet = self.help
    """
    if self.type:
      snippet = "%s\\n- type: %s" % (snippet, self.type)
    if self.depends:
      snippet = "%s\\n- depends on the following option(s): %s" % (snippet, self.depends)
    if self.defined:
      snippet = "%s\\n- defined in: %s" % (snippet, self.defined)
    if self.kernelversions:
      snippet = "%s\\n- available in the following Linux version(s): %s" % (snippet, self.kernelversions)
    if self.modules:
      snippet = "%s\\n- will build the following module(s): %s" % (snippet, self.modules)
    """
    fields = [self.name,
              "A",
              "",
              "",
              "",
              "",
              "",
              "",
              "[http://cateee.net/lkddb/web-lkddb/ Linux Kernel Driver DataBase]",
              "",
              "",
              snippet,
              self.url]
    return "%s\n%s\n" % (redirect, "\t".join(fields))


class LkddbParser:

  BASE_URL = "http://cateee.net/lkddb/web-lkddb/"
  INDEX_URL = "%sindex.html" % (BASE_URL)
  KO_REASON = (MISSING_CONTENT, INVALID_STRUCTURE, INCOMPLETE_PAGE, INVALID_CHAR, UNKNOWN) = range(5)
  KO_REASON_STR = ("missing content", "invalid document structure", "incomplete page",  "invalid char", "unknown")

  def __init__(self):
    self.parser = lxml.etree.HTMLParser()
    self.ok_count = 0
    self.ko_count = {k : 0 for k in __class__.KO_REASON}

  def __iter__(self):
    # get main page
    main_page = self.getPageFromCache(__class__.INDEX_URL)
    self.main_page_xml = lxml.etree.XML(main_page, self.parser)
    return self.__next__()

  def __next__(self):
    logger = logging.getLogger()

    # get subpages
    for sub_page_tag in self.main_page_xml.iterfind("body/ul/li/a"):
      sub_page_url = "%s%s" % (self.BASE_URL, sub_page_tag.attrib["href"])
      sub_page = self.getPageFromCache(sub_page_url)
      sub_page_xml = lxml.etree.XML(sub_page, self.parser)

      # get config item page
      for config_page_tag in sub_page_xml.iterfind("body/ul/li/ul/li/a"):
        config_page_url = "%s%s" % (self.BASE_URL, config_page_tag.attrib["href"])
        config_page = self.getPageFromCache(config_page_url)
        config_page_xml = lxml.etree.XML(config_page, self.parser)

        try:
          # has this option several descriptions?
          multiple = len(config_page_xml.findall("body/div/ul")) > 3

          # get name of config option
          name = config_page_xml.findtext("body/div/h1")
          if ":" in name:
            name = name.split(":", 1)[0]

          # get full help
          help_lines = []
          for help_line in config_page_xml.xpath("body/div/*[self::h2 or self::h3][text()='Help text']/following-sibling::*"):
            if help_line.tag != "p":
              break
            help_lines.append(lxml.etree.tostring(help_line, encoding="unicode", method="text").replace("\n", " ").strip())
          help = "<i>Help text:</i> " + " ".join(help_lines)
          if (not help) or (help == "(none)"):
            self.logParsingError(__class__.MISSING_CONTENT, config_page_url)
            continue

          # detect erroneous pages
          pre_list_msg_xml = config_page_xml.xpath("body/div/h2[text()='General informations']/following::p")
          if not config_page_xml.xpath("body/div/h2[text()='General informations']/following::p"):
            # for some pages lxml fail to get the right xml structure
            # eg: http://cateee.net/lkddb/web-lkddb/M25PXX_USE_FAST_READ.html (xpath query "body/div/h2[text()='General informations']" gives nothing, but "body//h2[text()='General informations']" does)
            self.logParsingError(__class__.INVALID_STRUCTURE, config_page_url)
            continue
          pre_list_msg_xml = pre_list_msg_xml[0]
          pre_list_msg = lxml.etree.tostring(pre_list_msg_xml, encoding="unicode", method="text").strip()
          if pre_list_msg.endswith("error: definition not found!"):
            # some pages are incomplete, eg: http://cateee.net/lkddb/web-lkddb/ATHEROS_AR71XX.html
            self.logParsingError(__class__.INCOMPLETE_PAGE, config_page_url)
            continue

          # get other option info
          if multiple:
            li_list = list(x.text for x in config_page_xml.xpath("body/div/h2[1]/following::ul/li") if x.text)
          else:
            li_list = list(x.text for x in config_page_xml.xpath("body/div/h2[text()='General informations']/following::ul/li") if x.text)
          shorthelp, type, depends, defined, kernelversions, modules = None, None, None, None, None, None
          for li in li_list:
            if li.startswith("prompt: "):
              shorthelp = li[8:]
            elif li.startswith("type: "):
              type = li[6:]
            elif li.startswith("depends on: "):
              depends = li[12:]
            elif li.startswith("defined in: "):
              defined = li[12:]
            elif li.startswith("found in Linux kernels: "):
              kernelversions = li[24:]
            elif li.startswith("modules built: "):
              modules = li[15:]

          self.ok_count += 1
          logger.info("Page '%s' parsed successfully" % (config_page_url))
          yield KernelConfigItem(config_page_url, name, shorthelp, help, type, depends, defined, kernelversions, modules)

        except UnicodeDecodeError:
          # some pages contain badly encoded chars, eg: http://cateee.net/lkddb/web-lkddb/SA1100_PFS168.html
          self.logParsingError(__class__.INVALID_CHAR, config_page_url)
        except:
          # unknown error
          self.logParsingError(__class__.UNKNOWN, config_page_url)
          raise
    raise StopIteration

  def logParsingError(self, error, url):
    self.ko_count[error] += 1
    logger.warning("Skipping page '%s' (%s)" % (url, __class__.KO_REASON_STR[error]))

  def getPageFromCache(self, url):
    logger = logging.getLogger()
    # get path to local file
    domain = urllib.parse.urlparse(url)[1]
    page = urllib.parse.urlparse(url)[2]
    local_filepath = os.path.join("download", domain)
    for subdir in page.split("/")[1:]:
      local_filepath = os.path.join(local_filepath, subdir)
    logger.debug("Getting local file '%s' for url '%s'..." % (local_filepath, url))
    # read file
    with open(local_filepath, "rb") as file:
      page = file.read()
    return page


if __name__ == "__main__":

  # setup logger
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  logger = logging.getLogger()

  # dump config items
  parser = LkddbParser()
  with open("output.txt", "wt") as output_file:
    for config_item in parser:
      output_file.write(str(config_item))
  logger.info("%d config items parsed successfully" % (parser.ok_count))
  logger.info("%d skipped pages (website errors)" % (sum(parser.ko_count.values())))
  for error_cause in LkddbParser.KO_REASON:
    logger.info("\t %d %s errors" % (parser.ko_count[error_cause], LkddbParser.KO_REASON_STR[error_cause]))

########NEW FILE########
__FILENAME__ = fetch
import codecs
from httplib2 import urllib
import os
import time

from bs4 import BeautifulSoup

from lxml import etree
    
class CacheFetcher(object):
  """ A wrapper around urllib's fetcher that provides filesystem caching. """
  def __init__(self, cachedir, formatter, sleep=0):
    self._sleep = sleep
    if not os.path.exists(cachedir):
      os.mkdir(cachedir)
    self._cachedir = cachedir
    self._formatter = formatter

  def fetch(self, url):
    """ Fetch url and return a file-like representation. """
    fname = os.path.join(self._cachedir, self._formatter(url))
    if not os.path.exists(fname):
      time.sleep(self._sleep)
      html = urllib.urlopen(url).read()
      with codecs.open(fname, 'w', 'utf-8') as f:
        soup = BeautifulSoup(html)
        f.write(unicode(soup))
    return fname

def extract_sitemap(sitemap, patt):
  """ A generator for crawlable URLs. """
  tree = etree.parse(sitemap).getroot()
  for e in tree.xpath('/x:urlset/x:url/x:loc',
      namespaces={'x': 'http://www.sitemaps.org/schemas/sitemap/0.9'}):
    # `example` is a one-off fix to remove tutorial-like pages.
    # An obvious improvement is to roll this back into pattern.
    if patt in e.text and 'example' not in e.text:
      yield e.text

def filename_formatter(url):
  _, obj, prop = url.rsplit('/', 2)
  return obj + '.' + prop
  
def run(sitemapurl, patt, cachedir, cachejournal, sleep=5):
  """
  Args:
    sitemapurl: A string URL to an XML sitemap.
    patt: A string used for substring matching of the urls in the sitemap.
    cachedir: Directory used to cache downloaded HTML files.
    cachejournal: A string filename to store records about the 
      cache directory. Should be considered a tmp file.
    sleep: Integer amount of time to sleep between HTTP requests, in seconds.
  """
  fetcher = CacheFetcher(cachedir, filename_formatter, sleep)
  sitemap = urllib.urlopen(sitemapurl)
  with open(cachejournal, 'w') as journal:
    for url in extract_sitemap(sitemap, patt):
      fname = fetcher.fetch(url)
      journal.write('{0},{1}\n'.format(fname, url))
  
if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('--sitemap')
  parser.add_argument('--patt')
  parser.add_argument('--cachedir')
  parser.add_argument('--cachejournal')
  parser.add_argument('--sleep', type=int)
  args = parser.parse_args()
  run(args.sitemap, args.patt, args.cachedir, args.cachejournal, args.sleep)

########NEW FILE########
__FILENAME__ = parse
import codecs
from collections import Counter

from bs4 import BeautifulSoup

class Standardizer(object):
  """ Standardize the titles of each entry.

  MDN uses a wiki for its documentation, so titles aren't consistent.
  For example, you might have:
    Array reverse
    Array.reverse
    Array.prototype.reverse
  """
  TITLE_FORMATTING = {
    'class_property': '%s.%s',
    'class_function': '%s.%s',
    'instance_method': '%s.prototype.%s',
    'instance_property': '%s.prototype.%s',
  }
  def __init__(self, specfile):
    """
    Args:
      specfile: A filesystem path to a csv file containing language 
      definitions. It should have the format:
        BaseObject,property,{class_property,class_function,instance_method,instance_property}
    """
    self.inverted_index = {}
    self.objects = set()
    with codecs.open(specfile, 'r', 'utf-8') as f:
      for line in f:
        line = line.strip()
        index = line.split('(')[0]
        if index.count('.') > 1:
          index = index.split('prototype')[-1]
        index = index.split('.')[-1].lower().strip()
        if index not in self.inverted_index:
          self.inverted_index[index] = []
        self.inverted_index[index].append(line)

        obj = line.split('.')[0]
        self.objects.add(obj)

  def standardize(self, mdn):
    """ Standardize and clean the fields within an MDN object. """
    if 'Global' in mdn.obj: 
      mdn.obj = 'Global'
    if mdn.obj not in self.objects:
      return None
    if mdn.prop.lower() not in self.inverted_index:
      return mdn
    for signature in self.inverted_index[mdn.prop.lower()]:
      if signature.startswith(mdn.obj):
        mdn.codesnippet = signature
        mdn.title = signature.split('(')[0].strip()
        break

    return mdn


class FatWriter(object):
  """ File writer for DDG Fathead files. Field orders and output format
  comply with the documentation at https://github.com/duckduckgo/
  zeroclickinfo-fathead."""

  FIELDS = [
    'title',
    'type',
    'redirect',
    'otheruses',
    'categories',
    'references',
    'see_also',
    'further_reading',
    'external_links',
    'disambiguation',
    'images',
    'abstract',
    'source_url'
  ]
  def __init__(self, outfile):
    self.outfile = outfile

  def writerow(self, outdict):
    """ Write the dict row. """
    row = []
    for field in FatWriter.FIELDS:
      col = outdict.get(field, '')
      col = col.replace('\t', '    ')
      col = col.replace('\n', '\\n')
      row.append(col)
    self.outfile.write('\t'.join(row) + '\n')

class MDNWriter(FatWriter):
  """ An implementation of FatWriter that knows how to convert between MDN objects
      and the FatWriter spec. """
  def writemdn(self, mdn):
    code = ''
    abstract = ''
    if mdn.codesnippet:
      code = '<pre><code>%s</code></pre>' % mdn.codesnippet
    if mdn.summary:
      if abstract:
        abstract += ': '
      abstract += mdn.summary
    abstract = code + abstract
    d = {
      'title': mdn.title,
      'type': 'A', 
      'source_url': mdn.url,
      'abstract': abstract 
    }
    self.writerow(d)

class MDN(object):
  """ A container object for an MDN article. 

  For example, given http://developer.mozilla.org/en-US/docs/
  JavaScript/Reference/Global_Objects/Array/pop, the object would have these
  properties:

  title         Array.pop
  url           http://developer.mozilla.org ...
  summary       Removes the last element from an array and returns that element.
  codesnippet   array.pop()
  obj           Array
  prop          pop

  
  Args:
    title: The article's title.
    url: The articles full URL.
    summary: A couple-sentence overview of the article.
    codesnippet: A couple lines of code showing the syntax. Multiple lines
    should be delimited with \n.
    obj: The calling object.
    prop: The calling object's property.
  """
  def __init__(self, title=None, url=None, summary=None, codesnippet=None,
                     obj=None, prop=None):
    self.title = title
    self.url = url
    self.summary = summary
    self.codesnippet = codesnippet
    self.obj = obj
    self.prop = prop
        
class MDNParser(object):
  """ A parser that takes an MDN wiki page and returns an MDN object. If pages change
  causing this Fathead to break, then the queries in this class should be checked. """
  def _extract_node(self, node):
    if node is not None:
      txt = node.text
      if txt:
        return txt.strip()

  def _is_obsolete(self, soup):
    obsolete = soup.find(_class='obsoleteHeader')
    return obsolete is not None

  def parse(self, htmlfile):
    """ Parse an html file and return an mdn object.

    Args:
      htmlfile: A file-like object that should parse with beautiful soup's html parser.
    """
    title_el, summary_el, codesnippet_el = None, None, None
    soup = BeautifulSoup(htmlfile)
    if self._is_obsolete(soup):
      return None
    title_el = soup.find('h1', class_='page-title')
    article = soup.find(id='wikiArticle')
    if article:
      summary_el = article.find(
          lambda e: e.name=='p' and e.text.strip() != '', recursive=False)
    syntax_header = soup.find(id='Syntax')
    if syntax_header:
      codesnippet_el = syntax_header.find_next(['pre', 'code'])
    mdn = MDN()
    mdn.title = self._extract_node(title_el)
    mdn.summary = self._extract_node(summary_el)
    mdn.codesnippet = self._extract_node(codesnippet_el)
    return mdn

class MDNIndexer(object):
  def __init__(self, writer):
    self._writer = writer
    self.counter = Counter()
    self.inverted_index = {}

  def add(self, mdn): 
    keyword = mdn.prop.lower()
    self.counter[keyword] += 1
    if keyword not in self.inverted_index:
      self.inverted_index[keyword] = []
    self.inverted_index[keyword].append(mdn)

  def writerows(self):
    for keyword, count in self.counter.most_common():
      if count > 1:
        disambig = ''
        for mdn in self.inverted_index[keyword]:
          if disambig:
            disambig += '\\n'
          if '.' in mdn.summary:
            summary = mdn.summary[:mdn.summary.find('.') + 1]
          else:
            summary = mdn.summary
          disambig += '*[[%s]] %s' % (mdn.title, summary)
        # Write a disambiguation
        self._writer.writerow({
          'title': keyword,
          'type': 'D',
          'disambiguation': disambig
        })
      for mdn in self.inverted_index[keyword]:
        # For all entries in the inverted index, write a redirect of 
        # of the form <object><space><property>
        self._writer.writerow({
          'title': '%s %s' %(mdn.obj.lower(), mdn.prop.lower()),
          'type': 'R',
          'redirect': mdn.title
        })
        # If this is the only item in the inverted index,
        # write a primary redirect on the keyword.
        if count == 1:
          self._writer.writerow({
            'title': keyword,
            'type': 'R',
            'redirect': mdn.title
          })

def run(cachedir, cachejournal, langdefs, outfname):
  """
  Args:
    cachedir: Directory used to cache downloaded HTML files.
    cachejournal: A csv of fname,url pairs for the cache dir. 
    langdefs: A filepath to a language definition for JavaScript. See
      the Standardizer class for info on this spec.
    outname: The output filename.
  """
  standardizer = Standardizer(langdefs)
  parser = MDNParser()
  journal = [l.strip().split(',') for l in open(cachejournal).read().splitlines()]
  with codecs.open(outfname, 'w', 'utf-8') as outfile:
    writer = MDNWriter(outfile)
    indexer = MDNIndexer(writer)
    # Iterate over URLs in the sitemap ...
    for fname, url in journal:
      # ... and parse each to generate an mdn object.
      mdn = parser.parse(codecs.open(fname, 'r', 'utf-8'))
      if not mdn or not mdn.summary:
        continue
      # WARNING WARNING
      # 
      #  If MDN updates their URL structure, this will break. This assumes that
      #  the URL ends with /obj/property
      #
      #  An improvement would be to supply this as a regex pattern to the CL
      #
      # WARNING WARNING
      _, obj, prop = url.rsplit('/', 2)
      mdn.url = url
      mdn.obj = obj
      mdn.prop = prop
      mdn = standardizer.standardize(mdn)
      if mdn is None:
        continue
      # Here we require that outputs have either a summary or a code sample.
      if mdn.summary or mdn.codesnippet:
        writer.writemdn(mdn)
        indexer.add(mdn)
    indexer.writerows()
  
if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('--out')
  parser.add_argument('--cachedir')
  parser.add_argument('--cachejournal')
  parser.add_argument('--langdefs')
  args = parser.parse_args()
  run(args.cachedir, args.cachejournal, args.langdefs, args.out)

########NEW FILE########
__FILENAME__ = tohtml
"""
 Generate a quick HTML dump of a Fathead output.txt
"""
import csv

from parse import FatWriter

HTML = """
 <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
 <style>
   body {{
     font-family: 'Helvetica Neue', 'Segoe UI', sans-serif;
     font-size: 12px;
   }}
   .block {{
     margin: 40px auto;
     width: 600px;
   }}
   h1 {{
     color: rgb(67, 67, 67);
     font-size: 18px;
     font-style: normal;
     font-variant: normal;
     font-weight: bold;
     line-height: 36px;
   }}
 </style>
 <body>
 {body}
 </body>
"""
ROW = """
<div class="block">
<h1>{title} (JavaScript)</h1>
<div>
  {abstract}
</div>
<a href="{source_url}">{source_url}</a>
<p>{redirect}</p>
<pre>{disambiguation}</pre>
</div>
"""

def run(infname, outfname):
  infile = open(infname)
  reader = csv.DictReader(infile, FatWriter.FIELDS, dialect='excel-tab')
  with open(outfname, 'w') as outfile:
    rows = []
    for line in reader:
      rows.append(ROW.format(**line))
    body = '\n'.join(rows)
    outfile.write(HTML.format(body=body).replace('\\n', '\n'))

if __name__ == '__main__':
  infname = 'output.txt'
  outfname = 'output.html'
  run(infname, outfname)

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python2
import mimetypes
mimetypes.init()
OUTPUT = "output.txt"
fout = open(OUTPUT,"w")
for extension, mimetype in mimetypes.types_map.iteritems():
	fout.write("\t".join([extension, "A", "", "", "", "", "", "", "", "", "", "The MIME type for the extension "+extension+" is "+mimetype+".", "http://en.wikipedia.org/wiki/MIME_type#List_of_common_media_types"])+"\n")

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Released under the GPL v2 license 
# https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

import lxml.etree, lxml.html
import re

editlink = re.compile("action=edit"); 
iswikipedia = re.compile("wikipedia");
url = "https://secure.wikimedia.org/wikipedia/en/wiki/List_of_TCP_and_UDP_port_numbers"
output = "output.txt"

f = open(output, "w");

ports_list = {};

def get_port_range(ports):
    '''Returns a list with start and end of the range'''
    ports = ports.encode("utf8");
    p = ports.replace("–", "-").split("-");
    if len(p) == 2:
        return [int(p[0]), int(p[1])]
    else:
        return [int(p[0]), int(p[0])]

def get_protocol_string(tcp, udp):
    '''TCP/UDP string for description'''
    if tcp == "TCP" and udp == "UDP":
        return tcp + "/" + udp + " - ";
    elif tcp == "TCP" or udp == "UDP":
        return tcp + udp + " - ";
    else:
        return "";


tree = lxml.html.parse("download/raw.dat").getroot()
tables = tree.find_class("wikitable sortable")
for table in tables:
    for row in table.findall('tr'):
        cells = row.findall('td')
        if len(cells) != 5:
            continue;

        ports = get_port_range(cells[0].text_content());
        is_port_range = False;
        if ports[0] != ports[1]:
            is_port_range = True;
        protocol = get_protocol_string(cells[1].text_content(), cells[2].text_content());

        try:
            links = cells[3].findall('a');
        except:
            links = [];
        
        if len(links):
            for i in links:
                if not editlink.search(i.attrib['href']) and iswikipedia.search(i.attrib['href']):
                    # Convert link to Wikipedia format
                    i.text = "[[" + i.attrib["title"] + "|" + i.text_content() + "]]"

        # Remove citenote text
        description = re.sub("\[\d*\]", "", cells[3].text_content());
        # And [citation needed] text too
        description = re.sub("\[citation needed\]", "", description);

        status = cells[4].text_content();

        description = protocol + description + " (" + status + ")";
        if is_port_range:
            description += " [" + str(ports[0]) + "-" + str(ports[1]) + "]";

        for j in xrange(ports[0], ports[1] + 1):
            # Loop through the port range, and add to list or create list as necessary
            if ports_list.has_key(j):
                ports_list[j].append(description);
            else:
                ports_list[j] = [description];


for port, descriptions in ports_list.iteritems():
    description = unicode("<br />".join(descriptions)).encode("utf-8");
    f.write("\t".join([str(port),      # title
                    "",                # namespace
                    url,               # url
                    description,       # description
                    "",                # synopsis
                    "",                # details
                    "",                # type
                    ""                 # lang
                   ])
           );
    f.write("\n");
f.close()

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/python
# -*- coding: utf-8 -*-

import lxml.etree, lxml.html
import re

url = "http://redis.io"
output = "output.txt"

f = open(output, "w");

tree = lxml.html.parse("download/raw.dat").getroot()
commands = tree.find_class("command")

data = {}

for command in commands:

    for row in command.findall('a'):
        command_url = "%s%s" % (url, row.get('href'))
        
        for sibling in command.itersiblings():
            usage = ""
            
            for command_args in command.findall('span'):
                usage = "%s %s" % (row.text, command_args.text.replace(' ', '').replace('\n', ' ').strip())

            summary = "%s." % (re.sub('\.$', '', sibling.text))

            data[command_url] = (row.text, summary, usage)

for command_url in data.keys():
    command, summary, usage = data[command_url]
    summary = unicode(summary).encode("utf-8")
    usage = unicode(usage).encode("utf-8")
    
    f.write("\t".join([str(command),      # title
                    "",                # namespace
                    command_url,               # url
                    summary,       # description
                    usage,                # synopsis
                    "",                # details
                    "",                # type
                    ""                 # lang
                   ])
           )
    f.write("\n")
f.close()

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import namedtuple
import json, itertools, urllib, re, sys

ABSTRACT_TEMPLATE = unicode("""
{name} is a researcher{keyword_phrase}. {last_name} has written {num_papers} paper{paper_prefix} with {num_coauthors} coauthor{coauthor_prefix} and {num_citations} citation{citation_prefix}.
""")

AUTHOR_CATEGORIES = ['researchers']

DownloadRow = namedtuple('DownloadRow',
        ['names','url','image_url','num_papers', 'num_coauthors',
         'num_citations','keywords'])

class ParsedDownloadRow(DownloadRow):
    @property
    def names(self):
        try:
            return json.loads(super(ParsedDownloadRow, self).names)
        except:
            return []

    @property
    def keywords(self):
        try:
            return json.loads(super(ParsedDownloadRow, self).keywords)
        except:
            return []

DDGOutputRow = namedtuple('DDGOutputRow',
        ['title', 'type', 'redirect', 'other_uses', 'categories', 'references',
         'see_also', 'further_reading', 'external_links', 'disambiguation',
         'images', 'abstract', 'source_url'])

def replace_whitespace(s):
    return unicode(s).replace('\t',' ').replace('\n', ' ').replace('\r', ' ')

WHITESPACE_PATTERN = re.compile(r'\s+')

def minify_whitespace(s):
    return WHITESPACE_PATTERN.sub(' ', s)

def ddg_search_url(query):
    return 'https://duckduckgo.com/?%s' % urllib.urlencode({'q':query})

def format_keywords(keywords):
    linked_kw = [kw.lower() for kw in keywords]
    first_part = ', '.join(linked_kw[:-2])
    second_part = ' and '.join(linked_kw[-2:])
    parts = [part for part in [first_part, second_part] if len(part) > 0]
    return ', '.join(parts)

def output_from_row(row):
    # generate the main page
    if len(row.names) == 0 or len(row.keywords) == 0:
        return ''
    
    # NB these templating funcs expect n >= 0
    def number_or_no(n):
        return unicode(n) if n > 0 else 'no'

    def plural_suffix(n):
        return 's' if n > 1 or n == 0 else ''

    keyword_phrase = ' interested in %s' % format_keywords(row.keywords) \
            if len(row.keywords) > 0 else ''

    # NB this is not the best way to handle last names (at all), but should
    # work for the majority of cases right now
    last_name = row.names[0].split()[-1]

    num_coauthors = number_or_no(row.num_coauthors)
    coauthor_prefix = plural_suffix(row.num_coauthors)

    num_papers = number_or_no(row.num_papers)
    paper_prefix = plural_suffix(row.num_papers)

    num_citations = number_or_no(row.num_citations)
    citation_prefix = plural_suffix(row.num_citations)

    article = DDGOutputRow(title=row.names[0],
                           type='A',
                           redirect='',
                           other_uses='',
                           categories='\\n'.join(AUTHOR_CATEGORIES),
                           references='',
                           see_also='',
                           further_reading='',
                           external_links='[%s More at Scholrly]' % row.url,
                           disambiguation='',
                           images='[[Image:%s]]' % row.image_url,
                           abstract=minify_whitespace(
                               ABSTRACT_TEMPLATE.format(
                                   name=row.names[0],
                                   last_name=last_name,
                                   num_coauthors=num_coauthors,
                                   coauthor_prefix=coauthor_prefix,
                                   num_papers=num_papers,
                                   paper_prefix=paper_prefix,
                                   num_citations=num_citations,
                                   citation_prefix=citation_prefix,
                                   keyword_phrase=keyword_phrase)),
                           source_url=row.url)
    # generate redirects for any aliases
    redirects = [DDGOutputRow(title=name, type='R',redirect=row.names[0],
                              other_uses='',categories='',references='',
                              see_also='',further_reading='',external_links='',
                              disambiguation='', images='', abstract='',
                              source_url='')
                 for name in row.names[1:]]
    return '\n'.join('\t'.join(replace_whitespace(el) for el in row)
                     for row in [article] + redirects)

used_names = set()

if __name__ == '__main__':
    with open(sys.argv[1]) as data_file:
        # read in the downloaded data, skipping the header
        rows = (ParsedDownloadRow(*line.split('\t'))
                for line in itertools.islice(data_file, 1, None))
        with open(sys.argv[2], 'a') as output_file:
            for row in rows:
                # make sure we don't use a name twice, since we don't do disambig
                # pages yet
                if all(name not in used_names and not used_names.add(name)
                    for name in row.names):
                    output_file.write(output_from_row(row).encode('utf8') + '\n')

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2008, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.0.7a"
__copyright__ = "Copyright (c) 2004-2008 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

# First, the classes that represent markup elements.

class PageElement:
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.contents.index(self)
        if hasattr(replaceWith, 'parent') and replaceWith.parent == self.parent:
            # We're replacing this element with one of its siblings.
            index = self.parent.contents.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                self.parent.contents.remove(self)
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if (isinstance(newChild, basestring)
            or isinstance(newChild, unicode)) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent != None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent == self:
                index = self.find(newChild)
                if index and index < position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        else:
            # Build a SoupStrainer
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        if encoding:
            return self.encode(encoding)
        else:
            return self

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs == None:
            attrs = []
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isString(val):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        contents = [i for i in self.contents]
        for i in contents:
            if isinstance(i, Tag):
                i.decompose()
            else:
                i.extract()
        self.extract()

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        for i in range(0, len(self.contents)):
            yield self.contents[i]
        raise StopIteration

    def recursiveChildGenerator(self):
        stack = [(self, 0)]
        while stack:
            tag, start = stack.pop()
            if isinstance(tag, Tag):
                for i in range(start, len(tag.contents)):
                    a = tag.contents[i]
                    yield a
                    if isinstance(a, Tag) and tag.contents:
                        if i < len(tag.contents) - 1:
                            stack.append((tag, i+1))
                        stack.append((a, 0))
                        break
        raise StopIteration

# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isString(attrs):
            kwargs['class'] = attrs
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if isList(markup) and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isString(markup):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst == True and type(matchAgainst) == types.BooleanType:
            result = markup != None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isString(markup):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif isList(matchAgainst):
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isString(markup):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def isList(l):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is listlike."""
    return hasattr(l, '__iter__') \
           or (type(l) in (types.ListType, types.TupleType))

def isString(s):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is stringlike."""
    try:
        return isinstance(s, unicode) or isinstance(s, basestring)
    except NameError:
        return isinstance(s, str)

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif isList(portion):
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not isList(self.markupMassage):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.find('start_') == 0 or methodName.find('end_') == 0 \
               or methodName.find('do_') == 0:
            return SGMLParser.__getattr__(self, methodName)
        elif methodName.find('__') != 0:
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()
        # Tags with just one string-owning child get the child as a
        # 'string' property, so that soup.tag.string is shorthand for
        # soup.tag.contents[0]
        if len(self.currentTag.contents) == 1 and \
           isinstance(self.currentTag.contents[0], NavigableString):
            self.currentTag.string = self.currentTag.contents[0]

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers != None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers == None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join(map(lambda(x, y): ' %s="%s"' % (x, y), attrs))
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ['br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base'])

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ['span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center']

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ['blockquote', 'div', 'fieldset', 'ins', 'del']

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ['address', 'form', 'p', 'pre']

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ['em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big']

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ['noscript']

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if type(sub) == types.TupleType:
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = parse_apache2option
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/apache2/'):
  if '.html' in file:
    files.append('./docs/apache2/%s'%(file))

for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  for dir in soup.findAll(attrs={"class":"directive-section"}):
    name = openclosetags.sub('',str(dir.findAll('h2')[0])).strip()
    desc = ''
    p = dir.findAll('p')
    if len(p) == 0:
      desc = openclosetags.sub('',str(dir.findAll(attrs={"class":"note"})[0]))
    else:
      desc = openclosetags.sub('',str(p[0]))
    synopsis = openclosetags.sub('',str(dir.findAll('tr')[1].findAll('td')[0]))

    url = "http://httpd.apache.org/docs/2.2/mod/%s#%s"%(file.replace('./docs/apache2/',''),dir.findAll('a')[0]['id'])

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','apache2directive','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apache apache2 directive apache2.2','apache2directive','en')

########NEW FILE########
__FILENAME__ = parse_appleios
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

#files.append('./docs/apple/osx/developer.apple.com.library/mac/documentation/Cocoa/Reference/NSCondition_class/Reference-Reference.html')


for root,dirs,filelist in os.walk('./docs/apple/ios/'):
  for file in filelist:
    if '.html' in file:
      files.append("%s/%s"%(root,file))


for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  # Get Object Details
  name = openclosetags.sub('',str(soup.findAll(attrs={"id":"pageTitle"})[0]))
  if len(soup.findAll(attrs={"class":"abstract"})) != 0:
    desc = openclosetags.sub('',str(soup.findAll(attrs={"class":"abstract"})[0]))
  else:
    temp = soup.findAll(attrs={"id":"Overview_section"})[0].findAll('p')
    temp = ''.join(map(lambda x:str(x),temp))
    desc = openclosetags.sub('',temp)

  name = name.split(' ')[0]
  url = "http://%s"%(file.replace('./docs/apple/ios/','').replace('\\','/').replace('developer.apple.com.','developer.apple.com/').replace('-','/')).replace("ReferenceReference","Reference/Reference")
  synopsis = ''
  namespace = name


  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url,desc,synopsis,'','osx','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple ios iphone ipad','appleios','en')

  space = name
  for i in soup.findAll(attrs={"class":"api instanceMethod"}):
    name = i.findAll('h3')[0].string
    desc = openclosetags.sub('',str(i.findAll('p')[0]))
    namespace = "%s.%s"%(space,name)

    url2 = "%s#%s" %(url,i.findAll('a')[0]['name'])

    api = i.findAll(attrs={'class':'api discussion'})
    if len(api) != 0:
      desc = "%s %s"%(desc, openclosetags.sub('',' '.join(map(lambda x:str(x),api[0].findAll('p')))))
    if len(i.findAll(attrs={'class':'api availability'})) != 0:
      if len(i.findAll(attrs={'class':'api availability'})[0].findAll('li')) != 0:
        desc = '%s %s'%(desc,openclosetags.sub('',str(i.findAll(attrs={'class':'api availability'})[0].findAll('li')[0])))
    synopsis = openclosetags.sub('',str(i.findAll(attrs={'class':'declaration'})[0]))[2:]

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url2,desc,synopsis,'','osx','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url2,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple ios iphone ipad','appleios','en')

  for i in soup.findAll(attrs={"class":"api classMethod"}):
    name = i.findAll('h3')[0].string
    desc = openclosetags.sub('',str(i.findAll('p')[0]))
    namespace = "%s.%s"%(space,name)

    url2 = "%s#%s" %(url,i.findAll('a')[0]['name'])

    api = i.findAll(attrs={'class':'api discussion'})
    if len(api) != 0:
      desc = "%s %s"%(desc, openclosetags.sub('',' '.join(map(lambda x:str(x),api[0].findAll('p')))))
    if len(i.findAll(attrs={'class':'api availability'})) != 0:
      if len(i.findAll(attrs={'class':'api availability'})[0].findAll('li')) != 0:
        desc = '%s %s'%(desc,openclosetags.sub('',str(i.findAll(attrs={'class':'api availability'})[0].findAll('li')[0])))
    synopsis = openclosetags.sub('',str(i.findAll(attrs={'class':'declaration'})[0]))[2:]

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url2,desc,synopsis,'','osx','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url2,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple ios iphone ipad','appleios','en')



########NEW FILE########
__FILENAME__ = parse_appleosx
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

#files.append('./docs/apple/osx/developer.apple.com.library/mac/documentation/Cocoa/Reference/NSCondition_class/Reference-Reference.html')


for root,dirs,filelist in os.walk('./docs/apple/osx/'):
  for file in filelist:
    if '.html' in file:
      files.append("%s/%s"%(root,file))


for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  # Get Object Details
  name = openclosetags.sub('',str(soup.findAll(attrs={"id":"pageTitle"})[0]))
  if len(soup.findAll(attrs={"class":"abstract"})) != 0:
    desc = openclosetags.sub('',str(soup.findAll(attrs={"class":"abstract"})[0]))
  else:
    temp = soup.findAll(attrs={"id":"Overview_section"})[0].findAll('p')
    temp = ''.join(map(lambda x:str(x),temp))
    desc = openclosetags.sub('',temp)

  name = name.split(' ')[0]
  url = "http://%s"%(file.replace('./docs/apple/osx/','').replace('\\','/').replace('developer.apple.com.','developer.apple.com/').replace('-','/'))
  synopsis = ''
  namespace = name


  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url,desc,synopsis,'','osx','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple osx os x mac','osx','en')

  space = name
  for i in soup.findAll(attrs={"class":"api instanceMethod"}):
    name = i.findAll('h3')[0].string
    desc = openclosetags.sub('',str(i.findAll('p')[0]))
    namespace = "%s.%s"%(space,name)

    url2 = "%s#%s" %(url,i.findAll('a')[0]['name'])

    api = i.findAll(attrs={'class':'api discussion'})
    if len(api) != 0:
      desc = "%s %s"%(desc, openclosetags.sub('',' '.join(map(lambda x:str(x),api[0].findAll('p')))))
    if len(i.findAll(attrs={'class':'api availability'})) != 0:
      desc = '%s %s'%(desc,openclosetags.sub('',str(i.findAll(attrs={'class':'api availability'})[0].findAll('li')[0])))
    synopsis = openclosetags.sub('',str(i.findAll(attrs={'class':'declaration'})[0]))[2:]

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url2,desc,synopsis,'','osx','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url2,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple osx os x mac','osx','en')

  for i in soup.findAll(attrs={"class":"api classMethod"}):
    name = i.findAll('h3')[0].string
    desc = openclosetags.sub('',str(i.findAll('p')[0]))
    namespace = "%s.%s"%(space,name)

    url2 = "%s#%s" %(url,i.findAll('a')[0]['name'])

    api = i.findAll(attrs={'class':'api discussion'})
    if len(api) != 0:
      desc = "%s %s"%(desc, openclosetags.sub('',' '.join(map(lambda x:str(x),api[0].findAll('p')))))
    if len(i.findAll(attrs={'class':'api availability'})) != 0:
      desc = '%s %s'%(desc,openclosetags.sub('',str(i.findAll(attrs={'class':'api availability'})[0].findAll('li')[0])))
    synopsis = openclosetags.sub('',str(i.findAll(attrs={'class':'declaration'})[0]))[2:]

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url2,desc,synopsis,'','osx','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url2,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'apple osx os x mac','osx','en')



########NEW FILE########
__FILENAME__ = parse_backbonejs
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)
badtags = re.compile('''<p.*>|</p>|<b.*>.*</b>|<code.*>.*</code>|<span.*>.*</span>|<.*?>|</.*?>''')
spaces = re.compile('''\s+''',re.DOTALL)

files = []

files.append('./docs/backbonejs.html')


for file in files:
	filecontents = open(file).read()
	soup = BeautifulSoup(filecontents)
	for s in soup.findAll('p'):
		
		name = ''
		synopsis = ''
		
		try:
			name = openclosetags.sub('',str(s.findAll('b')[0]))
			#synopsis = openclosetags.sub('',str(s.findAll('code')[0]))
			synopsis = openclosetags.sub('', str(s.findNextSiblings('pre')[0])).replace("'","''")
			desc = openclosetags.sub('',spaces.sub(' ',badtags.sub('',str(s)))).replace("'","")
			url = "http://documentcloud.github.com/underscore/#%s"%(name)
			
			if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
				print "%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis)
			if sys.argv[1].lower() == 'sql':
				print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'','backbone.js','en')
			
		except:
			pass
########NEW FILE########
__FILENAME__ = parse_clojure
from BeautifulSoup import BeautifulSoup
import re
import os
import sys


openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/clojure/'):
  files.append('./docs/clojure/%s'%(file))


for file in files:
  filecontents = open(file).read()
  
  soup = BeautifulSoup(filecontents)
  
  namespace = openclosetags.sub('',str(soup.findAll(attrs={"id":"long-name"})[0]))
  
  for node in soup.findAll(attrs={"id":"var-entry"}):
    name = openclosetags.sub('',str(node.findAll('h2')[0]))
    synopsis = openclosetags.sub('',str(node.findAll(attrs={"id":"var-usage"})[0]))
    desc =  openclosetags.sub('',''.join(map(lambda x:str(x),(node.findAll(attrs={"id":"var-docstr"})))))
    url = "http://clojure.github.com/clojure/%s#%s/%s"%(file.replace('./docs/clojure/',''),namespace,name)

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url,desc.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','clojure','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,desc.replace("'","''"),synopsis.replace("'","''"),'','clojure','')

########NEW FILE########
__FILENAME__ = parse_cobol
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

files.append('./docs/cobol.htm')

args = {
	'ABS':'( argument-1 )',
	'ACOS':'( argument-1 )',
	'ANNUITY':'( argument-1 argument-2 )',
	'ASIN':'( argument-1 )',
	'ATAN':'( argument-1 )',
	'CHAR':'( argument-1 )',
	'CHAR-NATIONAL':'( argument-1 )',
	'COS':'( argument-1 )',
	'CURRENT-DATE':'',
	'DATE-OF-INTEGER':'( argument-1 )',
	'DATE-TO-YYYYMMDD':'( argument-1 [argument-2] )',
	'DAY-OF-INTEGER':'( argument-1 )',
	'DAY-TO-YYYYDDD':'( argument-1 [argument-2] )',
	'DISPLAY-OF':'( argument-1 [argument-2] )',
	'E':'',
	'EXP':'( argument-1 )',
	'EXP10':'( argument-1 )',
	'FACTORIAL':'( argument-1 )',
	'FRACTION-PART':'( argument-1 )',
	'INTEGER':'( argument-1 )',
	'INTEGER-OF-DATE':'( argument-1 )',
	'INTEGER-OF-DAY':'( argument-1 )',
	'INTEGER-PART':'( argument-1 )',
	'LENGTH':'( argument-1 )',
	'LENGTH-AN':'( argument-1 )',
	'LOG':'( argument-1 )',
	'LOG10':'( argument-1 )',
	'LOWER-CASE':'( argument-1 )',
	'MAX':'( argument-1 )',
	'MEAN':'( { argument-1 } ... )',
	'MEDIAN':'( { argument-1 } ... )',
	'MIDRANGE':'( { argument-1 } ... )',
	'MIN':'( { argument-1 } ... )',
	'MOD':'( argument-1 argument-2 )',
	'NATIONAL-OF':'( argument-1 [argument-2] )',
	'NUMVAL':'( argument-1 )',
	'NUMVAL-C':'( argument-1 [argument-2] )',
	'ORD':'( argument-1 )',
	'ORD-MAX':'( { argument-1 } ... )',
	'ORD-MIN':'( { argument-1 } ... )',
	'PI':'',
	'PRESENT-VALUE':'( argument-1 [argument-2] )',
	'RANDOM':'[ ( argument-1 ) ]',
	'RANGE':'( { argument-1 } ... )',
	'REM':'( argument-1 argument-2 )',
	'REVERSE':'( argument-1 )',
	'SIGN':'( argument-1 )',
	'SIN':'( argument-1 )',
	'SQRT':'( argument-1 )',
	'STANDARD-DEVIATION':'( { argument-1 } ... )',
	'SUM':'( { argument-1 } ... )',
	'TAN':'( argument-1 )',
	'UPPER-CASE':'( argument-1 )',
	'VARIANCE':'( { argument-1 } ... )',
	'WHEN-COMPILED':'',
	'YEAR-TO-YYYY':'( argument-1 [argument-2] ) ',
}


for file in files:
	filecontents = open(file).read()
	soup = BeautifulSoup(filecontents)
	for s in soup.findAll('h3'):
		t = re.compile('''[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2} ''',re.DOTALL)
		name = t.sub('',str(s))
		name = openclosetags.sub('',name.replace('The ','').replace(' Function','').replace(' function',''))
		
		desc =  str(s.nextSibling.nextSibling)
		if "dialm.gif" in desc:
			desc = str(s.nextSibling.nextSibling.nextSibling.nextSibling)
		desc = openclosetags.sub('',desc)
		
		url = "http://supportline.microfocus.com/documentation/books/sx20books/lrpdf7.htm#%s"%s.findAll('a')[0]['name']
		
		
		synopsis = "FUNCTION %s %s"%(name,args[name.strip()])
		
		
		if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
			print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc.replace("\n","__NEWLINE__"),synopsis.replace("\n","__NEWLINE__"),'','cobol','en')
		if sys.argv[1].lower() == 'sql':
			print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'','cobol','en')
		
		
########NEW FILE########
__FILENAME__ = parse_cplusplus
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import MySQLdb


conn = MySQLdb.connect(user='root')

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/cplusplus/'):
  files.append('./docs/cplusplus/%s'%(file))

#http://www.cplusplus.com/reference/
for file in files:
  filecontents = open(file).read()
  
  soup = BeautifulSoup(filecontents)
  
  for node in soup.findAll("div",{"class":re.compile(r'\btype-post\b')}):
    name = openclosetags.sub('',str(node.findAll("div","post-title")[0]))
    desc = openclosetags.sub('',str(node.findAll("div","p-con")[0].findAll('p')[0]))
    s = node.findAll("div","wp_syntax")[0].findAll('pre')
    synopsis = ''
    if len(s) == 1:
        synopsis = openclosetags.sub('',str(s[0]))
    else:
        synopsis = openclosetags.sub('',str(s[1]))
    url = node.findAll('a')[0]['href']


    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s"%(name,url,desc,synopsis,desc)
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,conn.escape_string(desc),conn.escape_string(synopsis),'','stuntsnippets','')

########NEW FILE########
__FILENAME__ = parse_emacs
from BeautifulSoup import BeautifulSoup
import re
import os
import sys


openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

files.append('./docs/emacs.txt')

for file in files:
  for line in open(file):
    for command in line.split("\t"):
      if command.strip() != '':
        desc = command.strip().split(' ')[-1:][0]
        synopsis = ' '.join(command.strip().split(' ')[:-1])
        name = command.strip()
        url = ''
        namespace = ''

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','emacs','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name.replace("'","''"),namespace,url,desc.replace("'","''"),synopsis.replace("'","''"),'','emacs','')

########NEW FILE########
__FILENAME__ = parse_fossil
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

def findindex(t,find):
  count = 0
  for i in t:
    if find in i:
      return count
    count +=1
  return -1

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/fossil/'):
  files.append('./docs/fossil/%s'%(file))


for file in files:
  filecontents = open(file).read()
  

  soup = BeautifulSoup(filecontents)
  
  name = str(soup.findAll('h1')[0]).replace('<h1>The "','').replace('" command:</h1>','')
  url = "http://www.fossil-scm.org/index.html/help?cmd=%s"%(name)
  description = ''
  t = openclosetags.sub('',str(soup.findAll('pre')[0])).split("\n")
  synopsis = t[findindex(t,'Usage: ')].replace('Usage: ','')
  if synopsis == '':
    synopsis = (''.join(t[0:2])).strip()
  
  for i in range(3,len(t)):
    if t[i] == '' and i != 3:
      description = (' '.join(t[3:i])).strip()
      break

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,description.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','fossil','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name.replace("'","''"),'',url,description.replace("'","''"),synopsis.replace("'","''"),'','fossil','en')

########NEW FILE########
__FILENAME__ = parse_freebsdman
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

def findindex(haystack,needle):
  count = 0
  for line in haystack:
    if needle in line:
      return count
    count += 1

def getsection(file,start,end):
  html = ''
  for i in file[start:end]:
    html = "%s\r\n%s"%(html,i)
  return html.strip()

def getall(file):
  html = ''
  for i in file:
    html = "%s\r\n%s"%(html,i)
  return html


openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/freebsdman/'):
  #if "git" in file:
  files.append('./docs/freebsdman/%s'%(file))


for file in files:
  filecontents = open(file).read()
  soup = BeautifulSoup(filecontents)


  lines = []
  if len(soup.findAll('pre')) == 0:
    continue
  for line in str(soup.findAll('pre')[0]).split("\n"):
    lines.append(line.replace("'",""))

  name = ''.join(openclosetags.sub('',getsection(lines,findindex(lines,'NAME'),findindex(lines,'SYNOPSIS'))).split("\n")[1:]).replace('...','').strip()
  name = name.replace("\r\n"," ")
  synopsis = openclosetags.sub('',getsection(lines,findindex(lines,'SYNOPSIS'),findindex(lines,'DESCRIPTION')))
  synopsis = synopsis.replace("\r\n","\n").replace("'","\'").replace("SYNOPSIS","")
  desc = openclosetags.sub('',getsection(lines,findindex(lines,'DESCRIPTION'),findindex(lines,'AUTHOR')))
  desc = "%s..."%(desc.replace("\r\n","\n").replace("'","\'").replace("DESCRIPTION","")[:850])
  url = "http://www.freebsd.org/cgi/%s"%(file.replace('./docs/freebsdman/',''))

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','freebsdman','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'freebsd man bsd','freebsdman','en')


########NEW FILE########
__FILENAME__ = parse_ftpcode
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

files = []
files.append('./docs/ftpcode.html')

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

for file in files:
  filecontents = ''
  for line in open(file):
    line = line.replace("'","\\'").strip()
    filecontents = '%s %s'%(filecontents,line)

  soup = BeautifulSoup(filecontents)
  for trtag in soup.findAll('tr'):
    td = trtag.findAll('td')
    if len(td) != 0:
      name = td[0].findAll('code')[0].string
      desc = openclosetags.sub('',str(td[1])).strip()

      url = 'http://en.wikipedia.org/wiki/List_of_FTP_server_return_codes'

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','ftpcode','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, 

`lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','ftpcode','en')


########NEW FILE########
__FILENAME__ = parse_git
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)


files = []

for file in os.listdir('./docs/git/html/'):
  if 'git-' in file and '.html' in file:
    files.append('./docs/git/html/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)
  
  t = soup.findAll(attrs={"class" : "sectionbody"})

  searchname = file.replace('./docs/git/html/','').replace('.html','').replace('-',' ')

  url = "http://schacon.github.com/git/%s"%(file.replace('./docs/git/html/',''))

  name = str(t[0])
  name = openclosep.sub('',openclosediv.sub('',name)).strip()

  synopsis = str(t[1])
  synopsis = openclosep.sub('',openclosediv.sub('',synopsis)).strip()

  description = str(t[2])
  description = openclosett.sub('',opencloseh3.sub('',openclosep.sub('',openclosediv.sub('',description)))).strip()
  description = description.replace('''<a href="''','''<a href="http://www.kernel.org/pub/software/scm/git/docs/''')

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(searchname,'',url,description.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','git','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(searchname,'',url,name,synopsis,description,'git','en')

########NEW FILE########
__FILENAME__ = parse_gwt
import os
import re
from BeautifulSoup import BeautifulSoup
import sys
import string

def findindex(haystack,needle):
  count = 0
  for line in haystack:
    if needle in line:
      return count
    count += 1

def getsection(file,start,end):
  html = ''
  for i in file[start:end]:
    html = "%s\r\n%s"%(html,i)
  return html

def getall(file):
  html = ''
  for i in file:
    html = "%s\r\n%s"%(html,i)
  return html

r1 = re.compile('''<.*?>''',re.DOTALL)
findtr = re.compile('''<TR .*?>.*?</TR>''',re.DOTALL)
findtd = re.compile('''<TD>.*?</TD>''',re.DOTALL)
findtable = re.compile('''<TABLE .*?</TABLE>''',re.DOTALL)
findp = re.compile('''<P>.*?<P>''',re.DOTALL)
findpre = re.compile('''<PRE>.*?</PRE>''',re.DOTALL)
findh2 = re.compile('''<H2>.*?</H2>''',re.DOTALL)
findh3 = re.compile('''<H3>.*?</H3>''',re.DOTALL)
findcode = re.compile('''<code>.*?</code>''',re.DOTALL)
findcodeupper = re.compile('''<CODE>.*?</CODE>''',re.DOTALL)
findmethoddetail = re.compile('''<A NAME.*?<HR>''',re.DOTALL)
finda = re.compile('''<A NAME.*?>''',re.DOTALL)
findb = re.compile('''<B>.*?</B>''',re.DOTALL)
findddtop = re.compile('''<DD.*?<P>''',re.DOTALL)
findinherit = re.compile('''<B>Methods inherited from.*?</TABLE>''',re.DOTALL)
findopenclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

# java javax and org


#get all the files here
dirList = []


dir = "./docs/gwt/javadoc/com/google/gwt/"

for (path,dirs,files) in os.walk(dir):
  if 'class-use' not in path:
    for f in files:
      dirList.append("%s/%s"%(path,f))

 


first = True

for fname in dirList:
  file = []

  #if fname == 'XmlAnyElement.html':
  #if fname  == 'RandomAccess.html': # interface
  if fname.endswith('.html') and 'package-' not in fname and 'doc-files' not in fname:
    for line in open("%s"%(fname)):
      line = line.strip().replace("'",'')
      line = ''.join(filter(lambda x:x in string.printable, line))
      file.append(line)

    start   = findindex(file,"START OF CLASS DATA")
    consum  = findindex(file,"CONSTRUCTOR SUMMARY")
    methsum = findindex(file,"METHOD SUMMARY")
    condet  = findindex(file,"CONSTRUCTOR DETAIL")
    methdet = findindex(file,"METHOD DETAIL")
    end     = findindex(file,"END OF CLASS DATA")

    #finds the name and namespace
    np = findh2.findall(getall(file))[0]
    np = np.split('<BR>')
    namespace = r1.sub('',np[0]).strip()
    classtype = r1.sub('',np[1]).strip()

    #if its an interface skip it
    if 'interface' in classtype.lower():
      continue

    #finds the description which is the large text at the beginning
    desc = findp.findall(getall(file))[0]

    # print the object

    name = fname.split('/')[-1].replace('.html','')
    url = "http://download.oracle.com/javase/6/docs/%s"%(fname.replace('./docs/java/en/',''))
    description = spaces.sub(' ',findopenclosetags.sub('',desc).strip())

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url,description,'','','gwt','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,description,'','','gwt','en')

    #finds all inherited methods
    for i in findinherit.findall(getall(file)):
      description = spaces.sub(' ',findopenclosetags.sub('',findb.findall(i)[0].replace('Methods','Method').replace('<B>','').replace('</B>','')))
      #print detail
      for j in findcodeupper.findall(i)[0].replace('<CODE>','').replace('</CODE>','').split('>, '):
        #synopsis = j.strip().replace('</A','</A>').replace('>>','>')
        synopsis = ''
        methodname =  r1.sub('',j).replace('</A','').strip()
        url = 'http://download.oracle.com/javase/6/docs/%s#%s'%(fname.replace('./docs/java/en/',''),methodname)
        namespaceinherited = "%s.%s"%(namespace,name)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methodname,namespaceinherited,url,description,synopsis,'','gwt','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methodname,namespaceinherited,url,description,synopsis,'','gwt','en')


    #finds all methoddetailinfo
    for meth in findmethoddetail.findall("%s<HR>"%(findtable.sub('',getsection(file,methdet,end)).replace('<A NAME="method_detail"><!-- --></A>',''))):
      try:
        methodname = r1.sub('',findh3.findall(meth)[0]).strip()
        methodurl = finda.findall(meth)[0]
        methodurl = methodurl.replace('<A NAME="','').replace('">','')
        url = 'http://download.oracle.com/javase/6/docs/%s#%s'%(fname.replace('./docs/java/en/',''),methodurl)
        synopsis = findopenclosetags.sub('',findpre.findall(meth)[0].replace('<PRE>','').replace('</PRE>','').replace("\r\n",'').strip())
        description = spaces.sub(' ',findopenclosetags.sub('',findddtop.findall(meth)[0].replace('<DD>','').replace('<P>','')))
        namespaceinherited = "%s.%s"%(namespace,name)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methodname,namespaceinherited,url,description,synopsis,'','gwt','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methodname,namespaceinherited,url,description,synopsis,'','gwt','en')
      except:
        pass

########NEW FILE########
__FILENAME__ = parse_helloworld
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)
badtags = re.compile('''<p.*>|</p>|<b.*>.*</b>|<code.*>.*</code>|<span.*>.*</span>|<.*?>|</.*?>''')
spaces = re.compile('''\s+''',re.DOTALL)

files = []

files.append('./docs/helloworld.html')


for file in files:
	filecontents = open(file).read()
	soup = BeautifulSoup(filecontents)
	for s in soup.findAll('a'):
		
		if 'table' in str(s):
		
			name = openclosetags.sub('',str(s.findAll('h2')[0])).replace("'","''")
			synopsis = ''
			description = ''
			
			try:
				synopsis = openclosetags.sub('',str(s.findNextSiblings('pre')[0])).replace("'","''")
			except:
				try:
					description = str(s.findNextSiblings('p')[0]).replace("'","''")
				except:
					if name == 'Piet':
						description = '<img src="http://helloworldsite.he.funpic.de/hellopics/piet.png">'
				
			url = "http://helloworldsite.he.funpic.de/hello.htm#%s"%(name)
			
			if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
				print "%s\t%s\t%s\t%s\t%s"%(name,'',url,description,synopsis)
			if sys.argv[1].lower() == 'sql':
				print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,description,synopsis,'hello world helloworld hw','helloworld','en')
			

########NEW FILE########
__FILENAME__ = parse_hresult
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)


files = []

files.append('./docs/microsoft/hresult.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)
  t = soup.findAll(attrs={"class":"FixedWidth-40-60"})
  for i in t[0].findAll("tr"):
    j = i.findAll("td")
    if len(j) != 0:
      name1 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[0]
      name2 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[1]
      name = "%s %s"%(name1,name2)
      desc = openclosetags.sub(' ',str(j[1])).strip()

      url = '''http://msdn.microsoft.com/en-us/library/cc704587%28v=PROT.10%29.aspx'''

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','hresult','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','hresult','en')

########NEW FILE########
__FILENAME__ = parse_html
from BeautifulSoup import BeautifulSoup
import re
import os
import sys


openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/html/'):
  files.append('./docs/html/%s'%(file))

  #id class style

for file in files:
  filecontents = open(file).read()
  
  soup = BeautifulSoup(filecontents)
  
  name = openclosetags.sub('',str(soup.findAll("h1")[0]))
  namespace = ''
  synopsis = openclosetags.sub('',str(soup.findAll("table")[0].findAll('td')[0]))
  synopsis += "\r\n\r\nAttributes"
  
  for li in soup.findAll('ul')[0].findAll('li'):
    li = openclosetags.sub('',str(li))
    if li != "common attributes":
      synopsis += "\r\n" + li
    else:
      synopsis += "\r\nID" 
      synopsis += "\r\nCLASS" 
      synopsis += "\r\nSTYLE" 
  desc =  openclosetags.sub('',str(soup.findAll("p")[0]))
  
 
  url = "http://www.htmlhelp.com/reference/html40/%s"%(file.replace('./docs/html/',''))

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s"%(name,url,desc,synopsis,desc)
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,desc.replace("'","''"),synopsis.replace("'","''"),'','html','')

########NEW FILE########
__FILENAME__ = parse_httpcode
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

files = []
files.append('./docs/httpcode')


for file in files:
  lines = []
  for line in open(file):
    line = line.replace("'","\\'")
    lines.append(line.strip())

  for i in range(len(lines)-1):
    if i%2 ==0:
      name = lines[i]
      desc = lines[i+1]

      url = 'http://en.wikipedia.org/wiki/List_of_HTTP_status_codes'

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','httpcode','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, 

`lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','httpcode','en')


########NEW FILE########
__FILENAME__ = parse_java
import os
import re
from BeautifulSoup import BeautifulSoup
import sys
import string

def findindex(haystack,needle):
  count = 0
  for line in haystack:
    if needle in line:
      return count
    count += 1

def getsection(file,start,end):
  html = ''
  for i in file[start:end]:
    html = "%s\r\n%s"%(html,i)
  return html

def getall(file):
  html = ''
  for i in file:
    html = "%s\r\n%s"%(html,i)
  return html

r1 = re.compile('''<.*?>''',re.DOTALL)
findtr = re.compile('''<TR .*?>.*?</TR>''',re.DOTALL)
findtd = re.compile('''<TD>.*?</TD>''',re.DOTALL)
findtable = re.compile('''<TABLE .*?</TABLE>''',re.DOTALL)
findp = re.compile('''<P>.*?<P>''',re.DOTALL)
findpre = re.compile('''<PRE>.*?</PRE>''',re.DOTALL)
findh2 = re.compile('''<H2>.*?</H2>''',re.DOTALL)
findh3 = re.compile('''<H3>.*?</H3>''',re.DOTALL)
findcode = re.compile('''<code>.*?</code>''',re.DOTALL)
findcodeupper = re.compile('''<CODE>.*?</CODE>''',re.DOTALL)
findmethoddetail = re.compile('''<A NAME.*?<HR>''',re.DOTALL)
finda = re.compile('''<A NAME.*?>''',re.DOTALL)
findb = re.compile('''<B>.*?</B>''',re.DOTALL)
findddtop = re.compile('''<DD.*?<P>''',re.DOTALL)
findinherit = re.compile('''<B>Methods inherited from.*?</TABLE>''',re.DOTALL)
findopenclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

# java javax and org


#get all the files here
dirList = []


dir = "./docs/java/en/api/java/"

for (path,dirs,files) in os.walk(dir):
  if 'class-use' not in path:
    for f in files:
      dirList.append("%s/%s"%(path,f))

dir = "./docs/java/en/api/javax/"

for (path,dirs,files) in os.walk(dir):
  if 'class-use' not in path:
    for f in files:
      dirList.append("%s/%s"%(path,f))
  


first = True

for fname in dirList:
  file = []

  #if fname == 'XmlAnyElement.html':
  #if fname  == 'RandomAccess.html': # interface
  if fname.endswith('.html') and 'package-' not in fname and 'doc-files' not in fname:
    for line in open("%s"%(fname)):
      line = line.strip().replace("'",'')
      line = ''.join(filter(lambda x:x in string.printable, line))
      file.append(line)

    start   = findindex(file,"START OF CLASS DATA")
    consum  = findindex(file,"CONSTRUCTOR SUMMARY")
    methsum = findindex(file,"METHOD SUMMARY")
    condet  = findindex(file,"CONSTRUCTOR DETAIL")
    methdet = findindex(file,"METHOD DETAIL")
    end     = findindex(file,"END OF CLASS DATA")

    #finds the name and namespace
    np = findh2.findall(getall(file))[0]
    np = np.split('<BR>')
    namespace = r1.sub('',np[0]).strip()
    classtype = r1.sub('',np[1]).strip()

    #if its an interface skip it
    if 'interface' in classtype.lower():
      continue

    #finds the description which is the large text at the beginning
    desc = findp.findall(getall(file))[0]

    # print the object

    name = fname.split('/')[-1].replace('.html','')
    url = "http://download.oracle.com/javase/6/docs/%s"%(fname.replace('./docs/java/en/',''))
    description = spaces.sub(' ',findopenclosetags.sub('',desc).strip())

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,namespace,url,description,'','','java','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,namespace,url,description,'','','java','en')

    #finds all inherited methods
    for i in findinherit.findall(getall(file)):
      description = spaces.sub(' ',findopenclosetags.sub('',findb.findall(i)[0].replace('Methods','Method').replace('<B>','').replace('</B>','')))
      #print detail
      for j in findcodeupper.findall(i)[0].replace('<CODE>','').replace('</CODE>','').split('>, '):
        #synopsis = j.strip().replace('</A','</A>').replace('>>','>')
        synopsis = ''
        methodname =  r1.sub('',j).replace('</A','').strip()
        url = 'http://download.oracle.com/javase/6/docs/%s#%s'%(fname.replace('./docs/java/en/',''),methodname)
        namespaceinherited = "%s.%s"%(namespace,name)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methodname,namespaceinherited,url,description,synopsis,'','java','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methodname,namespaceinherited,url,description,synopsis,'','java','en')


    #finds all methoddetailinfo
    for meth in findmethoddetail.findall("%s<HR>"%(findtable.sub('',getsection(file,methdet,end)).replace('<A NAME="method_detail"><!-- --></A>',''))):
      try:
        methodname = r1.sub('',findh3.findall(meth)[0]).strip()
        methodurl = finda.findall(meth)[0]
        methodurl = methodurl.replace('<A NAME="','').replace('">','')
        url = 'http://download.oracle.com/javase/6/docs/%s#%s'%(fname.replace('./docs/java/en/',''),methodurl)
        synopsis = findopenclosetags.sub('',findpre.findall(meth)[0].replace('<PRE>','').replace('</PRE>','').replace("\r\n",'').strip())
        description = spaces.sub(' ',findopenclosetags.sub('',findddtop.findall(meth)[0].replace('<DD>','').replace('<P>','')))
        namespaceinherited = "%s.%s"%(namespace,name)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methodname,namespaceinherited,url,description,synopsis,'','java','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methodname,namespaceinherited,url,description,synopsis,'','java','en')
      except:
        pass

########NEW FILE########
__FILENAME__ = parse_javascript
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import urllib2

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/javascript/'):
  if '.asp' in file:
    files.append('./docs/javascript/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"style":"background-color:#ffffff;color:#000000;padding-bottom:8px;padding-right:5px"})

  url = "http://www.w3schools.com/jsref/%s"%(file.replace('./docs/javascript/',''))
  name = t[0].findAll("h2")[0].string.split(' ')[0]
  desc = t[0].findAll("p")[0].string

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','javascript','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','javascript','en')


  for table in soup.findAll(attrs={"class":"reference"}):
    for tr in table.findAll("tr"):
      td = tr.findAll("td")
      if len(td) != 0:
        try:
          one = td[0].findAll('a')[0]
          namespace = name
          methname = one.string.replace('()','')
          url = "http://www.w3schools.com/jsref/%s"%( one['href'])
          desc = td[1].string

          opener = urllib2.build_opener()
          url_opener = opener.open(url)
          page = url_opener.read()
          soup2 = BeautifulSoup(page)
          synopsis = openclosetags.sub('',str(soup2.findAll(attrs={"class":"code notranslate"})[0])).strip()

          if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
            print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methname,namespace,url,desc,synopsis,'','javascript','en')
          if sys.argv[1].lower() == 'sql':
            print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methname,namespace,url,desc,synopsis,'','javascript','en')
        except:
          pass

########NEW FILE########
__FILENAME__ = parse_javascript2
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import urllib2

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/javascript/'):
  if '.asp' in file:
    files.append('./docs/javascript/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"style":"background-color:#ffffff;color:#000000;padding-bottom:8px;padding-right:5px"})

  url = "http://www.w3schools.com/jsref/%s"%(file.replace('./docs/javascript/',''))
  name = t[0].findAll("h2")[0].string.split(' ')[0]
  desc = t[0].findAll("p")[0].string

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','javascript','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','javascript','en')


  for table in soup.findAll(attrs={"class":"reference"}):
    for tr in table.findAll("tr"):
      td = tr.findAll("td")
      if len(td) != 0:
        try:
          one = td[0].findAll('a')[0]
          namespace = name
          methname = one.string.replace('()','')
          url = "http://www.w3schools.com/jsref/%s"%( one['href'])
          desc = td[1].string

          opener = urllib2.build_opener()
          url_opener = opener.open(url)
          page = url_opener.read()
          soup2 = BeautifulSoup(page)
          synopsis = openclosetags.sub('',str(soup2.findAll(attrs={"class":"code notranslate"})[0])).strip()

          if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
            print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(methname,namespace,url,desc,synopsis,'','javascript','en')
          if sys.argv[1].lower() == 'sql':
            print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(methname,namespace,url,desc,synopsis,'','javascript','en')
        except:
          pass

########NEW FILE########
__FILENAME__ = parse_jquery
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
findjqueryscript = re.compile('''&lt;script&gt;.*?&lt;/script&gt;''',re.DOTALL)

files = []

for file in os.listdir('./docs/jquery/'):
  files.append('./docs/jquery/%s'%(file))

for file in files:
  filecontents = ''
  filecontents = open(file).read()
  filecontents = ''.join(filter(lambda x:x in string.printable, filecontents))


  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"class":"entry-content"})
  if len(t) == 0:
    #print file # dont want these ones
    continue

  t = t[0]

  name = t.findAll('h1')[0].string

  desc = openclosetags.sub('',str(t.findAll(attrs={"class":"desc"})[0]).replace("<strong>Description: </strong>",""))
  try:
    desc = "%s %s"%(desc,openclosetags.sub('',str(t.findAll(attrs={"class":"longdesc"})[0].findAll('p')[0])))
  except:
    pass

  synopsis = ''
  try:
    synopsis = openclosetags.sub('',str(t.findAll(attrs={"id":"example-0"})[0].findAll('pre')[0]))
    synopsis = findjqueryscript.findall(synopsis)[0]
  except:
    pass

  url = "http://api.jquery.com/%s/"%(file.replace("./docs/jquery/","").replace(".html","").replace(".htm",""))
  

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc.replace("\n","__NEWLINE__").replace("\r\n","__NEWLINE__").replace("\t","    "),synopsis.replace("'","''").replace("\n","__NEWLINE__").replace("\r\n","__NEWLINE__").replace("\t","    "),'','jquery','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc.replace("'","''"),synopsis.replace("'","''"),'','jquery','en')

########NEW FILE########
__FILENAME__ = parse_linuxcommand
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
openclosetagsem = re.compile('''<.[^em]*?>|</.[^em]*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/linuxcommand/'):
  files.append('./docs/linuxcommand/%s'%(file))



for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"id":"commanddirectory"})[0]

  name = t.findAll('h2')[0].string
  syn = t.findAll('p')
  synopsis =  openclosetagsem.sub('',str(syn[0])).strip()
  desc = openclosetags.sub('',str(syn[1])).strip()

  opt = t.findAll('variablelist')
  if len(opt) != 0:
    term = opt[0].findAll('term')
    options = ' '.join(map(lambda x:openclosetags.sub('',str(x)), term))
    synopsis = "%s [Options: %s]"%(synopsis,options)


  url = "http://oreilly.com/linux/command-directory/cmd.csp?path=%s/%s"%(name[0],name.replace('+','%2B'))


  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','linuxcommand','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'','linuxcommand','en')
########NEW FILE########
__FILENAME__ = parse_linuxkernelheader
import re
import os
import sys

files = []

files.append('./docs/linuxkernelerror/errorno.h')

for file in files:
  filecontents = ''
  for line in open(file):
    line = line.strip()

    t = line.split("\t")
    if len(t) == 5:
      searchname = t[1]
      url = 'http://sysinf0.klabs.be/usr/include/asm-generic/errno.h'
      name = "%s - %s"%(t[3],t[4].replace('/* ','').replace(' */',''))
      synopsis = ''
      description = ''

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(searchname,'',url,name.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','linuxkernelheader','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(searchname,'',url,name,synopsis,description,'linuxkernelerror','')

files = []
files.append('./docs/linuxkernelerror/errorno-base.h')


for file in files:
  filecontents = ''
  for line in open(file):
    line = line.strip()

    t = line.split("\t")
    if len(t) == 5:
      searchname = t[1]
      url = 'http://sysinf0.klabs.be/usr/include/asm-generic/errno-base.h'
      name = "%s - %s"%(t[3],t[4].replace('/* ','').replace(' */',''))
      synopsis = ''
      description = ''

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(searchname,'',url,name.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','linuxkernelheader','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(searchname,'',url,name,synopsis,description,'linuxkernelerror','')

########NEW FILE########
__FILENAME__ = parse_mercurial
from BeautifulSoup import BeautifulSoup
import re
import os
import sys


replaceopenclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
replaceopenclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
replaceopencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
replaceopenclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

findopenclosediv = re.compile('''<div.*?</div>''')

findopenclosetag = re.compile('''<.*?>|</.*?>''',re.DOTALL)


files = []

files.append('./docs/mercurial/hg.1.html')
#files.append('./hg.1.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'",'')

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"id" : "commands"})

  for i in t[0].findAll('div'):
    searchname = None
    if len(i.findAll('h2')) != 0:
      searchname = "hg %s"%(i.findAll('h2')[0].string)
      url = "http://www.selenic.com/mercurial/hg.1.html#%s"%(searchname)
    if len(i.findAll('pre')) != 0:
      synopsis = i.findAll('pre')[0].string.strip()
    if len(i.findAll('p')) != 0:
      description = i.findAll('p')[0].string

    option = ""
    if len(i.findAll(attrs={"class" : "docutils option-list"})) != 0:
      for tr in i.findAll(attrs={"class" : "docutils option-list"})[0].findAll('tr'):
        span = tr.findAll('td')[0].findAll('span')
        if len(span) >= 1:
          option = "%s %s"%(option,span[0].string)
        if len(span) == 2:
          option = "%s %s"%(option,span[1].string)

    if option != "":
      synopsis = "%s [Options: %s]"%(synopsis,option)

    if searchname != None:
      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(searchname,'',url,searchname,synopsis,description,'mercurial','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(searchname,'',url,description,synopsis,description,'mercurial','')


########NEW FILE########
__FILENAME__ = parse_mysqlerror
from BeautifulSoup import BeautifulSoup
import re
import os
import sys


openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)


files = []

files.append('./docs/mysql/error.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)
  t = soup.findAll(attrs={"class":"itemizedlist"})
  for i in t[2].findAll("li"):

    p = i.findAll('p')
    name = openclosetags.sub('',str(p[0])).strip()
    desc = openclosetags.sub('',str(p[1])).strip()
    url = "http://dev.mysql.com/doc/refman/5.5/en/%s"%(i.findAll('a')[1]['href'])

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','mysqlerror','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,'','','mysqlerror','en')

########NEW FILE########
__FILENAME__ = parse_mysqlfunction
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosediv = re.compile('''<div class="itemizedlist">.*?</div>|<div class="orderedlist">.*?</div>''',re.DOTALL)
openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/mysql/functions/'):
  if 'functions' in file and '.html' in file:
    files.append('./docs/mysql/functions/%s'%(file))

for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"class" : "itemizedlist"})[0]
  t = openclosediv.sub('',str(t.contents[0]))
  t = BeautifulSoup(t)

  for li in t.findAll('li'):
    name = openclosetags.sub('',str(li.findAll('p')[0])).strip()
    desc = openclosetags.sub('',str(li.findAll('p')[1])).strip()
    synopsis = ''
    for a in li.findAll('a'):
      try:
        url = a['href']
        break
      except:
        pass
      

    pre = li.findAll('pre')
    if len(pre) != 0:
      synopsis = openclosetags.sub('',str(pre[0])).replace('mysql&gt;',"\r\nmysql>").replace('','').strip()


    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis.replace("\r\n","__NEWLINE__"),'','mysqlfunction','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name.replace("'","\\'").replace("\\\\","\\"),'',url,desc.replace("'","\\'").replace("\\\\","\\"),synopsis.replace("'","\\'").replace("\\\\","\\"),'','mysqlfunction','en')

########NEW FILE########
__FILENAME__ = parse_nginxcore
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

files.append('./docs/NginxHttpCoreModule.htm')
#files.append('./NginxHttpCoreModule.htm')

def geth2locations(filecontents):
  ret = []
  count = 0
  for x in filecontents:
    count += 1
    if 'h2' in x:
      ret.append(count)
  ret.append(count)
  return ret

for file in files:
  filecontents = []
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents.append(line.strip())
  
  contents = geth2locations(filecontents)
  for x in range(len(contents)-1):
    name = ''
    synopsis = ''
    description = ''
    soup = BeautifulSoup(''.join(filecontents[contents[x]-1:contents[x+1]-1]))
    h2 = soup.findAll('h2')
    if len(h2) != 0:
      name = openclosetags.sub('',str(h2[0])).strip()
    ps = soup.findAll('p')
    if '$' in name:
      description = openclosetags.sub('',str(ps[0]))
    else:
      for p in ps:
        if '<b>' in str(p):
          synopsis = '%s<br>%s'%(synopsis,openclosetags.sub('',str(p)))
        else:
          description = openclosetags.sub('',str(p))
          break
    url = 'http://wiki.nginx.org/NginxHttpCoreModule#%s'%(name.replace('$','.24'))
    if name != '':
      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,description,synopsis[4:],'','nginxcoremodule','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,description.replace("'","\\'"),synopsis.replace("'","\\'"),'nginx core module','nginxcoremodule','en')

########NEW FILE########
__FILENAME__ = parse_nodejs
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import MySQLdb


def getall(soup):
  s = soup.nextSibling
  if s != None and '<h3' not in str(s):
    print ' '.join([str(s),getall(s)])
  return ''


conn = MySQLdb.connect(user='root')

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/nodejs/'):
  files.append('./docs/nodejs/%s'%(file))


for file in files:
  if 'buffers' not in file:
    continue
  filecontents = open(file).read()
  
  soup = BeautifulSoup(filecontents)
  
  for node in soup.findAll("h3"):
    print "=================================================="
    print openclosetags.sub('',str(node))
    #print node.next.next.next.next.next
    print getall(node)
    #print node.nextSibling.nextSibling.nextSibling.nextSibling.nextSibling.nextSibling
    continue
    name = openclosetags.sub('',str(node.findAll("div","post-title")[0]))
    desc = openclosetags.sub('',str(node.findAll("div","p-con")[0].findAll('p')[0]))
    s = node.findAll("div","wp_syntax")[0].findAll('pre')
    synopsis = ''
    if len(s) == 1:
        synopsis = openclosetags.sub('',str(s[0]))
    else:
        synopsis = openclosetags.sub('',str(s[1]))
    url = node.findAll('a')[0]['href']


    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s"%(name,url,desc,synopsis,desc)
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,conn.escape_string(desc),conn.escape_string(synopsis),'','stuntsnippets','')

########NEW FILE########
__FILENAME__ = parse_ntstatus
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)


files = []

files.append('./docs/microsoft/ntstatus.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)
  t = soup.findAll(attrs={"class":"FixedWidth-40-60"})
  for i in t[0].findAll("tr"):
    j = i.findAll("td")
    if len(j) != 0:
      name1 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[0]
      name2 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[1]
      desc = openclosetags.sub(' ',str(j[1])).strip()

      url = '''http://msdn.microsoft.com/en-us/library/cc704588%28v=PROT.10%29.aspx'''

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name1,'',url,desc,'','','ntstatus','en')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name2,'',url,desc,'','','ntstatus','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name1,'',url,desc,'','','ntstatus','en')
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name2,'',url,desc,'','','ntstatus','en')


########NEW FILE########
__FILENAME__ = parse_perl
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/perl/functions/'):
#  if file == 'abs.html':
  files.append('./docs/perl/functions/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"id" : "content_body"})
  name = t[0].findAll('h1')[0].string

  syn = t[0].findAll('ul')
  synopsis = syn[0].findAll('b')[0].string
  if len(syn) == 2:
    for b in syn[1].findAll('b'):
      synopsis = "%s\r\n%s"%(synopsis,b.string)

  for ul in t[0].findAll('ul'):
    for p in ul.findAll('p'):
      if openclosetags.sub('',str(p)).strip() != '':
        desc = openclosetags.sub('',str(p)).strip()
        if desc[-1] == ':':
          desc = "%s..."%(desc[:-1])
        break
  url = 'http://perldoc.perl.org/%s'%(file.replace('./docs/perl/',''))

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','perl5','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,filecontents,'perl5','en')

########NEW FILE########
__FILENAME__ = parse_perlvars
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []

for file in os.listdir('./docs/perl/perlvar/'):
  if '.html' in file:
    files.append('./docs/perl/perlvar/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  for ul in soup.findAll("ul"):
    prevnames = []
    for li in ul.findAll('li',recursive=False):
      b = li.findAll('b')
      p = li.findAll('p')
      pre = li.findAll('pre')
      name = openclosetags.sub('',str(b[0]))
      synopsis = ""
      if len(p) == 0:
        prevnames.append(name)
      else:
        desc = openclosetags.sub('',str(p[0]))
        if len(pre) != 0:
          for l in pre[0].findAll('li'):
            synopsis = "%s\r\nb%s"%(synopsis,openclosetags.sub('',str(l)).strip())
        synopsis = synopsis.strip()
        synopsis = synopsis.replace("\r\n","\n")

        url = "http://perldoc.perl.org/perlvar.html#%s"%(li.findAll('a')[0]['name'])
        url = url.replace("\\","\\\\")
        prevnames.append(name)
        for name in prevnames:
          if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
            print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis.replace("\r\n","__NEWLINE__"),'','perl5var','en')

        if sys.argv[1].lower() == 'sql':
          name = ' '.join(prevnames)
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'','perl5var','en')
        prevnames = []


########NEW FILE########
__FILENAME__ = parse_phpcontrol
import os
import re
import codecs
import sys

r = re.compile('''<p class="simpara">.*?</p>''')
r3 = re.compile('''<p class="para">.*?</p>''')
r4 = re.compile('''<div class="cdata">.*?</div>''')
r5 = re.compile('''<div class="methodsynopsis dc-description">.*?</div>''')
r2 = re.compile('''<.*?>''')


first = True

#langs = ['de','en','es','fa','fr','ja','pl','pt','ro','tr']
langs = ['en']

for lang in langs:
  dirList=os.listdir("./docs/phpapi/%s/"%(lang))
  for fname in dirList:
    if fname.startswith('function.') or fname == 'images':
      pass
    else:
      filelines = ''
      name = ''
      description = ''
      synopsis = ''
      for line in codecs.open("./docs/phpapi/%s/%s"%(lang,fname)):
        line = line.replace("'","")
        line = line.strip()
        if '<title>' in line:
          name = line.replace('<title>','').replace('</title>','').strip()
          name = r2.sub('',name).strip()

        filelines = "%s%s"%(filelines,line)
      t = r.findall(filelines)
      if len(t) != 0:
        description = t[0].replace('<p class="simpara">','').replace('</p>','')
      else:
        t = r3.findall(filelines)
        if len(t) != 0:
          description = t[0].replace('<p class="para">','').replace('</p>','')
    
    
      t = r5.findall(filelines)
      if len(t) != 0:
        synopsis = t[0].replace('<div class="cdata">','').replace('</div>','').replace('<pre>','').replace('</pre>','')
      else:
        t = r4.findall(filelines)
        if len(t) != 0:
          synopsis = t[0].replace('<div class="cdata">','').replace('</div>','').replace('<pre>','').replace('</pre>','')

      if 'foreach' in fname or 'while' in fname or 'for' in fname or 'declare' in fname:
        synopsis = synopsis
      else:
        synopsis = ''

      fname = "%s.php"%(fname[:-5])
      toprint = ''

      description = description.replace('<code>','<pre>').replace('</code>','</pre>')
      url = 'http://www.php.net/manual/en/%s'%(fname)

      if 'control-structures' in fname and fname != 'language.control-structures.php' and fname != 'control-structures.intro.php':
        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,description,synopsis,filelines,'php','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,description,synopsis,name.replace('_',' '),'php','en')


########NEW FILE########
__FILENAME__ = parse_phpfunction
import os
import re
import codecs
import sys


r = re.compile('''<div class="methodsynopsis dc-description">.*?</div>''')
r2 = re.compile('''<.*?>''')
r3 = re.compile('''<div class="refsect1 parameters">.*?</div>''')
r4 = re.compile('''<div class="refsect1 returnvalues">.*?</div>''')
r5 = re.compile('''<p class="simpara">.*?</p>''')
r6 = re.compile('''<p class="para">.*?</p>''')
r7 = re.compile('''<p class="verinfo">.*?<p class="refpurpose">.*?</p>''')


repdiv = re.compile('''<div.*?>''')
repdivc = re.compile('''</div>''')
repspan = re.compile('''<span.*?>''')
repspanc = re.compile('''</span>''')
reptt = re.compile('''<tt.*?>''')
repttc = re.compile('''</tt>''')
repspace = re.compile('''\s+''')

first = True

#langs = ['de','en','es','fa','fr','ja','pl','pt','ro','tr']
langs = ['en']

for lang in langs:
  dirList=os.listdir("./docs/phpapi/%s/"%(lang))
  for fname in dirList:
    if fname.startswith('function.'):
      filelines = ''
      name = ''
      description = ''
      synopsis = ''
      param = ''
      returnval = ''
      for line in codecs.open("./docs/phpapi/%s/%s"%(lang,fname)):
        line = line.replace("'","")
        line = line.strip()
        if '<h1 class="refname"' in line:
          name = line.replace('<h1 class="refname">','').replace('</h1>','').strip()
          name = r2.sub('',name).strip()

        if name == '' and '<h2 class="title"' in line:
          name = line.replace('<h2 class="title"><span class="function"><b>','').replace('</b></span></h2>','').replace('(','').replace(')','')

        if '<p class="refpurpose">' in line:
          description = line.replace('''<p class="verinfo">''','').replace('''</p><p class="refpurpose"><span class="refname">''',' ').replace('''<span class="refname">''',' ').replace('''</span>''',' ').replace('''<span class="dc-title">''',' ').replace('''</p>''','').strip()
          description = r2.sub('',description).strip()
        filelines = "%s%s"%(filelines,line)
      t = r.findall(filelines)
      if len(t) != 0:
        synopsis = t[0]

      t = r3.findall(filelines)
      if len(t) != 0:
        param = t[0]

      t = r4.findall(filelines)
      if len(t) != 0:
        returnval = t[0]

      t = r7.findall(filelines)
      if len(t) != 0:
        description = r2.sub('',t[0]).replace(')',') ')

      fname = "%s.php"%(fname[:-5])
      if description.strip() == '':
        t = r5.findall(filelines)
        if len(t) != 0:
          description = t[0]
      if description.strip() == '':
        t = r6.findall(filelines)
        if len(t) != 0:
          description = t[0]

      synopsis = repdiv.sub(' ',synopsis)
      synopsis = repdivc.sub(' ',synopsis)
      synopsis = repspan.sub(' ',synopsis)
      synopsis = repspanc.sub(' ',synopsis)
      synopsis = reptt.sub(' ',synopsis)
      synopsis = repttc.sub(' ',synopsis)
      synopsis = repspace.sub(' ',synopsis)

      url = 'http://www.php.net/manual/en/%s'%(fname)

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,description,synopsis,filelines,'php','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,description,synopsis,name.replace('_',' '),'php','en')

########NEW FILE########
__FILENAME__ = parse_python
from BeautifulSoup import BeautifulSoup
import os
import sys
import re


ver = 'python-2.7.1-docs-html'

findp = re.compile('''(<p>.*?</p>)|(<p.id.*?</p>)''',re.DOTALL)
findallstartp = re.compile('''<p.*?>''')
findalla = re.compile('''<a.*?</a>''',re.DOTALL)

finddlfun = re.compile('''<dl class="function">.*?</dl>''',re.DOTALL)
finddt = re.compile('''<dt .*?</dt>''',re.DOTALL)
finddd = re.compile('''<dd>.*?</dd>''',re.DOTALL)

findid = re.compile('''<dt id=".*?">''',re.DOTALL)
openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

for file in os.listdir('./docs/%s/library/'%(ver)):
  if '_' not in file and '2' not in file and file != 'crypto.html' and file != 'internet.html' and file != 'profile.html':# and file == 'crypt.html':
    filecontents = ''
    for line in open('./docs/%s/library/%s'%(ver,file)):
      line = line.replace("'","")
      line = line.strip()
      filecontents = "%s %s"%(filecontents,line)

    t = findp.findall(filecontents)
    desc = ''

    if len(t) != 0:
      if len(t[0][0]) >= 50:
        desc = t[0][0]
      else:
        if len(t) == 1:
          desc = t[0][1]
        else:
          if len(t[0][1]) != 0:
            desc = t[0][1]
          else:
            desc = t[1][0]
    if desc == '':
      desc = t[1][1]
    desc = findallstartp.sub('',desc).replace('</p>','')
    desc = openclosetags.sub('',desc)

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(file[:file.rfind('.')], '', "http://docs.python.org/library/%s"%(file), desc, '', '', 'python', 'en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(file[:file.rfind('.')], '', "http://docs.python.org/library/%s"%(file), desc, '', '', 'python', 'en')


    functions = finddlfun.findall(filecontents)
    for fun in functions:
      det = ''
      ded = ''
      dt = finddt.findall(fun)
      dd = finddd.findall(fun)
      if len(dt) != 0:
        det = dt[0]
        det = findalla.sub('',det)
      if len(dd) != 0:
        ded = dd[0].replace('href="','href="http://docs.python.org/library/%s'%(file))

      t = findid.findall(det)

      if len(t) != 0:
        fname = t[0].replace('<dt id="','').replace('">','')

        name = fname.split('.')[-1]
        namespace = fname
        url = "http://docs.python.org/library/%s#%s"%(file,fname)
        synopsis = openclosetags.sub('',det).strip()
        detail = BeautifulSoup(ded)
        if len(detail.findAll('p')) != 0:
          detail = openclosetags.sub('',str(detail.findAll('p')[0]))
        else:
          detail = openclosetags.sub('',ded)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name, namespace, url, detail, synopsis, '', 'python', 'en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name, namespace, url, detail, synopsis, '', 'python', 'en')

########NEW FILE########
__FILENAME__ = parse_rfc
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)
cleaner = re.compile('\W',re.DOTALL)

files = []

for file in os.listdir('./docs/RFC-all/'):
  if '.txt' in file:
    files.append('./docs/RFC-all/%s'%(file))

for file in files:
  filecontents = open(file).read()

  name = file.replace('.txt','').split('/')[-1]
  url = 'http://tools.ietf.org/html/%s'%(name)
  name = name.upper()
  synopsis = ''
  
  split = filecontents.split("\n\n")
  split = map(lambda x: cleaner.sub(' ',x), split)
  split = map(lambda x: spaces.sub(' ',x).strip(), split)
  split = map(lambda x: x.replace('_',''),split)
  
  try:
    desc = filter(lambda x: len(x) >= 120, split)[0]
  except:
    desc = filter(lambda x: len(x) >= 0, split)[0]
  
  filecontents = spaces.sub(' ',cleaner.sub(' ',filecontents)).replace("'",'')
  
  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','rfc','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,filecontents,'rfc','en')

########NEW FILE########
__FILENAME__ = parse_ruby
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
files = []

for file in os.listdir('./docs/ruby/'):
  if '_' not in file:
    files.append('./docs/ruby/%s'%(file))

for file in files:
  filecontents = ''
  filecontents = open(file).read()
  filecontents = ''.join(filter(lambda x:x in string.printable, filecontents))


  soup = BeautifulSoup(filecontents)

  name = soup.findAll(attrs={"class":"class-name-in-header"})[0].string
  
  print file
  desc = ''
  if len(soup.findAll(attrs={"id":"description"})) != 0:
    t = soup.findAll(attrs={"id":"description"})[0].findAll('p')
    if len(str(t[0])) > 20:
      desc = openclosetags.sub('',str(t[0]))
    else:
      desc = openclosetags.sub('',str(t[1]))
  
  print desc
  print
  continue
  if len(t) == 0:
    #print file # dont want these ones
    continue

  t = t[0]

  name = t.findAll('h1')[0].string

  desc = openclosetags.sub('',str(t.findAll(attrs={"class":"desc"})[0]).replace("<strong>Description: </strong>",""))
  try:
    desc = "%s %s"%(desc,openclosetags.sub('',str(t.findAll(attrs={"class":"longdesc"})[0].findAll('p')[0])))
  except:
    pass

  synopsis = ''
  try:
    synopsis = openclosetags.sub('',str(t.findAll(attrs={"id":"example-0"})[0].findAll('pre')[0]))
    synopsis = findjqueryscript.findall(synopsis)[0]
  except:
    pass

  url = "http://api.jquery.com/%s/"%(file.replace("./docs/jquery/","").replace(".html","").replace(".htm",""))
  

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,'','','jquery','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc.replace("'","''"),synopsis.replace("'","''"),'','jquery','en')

########NEW FILE########
__FILENAME__ = parse_rubycommandoptions
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)

files = []


files.append('./docs/ruby-doc-bundle/Manual/man-1.4/options.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")


  details = []

  soup = BeautifulSoup(filecontents)

  dt = soup.findAll("dt")
  dd = soup.findAll("dd")

  previous = ''
  for i in range(len(dt)):
    name = 'ruby %s'%(openclosetags.sub('',str(dt[i])).strip())
    detail = openclosetags.sub('',str(dd[i])).strip()
    if detail == '':
      previous = name
    else:
      if previous != '':
        details.append([previous,detail])
        previous = ''
      details.append([name,detail])


  for i in details:
    url = 'http://rubysomthing.ruby/%s'%(file.replace('./docs/perl/',''))

    if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
      print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(i[0],'',url,i[1],'','','ruby','en')
    if sys.argv[1].lower() == 'sql':
      print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(i[0],'',url,i[1],'','','ruby','en')

########NEW FILE########
__FILENAME__ = parse_smarty
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/smarty/'):
  if 'language.modifier.' in file:
    files.append('./docs/smarty/%s'%(file))

'''for file in os.listdir('./docs/smarty/'):
  if 'language.function.' in file:
    files.append('./docs/smarty/%s'%(file))'''


for file in files:
  filecontents = ''
  for line in open(file):
    line = line.replace("'","\\'").replace("\\\\'","\\'")
    filecontents = "%s %s"%(filecontents,line)

  soup = BeautifulSoup(filecontents)
  name = openclosetags.sub('',str(soup.findAll('h2')[0])).strip()
  desc = openclosetags.sub('',str(soup.findAll('p')[0])).strip()

  url = "http://www.smarty.net/docs/en/%s"%(file.replace('./docs/smarty/','').replace('.html','.tpl'))

  synopsis = "%s\r\n"%(openclosetags.sub('',str(soup.findAll(attrs={"class":"programlisting"})[0])).strip())
  syn = openclosetags.sub('',str(soup.findAll(attrs={"class":"programlisting"})[1])).strip()
  syn2 = openclosetags.sub('',str(soup.findAll(attrs={"class":"screen"})[0])).strip()

  synsplit = syn.split("\n")
  synsplit2 = syn2.split("\n")

  largest = max(map(lambda x:len(x),synsplit))

  if len(synsplit) == len(synsplit2):
    for i in range(len(synsplit)):
      synopsis = "%s\r\n%s - %s"%(synopsis,synsplit[i].strip().ljust(largest),synsplit2[i])
  else:
    synopsis = syn

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'smarty.%s'%(name),url,desc,synopsis,'','smarty','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'smarty.%s'%(name),url,desc,synopsis,'','smarty','en')
  



########NEW FILE########
__FILENAME__ = parse_sqlserverfunction
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/sqlserver/functions/'):
  if '.html' in file:
    files.append('./docs/sqlserver/functions/%s'%(file))

for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  name = soup.findAll('h1')[0].string.replace('(Transact-SQL)','')
  desc = openclosetags.sub('',str(soup.findAll(attrs={"class" : "introduction"})[0].findAll('p')[0]))
  synopsis = soup.findAll(attrs={"class":"LW_CodeSnippetContainerCodeCollection"})[0].findAll('pre')[0].string.strip()

  url = "http://msdn.microsoft.com/en-us/library/%s"%(file.replace('./docs/sqlserver/functions/library','').replace('.html',''))
  url = url.replace('./docs/sqlserver/functions/','')

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','sqlserverfunction','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'sql server sqlserver sqlserver2008 2008','sqlserverfunction','en')

########NEW FILE########
__FILENAME__ = parse_svn
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/svn/'):
  if 'svn.ref.svn.c' in file and '.html' in file:
    files.append('./docs/svn/%s'%(file))

for file in os.listdir('./docs/svn/'):
  if 'svn.ref.svnadmin.c' in file and '.html' in file:
    files.append('./docs/svn/%s'%(file))


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)

  t = soup.findAll(attrs={"class" : "refnamediv"})
  name = spaces.sub(' ',openclosetags.sub('',openclosep.sub('',t[0].findAll('p')[0].prettify()).strip()))
  searchname = ' '.join(name.split(' ')[:2])
  synopsis = str(soup.findAll('pre')[0])
  synopsis = openclosetags.sub('',synopsis)
  url = "http://svnbook.red-bean.com/en/1.5/%s"%(file.replace('./docs/svn/',''))

  t = soup.findAll(attrs={"class":"refsect1"})
  description = ''
  for p in t[1].findAll('p'):
    description = "%s %s"%(description,p)
  description = openclosetags.sub('',description)

  t = soup.findAll(text=re.compile('Options'))
  if len(t) != 0:
    if str(t[0].next.string) != 'None':
      synopsis = "%s %s"%(synopsis,str(t[0].next.string))

  t = soup.findAll(text=re.compile('Alternate names'))
  if len(t) != 0:
    if openclosetags.sub('',str(t[0].next)) != 'None':
      previoushasseperator = True
      for altname in openclosetags.sub('',str(t[0].next)).split(' '):
        altname = altname.replace(',','')
        p = searchname.split(' ')
        p[1] = altname
        altname = ' '.join(p)

        if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
          print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(altname,'',url,name,synopsis,description,'svn','en')
        if sys.argv[1].lower() == 'sql':
          print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(altname,'',url,name,synopsis,description,'svn','')
        if ',' in altname:
          previoushasseperator = True
        else:
          break



  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(searchname,'',url,name,synopsis,description,'svn','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(searchname,'',url,name,synopsis,description,'svn','')


########NEW FILE########
__FILENAME__ = parse_underscorejs
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)
badtags = re.compile('''<p.*>|</p>|<b.*>.*</b>|<code.*>.*</code>|<span.*>.*</span>|<.*?>|</.*?>''')
spaces = re.compile('''\s+''',re.DOTALL)

files = []

files.append('./docs/underscorejs.html')


for file in files:
	filecontents = open(file).read()
	soup = BeautifulSoup(filecontents)
	for s in soup.findAll('p'):
		
		name = ''
		synopsis = ''
		
		try:
			name = openclosetags.sub('',str(s.findAll('b')[0]))
			#synopsis = openclosetags.sub('',str(s.findAll('code')[0]))
			synopsis = openclosetags.sub('', str(s.findNextSiblings('pre')[0])).replace("'","''")
			desc = openclosetags.sub('',spaces.sub(' ',badtags.sub('',str(s)))).replace("'","")
			url = "http://documentcloud.github.com/underscore/#%s"%(name)
			
			if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
				print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc.replace("\r\n","__NEWLINE__"),synopsis.replace("\r\n","__NEWLINE__"),'','underscorejs','en')
			if sys.argv[1].lower() == 'sql':
				print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc,synopsis,'','underscore.js','en')
			
		except:
			pass
########NEW FILE########
__FILENAME__ = parse_win32error
from BeautifulSoup import BeautifulSoup
import re
import os
import sys

openclosediv = re.compile('''<div.*?>|</div>''',re.DOTALL)
openclosep = re.compile('''<p.*?>|</p>''',re.DOTALL)
opencloseh3 = re.compile('''<h3.*?>|</h3>''',re.DOTALL)
openclosett = re.compile('''<t.*?>|</tt>|<tt>|</td>|</tr>''',re.DOTALL)

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)


files = []

files.append('./docs/microsoft/win32.html')


for file in files:
  filecontents = ''
  for line in open(file):
    filecontents = "%s %s"%(filecontents,line.strip())
    filecontents = filecontents.replace("'","")

  soup = BeautifulSoup(filecontents)
  t = soup.findAll(attrs={"class":"FixedWidth-40-60"})
  for i in t[0].findAll("tr"):
    j = i.findAll("td")
    if len(j) != 0:
      name1 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[0]
      name2 = openclosetags.sub(' ',str(j[0])).strip().split(' ')[1]
      desc = openclosetags.sub(' ',str(j[1])).strip()

      url = '''http://msdn.microsoft.com/en-us/library/cc231199%28v=PROT.10%29.aspx'''

      if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name1,'',url,desc,'','','win32error','en')
        print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name2,'',url,desc,'','','win32error','en')
      if sys.argv[1].lower() == 'sql':
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name1,'',url,desc,'','','win32error','en')
        print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name2,'',url,desc,'','','win32error','en')


########NEW FILE########
__FILENAME__ = parse_windowscommand
from BeautifulSoup import BeautifulSoup
import re
import os
import sys
import string

openclosetags = re.compile('''<.*?>|</.*?>''',re.DOTALL)
spaces = re.compile('''\s+''',re.DOTALL)

files = []

for file in os.listdir('./docs/windowscommand/'):
  if '.html' in file:
    files.append('./docs/windowscommand/%s'%(file))

for file in files:
  filecontents = ''
  for line in open(file):
    line = ''.join(filter(lambda x:x in string.printable, line))
    filecontents = "%s %s"%(filecontents,line.strip())

  soup = BeautifulSoup(filecontents)

  name = openclosetags.sub('',str(soup.findAll(attrs={"class":"title"})[0]))
  p = soup.findAll(attrs={"id":"mainBody"})[0].findAll('p')
  desc = openclosetags.sub('',str(p[0])).strip()
  if desc == '':
    desc = openclosetags.sub('',str(p[1])).strip()

  synopsis = ""
  for p in soup.findAll('pre'):
    if name.lower() in str(p).lower():
      synopsis = openclosetags.sub('',str(p))
      break
  
  url = "http://technet.microsoft.com/en-us/library/%s"%(file.replace('./docs/windowscommand/library','').replace('.html',''))

  if len(sys.argv) == 1 or sys.argv[1].lower() == 'tsv':
    print "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s"%(name,'',url,desc,synopsis,'','windowscommand','en')
  if sys.argv[1].lower() == 'sql':
    print '''INSERT INTO functions (`id`, `name`, `namespace`, `url`, `description`, `synopsis`, `detail`, `type`, `lang`) VALUES (NULL, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');'''%(name,'',url,desc.replace("'","\\'"),synopsis.replace("'","\\'"),'windows command commandline line','windowscommand','en')

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Released under the GPL v2 license 
# https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

from glob import glob
from lxml import etree

OUTPUT = "output.txt"

out = open(OUTPUT, "w")
xeps = {}


files = glob('download/extensions/xep-????.xml')
for f in files:
    tree = etree.parse(f)

    title = tree.xpath('/xep/header/title')[0].text
    number = tree.xpath('/xep/header/number')[0].text
    long_name = 'XEP-%s' % number
    short_name = 'XEP-%d' % int(number)
    short_num = '%d' % int(number)
    url = 'http://xmpp.org/extensions/' + long_name.lower() + '.html'
    abstract = tree.xpath('/xep/header/abstract')[0].text
    image = '';
    
    # The ZCI box looks weird if there is an image with a small abstract
    if len(abstract) > 150:
        image = '[[Image:http://xmpp.org/images/xmpp.png]]'

    abstract = abstract.replace('\n', ' ')
    abstract = abstract.replace('\t', ' ')
    
    out.write('\t'.join([long_name, "A", "", "", "", "", "", "", "", "",
                         image,
                         abstract,
                         url]) + '\n')
    out.write('\t'.join([short_num, "R", long_name,
                         "", "", "", "", "", "", "", "", "", ""]) + '\n')
    out.write('\t'.join([number, "R", long_name,
                         "", "", "", "", "", "", "", "", "", ""]) + '\n')
    out.write('\t'.join([short_name, "R", long_name,
                         "", "", "", "", "", "", "", "", "", ""]) + '\n')

########NEW FILE########
__FILENAME__ = parse
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from BeautifulSoup import BeautifulSoup
from collections import defaultdict
# Use defaultdict to append duplicates, but output only the first entry

modules = defaultdict(list)


def normalize(string):
    ''' -> Remove parantheses part from ending of module names
        -> Remove YUI from module name
    '''
    return re.sub('( ?\(.*\)$|YUI\ ?[2-3]?[ -]?)', '', string)


def get_descr_string(type, descr):
    return '''<i>Type</i>: %s<br /><i>Description</i>: %s''' \
        % (type, re.sub('(\n|\r)', '<br />', descr))

# Parse the official modules
official_soup = BeautifulSoup(open('data/official.html'))
for module in official_soup.findAll('li', {'class': 'component'}):
    mah = module.a['href']
    descr = get_descr_string('Official', module.a['data-tooltip'])
    modules[module.a.text].append({'link': 'http://yuilibrary.com%s' % mah,
                                   'name': module.a.text,
                                   'descr': descr
                                   })

# Parse the community supported gallery modules
gallery_soup = BeautifulSoup(open('data/gallery.html'))
for module in gallery_soup.findAll('a', href=re.compile('/gallery/show/.+')):
    if 'patch' in module.text.lower():
        continue
    h4 = module.findNext('h4')
    if h4.span:
        hsnn = h4.span.next.next
        descr = get_descr_string('Gallery, available on CDN', hsnn)
    else:
        descr = get_descr_string('Gallery', h4.next.next)
    mh = module['href']
    mt = normalize(module.text)
    modules[mt].append({'link': 'http://yuilibrary.com%s' % mh,
                        'descr': descr,
                        'name': module.text})

with open('output.txt', 'w') as f:
    for name, value in modules.items():
        f.write('\t'.join(
                [
                    name,  # title
                    'A',   # type
                    '',    # redirect
                    '',    # otheruses
                    '',    # categories
                    '',    # references
                    '',    # see_also
                    '',    # further_reading
                    '',    # external_links
                    '',    # disambiguation
                    '',    # images
                    value[0]['descr'],   # abstract
                    value[0]['link']     # source_url
                    ]
                ) + "\n")

########NEW FILE########
