__FILENAME__ = get_character
#!/usr/bin/env python
"""
get_character.py

Usage: get_character "characterID"

Show some info about the character with the given characterID (e.g. '0000001'
for "Jesse James", using 'http' or 'mobile').
Notice that characterID, using 'sql', are not the same IDs used on the web.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "characterID"' % sys.argv[0]
    sys.exit(2)

characterID = sys.argv[1]

i = imdb.IMDb()

out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

try:
    # Get a character object with the data about the character identified by
    # the given characterID.
    character = i.get_character(characterID)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)


if not character:
    print 'It seems that there\'s no character with characterID "%s"' % characterID
    sys.exit(4)

# XXX: this is the easier way to print the main info about a character;
# calling the summary() method of a character object will returns a string
# with the main information about the character.
# Obviously it's not really meaningful if you want to know how
# to access the data stored in a character object, so look below; the
# commented lines show some ways to retrieve information from a
# character object.
print character.summary().encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = get_company
#!/usr/bin/env python
"""
get_company.py

Usage: get_company "companyID"

Show some info about the company with the given companyID (e.g. '0071509'
for "Columbia Pictures [us]", using 'http' or 'mobile').
Notice that companyID, using 'sql', are not the same IDs used on the web.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "companyID"' % sys.argv[0]
    sys.exit(2)

companyID = sys.argv[1]

i = imdb.IMDb()

out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

try:
    # Get a company object with the data about the company identified by
    # the given companyID.
    company = i.get_company(companyID)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)


if not company:
    print 'It seems that there\'s no company with companyID "%s"' % companyID
    sys.exit(4)

# XXX: this is the easier way to print the main info about a company;
# calling the summary() method of a company object will returns a string
# with the main information about the company.
# Obviously it's not really meaningful if you want to know how
# to access the data stored in a company object, so look below; the
# commented lines show some ways to retrieve information from a
# company object.
print company.summary().encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = get_first_character
#!/usr/bin/env python
"""
get_first_character.py

Usage: get_first_character "character name"

Search for the given name and print the best matching result.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "character name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of character objects).
    results = i.search_character(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

if not results:
    print 'No matches for "%s", sorry.' % name.encode(out_encoding, 'replace')
    sys.exit(0)

# Print only the first result.
print '    Best match for "%s"' % name.encode(out_encoding, 'replace')

# This is a character instance.
character = results[0]

# So far the character object only contains basic information like the
# name; retrieve main information:
i.update(character)

print character.summary().encode(out_encoding, 'replace')




########NEW FILE########
__FILENAME__ = get_first_company
#!/usr/bin/env python
"""
get_first_company.py

Usage: get_first_company "company name"

Search for the given name and print the best matching result.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "company name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of company objects).
    results = i.search_company(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

if not results:
    print 'No matches for "%s", sorry.' % name.encode(out_encoding, 'replace')
    sys.exit(0)

# Print only the first result.
print '    Best match for "%s"' % name.encode(out_encoding, 'replace')

# This is a company instance.
company = results[0]

# So far the company object only contains basic information like the
# name; retrieve main information:
i.update(company)

print company.summary().encode(out_encoding, 'replace')




########NEW FILE########
__FILENAME__ = get_first_movie
#!/usr/bin/env python
"""
get_first_movie.py

Usage: get_first_movie "movie title"

Search for the given title and print the best matching result.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "movie title"' % sys.argv[0]
    sys.exit(2)

title = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

title = unicode(title, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of Movie objects).
    results = i.search_movie(title)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

if not results:
    print 'No matches for "%s", sorry.' % title.encode(out_encoding, 'replace')
    sys.exit(0)

# Print only the first result.
print '    Best match for "%s"' % title.encode(out_encoding, 'replace')

# This is a Movie instance.
movie = results[0]

# So far the Movie object only contains basic information like the
# title and the year; retrieve main information:
i.update(movie)

print movie.summary().encode(out_encoding, 'replace')




########NEW FILE########
__FILENAME__ = get_first_person
#!/usr/bin/env python
"""
get_first_person.py

Usage: get_first_person "person name"

Search for the given name and print the best matching result.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "person name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of Person objects).
    results = i.search_person(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

if not results:
    print 'No matches for "%s", sorry.' % name.encode(out_encoding, 'replace')
    sys.exit(0)

# Print only the first result.
print '    Best match for "%s"' % name.encode(out_encoding, 'replace')

# This is a Person instance.
person = results[0]

# So far the Person object only contains basic information like the
# name; retrieve main information:
i.update(person)

print person.summary().encode(out_encoding, 'replace')




########NEW FILE########
__FILENAME__ = get_keyword
#!/usr/bin/env python
"""
get_keyword.py

Usage: get_keyword "keyword"

search for movies tagged with the given keyword and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "keyword"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of movies).
    results = i.get_keyword(name, results=20)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    name.encode(out_encoding, 'replace'))
print ' : movie title'

# Print the long imdb title for every movie.
for idx, movie in enumerate(results):
    outp = u'%d: %s' % (idx+1, movie['long imdb title'])
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = get_movie
#!/usr/bin/env python
"""
get_movie.py

Usage: get_movie "movieID"

Show some info about the movie with the given movieID (e.g. '0133093'
for "The Matrix", using 'http' or 'mobile').
Notice that movieID, using 'sql', are not the same IDs used on the web.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "movieID"' % sys.argv[0]
    sys.exit(2)

movieID = sys.argv[1]

i = imdb.IMDb()

out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

try:
    # Get a Movie object with the data about the movie identified by
    # the given movieID.
    movie = i.get_movie(movieID)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)


if not movie:
    print 'It seems that there\'s no movie with movieID "%s"' % movieID
    sys.exit(4)

# XXX: this is the easier way to print the main info about a movie;
# calling the summary() method of a Movie object will returns a string
# with the main information about the movie.
# Obviously it's not really meaningful if you want to know how
# to access the data stored in a Movie object, so look below; the
# commented lines show some ways to retrieve information from a
# Movie object.
print movie.summary().encode(out_encoding, 'replace')

# Show some info about the movie.
# This is only a short example; you can get a longer summary using
# 'print movie.summary()' and the complete set of information looking for
# the output of the movie.keys() method.
#print '==== "%s" / movieID: %s ====' % (movie['title'], movieID)
# XXX: use the IMDb instance to get the IMDb web URL for the movie.
#imdbURL = i.get_imdbURL(movie)
#if imdbURL:
#    print 'IMDb URL: %s' % imdbURL
#
# XXX: many keys return a list of values, like "genres".
#genres = movie.get('genres')
#if genres:
#    print 'Genres: %s' % ' '.join(genres)
#
# XXX: even when only one value is present (e.g.: movie with only one
#      director), fields that can be multiple are ALWAYS a list.
#      Note that the 'name' variable is a Person object, but since its
#      __str__() method returns a string with the name, we can use it
#      directly, instead of name['name']
#director = movie.get('director')
#if director:
#    print 'Director(s): ',
#    for name in director:
#        sys.stdout.write('%s ' % name)
#    print ''
#
# XXX: notice that every name in the cast is a Person object, with a
#      currentRole instance variable, which is a string for the played role.
#cast = movie.get('cast')
#if cast:
#    print 'Cast: '
#    cast = cast[:5]
#    for name in cast:
#        print '      %s (%s)' % (name['name'], name.currentRole)
# XXX: some information are not lists of strings or Person objects, but simple
#      strings, like 'rating'.
#rating = movie.get('rating')
#if rating:
#    print 'Rating: %s' % rating
# XXX: an example of how to use information sets; retrieve the "trivia"
#      info set; check if it contains some data, select and print a
#      random entry.
#import random
#i.update(movie, info=['trivia'])
#trivia = movie.get('trivia')
#if trivia:
#    rand_trivia = trivia[random.randrange(len(trivia))]
#    print 'Random trivia: %s' % rand_trivia



########NEW FILE########
__FILENAME__ = get_person
#!/usr/bin/env python
"""
get_person.py

Usage: get_person "personID"

Show some info about the person with the given personID (e.g. '0000210'
for "Julia Roberts".
Notice that personID, using 'sql', are not the same IDs used on the web.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "personID"' % sys.argv[0]
    sys.exit(2)

personID = sys.argv[1]

i = imdb.IMDb()

out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

try:
    # Get a Person object with the data about the person identified by
    # the given personID.
    person = i.get_person(personID)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)


if not person:
    print 'It seems that there\'s no person with personID "%s"' % personID
    sys.exit(4)

# XXX: this is the easier way to print the main info about a person;
# calling the summary() method of a Person object will returns a string
# with the main information about the person.
# Obviously it's not really meaningful if you want to know how
# to access the data stored in a Person object, so look below; the
# commented lines show some ways to retrieve information from a
# Person object.
print person.summary().encode(out_encoding, 'replace')

# Show some info about the person.
# This is only a short example; you can get a longer summary using
# 'print person.summary()' and the complete set of information looking for
# the output of the person.keys() method.
#print '==== "%s" / personID: %s ====' % (person['name'], personID)
# XXX: use the IMDb instance to get the IMDb web URL for the person.
#imdbURL = i.get_imdbURL(person)
#if imdbURL:
#    print 'IMDb URL: %s' % imdbURL
# XXX: print the birth date and birth notes.
#d_date = person.get('birth date')
#if d_date:
#    print 'Birth date: %s' % d_date
#    b_notes = person.get('birth notes')
#    if b_notes:
#        print 'Birth notes: %s' % b_notes
# XXX: print the last five movies he/she acted in, and the played role.
#movies_acted = person.get('actor') or person.get('actress')
#if movies_acted:
#    print 'Last roles played: '
#    for movie in movies_acted[:5]:
#        print '    %s (in "%s")' % (movie.currentRole, movie['title'])
# XXX: example of the use of information sets.
#import random
#i.update(person, info=['awards'])
#awards = person.get('awards')
#if awards:
#    rand_award = awards[random.randrange(len(awards))]
#    s = 'Random award: in year '
#    s += rand_award.get('year', '')
#    s += ' %s "%s"' % (rand_award.get('result', '').lower(),
#                        rand_award.get('award', ''))
#    print s



########NEW FILE########
__FILENAME__ = get_top_bottom_movies
#!/usr/bin/env python
"""
get_top_bottom_movies.py

Usage: get_top_bottom_movies

Return top and bottom 10 movies, by ratings.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 1:
    print 'No arguments are required.'
    sys.exit(2)

i = imdb.IMDb()

top250 = i.get_top250_movies()
bottom100 = i.get_bottom100_movies()

out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

for label, ml in [('top 10', top250[:10]), ('bottom 10', bottom100[:10])]:
    print ''
    print '%s movies' % label
    print 'rating\tvotes\ttitle'
    for movie in ml:
        outl = u'%s\t%s\t%s' % (movie.get('rating'), movie.get('votes'),
                                    movie['long imdb title'])
        print outl.encode(out_encoding, 'replace')


########NEW FILE########
__FILENAME__ = imdbpy2sql
#!/usr/bin/env python
"""
imdbpy2sql.py script.

This script puts the data of the plain text data files into a
SQL database.

Copyright 2005-2012 Davide Alberani <da@erlug.linux.it>
               2006 Giuseppe "Cowo" Corbelli <cowo --> lugbs.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import os
import sys
import getopt
import time
import re
import warnings
import anydbm
from itertools import islice, chain
try: import cPickle as pickle
except ImportError: import pickle
try: from hashlib import md5
except ImportError: from md5 import md5
from gzip import GzipFile
from types import UnicodeType

from imdb.parser.sql.dbschema import *
from imdb.parser.sql import get_movie_data, soundex
from imdb.utils import analyze_title, analyze_name, date_and_notes, \
        build_name, build_title, normalizeName, normalizeTitle, _articles, \
        build_company_name, analyze_company_name, canonicalTitle
from imdb._exceptions import IMDbParserError, IMDbError


HELP = """imdbpy2sql.py usage:
    %s -d /directory/with/PlainTextDataFiles/ -u URI [-c /directory/for/CSV_files] [-o sqlobject,sqlalchemy] [-i table,dbm] [--CSV-OPTIONS] [--COMPATIBILITY-OPTIONS]

        # NOTE: URI is something along the line:
                scheme://[user[:password]@]host[:port]/database[?parameters]

                Examples:
                mysql://user:password@host/database
                postgres://user:password@host/database
                sqlite:/tmp/imdb.db
                sqlite:/C|/full/path/to/database

        # NOTE: CSV mode (-c path):
                A directory is used to store CSV files; on supported
                database servers it should be really fast.

        # NOTE: ORMs (-o orm):
                Valid options are 'sqlobject', 'sqlalchemy' or the
                preferred order separating the voices with a comma.

        # NOTE: imdbIDs store/restore (-i method):
                Valid options are 'table' (imdbIDs stored in a temporary
                table of the database) or 'dbm' (imdbIDs stored on a dbm
                file - this is the default if CSV is used).

        # NOTE: --CSV-OPTIONS can be:
            --csv-ext STRING        files extension (.csv)
            --csv-only-write        exit after the CSV files are written.
            --csv-only-load         load an existing set of CSV files.

        # NOTE: --COMPATIBILITY-OPTIONS can be one of:
            --mysql-innodb          insert data into a MySQL MyISAM db,
                                    and then convert it to InnoDB.
            --mysql-force-myisam    force the creation of MyISAM tables.
            --ms-sqlserver          compatibility mode for Microsoft SQL Server
                                    and SQL Express.
            --sqlite-transactions   uses transactions, to speed-up SQLite.


                See README.sqldb for more information.
""" % sys.argv[0]

# Directory containing the IMDb's Plain Text Data Files.
IMDB_PTDF_DIR = None
# URI used to connect to the database.
URI = None
# ORM to use (list of options) and actually used (string).
USE_ORM = None
USED_ORM = None
# List of tables of the database.
DB_TABLES = []
# Max allowed recursion, inserting data.
MAX_RECURSION = 10
# Method used to (re)store imdbIDs.
IMDBIDS_METHOD = None
# If set, this directory is used to output CSV files.
CSV_DIR = None
CSV_CURS = None
CSV_ONLY_WRITE = False
CSV_ONLY_LOAD = False
CSV_EXT = '.csv'
CSV_EOL = '\n'
CSV_DELIMITER = ','
CSV_QUOTE = '"'
CSV_ESCAPE = '"'
CSV_NULL = 'NULL'
CSV_QUOTEINT = False
CSV_LOAD_SQL = None
CSV_MYSQL = "LOAD DATA LOCAL INFILE '%(file)s' INTO TABLE `%(table)s` FIELDS TERMINATED BY '%(delimiter)s' ENCLOSED BY '%(quote)s' ESCAPED BY '%(escape)s' LINES TERMINATED BY '%(eol)s'"
CSV_PGSQL = "COPY %(table)s FROM '%(file)s' WITH DELIMITER AS '%(delimiter)s' NULL AS '%(null)s' QUOTE AS '%(quote)s' ESCAPE AS '%(escape)s' CSV"
CSV_DB2 = "CALL SYSPROC.ADMIN_CMD('LOAD FROM %(file)s OF del MODIFIED BY lobsinfile INSERT INTO %(table)s')"

# Temporary fix for old style titles.
#FIX_OLD_STYLE_TITLES = True

# Store custom queries specified on the command line.
CUSTOM_QUERIES = {}
# Allowed time specification, for custom queries.
ALLOWED_TIMES = ('BEGIN', 'BEFORE_DROP', 'BEFORE_CREATE', 'AFTER_CREATE',
                'BEFORE_MOVIES', 'BEFORE_COMPANIES', 'BEFORE_CAST',
                'BEFORE_RESTORE', 'BEFORE_INDEXES', 'END', 'BEFORE_MOVIES_TODB',
                'AFTER_MOVIES_TODB', 'BEFORE_PERSONS_TODB',
                'AFTER_PERSONS_TODB','BEFORE_SQLDATA_TODB',
                'AFTER_SQLDATA_TODB', 'BEFORE_AKAMOVIES_TODB',
                'AFTER_AKAMOVIES_TODB', 'BEFORE_CHARACTERS_TODB',
                'AFTER_CHARACTERS_TODB', 'BEFORE_COMPANIES_TODB',
                'AFTER_COMPANIES_TODB', 'BEFORE_EVERY_TODB',
                'AFTER_EVERY_TODB', 'BEFORE_CSV_LOAD', 'BEFORE_CSV_TODB',
                'AFTER_CSV_TODB')

# Shortcuts for some compatibility options.
MYSQLFORCEMYISAM_OPTS = ['-e',
        'AFTER_CREATE:FOR_EVERY_TABLE:ALTER TABLE %(table)s ENGINE=MyISAM;']
MYSQLINNODB_OPTS = ['-e',
        'AFTER_CREATE:FOR_EVERY_TABLE:ALTER TABLE %(table)s ENGINE=MyISAM;',
        '-e',
        'BEFORE_INDEXES:FOR_EVERY_TABLE:ALTER TABLE %(table)s ENGINE=InnoDB;']
SQLSERVER_OPTS =  ['-e', 'BEFORE_MOVIES_TODB:SET IDENTITY_INSERT %(table)s ON;',
        '-e', 'AFTER_MOVIES_TODB:SET IDENTITY_INSERT %(table)s OFF;',
        '-e', 'BEFORE_PERSONS_TODB:SET IDENTITY_INSERT %(table)s ON;',
        '-e', 'AFTER_PERSONS_TODB:SET IDENTITY_INSERT %(table)s OFF;',
        '-e', 'BEFORE_COMPANIES_TODB:SET IDENTITY_INSERT %(table)s ON;',
        '-e', 'AFTER_COMPANIES_TODB:SET IDENTITY_INSERT %(table)s OFF;',
        '-e', 'BEFORE_CHARACTERS_TODB:SET IDENTITY_INSERT %(table)s ON;',
        '-e', 'AFTER_CHARACTERS_TODB:SET IDENTITY_INSERT %(table)s OFF;',
        '-e', 'BEFORE_AKAMOVIES_TODB:SET IDENTITY_INSERT %(table)s ON;',
        '-e', 'AFTER_AKAMOVIES_TODB:SET IDENTITY_INSERT %(table)s OFF;']
SQLITE_OPTS = ['-e', 'BEGIN:PRAGMA synchronous = OFF;',
        '-e', 'BEFORE_EVERY_TODB:BEGIN TRANSACTION;',
        '-e', 'AFTER_EVERY_TODB:COMMIT;',
        '-e', 'BEFORE_INDEXES:BEGIN TRANSACTION;',
        'e', 'END:COMMIT;']

if '--mysql-innodb' in sys.argv[1:]:
    sys.argv += MYSQLINNODB_OPTS
if '--mysql-force-myisam' in sys.argv[1:]:
    sys.argv += MYSQLFORCEMYISAM_OPTS
if '--ms-sqlserver' in sys.argv[1:]:
    sys.argv += SQLSERVER_OPTS
if '--sqlite-transactions' in sys.argv[1:]:
    sys.argv += SQLITE_OPTS

# Manage arguments list.
try:
    optlist, args = getopt.getopt(sys.argv[1:], 'u:d:e:o:c:i:h',
                                                ['uri=', 'data=', 'execute=',
                                                'mysql-innodb', 'ms-sqlserver',
                                                'sqlite-transactions',
                                                'fix-old-style-titles',
                                                'mysql-force-myisam', 'orm',
                                                'csv-only-write',
                                                'csv-only-load',
                                                'csv=', 'csv-ext=',
                                                'imdbids=', 'help'])
except getopt.error, e:
    print 'Troubles with arguments.'
    print HELP
    sys.exit(2)

for opt in optlist:
    if opt[0] in ('-d', '--data'):
        IMDB_PTDF_DIR = opt[1]
    elif opt[0] in ('-u', '--uri'):
        URI = opt[1]
    elif opt[0] in ('-c', '--csv'):
        CSV_DIR = opt[1]
    elif opt[0] == '--csv-ext':
        CSV_EXT = opt[1]
    elif opt[0] in ('-i', '--imdbids'):
        IMDBIDS_METHOD = opt[1]
    elif opt[0] in ('-e', '--execute'):
        if opt[1].find(':') == -1:
            print 'WARNING: wrong command syntax: "%s"' % opt[1]
            continue
        when, cmd = opt[1].split(':', 1)
        if when not in ALLOWED_TIMES:
            print 'WARNING: unknown time: "%s"' % when
            continue
        if when == 'BEFORE_EVERY_TODB':
            for nw in ('BEFORE_MOVIES_TODB', 'BEFORE_PERSONS_TODB',
                        'BEFORE_SQLDATA_TODB', 'BEFORE_AKAMOVIES_TODB',
                        'BEFORE_CHARACTERS_TODB', 'BEFORE_COMPANIES_TODB'):
                CUSTOM_QUERIES.setdefault(nw, []).append(cmd)
        elif when == 'AFTER_EVERY_TODB':
            for nw in ('AFTER_MOVIES_TODB', 'AFTER_PERSONS_TODB',
                        'AFTER_SQLDATA_TODB', 'AFTER_AKAMOVIES_TODB',
                        'AFTER_CHARACTERS_TODB', 'AFTER_COMPANIES_TODB'):
                CUSTOM_QUERIES.setdefault(nw, []).append(cmd)
        else:
            CUSTOM_QUERIES.setdefault(when, []).append(cmd)
    elif opt[0] in ('-o', '--orm'):
        USE_ORM = opt[1].split(',')
    elif opt[0] == '--fix-old-style-titles':
        warnings.warn('The --fix-old-style-titles argument is obsolete.')
    elif opt[0] == '--csv-only-write':
        CSV_ONLY_WRITE = True
    elif opt[0] == '--csv-only-load':
        CSV_ONLY_LOAD = True
    elif opt[0] in ('-h', '--help'):
        print HELP
        sys.exit(0)

if IMDB_PTDF_DIR is None:
    print 'You must supply the directory with the plain text data files'
    print HELP
    sys.exit(2)

if URI is None:
    print 'You must supply the URI for the database connection'
    print HELP
    sys.exit(2)

if IMDBIDS_METHOD not in (None, 'dbm', 'table'):
    print 'the method to (re)store imdbIDs must be one of "dbm" or "table"'
    print HELP
    sys.exit(2)

if (CSV_ONLY_WRITE or CSV_ONLY_LOAD) and not CSV_DIR:
    print 'You must specify the CSV directory with the -c argument'
    print HELP
    sys.exit(3)


# Some warnings and notices.
URIlower = URI.lower()

if URIlower.startswith('mysql'):
    if '--mysql-force-myisam' in sys.argv[1:] and \
            '--mysql-innodb' in sys.argv[1:]:
        print '\nWARNING: there is no sense in mixing the --mysql-innodb and\n'\
                '--mysql-force-myisam command line options!\n'
    elif '--mysql-innodb' in sys.argv[1:]:
        print "\nNOTICE: you've specified the --mysql-innodb command line\n"\
                "option; you should do this ONLY IF your system uses InnoDB\n"\
                "tables or you really want to use InnoDB; if you're running\n"\
                "a MyISAM-based database, please omit any option; if you\n"\
                "want to force MyISAM usage on a InnoDB-based database,\n"\
                "try the --mysql-force-myisam command line option, instead.\n"
    elif '--mysql-force-myisam' in sys.argv[1:]:
        print "\nNOTICE: you've specified the --mysql-force-myisam command\n"\
                "line option; you should do this ONLY IF your system uses\n"\
                "InnoDB tables and you want to use MyISAM tables, instead.\n"
    else:
        print "\nNOTICE: IF you're using InnoDB tables, data insertion can\n"\
                "be very slow; you can switch to MyISAM tables - forcing it\n"\
                "with the --mysql-force-myisam option - OR use the\n"\
                "--mysql-innodb command line option, but DON'T USE these if\n"\
                "you're already working on MyISAM tables, because it will\n"\
                "force MySQL to use InnoDB, and performances will be poor.\n"
elif URIlower.startswith('mssql') and \
        '--ms-sqlserver' not in sys.argv[1:]:
    print "\nWARNING: you're using MS SQLServer without the --ms-sqlserver\n"\
            "command line option: if something goes wrong, try using it.\n"
elif URIlower.startswith('sqlite') and \
        '--sqlite-transactions' not in sys.argv[1:]:
    print "\nWARNING: you're using SQLite without the --sqlite-transactions\n"\
            "command line option: you'll have very poor performances!  Try\n"\
            "using it.\n"
if ('--mysql-force-myisam' in sys.argv[1:] and
        not URIlower.startswith('mysql')) or ('--mysql-innodb' in
        sys.argv[1:] and not URIlower.startswith('mysql')) or ('--ms-sqlserver'
        in sys.argv[1:] and not URIlower.startswith('mssql')) or \
        ('--sqlite-transactions' in sys.argv[1:] and
        not URIlower.startswith('sqlite')):
    print "\nWARNING: you've specified command line options that don't\n"\
            "belong to the database server you're using: proceed at your\n"\
            "own risk!\n"


if CSV_DIR:
    if URIlower.startswith('mysql'):
        CSV_LOAD_SQL = CSV_MYSQL
    elif URIlower.startswith('postgres'):
        CSV_LOAD_SQL = CSV_PGSQL
    elif URIlower.startswith('ibm'):
        CSV_LOAD_SQL = CSV_DB2
        CSV_NULL = ''
    else:
        print "\nERROR: importing CSV files is not supported for this database"
        sys.exit(3)


if USE_ORM is None:
    USE_ORM = ('sqlobject', 'sqlalchemy')
if not isinstance(USE_ORM, (tuple, list)):
    USE_ORM = [USE_ORM]
nrMods = len(USE_ORM)
_gotError = False
for idx, mod in enumerate(USE_ORM):
    mod = mod.lower()
    try:
        if mod == 'sqlalchemy':
            from imdb.parser.sql.alchemyadapter import getDBTables, \
                    NotFoundError, setConnection, ISNOTNULL, IN
        elif mod == 'sqlobject':
            from imdb.parser.sql.objectadapter import getDBTables, \
                    NotFoundError, setConnection, ISNOTNULL, IN
        else:
            warnings.warn('unknown module "%s".' % mod)
            continue
        DB_TABLES = getDBTables(URI)
        for t in DB_TABLES:
            globals()[t._imdbpyName] = t
        if _gotError:
            warnings.warn('falling back to "%s".' % mod)
        USED_ORM = mod
        break
    except ImportError, e:
        if idx+1 >= nrMods:
            raise IMDbError('unable to use any ORM in %s: %s' % (
                                            str(USE_ORM), str(e)))
        else:
            warnings.warn('unable to use "%s": %s' % (mod, str(e)))
            _gotError = True
        continue
else:
    raise IMDbError('unable to use any ORM in %s' % str(USE_ORM))


#-----------------------
# CSV Handling.


class CSVCursor(object):
    """Emulate a cursor object, but instead it writes data to a set
    of CSV files."""
    def __init__(self, csvDir, csvExt=CSV_EXT, csvEOL=CSV_EOL,
            delimeter=CSV_DELIMITER, quote=CSV_QUOTE, escape=CSV_ESCAPE,
            null=CSV_NULL, quoteInteger=CSV_QUOTEINT):
        """Initialize a CSVCursor object; csvDir is the directory where the
        CSV files will be stored."""
        self.csvDir = csvDir
        self.csvExt = csvExt
        self.csvEOL = csvEOL
        self.delimeter = delimeter
        self.quote = quote
        self.escape = escape
        self.escaped = '%s%s' % (escape, quote)
        self.null = null
        self.quoteInteger = quoteInteger
        self._fdPool = {}
        self._lobFDPool = {}
        self._counters = {}

    def buildLine(self, items, tableToAddID=False, rawValues=(),
                    lobFD=None, lobFN=None):
        """Build a single text line for a set of information."""
        # FIXME: there are too many special cases to handle, and that
        #        affects performances: management of LOB files, at least,
        #        must be moved away from here.
        quote = self.quote
        escape = self.escape
        null = self.null
        escaped = self.escaped
        quoteInteger = self.quoteInteger
        if not tableToAddID:
            r = []
        else:
            _counters = self._counters
            r = [_counters[tableToAddID]]
            _counters[tableToAddID] += 1
        r += list(items)
        for idx, val in enumerate(r):
            if val is None:
                r[idx] = null
                continue
            if (not quoteInteger) and isinstance(val, (int, long)):
                r[idx] = str(val)
                continue
            if lobFD and idx == 3:
                continue
            val = str(val)
            if quote:
                val = '%s%s%s' % (quote, val.replace(quote, escaped), quote)
            r[idx] = val
        # Add RawValue(s), if present.
        rinsert = r.insert
        if tableToAddID:
            shift = 1
        else:
            shift = 0
        for idx, item in rawValues:
            rinsert(idx + shift, item)
        if lobFD:
            # XXX: totally tailored to suit person_info.info column!
            val3 = r[3]
            val3len = len(val3 or '') or -1
            if val3len == -1:
                val3off = 0
            else:
                val3off = lobFD.tell()
            r[3] = '%s.%d.%d/' % (lobFN, val3off, val3len)
            lobFD.write(val3)
        # Build the line and add the end-of-line.
        return '%s%s' % (self.delimeter.join(r), self.csvEOL)

    def executemany(self, sqlstr, items):
        """Emulate the executemany method of a cursor, but writes the
        data in a set of CSV files."""
        # XXX: find a safer way to get the table/file name!
        tName = sqlstr.split()[2]
        lobFD = None
        lobFN = None
        doLOB = False
        # XXX: ugly special case, to create the LOB file.
        if URIlower.startswith('ibm') and tName == 'person_info':
            doLOB = True
        # Open the file descriptor or get it from the pool.
        if tName in self._fdPool:
            tFD = self._fdPool[tName]
            lobFD = self._lobFDPool.get(tName)
            lobFN = getattr(lobFD, 'name', None)
            if lobFN:
                lobFN = os.path.basename(lobFN)
        else:
            tFD = open(os.path.join(CSV_DIR, tName + self.csvExt), 'wb')
            self._fdPool[tName] = tFD
            if doLOB:
                lobFN = '%s.lob' % tName
                lobFD = open(os.path.join(CSV_DIR, lobFN), 'wb')
                self._lobFDPool[tName] = lobFD
        buildLine = self.buildLine
        tableToAddID = False
        if tName in ('cast_info', 'movie_info', 'person_info',
                    'movie_companies', 'movie_link', 'aka_name',
                    'complete_cast', 'movie_info_idx', 'movie_keyword'):
            tableToAddID = tName
            if tName not in self._counters:
                self._counters[tName] = 1
        # Identify if there are RawValue in the VALUES (...) portion of
        # the query.
        parIdx = sqlstr.rfind('(')
        rawValues = []
        vals = sqlstr[parIdx+1:-1]
        if parIdx != 0:
            vals = sqlstr[parIdx+1:-1]
            for idx, item in enumerate(vals.split(', ')):
                if item[0] in ('%', '?', ':'):
                    continue
                rawValues.append((idx, item))
        # Write these lines.
        tFD.writelines(buildLine(i, tableToAddID=tableToAddID,
                        rawValues=rawValues, lobFD=lobFD, lobFN=lobFN)
                        for i in items)
        # Flush to disk, so that no truncaded entries are ever left.
        # XXX: is this a good idea?
        tFD.flush()

    def fileNames(self):
        """Return the list of file names."""
        return [fd.name for fd in self._fdPool.values()]

    def buildFakeFileNames(self):
        """Populate the self._fdPool dictionary with fake objects
        taking file names from the content of the self.csvDir directory."""
        class _FakeFD(object): pass
        for fname in os.listdir(self.csvDir):
            if not fname.endswith(CSV_EXT):
                continue
            fpath = os.path.join(self.csvDir, fname)
            if not os.path.isfile(fpath):
                continue
            fd = _FakeFD()
            fd.name = fname
            self._fdPool[fname[:-len(CSV_EXT)]] = fd

    def close(self, tName):
        """Close a given table/file."""
        if tName in self._fdPool:
            self._fdPool[tName].close()

    def closeAll(self):
        """Close all open file descriptors."""
        for fd in self._fdPool.values():
            fd.close()
        for fd in self._lobFDPool.values():
            fd.close()


def loadCSVFiles():
    """Load every CSV file into the database."""
    CSV_REPL = {'quote': CSV_QUOTE, 'delimiter': CSV_DELIMITER,
                'escape': CSV_ESCAPE, 'null': CSV_NULL, 'eol': CSV_EOL}
    for fName in CSV_CURS.fileNames():
        connectObject.commit()
        tName = os.path.basename(fName[:-len(CSV_EXT)])
        cfName = os.path.join(CSV_DIR, fName)
        CSV_REPL['file'] = cfName
        CSV_REPL['table'] = tName
        sqlStr = CSV_LOAD_SQL % CSV_REPL
        print ' * LOADING CSV FILE %s...' % cfName
        sys.stdout.flush()
        executeCustomQueries('BEFORE_CSV_TODB')
        try:
            CURS.execute(sqlStr)
            try:
                res = CURS.fetchall()
                if res:
                    print 'LOADING OUTPUT:', res
            except:
                pass
        except Exception, e:
            print 'ERROR: unable to import CSV file %s: %s' % (cfName, str(e))
            continue
        connectObject.commit()
        executeCustomQueries('AFTER_CSV_TODB')

#-----------------------


conn = setConnection(URI, DB_TABLES)
if CSV_DIR:
    # Go for a CSV ride...
    CSV_CURS = CSVCursor(CSV_DIR)

# Extract exceptions to trap.
try:
    OperationalError = conn.module.OperationalError
except AttributeError, e:
    warnings.warn('Unable to import OperationalError; report this as a bug, ' \
            'since it will mask important exceptions: %s' % e)
    OperationalError = Exception
try:
    IntegrityError = conn.module.IntegrityError
except AttributeError, e:
    warnings.warn('Unable to import IntegrityError')
    IntegrityError = Exception

connectObject = conn.getConnection()
# XXX: fix for a problem that should be fixed in objectadapter.py (see it).
if URI and URI.startswith('sqlite') and USED_ORM == 'sqlobject':
    major = sys.version_info[0]
    minor = sys.version_info[1]
    if major > 2 or (major == 2 and minor > 5):
        connectObject.text_factory = str

# Cursor object.
CURS = connectObject.cursor()

# Name of the database and style of the parameters.
DB_NAME = conn.dbName
PARAM_STYLE = conn.paramstyle


def _get_imdbids_method():
    """Return the method to be used to (re)store
    imdbIDs (one of 'dbm' or 'table')."""
    if IMDBIDS_METHOD:
        return IMDBIDS_METHOD
    if CSV_DIR:
        return 'dbm'
    return 'table'


def tableName(table):
    """Return a string with the name of the table in the current db."""
    return table.sqlmeta.table

def colName(table, column):
    """Return a string with the name of the column in the current db."""
    if column == 'id':
        return table.sqlmeta.idName
    return table.sqlmeta.columns[column].dbName


class RawValue(object):
    """String-like objects to store raw SQL parameters, that are not
    intended to be replaced with positional parameters, in the query."""
    def __init__(self, s, v):
        self.string = s
        self.value = v
    def __str__(self):
        return self.string


def _makeConvNamed(cols):
    """Return a function to be used to convert a list of parameters
    from positional style to named style (convert from a list of
    tuples to a list of dictionaries."""
    nrCols = len(cols)
    def _converter(params):
        for paramIndex, paramSet in enumerate(params):
            d = {}
            for i in xrange(nrCols):
                d[cols[i]] = paramSet[i]
            params[paramIndex] = d
        return params
    return _converter

def createSQLstr(table, cols, command='INSERT'):
    """Given a table and a list of columns returns a sql statement
    useful to insert a set of data in the database.
    Along with the string, also a function useful to convert parameters
    from positional to named style is returned."""
    sqlstr = '%s INTO %s ' % (command, tableName(table))
    colNames = []
    values = []
    convCols = []
    count = 1
    def _valStr(s, index):
        if DB_NAME in ('mysql', 'postgres'): return '%s'
        elif PARAM_STYLE == 'format': return '%s'
        elif PARAM_STYLE == 'qmark': return '?'
        elif PARAM_STYLE == 'numeric': return ':%s' % index
        elif PARAM_STYLE == 'named': return ':%s' % s
        elif PARAM_STYLE == 'pyformat': return '%(' + s + ')s'
        return '%s'
    for col in cols:
        if isinstance(col, RawValue):
            colNames.append(colName(table, col.string))
            values.append(str(col.value))
        elif col == 'id':
            colNames.append(table.sqlmeta.idName)
            values.append(_valStr('id', count))
            convCols.append(col)
            count += 1
        else:
            colNames.append(colName(table, col))
            values.append(_valStr(col, count))
            convCols.append(col)
            count += 1
    sqlstr += '(%s) ' % ', '.join(colNames)
    sqlstr += 'VALUES (%s)' % ', '.join(values)
    if DB_NAME not in ('mysql', 'postgres') and \
            PARAM_STYLE in ('named', 'pyformat'):
        converter = _makeConvNamed(convCols)
    else:
        # Return the list itself.
        converter = lambda x: x
    return sqlstr, converter

def _(s, truncateAt=None):
    """Nicely print a string to sys.stdout, optionally
    truncating it a the given char."""
    if not isinstance(s, UnicodeType):
        s = unicode(s, 'utf_8')
    if truncateAt is not None:
        s = s[:truncateAt]
    s = s.encode(sys.stdout.encoding or 'utf_8', 'replace')
    return s

if not hasattr(os, 'times'):
    def times():
        """Fake times() function."""
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    os.times = times

# Show time consumed by the single function call.
CTIME = int(time.time())
BEGIN_TIME = CTIME
CTIMES = os.times()
BEGIN_TIMES = CTIMES

def _minSec(*t):
    """Return a tuple of (mins, secs, ...) - two for every item passed."""
    l = []
    for i in t:
        l.extend(divmod(int(i), 60))
    return tuple(l)

def t(s, sinceBegin=False):
    """Pretty-print timing information."""
    global CTIME, CTIMES
    nt = int(time.time())
    ntimes = os.times()
    if not sinceBegin:
        ct = CTIME
        cts = CTIMES
    else:
        ct = BEGIN_TIME
        cts = BEGIN_TIMES
    print '# TIME', s, \
            ': %dmin, %dsec (wall) %dmin, %dsec (user) %dmin, %dsec (system)' \
            % _minSec(nt-ct, ntimes[0]-cts[0], ntimes[1]-cts[1])
    if not sinceBegin:
        CTIME = nt
        CTIMES = ntimes

def title_soundex(title):
    """Return the soundex code for the given title; the (optional) starting
    article is pruned.  It assumes to receive a title without year/imdbIndex
    or kind indications, but just the title string, as the one in the
    analyze_title(title)['title'] value."""
    if not title: return None
    # Convert to canonical format.
    title = canonicalTitle(title)
    ts = title.split(', ')
    # Strip the ending article, if any.
    if ts[-1].lower() in _articles:
        title = ', '.join(ts[:-1])
    return soundex(title)

def name_soundexes(name, character=False):
    """Return three soundex codes for the given name; the name is assumed
    to be in the 'surname, name' format, without the imdbIndex indication,
    as the one in the analyze_name(name)['name'] value.
    The first one is the soundex of the name in the canonical format.
    The second is the soundex of the name in the normal format, if different
    from the first one.
    The third is the soundex of the surname, if different from the
    other two values."""
    ##if not isinstance(name, unicode): name = unicode(name, 'utf_8')
    # Prune non-ascii chars from the string.
    ##name = name.encode('ascii', 'ignore')
    if not name: return (None, None, None)
    s1 = soundex(name)
    name_normal = normalizeName(name)
    s2 = soundex(name_normal)
    if s1 == s2: s2 = None
    if not character:
        namesplit = name.split(', ')
        s3 = soundex(namesplit[0])
    else:
        s3 = soundex(name.split(' ')[-1])
    if s3 and s3 in (s1, s2): s3 = None
    return (s1, s2, s3)


# Tags to identify where the meaningful data begin/end in files.
MOVIES = 'movies.list.gz'
MOVIES_START = ('MOVIES LIST', '===========', '')
MOVIES_STOP = '--------------------------------------------------'
CAST_START = ('Name', '----')
CAST_STOP = '-----------------------------'
RAT_START = ('MOVIE RATINGS REPORT', '',
            'New  Distribution  Votes  Rank  Title')
RAT_STOP = '\n'
RAT_TOP250_START = ('note: for this top 250', '', 'New  Distribution')
RAT_BOT10_START = ('BOTTOM 10 MOVIES', '', 'New  Distribution')
TOPBOT_STOP = '\n'
AKAT_START = ('AKA TITLES LIST', '=============', '', '', '')
AKAT_IT_START = ('AKA TITLES LIST ITALIAN', '=======================', '', '')
AKAT_DE_START = ('AKA TITLES LIST GERMAN', '======================', '')
AKAT_ISO_START = ('AKA TITLES LIST ISO', '===================', '')
AKAT_HU_START = ('AKA TITLES LIST HUNGARIAN', '=========================', '')
AKAT_NO_START = ('AKA TITLES LIST NORWEGIAN', '=========================', '')
AKAN_START = ('AKA NAMES LIST', '=============', '')
AV_START = ('ALTERNATE VERSIONS LIST', '=======================', '', '')
MINHASH_STOP = '-------------------------'
GOOFS_START = ('GOOFS LIST', '==========', '')
QUOTES_START = ('QUOTES LIST', '=============')
CC_START = ('CRAZY CREDITS', '=============')
BIO_START = ('BIOGRAPHY LIST', '==============')
BUS_START = ('BUSINESS LIST', '=============', '')
BUS_STOP = '                                    ====='
CER_START = ('CERTIFICATES LIST', '=================')
COL_START = ('COLOR INFO LIST', '===============')
COU_START = ('COUNTRIES LIST', '==============')
DIS_START = ('DISTRIBUTORS LIST', '=================', '')
GEN_START = ('8: THE GENRES LIST', '==================', '')
KEY_START = ('8: THE KEYWORDS LIST', '====================', '')
LAN_START = ('LANGUAGE LIST', '=============')
LOC_START = ('LOCATIONS LIST', '==============', '')
MIS_START = ('MISCELLANEOUS COMPANY LIST', '============================')
MIS_STOP = '--------------------------------------------------------------------------------'
PRO_START = ('PRODUCTION COMPANIES LIST', '=========================', '')
RUN_START = ('RUNNING TIMES LIST', '==================')
SOU_START = ('SOUND-MIX LIST', '==============')
SFX_START = ('SFXCO COMPANIES LIST', '====================', '')
TCN_START = ('TECHNICAL LIST', '==============', '', '')
LSD_START = ('LASERDISC LIST', '==============', '------------------------')
LIT_START = ('LITERATURE LIST', '===============', '')
LIT_STOP = 'COPYING POLICY'
LINK_START = ('MOVIE LINKS LIST', '================', '')
MPAA_START = ('MPAA RATINGS REASONS LIST', '=========================')
PLOT_START = ('PLOT SUMMARIES LIST', '===================', '')
RELDATE_START = ('RELEASE DATES LIST', '==================')
SNDT_START = ('SOUNDTRACKS LIST', '================', '', '', '')
TAGL_START = ('TAG LINES LIST', '==============', '', '')
TAGL_STOP = '-----------------------------------------'
TRIV_START = ('FILM TRIVIA', '===========', '')
COMPCAST_START = ('CAST COVERAGE TRACKING LIST', '===========================')
COMPCREW_START = ('CREW COVERAGE TRACKING LIST', '===========================')
COMP_STOP = '---------------'

GzipFileRL = GzipFile.readline
class SourceFile(GzipFile):
    """Instances of this class are used to read gzipped files,
    starting from a defined line to a (optionally) given end."""
    def __init__(self, filename=None, mode=None, start=(), stop=None,
                    pwarning=1, *args, **kwds):
        filename = os.path.join(IMDB_PTDF_DIR, filename)
        try:
            GzipFile.__init__(self, filename, mode, *args, **kwds)
        except IOError, e:
            if not pwarning: raise
            print 'WARNING WARNING WARNING'
            print 'WARNING unable to read the "%s" file.' % filename
            print 'WARNING The file will be skipped, and the contained'
            print 'WARNING information will NOT be stored in the database.'
            print 'WARNING Complete error: ', e
            # re-raise the exception.
            raise
        self.start = start
        for item in start:
            itemlen = len(item)
            for line in self:
                if line[:itemlen] == item: break
        self.set_stop(stop)

    def set_stop(self, stop):
        if stop is not None:
            self.stop = stop
            self.stoplen = len(self.stop)
            self.readline = self.readline_checkEnd
        else:
            self.readline = self.readline_NOcheckEnd

    def readline_NOcheckEnd(self, size=-1):
        line = GzipFile.readline(self, size)
        return unicode(line, 'latin_1').encode('utf_8')

    def readline_checkEnd(self, size=-1):
        line = GzipFile.readline(self, size)
        if self.stop is not None and line[:self.stoplen] == self.stop: return ''
        return unicode(line, 'latin_1').encode('utf_8')

    def getByHashSections(self):
        return getSectionHash(self)

    def getByNMMVSections(self):
        return getSectionNMMV(self)


def getSectionHash(fp):
    """Return sections separated by lines starting with #."""
    curSectList = []
    curSectListApp = curSectList.append
    curTitle = ''
    joiner = ''.join
    for line in fp:
        if line and line[0] == '#':
            if curSectList and curTitle:
                yield curTitle, joiner(curSectList)
                curSectList[:] = []
                curTitle = ''
            curTitle = line[2:]
        else: curSectListApp(line)
    if curSectList and curTitle:
        yield curTitle, joiner(curSectList)
        curSectList[:] = []
        curTitle = ''

NMMVSections = dict([(x, None) for x in ('MV: ', 'NM: ', 'OT: ', 'MOVI')])
def getSectionNMMV(fp):
    """Return sections separated by lines starting with 'NM: ', 'MV: ',
    'OT: ' or 'MOVI'."""
    curSectList = []
    curSectListApp = curSectList.append
    curNMMV = ''
    joiner = ''.join
    for line in fp:
        if line[:4] in NMMVSections:
            if curSectList and curNMMV:
                yield curNMMV, joiner(curSectList)
                curSectList[:] = []
                curNMMV = ''
            if line[:4] == 'MOVI': curNMMV = line[6:]
            else: curNMMV = line[4:]
        elif not (line and line[0] == '-'): curSectListApp(line)
    if curSectList and curNMMV:
        yield curNMMV, joiner(curSectList)
        curSectList[:] = []
        curNMMV = ''

def counter(initValue=1):
    """A counter implemented using a generator."""
    i = initValue
    while 1:
        yield i
        i += 1

class _BaseCache(dict):
    """Base class for Movie and Person basic information."""
    def __init__(self, d=None, flushEvery=100000):
        dict.__init__(self)
        # Flush data into the SQL database every flushEvery entries.
        self.flushEvery = flushEvery
        self._tmpDict = {}
        self._flushing = 0
        self._deferredData = {}
        self._recursionLevel = 0
        self._table_name = ''
        self._id_for_custom_q = ''
        if d is not None:
            for k, v in d.iteritems(): self[k] = v

    def __setitem__(self, key, counter):
        """Every time a key is set, its value is the counter;
        every flushEvery, the temporary dictionary is
        flushed to the database, and then zeroed."""
        if counter % self.flushEvery == 0:
            self.flush()
        dict.__setitem__(self, key, counter)
        if not self._flushing:
            self._tmpDict[key] = counter
        else:
            self._deferredData[key] = counter

    def flush(self, quiet=0, _recursionLevel=0):
        """Flush to the database."""
        if self._flushing: return
        self._flushing = 1
        if _recursionLevel >= MAX_RECURSION:
            print 'WARNING recursion level exceded trying to flush data'
            print 'WARNING this batch of data is lost (%s).' % self.className
            self._tmpDict.clear()
            return
        if self._tmpDict:
            # Horrible hack to know if AFTER_%s_TODB has run.
            _after_has_run = False
            keys = {'table': self._table_name}
            try:
                executeCustomQueries('BEFORE_%s_TODB' % self._id_for_custom_q,
                                    _keys=keys, _timeit=False)
                self._toDB(quiet)
                executeCustomQueries('AFTER_%s_TODB' % self._id_for_custom_q,
                                    _keys=keys, _timeit=False)
                _after_has_run = True
                self._tmpDict.clear()
            except OperationalError, e:
                # XXX: I'm not sure this is the right thing (and way)
                #      to proceed.
                if not _after_has_run:
                    executeCustomQueries('AFTER_%s_TODB'%self._id_for_custom_q,
                                        _keys=keys, _timeit=False)
                # Dataset too large; split it in two and retry.
                # XXX: new code!
                # the same class instance (self) is used, instead of
                # creating two separated objects.
                _recursionLevel += 1
                self._flushing = 0
                firstHalf = {}
                poptmpd = self._tmpDict.popitem
                originalLength = len(self._tmpDict)
                for x in xrange(1 + originalLength/2):
                    k, v = poptmpd()
                    firstHalf[k] = v
                print ' * TOO MANY DATA (%s items in %s), recursion: %s' % \
                                                        (originalLength,
                                                        self.className,
                                                        _recursionLevel)
                print '   * SPLITTING (run 1 of 2), recursion: %s' % \
                                                        _recursionLevel
                self.flush(quiet=quiet, _recursionLevel=_recursionLevel)
                self._tmpDict = firstHalf
                print '   * SPLITTING (run 2 of 2), recursion: %s' % \
                                                        _recursionLevel
                self.flush(quiet=quiet, _recursionLevel=_recursionLevel)
                self._tmpDict.clear()
            except Exception, e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                print 'WARNING: unknown exception caught committing the data'
                print 'WARNING: to the database; report this as a bug, since'
                print 'WARNING: many data (%d items) were lost: %s' % \
                        (len(self._tmpDict), e)
        self._flushing = 0
        # Flush also deferred data.
        if self._deferredData:
            self._tmpDict = self._deferredData
            self.flush(quiet=1)
            self._deferredData = {}
        connectObject.commit()

    def populate(self):
        """Populate the dictionary from the database."""
        raise NotImplementedError

    def _toDB(self, quiet=0):
        """Write the dictionary to the database."""
        raise NotImplementedError

    def add(self, key, miscData=None):
        """Insert a new key and return its value."""
        c = self.counter.next()
        # miscData=[('a_dict', 'value')] will set self.a_dict's c key
        # to 'value'.
        if miscData is not None:
            for d_name, data in miscData:
                getattr(self, d_name)[c] = data
        self[key] = c
        return c

    def addUnique(self, key, miscData=None):
        """Insert a new key and return its value; if the key is already
        in the dictionary, its previous  value is returned."""
        if key in self: return self[key]
        else: return self.add(key, miscData)


def fetchsome(curs, size=20000):
    """Yes, I've read the Python Cookbook! :-)"""
    while 1:
        res = curs.fetchmany(size)
        if not res: break
        for r in res: yield r


class MoviesCache(_BaseCache):
    """Manage the movies list."""
    className = 'MoviesCache'
    counter = counter()

    def __init__(self, *args, **kwds):
        _BaseCache.__init__(self, *args, **kwds)
        self.movieYear = {}
        self._table_name = tableName(Title)
        self._id_for_custom_q = 'MOVIES'
        self.sqlstr, self.converter = createSQLstr(Title, ('id', 'title',
                                    'imdbIndex', 'kindID', 'productionYear',
                                    'imdbID', 'phoneticCode', 'episodeOfID',
                                    'seasonNr', 'episodeNr', 'seriesYears',
                                    'md5sum'))

    def populate(self):
        print ' * POPULATING %s...' % self.className
        titleTbl = tableName(Title)
        movieidCol = colName(Title, 'id')
        titleCol = colName(Title, 'title')
        kindidCol = colName(Title, 'kindID')
        yearCol = colName(Title, 'productionYear')
        imdbindexCol = colName(Title, 'imdbIndex')
        episodeofidCol = colName(Title, 'episodeOfID')
        seasonNrCol = colName(Title, 'seasonNr')
        episodeNrCol = colName(Title, 'episodeNr')
        sqlPop = 'SELECT %s, %s, %s, %s, %s, %s, %s, %s FROM %s;' % \
                (movieidCol, titleCol, kindidCol, yearCol, imdbindexCol,
                episodeofidCol, seasonNrCol, episodeNrCol, titleTbl)
        CURS.execute(sqlPop)
        _oldcacheValues = Title.sqlmeta.cacheValues
        Title.sqlmeta.cacheValues = False
        for x in fetchsome(CURS, self.flushEvery):
            mdict = {'title': x[1], 'kind': KIND_STRS[x[2]],
                    'year': x[3], 'imdbIndex': x[4]}
            if mdict['imdbIndex'] is None: del mdict['imdbIndex']
            if mdict['year'] is None: del mdict['year']
            else: mdict['year'] = str(mdict['year'])
            episodeOfID = x[5]
            if episodeOfID is not None:
                s = Title.get(episodeOfID)
                series_d = {'title': s.title,
                            'kind': str(KIND_STRS[s.kindID]),
                            'year': s.productionYear, 'imdbIndex': s.imdbIndex}
                if series_d['imdbIndex'] is None: del series_d['imdbIndex']
                if series_d['year'] is None: del series_d['year']
                else: series_d['year'] = str(series_d['year'])
                mdict['episode of'] = series_d
            title = build_title(mdict, ptdf=1, _emptyString='')
            dict.__setitem__(self, title, x[0])
        self.counter = counter(Title.select().count() + 1)
        Title.sqlmeta.cacheValues = _oldcacheValues

    def _toDB(self, quiet=0):
        if not quiet:
            print ' * FLUSHING %s...' % self.className
            sys.stdout.flush()
        l = []
        lapp = l.append
        tmpDictiter = self._tmpDict.iteritems
        for k, v in tmpDictiter():
            try:
                t = analyze_title(k, _emptyString='')
            except IMDbParserError:
                if k and k.strip():
                    print 'WARNING %s._toDB() invalid title:' % self.className,
                    print _(k)
                continue
            tget = t.get
            episodeOf = None
            kind = tget('kind')
            if kind == 'episode':
                # Series title.
                stitle = build_title(tget('episode of'), _emptyString='', ptdf=1)
                episodeOf = self.addUnique(stitle)
                del t['episode of']
                year = self.movieYear.get(v)
                if year is not None and year != '????':
                    try: t['year'] = int(year)
                    except ValueError: pass
            elif kind in ('tv series', 'tv mini series'):
                t['series years'] = self.movieYear.get(v)
            title = tget('title')
            soundex = title_soundex(title)
            lapp((v, title, tget('imdbIndex'), KIND_IDS[kind],
                    tget('year'), None, soundex, episodeOf,
                    tget('season'), tget('episode'), tget('series years'),
                    md5(k).hexdigest()))
        self._runCommand(l)

    def _runCommand(self, dataList):
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(dataList))
        else:
            CSV_CURS.executemany(self.sqlstr, dataList)

    def addUnique(self, key, miscData=None):
        """Insert a new key and return its value; if the key is already
        in the dictionary, its previous  value is returned."""
        if key.endswith('{{SUSPENDED}}'):
            return None
        # DONE: to be removed when it will be no more needed!
        #if FIX_OLD_STYLE_TITLES:
        #    key = build_title(analyze_title(key, canonical=False,
        #                    _emptyString=''), ptdf=1, _emptyString='')
        if key in self: return self[key]
        else: return self.add(key, miscData)


class PersonsCache(_BaseCache):
    """Manage the persons list."""
    className = 'PersonsCache'
    counter = counter()

    def __init__(self, *args, **kwds):
        _BaseCache.__init__(self, *args, **kwds)
        self.personGender = {}
        self._table_name = tableName(Name)
        self._id_for_custom_q = 'PERSONS'
        self.sqlstr, self.converter = createSQLstr(Name, ['id', 'name',
                                'imdbIndex', 'imdbID', 'gender', 'namePcodeCf',
                                'namePcodeNf', 'surnamePcode', 'md5sum'])

    def populate(self):
        print ' * POPULATING PersonsCache...'
        nameTbl = tableName(Name)
        personidCol = colName(Name, 'id')
        nameCol = colName(Name, 'name')
        imdbindexCol = colName(Name, 'imdbIndex')
        CURS.execute('SELECT %s, %s, %s FROM %s;' % (personidCol, nameCol,
                                                    imdbindexCol, nameTbl))
        _oldcacheValues = Name.sqlmeta.cacheValues
        Name.sqlmeta.cacheValues = False
        for x in fetchsome(CURS, self.flushEvery):
            nd = {'name': x[1]}
            if x[2]: nd['imdbIndex'] = x[2]
            name = build_name(nd)
            dict.__setitem__(self, name, x[0])
        self.counter = counter(Name.select().count() + 1)
        Name.sqlmeta.cacheValues = _oldcacheValues

    def _toDB(self, quiet=0):
        if not quiet:
            print ' * FLUSHING PersonsCache...'
            sys.stdout.flush()
        l = []
        lapp = l.append
        tmpDictiter = self._tmpDict.iteritems
        for k, v in tmpDictiter():
            try:
                t = analyze_name(k)
            except IMDbParserError:
                if k and k.strip():
                    print 'WARNING PersonsCache._toDB() invalid name:', _(k)
                continue
            tget = t.get
            name = tget('name')
            namePcodeCf, namePcodeNf, surnamePcode = name_soundexes(name)
            gender = self.personGender.get(v)
            lapp((v, name, tget('imdbIndex'), None, gender,
                namePcodeCf, namePcodeNf, surnamePcode,
                md5(k).hexdigest()))
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(l))
        else:
            CSV_CURS.executemany(self.sqlstr, l)


class CharactersCache(_BaseCache):
    """Manage the characters list."""
    counter = counter()
    className = 'CharactersCache'

    def __init__(self, *args, **kwds):
        _BaseCache.__init__(self, *args, **kwds)
        self._table_name = tableName(CharName)
        self._id_for_custom_q = 'CHARACTERS'
        self.sqlstr, self.converter = createSQLstr(CharName, ['id', 'name',
                                'imdbIndex', 'imdbID', 'namePcodeNf',
                                'surnamePcode', 'md5sum'])

    def populate(self):
        print ' * POPULATING CharactersCache...'
        nameTbl = tableName(CharName)
        personidCol = colName(CharName, 'id')
        nameCol = colName(CharName, 'name')
        imdbindexCol = colName(CharName, 'imdbIndex')
        CURS.execute('SELECT %s, %s, %s FROM %s;' % (personidCol, nameCol,
                                                    imdbindexCol, nameTbl))
        _oldcacheValues = CharName.sqlmeta.cacheValues
        CharName.sqlmeta.cacheValues = False
        for x in fetchsome(CURS, self.flushEvery):
            nd = {'name': x[1]}
            if x[2]: nd['imdbIndex'] = x[2]
            name = build_name(nd)
            dict.__setitem__(self, name, x[0])
        self.counter = counter(CharName.select().count() + 1)
        CharName.sqlmeta.cacheValues = _oldcacheValues

    def _toDB(self, quiet=0):
        if not quiet:
            print ' * FLUSHING CharactersCache...'
            sys.stdout.flush()
        l = []
        lapp = l.append
        tmpDictiter = self._tmpDict.iteritems
        for k, v in tmpDictiter():
            try:
                t = analyze_name(k)
            except IMDbParserError:
                if k and k.strip():
                    print 'WARNING CharactersCache._toDB() invalid name:', _(k)
                continue
            tget = t.get
            name = tget('name')
            namePcodeCf, namePcodeNf, surnamePcode = name_soundexes(name,
                                                                character=True)
            lapp((v, name, tget('imdbIndex'), None,
                namePcodeCf, surnamePcode, md5(k).hexdigest()))
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(l))
        else:
            CSV_CURS.executemany(self.sqlstr, l)


class CompaniesCache(_BaseCache):
    """Manage the companies list."""
    counter = counter()
    className = 'CompaniesCache'

    def __init__(self, *args, **kwds):
        _BaseCache.__init__(self, *args, **kwds)
        self._table_name = tableName(CompanyName)
        self._id_for_custom_q = 'COMPANIES'
        self.sqlstr, self.converter = createSQLstr(CompanyName, ['id', 'name',
                                'countryCode', 'imdbID', 'namePcodeNf',
                                'namePcodeSf', 'md5sum'])

    def populate(self):
        print ' * POPULATING CharactersCache...'
        nameTbl = tableName(CompanyName)
        companyidCol = colName(CompanyName, 'id')
        nameCol = colName(CompanyName, 'name')
        countryCodeCol = colName(CompanyName, 'countryCode')
        CURS.execute('SELECT %s, %s, %s FROM %s;' % (companyidCol, nameCol,
                                                    countryCodeCol, nameTbl))
        _oldcacheValues = CompanyName.sqlmeta.cacheValues
        CompanyName.sqlmeta.cacheValues = False
        for x in fetchsome(CURS, self.flushEvery):
            nd = {'name': x[1]}
            if x[2]: nd['country'] = x[2]
            name = build_company_name(nd)
            dict.__setitem__(self, name, x[0])
        self.counter = counter(CompanyName.select().count() + 1)
        CompanyName.sqlmeta.cacheValues = _oldcacheValues

    def _toDB(self, quiet=0):
        if not quiet:
            print ' * FLUSHING CompaniesCache...'
            sys.stdout.flush()
        l = []
        lapp = l.append
        tmpDictiter = self._tmpDict.iteritems
        for k, v in tmpDictiter():
            try:
                t = analyze_company_name(k)
            except IMDbParserError:
                if k and k.strip():
                    print 'WARNING CompaniesCache._toDB() invalid name:', _(k)
                continue
            tget = t.get
            name = tget('name')
            namePcodeNf = soundex(name)
            namePcodeSf = None
            country = tget('country')
            if k != name:
                namePcodeSf = soundex(k)
            lapp((v, name, country, None, namePcodeNf, namePcodeSf,
                    md5(k).hexdigest()))
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(l))
        else:
            CSV_CURS.executemany(self.sqlstr, l)


class KeywordsCache(_BaseCache):
    """Manage the list of keywords."""
    counter = counter()
    className = 'KeywordsCache'

    def __init__(self, *args, **kwds):
        _BaseCache.__init__(self, *args, **kwds)
        self._table_name = tableName(CompanyName)
        self._id_for_custom_q = 'KEYWORDS'
        self.flushEvery = 10000
        self.sqlstr, self.converter = createSQLstr(Keyword, ['id', 'keyword',
                                'phoneticCode'])

    def populate(self):
        print ' * POPULATING KeywordsCache...'
        nameTbl = tableName(CompanyName)
        keywordidCol = colName(Keyword, 'id')
        keyCol = colName(Keyword, 'name')
        CURS.execute('SELECT %s, %s FROM %s;' % (keywordidCol, keyCol,
                                                    nameTbl))
        _oldcacheValues = Keyword.sqlmeta.cacheValues
        Keyword.sqlmeta.cacheValues = False
        for x in fetchsome(CURS, self.flushEvery):
            dict.__setitem__(self, x[1], x[0])
        self.counter = counter(Keyword.select().count() + 1)
        Keyword.sqlmeta.cacheValues = _oldcacheValues

    def _toDB(self, quiet=0):
        if not quiet:
            print ' * FLUSHING KeywordsCache...'
            sys.stdout.flush()
        l = []
        lapp = l.append
        tmpDictiter = self._tmpDict.iteritems
        for k, v in tmpDictiter():
            keySoundex = soundex(k)
            lapp((v, k, keySoundex))
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(l))
        else:
            CSV_CURS.executemany(self.sqlstr, l)


class SQLData(dict):
    """Variable set of information, to be stored from time to time
    to the SQL database."""
    def __init__(self, table=None, cols=None, sqlString='', converter=None,
                d={}, flushEvery=20000, counterInit=1):
        if not sqlString:
            if not (table and cols):
                raise TypeError('"table" or "cols" unspecified')
            sqlString, converter = createSQLstr(table, cols)
        elif converter is None:
            raise TypeError('"sqlString" or "converter" unspecified')
        dict.__init__(self)
        self.counterInit = counterInit
        self.counter = counterInit
        self.flushEvery = flushEvery
        self.sqlString = sqlString
        self.converter = converter
        self._recursionLevel = 1
        self._table = table
        self._table_name = tableName(table)
        for k, v in d.items(): self[k] = v

    def __setitem__(self, key, value):
        """The value is discarded, the counter is used as the 'real' key
        and the user's 'key' is used as its values."""
        counter = self.counter
        if counter % self.flushEvery == 0:
            self.flush()
        dict.__setitem__(self, counter, key)
        self.counter += 1

    def add(self, key):
        self[key] = None

    def flush(self, _resetRecursion=1):
        if not self: return
        # XXX: it's safer to flush MoviesCache and PersonsCache, to preserve
        #      consistency of ForeignKey, but it can also slow down everything
        #      a bit...
        CACHE_MID.flush(quiet=1)
        CACHE_PID.flush(quiet=1)
        if _resetRecursion: self._recursionLevel = 1
        if self._recursionLevel >= MAX_RECURSION:
            print 'WARNING recursion level exceded trying to flush data'
            print 'WARNING this batch of data is lost.'
            self.clear()
            self.counter = self.counterInit
            return
        keys = {'table': self._table_name}
        _after_has_run = False
        try:
            executeCustomQueries('BEFORE_SQLDATA_TODB', _keys=keys,
                                _timeit=False)
            self._toDB()
            executeCustomQueries('AFTER_SQLDATA_TODB', _keys=keys,
                                _timeit=False)
            _after_has_run = True
            self.clear()
            self.counter = self.counterInit
        except OperationalError, e:
            if not _after_has_run:
                executeCustomQueries('AFTER_SQLDATA_TODB', _keys=keys,
                                    _timeit=False)
            print ' * TOO MANY DATA (%s items), SPLITTING (run #%d)...' % \
                    (len(self), self._recursionLevel)
            self._recursionLevel += 1
            newdata = self.__class__(table=self._table,
                                    sqlString=self.sqlString,
                                    converter=self.converter)
            newdata._recursionLevel = self._recursionLevel
            newflushEvery = self.flushEvery / 2
            if newflushEvery < 1:
                print 'WARNING recursion level exceded trying to flush data'
                print 'WARNING this batch of data is lost.'
                self.clear()
                self.counter = self.counterInit
                return
            self.flushEvery = newflushEvery
            newdata.flushEvery = newflushEvery
            popitem = self.popitem
            dsi = dict.__setitem__
            for x in xrange(len(self)/2):
                k, v = popitem()
                dsi(newdata, k, v)
            newdata.flush(_resetRecursion=0)
            del newdata
            self.flush(_resetRecursion=0)
            self.clear()
            self.counter = self.counterInit
        except Exception, e:
            if isinstance(e, KeyboardInterrupt):
                raise
            print 'WARNING: unknown exception caught committing the data'
            print 'WARNING: to the database; report this as a bug, since'
            print 'WARNING: many data (%d items) were lost: %s' % \
                    (len(self), e)
        connectObject.commit()

    def _toDB(self):
        print ' * FLUSHING SQLData...'
        if not CSV_DIR:
            CURS.executemany(self.sqlString, self.converter(self.values()))
        else:
            CSV_CURS.executemany(self.sqlString, self.values())


# Miscellaneous functions.

def unpack(line, headers, sep='\t'):
    """Given a line, split at seps and return a dictionary with key
    from the header list.
    E.g.:
        line = '      0000000124    8805   8.4  Incredibles, The (2004)'
        header = ('votes distribution', 'votes', 'rating', 'title')
        seps=('  ',)

    will returns: {'votes distribution': '0000000124', 'votes': '8805',
                    'rating': '8.4', 'title': 'Incredibles, The (2004)'}
    """
    r = {}
    ls1 = filter(None, line.split(sep))
    for index, item in enumerate(ls1):
        try: name = headers[index]
        except IndexError: name = 'item%s' % index
        r[name] = item.strip()
    return r

def _parseMinusList(fdata):
    """Parse a list of lines starting with '- '."""
    rlist = []
    tmplist = []
    for line in fdata:
        if line and line[:2] == '- ':
            if tmplist: rlist.append(' '.join(tmplist))
            l = line[2:].strip()
            if l: tmplist[:] = [l]
            else: tmplist[:] = []
        else:
            l = line.strip()
            if l: tmplist.append(l)
    if tmplist: rlist.append(' '.join(tmplist))
    return rlist


def _parseColonList(lines, replaceKeys):
    """Parser for lists with "TAG: value" strings."""
    out = {}
    for line in lines:
        line = line.strip()
        if not line: continue
        cols = line.split(':', 1)
        if len(cols) < 2: continue
        k = cols[0]
        k = replaceKeys.get(k, k)
        v = ' '.join(cols[1:]).strip()
        if k not in out: out[k] = []
        out[k].append(v)
    return out


# Functions used to manage data files.

def readMovieList():
    """Read the movies.list.gz file."""
    try: mdbf = SourceFile(MOVIES, start=MOVIES_START, stop=MOVIES_STOP)
    except IOError: return
    count = 0
    for line in mdbf:
        line_d = unpack(line, ('title', 'year'))
        title = line_d['title']
        yearData = None
        # Collect 'year' column for tv "series years" and episodes' year.
        if title[0] == '"':
            yearData = [('movieYear', line_d['year'])]
        mid = CACHE_MID.addUnique(title, yearData)
        if mid is None:
            continue
        if count % 10000 == 0:
            print 'SCANNING movies:', _(title),
            print '(movieID: %s)' % mid
        count += 1
    CACHE_MID.flush()
    CACHE_MID.movieYear.clear()
    mdbf.close()


def doCast(fp, roleid, rolename):
    """Populate the cast table."""
    pid = None
    count = 0
    name = ''
    roleidVal = RawValue('roleID', roleid)
    sqldata = SQLData(table=CastInfo, cols=['personID', 'movieID',
                        'personRoleID', 'note', 'nrOrder', roleidVal])
    if rolename == 'miscellaneous crew': sqldata.flushEvery = 10000
    for line in fp:
        if line and line[0] != '\t':
            if line[0] == '\n': continue
            sl = filter(None, line.split('\t'))
            if len(sl) != 2: continue
            name, line = sl
            miscData = None
            if rolename == 'actor':
                miscData = [('personGender', 'm')]
            elif rolename == 'actress':
                miscData = [('personGender', 'f')]
            pid = CACHE_PID.addUnique(name.strip(), miscData)
        line = line.strip()
        ll = line.split('  ')
        title = ll[0]
        note = None
        role = None
        order = None
        for item in ll[1:]:
            if not item: continue
            if item[0] == '[':
                # Quite inefficient, but there are some very strange
                # cases of garbage in the plain text data files to handle...
                role = item[1:]
                if role[-1:] == ']':
                    role = role[:-1]
                if role[-1:] == ')':
                    nidx = role.find('(')
                    if nidx != -1:
                        note = role[nidx:]
                        role = role[:nidx].rstrip()
                        if not role: role = None
            elif item[0] == '(':
                if note is None:
                    note = item
                else:
                    note = '%s %s' % (note, item)
            elif item[0] == '<':
                textor = item[1:-1]
                try:
                    order = long(textor)
                except ValueError:
                    os = textor.split(',')
                    if len(os) == 3:
                        try:
                            order = ((long(os[2])-1) * 1000) + \
                                    ((long(os[1])-1) * 100) + (long(os[0])-1)
                        except ValueError:
                            pass
        movieid = CACHE_MID.addUnique(title)
        if movieid is None:
            continue
        if role is not None:
            roles = filter(None, [x.strip() for x in role.split('/')])
            for role in roles:
                cid = CACHE_CID.addUnique(role)
                sqldata.add((pid, movieid, cid, note, order))
        else:
            sqldata.add((pid, movieid, None, note, order))
        if count % 10000 == 0:
            print 'SCANNING %s:' % rolename,
            print _(name)
        count += 1
    sqldata.flush()
    CACHE_PID.flush()
    CACHE_PID.personGender.clear()
    print 'CLOSING %s...' % rolename


def castLists():
    """Read files listed in the 'role' column of the 'roletypes' table."""
    rt = [(x.id, x.role) for x in RoleType.select()]
    for roleid, rolename in rt:
        if rolename == 'guest':
            continue
        fname = rolename
        fname = fname.replace(' ', '-')
        if fname == 'actress': fname = 'actresses.list.gz'
        elif fname == 'miscellaneous-crew': fname = 'miscellaneous.list.gz'
        else: fname = fname + 's.list.gz'
        print 'DOING', fname
        try:
            f = SourceFile(fname, start=CAST_START, stop=CAST_STOP)
        except IOError:
            if rolename == 'actress':
                CACHE_CID.flush()
                if not CSV_DIR:
                    CACHE_CID.clear()
            continue
        doCast(f, roleid, rolename)
        f.close()
        if rolename == 'actress':
            CACHE_CID.flush()
            if not CSV_DIR:
                CACHE_CID.clear()
        t('castLists(%s)' % rolename)


def doAkaNames():
    """People's akas."""
    pid = None
    count = 0
    try: fp = SourceFile('aka-names.list.gz', start=AKAN_START)
    except IOError: return
    sqldata = SQLData(table=AkaName, cols=['personID', 'name', 'imdbIndex',
                            'namePcodeCf', 'namePcodeNf', 'surnamePcode',
                            'md5sum'])
    for line in fp:
        if line and line[0] != ' ':
            if line[0] == '\n': continue
            pid = CACHE_PID.addUnique(line.strip())
        else:
            line = line.strip()
            if line[:5] == '(aka ': line = line[5:]
            if line[-1:] == ')': line = line[:-1]
            try:
                name_dict = analyze_name(line)
            except IMDbParserError:
                if line: print 'WARNING doAkaNames wrong name:', _(line)
                continue
            name = name_dict.get('name')
            namePcodeCf, namePcodeNf, surnamePcode = name_soundexes(name)
            sqldata.add((pid, name, name_dict.get('imdbIndex'),
                        namePcodeCf, namePcodeNf, surnamePcode,
                        md5(line).hexdigest()))
            if count % 10000 == 0:
                print 'SCANNING akanames:', _(line)
            count += 1
    sqldata.flush()
    fp.close()


class AkasMoviesCache(MoviesCache):
    """A MoviesCache-like class used to populate the AkaTitle table."""
    className = 'AkasMoviesCache'
    counter = counter()

    def __init__(self, *args, **kdws):
        MoviesCache.__init__(self, *args, **kdws)
        self.flushEvery = 50000
        self._mapsIDsToTitles = True
        self.notes = {}
        self.ids = {}
        self._table_name = tableName(AkaTitle)
        self._id_for_custom_q = 'AKAMOVIES'
        self.sqlstr, self.converter = createSQLstr(AkaTitle, ('id', 'movieID',
                            'title', 'imdbIndex', 'kindID', 'productionYear',
                            'phoneticCode', 'episodeOfID', 'seasonNr',
                            'episodeNr', 'note', 'md5sum'))

    def flush(self, *args, **kwds):
        # Preserve consistency of ForeignKey.
        CACHE_MID.flush(quiet=1)
        super(AkasMoviesCache, self).flush(*args, **kwds)

    def _runCommand(self, dataList):
        new_dataList = []
        new_dataListapp = new_dataList.append
        while dataList:
            item = list(dataList.pop())
            # Remove the imdbID.
            del item[5]
            # id used to store this entry.
            the_id = item[0]
            # id of the referred title.
            original_title_id = self.ids.get(the_id) or 0
            new_item = [the_id, original_title_id]
            md5sum = item[-1]
            new_item += item[1:-2]
            new_item.append(self.notes.get(the_id))
            new_item.append(md5sum)
            new_dataListapp(tuple(new_item))
        new_dataList.reverse()
        if not CSV_DIR:
            CURS.executemany(self.sqlstr, self.converter(new_dataList))
        else:
            CSV_CURS.executemany(self.sqlstr, new_dataList)
CACHE_MID_AKAS = AkasMoviesCache()


def doAkaTitles():
    """Movies' akas."""
    mid = None
    count = 0
    for fname, start in (('aka-titles.list.gz',AKAT_START),
                    ('italian-aka-titles.list.gz',AKAT_IT_START),
                    ('german-aka-titles.list.gz',AKAT_DE_START),
                    ('iso-aka-titles.list.gz',AKAT_ISO_START),
                    (os.path.join('contrib','hungarian-aka-titles.list.gz'),
                        AKAT_HU_START),
                    (os.path.join('contrib','norwegian-aka-titles.list.gz'),
                        AKAT_NO_START)):
        incontrib = 0
        pwarning = 1
        # Looks like that the only up-to-date AKA file is aka-titles.
        obsolete = False
        if fname != 'aka-titles.list.gz':
            obsolete = True
        if start in (AKAT_HU_START, AKAT_NO_START):
            pwarning = 0
            incontrib = 1
        try:
            fp = SourceFile(fname, start=start,
                            stop='---------------------------',
                            pwarning=pwarning)
        except IOError:
            continue
        isEpisode = False
        seriesID = None
        doNotAdd = False
        for line in fp:
            if line and line[0] != ' ':
                # Reading the official title.
                doNotAdd = False
                if line[0] == '\n': continue
                line = line.strip()
                if obsolete:
                    try:
                        tonD = analyze_title(line, _emptyString='')
                    except IMDbParserError:
                        if line:
                            print 'WARNING doAkaTitles(obsol O) invalid title:',
                            print _(line)
                        continue
                    tonD['title'] = normalizeTitle(tonD['title'])
                    line = build_title(tonD, ptdf=1, _emptyString='')
                    # Aka information for titles in obsolete files are
                    # added only if the movie already exists in the cache.
                    if line not in CACHE_MID:
                        doNotAdd = True
                        continue
                mid = CACHE_MID.addUnique(line)
                if mid is None:
                    continue
                if line[0] == '"':
                    try:
                        titleDict = analyze_title(line, _emptyString='')
                    except IMDbParserError:
                        if line:
                            print 'WARNING doAkaTitles (O) invalid title:',
                            print _(line)
                        continue
                    if 'episode of' in titleDict:
                        if obsolete:
                            titleDict['episode of']['title'] = \
                                normalizeTitle(titleDict['episode of']['title'])
                        series = build_title(titleDict['episode of'],
                                            ptdf=1, _emptyString='')
                        seriesID = CACHE_MID.addUnique(series)
                        if seriesID is None:
                            continue
                        isEpisode = True
                    else:
                        seriesID = None
                        isEpisode = False
                else:
                    seriesID = None
                    isEpisode = False
            else:
                # Reading an aka title.
                if obsolete and doNotAdd:
                    continue
                res = unpack(line.strip(), ('title', 'note'))
                note = res.get('note')
                if incontrib:
                    if res.get('note'): note += ' '
                    else: note = ''
                    if start == AKAT_HU_START: note += '(Hungary)'
                    elif start == AKAT_NO_START: note += '(Norway)'
                akat = res.get('title', '')
                if akat[:5] == '(aka ': akat = akat[5:]
                if akat[-2:] in ('))', '})'): akat = akat[:-1]
                akat = akat.strip()
                if not akat:
                    continue
                if obsolete:
                    try:
                        akatD = analyze_title(akat, _emptyString='')
                    except IMDbParserError:
                        if line:
                            print 'WARNING doAkaTitles(obsol) invalid title:',
                            print _(akat)
                        continue
                    akatD['title'] = normalizeTitle(akatD['title'])
                    akat = build_title(akatD, ptdf=1, _emptyString='')
                if count % 10000 == 0:
                    print 'SCANNING %s:' % fname[:-8].replace('-', ' '),
                    print _(akat)
                if isEpisode and seriesID is not None:
                    # Handle series for which only single episodes have
                    # aliases.
                    try:
                        akaDict = analyze_title(akat, _emptyString='')
                    except IMDbParserError:
                        if line:
                            print 'WARNING doAkaTitles (epis) invalid title:',
                            print _(akat)
                        continue
                    if 'episode of' in akaDict:
                        if obsolete:
                            akaDict['episode of']['title'] = normalizeTitle(
                                            akaDict['episode of']['title'])
                        akaSeries = build_title(akaDict['episode of'], ptdf=1)
                        CACHE_MID_AKAS.add(akaSeries, [('ids', seriesID)])
                append_data = [('ids', mid)]
                if note is not None:
                    append_data.append(('notes', note))
                CACHE_MID_AKAS.add(akat, append_data)
                count += 1
        fp.close()
    CACHE_MID_AKAS.flush()
    CACHE_MID_AKAS.clear()
    CACHE_MID_AKAS.notes.clear()
    CACHE_MID_AKAS.ids.clear()


def doMovieLinks():
    """Connections between movies."""
    mid = None
    count = 0
    sqldata = SQLData(table=MovieLink,
                cols=['movieID', 'linkedMovieID', 'linkTypeID'],
                flushEvery=10000)
    try: fp = SourceFile('movie-links.list.gz', start=LINK_START)
    except IOError: return
    for line in fp:
        if line and line[0] != ' ':
            if line[0] == '\n': continue
            title = line.strip()
            mid = CACHE_MID.addUnique(title)
            if mid is None:
                continue
            if count % 10000 == 0:
                print 'SCANNING movielinks:', _(title)
        else:
            line = line.strip()
            link_txt = unicode(line, 'utf_8').encode('ascii', 'replace')
            theid = None
            for k, lenkp1, v in MOVIELINK_IDS:
                if link_txt and link_txt[0] == '(' \
                        and link_txt[1:lenkp1+1] == k:
                    theid = v
                    break
            if theid is None: continue
            totitle = line[lenkp1+2:-1].strip()
            totitleid = CACHE_MID.addUnique(totitle)
            if totitleid is None:
                continue
            sqldata.add((mid, totitleid, theid))
        count += 1
    sqldata.flush()
    fp.close()


def minusHashFiles(fp, funct, defaultid, descr):
    """A file with lines starting with '# ' and '- '."""
    sqldata = SQLData(table=MovieInfo,
                        cols=['movieID', 'infoTypeID', 'info', 'note'])
    sqldata.flushEvery = 2500
    if descr == 'quotes': sqldata.flushEvery = 4000
    elif descr == 'soundtracks': sqldata.flushEvery = 3000
    elif descr == 'trivia': sqldata.flushEvery = 3000
    count = 0
    for title, text in fp.getByHashSections():
        title = title.strip()
        d = funct(text.split('\n'))
        if not d:
            print 'WARNING skipping empty information about title:',
            print _(title)
            continue
        if not title:
            print 'WARNING skipping information associated to empty title:',
            print _(d[0], truncateAt=40)
            continue
        mid = CACHE_MID.addUnique(title)
        if mid is None:
            continue
        if count % 5000 == 0:
            print 'SCANNING %s:' % descr,
            print _(title)
        for data in d:
            sqldata.add((mid, defaultid, data, None))
        count += 1
    sqldata.flush()


def doMinusHashFiles():
    """Files with lines starting with '# ' and '- '."""
    for fname, start in [('alternate versions',AV_START),
                         ('goofs',GOOFS_START), ('crazy credits',CC_START),
                         ('quotes',QUOTES_START),
                         ('soundtracks',SNDT_START),
                         ('trivia',TRIV_START)]:
        try:
            fp = SourceFile(fname.replace(' ', '-')+'.list.gz', start=start,
                        stop=MINHASH_STOP)
        except IOError:
            continue
        funct = _parseMinusList
        if fname == 'quotes': funct = getQuotes
        index = fname
        if index == 'soundtracks': index = 'soundtrack'
        minusHashFiles(fp, funct, INFO_TYPES[index], fname)
        fp.close()


def getTaglines():
    """Movie's taglines."""
    try: fp = SourceFile('taglines.list.gz', start=TAGL_START, stop=TAGL_STOP)
    except IOError: return
    sqldata = SQLData(table=MovieInfo,
                cols=['movieID', 'infoTypeID', 'info', 'note'],
                flushEvery=10000)
    count = 0
    for title, text in fp.getByHashSections():
        title = title.strip()
        mid = CACHE_MID.addUnique(title)
        if mid is None:
            continue
        for tag in text.split('\n'):
            tag = tag.strip()
            if not tag: continue
            if count % 10000 == 0:
                print 'SCANNING taglines:', _(title)
            sqldata.add((mid, INFO_TYPES['taglines'], tag, None))
        count += 1
    sqldata.flush()
    fp.close()


def getQuotes(lines):
    """Movie's quotes."""
    quotes = []
    qttl = []
    for line in lines:
        if line and line[:2] == '  ' and qttl and qttl[-1] and \
                not qttl[-1].endswith('::'):
            line = line.lstrip()
            if line: qttl[-1] += ' %s' % line
        elif not line.strip():
            if qttl: quotes.append('::'.join(qttl))
            qttl[:] = []
        else:
            line = line.lstrip()
            if line: qttl.append(line)
    if qttl: quotes.append('::'.join(qttl))
    return quotes


_bus = {'BT': 'budget',
        'WG': 'weekend gross',
        'GR': 'gross',
        'OW': 'opening weekend',
        'RT': 'rentals',
        'AD': 'admissions',
        'SD': 'filming dates',
        'PD': 'production dates',
        'ST': 'studios',
        'CP': 'copyright holder'
}
_usd = '$'
_gbp = unichr(0x00a3).encode('utf_8')
_eur = unichr(0x20ac).encode('utf_8')
def getBusiness(lines):
    """Movie's business information."""
    bd = _parseColonList(lines, _bus)
    for k in bd.keys():
        nv = []
        for v in bd[k]:
            v = v.replace('USD ',_usd).replace('GBP ',_gbp).replace('EUR',_eur)
            nv.append(v)
        bd[k] = nv
    return bd


_ldk = {'OT': 'original title',
        'PC': 'production country',
        'YR': 'year',
        'CF': 'certification',
        'CA': 'category',
        'GR': 'group genre',
        'LA': 'language',
        'SU': 'subtitles',
        'LE': 'length',
        'RD': 'release date',
        'ST': 'status of availablility',
        'PR': 'official retail price',
        'RC': 'release country',
        'VS': 'video standard',
        'CO': 'color information',
        'SE': 'sound encoding',
        'DS': 'digital sound',
        'AL': 'analog left',
        'AR': 'analog right',
        'MF': 'master format',
        'PP': 'pressing plant',
        'SZ': 'disc size',
        'SI': 'number of sides',
        'DF': 'disc format',
        'PF': 'picture format',
        'AS': 'aspect ratio',
        'CC': 'close captions-teletext-ld-g',
        'CS': 'number of chapter stops',
        'QP': 'quality program',
        'IN': 'additional information',
        'SL': 'supplement',
        'RV': 'review',
        'V1': 'quality of source',
        'V2': 'contrast',
        'V3': 'color rendition',
        'V4': 'sharpness',
        'V5': 'video noise',
        'V6': 'video artifacts',
        'VQ': 'video quality',
        'A1': 'frequency response',
        'A2': 'dynamic range',
        'A3': 'spaciality',
        'A4': 'audio noise',
        'A5': 'dialogue intellegibility',
        'AQ': 'audio quality',
        'LN': 'number',
        'LB': 'label',
        'CN': 'catalog number',
        'LT': 'laserdisc title'
}
# Handle laserdisc keys.
for key, value in _ldk.items():
    _ldk[key] = 'LD %s' % value

def getLaserDisc(lines):
    """Laserdisc information."""
    d = _parseColonList(lines, _ldk)
    for k, v in d.iteritems():
        d[k] = ' '.join(v)
    return d


_lit = {'SCRP': 'screenplay-teleplay',
        'NOVL': 'novel',
        'ADPT': 'adaption',
        'BOOK': 'book',
        'PROT': 'production process protocol',
        'IVIW': 'interviews',
        'CRIT': 'printed media reviews',
        'ESSY': 'essays',
        'OTHR': 'other literature'
}
def getLiterature(lines):
    """Movie's literature information."""
    return _parseColonList(lines, _lit)


_mpaa = {'RE': 'mpaa'}
def getMPAA(lines):
    """Movie's mpaa information."""
    d = _parseColonList(lines, _mpaa)
    for k, v in d.iteritems():
        d[k] = ' '.join(v)
    return d


re_nameImdbIndex = re.compile(r'\(([IVXLCDM]+)\)')

def nmmvFiles(fp, funct, fname):
    """Files with sections separated by 'MV: ' or 'NM: '."""
    count = 0
    sqlsP = (PersonInfo, ['personID', 'infoTypeID', 'info', 'note'])
    sqlsM = (MovieInfo, ['movieID', 'infoTypeID', 'info', 'note'])

    if fname == 'biographies.list.gz':
        datakind = 'person'
        sqls = sqlsP
        guestid = RoleType.select(RoleType.q.role == 'guest')[0].id
        roleid = str(guestid)
        guestdata = SQLData(table=CastInfo,
                cols=['personID', 'movieID', 'personRoleID', 'note',
                RawValue('roleID', roleid)], flushEvery=10000)
        akanamesdata = SQLData(table=AkaName, cols=['personID', 'name',
                'imdbIndex', 'namePcodeCf', 'namePcodeNf', 'surnamePcode',
                'md5sum'])
    else:
        datakind = 'movie'
        sqls = sqlsM
        guestdata = None
        akanamesdata = None
    sqldata = SQLData(table=sqls[0], cols=sqls[1])
    if fname == 'plot.list.gz': sqldata.flushEvery = 1100
    elif fname == 'literature.list.gz': sqldata.flushEvery = 5000
    elif fname == 'business.list.gz': sqldata.flushEvery = 10000
    elif fname == 'biographies.list.gz': sqldata.flushEvery = 5000
    islaserdisc = False
    if fname == 'laserdisc.list.gz':
        islaserdisc = True
    _ltype = type([])
    for ton, text in fp.getByNMMVSections():
        ton = ton.strip()
        if not ton: continue
        note = None
        if datakind == 'movie':
            if islaserdisc:
                tonD = analyze_title(ton, _emptyString='')
                tonD['title'] = normalizeTitle(tonD['title'])
                ton = build_title(tonD, ptdf=1, _emptyString='')
                # Skips movies that are not already in the cache, since
                # laserdisc.list.gz is an obsolete file.
                if ton not in CACHE_MID:
                    continue
            mopid = CACHE_MID.addUnique(ton)
            if mopid is None:
                continue
        else: mopid = CACHE_PID.addUnique(ton)
        if count % 6000 == 0:
            print 'SCANNING %s:' % fname[:-8].replace('-', ' '),
            print _(ton)
        d = funct(text.split('\n'))
        for k, v in d.iteritems():
            if k != 'notable tv guest appearances':
                theid = INFO_TYPES.get(k)
                if theid is None:
                    print 'WARNING key "%s" of ToN' % k,
                    print _(ton),
                    print 'not in INFO_TYPES'
                    continue
            if type(v) is _ltype:
                for i in v:
                    if k == 'notable tv guest appearances':
                        # Put "guest" information in the cast table; these
                        # are a list of Movie object (yes, imdb.Movie.Movie)
                        # FIXME: no more used?
                        title = i.get('long imdb canonical title')
                        if not title: continue
                        movieid = CACHE_MID.addUnique(title)
                        if movieid is None:
                            continue
                        crole = i.currentRole
                        if isinstance(crole, list):
                            crole = ' / '.join([x.get('long imdb name', u'')
                                                for x in crole])
                        if not crole:
                            crole = None
                        else:
                            crole = unicode(crole).encode('utf_8')
                        guestdata.add((mopid, movieid, crole,
                                        i.notes or None))
                        continue
                    if k in ('plot', 'mini biography'):
                        s = i.split('::')
                        if len(s) == 2:
                            #if note: note += ' '
                            #else: note = ''
                            #note += '(author: %s)' % s[1]
                            note = s[1]
                            i = s[0]
                    if i: sqldata.add((mopid, theid, i, note))
                    note = None
            else:
                if v: sqldata.add((mopid, theid, v, note))
            if k in ('nick names', 'birth name') and v:
                # Put also the birth name/nick names in the list of aliases.
                if k == 'birth name': realnames = [v]
                else: realnames = v
                for realname in realnames:
                    imdbIndex = re_nameImdbIndex.findall(realname) or None
                    if imdbIndex:
                        imdbIndex = imdbIndex[0]
                        realname = re_nameImdbIndex.sub('', realname)
                    if realname:
                        # XXX: check for duplicates?
                        ##if k == 'birth name':
                        ##    realname = canonicalName(realname)
                        ##else:
                        ##    realname = normalizeName(realname)
                        namePcodeCf, namePcodeNf, surnamePcode = \
                                    name_soundexes(realname)
                        akanamesdata.add((mopid, realname, imdbIndex,
                                    namePcodeCf, namePcodeNf, surnamePcode,
                                    md5(realname).hexdigest()))
        count += 1
    if guestdata is not None: guestdata.flush()
    if akanamesdata is not None: akanamesdata.flush()
    sqldata.flush()


# ============
# Code from the old 'local' data access system.

def _parseList(l, prefix, mline=1):
    """Given a list of lines l, strips prefix and join consecutive lines
    with the same prefix; if mline is True, there can be multiple info with
    the same prefix, and the first line starts with 'prefix: * '."""
    resl = []
    reslapp = resl.append
    ltmp = []
    ltmpapp = ltmp.append
    fistl = '%s: * ' % prefix
    otherl = '%s:   ' % prefix
    if not mline:
        fistl = fistl[:-2]
        otherl = otherl[:-2]
    firstlen = len(fistl)
    otherlen = len(otherl)
    parsing = 0
    joiner = ' '.join
    for line in l:
        if line[:firstlen] == fistl:
            parsing = 1
            if ltmp:
                reslapp(joiner(ltmp))
                ltmp[:] = []
            data = line[firstlen:].strip()
            if data: ltmpapp(data)
        elif mline and line[:otherlen] == otherl:
            data = line[otherlen:].strip()
            if data: ltmpapp(data)
        else:
            if ltmp:
                reslapp(joiner(ltmp))
                ltmp[:] = []
            if parsing:
                if ltmp: reslapp(joiner(ltmp))
                break
    return resl


def _parseBioBy(l):
    """Return a list of biographies."""
    bios = []
    biosappend = bios.append
    tmpbio = []
    tmpbioappend = tmpbio.append
    joiner = ' '.join
    for line in l:
        if line[:4] == 'BG: ':
            tmpbioappend(line[4:].strip())
        elif line[:4] == 'BY: ':
            if tmpbio:
                biosappend(joiner(tmpbio) + '::' + line[4:].strip())
                tmpbio[:] = []
    # Cut mini biographies up to 2**16-1 chars, to prevent errors with
    # some MySQL versions - when used by the imdbpy2sql.py script.
    bios[:] = [bio[:65535] for bio in bios]
    return bios


def _parseBiography(biol):
    """Parse the biographies.data file."""
    res = {}
    bio = ' '.join(_parseList(biol, 'BG', mline=0))
    bio = _parseBioBy(biol)
    if bio: res['mini biography'] = bio

    for x in biol:
        x4 = x[:4]
        x6 = x[:6]
        if x4 == 'DB: ':
            date, notes = date_and_notes(x[4:])
            if date:
                res['birth date'] = date
            if notes:
                res['birth notes'] = notes
        elif x4 == 'DD: ':
            date, notes = date_and_notes(x[4:])
            if date:
                res['death date'] = date
            if notes:
                res['death notes'] = notes
        elif x6 == 'SP: * ':
            res.setdefault('spouse', []).append(x[6:].strip())
        elif x4 == 'RN: ':
            n = x[4:].strip()
            if not n: continue
            try:
                rn = build_name(analyze_name(n, canonical=1), canonical=1)
                res['birth name'] = rn
            except IMDbParserError:
                if line: print 'WARNING _parseBiography wrong name:', _(n)
                continue
        elif x6 == 'AT: * ':
            res.setdefault('article', []).append(x[6:].strip())
        elif x4 == 'HT: ':
            res['height'] = x[4:].strip()
        elif x6 == 'PT: * ':
            res.setdefault('pictorial', []).append(x[6:].strip())
        elif x6 == 'CV: * ':
            res.setdefault('magazine cover photo', []).append(x[6:].strip())
        elif x4 == 'NK: ':
            res.setdefault('nick names', []).append(normalizeName(x[4:]))
        elif x6 == 'PI: * ':
            res.setdefault('portrayed in', []).append(x[6:].strip())
        elif x6 == 'SA: * ':
            sal = x[6:].strip().replace(' -> ', '::')
            res.setdefault('salary history', []).append(sal)
    trl = _parseList(biol, 'TR')
    if trl: res['trivia'] = trl
    quotes = _parseList(biol, 'QU')
    if quotes: res['quotes'] = quotes
    otherworks = _parseList(biol, 'OW')
    if otherworks: res['other works'] = otherworks
    books = _parseList(biol, 'BO')
    if books: res['books'] = books
    agent = _parseList(biol, 'AG')
    if agent: res['agent address'] = agent
    wherenow = _parseList(biol, 'WN')
    if wherenow: res['where now'] = wherenow[0]
    biomovies = _parseList(biol, 'BT')
    if biomovies: res['biographical movies'] = biomovies
    tm = _parseList(biol, 'TM')
    if tm: res['trade mark'] = tm
    interv = _parseList(biol, 'IT')
    if interv: res['interviews'] = interv
    return res

# ============


def doNMMVFiles():
    """Files with large sections, about movies and persons."""
    for fname, start, funct in [
            ('biographies.list.gz', BIO_START, _parseBiography),
            ('business.list.gz', BUS_START, getBusiness),
            ('laserdisc.list.gz', LSD_START, getLaserDisc),
            ('literature.list.gz', LIT_START, getLiterature),
            ('mpaa-ratings-reasons.list.gz', MPAA_START, getMPAA),
            ('plot.list.gz', PLOT_START, getPlot)]:
    ##for fname, start, funct in [('business.list.gz',BUS_START,getBusiness)]:
        try:
            fp = SourceFile(fname, start=start)
        except IOError:
            continue
        if fname == 'literature.list.gz': fp.set_stop(LIT_STOP)
        elif fname == 'business.list.gz': fp.set_stop(BUS_STOP)
        nmmvFiles(fp, funct, fname)
        fp.close()
        t('doNMMVFiles(%s)' % fname[:-8].replace('-', ' '))


def doMovieCompaniesInfo():
    """Files with information on a single line about movies,
    concerning companies."""
    sqldata = SQLData(table=MovieCompanies,
                cols=['movieID', 'companyID', 'companyTypeID', 'note'])
    for dataf in (('distributors.list.gz', DIS_START),
                    ('miscellaneous-companies.list.gz', MIS_START),
                    ('production-companies.list.gz', PRO_START),
                    ('special-effects-companies.list.gz', SFX_START)):
        try:
            fp = SourceFile(dataf[0], start=dataf[1])
        except IOError:
            continue
        typeindex = dataf[0][:-8].replace('-', ' ')
        infoid =  COMP_TYPES[typeindex]
        count = 0
        for line in fp:
            data = unpack(line.strip(), ('title', 'company', 'note'))
            if 'title' not in data: continue
            if 'company' not in data: continue
            title = data['title']
            company = data['company']
            mid = CACHE_MID.addUnique(title)
            if mid is None:
                continue
            cid = CACHE_COMPID.addUnique(company)
            note = None
            if 'note' in data:
                note = data['note']
            if count % 10000 == 0:
                print 'SCANNING %s:' % dataf[0][:-8].replace('-', ' '),
                print _(data['title'])
            sqldata.add((mid, cid, infoid, note))
            count += 1
        sqldata.flush()
        CACHE_COMPID.flush()
        fp.close()
        t('doMovieCompaniesInfo(%s)' % dataf[0][:-8].replace('-', ' '))


def doMiscMovieInfo():
    """Files with information on a single line about movies."""
    for dataf in (('certificates.list.gz',CER_START),
                    ('color-info.list.gz',COL_START),
                    ('countries.list.gz',COU_START),
                    ('genres.list.gz',GEN_START),
                    ('keywords.list.gz',KEY_START),
                    ('language.list.gz',LAN_START),
                    ('locations.list.gz',LOC_START),
                    ('running-times.list.gz',RUN_START),
                    ('sound-mix.list.gz',SOU_START),
                    ('technical.list.gz',TCN_START),
                    ('release-dates.list.gz',RELDATE_START)):
        try:
            fp = SourceFile(dataf[0], start=dataf[1])
        except IOError:
            continue
        typeindex = dataf[0][:-8].replace('-', ' ')
        if typeindex == 'running times': typeindex = 'runtimes'
        elif typeindex == 'technical': typeindex = 'tech info'
        elif typeindex == 'language': typeindex = 'languages'
        if typeindex != 'keywords':
            sqldata = SQLData(table=MovieInfo,
                        cols=['movieID', 'infoTypeID', 'info', 'note'])
        else:
            sqldata = SQLData(table=MovieKeyword,
                        cols=['movieID', 'keywordID'])
        infoid =  INFO_TYPES[typeindex]
        count = 0
        if dataf[0] == 'locations.list.gz':
            sqldata.flushEvery = 10000
        else:
            sqldata.flushEvery = 20000
        for line in fp:
            data = unpack(line.strip(), ('title', 'info', 'note'))
            if 'title' not in data: continue
            if 'info' not in data: continue
            title = data['title']
            mid = CACHE_MID.addUnique(title)
            if mid is None:
                continue
            note = None
            if 'note' in data:
                note = data['note']
            if count % 10000 == 0:
                print 'SCANNING %s:' % dataf[0][:-8].replace('-', ' '),
                print _(data['title'])
            info = data['info']
            if typeindex == 'keywords':
                keywordID = CACHE_KWRDID.addUnique(info)
                sqldata.add((mid, keywordID))
            else:
                sqldata.add((mid, infoid, info, note))
            count += 1
        sqldata.flush()
        if typeindex == 'keywords':
            CACHE_KWRDID.flush()
            CACHE_KWRDID.clear()
        fp.close()
        t('doMiscMovieInfo(%s)' % dataf[0][:-8].replace('-', ' '))


def getRating():
    """Movie's rating."""
    try: fp = SourceFile('ratings.list.gz', start=RAT_START, stop=RAT_STOP)
    except IOError: return
    sqldata = SQLData(table=MovieInfoIdx, cols=['movieID', 'infoTypeID',
                                                'info', 'note'])
    count = 0
    for line in fp:
        data = unpack(line, ('votes distribution', 'votes', 'rating', 'title'),
                        sep='  ')
        if 'title' not in data: continue
        title = data['title'].strip()
        mid = CACHE_MID.addUnique(title)
        if mid is None:
            continue
        if count % 10000 == 0:
            print 'SCANNING rating:', _(title)
        sqldata.add((mid, INFO_TYPES['votes distribution'],
                    data.get('votes distribution'), None))
        sqldata.add((mid, INFO_TYPES['votes'], data.get('votes'), None))
        sqldata.add((mid, INFO_TYPES['rating'], data.get('rating'), None))
        count += 1
    sqldata.flush()
    fp.close()


def getTopBottomRating():
    """Movie's rating, scanning for top 250 and bottom 10."""
    for what in ('top 250 rank', 'bottom 10 rank'):
        if what == 'top 250 rank': st = RAT_TOP250_START
        else: st = RAT_BOT10_START
        try: fp = SourceFile('ratings.list.gz', start=st, stop=TOPBOT_STOP)
        except IOError: break
        sqldata = SQLData(table=MovieInfoIdx,
                    cols=['movieID',
                        RawValue('infoTypeID', INFO_TYPES[what]),
                        'info', 'note'])
        count = 1
        print 'SCANNING %s...' % what
        for line in fp:
            data = unpack(line, ('votes distribution', 'votes', 'rank',
                                'title'), sep='  ')
            if 'title' not in data: continue
            title = data['title'].strip()
            mid = CACHE_MID.addUnique(title)
            if mid is None:
                continue
            if what == 'top 250 rank': rank = count
            else: rank = 11 - count
            sqldata.add((mid, str(rank), None))
            count += 1
        sqldata.flush()
        fp.close()


def getPlot(lines):
    """Movie's plot."""
    plotl = []
    plotlappend = plotl.append
    plotltmp = []
    plotltmpappend = plotltmp.append
    for line in lines:
        linestart = line[:4]
        if linestart == 'PL: ':
            plotltmpappend(line[4:])
        elif linestart == 'BY: ':
            plotlappend('%s::%s' % (' '.join(plotltmp), line[4:].strip()))
            plotltmp[:] = []
    return {'plot': plotl}


def completeCast():
    """Movie's complete cast/crew information."""
    CCKind = {}
    cckinds = [(x.id, x.kind) for x in CompCastType.select()]
    for k, v in cckinds:
        CCKind[v] = k
    for fname, start in [('complete-cast.list.gz',COMPCAST_START),
                        ('complete-crew.list.gz',COMPCREW_START)]:
        try:
            fp = SourceFile(fname, start=start, stop=COMP_STOP)
        except IOError:
            continue
        if fname == 'complete-cast.list.gz': obj = 'cast'
        else: obj = 'crew'
        subID = str(CCKind[obj])
        sqldata = SQLData(table=CompleteCast,
                cols=['movieID', RawValue('subjectID', subID),
                'statusID'])
        count = 0
        for line in fp:
            ll = [x for x in line.split('\t') if x]
            if len(ll) != 2: continue
            title = ll[0]
            mid = CACHE_MID.addUnique(title)
            if mid is None:
                continue
            if count % 10000 == 0:
                print 'SCANNING %s:' % fname[:-8].replace('-', ' '),
                print _(title)
            sqldata.add((mid, CCKind[ll[1].lower().strip()]))
            count += 1
        fp.close()
        sqldata.flush()


# global instances
CACHE_MID = MoviesCache()
CACHE_PID = PersonsCache()
CACHE_CID = CharactersCache()
CACHE_CID.className = 'CharactersCache'
CACHE_COMPID = CompaniesCache()
CACHE_KWRDID = KeywordsCache()

def _cmpfunc(x, y):
    """Sort a list of tuples, by the length of the first item (in reverse)."""
    lx = len(x[0])
    ly = len(y[0])
    if lx > ly: return -1
    elif lx < ly: return 1
    return 0

INFO_TYPES = {}
MOVIELINK_IDS = []
KIND_IDS = {}
KIND_STRS = {}
CCAST_TYPES = {}
COMP_TYPES = {}

def readConstants():
    """Read constants from the database."""
    global INFO_TYPES, MOVIELINK_IDS, KIND_IDS, KIND_STRS, \
            CCAST_TYPES, COMP_TYPES

    for x in InfoType.select():
        INFO_TYPES[x.info] = x.id

    for x in LinkType.select():
        MOVIELINK_IDS.append((x.link, len(x.link), x.id))
    MOVIELINK_IDS.sort(_cmpfunc)

    for x in KindType.select():
        KIND_IDS[x.kind] = x.id
        KIND_STRS[x.id] = x.kind

    for x in CompCastType.select():
        CCAST_TYPES[x.kind] = x.id

    for x in CompanyType.select():
        COMP_TYPES[x.kind] = x.id


def _imdbIDsFileName(fname):
    """Return a file name, adding the optional
    CSV_DIR directory."""
    return os.path.join(*(filter(None, [CSV_DIR, fname])))


def _countRows(tableName):
    """Return the number of rows in a table."""
    try:
        CURS.execute('SELECT COUNT(*) FROM %s' % tableName)
        return (CURS.fetchone() or [0])[0]
    except Exception, e:
        print 'WARNING: unable to count rows of table %s: %s' % (tableName, e)
        return 0


def storeNotNULLimdbIDs(cls):
    """Store in a temporary table or in a dbm database a mapping between
    md5sum (of title or name) and imdbID, when the latter
    is present in the database."""
    if cls is Title: cname = 'movies'
    elif cls is Name: cname = 'people'
    elif cls is CompanyName: cname = 'companies'
    else: cname = 'characters'
    table_name = tableName(cls)
    md5sum_col = colName(cls, 'md5sum')
    imdbID_col = colName(cls, 'imdbID')

    print 'SAVING imdbID values for %s...' % cname,
    sys.stdout.flush()
    if _get_imdbids_method() == 'table':
        try:
            try:
                CURS.execute('DROP TABLE %s_extract' % table_name)
            except:
                pass
            try:
                CURS.execute('SELECT * FROM %s LIMIT 1' % table_name)
            except Exception, e:
                print 'missing "%s" table (ok if this is the first run)' % table_name
                return
            query = 'CREATE TEMPORARY TABLE %s_extract AS SELECT %s, %s FROM %s WHERE %s IS NOT NULL' % \
                    (table_name, md5sum_col, imdbID_col,
                    table_name, imdbID_col)
            CURS.execute(query)
            CURS.execute('CREATE INDEX %s_md5sum_idx ON %s_extract (%s)' % (table_name, table_name, md5sum_col))
            CURS.execute('CREATE INDEX %s_imdbid_idx ON %s_extract (%s)' % (table_name, table_name, imdbID_col))
            rows = _countRows('%s_extract' % table_name)
            print 'DONE! (%d entries using a temporary table)' % rows
            return
        except Exception, e:
            print 'WARNING: unable to store imdbIDs in a temporary table (falling back to dbm): %s' % e
    try:
        db = anydbm.open(_imdbIDsFileName('%s_imdbIDs.db' % cname), 'c')
    except Exception, e:
        print 'WARNING: unable to store imdbIDs: %s' % str(e)
        return
    try:
        CURS.execute('SELECT %s, %s FROM %s WHERE %s IS NOT NULL' %
                    (md5sum_col, imdbID_col, table_name, imdbID_col))
        res = CURS.fetchmany(10000)
        while res:
            db.update(dict((str(x[0]), str(x[1])) for x in res))
            res = CURS.fetchmany(10000)
    except Exception, e:
        print 'SKIPPING: unable to retrieve data: %s' % e
        return
    print 'DONE! (%d entries)' % len(db)
    db.close()
    return


def iterbatch(iterable, size):
    """Process an iterable 'size' items at a time."""
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([batchiter.next()], batchiter)


def restoreImdbIDs(cls):
    """Restore imdbIDs for movies, people, companies and characters."""
    if cls is Title:
        cname = 'movies'
    elif cls is Name:
        cname = 'people'
    elif cls is CompanyName:
        cname = 'companies'
    else:
        cname = 'characters'
    print 'RESTORING imdbIDs values for %s...' % cname,
    sys.stdout.flush()
    table_name = tableName(cls)
    md5sum_col = colName(cls, 'md5sum')
    imdbID_col = colName(cls, 'imdbID')

    if _get_imdbids_method() == 'table':
        try:
            try:
                CURS.execute('SELECT * FROM %s_extract LIMIT 1' % table_name)
            except Exception, e:
                raise Exception('missing "%s_extract" table (ok if this is the first run)' % table_name)

            if DB_NAME == 'mysql':
                query = 'UPDATE %s INNER JOIN %s_extract USING (%s) SET %s.%s = %s_extract.%s' % \
                        (table_name, table_name, md5sum_col,
                        table_name, imdbID_col, table_name, imdbID_col)
            else:
                query = 'UPDATE %s SET %s = %s_extract.%s FROM %s_extract WHERE %s.%s = %s_extract.%s' % \
                        (table_name, imdbID_col, table_name,
                        imdbID_col, table_name, table_name,
                        md5sum_col, table_name, md5sum_col)
            CURS.execute(query)
            affected_rows = 'an unknown number of'
            try:
                CURS.execute('SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL' %
                        (table_name, imdbID_col))
                affected_rows = (CURS.fetchone() or [0])[0]
            except Exception, e:
                pass
            rows = _countRows('%s_extract' % table_name)
            print 'DONE! (restored %s entries out of %d)' % (affected_rows, rows)
            t('restore %s' % cname)
            try: CURS.execute('DROP TABLE %s_extract' % table_name)
            except: pass
            return
        except Exception, e:
            print 'WARNING: unable to restore imdbIDs using the temporary table (falling back to dbm): %s' % e
    try:
        db = anydbm.open(_imdbIDsFileName('%s_imdbIDs.db' % cname), 'r')
    except Exception, e:
        print 'WARNING: unable to restore imdbIDs (ok if this is the first run)'
        return
    count = 0
    sql = "UPDATE " + table_name + " SET " + imdbID_col + \
            " = CASE " + md5sum_col + " %s END WHERE " + \
            md5sum_col + " IN (%s)"
    def _restore(query, batch):
        """Execute a query to restore a batch of imdbIDs"""
        items = list(batch)
        case_clause = ' '.join("WHEN '%s' THEN %s" % (k, v) for k, v in items)
        where_clause = ', '.join("'%s'" % x[0] for x in items)
        success = _executeQuery(query % (case_clause, where_clause))
        if success:
            return len(items)
        return 0
    for batch in iterbatch(db.iteritems(), 10000):
        count += _restore(sql, batch)
    print 'DONE! (restored %d entries out of %d)' % (count, len(db))
    t('restore %s' % cname)
    db.close()
    return

def restoreAll_imdbIDs():
    """Restore imdbIDs for movies, persons, companies and characters."""
    # Restoring imdbIDs for movies and persons (moved after the
    # built of indexes, so that it can take advantage of them).
    runSafely(restoreImdbIDs, 'failed to restore imdbIDs for movies',
            None, Title)
    runSafely(restoreImdbIDs, 'failed to restore imdbIDs for people',
            None, Name)
    runSafely(restoreImdbIDs, 'failed to restore imdbIDs for characters',
            None, CharName)
    runSafely(restoreImdbIDs, 'failed to restore imdbIDs for companies',
            None, CompanyName)


def runSafely(funct, fmsg, default, *args, **kwds):
    """Run the function 'funct' with arguments args and
    kwds, catching every exception; fmsg is printed out (along
    with the exception message) in case of trouble; the return
    value of the function is returned (or 'default')."""
    try:
        return funct(*args, **kwds)
    except Exception, e:
        print 'WARNING: %s: %s' % (fmsg, e)
    return default


def _executeQuery(query):
    """Execute a query on the CURS object."""
    if len(query) > 60:
        s_query = query[:60] + '...'
    else:
        s_query = query
    print 'EXECUTING "%s"...' % (s_query),
    sys.stdout.flush()
    try:
        CURS.execute(query)
        print 'DONE!'
        return True
    except Exception, e:
        print 'FAILED (%s)!' % e
        return False


def executeCustomQueries(when, _keys=None, _timeit=True):
    """Run custom queries as specified on the command line."""
    if _keys is None: _keys = {}
    for query in CUSTOM_QUERIES.get(when, []):
        print 'EXECUTING "%s:%s"...' % (when, query)
        sys.stdout.flush()
        if query.startswith('FOR_EVERY_TABLE:'):
            query = query[16:]
            CURS.execute('SHOW TABLES;')
            tables = [x[0] for x in CURS.fetchall()]
            for table in tables:
                try:
                    keys = {'table': table}
                    keys.update(_keys)
                    _executeQuery(query % keys)
                    if _timeit:
                        t('%s command' % when)
                except Exception, e:
                    print 'FAILED (%s)!' % e
                    continue
        else:
            try:
                _executeQuery(query % _keys)
            except Exception, e:
                print 'FAILED (%s)!' % e
                continue
            if _timeit:
                t('%s command' % when)


def buildIndexesAndFK():
    """Build indexes and Foreign Keys."""
    executeCustomQueries('BEFORE_INDEXES')
    print 'building database indexes (this may take a while)'
    sys.stdout.flush()
    # Build database indexes.
    idx_errors = createIndexes(DB_TABLES)
    for idx_error in idx_errors:
        print 'ERROR caught exception creating an index: %s' % idx_error
    t('createIndexes()')
    print 'adding foreign keys (this may take a while)'
    sys.stdout.flush()
    # Add FK.
    fk_errors = createForeignKeys(DB_TABLES)
    for fk_error in fk_errors:
        print 'ERROR caught exception creating a foreign key: %s' % fk_error
    t('createForeignKeys()')


def restoreCSV():
    """Only restore data from a set of CSV files."""
    CSV_CURS.buildFakeFileNames()
    print 'loading CSV files into the database'
    executeCustomQueries('BEFORE_CSV_LOAD')
    loadCSVFiles()
    t('loadCSVFiles()')
    executeCustomQueries('BEFORE_RESTORE')
    t('TOTAL TIME TO LOAD CSV FILES', sinceBegin=True)
    buildIndexesAndFK()
    restoreAll_imdbIDs()
    executeCustomQueries('END')
    t('FINAL', sinceBegin=True)


# begin the iterations...
def run():
    print 'RUNNING imdbpy2sql.py using the %s ORM' % USED_ORM

    executeCustomQueries('BEGIN')

    # Storing imdbIDs for movies and persons.
    runSafely(storeNotNULLimdbIDs, 'failed to read imdbIDs for movies',
            None, Title)
    runSafely(storeNotNULLimdbIDs, 'failed to read imdbIDs for people',
            None, Name)
    runSafely(storeNotNULLimdbIDs, 'failed to read imdbIDs for characters',
            None, CharName)
    runSafely(storeNotNULLimdbIDs, 'failed to read imdbIDs for companies',
            None, CompanyName)

    # Truncate the current database.
    print 'DROPPING current database...',
    sys.stdout.flush()
    dropTables(DB_TABLES)
    print 'DONE!'

    executeCustomQueries('BEFORE_CREATE')
    # Rebuild the database structure.
    print 'CREATING new tables...',
    sys.stdout.flush()
    createTables(DB_TABLES)
    print 'DONE!'
    t('dropping and recreating the database')
    executeCustomQueries('AFTER_CREATE')

    # Read the constants.
    readConstants()

    # Populate the CACHE_MID instance.
    readMovieList()
    # Comment readMovieList() and uncomment the following two lines
    # to keep the current info in the name and title tables.
    ##CACHE_MID.populate()
    t('readMovieList()')

    executeCustomQueries('BEFORE_COMPANIES')

    # distributors, miscellaneous-companies, production-companies,
    # special-effects-companies.
    ##CACHE_COMPID.populate()
    doMovieCompaniesInfo()
    # Do this now, and free some memory.
    CACHE_COMPID.flush()
    CACHE_COMPID.clear()

    executeCustomQueries('BEFORE_CAST')

    # actors, actresses, producers, writers, cinematographers, composers,
    # costume-designers, directors, editors, miscellaneous,
    # production-designers.
    castLists()
    ##CACHE_PID.populate()
    ##CACHE_CID.populate()

    # Aka names and titles.
    doAkaNames()
    t('doAkaNames()')
    doAkaTitles()
    t('doAkaTitles()')

    # alternate-versions, goofs, crazy-credits, quotes, soundtracks, trivia.
    doMinusHashFiles()
    t('doMinusHashFiles()')

    # biographies, business, laserdisc, literature, mpaa-ratings-reasons, plot.
    doNMMVFiles()

    # certificates, color-info, countries, genres, keywords, language,
    # locations, running-times, sound-mix, technical, release-dates.
    doMiscMovieInfo()
    # movie-links.
    doMovieLinks()
    t('doMovieLinks()')

    # ratings.
    getRating()
    t('getRating()')
    # taglines.
    getTaglines()
    t('getTaglines()')
    # ratings (top 250 and bottom 10 movies).
    getTopBottomRating()
    t('getTopBottomRating()')
    # complete-cast, complete-crew.
    completeCast()
    t('completeCast()')

    if CSV_DIR:
        CSV_CURS.closeAll()

    # Flush caches.
    CACHE_MID.flush()
    CACHE_PID.flush()
    CACHE_CID.flush()
    CACHE_MID.clear()
    CACHE_PID.clear()
    CACHE_CID.clear()
    t('fushing caches...')

    if CSV_ONLY_WRITE:
        t('TOTAL TIME TO WRITE CSV FILES', sinceBegin=True)
        executeCustomQueries('END')
        t('FINAL', sinceBegin=True)
        return

    if CSV_DIR:
        print 'loading CSV files into the database'
        executeCustomQueries('BEFORE_CSV_LOAD')
        loadCSVFiles()
        t('loadCSVFiles()')
        executeCustomQueries('BEFORE_RESTORE')

    t('TOTAL TIME TO INSERT/WRITE DATA', sinceBegin=True)

    buildIndexesAndFK()

    restoreAll_imdbIDs()

    executeCustomQueries('END')

    t('FINAL', sinceBegin=True)


_HEARD = 0
def _kdb_handler(signum, frame):
    """Die gracefully."""
    global _HEARD
    if _HEARD:
        print "EHI!  DON'T PUSH ME!  I'VE HEARD YOU THE FIRST TIME! :-)"
        return
    print 'INTERRUPT REQUEST RECEIVED FROM USER.  FLUSHING CACHES...'
    _HEARD = 1
    # XXX: trap _every_ error?
    try: CACHE_MID.flush()
    except IntegrityError: pass
    try: CACHE_PID.flush()
    except IntegrityError: pass
    try: CACHE_CID.flush()
    except IntegrityError: pass
    try: CACHE_COMPID.flush()
    except IntegrityError: pass
    print 'DONE! (in %d minutes, %d seconds)' % \
            divmod(int(time.time())-BEGIN_TIME, 60)
    sys.exit()


if __name__ == '__main__':
    try:
        print 'IMPORTING psyco...',
        sys.stdout.flush()
        #import DONOTIMPORTPSYCO
        import psyco
        #psyco.log()
        psyco.profile()
        print 'DONE!'
        print ''
    except ImportError:
        print 'FAILED (not a big deal, everything is alright...)'
        print ''
    import signal
    signal.signal(signal.SIGINT, _kdb_handler)
    if CSV_ONLY_LOAD:
        restoreCSV()
    else:
        run()


########NEW FILE########
__FILENAME__ = search_character
#!/usr/bin/env python
"""
search_character.py

Usage: search_character "character name"

Search for the given name and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "character name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of character objects).
    results = i.search_character(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    name.encode(out_encoding, 'replace'))
print 'characterID\t: imdbID : name'

# Print the long imdb name for every character.
for character in results:
    outp = u'%s\t\t: %s : %s' % (character.characterID, i.get_imdbID(character),
                                character['long imdb name'])
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = search_company
#!/usr/bin/env python
"""
search_company.py

Usage: search_company "company name"

Search for the given name and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "company name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of company objects).
    results = i.search_company(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    name.encode(out_encoding, 'replace'))
print 'companyID\t: imdbID : name'

# Print the long imdb name for every company.
for company in results:
    outp = u'%s\t\t: %s : %s' % (company.companyID, i.get_imdbID(company),
                                company['long imdb name'])
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = search_keyword
#!/usr/bin/env python
"""
search_keyword.py

Usage: search_keyword "keyword"

Search for keywords similar to the give one and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "keyword name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of keyword strings).
    results = i.search_keyword(name, results=20)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    name.encode(out_encoding, 'replace'))
print ' : keyword'

# Print every keyword.
for idx, keyword in enumerate(results):
    outp = u'%d: %s' % (idx+1, keyword)
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = search_movie
#!/usr/bin/env python
"""
search_movie.py

Usage: search_movie "movie title"

Search for the given title and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "movie title"' % sys.argv[0]
    sys.exit(2)

title = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

title = unicode(title, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of Movie objects).
    results = i.search_movie(title)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    title.encode(out_encoding, 'replace'))
print 'movieID\t: imdbID : title'

# Print the long imdb title for every movie.
for movie in results:
    outp = u'%s\t: %s : %s' % (movie.movieID, i.get_imdbID(movie),
                                movie['long imdb title'])
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = search_person
#!/usr/bin/env python
"""
search_person.py

Usage: search_person "person name"

Search for the given name and print the results.
"""

import sys

# Import the IMDbPY package.
try:
    import imdb
except ImportError:
    print 'You bad boy!  You need to install the IMDbPY package!'
    sys.exit(1)


if len(sys.argv) != 2:
    print 'Only one argument is required:'
    print '  %s "person name"' % sys.argv[0]
    sys.exit(2)

name = sys.argv[1]


i = imdb.IMDb()

in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

name = unicode(name, in_encoding, 'replace')
try:
    # Do the search, and get the results (a list of Person objects).
    results = i.search_person(name)
except imdb.IMDbError, e:
    print "Probably you're not connected to Internet.  Complete error report:"
    print e
    sys.exit(3)

# Print the results.
print '    %s result%s for "%s":' % (len(results),
                                    ('', 's')[len(results) != 1],
                                    name.encode(out_encoding, 'replace'))
print 'personID\t: imdbID : name'

# Print the long imdb name for every person.
for person in results:
    outp = u'%s\t: %s : %s' % (person.personID, i.get_imdbID(person),
                                person['long imdb name'])
    print outp.encode(out_encoding, 'replace')



########NEW FILE########
__FILENAME__ = download_applydiffs
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# This script downloads and applies any and all imdb diff files which
# have not already been applied to the lists in the ImdbListsPath folder
#
# NOTE: this is especially useful in Windows environment; you have
# to modify the paths in the 'Script configuration' section below,
# accordingly with your needs.
#
# The script will check the imdb list files (compressed or incompressed)
# in ImdbListsPath and assume that the imdb lists were most recently downloaded
# or updated based on the most recently modified list file in that folder.
#
# In order to run correctly, the configuration section below needs to be
# set to the location of the imdb list files and the commands required to
# unGzip, UnTar, patch and Gzip files.
#
# Optional configuration settings are to set the imdb diff files download and/or
# backup folders. If you do not want to keep or backup the downloaded imdb diff
# files then set keepDiffFiles to False and diffFilesBackupFolder to None.
#
# If RunAfterSuccessfulUpdate is set to a value other than None then the program
# specified will be run after the imdb list files have been successfully updated.
# This enables, for example, the script to automatically run imdbPy to rebuild
# the database once the imdb list files have been updated.
#
# If a specific downloaded imdb diff file cannot be applied correctly then this script
# will fail as gracefully as possible.
#
# Copyright 2013 (C) Roy Stead
# Released under the terms of the GPL license.
#

import os
import sys
import shutil
import subprocess
import re
import datetime
import time
import MySQLdb
import logging

from datetime import timedelta,datetime
from ftplib import FTP
from random import choice

#############################################
#           Script configuration            #
#############################################

# The local folders where imdb list and diffs files are stored
#
# If ImdbDiffsPath is set to None then a working folder, "diffs" will be created as a sub-folder of ImdbListsPath
# and will be cleaned up afterwards if you also set keepDiffFiles to False
ImdbListsPath = "Z:\\MovieDB\\data\\lists"
ImdbDiffsPath = None

# The path to the logfile, if desired
logfile = 'Z:\\MovieDB\\data\\logs\\update.log'

# Define the system commands to unZip, unTar, Patch and Gzip a file
# Values are substituted into these template strings at runtime, in the order indicated
#
# Note that this script REQUIRES that the program used to apply patches MUST return 0 on success and non-zero on failure
#
unGzip="\"C:/Program Files/7-Zip/7z.exe\" e %s -o%s"                                # params = archive, destination folder
unTar=unGzip                                                                        # params = archive, destination folder
applyPatch="\"Z:/MovieDB/Scripts/patch.exe\" --binary --force --silent %s %s"       # params = listfile, diffsfile
progGZip="\"Z:/MovieDB/Scripts/gzip.exe\" %s"                                       # param = file to Gzip

# Specify a program to be run after a successful update of the imdb lists,
# such as a command line to execute imdbPy to rebuild the db from the updated imdb list files
#
# Set to None if no such program should be run
RunAfterSuccessfulUpdate="\"Z:\\MovieDB\\Scripts\\Update db from imdb lists.bat\""

# Folder to copy downloaded imdb diff files to once they have been successfully applied
# Note that ONLY diff files which are successfully applied will be backed up.
#
# Set to None if no such folder
diffFilesBackupFolder=None

# Set keepDiffFiles to false if the script is to delete ImdbDiffsPath and all its files when it's finished
#
# If set to False and diffFilesBackupFolder is not None then diff files will be backed up before being deleted
# (and will not be deleted if there's any problem with backing up the diff files)
keepDiffFiles=True

# Possible FTP servers for downloading imdb diff files and the path to the diff files on each server
ImdbDiffsFtpServers = [ \
    {'url': "ftp.fu-berlin.de", 'path': "/pub/misc/movies/database/diffs"}, \
#    {'url': "ftp.sunet.se", 'path': "/pub/tv+movies/imdb/diffs"}, \                # Swedish server isn't kept up to date
    {'url': "ftp.funet.fi", 'path': "/pub/mirrors/ftp.imdb.com/pub/diffs"} ]        # Finish server tends to be updated first


#############################################
#                Script Code                #
#############################################

logger = None

# Returns the date of the most recent Friday
# The returned datetime object contains ONLY date information, all time data is set to zero
def previousFriday(day):

    friday =  datetime(day.year, day.month, day.day) - timedelta(days=day.weekday()) + timedelta(days=4)

    # Saturday and Sunday are a special case since Python's day of the week numbering starts at Monday = 0
    # Note that if day falls on a Friday then the "previous friday" for that date is the same date
    if day.weekday() <= 4:
        friday -= timedelta(weeks=1)

    return friday

# Delete all files and subfolders in the specified folder as well as the folder itself
def deleteFolder(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    if os.path.isdir(folder):
        os.rmdir(folder)

# Create folder and as many parent folders are needed to create the full path
# Returns 0 on success or -1 on failure
def mktree(path):
    import os.path as os_path
    paths_to_create = []
    while not os_path.lexists(path):
        paths_to_create.insert(0, path)
        head,tail = os_path.split(path)
        if len(tail.strip())==0: # Just incase path ends with a / or \
            path = head
            head,tail = os_path.split(path)
        path = head

    for path in paths_to_create:
        try:
            os.mkdir(path)
        except Exception, e:
            logger.exception("Error trying to create %p" % path)
            return -1
    return 0

# Downloads and applies all imdb diff files which have not yet been applied to the current imdb lists
def applyDiffs():

    global keepDiffFiles, ImdbListsPath, ImdbDiffsPath, diffFilesBackupFolder
    global unGzip, unTar, applyPatch, progGZip, RunAfterSuccessfulUpdate, ImdbDiffsFtpServers

    if not os.path.exists(ImdbListsPath):
        logger.critical("Please edit this script file and set ImdbListsPath to the current location of your imdb list files")
        return

    # If no ImdbDiffsPath is specified, create a working folder for the diffs file as a sub-folder of the imdb lists repository
    if ImdbDiffsPath is None:
        ImdbDiffsPath = os.path.join(ImdbListsPath,"diffs")

    # Get the date of the most recent Friday (i.e. the most recently released imdb diffs)
    # Note Saturday and Sunday are a special case since Python's day of the week numbering starts at Monday = 0
    day = datetime.now()
    mostrecentfriday =  previousFriday(day)

    # Now get the date when the imdb list files in ImdbListsPath were most recently updated.
    #
    # At the end of this loop, day will contain the most recent date that a list file was
    # modified (Note: modified, not created, since Windows changes the creation date on file copies)
    #
    # This approach assumes that since the imdb list files were last downloaded or updated nobody has
    # unzipped a compressed list file and then re-zipped it again without updating all of the imdb
    # list files at that time (and also that nobody has manualy changed the file last modified dates).
    # Which seem like reasonable assumptions.
    #
    # An even more robust approach would be to look inside each zipfile and read the date/time stamp
    # from the first line of the imdb list file itself but that seems like overkill to me.
    day = None;
    for f in os.listdir(ImdbListsPath):
        if re.match(".*\.list\.gz",f) or re.match(".*\.list",f):
            try:
                t = os.path.getmtime(os.path.join(ImdbListsPath,f))
                d = datetime.fromtimestamp(t)

                if day == None:
                    day = d
                elif d > day:
                    day = d
            except Exception, e:
                logger.exception("Unable to read last modified date for file %s" % f)

    if day is None:

        # No diff files found and unable to read imdb list files
        logger.critical("Problem: Unable to check imdb lists in folder %s" % ImdbListsPath)
        logger.critical("Solutions: Download imdb lists, change ImdbListsPath value in this script or change access settings for that folder.")
        return

    # Last update date for imdb list files is the Friday before they were downloaded
    imdbListsDate =  previousFriday(day)

    logger.debug("imdb lists updated up to %s" % imdbListsDate)

    if imdbListsDate >= mostrecentfriday:
        logger.info("imdb database is already up to date")
        return

    # Create diffs file folder if it does not already exist
    if not os.path.isdir(ImdbDiffsPath):
        try:
            os.mkdir(ImdbDiffsPath)
        except Exception, e:
            logger.exception("Unable to create folder for imdb diff files (%s)" % ImdbDiffsPath)
            return

    # Next we check for the imdb diff files and download any which we need to apply but which are not already downloaded
    diffFileDate = imdbListsDate
    haveFTPConnection = False
    while 1:

        if diffFileDate >= mostrecentfriday:
            break;

        diff = "diffs-%s.tar.gz" % diffFileDate.strftime("%y%m%d")
        diffFilePath = os.path.join(ImdbDiffsPath, diff)

        logger.debug("Need diff file %s" % diff)

        if not os.path.isfile(diffFilePath):
            
            # diff file is missing so we need to download it so first make sure we have an FTP connection
            if not haveFTPConnection:
                try:
                    # Choose a random ftp server from which to download the imdb diff file(s)
                    ImdbDiffsFtpServer = choice(ImdbDiffsFtpServers)
                    ImdbDiffsFtp = ImdbDiffsFtpServer['url']
                    ImdbDiffsFtpPath = ImdbDiffsFtpServer['path']

                    # Connect to chosen imdb FTP server
                    ftp = FTP(ImdbDiffsFtp)
                    ftp.login()

                    # Change to the diffs folder on the imdb files server
                    ftp.cwd(ImdbDiffsFtpPath)

                    haveFTPConnection = True
                except Exception, e:
                    logger.exception("Unable to connect to FTP server %s" % ImdbDiffsFtp)
                    return

            # Now download the diffs file
            logger.info("Downloading ftp://%s%s/%s" % ( ImdbDiffsFtp, ImdbDiffsFtpPath, diff ))
            diffFile = open(diffFilePath, 'wb');
            try:
                ftp.retrbinary("RETR " + diff, diffFile.write)
                diffFile.close()
            except Exception, e:

                # Unable to download diff file. This may be because it's not yet available but is due for release today
                code, message = e.message.split(' ', 1)
                if code == '550' and diffFileDate == imdbListsDate:
                    logger.info("Diff file %s not yet available on the imdb diffs server: try again later" % diff)
                else:
                    logger.exception("Unable to download %s" % diff)

                # Delete the diffs file placeholder since the file did not download
                diffFile.close()
                os.remove(diffFilePath)
                if os.path.isdir(ImdbDiffsPath) and not keepDiffFiles:
                    os.rmdir(ImdbDiffsPath)

                return

            logger.info("Successfully downloaded %s" % diffFilePath)

        # Check for the following week's diff file
        diffFileDate += timedelta(weeks=1)

    # Close FTP connection if we used one
    if haveFTPConnection:
        ftp.close()


    # At this point, we know we need to apply one or more diff files and we
    # also know that we have all of the diff files which need to be applied
    # so next step is to uncompress our existing list files to a folder so
    # we can apply diffs to them.
    #
    # Note that the script will ONLY apply diffs if ALL of the diff files
    # needed to bring the imdb lists up to date are available. It will, however,
    # partially-update the imdb list files if one of the later files could not
    # be applied for any reason but earlier ones were applied ok (see below).
    tmpListsPath = os.path.join(ImdbDiffsPath,"lists")
    deleteFolder(tmpListsPath)
    try:
        os.mkdir(tmpListsPath)
    except Exception, e:
        logger.exception("Unable to create temporary folder for imdb lists")
        return

    logger.info("Uncompressing imdb list files")

    # Uncompress list files in ImdbListsPath to our temporary folder tmpListsPath
    numListFiles = 0;
    for f in os.listdir(ImdbListsPath):
        if re.match(".*\.list\.gz",f):
            try:
                cmdUnGzip = unGzip % (os.path.join(ImdbListsPath,f), tmpListsPath)
                subprocess.call(cmdUnGzip , shell=True)
            except Exception, e:
                logger.exception("Unable to uncompress imdb list file using: %s" % cmdUnGzip)
            numListFiles += 1

    if numListFiles == 0:
        # Somebody has deleted or moved the list files since we checked their datetime stamps earlier(!)
        logger.critical("No imdb list files found in %s." % ImdbListsPath)
        return


    # Now we loop through the diff files and apply each one in turn to the uncompressed list files
    patchedOKWith = None
    while 1:

        if imdbListsDate >= mostrecentfriday:
            break;

        diff = "diffs-%s.tar.gz" % imdbListsDate.strftime("%y%m%d")
        diffFilePath = os.path.join(ImdbDiffsPath, diff)

        logger.info("Applying imdb diff file %s" % diff)

        # First uncompress the diffs file to a subdirectory.
        #
        # If that subdirectory already exists, delete any files from it
        # in case they are stale and replace them with files from the
        # newly-downloaded imdb diff file
        tmpDiffsPath = os.path.join(ImdbDiffsPath,"diffs")
        deleteFolder(tmpDiffsPath)
        os.mkdir(tmpDiffsPath)

        # unZip the diffs file to create a file diffs.tar
        try:
            cmdUnGzip = unGzip % (diffFilePath, tmpDiffsPath)
            subprocess.call(cmdUnGzip, shell=True)
        except Exception, e:
            logger.exception("Unable to unzip imdb diffs file using: %s" % cmdUnGzip)
            return

        # unTar the file diffs.tar
        tarFile = os.path.join(tmpDiffsPath,"diffs.tar")
        patchStatus = 0
        if os.path.isfile(tarFile):
            try:
                cmdUnTar = unTar % (tarFile, tmpDiffsPath)
                subprocess.call(cmdUnTar, shell=True)
            except Exception, e:
                logger.exception("Unable to untar imdb diffs file using: %s" % cmdUnTar)
                return

            # Clean up tar file and the sub-folder which 7z may have (weirdly) created while unTarring it
            os.remove(tarFile);
            if os.path.exists(os.path.join(tmpDiffsPath,"diffs")):
                os.rmdir(os.path.join(tmpDiffsPath,"diffs"));

            # Apply all the patch files to the list files in tmpListsPath
            isFirstPatchFile = True
            for f in os.listdir(tmpDiffsPath):
                if re.match(".*\.list",f):
                    logger.info("Patching imdb list file %s" % f)
                    try:
                        cmdApplyPatch = applyPatch % (os.path.join(tmpListsPath,f), os.path.join(tmpDiffsPath,f))
                        patchStatus = subprocess.call(cmdApplyPatch, shell=True)
                    except Exception, e:
                        logger.exception("Unable to patch imdb list file using: %s" % cmdApplyPatch)
                        patchStatus=-1

                    if patchStatus <> 0:

                        # Patch failed so...
                        logger.critical("Patch status %s: Wrong diff file for these imdb lists (%s)" % (patchStatus, diff))

                        # Delete the erroneous imdb diff file
                        os.remove(diffFilePath)

                        # Clean up temporary diff files
                        deleteFolder(tmpDiffsPath)

                        if patchedOKWith <> None and isFirstPatchFile:

                            # The previous imdb diffs file succeeded and the current diffs file failed with the
                            # first attempted patch, so we can keep our updated list files up to this point
                            logger.warning("Patched OK up to and including imdb diff file %s ONLY" % patchedOKWith)
                            break

                        else:
                            # We've not managed to successfully apply any imdb diff files and this was not the
                            # first patch attempt from a diff file from this imdb diffs file so we cannot rely
                            # on the updated imdb lists being accurate, in which case delete them and abandon
                            logger.critical("Abandoning update: original imdb lists are unchanged")
                            deleteFolder(tmpListsPath)
                            return

                    # Reset isFirstPatchFile flag since we have successfully
                    # applied at least one patch file from this imdb diffs file
                    isFirstPatchFile = False

        # Clean up the imdb diff files and their temporary folder
        deleteFolder(tmpDiffsPath)

        # Note the imdb patch file which was successfully applied, if any
        if patchStatus == 0:
            patchedOKWith = diff

            # Backup successfully-applied diff file if required
            if diffFilesBackupFolder is not None:

                # Create diff files backup folder if it does not already exist
                if not os.path.isdir(diffFilesBackupFolder):
                    if mktree(diffFilesBackupFolder) == -1:
                        if not keepDiffFiles:
                            keepDiffFiles = True
                            logger.warning("diff files will NOT be deleted but may be backed up manually")

                # Backup this imdb diff file to the backup folder if that folder exists and this diff file doesn't already exist there
                if os.path.isdir(diffFilesBackupFolder):
                    if not os.path.isfile(os.path.join(diffFilesBackupFolder,diff)):
                        try:
                            shutil.copy(diffFilePath,diffFilesBackupFolder)
                        except Exception, e:
                            logger.exception("Unable to copy %s to backup folder %s" % (diffFilePath, diffFilesBackupFolder))
                            if not keepDiffFiles:
                                keepDiffFiles = True
                                logger.warning("diff files will NOT be deleted but may be backed up manually")

            # Clean up imdb diff file if required
            if not keepDiffFiles:
                if os.path.isfile(diffFilePath):
                    os.remove(diffFilePath)

        # Next we apply the following week's imdb diff files
        imdbListsDate += timedelta(weeks=1)

    # List files are all updated so re-Gzip them up and delete the old list files
    for f in os.listdir(tmpListsPath):
        if re.match(".*\.list",f):
            try:
                cmdGZip = progGZip % os.path.join(tmpListsPath,f)
                subprocess.call(cmdGZip, shell=True)
            except Exception, e:
                logger.exception("Unable to Gzip imdb list file using: %s" % cmdGZip)
                break
            if os.path.isfile(os.path.join(tmpListsPath,f)):
                os.remove(os.path.join(tmpListsPath,f))

    # Now move the updated and compressed lists to the main lists folder, replacing the old list files
    for f in os.listdir(tmpListsPath):
        if re.match(".*\.list.gz",f):
            # Delete the original compressed list file from ImdbListsPath if it exists 
            if os.path.isfile(os.path.join(ImdbListsPath,f)):
                os.remove(os.path.join(ImdbListsPath,f))

            # Move the updated compressed list file to ImdbListsPath
            os.rename(os.path.join(tmpListsPath,f),os.path.join(ImdbListsPath,f))

    # Clean up the now-empty tmpListsPath temporary folder and anything left inside it
    deleteFolder(tmpListsPath)

    # Clean up imdb diff files if required
    # Note that this rmdir call will delete the folder only if it is empty. So if that folder was created, used and all
    # diff files deleted (possibly after being backed up) above then it should now be empty and will be removed.
    #
    # However, if the folder previously existed and contained some old diff files then those diff files will not be deleted.
    # To delete the folder and ALL of its contents regardless, replace os.rmdir() with a deleteFolder() call
    if not keepDiffFiles:
        os.rmdir(ImdbDiffsPath)
#        deleteFolder(ImdbDiffsPath)

    # If the imdb lists were successfully updated, even partially, then run my
    # DOS batch file "Update db from imdb lists.bat" to rebuild the imdbPy database
    # and relink and reintegrate my shadow tables data into it
    if patchedOKWith <> None:
        logger.info("imdb lists are updated up to imdb diffs file %s" % patchedOKWith)
        if RunAfterSuccessfulUpdate <> None:
            logger.info("Now running %s" % RunAfterSuccessfulUpdate)
            subprocess.call(RunAfterSuccessfulUpdate, shell=True)


# Set up logging
def initLogging(loggerName, logfilename):

    global logger

    logger = logging.getLogger(loggerName)
    logger.setLevel(logging.DEBUG)

    # Logger for file, if logfilename supplied
    if logfilename is not None:
        fh = logging.FileHandler(logfilename)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(name)s %(levelname)s %(asctime)s %(message)s\t\t\t[%(module)s line %(lineno)d: %(funcName)s%(args)s]', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)

    # Logger for stdout
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)

initLogging('__applydiffs__', logfile)

applyDiffs()

########NEW FILE########
__FILENAME__ = Character
"""
Character module (imdb package).

This module provides the Character class, used to store information about
a given character.

Copyright 2007-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from copy import deepcopy

from imdb.utils import analyze_name, build_name, flatten, _Container, cmpPeople


class Character(_Container):
    """A Character.

    Every information about a character can be accessed as:
        characterObject['information']
    to get a list of the kind of information stored in a
    Character object, use the keys() method; some useful aliases
    are defined (as "also known as" for the "akas" key);
    see the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main', 'filmography', 'biography')

    # Aliases for some not-so-intuitive keys.
    keys_alias = {'mini biography': 'biography',
                  'bio': 'biography',
                  'character biography': 'biography',
                  'character biographies': 'biography',
                  'biographies': 'biography',
                  'character bio': 'biography',
                  'aka': 'akas',
                  'also known as': 'akas',
                  'alternate names': 'akas',
                  'personal quotes': 'quotes',
                  'keys': 'keywords',
                  'keyword': 'keywords'}

    keys_tomodify_list = ('biography', 'quotes')

    cmpFunct = cmpPeople

    def _init(self, **kwds):
        """Initialize a Character object.

        *characterID* -- the unique identifier for the character.
        *name* -- the name of the Character, if not in the data dictionary.
        *myName* -- the nickname you use for this character.
        *myID* -- your personal id for this character.
        *data* -- a dictionary used to initialize the object.
        *notes* -- notes about the given character.
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to characters.
        *modFunct* -- function called returning text fields.
        """
        name = kwds.get('name')
        if name and not self.data.has_key('name'):
            self.set_name(name)
        self.characterID = kwds.get('characterID', None)
        self.myName = kwds.get('myName', u'')

    def _reset(self):
        """Reset the Character object."""
        self.characterID = None
        self.myName = u''

    def set_name(self, name):
        """Set the name of the character."""
        # XXX: convert name to unicode, if it's a plain string?
        try:
            d = analyze_name(name, canonical=0)
            self.data.update(d)
        except:
            # TODO: catch only IMDbPYParserError and issue a warning.
            pass

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        addkeys = []
        if self.data.has_key('name'):
            addkeys += ['long imdb name']
        if self.data.has_key('headshot'):
            addkeys += ['full-size headshot']
        return addkeys

    def _getitem(self, key):
        """Handle special keys."""
        ## XXX: can a character have an imdbIndex?
        if self.data.has_key('name'):
            if key == 'long imdb name':
                return build_name(self.data)
        if key == 'full-size headshot' and self.data.has_key('headshot'):
            return self._re_fullsizeURL.sub('', self.data.get('headshot', ''))
        return None

    def getID(self):
        """Return the characterID."""
        return self.characterID

    def __nonzero__(self):
        """The Character is "false" if the self.data does not contain a name."""
        # XXX: check the name and the characterID?
        if self.data.get('name'): return 1
        return 0

    def __contains__(self, item):
        """Return true if this Character was portrayed in the given Movie
        or it was impersonated by the given Person."""
        from Movie import Movie
        from Person import Person
        if isinstance(item, Person):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m.currentRole):
                    return 1
        elif isinstance(item, Movie):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m):
                    return 1
        return 0

    def isSameName(self, other):
        """Return true if two character have the same name
        and/or characterID."""
        if not isinstance(other, self.__class__):
            return 0
        if self.data.has_key('name') and \
                other.data.has_key('name') and \
                build_name(self.data, canonical=0) == \
                build_name(other.data, canonical=0):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.characterID is not None and \
                self.characterID == other.characterID:
            return 1
        return 0
    isSameCharacter = isSameName

    def __deepcopy__(self, memo):
        """Return a deep copy of a Character instance."""
        c = Character(name=u'', characterID=self.characterID,
                    myName=self.myName, myID=self.myID,
                    data=deepcopy(self.data, memo),
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        c.current_info = list(self.current_info)
        c.set_mod_funct(self.modFunct)
        return c

    def __repr__(self):
        """String representation of a Character object."""
        r = '<Character id:%s[%s] name:_%s_>' % (self.characterID,
                                        self.accessSystem,
                                        self.get('name'))
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short name."""
        return self.get('name', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('name', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the character."""
        if not self: return u''
        s = u'Character\n=====\nName: %s\n' % \
                                self.get('name', u'')
        bio = self.get('biography')
        if bio:
            s += u'Biography: %s\n' % bio[0]
        filmo = self.get('filmography')
        if filmo:
            a_list = [x.get('long imdb canonical title', u'')
                        for x in filmo[:5]]
            s += u'Last movies with this character: %s.\n' % u'; '.join(a_list)
        return s



########NEW FILE########
__FILENAME__ = Company
"""
company module (imdb package).

This module provides the company class, used to store information about
a given company.

Copyright 2008-2009 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from copy import deepcopy

from imdb.utils import analyze_company_name, build_company_name, \
                        flatten, _Container, cmpCompanies


class Company(_Container):
    """A company.

    Every information about a company can be accessed as:
        companyObject['information']
    to get a list of the kind of information stored in a
    company object, use the keys() method; some useful aliases
    are defined (as "also known as" for the "akas" key);
    see the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main',)

    # Aliases for some not-so-intuitive keys.
    keys_alias = {
            'distributor': 'distributors',
            'special effects company': 'special effects companies',
            'other company': 'miscellaneous companies',
            'miscellaneous company': 'miscellaneous companies',
            'other companies': 'miscellaneous companies',
            'misc companies': 'miscellaneous companies',
            'misc company': 'miscellaneous companies',
            'production company': 'production companies'}

    keys_tomodify_list = ()

    cmpFunct = cmpCompanies

    def _init(self, **kwds):
        """Initialize a company object.

        *companyID* -- the unique identifier for the company.
        *name* -- the name of the company, if not in the data dictionary.
        *myName* -- the nickname you use for this company.
        *myID* -- your personal id for this company.
        *data* -- a dictionary used to initialize the object.
        *notes* -- notes about the given company.
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to companies.
        *modFunct* -- function called returning text fields.
        """
        name = kwds.get('name')
        if name and not self.data.has_key('name'):
            self.set_name(name)
        self.companyID = kwds.get('companyID', None)
        self.myName = kwds.get('myName', u'')

    def _reset(self):
        """Reset the company object."""
        self.companyID = None
        self.myName = u''

    def set_name(self, name):
        """Set the name of the company."""
        # XXX: convert name to unicode, if it's a plain string?
        # Company diverges a bit from other classes, being able
        # to directly handle its "notes".  AND THAT'S PROBABLY A BAD IDEA!
        oname = name = name.strip()
        notes = u''
        if name.endswith(')'):
            fparidx = name.find('(')
            if fparidx != -1:
                notes = name[fparidx:]
                name = name[:fparidx].rstrip()
        if self.notes:
            name = oname
        d = analyze_company_name(name)
        self.data.update(d)
        if notes and not self.notes:
            self.notes = notes

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        if self.data.has_key('name'):
            return ['long imdb name']
        return []

    def _getitem(self, key):
        """Handle special keys."""
        ## XXX: can a company have an imdbIndex?
        if self.data.has_key('name'):
            if key == 'long imdb name':
                return build_company_name(self.data)
        return None

    def getID(self):
        """Return the companyID."""
        return self.companyID

    def __nonzero__(self):
        """The company is "false" if the self.data does not contain a name."""
        # XXX: check the name and the companyID?
        if self.data.get('name'): return 1
        return 0

    def __contains__(self, item):
        """Return true if this company and the given Movie are related."""
        from Movie import Movie
        if isinstance(item, Movie):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m):
                    return 1
        return 0

    def isSameName(self, other):
        """Return true if two company have the same name
        and/or companyID."""
        if not isinstance(other, self.__class__):
            return 0
        if self.data.has_key('name') and \
                other.data.has_key('name') and \
                build_company_name(self.data) == \
                build_company_name(other.data):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.companyID is not None and \
                self.companyID == other.companyID:
            return 1
        return 0
    isSameCompany = isSameName

    def __deepcopy__(self, memo):
        """Return a deep copy of a company instance."""
        c = Company(name=u'', companyID=self.companyID,
                    myName=self.myName, myID=self.myID,
                    data=deepcopy(self.data, memo),
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        c.current_info = list(self.current_info)
        c.set_mod_funct(self.modFunct)
        return c

    def __repr__(self):
        """String representation of a Company object."""
        r = '<Company id:%s[%s] name:_%s_>' % (self.companyID,
                                        self.accessSystem,
                                        self.get('long imdb name'))
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short name."""
        return self.get('name', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('name', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the company."""
        if not self: return u''
        s = u'Company\n=======\nName: %s\n' % \
                                self.get('name', u'')
        for k in ('distributor', 'production company', 'miscellaneous company',
                'special effects company'):
            d = self.get(k, [])[:5]
            if not d: continue
            s += u'Last movies from this company (%s): %s.\n' % \
                    (k, u'; '.join([x.get('long imdb title', u'') for x in d]))
        return s



########NEW FILE########
__FILENAME__ = helpers
"""
helpers module (imdb package).

This module provides functions not used directly by the imdb package,
but useful for IMDbPY-based programs.

Copyright 2006-2012 Davide Alberani <da@erlug.linux.it>
               2012 Alberto Malagoli <albemala AT gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

# XXX: find better names for the functions in this modules.

import re
import difflib
from cgi import escape
import gettext
from gettext import gettext as _
gettext.textdomain('imdbpy')

# The modClearRefs can be used to strip names and titles references from
# the strings in Movie and Person objects.
from imdb.utils import modClearRefs, re_titleRef, re_nameRef, \
                    re_characterRef, _tagAttr, _Container, TAGS_TO_MODIFY
from imdb import IMDb, imdbURL_movie_base, imdbURL_person_base, \
                    imdbURL_character_base

import imdb.locale
from imdb.linguistics import COUNTRY_LANG
from imdb.Movie import Movie
from imdb.Person import Person
from imdb.Character import Character
from imdb.Company import Company
from imdb.parser.http.utils import re_entcharrefssub, entcharrefs, \
                                    subXMLRefs, subSGMLRefs
from imdb.parser.http.bsouplxml.etree import BeautifulSoup


# An URL, more or less.
_re_href = re.compile(r'(http://.+?)(?=\s|$)', re.I)
_re_hrefsub = _re_href.sub


def makeCgiPrintEncoding(encoding):
    """Make a function to pretty-print strings for the web."""
    def cgiPrint(s):
        """Encode the given string using the %s encoding, and replace
        chars outside the given charset with XML char references.""" % encoding
        s = escape(s, quote=1)
        if isinstance(s, unicode):
            s = s.encode(encoding, 'xmlcharrefreplace')
        return s
    return cgiPrint

# cgiPrint uses the latin_1 encoding.
cgiPrint = makeCgiPrintEncoding('latin_1')

# Regular expression for %(varname)s substitutions.
re_subst = re.compile(r'%\((.+?)\)s')
# Regular expression for <if condition>....</if condition> clauses.
re_conditional = re.compile(r'<if\s+(.+?)\s*>(.+?)</if\s+\1\s*>')


def makeTextNotes(replaceTxtNotes):
    """Create a function useful to handle text[::optional_note] values.
    replaceTxtNotes is a format string, which can include the following
    values: %(text)s and %(notes)s.
    Portions of the text can be conditionally excluded, if one of the
    values is absent. E.g.: <if notes>[%(notes)s]</if notes> will be replaced
    with '[notes]' if notes exists, or by an empty string otherwise.
    The returned function is suitable be passed as applyToValues argument
    of the makeObject2Txt function."""
    def _replacer(s):
        outS = replaceTxtNotes
        if not isinstance(s, (unicode, str)):
            return s
        ssplit = s.split('::', 1)
        text = ssplit[0]
        # Used to keep track of text and note existence.
        keysDict = {}
        if text:
            keysDict['text'] = True
        outS = outS.replace('%(text)s', text)
        if len(ssplit) == 2:
            keysDict['notes'] = True
            outS = outS.replace('%(notes)s', ssplit[1])
        else:
            outS = outS.replace('%(notes)s', u'')
        def _excludeFalseConditionals(matchobj):
            # Return an empty string if the conditional is false/empty.
            if matchobj.group(1) in keysDict:
                return matchobj.group(2)
            return u''
        while re_conditional.search(outS):
            outS = re_conditional.sub(_excludeFalseConditionals, outS)
        return outS
    return _replacer


def makeObject2Txt(movieTxt=None, personTxt=None, characterTxt=None,
               companyTxt=None, joiner=' / ',
               applyToValues=lambda x: x, _recurse=True):
    """"Return a function useful to pretty-print Movie, Person,
    Character and Company instances.

    *movieTxt* -- how to format a Movie object.
    *personTxt* -- how to format a Person object.
    *characterTxt* -- how to format a Character object.
    *companyTxt* -- how to format a Company object.
    *joiner* -- string used to join a list of objects.
    *applyToValues* -- function to apply to values.
    *_recurse* -- if True (default) manage only the given object.
    """
    # Some useful defaults.
    if movieTxt is None:
        movieTxt = '%(long imdb title)s'
    if personTxt is None:
        personTxt = '%(long imdb name)s'
    if characterTxt is None:
        characterTxt = '%(long imdb name)s'
    if companyTxt is None:
        companyTxt = '%(long imdb name)s'
    def object2txt(obj, _limitRecursion=None):
        """Pretty-print objects."""
        # Prevent unlimited recursion.
        if _limitRecursion is None:
            _limitRecursion = 0
        elif _limitRecursion > 5:
            return u''
        _limitRecursion += 1
        if isinstance(obj, (list, tuple)):
            return joiner.join([object2txt(o, _limitRecursion=_limitRecursion)
                                for o in obj])
        elif isinstance(obj, dict):
            # XXX: not exactly nice, neither useful, I fear.
            return joiner.join([u'%s::%s' %
                            (object2txt(k, _limitRecursion=_limitRecursion),
                            object2txt(v, _limitRecursion=_limitRecursion))
                            for k, v in obj.items()])
        objData = {}
        if isinstance(obj, Movie):
            objData['movieID'] = obj.movieID
            outs = movieTxt
        elif isinstance(obj, Person):
            objData['personID'] = obj.personID
            outs = personTxt
        elif isinstance(obj, Character):
            objData['characterID'] = obj.characterID
            outs = characterTxt
        elif isinstance(obj, Company):
            objData['companyID'] = obj.companyID
            outs = companyTxt
        else:
            return obj
        def _excludeFalseConditionals(matchobj):
            # Return an empty string if the conditional is false/empty.
            condition = matchobj.group(1)
            proceed = obj.get(condition) or getattr(obj, condition, None)
            if proceed:
                return matchobj.group(2)
            else:
                return u''
            return matchobj.group(2)
        while re_conditional.search(outs):
            outs = re_conditional.sub(_excludeFalseConditionals, outs)
        for key in re_subst.findall(outs):
            value = obj.get(key) or getattr(obj, key, None)
            if not isinstance(value, (unicode, str)):
                if not _recurse:
                    if value:
                        value =  unicode(value)
                if value:
                    value = object2txt(value, _limitRecursion=_limitRecursion)
            elif value:
                value = applyToValues(unicode(value))
            if not value:
                value = u''
            elif not isinstance(value, (unicode, str)):
                value = unicode(value)
            outs = outs.replace(u'%(' + key + u')s', value)
        return outs
    return object2txt


def makeModCGILinks(movieTxt, personTxt, characterTxt=None,
                    encoding='latin_1'):
    """Make a function used to pretty-print movies and persons refereces;
    movieTxt and personTxt are the strings used for the substitutions.
    movieTxt must contains %(movieID)s and %(title)s, while personTxt
    must contains %(personID)s and %(name)s and characterTxt %(characterID)s
    and %(name)s; characterTxt is optional, for backward compatibility."""
    _cgiPrint = makeCgiPrintEncoding(encoding)
    def modCGILinks(s, titlesRefs, namesRefs, characterRefs=None):
        """Substitute movies and persons references."""
        if characterRefs is None: characterRefs = {}
        # XXX: look ma'... more nested scopes! <g>
        def _replaceMovie(match):
            to_replace = match.group(1)
            item = titlesRefs.get(to_replace)
            if item:
                movieID = item.movieID
                to_replace = movieTxt % {'movieID': movieID,
                                        'title': unicode(_cgiPrint(to_replace),
                                                        encoding,
                                                        'xmlcharrefreplace')}
            return to_replace
        def _replacePerson(match):
            to_replace = match.group(1)
            item = namesRefs.get(to_replace)
            if item:
                personID = item.personID
                to_replace = personTxt % {'personID': personID,
                                        'name': unicode(_cgiPrint(to_replace),
                                                        encoding,
                                                        'xmlcharrefreplace')}
            return to_replace
        def _replaceCharacter(match):
            to_replace = match.group(1)
            if characterTxt is None:
                return to_replace
            item = characterRefs.get(to_replace)
            if item:
                characterID = item.characterID
                if characterID is None:
                    return to_replace
                to_replace = characterTxt % {'characterID': characterID,
                                        'name': unicode(_cgiPrint(to_replace),
                                                        encoding,
                                                        'xmlcharrefreplace')}
            return to_replace
        s = s.replace('<', '&lt;').replace('>', '&gt;')
        s = _re_hrefsub(r'<a href="\1">\1</a>', s)
        s = re_titleRef.sub(_replaceMovie, s)
        s = re_nameRef.sub(_replacePerson, s)
        s = re_characterRef.sub(_replaceCharacter, s)
        return s
    modCGILinks.movieTxt = movieTxt
    modCGILinks.personTxt = personTxt
    modCGILinks.characterTxt = characterTxt
    return modCGILinks

# links to the imdb.com web site.
_movieTxt = '<a href="' + imdbURL_movie_base + 'tt%(movieID)s">%(title)s</a>'
_personTxt = '<a href="' + imdbURL_person_base + 'nm%(personID)s">%(name)s</a>'
_characterTxt = '<a href="' + imdbURL_character_base + \
                'ch%(characterID)s">%(name)s</a>'
modHtmlLinks = makeModCGILinks(movieTxt=_movieTxt, personTxt=_personTxt,
                                characterTxt=_characterTxt)
modHtmlLinksASCII = makeModCGILinks(movieTxt=_movieTxt, personTxt=_personTxt,
                                    characterTxt=_characterTxt,
                                    encoding='ascii')


everyentcharrefs = entcharrefs.copy()
for k, v in {'lt':u'<','gt':u'>','amp':u'&','quot':u'"','apos':u'\''}.items():
    everyentcharrefs[k] = v
    everyentcharrefs['#%s' % ord(v)] = v
everyentcharrefsget = everyentcharrefs.get
re_everyentcharrefs = re.compile('&(%s|\#160|\#\d{1,5});' %
                            '|'.join(map(re.escape, everyentcharrefs)))
re_everyentcharrefssub = re_everyentcharrefs.sub

def _replAllXMLRef(match):
    """Replace the matched XML reference."""
    ref = match.group(1)
    value = everyentcharrefsget(ref)
    if value is None:
        if ref[0] == '#':
            return unichr(int(ref[1:]))
        else:
            return ref
    return value

def subXMLHTMLSGMLRefs(s):
    """Return the given string with XML/HTML/SGML entity and char references
    replaced."""
    return re_everyentcharrefssub(_replAllXMLRef, s)


def sortedSeasons(m):
    """Return a sorted list of seasons of the given series."""
    seasons = m.get('episodes', {}).keys()
    seasons.sort()
    return seasons


def sortedEpisodes(m, season=None):
    """Return a sorted list of episodes of the given series,
    considering only the specified season(s) (every season, if None)."""
    episodes = []
    seasons = season
    if season is None:
        seasons = sortedSeasons(m)
    else:
        if not isinstance(season, (tuple, list)):
            seasons = [season]
    for s in seasons:
        eps_indx = m.get('episodes', {}).get(s, {}).keys()
        eps_indx.sort()
        for e in eps_indx:
            episodes.append(m['episodes'][s][e])
    return episodes


# Idea and portions of the code courtesy of none none (dclist at gmail.com)
_re_imdbIDurl = re.compile(r'\b(nm|tt|ch|co)([0-9]{7})\b')
def get_byURL(url, info=None, args=None, kwds=None):
    """Return a Movie, Person, Character or Company object for the given URL;
    info is the info set to retrieve, args and kwds are respectively a list
    and a dictionary or arguments to initialize the data access system.
    Returns None if unable to correctly parse the url; can raise
    exceptions if unable to retrieve the data."""
    if args is None: args = []
    if kwds is None: kwds = {}
    ia = IMDb(*args, **kwds)
    match = _re_imdbIDurl.search(url)
    if not match:
        return None
    imdbtype = match.group(1)
    imdbID = match.group(2)
    if imdbtype == 'tt':
        return ia.get_movie(imdbID, info=info)
    elif imdbtype == 'nm':
        return ia.get_person(imdbID, info=info)
    elif imdbtype == 'ch':
        return ia.get_character(imdbID, info=info)
    elif imdbtype == 'co':
        return ia.get_company(imdbID, info=info)
    return None


# Idea and portions of code courtesy of Basil Shubin.
# Beware that these information are now available directly by
# the Movie/Person/Character instances.
def fullSizeCoverURL(obj):
    """Given an URL string or a Movie, Person or Character instance,
    returns an URL to the full-size version of the cover/headshot,
    or None otherwise.  This function is obsolete: the same information
    are available as keys: 'full-size cover url' and 'full-size headshot',
    respectively for movies and persons/characters."""
    if isinstance(obj, Movie):
        coverUrl = obj.get('cover url')
    elif isinstance(obj, (Person, Character)):
        coverUrl = obj.get('headshot')
    else:
        coverUrl = obj
    if not coverUrl:
        return None
    return _Container._re_fullsizeURL.sub('', coverUrl)


def keyToXML(key):
    """Return a key (the ones used to access information in Movie and
    other classes instances) converted to the style of the XML output."""
    return _tagAttr(key, '')[0]


def translateKey(key):
    """Translate a given key."""
    return _(keyToXML(key))


# Maps tags to classes.
_MAP_TOP_OBJ = {
    'person': Person,
    'movie': Movie,
    'character': Character,
    'company': Company
}

# Tags to be converted to lists.
_TAGS_TO_LIST = dict([(x[0], None) for x in TAGS_TO_MODIFY.values()])
_TAGS_TO_LIST.update(_MAP_TOP_OBJ)

def tagToKey(tag):
    """Return the name of the tag, taking it from the 'key' attribute,
    if present."""
    keyAttr = tag.get('key')
    if keyAttr:
        if tag.get('keytype') == 'int':
            keyAttr = int(keyAttr)
        return keyAttr
    return tag.name


def _valueWithType(tag, tagValue):
    """Return tagValue, handling some type conversions."""
    tagType = tag.get('type')
    if tagType == 'int':
        tagValue = int(tagValue)
    elif tagType == 'float':
        tagValue = float(tagValue)
    return tagValue


# Extra tags to get (if values were not already read from title/name).
_titleTags = ('imdbindex', 'kind', 'year')
_nameTags = ('imdbindex')
_companyTags = ('imdbindex', 'country')

def parseTags(tag, _topLevel=True, _as=None, _infoset2keys=None,
            _key2infoset=None):
    """Recursively parse a tree of tags."""
    # The returned object (usually a _Container subclass, but it can
    # be a string, an int, a float, a list or a dictionary).
    item = None
    if _infoset2keys is None:
        _infoset2keys = {}
    if _key2infoset is None:
        _key2infoset = {}
    name = tagToKey(tag)
    firstChild = tag.find(recursive=False)
    tagStr = (tag.string or u'').strip()
    if not tagStr and name == 'item':
        # Handles 'item' tags containing text and a 'notes' sub-tag.
        tagContent = tag.contents[0]
        if isinstance(tagContent, BeautifulSoup.NavigableString):
            tagStr = (unicode(tagContent) or u'').strip()
    tagType = tag.get('type')
    infoset = tag.get('infoset')
    if infoset:
        _key2infoset[name] = infoset
        _infoset2keys.setdefault(infoset, []).append(name)
    # Here we use tag.name to avoid tags like <item title="company">
    if tag.name in _MAP_TOP_OBJ:
        # One of the subclasses of _Container.
        item = _MAP_TOP_OBJ[name]()
        itemAs = tag.get('access-system')
        if itemAs:
            if not _as:
                _as = itemAs
        else:
            itemAs = _as
        item.accessSystem = itemAs
        tagsToGet = []
        theID = tag.get('id')
        if name == 'movie':
            item.movieID = theID
            tagsToGet = _titleTags
            theTitle = tag.find('title', recursive=False)
            if tag.title:
                item.set_title(tag.title.string)
                tag.title.extract()
        else:
            if name == 'person':
                item.personID = theID
                tagsToGet = _nameTags
                theName = tag.find('long imdb canonical name', recursive=False)
                if not theName:
                    theName = tag.find('name', recursive=False)
            elif name == 'character':
                item.characterID = theID
                tagsToGet = _nameTags
                theName = tag.find('name', recursive=False)
            elif name == 'company':
                item.companyID = theID
                tagsToGet = _companyTags
                theName = tag.find('name', recursive=False)
            if theName:
                item.set_name(theName.string)
            if theName:
                theName.extract()
        for t in tagsToGet:
            if t in item.data:
                continue
            dataTag = tag.find(t, recursive=False)
            if dataTag:
                item.data[tagToKey(dataTag)] = _valueWithType(dataTag,
                                                            dataTag.string)
        if tag.notes:
            item.notes = tag.notes.string
            tag.notes.extract()
        episodeOf = tag.find('episode-of', recursive=False)
        if episodeOf:
            item.data['episode of'] = parseTags(episodeOf, _topLevel=False,
                                        _as=_as, _infoset2keys=_infoset2keys,
                                        _key2infoset=_key2infoset)
            episodeOf.extract()
        cRole = tag.find('current-role', recursive=False)
        if cRole:
            cr = parseTags(cRole, _topLevel=False, _as=_as,
                        _infoset2keys=_infoset2keys, _key2infoset=_key2infoset)
            item.currentRole = cr
            cRole.extract()
        # XXX: big assumption, here.  What about Movie instances used
        #      as keys in dictionaries?  What about other keys (season and
        #      episode number, for example?)
        if not _topLevel:
            #tag.extract()
            return item
        _adder = lambda key, value: item.data.update({key: value})
    elif tagStr:
        if tag.notes:
            notes = (tag.notes.string or u'').strip()
            if notes:
                tagStr += u'::%s' % notes
        else:
            tagStr = _valueWithType(tag, tagStr)
        return tagStr
    elif firstChild:
        firstChildName = tagToKey(firstChild)
        if firstChildName in _TAGS_TO_LIST:
            item = []
            _adder = lambda key, value: item.append(value)
        else:
            item = {}
            _adder = lambda key, value: item.update({key: value})
    else:
        item = {}
        _adder = lambda key, value: item.update({name: value})
    for subTag in tag(recursive=False):
        subTagKey = tagToKey(subTag)
        # Exclude dinamically generated keys.
        if tag.name in _MAP_TOP_OBJ and subTagKey in item._additional_keys():
            continue
        subItem = parseTags(subTag, _topLevel=False, _as=_as,
                        _infoset2keys=_infoset2keys, _key2infoset=_key2infoset)
        if subItem:
            _adder(subTagKey, subItem)
    if _topLevel and name in _MAP_TOP_OBJ:
        # Add information about 'info sets', but only to the top-level object.
        item.infoset2keys = _infoset2keys
        item.key2infoset = _key2infoset
        item.current_info = _infoset2keys.keys()
    return item


def parseXML(xml):
    """Parse a XML string, returning an appropriate object (usually an
    instance of a subclass of _Container."""
    xmlObj = BeautifulSoup.BeautifulStoneSoup(xml,
                convertEntities=BeautifulSoup.BeautifulStoneSoup.XHTML_ENTITIES)
    if xmlObj:
        mainTag = xmlObj.find()
        if mainTag:
            return parseTags(mainTag)
    return None


_re_akas_lang = re.compile('(?:[(])([a-zA-Z]+?)(?: title[)])')
_re_akas_country = re.compile('\(.*?\)')

# akasLanguages, sortAKAsBySimilarity and getAKAsInLanguage code
# copyright of Alberto Malagoli (refactoring by Davide Alberani).
def akasLanguages(movie):
    """Given a movie, return a list of tuples in (lang, AKA) format;
    lang can be None, if unable to detect."""
    lang_and_aka = []
    akas = set((movie.get('akas') or []) +
                (movie.get('akas from release info') or []))
    for aka in akas:
        # split aka
        aka = aka.encode('utf8').split('::')
        # sometimes there is no countries information
        if len(aka) == 2:
            # search for something like "(... title)" where ... is a language
            language = _re_akas_lang.search(aka[1])
            if language:
                language = language.groups()[0]
            else:
                # split countries using , and keep only the first one (it's sufficient)
                country = aka[1].split(',')[0]
                # remove parenthesis
                country = _re_akas_country.sub('', country).strip()
                # given the country, get corresponding language from dictionary
                language = COUNTRY_LANG.get(country)
        else:
            language = None
        lang_and_aka.append((language, aka[0].decode('utf8')))
    return lang_and_aka


def sortAKAsBySimilarity(movie, title, _titlesOnly=True, _preferredLang=None):
    """Return a list of movie AKAs, sorted by their similarity to
    the given title.
    If _titlesOnly is not True, similarity information are returned.
    If _preferredLang is specified, AKAs in the given language will get
    a higher score.
    The return is a list of title, or a list of tuples if _titlesOnly is False."""
    language = movie.guessLanguage()
    # estimate string distance between current title and given title
    m_title = movie['title'].lower()
    l_title = title.lower()
    if isinstance(l_title, unicode):
        l_title = l_title.encode('utf8')
    scores = []
    score = difflib.SequenceMatcher(None, m_title.encode('utf8'), l_title).ratio()
    # set original title and corresponding score as the best match for given title
    scores.append((score, movie['title'], None))
    for language, aka in akasLanguages(movie):
        # estimate string distance between current title and given title
        m_title = aka.lower()
        if isinstance(m_title, unicode):
            m_title = m_title.encode('utf8')
        score = difflib.SequenceMatcher(None, m_title, l_title).ratio()
        # if current language is the same as the given one, increase score
        if _preferredLang and _preferredLang == language:
            score += 1
        scores.append((score, aka, language))
    scores.sort(reverse=True)
    if _titlesOnly:
        return [x[1] for x in scores]
    return scores


def getAKAsInLanguage(movie, lang, _searchedTitle=None):
    """Return a list of AKAs of a movie, in the specified language.
    If _searchedTitle is given, the AKAs are sorted by their similarity
    to it."""
    akas = []
    for language, aka in akasLanguages(movie):
        if lang == language:
            akas.append(aka)
    if _searchedTitle:
        scores = []
        if isinstance(_searchedTitle, unicode):
            _searchedTitle = _searchedTitle.encode('utf8')
        for aka in akas:
            m_aka = aka
            if isinstance(m_aka):
                m_aka = m_aka.encode('utf8')
            scores.append(difflib.SequenceMatcher(None, m_aka.lower(),
                            _searchedTitle.lower()), aka)
        scores.sort(reverse=True)
        akas = [x[1] for x in scores]
    return akas


########NEW FILE########
__FILENAME__ = linguistics
"""
linguistics module (imdb package).

This module provides functions and data to handle in a smart way
languages and articles (in various languages) at the beginning of movie titles.

Copyright 2009-2012 Davide Alberani <da@erlug.linux.it>
          2012 Alberto Malagoli <albemala AT gmail.com>
          2009 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

# List of generic articles used when the language of the title is unknown (or
# we don't have information about articles in that language).
# XXX: Managing titles in a lot of different languages, a function to recognize
# an initial article can't be perfect; sometimes we'll stumble upon a short
# word that is an article in some language, but it's not in another; in these
# situations we have to choose if we want to interpret this little word
# as an article or not (remember that we don't know what the original language
# of the title was).
# Example: 'en' is (I suppose) an article in Some Language.  Unfortunately it
# seems also to be a preposition in other languages (French?).
# Running a script over the whole list of titles (and aliases), I've found
# that 'en' is used as an article only 376 times, and as another thing 594
# times, so I've decided to _always_ consider 'en' as a non article.
#
# Here is a list of words that are _never_ considered as articles, complete
# with the cound of times they are used in a way or another:
# 'en' (376 vs 594), 'to' (399 vs 727), 'as' (198 vs 276), 'et' (79 vs 99),
# 'des' (75 vs 150), 'al' (78 vs 304), 'ye' (14 vs 70),
# 'da' (23 vs 298), "'n" (8 vs 12)
#
# I've left in the list 'i' (1939 vs 2151) and 'uno' (52 vs 56)
# I'm not sure what '-al' is, and so I've left it out...
#
# Generic list of articles in utf-8 encoding:
GENERIC_ARTICLES = ('the', 'la', 'a', 'die', 'der', 'le', 'el',
            "l'", 'il', 'das', 'les', 'i', 'o', 'ein', 'un', 'de', 'los',
            'an', 'una', 'las', 'eine', 'den', 'het', 'gli', 'lo', 'os',
            'ang', 'oi', 'az', 'een', 'ha-', 'det', 'ta', 'al-',
            'mga', "un'", 'uno', 'ett', 'dem', 'egy', 'els', 'eines',
            '\xc3\x8f', '\xc3\x87', '\xc3\x94\xc3\xaf', '\xc3\x8f\xc3\xa9')


# Lists of articles separated by language.  If possible, the list should
# be sorted by frequency (not very important, but...)
# If you want to add a list of articles for another language, mail it
# it at imdbpy-devel@lists.sourceforge.net; non-ascii articles must be utf-8
# encoded.
LANG_ARTICLES = {
    'English': ('the', 'a', 'an'),
    'Italian': ('la', 'le', "l'", 'il', 'i', 'un', 'una', 'gli', 'lo', "un'",
                'uno'),
    'Spanish': ('la', 'lo', 'el', 'las', 'un', 'los', 'una', 'al', 'del',
                'unos', 'unas', 'uno'),
    'French': ('le', "l'", 'la', 'les', 'un', 'une', 'des', 'au', 'du', '\xc3\xa0 la',
                'de la', 'aux'),
    'Portuguese': ('a', 'as', 'o', 'os', 'um', 'uns', 'uma', 'umas'),
    'Turkish': (), # Some languages doesn't have articles.
}
LANG_ARTICLESget = LANG_ARTICLES.get


# Maps a language to countries where it is the main language.
# If you want to add an entry for another language or country, mail it at
# imdbpy-devel@lists.sourceforge.net .
LANG_COUNTRIES = {
    'English': ('Canada', 'Swaziland', 'Ghana', 'St. Lucia', 'Liberia', 'Jamaica', 'Bahamas', 'New Zealand', 'Lesotho', 'Kenya', 'Solomon Islands', 'United States', 'South Africa', 'St. Vincent and the Grenadines', 'Fiji', 'UK', 'Nigeria', 'Australia', 'USA', 'St. Kitts and Nevis', 'Belize', 'Sierra Leone', 'Gambia', 'Namibia', 'Micronesia', 'Kiribati', 'Grenada', 'Antigua and Barbuda', 'Barbados', 'Malta', 'Zimbabwe', 'Ireland', 'Uganda', 'Trinidad and Tobago', 'South Sudan', 'Guyana', 'Botswana', 'United Kingdom', 'Zambia'),
    'Italian': ('Italy', 'San Marino', 'Vatican City'),
    'Spanish': ('Spain', 'Mexico', 'Argentina', 'Bolivia', 'Guatemala', 'Uruguay', 'Peru', 'Cuba', 'Dominican Republic', 'Panama', 'Costa Rica', 'Ecuador', 'El Salvador', 'Chile', 'Equatorial Guinea', 'Spain', 'Colombia', 'Nicaragua', 'Venezuela', 'Honduras', 'Paraguay'),
    'French': ('Cameroon', 'Burkina Faso', 'Dominica', 'Gabon', 'Monaco', 'France', "Cote d'Ivoire", 'Benin', 'Togo', 'Central African Republic', 'Mali', 'Niger', 'Congo, Republic of', 'Guinea', 'Congo, Democratic Republic of the', 'Luxembourg', 'Haiti', 'Chad', 'Burundi', 'Madagascar', 'Comoros', 'Senegal'),
    'Portuguese': ('Portugal', 'Brazil', 'Sao Tome and Principe', 'Cape Verde', 'Angola',  'Mozambique', 'Guinea-Bissau'),
    'German': ('Liechtenstein', 'Austria', 'West Germany', 'Switzerland', 'East Germany', 'Germany'),
    'Arabic': ('Saudi Arabia', 'Kuwait', 'Jordan', 'Oman', 'Yemen', 'United Arab Emirates', 'Mauritania', 'Lebanon', 'Bahrain', 'Libya', 'Palestinian State (proposed)', 'Qatar', 'Algeria', 'Morocco', 'Iraq', 'Egypt', 'Djibouti', 'Sudan', 'Syria', 'Tunisia'),
    'Turkish': ('Turkey', 'Azerbaijan'),
    'Swahili': ('Tanzania',),
    'Swedish': ('Sweden',),
    'Icelandic': ('Iceland',),
    'Estonian': ('Estonia',),
    'Romanian': ('Romania',),
    'Samoan': ('Samoa',),
    'Slovenian': ('Slovenia',),
    'Tok Pisin': ('Papua New Guinea',),
    'Palauan': ('Palau',),
    'Macedonian': ('Macedonia',),
    'Hindi': ('India',),
    'Dutch': ('Netherlands', 'Belgium', 'Suriname'),
    'Marshallese': ('Marshall Islands',),
    'Korean': ('Korea, North', 'Korea, South', 'North Korea', 'South Korea'),
    'Vietnamese': ('Vietnam',),
    'Danish': ('Denmark',),
    'Khmer': ('Cambodia',),
    'Lao': ('Laos',),
    'Somali': ('Somalia',),
    'Filipino': ('Philippines',),
    'Hungarian': ('Hungary',),
    'Ukrainian': ('Ukraine',),
    'Bosnian': ('Bosnia and Herzegovina',),
    'Georgian': ('Georgia',),
    'Lithuanian': ('Lithuania',),
    'Malay': ('Brunei',),
    'Tetum': ('East Timor',),
    'Norwegian': ('Norway',),
    'Armenian': ('Armenia',),
    'Russian': ('Russia',),
    'Slovak': ('Slovakia',),
    'Thai': ('Thailand',),
    'Croatian': ('Croatia',),
    'Turkmen': ('Turkmenistan',),
    'Nepali': ('Nepal',),
    'Finnish': ('Finland',),
    'Uzbek': ('Uzbekistan',),
    'Albanian': ('Albania', 'Kosovo'),
    'Hebrew': ('Israel',),
    'Bulgarian': ('Bulgaria',),
    'Greek': ('Cyprus', 'Greece'),
    'Burmese': ('Myanmar',),
    'Latvian': ('Latvia',),
    'Serbian': ('Serbia',),
    'Afar': ('Eritrea',),
    'Catalan': ('Andorra',),
    'Chinese': ('China', 'Taiwan'),
    'Czech': ('Czech Republic', 'Czechoslovakia'),
    'Bislama': ('Vanuatu',),
    'Japanese': ('Japan',),
    'Kinyarwanda': ('Rwanda',),
    'Amharic': ('Ethiopia',),
    'Persian': ('Afghanistan', 'Iran'),
    'Tajik': ('Tajikistan',),
    'Mongolian': ('Mongolia',),
    'Dzongkha': ('Bhutan',),
    'Urdu': ('Pakistan',),
    'Polish': ('Poland',),
    'Sinhala': ('Sri Lanka',),
}

# Maps countries to their main language.
COUNTRY_LANG = {}
for lang in LANG_COUNTRIES:
    for country in LANG_COUNTRIES[lang]:
        COUNTRY_LANG[country] = lang


def toUnicode(articles):
    """Convert a list of articles utf-8 encoded to unicode strings."""
    return tuple([art.decode('utf_8') for art in articles])


def toDicts(articles):
    """Given a list of utf-8 encoded articles, build two dictionary (one
    utf-8 encoded and another one with unicode keys) for faster matches."""
    uArticles = toUnicode(articles)
    return dict([(x, x) for x in articles]), dict([(x, x) for x in uArticles])


def addTrailingSpace(articles):
    """From the given list of utf-8 encoded articles, return two
    lists (one utf-8 encoded and another one in unicode) where a space
    is added at the end - if the last char is not ' or -."""
    _spArticles = []
    _spUnicodeArticles = []
    for article in articles:
        if article[-1] not in ("'", '-'):
            article += ' '
        _spArticles.append(article)
        _spUnicodeArticles.append(article.decode('utf_8'))
    return _spArticles, _spUnicodeArticles


# Caches.
_ART_CACHE = {}
_SP_ART_CACHE = {}

def articlesDictsForLang(lang):
    """Return dictionaries of articles specific for the given language, or the
    default one if the language is not known."""
    if lang in _ART_CACHE:
        return _ART_CACHE[lang]
    artDicts = toDicts(LANG_ARTICLESget(lang, GENERIC_ARTICLES))
    _ART_CACHE[lang] = artDicts
    return artDicts


def spArticlesForLang(lang):
    """Return lists of articles (plus optional spaces) specific for the
    given language, or the default one if the language is not known."""
    if lang in _SP_ART_CACHE:
        return _SP_ART_CACHE[lang]
    spArticles = addTrailingSpace(LANG_ARTICLESget(lang, GENERIC_ARTICLES))
    _SP_ART_CACHE[lang] = spArticles
    return spArticles


########NEW FILE########
__FILENAME__ = generatepot
#!/usr/bin/env python
"""
generatepot.py script.

This script generates the imdbpy.pot file, from the DTD.

Copyright 2009 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
import sys

from datetime import datetime as dt

DEFAULT_MESSAGES = { }

ELEMENT_PATTERN = r"""<!ELEMENT\s+([^\s]+)"""
re_element = re.compile(ELEMENT_PATTERN)

POT_HEADER_TEMPLATE = r"""# Gettext message file for imdbpy
msgid ""
msgstr ""
"Project-Id-Version: imdbpy\n"
"POT-Creation-Date: %(now)s\n"
"PO-Revision-Date: YYYY-MM-DD HH:MM+0000\n"
"Last-Translator: YOUR NAME <YOUR@EMAIL>\n"
"Language-Team: TEAM NAME <TEAM@EMAIL>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=1; plural=0;\n"
"Language-Code: en\n"
"Language-Name: English\n"
"Preferred-Encodings: utf-8\n"
"Domain: imdbpy\n"
"""

if len(sys.argv) != 2:
    print "Usage: %s dtd_file" % sys.argv[0]
    sys.exit()

dtdfilename = sys.argv[1]
dtd = open(dtdfilename).read()
elements = re_element.findall(dtd)
uniq = set(elements)
elements = list(uniq)

print POT_HEADER_TEMPLATE % {
    'now': dt.strftime(dt.now(), "%Y-%m-%d %H:%M+0000")
}
for element in sorted(elements):
    if element in DEFAULT_MESSAGES:
        print '# Default: %s' % DEFAULT_MESSAGES[element]
    else:
        print '# Default: %s' % element.replace('-', ' ').capitalize()
    print 'msgid "%s"' % element
    print 'msgstr ""'
    # use this part instead of the line above to generate the po file for English
    #if element in DEFAULT_MESSAGES:
    #    print 'msgstr "%s"' % DEFAULT_MESSAGES[element]
    #else:
    #    print 'msgstr "%s"' % element.replace('-', ' ').capitalize()
    print


########NEW FILE########
__FILENAME__ = msgfmt
#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Generate binary message catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a binary GNU catalog (.mo file).  This is essentially the same function as the
GNU msgfmt program, however, it is a simpler implementation.

Usage: msgfmt.py [OPTIONS] filename.po

Options:
    -o file
    --output-file=file
        Specify the output file to write to.  If omitted, output will go to a
        file named filename.mo (based off the input file name).

    -h
    --help
        Print this message and exit.

    -V
    --version
        Display version information and exit.

Written by Martin v. Löwis <loewis@informatik.hu-berlin.de>,
refactored / fixed by Thomas Waldmann <tw AT waldmann-edv DOT de>.
"""

import sys, os
import getopt, struct, array

__version__ = "1.3"

class SyntaxErrorException(Exception):
    """raised when having trouble parsing the po file content"""
    pass

class MsgFmt(object):
    """transform .po -> .mo format"""
    def __init__(self):
        self.messages = {}

    def make_filenames(self, filename, outfile=None):
        """Compute .mo name from .po name or language"""
        if filename.endswith('.po'):
            infile = filename
        else:
            infile = filename + '.po'
        if outfile is None:
            outfile = os.path.splitext(infile)[0] + '.mo'
        return infile, outfile

    def add(self, id, str, fuzzy):
        """Add a non-fuzzy translation to the dictionary."""
        if not fuzzy and str:
            self.messages[id] = str

    def read_po(self, lines):
        ID = 1
        STR = 2
        section = None
        fuzzy = False
        line_no = 0
        msgid = msgstr = ''
        # Parse the catalog
        for line in lines:
            line_no += 1
            # If we get a comment line after a msgstr, this is a new entry
            if line.startswith('#') and section == STR:
                self.add(msgid, msgstr, fuzzy)
                section = None
                fuzzy = False
            # Record a fuzzy mark
            if line.startswith('#,') and 'fuzzy' in line:
                fuzzy = True
            # Skip comments
            if line.startswith('#'):
                continue
            # Now we are in a msgid section, output previous section
            if line.startswith('msgid'):
                if section == STR:
                    self.add(msgid, msgstr, fuzzy)
                    fuzzy = False
                section = ID
                line = line[5:]
                msgid = msgstr = ''
            # Now we are in a msgstr section
            elif line.startswith('msgstr'):
                section = STR
                line = line[6:]
            # Skip empty lines
            line = line.strip()
            if not line:
                continue
            # XXX: Does this always follow Python escape semantics?
            line = eval(line)
            if section == ID:
                msgid += line
            elif section == STR:
                msgstr += line
            else:
                raise SyntaxErrorException('Syntax error on line %d, before:\n%s' % (line_no, line))
        # Add last entry
        if section == STR:
            self.add(msgid, msgstr, fuzzy)

    def generate_mo(self):
        """Return the generated output."""
        keys = self.messages.keys()
        # the keys are sorted in the .mo file
        keys.sort()
        offsets = []
        ids = ''
        strs = ''
        for id in keys:
            # For each string, we need size and file offset.  Each string is NUL
            # terminated; the NUL does not count into the size.
            offsets.append((len(ids), len(id), len(strs), len(self.messages[id])))
            ids += id + '\0'
            strs += self.messages[id] + '\0'
        output = []
        # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
        # the keys start right after the index tables.
        # translated string.
        keystart = 7*4 + 16*len(keys)
        # and the values start after the keys
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        # The string table first has the list of keys, then the list of values.
        # Each entry has first the size of the string, then the file offset.
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1 + keystart]
            voffsets += [l2, o2 + valuestart]
        offsets = koffsets + voffsets
        output.append(struct.pack("Iiiiiii",
                             0x950412deL,       # Magic
                             0,                 # Version
                             len(keys),         # # of entries
                             7*4,               # start of key index
                             7*4 + len(keys)*8, # start of value index
                             0, 0))             # size and offset of hash table
        output.append(array.array("i", offsets).tostring())
        output.append(ids)
        output.append(strs)
        return ''.join(output)


def make(filename, outfile):
    mf = MsgFmt()
    infile, outfile = mf.make_filenames(filename, outfile)
    try:
        lines = file(infile).readlines()
    except IOError, msg:
        print >> sys.stderr, msg
        sys.exit(1)
    try:
        mf.read_po(lines)
        output = mf.generate_mo()
    except SyntaxErrorException, msg:
        print >> sys.stderr, msg

    try:
        open(outfile, "wb").write(output)
    except IOError, msg:
        print >> sys.stderr, msg


def usage(code, msg=''):
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hVo:', ['help', 'version', 'output-file='])
    except getopt.error, msg:
        usage(1, msg)

    outfile = None
    # parse options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print >> sys.stderr, "msgfmt.py", __version__
            sys.exit(0)
        elif opt in ('-o', '--output-file'):
            outfile = arg
    # do it
    if not args:
        print >> sys.stderr, 'No input file given'
        print >> sys.stderr, "Try `msgfmt --help' for more information."
        return

    for filename in args:
        make(filename, outfile)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = rebuildmo
#!/usr/bin/env python
"""
rebuildmo.py script.

This script builds the .mo files, from the .po files.

Copyright 2009 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import glob
import msgfmt
import os

#LOCALE_DIR = os.path.dirname(__file__)

def rebuildmo():
    lang_glob = 'imdbpy-*.po'
    created = []
    for input_file in glob.glob(lang_glob):
        lang = input_file[7:-3]
        if not os.path.exists(lang):
            os.mkdir(lang)
        mo_dir = os.path.join(lang, 'LC_MESSAGES')
        if not os.path.exists(mo_dir):
            os.mkdir(mo_dir)
        output_file = os.path.join(mo_dir, 'imdbpy.mo')
        msgfmt.make(input_file, output_file)
        created.append(lang)
    return created


if __name__ == '__main__':
    languages = rebuildmo()
    print 'Created locale for: %s.' % ' '.join(languages)


########NEW FILE########
__FILENAME__ = Movie
"""
Movie module (imdb package).

This module provides the Movie class, used to store information about
a given movie.

Copyright 2004-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from copy import deepcopy

from imdb import linguistics
from imdb.utils import analyze_title, build_title, canonicalTitle, \
                        flatten, _Container, cmpMovies


class Movie(_Container):
    """A Movie.

    Every information about a movie can be accessed as:
        movieObject['information']
    to get a list of the kind of information stored in a
    Movie object, use the keys() method; some useful aliases
    are defined (as "casting" for the "casting director" key); see
    the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main', 'plot')

    # Aliases for some not-so-intuitive keys.
    keys_alias = {
                'tv schedule': 'airing',
                'user rating':  'rating',
                'plot summary': 'plot',
                'plot summaries': 'plot',
                'directed by':  'director',
                'created by': 'creator',
                'writing credits': 'writer',
                'produced by':  'producer',
                'original music by':    'original music',
                'non-original music by':    'non-original music',
                'music':    'original music',
                'cinematography by':    'cinematographer',
                'cinematography':   'cinematographer',
                'film editing by':  'editor',
                'film editing': 'editor',
                'editing':  'editor',
                'actors':   'cast',
                'actresses':    'cast',
                'casting by':   'casting director',
                'casting':  'casting director',
                'art direction by': 'art direction',
                'set decoration by':    'set decoration',
                'costume design by':    'costume designer',
                'costume design':    'costume designer',
                'makeup department':    'make up',
                'makeup':    'make up',
                'make-up':    'make up',
                'production management':    'production manager',
                'production company':    'production companies',
                'second unit director or assistant director':
                                                'assistant director',
                'second unit director':   'assistant director',
                'sound department': 'sound crew',
                'costume and wardrobe department': 'costume department',
                'special effects by':   'special effects',
                'visual effects by':    'visual effects',
                'special effects company':   'special effects companies',
                'stunts':   'stunt performer',
                'other crew':   'miscellaneous crew',
                'misc crew':   'miscellaneous crew',
                'miscellaneouscrew':   'miscellaneous crew',
                'crewmembers': 'miscellaneous crew',
                'crew members': 'miscellaneous crew',
                'other companies': 'miscellaneous companies',
                'misc companies': 'miscellaneous companies',
                'miscellaneous company': 'miscellaneous companies',
                'misc company': 'miscellaneous companies',
                'other company': 'miscellaneous companies',
                'aka':  'akas',
                'also known as':    'akas',
                'country':  'countries',
                'production country':  'countries',
                'production countries':  'countries',
                'genre': 'genres',
                'runtime':  'runtimes',
                'lang': 'languages',
                'color': 'color info',
                'cover': 'cover url',
                'full-size cover': 'full-size cover url',
                'seasons': 'number of seasons',
                'language': 'languages',
                'certificate':  'certificates',
                'certifications':   'certificates',
                'certification':    'certificates',
                'miscellaneous links':  'misc links',
                'miscellaneous':    'misc links',
                'soundclips':   'sound clips',
                'videoclips':   'video clips',
                'photographs':  'photo sites',
                'distributor': 'distributors',
                'distribution': 'distributors',
                'distribution companies': 'distributors',
                'distribution company': 'distributors',
                'guest': 'guests',
                'guest appearances': 'guests',
                'tv guests': 'guests',
                'notable tv guest appearances': 'guests',
                'episodes cast': 'guests',
                'episodes number': 'number of episodes',
                'amazon review': 'amazon reviews',
                'merchandising': 'merchandising links',
                'merchandise': 'merchandising links',
                'sales': 'merchandising links',
                'faq': 'faqs',
                'parental guide': 'parents guide',
                'frequently asked questions': 'faqs'}

    keys_tomodify_list = ('plot', 'trivia', 'alternate versions', 'goofs',
                        'quotes', 'dvd', 'laserdisc', 'news', 'soundtrack',
                        'crazy credits', 'business', 'supplements',
                        'video review', 'faqs')

    cmpFunct = cmpMovies

    def _init(self, **kwds):
        """Initialize a Movie object.

        *movieID* -- the unique identifier for the movie.
        *title* -- the title of the Movie, if not in the data dictionary.
        *myTitle* -- your personal title for the movie.
        *myID* -- your personal identifier for the movie.
        *data* -- a dictionary used to initialize the object.
        *currentRole* -- a Character instance representing the current role
                         or duty of a person in this movie, or a Person
                         object representing the actor/actress who played
                         a given character in a Movie.  If a string is
                         passed, an object is automatically build.
        *roleID* -- if available, the characterID/personID of the currentRole
                    object.
        *roleIsPerson* -- when False (default) the currentRole is assumed
                          to be a Character object, otherwise a Person.
        *notes* -- notes for the person referred in the currentRole
                    attribute; e.g.: '(voice)'.
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to characters.
        *modFunct* -- function called returning text fields.
        """
        title = kwds.get('title')
        if title and not self.data.has_key('title'):
            self.set_title(title)
        self.movieID = kwds.get('movieID', None)
        self.myTitle = kwds.get('myTitle', u'')

    def _reset(self):
        """Reset the Movie object."""
        self.movieID = None
        self.myTitle = u''

    def set_title(self, title):
        """Set the title of the movie."""
        # XXX: convert title to unicode, if it's a plain string?
        d_title = analyze_title(title)
        self.data.update(d_title)

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        addkeys = []
        if self.data.has_key('title'):
            addkeys += ['canonical title', 'long imdb title',
                        'long imdb canonical title',
                        'smart canonical title',
                        'smart long imdb canonical title']
        if self.data.has_key('episode of'):
            addkeys += ['long imdb episode title', 'series title',
                        'canonical series title', 'episode title',
                        'canonical episode title',
                        'smart canonical series title',
                        'smart canonical episode title']
        if self.data.has_key('cover url'):
            addkeys += ['full-size cover url']
        return addkeys

    def guessLanguage(self):
        """Guess the language of the title of this movie; returns None
        if there are no hints."""
        lang = self.get('languages')
        if lang:
            lang = lang[0]
        else:
            country = self.get('countries')
            if country:
                lang = linguistics.COUNTRY_LANG.get(country[0])
        return lang

    def smartCanonicalTitle(self, title=None, lang=None):
        """Return the canonical title, guessing its language.
        The title can be forces with the 'title' argument (internally
        used) and the language can be forced with the 'lang' argument,
        otherwise it's auto-detected."""
        if title is None:
            title = self.data.get('title', u'')
        if lang is None:
            lang = self.guessLanguage()
        return canonicalTitle(title, lang=lang)

    def _getitem(self, key):
        """Handle special keys."""
        if self.data.has_key('episode of'):
            if key == 'long imdb episode title':
                return build_title(self.data)
            elif key == 'series title':
                return self.data['episode of']['title']
            elif key == 'canonical series title':
                ser_title = self.data['episode of']['title']
                return canonicalTitle(ser_title)
            elif key == 'smart canonical series title':
                ser_title = self.data['episode of']['title']
                return self.smartCanonicalTitle(ser_title)
            elif key == 'episode title':
                return self.data.get('title', u'')
            elif key == 'canonical episode title':
                return canonicalTitle(self.data.get('title', u''))
            elif key == 'smart canonical episode title':
                return self.smartCanonicalTitle(self.data.get('title', u''))
        if self.data.has_key('title'):
            if key == 'title':
                return self.data['title']
            elif key == 'long imdb title':
                return build_title(self.data)
            elif key == 'canonical title':
                return canonicalTitle(self.data['title'])
            elif key == 'smart canonical title':
                return self.smartCanonicalTitle(self.data['title'])
            elif key == 'long imdb canonical title':
                return build_title(self.data, canonical=1)
            elif key == 'smart long imdb canonical title':
                return build_title(self.data, canonical=1,
                                    lang=self.guessLanguage())
        if key == 'full-size cover url' and self.data.has_key('cover url'):
            return self._re_fullsizeURL.sub('', self.data.get('cover url', ''))
        return None

    def getID(self):
        """Return the movieID."""
        return self.movieID

    def __nonzero__(self):
        """The Movie is "false" if the self.data does not contain a title."""
        # XXX: check the title and the movieID?
        if self.data.has_key('title'): return 1
        return 0

    def isSameTitle(self, other):
        """Return true if this and the compared object have the same
        long imdb title and/or movieID.
        """
        # XXX: obsolete?
        if not isinstance(other, self.__class__): return 0
        if self.data.has_key('title') and \
                other.data.has_key('title') and \
                build_title(self.data, canonical=0) == \
                build_title(other.data, canonical=0):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.movieID is not None and self.movieID == other.movieID:
            return 1
        return 0
    isSameMovie = isSameTitle # XXX: just for backward compatiblity.

    def __contains__(self, item):
        """Return true if the given Person object is listed in this Movie,
        or if the the given Character is represented in this Movie."""
        from Person import Person
        from Character import Character
        from Company import Company
        if isinstance(item, Person):
            for p in flatten(self.data, yieldDictKeys=1, scalar=Person,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(p):
                    return 1
        elif isinstance(item, Character):
            for p in flatten(self.data, yieldDictKeys=1, scalar=Person,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(p.currentRole):
                    return 1
        elif isinstance(item, Company):
            for c in flatten(self.data, yieldDictKeys=1, scalar=Company,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(c):
                    return 1
        return 0

    def __deepcopy__(self, memo):
        """Return a deep copy of a Movie instance."""
        m = Movie(title=u'', movieID=self.movieID, myTitle=self.myTitle,
                    myID=self.myID, data=deepcopy(self.data, memo),
                    currentRole=deepcopy(self.currentRole, memo),
                    roleIsPerson=self._roleIsPerson,
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        m.current_info = list(self.current_info)
        m.set_mod_funct(self.modFunct)
        return m

    def __repr__(self):
        """String representation of a Movie object."""
        # XXX: add also currentRole and notes, if present?
        if self.has_key('long imdb episode title'):
            title = self.get('long imdb episode title')
        else:
            title = self.get('long imdb title')
        r = '<Movie id:%s[%s] title:_%s_>' % (self.movieID, self.accessSystem,
                                                title)
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short title."""
        return self.get('title', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('title', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the movie."""
        if not self: return u''
        def _nameAndRole(personList, joiner=u', '):
            """Build a pretty string with name and role."""
            nl = []
            for person in personList:
                n = person.get('name', u'')
                if person.currentRole: n += u' (%s)' % person.currentRole
                nl.append(n)
            return joiner.join(nl)
        s = u'Movie\n=====\nTitle: %s\n' % \
                    self.get('long imdb canonical title', u'')
        genres = self.get('genres')
        if genres: s += u'Genres: %s.\n' % u', '.join(genres)
        director = self.get('director')
        if director:
            s += u'Director: %s.\n' % _nameAndRole(director)
        writer = self.get('writer')
        if writer:
            s += u'Writer: %s.\n' % _nameAndRole(writer)
        cast = self.get('cast')
        if cast:
            cast = cast[:5]
            s += u'Cast: %s.\n' % _nameAndRole(cast)
        runtime = self.get('runtimes')
        if runtime:
            s += u'Runtime: %s.\n' % u', '.join(runtime)
        countries = self.get('countries')
        if countries:
            s += u'Country: %s.\n' % u', '.join(countries)
        lang = self.get('languages')
        if lang:
            s += u'Language: %s.\n' % u', '.join(lang)
        rating = self.get('rating')
        if rating:
            s += u'Rating: %s' % rating
            nr_votes = self.get('votes')
            if nr_votes:
                s += u' (%s votes)' % nr_votes
            s += u'.\n'
        plot = self.get('plot')
        if not plot:
            plot = self.get('plot summary')
            if plot:
                plot = [plot]
        if plot:
            plot = plot[0]
            i = plot.find('::')
            if i != -1:
                plot = plot[:i]
            s += u'Plot: %s' % plot
        return s



########NEW FILE########
__FILENAME__ = bsoupxpath
"""
parser.http.bsoupxpath module (imdb.parser.http package).

This module provides XPath support for BeautifulSoup.

Copyright 2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

__author__ = 'H. Turgut Uyar <uyar@tekir.org>'
__docformat__ = 'restructuredtext'


import re
import string
import _bsoup as BeautifulSoup


# XPath related enumerations and constants

AXIS_ANCESTOR          = 'ancestor'
AXIS_ATTRIBUTE         = 'attribute'
AXIS_CHILD             = 'child'
AXIS_DESCENDANT        = 'descendant'
AXIS_FOLLOWING         = 'following'
AXIS_FOLLOWING_SIBLING = 'following-sibling'
AXIS_PRECEDING_SIBLING = 'preceding-sibling'

AXES = (AXIS_ANCESTOR, AXIS_ATTRIBUTE, AXIS_CHILD, AXIS_DESCENDANT,
        AXIS_FOLLOWING, AXIS_FOLLOWING_SIBLING, AXIS_PRECEDING_SIBLING)

XPATH_FUNCTIONS = ('starts-with', 'string-length', 'contains')


def tokenize_path(path):
    """Tokenize a location path into location steps. Return the list of steps.

    If two steps are separated by a double slash, the double slashes are part of
    the second step. If they are separated by only one slash, the slash is not
    included in any of the steps.
    """
    # form a list of tuples that mark the start and end positions of steps
    separators = []
    last_position = 0
    i = -1
    in_string = False
    while i < len(path) - 1:
        i = i + 1
        if path[i] == "'":
            in_string = not in_string
        if in_string:
            # slashes within strings are not step separators
            continue
        if path[i] == '/':
            if i > 0:
                separators.append((last_position, i))
            if (path[i+1] == '/'):
                last_position = i
                i = i + 1
            else:
                last_position = i + 1
    separators.append((last_position, len(path)))

    steps = []
    for start, end in separators:
        steps.append(path[start:end])
    return steps


class Path:
    """A location path.
    """

    def __init__(self, path, parse=True):
        self.path = path
        self.steps = []
        if parse:
            if (path[0] == '/') and (path[1] != '/'):
                # if not on the descendant axis, remove the leading slash
                path = path[1:]
            steps = tokenize_path(path)
            for step in steps:
                self.steps.append(PathStep(step))

    def apply(self, node):
        """Apply the path to a node. Return the resulting list of nodes.

        Apply the steps in the path sequentially by sending the output of each
        step as input to the next step.
        """
        # FIXME: this should return a node SET, not a node LIST
        # or at least a list with no duplicates
        if self.path[0] == '/':
            # for an absolute path, start from the root
            if not isinstance(node, BeautifulSoup.Tag) \
               or (node.name != '[document]'):
                node = node.findParent('[document]')
        nodes = [node]
        for step in self.steps:
            nodes = step.apply(nodes)
        return nodes


class PathStep:
    """A location step in a location path.
    """

    AXIS_PATTERN          = r"""(%s)::|@""" % '|'.join(AXES)
    NODE_TEST_PATTERN     = r"""\w+(\(\))?"""
    PREDICATE_PATTERN     = r"""\[(.*?)\]"""
    LOCATION_STEP_PATTERN = r"""(%s)?(%s)((%s)*)""" \
                          % (AXIS_PATTERN, NODE_TEST_PATTERN, PREDICATE_PATTERN)

    _re_location_step = re.compile(LOCATION_STEP_PATTERN)

    PREDICATE_NOT_PATTERN = r"""not\((.*?)\)"""
    PREDICATE_AXIS_PATTERN = r"""(%s)?(%s)(='(.*?)')?""" \
                           % (AXIS_PATTERN, NODE_TEST_PATTERN)
    PREDICATE_FUNCTION_PATTERN = r"""(%s)\(([^,]+(,\s*[^,]+)*)?\)(=(.*))?""" \
                               % '|'.join(XPATH_FUNCTIONS)

    _re_predicate_not = re.compile(PREDICATE_NOT_PATTERN)
    _re_predicate_axis = re.compile(PREDICATE_AXIS_PATTERN)
    _re_predicate_function = re.compile(PREDICATE_FUNCTION_PATTERN)

    def __init__(self, step):
        self.step = step
        if (step == '.') or (step == '..'):
            return

        if step[:2] == '//':
            default_axis = AXIS_DESCENDANT
            step = step[2:]
        else:
            default_axis = AXIS_CHILD

        step_match = self._re_location_step.match(step)

        # determine the axis
        axis = step_match.group(1)
        if axis is None:
            self.axis = default_axis
        elif axis == '@':
            self.axis = AXIS_ATTRIBUTE
        else:
            self.axis = step_match.group(2)

        self.soup_args = {}
        self.index = None

        self.node_test = step_match.group(3)
        if self.node_test == 'text()':
            self.soup_args['text'] = True
        else:
            self.soup_args['name'] = self.node_test

        self.checkers = []
        predicates = step_match.group(5)
        if predicates is not None:
            predicates = [p for p in predicates[1:-1].split('][') if p]
            for predicate in predicates:
                checker = self.__parse_predicate(predicate)
                if checker is not None:
                    self.checkers.append(checker)

    def __parse_predicate(self, predicate):
        """Parse the predicate. Return a callable that can be used to filter
        nodes. Update `self.soup_args` to take advantage of BeautifulSoup search
        features.
        """
        try:
            position = int(predicate)
            if self.axis == AXIS_DESCENDANT:
                return PredicateFilter('position', value=position)
            else:
                # use the search limit feature instead of a checker
                self.soup_args['limit'] = position
                self.index = position - 1
                return None
        except ValueError:
            pass

        if predicate == "last()":
            self.index = -1
            return None

        negate = self._re_predicate_not.match(predicate)
        if negate:
            predicate = negate.group(1)

        function_match = self._re_predicate_function.match(predicate)
        if function_match:
            name = function_match.group(1)
            arguments = function_match.group(2)
            value = function_match.group(4)
            if value is not None:
                value = function_match.group(5)
            return PredicateFilter(name, arguments, value)

        axis_match = self._re_predicate_axis.match(predicate)
        if axis_match:
            axis = axis_match.group(1)
            if axis is None:
                axis = AXIS_CHILD
            elif axis == '@':
                axis = AXIS_ATTRIBUTE
            if axis == AXIS_ATTRIBUTE:
                # use the attribute search feature instead of a checker
                attribute_name = axis_match.group(3)
                if axis_match.group(5) is not None:
                    attribute_value = axis_match.group(6)
                elif not negate:
                    attribute_value = True
                else:
                    attribute_value = None
                if not self.soup_args.has_key('attrs'):
                    self.soup_args['attrs'] = {}
                self.soup_args['attrs'][attribute_name] = attribute_value
                return None
            elif axis == AXIS_CHILD:
                node_test = axis_match.group(3)
                node_value = axis_match.group(6)
                return PredicateFilter('axis', node_test, value=node_value,
                                       negate=negate)

        raise NotImplementedError("This predicate is not implemented")

    def apply(self, nodes):
        """Apply the step to a list of nodes. Return the list of nodes for the
        next step.
        """
        if self.step == '.':
            return nodes
        elif self.step == '..':
            return [node.parent for node in nodes]

        result = []
        for node in nodes:
            if self.axis == AXIS_CHILD:
                found = node.findAll(recursive=False, **self.soup_args)
            elif self.axis == AXIS_DESCENDANT:
                found = node.findAll(recursive=True, **self.soup_args)
            elif self.axis == AXIS_ATTRIBUTE:
                try:
                    found = [node[self.node_test]]
                except KeyError:
                    found = []
            elif self.axis == AXIS_FOLLOWING_SIBLING:
                found = node.findNextSiblings(**self.soup_args)
            elif self.axis == AXIS_PRECEDING_SIBLING:
                # TODO: make sure that the result is reverse ordered
                found = node.findPreviousSiblings(**self.soup_args)
            elif self.axis == AXIS_FOLLOWING:
                # find the last descendant of this node
                last = node
                while (not isinstance(last, BeautifulSoup.NavigableString)) \
                      and (len(last.contents) > 0):
                    last = last.contents[-1]
                found = last.findAllNext(**self.soup_args)
            elif self.axis == AXIS_ANCESTOR:
                found = node.findParents(**self.soup_args)

            # this should only be active if there is a position predicate
            # and the axis is not 'descendant'
            if self.index is not None:
                if found:
                    if len(found) > self.index:
                        found = [found[self.index]]
                    else:
                        found = []

            if found:
                for checker in self.checkers:
                    found = filter(checker, found)
                result.extend(found)

        return result


class PredicateFilter:
    """A callable class for filtering nodes.
    """

    def __init__(self, name, arguments=None, value=None, negate=False):
        self.name = name
        self.arguments = arguments
        self.negate = negate

        if name == 'position':
            self.__filter = self.__position
            self.value = value
        elif name == 'axis':
            self.__filter = self.__axis
            self.node_test = arguments
            self.value = value
        elif name in ('starts-with', 'contains'):
            if name == 'starts-with':
                self.__filter = self.__starts_with
            else:
                self.__filter = self.__contains
            args = map(string.strip, arguments.split(','))
            if args[0][0] == '@':
                self.arguments = (True, args[0][1:], args[1][1:-1])
            else:
                self.arguments = (False, args[0], args[1][1:-1])
        elif name == 'string-length':
            self.__filter = self.__string_length
            args = map(string.strip, arguments.split(','))
            if args[0][0] == '@':
                self.arguments = (True, args[0][1:])
            else:
                self.arguments = (False, args[0])
            self.value = int(value)
        else:
            raise NotImplementedError("This XPath function is not implemented")

    def __call__(self, node):
        if self.negate:
            return not self.__filter(node)
        else:
            return self.__filter(node)

    def __position(self, node):
        if isinstance(node, BeautifulSoup.NavigableString):
            actual_position = len(node.findPreviousSiblings(text=True)) + 1
        else:
            actual_position = len(node.findPreviousSiblings(node.name)) + 1
        return actual_position == self.value

    def __axis(self, node):
        if self.node_test == 'text()':
            return node.string == self.value
        else:
            children = node.findAll(self.node_test, recursive=False)
            if len(children) > 0 and self.value is None:
                return True
            for child in children:
                if child.string == self.value:
                    return True
            return False

    def __starts_with(self, node):
        if self.arguments[0]:
            # this is an attribute
            attribute_name = self.arguments[1]
            if node.has_key(attribute_name):
                first = node[attribute_name]
                return first.startswith(self.arguments[2])
        elif self.arguments[1] == 'text()':
            first = node.contents and node.contents[0]
            if isinstance(first, BeautifulSoup.NavigableString):
                return first.startswith(self.arguments[2])
        return False

    def __contains(self, node):
        if self.arguments[0]:
            # this is an attribute
            attribute_name = self.arguments[1]
            if node.has_key(attribute_name):
                first = node[attribute_name]
                return self.arguments[2] in first
        elif self.arguments[1] == 'text()':
            first = node.contents and node.contents[0]
            if isinstance(first, BeautifulSoup.NavigableString):
                return self.arguments[2] in first
        return False

    def __string_length(self, node):
        if self.arguments[0]:
            # this is an attribute
            attribute_name = self.arguments[1]
            if node.has_key(attribute_name):
                value = node[attribute_name]
            else:
                value = None
        elif self.arguments[1] == 'text()':
            value = node.string
        if value is not None:
            return len(value) == self.value
        return False


_paths = {}
_steps = {}

def get_path(path):
    """Utility for eliminating repeated parsings of the same paths and steps.
    """
    if not _paths.has_key(path):
        p = Path(path, parse=False)
        steps = tokenize_path(path)
        for step in steps:
            if not _steps.has_key(step):
                _steps[step] = PathStep(step)
            p.steps.append(_steps[step])
        _paths[path] = p
    return _paths[path]

########NEW FILE########
__FILENAME__ = etree
"""
parser.http.bsouplxml.etree module (imdb.parser.http package).

This module adapts the beautifulsoup interface to lxml.etree module.

Copyright 2008 H. Turgut Uyar <uyar@tekir.org>
          2008 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import _bsoup as BeautifulSoup
from _bsoup import Tag as Element

import bsoupxpath

# Not directly used by IMDbPY, but do not remove: it's used by IMDbPYKit,
# for example.
def fromstring(xml_string):
    """Return a DOM representation of the string."""
    # We try to not use BeautifulSoup.BeautifulStoneSoup.XML_ENTITIES,
    # for convertEntities.
    return BeautifulSoup.BeautifulStoneSoup(xml_string,
                        convertEntities=None).findChild(True)


def tostring(element, encoding=None, pretty_print=False):
    """Return a string or unicode representation of an element."""
    if encoding is unicode:
        encoding = None
    # For BeautifulSoup 3.1
    #encArgs = {'prettyPrint': pretty_print}
    #if encoding is not None:
    #    encArgs['encoding'] = encoding
    #return element.encode(**encArgs)
    return element.__str__(encoding, pretty_print)

def setattribute(tag, name, value):
    tag[name] = value

def xpath(node, expr):
    """Apply an xpath expression to a node. Return a list of nodes."""
    #path = bsoupxpath.Path(expr)
    path = bsoupxpath.get_path(expr)
    return path.apply(node)


# XXX: monkey patching the beautifulsoup tag class
class _EverythingIsNestable(dict):
    """"Fake that every tag is nestable."""
    def get(self, key, *args, **kwds):
        return []

BeautifulSoup.BeautifulStoneSoup.NESTABLE_TAGS = _EverythingIsNestable()
BeautifulSoup.Tag.tag = property(fget=lambda self: self.name)
BeautifulSoup.Tag.attrib = property(fget=lambda self: self)
BeautifulSoup.Tag.text = property(fget=lambda self: self.string)
BeautifulSoup.Tag.set = setattribute
BeautifulSoup.Tag.getparent = lambda self: self.parent
BeautifulSoup.Tag.drop_tree = BeautifulSoup.Tag.extract
BeautifulSoup.Tag.xpath = xpath

# TODO: setting the text attribute for tags

########NEW FILE########
__FILENAME__ = html
"""
parser.http.bsouplxml.html module (imdb.parser.http package).

This module adapts the beautifulsoup interface to lxml.html module.

Copyright 2008 H. Turgut Uyar <uyar@tekir.org>
          2008 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import _bsoup as BeautifulSoup


def fromstring(html_string):
    """Return a DOM representation of the string."""
    return BeautifulSoup.BeautifulSoup(html_string,
        convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES
        ).findChild(True)

########NEW FILE########
__FILENAME__ = _bsoup
"""
imdb.parser.http._bsoup module (imdb.parser.http package).
This is the BeautifulSoup.py module, not modified; it's included here
so that it's not an external dependency.

Beautiful Soup
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
__FILENAME__ = characterParser
"""
parser.http.characterParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a character.
E.g., for "Jesse James" the referred pages would be:
    main details:   http://www.imdb.com/character/ch0000001/
    biography:      http://www.imdb.com/character/ch0000001/bio
    ...and so on...

Copyright 2007-2009 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
from utils import Attribute, Extractor, DOMParserBase, build_movie, \
                    analyze_imdbid
from personParser import DOMHTMLMaindetailsParser

from imdb.Movie import Movie

_personIDs = re.compile(r'/name/nm([0-9]{7})')
class DOMHTMLCharacterMaindetailsParser(DOMHTMLMaindetailsParser):
    """Parser for the "filmography" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bparser = DOMHTMLCharacterMaindetailsParser()
        result = bparser.parse(character_biography_html_string)
    """
    _containsObjects = True

    _film_attrs = [Attribute(key=None,
                      multi=True,
                      path={
                          'link': "./a[1]/@href",
                          'title': ".//text()",
                          'status': "./i/a//text()",
                          'roleID': "./a/@href"
                          },
                      postprocess=lambda x:
                          build_movie(x.get('title') or u'',
                              movieID=analyze_imdbid(x.get('link') or u''),
                              roleID=_personIDs.findall(x.get('roleID') or u''),
                              status=x.get('status') or None,
                              _parsingCharacter=True))]

    extractors = [
            Extractor(label='title',
                        path="//title",
                        attrs=Attribute(key='name',
                            path="./text()",
                            postprocess=lambda x: \
                                    x.replace(' (Character)', '').replace(
                                        '- Filmography by type', '').strip())),

            Extractor(label='headshot',
                        path="//a[@name='headshot']",
                        attrs=Attribute(key='headshot',
                            path="./img/@src")),

            Extractor(label='akas',
                        path="//div[h5='Alternate Names:']",
                        attrs=Attribute(key='akas',
                            path="./div//text()",
                            postprocess=lambda x: x.strip().split(' / '))),

            Extractor(label='filmography',
                        path="//div[@class='filmo'][not(h5)]/ol/li",
                        attrs=_film_attrs),

            Extractor(label='filmography sections',
                        group="//div[@class='filmo'][h5]",
                        group_key="./h5/a/text()",
                        group_key_normalize=lambda x: x.lower()[:-1],
                        path="./ol/li",
                        attrs=_film_attrs),
            ]

    preprocessors = [
            # Check that this doesn't cut "status"...
            (re.compile(r'<br>(\.\.\.|   ).+?</li>', re.I | re.M), '</li>')]


class DOMHTMLCharacterBioParser(DOMParserBase):
    """Parser for the "biography" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bparser = DOMHTMLCharacterBioParser()
        result = bparser.parse(character_biography_html_string)
    """
    _defGetRefs = True

    extractors = [
            Extractor(label='introduction',
                        path="//div[@id='_intro']",
                        attrs=Attribute(key='introduction',
                            path=".//text()",
                            postprocess=lambda x: x.strip())),

            Extractor(label='biography',
                        path="//span[@class='_biography']",
                        attrs=Attribute(key='biography',
                            multi=True,
                            path={
                                'info': "./preceding-sibling::h4[1]//text()",
                                'text': ".//text()"
                            },
                            postprocess=lambda x: u'%s: %s' % (
                                x.get('info').strip(),
                                x.get('text').replace('\n',
                                    ' ').replace('||', '\n\n').strip()))),
    ]

    preprocessors = [
        (re.compile('(<div id="swiki.2.3.1">)', re.I), r'\1<div id="_intro">'),
        (re.compile('(<a name="history">)\s*(<table .*?</table>)',
                    re.I | re.DOTALL),
         r'</div>\2\1</a>'),
        (re.compile('(<a name="[^"]+">)(<h4>)', re.I), r'</span>\1</a>\2'),
        (re.compile('(</h4>)</a>', re.I), r'\1<span class="_biography">'),
        (re.compile('<br/><br/>', re.I), r'||'),
        (re.compile('\|\|\n', re.I), r'</span>'),
        ]


class DOMHTMLCharacterQuotesParser(DOMParserBase):
    """Parser for the "quotes" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        qparser = DOMHTMLCharacterQuotesParser()
        result = qparser.parse(character_quotes_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='charquotes',
                    group="//h5",
                    group_key="./a/text()",
                    path="./following-sibling::div[1]",
                    attrs=Attribute(key=None,
                        path={'txt': ".//text()",
                              'movieID': ".//a[1]/@href"},
                        postprocess=lambda x: (analyze_imdbid(x['movieID']),
                                    x['txt'].strip().replace(':   ',
                                    ': ').replace(':  ', ': ').split('||'))))
    ]

    preprocessors = [
        (re.compile('(</h5>)', re.I), r'\1<div>'),
        (re.compile('\s*<br/><br/>\s*', re.I), r'||'),
        (re.compile('\|\|\s*(<hr/>)', re.I), r'</div>\1'),
        (re.compile('\s*<br/>\s*', re.I), r'::')
        ]

    def postprocess_data(self, data):
        if not data:
            return {}
        newData = {}
        for title in data:
            movieID, quotes = data[title]
            if movieID is None:
                movie = title
            else:
                movie = Movie(title=title, movieID=movieID,
                              accessSystem=self._as, modFunct=self._modFunct)
            newData[movie] = [quote.split('::') for quote in quotes]
        return {'quotes': newData}


from personParser import DOMHTMLSeriesParser

_OBJECTS = {
    'character_main_parser': ((DOMHTMLCharacterMaindetailsParser,),
                                {'kind': 'character'}),
    'character_series_parser': ((DOMHTMLSeriesParser,), None),
    'character_bio_parser': ((DOMHTMLCharacterBioParser,), None),
    'character_quotes_parser': ((DOMHTMLCharacterQuotesParser,), None)
}



########NEW FILE########
__FILENAME__ = companyParser
"""
parser.http.companyParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a company.
E.g., for "Columbia Pictures [us]" the referred page would be:
    main details:   http://akas.imdb.com/company/co0071509/

Copyright 2008-2009 Davide Alberani <da@erlug.linux.it>
          2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
from utils import build_movie, Attribute, Extractor, DOMParserBase, \
                    analyze_imdbid

from imdb.utils import analyze_company_name


class DOMCompanyParser(DOMParserBase):
    """Parser for the main page of a given company.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        cparser = DOMCompanyParser()
        result = cparser.parse(company_html_string)
    """
    _containsObjects = True

    extractors = [
            Extractor(label='name',
                        path="//title",
                        attrs=Attribute(key='name',
                            path="./text()",
                        postprocess=lambda x: \
                                analyze_company_name(x, stripNotes=True))),

            Extractor(label='filmography',
                        group="//b/a[@name]",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../following-sibling::ol[1]/li",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./a[1]/@href",
                                'title': "./a[1]/text()",
                                'year': "./text()[1]"
                                },
                            postprocess=lambda x:
                                build_movie(u'%s %s' % \
                                (x.get('title'), x.get('year').strip()),
                                movieID=analyze_imdbid(x.get('link') or u''),
                                _parsingCompany=True))),
            ]

    preprocessors = [
        (re.compile('(<b><a name=)', re.I), r'</p>\1')
        ]

    def postprocess_data(self, data):
        for key in data.keys():
            new_key = key.replace('company', 'companies')
            new_key = new_key.replace('other', 'miscellaneous')
            new_key = new_key.replace('distributor', 'distributors')
            if new_key != key:
                data[new_key] = data[key]
                del data[key]
        return data


_OBJECTS = {
    'company_main_parser': ((DOMCompanyParser,), None)
}


########NEW FILE########
__FILENAME__ = movieParser
"""
parser.http.movieParser module (imdb package).

This module provides the classes (and the instances), used to parse the
IMDb pages on the akas.imdb.com server about a movie.
E.g., for Brian De Palma's "The Untouchables", the referred
pages would be:
    combined details:   http://akas.imdb.com/title/tt0094226/combined
    plot summary:       http://akas.imdb.com/title/tt0094226/plotsummary
    ...and so on...

Copyright 2004-2013 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
import urllib

from imdb import imdbURL_base
from imdb.Person import Person
from imdb.Movie import Movie
from imdb.Company import Company
from imdb.utils import analyze_title, split_company_name_notes, _Container
from utils import build_person, DOMParserBase, Attribute, Extractor, \
                    analyze_imdbid


# Dictionary used to convert some section's names.
_SECT_CONV = {
        'directed': 'director',
        'directed by': 'director',
        'directors': 'director',
        'editors': 'editor',
        'writing credits': 'writer',
        'writers': 'writer',
        'produced': 'producer',
        'cinematography': 'cinematographer',
        'film editing': 'editor',
        'casting': 'casting director',
        'costume design': 'costume designer',
        'makeup department': 'make up',
        'production management': 'production manager',
        'second unit director or assistant director': 'assistant director',
        'costume and wardrobe department': 'costume department',
        'sound department': 'sound crew',
        'stunts':   'stunt performer',
        'other crew': 'miscellaneous crew',
        'also known as': 'akas',
        'country':  'countries',
        'runtime':  'runtimes',
        'language': 'languages',
        'certification':    'certificates',
        'genre': 'genres',
        'created': 'creator',
        'creators': 'creator',
        'color': 'color info',
        'plot': 'plot outline',
        'seasons': 'number of seasons',
        'art directors': 'art direction',
        'assistant directors': 'assistant director',
        'set decorators': 'set decoration',
        'visual effects department': 'visual effects',
        'production managers': 'production manager',
        'miscellaneous': 'miscellaneous crew',
        'make up department': 'make up',
        'plot summary': 'plot outline',
        'cinematographers': 'cinematographer',
        'camera department': 'camera and electrical department',
        'costume designers': 'costume designer',
        'production designers': 'production design',
        'production managers': 'production manager',
        'music original': 'original music',
        'casting directors': 'casting director',
        'other companies': 'miscellaneous companies',
        'producers': 'producer',
        'special effects by': 'special effects department',
        'special effects': 'special effects companies'
        }


def _manageRoles(mo):
    """Perform some transformation on the html, so that roleIDs can
    be easily retrieved."""
    firstHalf = mo.group(1)
    secondHalf = mo.group(2)
    newRoles = []
    roles = secondHalf.split(' / ')
    for role in roles:
        role = role.strip()
        if not role:
            continue
        roleID = analyze_imdbid(role)
        if roleID is None:
            roleID = u'/'
        else:
            roleID += u'/'
        newRoles.append(u'<div class="_imdbpyrole" roleid="%s">%s</div>' % \
                (roleID, role.strip()))
    return firstHalf + u' / '.join(newRoles) + mo.group(3)


_reRolesMovie = re.compile(r'(<td class="char">)(.*?)(</td>)',
                            re.I | re.M | re.S)

def _replaceBR(mo):
    """Replaces <br> tags with '::' (useful for some akas)"""
    txt = mo.group(0)
    return txt.replace('<br>', '::')

_reAkas = re.compile(r'<h5>also known as:</h5>.*?</div>', re.I | re.M | re.S)

def makeSplitter(lstrip=None, sep='|', comments=True,
                origNotesSep=' (', newNotesSep='::(', strip=None):
    """Return a splitter function suitable for a given set of data."""
    def splitter(x):
        if not x: return x
        x = x.strip()
        if not x: return x
        if lstrip is not None:
            x = x.lstrip(lstrip).lstrip()
        lx = x.split(sep)
        lx[:] = filter(None, [j.strip() for j in lx])
        if comments:
            lx[:] = [j.replace(origNotesSep, newNotesSep, 1) for j in lx]
        if strip:
            lx[:] = [j.strip(strip) for j in lx]
        return lx
    return splitter


def _toInt(val, replace=()):
    """Return the value, converted to integer, or None; if present, 'replace'
    must be a list of tuples of values to replace."""
    for before, after in replace:
        val = val.replace(before, after)
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


class DOMHTMLMovieParser(DOMParserBase):
    """Parser for the "combined details" (and if instance.mdparse is
    True also for the "main details") page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        mparser = DOMHTMLMovieParser()
        result = mparser.parse(combined_details_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='title',
                            path="//h1",
                            attrs=Attribute(key='title',
                                        path=".//text()",
                                        postprocess=analyze_title)),

                Extractor(label='glossarysections',
                        group="//a[@class='glossary']",
                        group_key="./@name",
                        group_key_normalize=lambda x: x.replace('_', ' '),
                        path="../../../..//tr",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={'person': ".//text()",
                                    'link': "./td[1]/a[@href]/@href"},
                            postprocess=lambda x: \
                                    build_person(x.get('person') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                )),

                Extractor(label='cast',
                        path="//table[@class='cast']//tr",
                        attrs=Attribute(key="cast",
                            multi=True,
                            path={'person': ".//text()",
                                'link': "td[2]/a/@href",
                                'roleID': \
                                    "td[4]/div[@class='_imdbpyrole']/@roleid"},
                            postprocess=lambda x: \
                                    build_person(x.get('person') or u'',
                                    personID=analyze_imdbid(x.get('link')),
                                    roleID=(x.get('roleID') or u'').split('/'))
                                )),

                Extractor(label='genres',
                        path="//div[@class='info']//a[starts-with(@href," \
                                " '/Sections/Genres')]",
                        attrs=Attribute(key="genres",
                            multi=True,
                            path="./text()")),

                Extractor(label='h5sections',
                        path="//div[@class='info']/h5/..",
                        attrs=[
                            Attribute(key="plot summary",
                                path="./h5[starts-with(text(), " \
                                        "'Plot:')]/../div/text()",
                                postprocess=lambda x: \
                                        x.strip().rstrip('|').rstrip()),
                            Attribute(key="aspect ratio",
                                path="./h5[starts-with(text()," \
                                        " 'Aspect')]/../div/text()",
                                postprocess=lambda x: x.strip()),
                            Attribute(key="mpaa",
                                path="./h5/a[starts-with(text()," \
                                        " 'MPAA')]/../../div/text()",
                                postprocess=lambda x: x.strip()),
                            Attribute(key="countries",
                                path="./h5[starts-with(text(), " \
                            "'Countr')]/../div[@class='info-content']//text()",
                            postprocess=makeSplitter('|')),
                            Attribute(key="language",
                                path="./h5[starts-with(text(), " \
                                        "'Language')]/..//text()",
                                    postprocess=makeSplitter('Language:')),
                            Attribute(key='color info',
                                path="./h5[starts-with(text(), " \
                                        "'Color')]/..//text()",
                                postprocess=makeSplitter('Color:')),
                            Attribute(key='sound mix',
                                path="./h5[starts-with(text(), " \
                                        "'Sound Mix')]/..//text()",
                                postprocess=makeSplitter('Sound Mix:')),
                            # Collects akas not encosed in <i> tags.
                            Attribute(key='other akas',
                                path="./h5[starts-with(text(), " \
                                        "'Also Known As')]/../div//text()",
                                postprocess=makeSplitter(sep='::',
                                                origNotesSep='" - ',
                                                newNotesSep='::',
                                                strip='"')),
                            Attribute(key='runtimes',
                                path="./h5[starts-with(text(), " \
                                        "'Runtime')]/../div/text()",
                                postprocess=makeSplitter()),
                            Attribute(key='certificates',
                                path="./h5[starts-with(text(), " \
                                        "'Certificat')]/..//text()",
                                postprocess=makeSplitter('Certification:')),
                            Attribute(key='number of seasons',
                                path="./h5[starts-with(text(), " \
                                        "'Seasons')]/..//text()",
                                postprocess=lambda x: x.count('|') + 1),
                            Attribute(key='original air date',
                                path="./h5[starts-with(text(), " \
                                        "'Original Air Date')]/../div/text()"),
                            Attribute(key='tv series link',
                                path="./h5[starts-with(text(), " \
                                        "'TV Series')]/..//a/@href"),
                            Attribute(key='tv series title',
                                path="./h5[starts-with(text(), " \
                                        "'TV Series')]/..//a/text()")
                            ]),

                Extractor(label='language codes',
                            path="//h5[starts-with(text(), 'Language')]/..//a[starts-with(@href, '/language/')]",
                            attrs=Attribute(key='language codes', multi=True,
                                    path="./@href",
                                    postprocess=lambda x: x.split('/')[2].strip()
                                    )),

                Extractor(label='country codes',
                            path="//h5[starts-with(text(), 'Country')]/..//a[starts-with(@href, '/country/')]",
                            attrs=Attribute(key='country codes', multi=True,
                                    path="./@href",
                                    postprocess=lambda x: x.split('/')[2].strip()
                                    )),

                Extractor(label='creator',
                            path="//h5[starts-with(text(), 'Creator')]/..//a",
                            attrs=Attribute(key='creator', multi=True,
                                    path={'name': "./text()",
                                        'link': "./@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='thin writer',
                            path="//h5[starts-with(text(), 'Writer')]/..//a",
                            attrs=Attribute(key='thin writer', multi=True,
                                    path={'name': "./text()",
                                        'link': "./@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='thin director',
                            path="//h5[starts-with(text(), 'Director')]/..//a",
                            attrs=Attribute(key='thin director', multi=True,
                                    path={'name': "./text()",
                                        'link': "@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='top 250/bottom 100',
                            path="//div[@class='starbar-special']/" \
                                    "a[starts-with(@href, '/chart/')]",
                            attrs=Attribute(key='top/bottom rank',
                                            path="./text()")),

                Extractor(label='series years',
                            path="//div[@id='tn15title']//span" \
                                "[starts-with(text(), 'TV series')]",
                            attrs=Attribute(key='series years',
                                    path="./text()",
                                    postprocess=lambda x: \
                                            x.replace('TV series','').strip())),

                Extractor(label='number of episodes',
                            path="//a[@title='Full Episode List']",
                            attrs=Attribute(key='number of episodes',
                                    path="./text()",
                                    postprocess=lambda x: \
                                            _toInt(x, [(' Episodes', '')]))),

                Extractor(label='akas',
                        path="//i[@class='transl']",
                        attrs=Attribute(key='akas', multi=True, path='text()',
                                postprocess=lambda x:
                                x.replace('  ', ' ').rstrip('-').replace('" - ',
                                    '"::', 1).strip('"').replace('  ', ' '))),

                Extractor(label='production notes/status',
                        path="//h5[starts-with(text(), 'Status:')]/..//div[@class='info-content']",
                        attrs=Attribute(key='production status',
                                path=".//text()",
                                postprocess=lambda x: x.strip().split('|')[0].strip().lower())),

                Extractor(label='production notes/status updated',
                        path="//h5[starts-with(text(), 'Status Updated:')]/..//div[@class='info-content']",
                        attrs=Attribute(key='production status updated',
                                path=".//text()",
                                postprocess=lambda x: x.strip())),

                Extractor(label='production notes/comments',
                        path="//h5[starts-with(text(), 'Comments:')]/..//div[@class='info-content']",
                        attrs=Attribute(key='production comments',
                                path=".//text()",
                                postprocess=lambda x: x.strip())),

                Extractor(label='production notes/note',
                        path="//h5[starts-with(text(), 'Note:')]/..//div[@class='info-content']",
                        attrs=Attribute(key='production note',
                                path=".//text()",
                                postprocess=lambda x: x.strip())),

                Extractor(label='blackcatheader',
                        group="//b[@class='blackcatheader']",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../ul/li",
                        attrs=Attribute(key=None,
                                multi=True,
                                path={'name': "./a//text()",
                                        'comp-link': "./a/@href",
                                        'notes': "./text()"},
                                postprocess=lambda x: \
                                        Company(name=x.get('name') or u'',
                                companyID=analyze_imdbid(x.get('comp-link')),
                                notes=(x.get('notes') or u'').strip())
                            )),

                Extractor(label='rating',
                        path="//div[@class='starbar-meta']/b",
                        attrs=Attribute(key='rating',
                                        path=".//text()")),

                Extractor(label='votes',
                        path="//div[@class='starbar-meta']/a[@href]",
                        attrs=Attribute(key='votes',
                                        path=".//text()")),

                Extractor(label='cover url',
                        path="//a[@name='poster']",
                        attrs=Attribute(key='cover url',
                                        path="./img/@src"))
                ]

    preprocessors = [
        (re.compile(r'(<b class="blackcatheader">.+?</b>)', re.I),
            r'</div><div>\1'),
        ('<small>Full cast and crew for<br>', ''),
        ('<td> </td>', '<td>...</td>'),
        ('<span class="tv-extra">TV mini-series</span>',
            '<span class="tv-extra">(mini)</span>'),
        (_reRolesMovie, _manageRoles),
        (_reAkas, _replaceBR)]

    def preprocess_dom(self, dom):
        # Handle series information.
        xpath = self.xpath(dom, "//b[text()='Series Crew']")
        if xpath:
            b = xpath[-1] # In doubt, take the last one.
            for a in self.xpath(b, "./following::h5/a[@class='glossary']"):
                name = a.get('name')
                if name:
                    a.set('name', 'series %s' % name)
        # Remove links to IMDbPro.
        for proLink in self.xpath(dom, "//span[@class='pro-link']"):
            proLink.drop_tree()
        # Remove some 'more' links (keep others, like the one around
        # the number of votes).
        for tn15more in self.xpath(dom,
                    "//a[@class='tn15more'][starts-with(@href, '/title/')]"):
            tn15more.drop_tree()
        return dom

    re_space = re.compile(r'\s+')
    re_airdate = re.compile(r'(.*)\s*\(season (\d+), episode (\d+)\)', re.I)
    def postprocess_data(self, data):
        # Convert section names.
        for sect in data.keys():
            if sect in _SECT_CONV:
                data[_SECT_CONV[sect]] = data[sect]
                del data[sect]
                sect = _SECT_CONV[sect]
        # Filter out fake values.
        for key in data:
            value = data[key]
            if isinstance(value, list) and value:
                if isinstance(value[0], Person):
                    data[key] = filter(lambda x: x.personID is not None, value)
                if isinstance(value[0], _Container):
                    for obj in data[key]:
                        obj.accessSystem = self._as
                        obj.modFunct = self._modFunct
        if 'akas' in data or 'other akas' in data:
            akas = data.get('akas') or []
            other_akas = data.get('other akas') or []
            akas += other_akas
            nakas = []
            for aka in akas:
                aka = aka.strip()
                if aka.endswith('" -'):
                    aka = aka[:-3].rstrip()
                nakas.append(aka)
            if 'akas' in data:
                del data['akas']
            if 'other akas' in data:
                del data['other akas']
            if nakas:
                data['akas'] = nakas
        if 'runtimes' in data:
            data['runtimes'] = [x.replace(' min', u'')
                                for x in data['runtimes']]
        if 'original air date' in data:
            oid = self.re_space.sub(' ', data['original air date']).strip()
            data['original air date'] = oid
            aid = self.re_airdate.findall(oid)
            if aid and len(aid[0]) == 3:
                date, season, episode = aid[0]
                date = date.strip()
                try: season = int(season)
                except: pass
                try: episode = int(episode)
                except: pass
                if date and date != '????':
                    data['original air date'] = date
                else:
                    del data['original air date']
                # Handle also "episode 0".
                if season or type(season) is type(0):
                    data['season'] = season
                if episode or type(season) is type(0):
                    data['episode'] = episode
        for k in ('writer', 'director'):
            t_k = 'thin %s' % k
            if t_k not in data:
                continue
            if k not in data:
                data[k] = data[t_k]
            del data[t_k]
        if 'top/bottom rank' in data:
            tbVal = data['top/bottom rank'].lower()
            if tbVal.startswith('top'):
                tbKey = 'top 250 rank'
                tbVal = _toInt(tbVal, [('top 250: #', '')])
            else:
                tbKey = 'bottom 100 rank'
                tbVal = _toInt(tbVal, [('bottom 100: #', '')])
            if tbVal:
                data[tbKey] = tbVal
            del data['top/bottom rank']
        if 'year' in data and data['year'] == '????':
            del data['year']
        if 'tv series link' in data:
            if 'tv series title' in data:
                data['episode of'] = Movie(title=data['tv series title'],
                                            movieID=analyze_imdbid(
                                                    data['tv series link']),
                                            accessSystem=self._as,
                                            modFunct=self._modFunct)
                del data['tv series title']
            del data['tv series link']
        if 'rating' in data:
            try:
                data['rating'] = float(data['rating'].replace('/10', ''))
            except (TypeError, ValueError):
                pass
        if 'votes' in data:
            try:
                votes = data['votes'].replace(',', '').replace('votes', '')
                data['votes'] = int(votes)
            except (TypeError, ValueError):
                pass
        return data


def _process_plotsummary(x):
    """Process a plot (contributed by Rdian06)."""
    xauthor = x.get('author')
    xplot = x.get('plot', u'').strip()
    if xauthor:
        xplot += u'::%s' % xauthor
    return xplot

class DOMHTMLPlotParser(DOMParserBase):
    """Parser for the "plot summary" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a 'plot' key, containing a list
    of string with the structure: 'summary::summary_author <author@email>'.

    Example:
        pparser = HTMLPlotParser()
        result = pparser.parse(plot_summary_html_string)
    """
    _defGetRefs = True

    # Notice that recently IMDb started to put the email of the
    # author only in the link, that we're not collecting, here.
    extractors = [Extractor(label='plot',
                            path="//ul[@class='zebraList']//p",
                            attrs=Attribute(key='plot',
                                            multi=True,
                                            path={'plot': './text()[1]',
                                                  'author': './span/em/a/text()'},
                                            postprocess=_process_plotsummary))]


def _process_award(x):
    award = {}
    _award = x.get('award')
    if _award is not None:
        _award = _award.strip()
    award['award'] = _award
    if not award['award']:
        return {}
    award['year'] = x.get('year').strip()
    if award['year'] and award['year'].isdigit():
        award['year'] = int(award['year'])
    award['result'] = x.get('result').strip()
    category = x.get('category').strip()
    if category:
        award['category'] = category
    received_with = x.get('with')
    if received_with is not None:
        award['with'] = received_with.strip()
    notes = x.get('notes')
    if notes is not None:
        notes = notes.strip()
        if notes:
            award['notes'] = notes
    award['anchor'] = x.get('anchor')
    return award



class DOMHTMLAwardsParser(DOMParserBase):
    """Parser for the "awards" page of a given person or movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        awparser = HTMLAwardsParser()
        result = awparser.parse(awards_html_string)
    """
    subject = 'title'
    _containsObjects = True

    extractors = [
        Extractor(label='awards',
            group="//table//big",
            group_key="./a",
            path="./ancestor::tr[1]/following-sibling::tr/" \
                    "td[last()][not(@colspan)]",
            attrs=Attribute(key=None,
                multi=True,
                path={
                    'year': "../td[1]/a/text()",
                    'result': "../td[2]/b/text()",
                    'award': "../td[3]/text()",
                    'category': "./text()[1]",
                    # FIXME: takes only the first co-recipient
                    'with': "./small[starts-with(text()," \
                            " 'Shared with:')]/following-sibling::a[1]/text()",
                    'notes': "./small[last()]//text()",
                    'anchor': ".//text()"
                    },
                postprocess=_process_award
                )),
        Extractor(label='recipients',
            group="//table//big",
            group_key="./a",
            path="./ancestor::tr[1]/following-sibling::tr/" \
                    "td[last()]/small[1]/preceding-sibling::a",
            attrs=Attribute(key=None,
                multi=True,
                path={
                    'name': "./text()",
                    'link': "./@href",
                    'anchor': "..//text()"
                    }
                ))
    ]

    preprocessors = [
        (re.compile('(<tr><td[^>]*>.*?</td></tr>\n\n</table>)', re.I),
         r'\1</table>'),
        (re.compile('(<tr><td[^>]*>\n\n<big>.*?</big></td></tr>)', re.I),
         r'</table><table class="_imdbpy">\1'),
        (re.compile('(<table[^>]*>\n\n)</table>(<table)', re.I), r'\1\2'),
        (re.compile('(<small>.*?)<br>(.*?</small)', re.I), r'\1 \2'),
        (re.compile('(</tr>\n\n)(<td)', re.I), r'\1<tr>\2')
        ]

    def preprocess_dom(self, dom):
        """Repeat td elements according to their rowspan attributes
        in subsequent tr elements.
        """
        cols = self.xpath(dom, "//td[@rowspan]")
        for col in cols:
            span = int(col.get('rowspan'))
            del col.attrib['rowspan']
            position = len(self.xpath(col, "./preceding-sibling::td"))
            row = col.getparent()
            for tr in self.xpath(row, "./following-sibling::tr")[:span-1]:
                # if not cloned, child will be moved to new parent
                clone = self.clone(col)
                # XXX: beware that here we don't use an "adapted" function,
                #      because both BeautifulSoup and lxml uses the same
                #      "insert" method.
                tr.insert(position, clone)
        return dom

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        nd = []
        for key in data.keys():
            dom = self.get_dom(key)
            assigner = self.xpath(dom, "//a/text()")[0]
            for entry in data[key]:
                if not entry.has_key('name'):
                    if not entry:
                        continue
                    # this is an award, not a recipient
                    entry['assigner'] = assigner.strip()
                    # find the recipients
                    matches = [p for p in data[key]
                               if p.has_key('name') and (entry['anchor'] ==
                                   p['anchor'])]
                    if self.subject == 'title':
                        recipients = [Person(name=recipient['name'],
                                    personID=analyze_imdbid(recipient['link']))
                                    for recipient in matches]
                        entry['to'] = recipients
                    elif self.subject == 'name':
                        recipients = [Movie(title=recipient['name'],
                                    movieID=analyze_imdbid(recipient['link']))
                                    for recipient in matches]
                        entry['for'] = recipients
                    nd.append(entry)
                del entry['anchor']
        return {'awards': nd}


class DOMHTMLTaglinesParser(DOMParserBase):
    """Parser for the "taglines" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLTaglinesParser()
        result = tparser.parse(taglines_html_string)
    """
    extractors = [Extractor(label='taglines',
                            path='//*[contains(concat(" ", normalize-space(@class), " "), " soda ")]',
                            attrs=Attribute(key='taglines',
                                            multi=True,
                                            path="./text()"))]

    def postprocess_data(self, data):
        if 'taglines' in data:
            data['taglines'] = [tagline.strip() for tagline in data['taglines']]
        return data


class DOMHTMLKeywordsParser(DOMParserBase):
    """Parser for the "keywords" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        kwparser = DOMHTMLKeywordsParser()
        result = kwparser.parse(keywords_html_string)
    """
    extractors = [Extractor(label='keywords',
                            path="//a[starts-with(@href, '/keyword/')]",
                            attrs=Attribute(key='keywords',
                                            path="./text()", multi=True,
                                            postprocess=lambda x: \
                                                x.lower().replace(' ', '-')))]


class DOMHTMLAlternateVersionsParser(DOMParserBase):
    """Parser for the "alternate versions" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        avparser = HTMLAlternateVersionsParser()
        result = avparser.parse(alternateversions_html_string)
    """
    _defGetRefs = True
    extractors = [Extractor(label='alternate versions',
                            path="//ul[@class='trivia']/li",
                            attrs=Attribute(key='alternate versions',
                                            multi=True,
                                            path=".//text()",
                                            postprocess=lambda x: x.strip()))]


class DOMHTMLTriviaParser(DOMParserBase):
    """Parser for the "trivia" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        avparser = HTMLAlternateVersionsParser()
        result = avparser.parse(alternateversions_html_string)
    """
    _defGetRefs = True
    extractors = [Extractor(label='alternate versions',
                            path="//div[@class='sodatext']",
                            attrs=Attribute(key='trivia',
                                            multi=True,
                                            path=".//text()",
                                            postprocess=lambda x: x.strip()))]

    def preprocess_dom(self, dom):
        # Remove "link this quote" links.
        for qLink in self.xpath(dom, "//span[@class='linksoda']"):
            qLink.drop_tree()
        return dom



class DOMHTMLSoundtrackParser(DOMHTMLAlternateVersionsParser):
    kind = 'soundtrack'

    preprocessors = [
        ('<br>', '\n')
        ]

    def postprocess_data(self, data):
        if 'alternate versions' in data:
            nd = []
            for x in data['alternate versions']:
                ds = x.split('\n')
                title = ds[0]
                if title[0] == '"' and title[-1] == '"':
                    title = title[1:-1]
                nds = []
                newData = {}
                for l in ds[1:]:
                    if ' with ' in l or ' by ' in l or ' from ' in l \
                            or ' of ' in l or l.startswith('From '):
                        nds.append(l)
                    else:
                        if nds:
                            nds[-1] += l
                        else:
                            nds.append(l)
                newData[title] = {}
                for l in nds:
                    skip = False
                    for sep in ('From ',):
                        if l.startswith(sep):
                            fdix = len(sep)
                            kind = l[:fdix].rstrip().lower()
                            info = l[fdix:].lstrip()
                            newData[title][kind] = info
                            skip = True
                    if not skip:
                        for sep in ' with ', ' by ', ' from ', ' of ':
                            fdix = l.find(sep)
                            if fdix != -1:
                                fdix = fdix+len(sep)
                                kind = l[:fdix].rstrip().lower()
                                info = l[fdix:].lstrip()
                                newData[title][kind] = info
                                break
                nd.append(newData)
            data['soundtrack'] = nd
        return data


class DOMHTMLCrazyCreditsParser(DOMParserBase):
    """Parser for the "crazy credits" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        ccparser = DOMHTMLCrazyCreditsParser()
        result = ccparser.parse(crazycredits_html_string)
    """
    _defGetRefs = True

    extractors = [Extractor(label='crazy credits', path="//ul/li/tt",
                            attrs=Attribute(key='crazy credits', multi=True,
                                path=".//text()",
                                postprocess=lambda x: \
                                    x.replace('\n', ' ').replace('  ', ' ')))]


def _process_goof(x):
    if x['spoiler_category']:
        return x['spoiler_category'].strip() + ': SPOILER: ' + x['text'].strip()
    else:
        return x['category'].strip() + ': ' + x['text'].strip()


class DOMHTMLGoofsParser(DOMParserBase):
    """Parser for the "goofs" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        gparser = DOMHTMLGoofsParser()
        result = gparser.parse(goofs_html_string)
    """
    _defGetRefs = True

    extractors = [Extractor(label='goofs', path="//div[@class='soda odd']",
                    attrs=Attribute(key='goofs', multi=True,
                        path={
                              'text':"./text()",
                              'category':'./preceding-sibling::h4[1]/text()',
                              'spoiler_category': './h4/text()'
                        },
                        postprocess=_process_goof))]


class DOMHTMLQuotesParser(DOMParserBase):
    """Parser for the "memorable quotes" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        qparser = DOMHTMLQuotesParser()
        result = qparser.parse(quotes_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='quotes_odd',
            path="//div[@class='quote soda odd']",
            attrs=Attribute(key='quotes_odd',
                multi=True,
                path=".//text()",
                postprocess=lambda x: x.strip().replace(' \n',
                            '::').replace('::\n', '::').replace('\n', ' '))),
        Extractor(label='quotes_even',
            path="//div[@class='quote soda even']",
            attrs=Attribute(key='quotes_even',
                multi=True,
                path=".//text()",
                postprocess=lambda x: x.strip().replace(' \n',
                            '::').replace('::\n', '::').replace('\n', ' ')))
        ]

    preprocessors = [
        (re.compile('<a href="#" class="hidesoda hidden">Hide options</a><br>', re.I), '')
    ]

    def preprocess_dom(self, dom):
        # Remove "link this quote" links.
        for qLink in self.xpath(dom, "//span[@class='linksoda']"):
            qLink.drop_tree()
        for qLink in self.xpath(dom, "//div[@class='sharesoda_pre']"):
            qLink.drop_tree()
        return dom

    def postprocess_data(self, data):
        quotes = data.get('quotes_odd', []) + data.get('quotes_even', [])
        if not quotes:
            return {}
        quotes = [q.split('::') for q in quotes]
        return {'quotes': quotes}


class DOMHTMLReleaseinfoParser(DOMParserBase):
    """Parser for the "release dates" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rdparser = DOMHTMLReleaseinfoParser()
        result = rdparser.parse(releaseinfo_html_string)
    """
    extractors = [Extractor(label='release dates',
                    path="//table[@id='release_dates']//tr",
                    attrs=Attribute(key='release dates', multi=True,
                        path={'country': ".//td[1]//text()",
                            'date': ".//td[2]//text()",
                            'notes': ".//td[3]//text()"})),
                Extractor(label='akas',
                    path="//table[@id='akas']//tr",
                    attrs=Attribute(key='akas', multi=True,
                        path={'title': "./td[1]/text()",
                            'countries': "./td[2]/text()"}))]

    preprocessors = [
        (re.compile('(<h5><a name="?akas"?.*</table>)', re.I | re.M | re.S),
            r'<div class="_imdbpy_akas">\1</div>')]

    def postprocess_data(self, data):
        if not ('release dates' in data or 'akas' in data): return data
        releases = data.get('release dates') or []
        rl = []
        for i in releases:
            country = i.get('country')
            date = i.get('date')
            if not (country and date): continue
            country = country.strip()
            date = date.strip()
            if not (country and date): continue
            notes = i['notes']
            info = u'%s::%s' % (country, date)
            if notes:
                info += notes
            rl.append(info)
        if releases:
            del data['release dates']
        if rl:
            data['release dates'] = rl
        akas = data.get('akas') or []
        nakas = []
        for aka in akas:
            title = (aka.get('title') or '').strip()
            if not title:
                continue
            countries = (aka.get('countries') or '').split(',')
            if not countries:
                nakas.append(title)
            else:
                for country in countries:
                    nakas.append('%s::%s' % (title, country.strip()))
        if akas:
            del data['akas']
        if nakas:
            data['akas from release info'] = nakas
        return data


class DOMHTMLRatingsParser(DOMParserBase):
    """Parser for the "user ratings" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rparser = DOMHTMLRatingsParser()
        result = rparser.parse(userratings_html_string)
    """
    re_means = re.compile('mean\s*=\s*([0-9]\.[0-9])\.\s*median\s*=\s*([0-9])',
                          re.I)
    extractors = [
        Extractor(label='number of votes',
            path="//td[b='Percentage']/../../tr",
            attrs=[Attribute(key='votes',
                            multi=True,
                            path={
                                'votes': "td[1]//text()",
                                'ordinal': "td[3]//text()"
                                })]),
        Extractor(label='mean and median',
            path="//p[starts-with(text(), 'Arithmetic mean')]",
            attrs=Attribute(key='mean and median',
                            path="text()")),
        Extractor(label='rating',
            path="//a[starts-with(@href, '/search/title?user_rating=')]",
            attrs=Attribute(key='rating',
                            path="text()")),
        Extractor(label='demographic voters',
            path="//td[b='Average']/../../tr",
            attrs=Attribute(key='demographic voters',
                            multi=True,
                            path={
                                'voters': "td[1]//text()",
                                'votes': "td[2]//text()",
                                'average': "td[3]//text()"
                                })),
        Extractor(label='top 250',
            path="//a[text()='top 250']",
            attrs=Attribute(key='top 250',
                            path="./preceding-sibling::text()[1]"))
        ]

    def postprocess_data(self, data):
        nd = {}
        votes = data.get('votes', [])
        if votes:
            nd['number of votes'] = {}
            for i in xrange(1, 11):
                _ordinal = int(votes[i]['ordinal'])
                _strvts = votes[i]['votes'] or '0'
                nd['number of votes'][_ordinal] = \
                        int(_strvts.replace(',', ''))
        mean = data.get('mean and median', '')
        if mean:
            means = self.re_means.findall(mean)
            if means and len(means[0]) == 2:
                am, med = means[0]
                try: am = float(am)
                except (ValueError, OverflowError): pass
                if type(am) is type(1.0):
                    nd['arithmetic mean'] = am
                try: med = int(med)
                except (ValueError, OverflowError): pass
                if type(med) is type(0):
                    nd['median'] = med
        if 'rating' in data:
            nd['rating'] = float(data['rating'])
        dem_voters = data.get('demographic voters')
        if dem_voters:
            nd['demographic'] = {}
            for i in xrange(1, len(dem_voters)):
                if (dem_voters[i]['votes'] is not None) \
                   and (dem_voters[i]['votes'].strip()):
                    nd['demographic'][dem_voters[i]['voters'].strip().lower()] \
                                = (int(dem_voters[i]['votes'].replace(',', '')),
                            float(dem_voters[i]['average']))
        if 'imdb users' in nd.get('demographic', {}):
            nd['votes'] = nd['demographic']['imdb users'][0]
            nd['demographic']['all votes'] = nd['demographic']['imdb users']
            del nd['demographic']['imdb users']
        top250 = data.get('top 250')
        if top250:
            sd = top250[9:]
            i = sd.find(' ')
            if i != -1:
                sd = sd[:i]
                try: sd = int(sd)
                except (ValueError, OverflowError): pass
                if type(sd) is type(0):
                    nd['top 250 rank'] = sd
        return nd


class DOMHTMLEpisodesRatings(DOMParserBase):
    """Parser for the "episode ratings ... by date" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        erparser = DOMHTMLEpisodesRatings()
        result = erparser.parse(eprating_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='title', path="//title",
                            attrs=Attribute(key='title', path="./text()")),
                Extractor(label='ep ratings',
                        path="//th/../..//tr",
                        attrs=Attribute(key='episodes', multi=True,
                                path={'nr': ".//td[1]/text()",
                                        'ep title': ".//td[2]//text()",
                                        'movieID': ".//td[2]/a/@href",
                                        'rating': ".//td[3]/text()",
                                        'votes': ".//td[4]/text()"}))]

    def postprocess_data(self, data):
        if 'title' not in data or 'episodes' not in data: return {}
        nd = []
        title = data['title']
        for i in data['episodes']:
            ept = i['ep title']
            movieID = analyze_imdbid(i['movieID'])
            votes = i['votes']
            rating = i['rating']
            if not (ept and movieID and votes and rating): continue
            try:
                votes = int(votes.replace(',', '').replace('.', ''))
            except:
                pass
            try:
                rating = float(rating)
            except:
                pass
            ept = ept.strip()
            ept = u'%s {%s' % (title, ept)
            nr = i['nr']
            if nr:
                ept += u' (#%s)' % nr.strip()
            ept += '}'
            if movieID is not None:
                movieID = str(movieID)
            m = Movie(title=ept, movieID=movieID, accessSystem=self._as,
                        modFunct=self._modFunct)
            epofdict = m.get('episode of')
            if epofdict is not None:
                m['episode of'] = Movie(data=epofdict, accessSystem=self._as,
                        modFunct=self._modFunct)
            nd.append({'episode': m, 'votes': votes, 'rating': rating})
        return {'episodes rating': nd}


def _normalize_href(href):
    if (href is not None) and (not href.lower().startswith('http://')):
        if href.startswith('/'): href = href[1:]
        # TODO: imdbURL_base may be set by the user!
        href = '%s%s' % (imdbURL_base, href)
    return href

class DOMHTMLCriticReviewsParser(DOMParserBase):
    """Parser for the "critic reviews" pages of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        osparser = DOMHTMLCriticReviewsParser()
        result = osparser.parse(officialsites_html_string)
    """
    kind = 'critic reviews'

    extractors = [
        Extractor(label='metascore',
                path="//div[@class='metascore_wrap']/div/span",
                attrs=Attribute(key='metascore',
                                path=".//text()")),
        Extractor(label='metacritic url',
                path="//div[@class='article']/div[@class='see-more']/a",
                attrs=Attribute(key='metacritic url',
                                path="./@href")) ]
    
class DOMHTMLOfficialsitesParser(DOMParserBase):
    """Parser for the "official sites", "external reviews", "newsgroup
    reviews", "miscellaneous links", "sound clips", "video clips" and
    "photographs" pages of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        osparser = DOMHTMLOfficialsitesParser()
        result = osparser.parse(officialsites_html_string)
    """
    kind = 'official sites'

    extractors = [
        Extractor(label='site',
            path="//ol/li/a",
            attrs=Attribute(key='self.kind',
                multi=True,
                path={
                    'link': "./@href",
                    'info': "./text()"
                },
                postprocess=lambda x: (x.get('info').strip(),
                            urllib.unquote(_normalize_href(x.get('link'))))))
        ]


class DOMHTMLConnectionParser(DOMParserBase):
    """Parser for the "connections" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        connparser = DOMHTMLConnectionParser()
        result = connparser.parse(connections_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='connection',
                    group="//div[@class='_imdbpy']",
                    group_key="./h5/text()",
                    group_key_normalize=lambda x: x.lower(),
                    path="./a",
                    attrs=Attribute(key=None,
                                    path={'title': "./text()",
                                            'movieID': "./@href"},
                                    multi=True))]

    preprocessors = [
        ('<h5>', '</div><div class="_imdbpy"><h5>'),
        # To get the movie's year.
        ('</a> (', ' ('),
        ('\n<br/>', '</a>'),
        ('<br/> - ', '::')
        ]

    def postprocess_data(self, data):
        for key in data.keys():
            nl = []
            for v in data[key]:
                title = v['title']
                ts = title.split('::', 1)
                title = ts[0].strip()
                notes = u''
                if len(ts) == 2:
                    notes = ts[1].strip()
                m = Movie(title=title,
                            movieID=analyze_imdbid(v['movieID']),
                            accessSystem=self._as, notes=notes,
                            modFunct=self._modFunct)
                nl.append(m)
            data[key] = nl
        if not data: return {}
        return {'connections': data}


class DOMHTMLLocationsParser(DOMParserBase):
    """Parser for the "locations" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        lparser = DOMHTMLLocationsParser()
        result = lparser.parse(locations_html_string)
    """
    extractors = [Extractor(label='locations', path="//dt",
                    attrs=Attribute(key='locations', multi=True,
                                path={'place': ".//text()",
                                        'note': "./following-sibling::dd[1]" \
                                                "//text()"},
                                postprocess=lambda x: (u'%s::%s' % (
                                    x['place'].strip(),
                                    (x['note'] or u'').strip())).strip(':')))]


class DOMHTMLTechParser(DOMParserBase):
    """Parser for the "technical", "business", "literature",
    "publicity" (for people) and "contacts (for people) pages of
    a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = HTMLTechParser()
        result = tparser.parse(technical_html_string)
    """
    kind = 'tech'

    extractors = [Extractor(label='tech',
                        group="//h5",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="./following-sibling::div[1]",
                        attrs=Attribute(key=None,
                                    path=".//text()",
                                    postprocess=lambda x: [t.strip()
                                        for t in x.split('\n') if t.strip()]))]

    preprocessors = [
        (re.compile('(<h5>.*?</h5>)', re.I), r'</div>\1<div class="_imdbpy">'),
        (re.compile('((<br/>|</p>|</table>))\n?<br/>(?!<a)', re.I),
            r'\1</div>'),
        # the ones below are for the publicity parser
        (re.compile('<p>(.*?)</p>', re.I), r'\1<br/>'),
        (re.compile('(</td><td valign="top">)', re.I), r'\1::'),
        (re.compile('(</tr><tr>)', re.I), r'\n\1'),
        # this is for splitting individual entries
        (re.compile('<br/>', re.I), r'\n'),
        ]

    def postprocess_data(self, data):
        for key in data:
            data[key] = filter(None, data[key])
        if self.kind in ('literature', 'business', 'contacts') and data:
            if 'screenplay/teleplay' in data:
                data['screenplay-teleplay'] = data['screenplay/teleplay']
                del data['screenplay/teleplay']
            data = {self.kind: data}
        else:
            if self.kind == 'publicity':
                if 'biography (print)' in data:
                    data['biography-print'] = data['biography (print)']
                    del data['biography (print)']
            # Tech info.
            for key in data.keys():
                if key.startswith('film negative format'):
                    data['film negative format'] = data[key]
                    del data[key]
                elif key.startswith('film length'):
                    data['film length'] = data[key]
                    del data[key]
        return data


class DOMHTMLRecParser(DOMParserBase):
    """Parser for the "recommendations" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rparser = HTMLRecParser()
        result = rparser.parse(recommendations_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='recommendations',
                    path="//td[@valign='middle'][1]",
                    attrs=Attribute(key='../../tr/td[1]//text()',
                            multi=True,
                            path={'title': ".//text()",
                                    'movieID': ".//a/@href"}))]
    def postprocess_data(self, data):
        for key in data.keys():
            n_key = key
            n_keyl = n_key.lower()
            if n_keyl == 'suggested by the database':
                n_key = 'database'
            elif n_keyl == 'imdb users recommend':
                n_key = 'users'
            data[n_key] = [Movie(title=x['title'],
                        movieID=analyze_imdbid(x['movieID']),
                        accessSystem=self._as, modFunct=self._modFunct)
                        for x in data[key]]
            del data[key]
        if data: return {'recommendations': data}
        return data


class DOMHTMLNewsParser(DOMParserBase):
    """Parser for the "news" page of a given movie or person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        nwparser = DOMHTMLNewsParser()
        result = nwparser.parse(news_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='news',
            path="//h2",
            attrs=Attribute(key='news',
                multi=True,
                path={
                    'title': "./text()",
                    'fromdate': "../following-sibling::p[1]/small//text()",
                    # FIXME: sometimes (see The Matrix (1999)) <p> is found
                    #        inside news text.
                    'body': "../following-sibling::p[2]//text()",
                    'link': "../..//a[text()='Permalink']/@href",
                    'fulllink': "../..//a[starts-with(text(), " \
                            "'See full article at')]/@href"
                    },
                postprocess=lambda x: {
                    'title': x.get('title').strip(),
                    'date': x.get('fromdate').split('|')[0].strip(),
                    'from': x.get('fromdate').split('|')[1].replace('From ',
                            '').strip(),
                    'body': (x.get('body') or u'').strip(),
                    'link': _normalize_href(x.get('link')),
                    'full article link': _normalize_href(x.get('fulllink'))
                }))
        ]

    preprocessors = [
        (re.compile('(<a name=[^>]+><h2>)', re.I), r'<div class="_imdbpy">\1'),
        (re.compile('(<hr/>)', re.I), r'</div>\1'),
        (re.compile('<p></p>', re.I), r'')
        ]

    def postprocess_data(self, data):
        if not data.has_key('news'):
            return {}
        for news in data['news']:
            if news.has_key('full article link'):
                if news['full article link'] is None:
                    del news['full article link']
        return data


def _parse_review(x):
    result = {}
    title = x.get('title').strip()
    if title[-1] == ':': title = title[:-1]
    result['title'] = title
    result['link'] = _normalize_href(x.get('link'))
    kind =  x.get('kind').strip()
    if kind[-1] == ':': kind = kind[:-1]
    result['review kind'] = kind
    text = x.get('review').replace('\n\n', '||').replace('\n', ' ').split('||')
    review = '\n'.join(text)
    if x.get('author') is not None:
        author = x.get('author').strip()
        review = review.split(author)[0].strip()
        result['review author'] = author[2:]
    if x.get('item') is not None:
        item = x.get('item').strip()
        review = review[len(item):].strip()
        review = "%s: %s" % (item, review)
    result['review'] = review
    return result


class DOMHTMLSeasonEpisodesParser(DOMParserBase):
    """Parser for the "episode list" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = DOMHTMLSeasonEpisodesParser()
        result = sparser.parse(episodes_html_string)
    """
    extractors = [
            Extractor(label='series link',
                path="//div[@class='parent']",
                attrs=[Attribute(key='series link',
                            path=".//a/@href")]
            ),

            Extractor(label='series title',
                path="//head/meta[@property='og:title']",
                attrs=[Attribute(key='series title',
                            path="./@content")]
            ),

            Extractor(label='seasons list',
                path="//select[@id='bySeason']//option",
                attrs=[Attribute(key='_seasons',
                            multi=True,
                            path="./@value")]),

            Extractor(label='selected season',
                path="//select[@id='bySeason']//option[@selected]",
                attrs=[Attribute(key='_current_season',
                            path='./@value')]),

            Extractor(label='episodes',
                path=".",
                group="//div[@class='info']",
                group_key=".//meta/@content",
                group_key_normalize=lambda x: 'episode %s' % x,
                attrs=[Attribute(key=None,
                            multi=True,
                            path={
                                "link": ".//strong//a[@href][1]/@href",
                                "original air date": ".//div[@class='airdate']/text()",
                                "title": ".//strong//text()",
                                "plot": ".//div[@class='item_description']//text()"
                            }
                        )]
                )
            ]

    def postprocess_data(self, data):
        series_id = analyze_imdbid(data.get('series link'))
        series_title = data.get('series title', '').strip()
        selected_season = data.get('_current_season',
                                    'unknown season').strip()
        if not (series_id and series_title):
            return {}
        series = Movie(title=series_title, movieID=str(series_id),
                        accessSystem=self._as, modFunct=self._modFunct)
        if series.get('kind') == 'movie':
            series['kind'] = u'tv series'
        try: selected_season = int(selected_season)
        except: pass
        nd = {selected_season: {}}
        if 'episode -1' in data:
          counter = 1
          for episode in data['episode -1']:
            while 'episode %d' % counter in data:
              counter += 1
            k = 'episode %d' % counter
            data[k] = [episode]
          del data['episode -1']
        for episode_nr, episode in data.iteritems():
            if not (episode and episode[0] and
                    episode_nr.startswith('episode ')):
                continue
            episode = episode[0]
            episode_nr = episode_nr[8:].rstrip()
            try: episode_nr = int(episode_nr)
            except: pass
            episode_id = analyze_imdbid(episode.get('link' ''))
            episode_air_date = episode.get('original air date',
                                            '').strip()
            episode_title = episode.get('title', '').strip()
            episode_plot = episode.get('plot', '')
            if not (episode_nr and episode_id and episode_title):
                continue
            ep_obj = Movie(movieID=episode_id, title=episode_title,
                        accessSystem=self._as, modFunct=self._modFunct)
            ep_obj['kind'] = u'episode'
            ep_obj['episode of'] = series
            ep_obj['season'] = selected_season
            ep_obj['episode'] = episode_nr
            if episode_air_date:
                ep_obj['original air date'] = episode_air_date
                if episode_air_date[-4:].isdigit():
                    ep_obj['year'] = episode_air_date[-4:]
            if episode_plot:
                ep_obj['plot'] = episode_plot
            nd[selected_season][episode_nr] = ep_obj
        _seasons = data.get('_seasons') or []
        for idx, season in enumerate(_seasons):
            try: _seasons[idx] = int(season)
            except: pass
        return {'episodes': nd, '_seasons': _seasons,
                '_current_season': selected_season}


def _build_episode(x):
    """Create a Movie object for a given series' episode."""
    episode_id = analyze_imdbid(x.get('link'))
    episode_title = x.get('title')
    e = Movie(movieID=episode_id, title=episode_title)
    e['kind'] = u'episode'
    oad = x.get('oad')
    if oad:
        e['original air date'] = oad.strip()
    year = x.get('year')
    if year is not None:
        year = year[5:]
        if year == 'unknown': year = u'????'
        if year and year.isdigit():
            year = int(year)
        e['year'] = year
    else:
        if oad and oad[-4:].isdigit():
            e['year'] = int(oad[-4:])
    epinfo = x.get('episode')
    if epinfo is not None:
        season, episode = epinfo.split(':')[0].split(',')
        e['season'] = int(season[7:])
        e['episode'] = int(episode[8:])
    else:
        e['season'] = 'unknown'
        e['episode'] = 'unknown'
    plot = x.get('plot')
    if plot:
        e['plot'] = plot.strip()
    return e


class DOMHTMLEpisodesParser(DOMParserBase):
    """Parser for the "episode list" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        eparser = DOMHTMLEpisodesParser()
        result = eparser.parse(episodes_html_string)
    """
    # XXX: no more used for the list of episodes parser,
    #      but only for the episodes cast parser (see below).
    _containsObjects = True

    kind = 'episodes list'
    _episodes_path = "..//h4"
    _oad_path = "./following-sibling::span/strong[1]/text()"

    def _init(self):
        self.extractors = [
            Extractor(label='series',
                path="//html",
                attrs=[Attribute(key='series title',
                                path=".//title/text()"),
                        Attribute(key='series movieID',
                                path=".//h1/a[@class='main']/@href",
                                postprocess=analyze_imdbid)
                    ]),
            Extractor(label='episodes',
                group="//div[@class='_imdbpy']/h3",
                group_key="./a/@name",
                path=self._episodes_path,
                attrs=Attribute(key=None,
                    multi=True,
                    path={
                        'link': "./a/@href",
                        'title': "./a/text()",
                        'year': "./preceding-sibling::a[1]/@name",
                        'episode': "./text()[1]",
                        'oad': self._oad_path,
                        'plot': "./following-sibling::text()[1]"
                    },
                    postprocess=_build_episode))]
        if self.kind == 'episodes cast':
            self.extractors += [
                Extractor(label='cast',
                    group="//h4",
                    group_key="./text()[1]",
                    group_key_normalize=lambda x: x.strip(),
                    path="./following-sibling::table[1]//td[@class='nm']",
                    attrs=Attribute(key=None,
                        multi=True,
                        path={'person': "..//text()",
                            'link': "./a/@href",
                            'roleID': \
                                "../td[4]/div[@class='_imdbpyrole']/@roleid"},
                        postprocess=lambda x: \
                                build_person(x.get('person') or u'',
                                personID=analyze_imdbid(x.get('link')),
                                roleID=(x.get('roleID') or u'').split('/'),
                                accessSystem=self._as,
                                modFunct=self._modFunct)))
                ]

    preprocessors = [
        (re.compile('(<hr/>\n)(<h3>)', re.I),
                    r'</div>\1<div class="_imdbpy">\2'),
        (re.compile('(</p>\n\n)</div>', re.I), r'\1'),
        (re.compile('<h3>(.*?)</h3>', re.I), r'<h4>\1</h4>'),
        (_reRolesMovie, _manageRoles),
        (re.compile('(<br/> <br/>\n)(<hr/>)', re.I), r'\1</div>\2')
        ]

    def postprocess_data(self, data):
        # A bit extreme?
        if not 'series title' in data: return {}
        if not 'series movieID' in data: return {}
        stitle = data['series title'].replace('- Episode list', '')
        stitle = stitle.replace('- Episodes list', '')
        stitle = stitle.replace('- Episode cast', '')
        stitle = stitle.replace('- Episodes cast', '')
        stitle = stitle.strip()
        if not stitle: return {}
        seriesID = data['series movieID']
        if seriesID is None: return {}
        series = Movie(title=stitle, movieID=str(seriesID),
                        accessSystem=self._as, modFunct=self._modFunct)
        nd = {}
        for key in data.keys():
            if key.startswith('filter-season-') or key.startswith('season-'):
                season_key = key.replace('filter-season-', '').replace('season-', '')
                try: season_key = int(season_key)
                except: pass
                nd[season_key] = {}
                ep_counter = 1
                for episode in data[key]:
                    if not episode: continue
                    episode_key = episode.get('episode')
                    if episode_key is None: continue
                    if not isinstance(episode_key, int):
                        episode_key = ep_counter
                        ep_counter += 1
                    cast_key = 'Season %s, Episode %s:' % (season_key,
                                                            episode_key)
                    if data.has_key(cast_key):
                        cast = data[cast_key]
                        for i in xrange(len(cast)):
                            cast[i].billingPos = i + 1
                        episode['cast'] = cast
                    episode['episode of'] = series
                    nd[season_key][episode_key] = episode
        if len(nd) == 0:
            return {}
        return {'episodes': nd}


class DOMHTMLEpisodesCastParser(DOMHTMLEpisodesParser):
    """Parser for the "episodes cast" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        eparser = DOMHTMLEpisodesParser()
        result = eparser.parse(episodes_html_string)
    """
    kind = 'episodes cast'
    _episodes_path = "..//h4"
    _oad_path = "./following-sibling::b[1]/text()"


class DOMHTMLFaqsParser(DOMParserBase):
    """Parser for the "FAQ" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        fparser = DOMHTMLFaqsParser()
        result = fparser.parse(faqs_html_string)
    """
    _defGetRefs = True

    # XXX: bsoup and lxml don't match (looks like a minor issue, anyway).

    extractors = [
        Extractor(label='faqs',
            path="//div[@class='section']",
            attrs=Attribute(key='faqs',
                multi=True,
                path={
                    'question': "./h3/a/span/text()",
                    'answer': "../following-sibling::div[1]//text()"
                },
                postprocess=lambda x: u'%s::%s' % (x.get('question').strip(),
                                    '\n\n'.join(x.get('answer').replace(
                                        '\n\n', '\n').strip().split('||')))))
        ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||'),
        (re.compile('<h4>(.*?)</h4>\n', re.I), r'||\1--'),
        (re.compile('<span class="spoiler"><span>(.*?)</span></span>', re.I),
         r'[spoiler]\1[/spoiler]')
        ]


class DOMHTMLAiringParser(DOMParserBase):
    """Parser for the "airing" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        aparser = DOMHTMLAiringParser()
        result = aparser.parse(airing_html_string)
    """
    _containsObjects = True

    extractors = [
        Extractor(label='series title',
            path="//title",
            attrs=Attribute(key='series title', path="./text()",
                            postprocess=lambda x: \
                                    x.replace(' - TV schedule', u''))),
        Extractor(label='series id',
            path="//h1/a[@href]",
            attrs=Attribute(key='series id', path="./@href")),

        Extractor(label='tv airings',
            path="//tr[@class]",
            attrs=Attribute(key='airing',
                multi=True,
                path={
                    'date': "./td[1]//text()",
                    'time': "./td[2]//text()",
                    'channel': "./td[3]//text()",
                    'link': "./td[4]/a[1]/@href",
                    'title': "./td[4]//text()",
                    'season': "./td[5]//text()",
                    },
                postprocess=lambda x: {
                    'date': x.get('date'),
                    'time': x.get('time'),
                    'channel': x.get('channel').strip(),
                    'link': x.get('link'),
                    'title': x.get('title'),
                    'season': (x.get('season') or '').strip()
                    }
                ))
    ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        seriesTitle = data['series title']
        seriesID = analyze_imdbid(data['series id'])
        if data.has_key('airing'):
            for airing in data['airing']:
                title = airing.get('title', '').strip()
                if not title:
                    epsTitle = seriesTitle
                    if seriesID is None:
                        continue
                    epsID = seriesID
                else:
                    epsTitle = '%s {%s}' % (data['series title'],
                                            airing['title'])
                    epsID = analyze_imdbid(airing['link'])
                e = Movie(title=epsTitle, movieID=epsID)
                airing['episode'] = e
                del airing['link']
                del airing['title']
                if not airing['season']:
                    del airing['season']
        if 'series title' in data:
            del data['series title']
        if 'series id' in data:
            del data['series id']
        if 'airing' in data:
            data['airing'] = filter(None, data['airing'])
        if 'airing' not in data or not data['airing']:
            return {}
        return data


class DOMHTMLSynopsisParser(DOMParserBase):
    """Parser for the "synopsis" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = HTMLSynopsisParser()
        result = sparser.parse(synopsis_html_string)
    """
    extractors = [
        Extractor(label='synopsis',
            path="//div[@class='display'][not(@style)]",
            attrs=Attribute(key='synopsis',
                path=".//text()",
                postprocess=lambda x: '\n\n'.join(x.strip().split('||'))))
    ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||')
        ]


class DOMHTMLParentsGuideParser(DOMParserBase):
    """Parser for the "parents guide" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        pgparser = HTMLParentsGuideParser()
        result = pgparser.parse(parentsguide_html_string)
    """
    extractors = [
        Extractor(label='parents guide',
            group="//div[@class='section']",
            group_key="./h3/a/span/text()",
            group_key_normalize=lambda x: x.lower(),
            path="../following-sibling::div[1]/p",
            attrs=Attribute(key=None,
                path=".//text()",
                postprocess=lambda x: [t.strip().replace('\n', ' ')
                                       for t in x.split('||') if t.strip()]))
    ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||')
        ]

    def postprocess_data(self, data):
        data2 = {}
        for key in data:
            if data[key]:
                data2[key] = data[key]
        if not data2:
            return {}
        return {'parents guide': data2}


_OBJECTS = {
    'movie_parser':  ((DOMHTMLMovieParser,), None),
    'plot_parser':  ((DOMHTMLPlotParser,), None),
    'movie_awards_parser': ((DOMHTMLAwardsParser,), None),
    'taglines_parser':  ((DOMHTMLTaglinesParser,), None),
    'keywords_parser':  ((DOMHTMLKeywordsParser,), None),
    'crazycredits_parser':  ((DOMHTMLCrazyCreditsParser,), None),
    'goofs_parser':  ((DOMHTMLGoofsParser,), None),
    'alternateversions_parser':  ((DOMHTMLAlternateVersionsParser,), None),
    'trivia_parser':  ((DOMHTMLTriviaParser,), None),
    'soundtrack_parser':  ((DOMHTMLSoundtrackParser,), {'kind': 'soundtrack'}),
    'quotes_parser':  ((DOMHTMLQuotesParser,), None),
    'releasedates_parser':  ((DOMHTMLReleaseinfoParser,), None),
    'ratings_parser':  ((DOMHTMLRatingsParser,), None),
    'officialsites_parser':  ((DOMHTMLOfficialsitesParser,), None),
    'criticrev_parser':  ((DOMHTMLCriticReviewsParser,),
                            {'kind': 'critic reviews'}),
    'externalrev_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'external reviews'}),
    'newsgrouprev_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'newsgroup reviews'}),
    'misclinks_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'misc links'}),
    'soundclips_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'sound clips'}),
    'videoclips_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'video clips'}),
    'photosites_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'photo sites'}),
    'connections_parser':  ((DOMHTMLConnectionParser,), None),
    'tech_parser':  ((DOMHTMLTechParser,), None),
    'business_parser':  ((DOMHTMLTechParser,),
                            {'kind': 'business', '_defGetRefs': 1}),
    'literature_parser':  ((DOMHTMLTechParser,), {'kind': 'literature'}),
    'locations_parser':  ((DOMHTMLLocationsParser,), None),
    'rec_parser':  ((DOMHTMLRecParser,), None),
    'news_parser':  ((DOMHTMLNewsParser,), None),
    'episodes_parser':  ((DOMHTMLEpisodesParser,), None),
    'season_episodes_parser':  ((DOMHTMLSeasonEpisodesParser,), None),
    'episodes_cast_parser':  ((DOMHTMLEpisodesCastParser,), None),
    'eprating_parser':  ((DOMHTMLEpisodesRatings,), None),
    'movie_faqs_parser':  ((DOMHTMLFaqsParser,), None),
    'airing_parser':  ((DOMHTMLAiringParser,), None),
    'synopsis_parser':  ((DOMHTMLSynopsisParser,), None),
    'parentsguide_parser':  ((DOMHTMLParentsGuideParser,), None)
}


########NEW FILE########
__FILENAME__ = personParser
"""
parser.http.personParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a person.
E.g., for "Mel Gibson" the referred pages would be:
    categorized:    http://akas.imdb.com/name/nm0000154/maindetails
    biography:      http://akas.imdb.com/name/nm0000154/bio
    ...and so on...

Copyright 2004-2013 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
from imdb.Movie import Movie
from imdb.utils import analyze_name, canonicalName, normalizeName, \
                        analyze_title, date_and_notes
from utils import build_movie, DOMParserBase, Attribute, Extractor, \
                        analyze_imdbid


from movieParser import _manageRoles
_reRoles = re.compile(r'(<li>.*? \.\.\.\. )(.*?)(</li>|<br>)',
                        re.I | re.M | re.S)

def build_date(date):
    day = date.get('day')
    year = date.get('year')
    if day and year:
        return "%s %s" % (day, year)
    if day:
        return day
    if year:
        return year
    return ""

class DOMHTMLMaindetailsParser(DOMParserBase):
    """Parser for the "categorized" (maindetails) page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        cparser = DOMHTMLMaindetailsParser()
        result = cparser.parse(categorized_html_string)
    """
    _containsObjects = True
    _name_imdb_index = re.compile(r'\([IVXLCDM]+\)')

    _birth_attrs = [Attribute(key='birth date',
                        path='.//time[@itemprop="birthDate"]/@datetime'),
                    Attribute(key='birth place',
                        path=".//a[starts-with(@href, " \
                                "'/search/name?birth_place=')]/text()")]
    _death_attrs = [Attribute(key='death date',
                        path='.//time[@itemprop="deathDate"]/@datetime'),
                    Attribute(key='death place',
                        path=".//a[starts-with(@href, " \
                                "'/search/name?death_place=')]/text()")]
    _film_attrs = [Attribute(key=None,
                      multi=True,
                      path={
                          'link': "./b/a[1]/@href",
                          'title': "./b/a[1]/text()",
                          'notes': "./b/following-sibling::text()",
                          'year': "./span[@class='year_column']/text()",
                          'status': "./a[@class='in_production']/text()",
                          'rolesNoChar': './/br/following-sibling::text()',
                          'chrRoles': "./a[@imdbpyname]/@imdbpyname",
                          'roleID': "./a[starts-with(@href, '/character/')]/@href"
                          },
                      postprocess=lambda x:
                          build_movie(x.get('title') or u'',
                              year=x.get('year'),
                              movieID=analyze_imdbid(x.get('link') or u''),
                              rolesNoChar=(x.get('rolesNoChar') or u'').strip(),
                              chrRoles=(x.get('chrRoles') or u'').strip(),
                              additionalNotes=x.get('notes'),
                              roleID=(x.get('roleID') or u''),
                              status=x.get('status') or None))]

    extractors = [
            Extractor(label='name',
                        path="//h1[@class='header']",
                        attrs=Attribute(key='name',
                            path=".//text()",
                            postprocess=lambda x: analyze_name(x,
                                                               canonical=1))),
            Extractor(label='name_index',
                        path="//h1[@class='header']/span[1]",
                        attrs=Attribute(key='name_index',
                            path="./text()")),

            Extractor(label='birth info',
                        path="//div[h4='Born:']",
                        attrs=_birth_attrs),

            Extractor(label='death info',
                        path="//div[h4='Died:']",
                        attrs=_death_attrs),

            Extractor(label='headshot',
                        path="//td[@id='img_primary']/div[@class='image']/a",
                        attrs=Attribute(key='headshot',
                            path="./img/@src")),

            Extractor(label='akas',
                        path="//div[h4='Alternate Names:']",
                        attrs=Attribute(key='akas',
                            path="./text()",
                            postprocess=lambda x: x.strip().split('  '))),

            Extractor(label='filmography',
                        group="//div[starts-with(@id, 'filmo-head-')]",
                        group_key="./a[@name]/text()",
                        group_key_normalize=lambda x: x.lower().replace(': ', ' '),
                        path="./following-sibling::div[1]" \
                                "/div[starts-with(@class, 'filmo-row')]",
                        attrs=_film_attrs),

            Extractor(label='indevelopment',
                        path="//div[starts-with(@class,'devitem')]",
                        attrs=Attribute(key='in development',
                            multi=True,
                            path={
                                'link': './a/@href',
                                'title': './a/text()'
                                },
                                postprocess=lambda x:
                                    build_movie(x.get('title') or u'',
                                        movieID=analyze_imdbid(x.get('link') or u''),
                                        roleID=(x.get('roleID') or u'').split('/'),
                                        status=x.get('status') or None)))
            ]

    preprocessors = [('<div class="clear"/> </div>', ''),
            ('<br/>', '<br />'),
            (re.compile(r'(<a href="/character/ch[0-9]{7}")>(.*?)</a>'),
                r'\1 imdbpyname="\2@@">\2</a>')]

    def postprocess_data(self, data):
        for what in 'birth date', 'death date':
            if what in data and not data[what]:
                del data[what]
        name_index = (data.get('name_index') or '').strip()
        if name_index:
            if self._name_imdb_index.match(name_index):
                data['imdbIndex'] = name_index[1:-1]
            del data['name_index']
        # XXX: the code below is for backwards compatibility
        # probably could be removed
        for key in data.keys():
            if key.startswith('actor '):
                if not data.has_key('actor'):
                    data['actor'] = []
                data['actor'].extend(data[key])
                del data[key]
            if key.startswith('actress '):
                if not data.has_key('actress'):
                    data['actress'] = []
                data['actress'].extend(data[key])
                del data[key]
            if key.startswith('self '):
                if not data.has_key('self'):
                    data['self'] = []
                data['self'].extend(data[key])
                del data[key]
            if key == 'birth place':
                data['birth notes'] = data[key]
                del data[key]
            if key == 'death place':
                data['death notes'] = data[key]
                del data[key]
        return data


class DOMHTMLBioParser(DOMParserBase):
    """Parser for the "biography" page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bioparser = DOMHTMLBioParser()
        result = bioparser.parse(biography_html_string)
    """
    _defGetRefs = True

    _birth_attrs = [Attribute(key='birth date',
                        path={
                            'day': "./a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./a[starts-with(@href, " \
                                    "'/search/name?birth_year=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='birth notes',
                        path="./a[starts-with(@href, " \
                                "'/search/name?birth_place=')]/text()")]
    _death_attrs = [Attribute(key='death date',
                        path={
                            'day': "./a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./a[starts-with(@href, " \
                                    "'/search/name?death_date=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='death notes',
                        path="./text()",
                        # TODO: check if this slicing is always correct
                        postprocess=lambda x: u''.join(x).strip()[2:])]
    extractors = [
            Extractor(label='headshot',
                        path="//a[@name='headshot']",
                        attrs=Attribute(key='headshot',
                            path="./img/@src")),
            Extractor(label='birth info',
                        path="//table[@id='overviewTable']//td[text()='Date of Birth']/following-sibling::td[1]",
                        attrs=_birth_attrs),
            Extractor(label='death info',
                        path="//table[@id='overviewTable']//td[text()='Date of Death']/following-sibling::td[1]",
                        attrs=_death_attrs),
            Extractor(label='nick names',
                        path="//table[@id='overviewTable']//td[text()='Nickenames']/following-sibling::td[1]",
                        attrs=Attribute(key='nick names',
                            path="./text()",
                            joiner='|',
                            postprocess=lambda x: [n.strip().replace(' (',
                                    '::(', 1) for n in x.split('|')
                                    if n.strip()])),
            Extractor(label='birth name',
                        path="//table[@id='overviewTable']//td[text()='Birth Name']/following-sibling::td[1]",
                        attrs=Attribute(key='birth name',
                            path="./text()",
                            postprocess=lambda x: canonicalName(x.strip()))),
            Extractor(label='height',
                path="//table[@id='overviewTable']//td[text()='Height']/following-sibling::td[1]",
                        attrs=Attribute(key='height',
                            path="./text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='mini biography',
                        path="//a[@name='mini_bio']/following-sibling::div[1 = count(preceding-sibling::a[1] | ../a[@name='mini_bio'])]",
                        attrs=Attribute(key='mini biography',
                            multi=True,
                            path={
                                'bio': ".//text()",
                                'by': ".//a[@name='ba']//text()"
                                },
                            postprocess=lambda x: "%s::%s" % \
                                ((x.get('bio') or u'').split('- IMDb Mini Biography By:')[0].strip(),
                                (x.get('by') or u'').strip() or u'Anonymous'))),
            Extractor(label='spouse',
                        path="//div[h5='Spouse']/table/tr",
                        attrs=Attribute(key='spouse',
                            multi=True,
                            path={
                                'name': "./td[1]//text()",
                                'info': "./td[2]//text()"
                                },
                            postprocess=lambda x: ("%s::%s" % \
                                (x.get('name').strip(),
                                (x.get('info') or u'').strip())).strip(':'))),
            Extractor(label='trade mark',
                        path="//div[h5='Trade Mark']/p",
                        attrs=Attribute(key='trade mark',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='trivia',
                        path="//div[h5='Trivia']/p",
                        attrs=Attribute(key='trivia',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='quotes',
                        path="//div[h5='Personal Quotes']/p",
                        attrs=Attribute(key='quotes',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='salary',
                        path="//div[h5='Salary']/table/tr",
                        attrs=Attribute(key='salary history',
                            multi=True,
                            path={
                                'title': "./td[1]//text()",
                                'info': "./td[2]/text()",
                                },
                            postprocess=lambda x: "%s::%s" % \
                                    (x.get('title').strip(),
                                        x.get('info').strip()))),
            Extractor(label='where now',
                        path="//div[h5='Where Are They Now']/p",
                        attrs=Attribute(key='where now',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            ]

    preprocessors = [
        (re.compile('(<h5>)', re.I), r'</div><div class="_imdbpy">\1'),
        (re.compile('(</table>\n</div>\s+)</div>', re.I + re.DOTALL), r'\1'),
        (re.compile('(<div id="tn15bot">)'), r'</div>\1'),
        (re.compile('\.<br><br>([^\s])', re.I), r'. \1')
        ]

    def postprocess_data(self, data):
        for what in 'birth date', 'death date':
            if what in data and not data[what]:
                del data[what]
        return data


class DOMHTMLOtherWorksParser(DOMParserBase):
    """Parser for the "other works" and "agent" pages of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        owparser = DOMHTMLOtherWorksParser()
        result = owparser.parse(otherworks_html_string)
    """
    _defGetRefs = True
    kind = 'other works'

    # XXX: looks like the 'agent' page is no more public.
    extractors = [
            Extractor(label='other works',
                        path="//h5[text()='Other works']/" \
                                "following-sibling::div[1]",
                        attrs=Attribute(key='self.kind',
                            path=".//text()",
                            postprocess=lambda x: x.strip().split('\n\n')))
            ]

    preprocessors = [
        (re.compile('(<h5>[^<]+</h5>)', re.I),
            r'</div>\1<div class="_imdbpy">'),
        (re.compile('(</table>\n</div>\s+)</div>', re.I), r'\1'),
        (re.compile('(<div id="tn15bot">)'), r'</div>\1'),
        (re.compile('<br/><br/>', re.I), r'\n\n')
        ]


def _build_episode(link, title, minfo, role, roleA, roleAID):
    """Build an Movie object for a given episode of a series."""
    episode_id = analyze_imdbid(link)
    notes = u''
    minidx = minfo.find(' -')
    # Sometimes, for some unknown reason, the role is left in minfo.
    if minidx != -1:
        slfRole = minfo[minidx+3:].lstrip()
        minfo = minfo[:minidx].rstrip()
        if slfRole.endswith(')'):
            commidx = slfRole.rfind('(')
            if commidx != -1:
                notes = slfRole[commidx:]
                slfRole = slfRole[:commidx]
        if slfRole and role is None and roleA is None:
            role = slfRole
    eps_data = analyze_title(title)
    eps_data['kind'] = u'episode'
    # FIXME: it's wrong for multiple characters (very rare on tv series?).
    if role is None:
        role = roleA # At worse, it's None.
    if role is None:
        roleAID = None
    if roleAID is not None:
        roleAID = analyze_imdbid(roleAID)
    e = Movie(movieID=episode_id, data=eps_data, currentRole=role,
            roleID=roleAID, notes=notes)
    # XXX: are we missing some notes?
    # XXX: does it parse things as "Episode dated 12 May 2005 (12 May 2005)"?
    if minfo.startswith('('):
        pe = minfo.find(')')
        if pe != -1:
            date = minfo[1:pe]
            if date != '????':
                e['original air date'] = date
                if eps_data.get('year', '????') == '????':
                    syear = date.split()[-1]
                    if syear.isdigit():
                        e['year'] = int(syear)
    return e


class DOMHTMLSeriesParser(DOMParserBase):
    """Parser for the "by TV series" page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = DOMHTMLSeriesParser()
        result = sparser.parse(filmoseries_html_string)
    """
    _containsObjects = True

    extractors = [
            Extractor(label='series',
                        group="//div[@class='filmo']/span[1]",
                        group_key="./a[1]",
                        path="./following-sibling::ol[1]/li/a[1]",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./@href",
                                'title': "./text()",
                                'info': "./following-sibling::text()",
                                'role': "./following-sibling::i[1]/text()",
                                'roleA': "./following-sibling::a[1]/text()",
                                'roleAID': "./following-sibling::a[1]/@href"
                                },
                            postprocess=lambda x: _build_episode(x.get('link'),
                                x.get('title'),
                                (x.get('info') or u'').strip(),
                                x.get('role'),
                                x.get('roleA'),
                                x.get('roleAID'))))
            ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        nd = {}
        for key in data.keys():
            dom = self.get_dom(key)
            link = self.xpath(dom, "//a/@href")[0]
            title = self.xpath(dom, "//a/text()")[0][1:-1]
            series = Movie(movieID=analyze_imdbid(link),
                           data=analyze_title(title),
                           accessSystem=self._as, modFunct=self._modFunct)
            nd[series] = []
            for episode in data[key]:
                # XXX: should we create a copy of 'series', to avoid
                #      circular references?
                episode['episode of'] = series
                nd[series].append(episode)
        return {'episodes': nd}


class DOMHTMLPersonGenresParser(DOMParserBase):
    """Parser for the "by genre" and "by keywords" pages of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        gparser = DOMHTMLPersonGenresParser()
        result = gparser.parse(bygenre_html_string)
    """
    kind = 'genres'
    _containsObjects = True

    extractors = [
            Extractor(label='genres',
                        group="//b/a[@name]/following-sibling::a[1]",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../../following-sibling::ol[1]/li//a[1]",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./@href",
                                'title': "./text()",
                                'info': "./following-sibling::text()"
                                },
                            postprocess=lambda x: \
                                    build_movie(x.get('title') + \
                                    x.get('info').split('[')[0],
                                    analyze_imdbid(x.get('link')))))
            ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        return {self.kind: data}


from movieParser import DOMHTMLTechParser
from movieParser import DOMHTMLOfficialsitesParser
from movieParser import DOMHTMLAwardsParser
from movieParser import DOMHTMLNewsParser


_OBJECTS = {
    'maindetails_parser': ((DOMHTMLMaindetailsParser,), None),
    'bio_parser': ((DOMHTMLBioParser,), None),
    'otherworks_parser': ((DOMHTMLOtherWorksParser,), None),
    #'agent_parser': ((DOMHTMLOtherWorksParser,), {'kind': 'agent'}),
    'person_officialsites_parser': ((DOMHTMLOfficialsitesParser,), None),
    'person_awards_parser': ((DOMHTMLAwardsParser,), {'subject': 'name'}),
    'publicity_parser': ((DOMHTMLTechParser,), {'kind': 'publicity'}),
    'person_series_parser': ((DOMHTMLSeriesParser,), None),
    'person_contacts_parser': ((DOMHTMLTechParser,), {'kind': 'contacts'}),
    'person_genres_parser': ((DOMHTMLPersonGenresParser,), None),
    'person_keywords_parser': ((DOMHTMLPersonGenresParser,),
                                {'kind': 'keywords'}),
    'news_parser': ((DOMHTMLNewsParser,), None),
}


########NEW FILE########
__FILENAME__ = searchCharacterParser
"""
parser.http.searchCharacterParser module (imdb package).

This module provides the HTMLSearchCharacterParser class (and the
search_character_parser instance), used to parse the results of a search
for a given character.
E.g., when searching for the name "Jesse James", the parsed page would be:
    http://akas.imdb.com/find?s=ch;mx=20;q=Jesse+James

Copyright 2007-2012 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from imdb.utils import analyze_name, build_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser


class DOMBasicCharacterParser(DOMBasicMovieParser):
    """Simply get the name of a character and the imdbID.

    It's used by the DOMHTMLSearchCharacterParser class to return a result
    for a direct match (when a search on IMDb results in a single
    character, the web server sends directly the movie page."""
    _titleFunct = lambda self, x: analyze_name(x or u'', canonical=False)


class DOMHTMLSearchCharacterParser(DOMHTMLSearchMovieParser):
    _BaseParser = DOMBasicCharacterParser
    _notDirectHitTitle = '<title>find - imdb'
    _titleBuilder = lambda self, x: build_name(x, canonical=False)
    _linkPrefix = '/character/ch'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            {'name': x.get('name')}
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[@class='result_text']/a[starts-with(@href, " \
                                    "'/character/ch')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_character_parser': ((DOMHTMLSearchCharacterParser,),
                {'kind': 'character', '_basic_parser': DOMBasicCharacterParser})
}


########NEW FILE########
__FILENAME__ = searchCompanyParser
"""
parser.http.searchCompanyParser module (imdb package).

This module provides the HTMLSearchCompanyParser class (and the
search_company_parser instance), used to parse the results of a search
for a given company.
E.g., when searching for the name "Columbia Pictures", the parsed page would be:
    http://akas.imdb.com/find?s=co;mx=20;q=Columbia+Pictures

Copyright 2008-2012 Davide Alberani <da@erlug.linux.it>
          2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from imdb.utils import analyze_company_name, build_company_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser

class DOMBasicCompanyParser(DOMBasicMovieParser):
    """Simply get the name of a company and the imdbID.

    It's used by the DOMHTMLSearchCompanyParser class to return a result
    for a direct match (when a search on IMDb results in a single
    company, the web server sends directly the company page.
    """
    _titleFunct = lambda self, x: analyze_company_name(x or u'')


class DOMHTMLSearchCompanyParser(DOMHTMLSearchMovieParser):
    _BaseParser = DOMBasicCompanyParser
    _notDirectHitTitle = '<title>find - imdb'
    _titleBuilder = lambda self, x: build_company_name(x)
    _linkPrefix = '/company/co'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()",
                            'notes': "./text()[1]"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link')),
                            analyze_company_name(x.get('name')+(x.get('notes')
                                                or u''), stripNotes=True)
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[@class='result_text']/a[starts-with(@href, " \
                                    "'/company/co')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_company_parser': ((DOMHTMLSearchCompanyParser,),
                {'kind': 'company', '_basic_parser': DOMBasicCompanyParser})
}


########NEW FILE########
__FILENAME__ = searchKeywordParser
"""
parser.http.searchKeywordParser module (imdb package).

This module provides the HTMLSearchKeywordParser class (and the
search_company_parser instance), used to parse the results of a search
for a given keyword.
E.g., when searching for the keyword "alabama", the parsed page would be:
    http://akas.imdb.com/find?s=kw;mx=20;q=alabama

Copyright 2009 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from utils import Extractor, Attribute, analyze_imdbid
from imdb.utils import analyze_title, analyze_company_name

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser

class DOMBasicKeywordParser(DOMBasicMovieParser):
    """Simply get the name of a keyword.

    It's used by the DOMHTMLSearchKeywordParser class to return a result
    for a direct match (when a search on IMDb results in a single
    keyword, the web server sends directly the keyword page.
    """
    # XXX: it's still to be tested!
    # I'm not even sure there can be a direct hit, searching for keywords.
    _titleFunct = lambda self, x: analyze_company_name(x or u'')


class DOMHTMLSearchKeywordParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, searching for keywords similar to
    the one given."""

    _BaseParser = DOMBasicKeywordParser
    _notDirectHitTitle = '<title>imdb keyword'
    _titleBuilder = lambda self, x: x
    _linkPrefix = '/keyword/'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path="./a[1]/text()"
                            )]
    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/keyword/')]/..",
                            attrs=_attrs)]


def custom_analyze_title4kwd(title, yearNote, outline):
    """Return a dictionary with the needed info."""
    title = title.strip()
    if not title:
        return {}
    if yearNote:
        yearNote = '%s)' % yearNote.split(' ')[0]
        title = title + ' ' + yearNote
    retDict = analyze_title(title)
    if outline:
        retDict['plot outline'] = outline
    return retDict


class DOMHTMLSearchMovieKeywordParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, searching for movies with the given
    keyword."""

    _notDirectHitTitle = '<title>best'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'info': "./a[1]//text()",
                            'ynote': "./span[@class='desc']/text()",
                            'outline': "./span[@class='outline']//text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            custom_analyze_title4kwd(x.get('info') or u'',
                                                    x.get('ynote') or u'',
                                                    x.get('outline') or u'')
                        ))]

    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/title/tt')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_keyword_parser': ((DOMHTMLSearchKeywordParser,),
                {'kind': 'keyword', '_basic_parser': DOMBasicKeywordParser}),
        'search_moviekeyword_parser': ((DOMHTMLSearchMovieKeywordParser,), None)
}


########NEW FILE########
__FILENAME__ = searchMovieParser
"""
parser.http.searchMovieParser module (imdb package).

This module provides the HTMLSearchMovieParser class (and the
search_movie_parser instance), used to parse the results of a search
for a given title.
E.g., for when searching for the title "the passion", the parsed
page would be:
    http://akas.imdb.com/find?q=the+passion&tt=on&mx=20

Copyright 2004-2013 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
from imdb.utils import analyze_title, build_title
from utils import DOMParserBase, Attribute, Extractor, analyze_imdbid


class DOMBasicMovieParser(DOMParserBase):
    """Simply get the title of a movie and the imdbID.

    It's used by the DOMHTMLSearchMovieParser class to return a result
    for a direct match (when a search on IMDb results in a single
    movie, the web server sends directly the movie page."""
    # Stay generic enough to be used also for other DOMBasic*Parser classes.
    _titleAttrPath = ".//text()"
    _linkPath = "//link[@rel='canonical']"
    _titleFunct = lambda self, x: analyze_title(x or u'')

    def _init(self):
        self.preprocessors += [('<span class="tv-extra">TV mini-series</span>',
                                '<span class="tv-extra">(mini)</span>')]
        self.extractors = [Extractor(label='title',
                                path="//h1",
                                attrs=Attribute(key='title',
                                                path=self._titleAttrPath,
                                                postprocess=self._titleFunct)),
                            Extractor(label='link',
                                path=self._linkPath,
                                attrs=Attribute(key='link', path="./@href",
                                postprocess=lambda x: \
                                        analyze_imdbid((x or u'').replace(
                                            'http://pro.imdb.com', ''))
                                    ))]

    # Remove 'More at IMDb Pro' links.
    preprocessors = [(re.compile(r'<span class="pro-link".*?</span>'), ''),
            (re.compile(r'<a href="http://ad.doubleclick.net.*?;id=(co[0-9]{7});'), r'<a href="http://pro.imdb.com/company/\1"></a>< a href="')]

    def postprocess_data(self, data):
        if not 'link' in data:
            data = []
        else:
            link = data.pop('link')
            if (link and data):
                data = [(link, data)]
            else:
                data = []
        return data


def custom_analyze_title(title):
    """Remove garbage notes after the (year), (year/imdbIndex) or (year) (TV)"""
    # XXX: very crappy. :-(
    nt = title.split(' aka ')[0]
    if nt:
        title = nt
    if not title:
        return {}
    return analyze_title(title)

# Manage AKAs.
_reAKAStitles = re.compile(r'(?:aka) <em>"(.*?)(<br>|<\/td>)', re.I | re.M)

class DOMHTMLSearchMovieParser(DOMParserBase):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, for movies."""

    _BaseParser = DOMBasicMovieParser
    _notDirectHitTitle = '<title>find - imdb</title>'
    _titleBuilder = lambda self, x: build_title(x)
    _linkPrefix = '/title/tt'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'info': ".//text()",
                            'akas': "./i//text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            custom_analyze_title(x.get('info') or u''),
                            x.get('akas')
                        ))]
    extractors = [Extractor(label='search',
                        path="//td[@class='result_text']",
                        attrs=_attrs)]
    def _init(self):
        self.url = u''

    def _reset(self):
        self.url = u''

    def preprocess_string(self, html_string):
        if self._notDirectHitTitle in html_string[:10240].lower():
            if self._linkPrefix == '/title/tt':
                # Only for movies.
                # XXX (HTU): does this still apply?
                html_string = html_string.replace('(TV mini-series)', '(mini)')
            return html_string
        # Direct hit!
        dbme = self._BaseParser(useModule=self._useModule)
        res = dbme.parse(html_string, url=self.url)
        if not res: return u''
        res = res['data']
        if not (res and res[0]): return u''
        link = '%s%s' % (self._linkPrefix, res[0][0])
        #    # Tries to cope with companies for which links to pro.imdb.com
        #    # are missing.
        #    link = self.url.replace(imdbURL_base[:-1], '')
        title = self._titleBuilder(res[0][1])
        if not (link and title): return u''
        link = link.replace('http://pro.imdb.com', '')
        new_html = '<td class="result_text"><a href="%s">%s</a></td>' % (link,
                                                                    title)
        return new_html

    def postprocess_data(self, data):
        if not data.has_key('data'):
            data['data'] = []
        results = getattr(self, 'results', None)
        if results is not None:
            data['data'][:] = data['data'][:results]
        # Horrible hack to support AKAs.
        if data and data['data'] and len(data['data'][0]) == 3 and \
                isinstance(data['data'][0], tuple):
            data['data'] = [x for x in data['data'] if x[0] and x[1]]
            for idx, datum in enumerate(data['data']):
                if not isinstance(datum, tuple):
                    continue
                if not datum[0] and datum[1]:
                    continue
                if datum[2] is not None:
                    #akas = filter(None, datum[2].split('::'))
                    if self._linkPrefix == '/title/tt':
                        # XXX (HTU): couldn't find a result with multiple akas
                        aka = datum[2]
                        akas = [aka[1:-1]]      # remove the quotes
                        #akas = [a.replace('" - ', '::').rstrip() for a in akas]
                        #akas = [a.replace('aka "', '', 1).replace('aka  "',
                                #'', 1).lstrip() for a in akas]
                    datum[1]['akas'] = akas
                    data['data'][idx] = (datum[0], datum[1])
                else:
                    data['data'][idx] = (datum[0], datum[1])
        return data

    def add_refs(self, data):
        return data


_OBJECTS = {
        'search_movie_parser': ((DOMHTMLSearchMovieParser,), None)
}


########NEW FILE########
__FILENAME__ = searchPersonParser
"""
parser.http.searchPersonParser module (imdb package).

This module provides the HTMLSearchPersonParser class (and the
search_person_parser instance), used to parse the results of a search
for a given person.
E.g., when searching for the name "Mel Gibson", the parsed page would be:
    http://akas.imdb.com/find?q=Mel+Gibson&nm=on&mx=20

Copyright 2004-2013 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
from imdb.utils import analyze_name, build_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser


def _cleanName(n):
    """Clean the name in a title tag."""
    if not n:
        return u''
    n = n.replace('Filmography by type for', '') # FIXME: temporary.
    return n

class DOMBasicPersonParser(DOMBasicMovieParser):
    """Simply get the name of a person and the imdbID.

    It's used by the DOMHTMLSearchPersonParser class to return a result
    for a direct match (when a search on IMDb results in a single
    person, the web server sends directly the movie page."""
    _titleFunct = lambda self, x: analyze_name(_cleanName(x), canonical=1)


_reAKASp = re.compile(r'(?:aka|birth name) (<em>")(.*?)"(<br>|<\/em>|<\/td>)',
                    re.I | re.M)

class DOMHTMLSearchPersonParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, for persons."""
    _BaseParser = DOMBasicPersonParser
    _notDirectHitTitle = '<title>find - imdb'
    _titleBuilder = lambda self, x: build_name(x, canonical=True)
    _linkPrefix = '/name/nm'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()",
                            'index': "./text()[1]",
                            'akas': ".//div[@class='_imdbpyAKA']/text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            analyze_name((x.get('name') or u'') + \
                                        (x.get('index') or u''),
                                         canonical=1), x.get('akas')
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[@class='result_text']/a[starts-with(@href, '/name/nm')]/..",
                            attrs=_attrs)]

    def preprocess_string(self, html_string):
        if self._notDirectHitTitle in html_string[:10240].lower():
            html_string = _reAKASp.sub(
                                    r'\1<div class="_imdbpyAKA">\2::</div>\3',
                                    html_string)
        return DOMHTMLSearchMovieParser.preprocess_string(self, html_string)


_OBJECTS = {
        'search_person_parser': ((DOMHTMLSearchPersonParser,),
                    {'kind': 'person', '_basic_parser': DOMBasicPersonParser})
}


########NEW FILE########
__FILENAME__ = topBottomParser
"""
parser.http.topBottomParser module (imdb package).

This module provides the classes (and the instances), used to parse the
lists of top 250 and bottom 100 movies.
E.g.:
    http://akas.imdb.com/chart/top
    http://akas.imdb.com/chart/bottom

Copyright 2009 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from imdb.utils import analyze_title
from utils import DOMParserBase, Attribute, Extractor, analyze_imdbid


class DOMHTMLTop250Parser(DOMParserBase):
    """Parser for the "top 250" page.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLTop250Parser()
        result = tparser.parse(top250_html_string)
    """
    label = 'top 250'
    ranktext = 'top 250 rank'

    def _init(self):
        self.extractors = [Extractor(label=self.label,
                        path="//div[@id='main']//table//tr",
                        attrs=Attribute(key=None,
                                multi=True,
                                path={self.ranktext: "./td[1]//text()",
                                        'rating': "./td[2]//text()",
                                        'title': "./td[3]//text()",
                                        'movieID': "./td[3]//a/@href",
                                        'votes': "./td[4]//text()"
                                        }))]

    def postprocess_data(self, data):
        if not data or self.label not in data:
            return []
        mlist = []
        data = data[self.label]
        # Avoid duplicates.  A real fix, using XPath, is auspicabile.
        # XXX: probably this is no more needed.
        seenIDs = []
        for d in data:
            if 'movieID' not in d: continue
            if self.ranktext not in d: continue
            if 'title' not in d: continue
            theID = analyze_imdbid(d['movieID'])
            if theID is None:
                continue
            theID = str(theID)
            if theID in seenIDs:
                continue
            seenIDs.append(theID)
            minfo = analyze_title(d['title'])
            try: minfo[self.ranktext] = int(d[self.ranktext].replace('.', ''))
            except: pass
            if 'votes' in d:
                try: minfo['votes'] = int(d['votes'].replace(',', ''))
                except: pass
            if 'rating' in d:
                try: minfo['rating'] = float(d['rating'])
                except: pass
            mlist.append((theID, minfo))
        return mlist


class DOMHTMLBottom100Parser(DOMHTMLTop250Parser):
    """Parser for the "bottom 100" page.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLBottom100Parser()
        result = tparser.parse(bottom100_html_string)
    """
    label = 'bottom 100'
    ranktext = 'bottom 100 rank'


_OBJECTS = {
    'top250_parser':  ((DOMHTMLTop250Parser,), None),
    'bottom100_parser':  ((DOMHTMLBottom100Parser,), None)
}


########NEW FILE########
__FILENAME__ = utils
"""
parser.http.utils module (imdb package).

This module provides miscellaneous utilities used by
the imdb.parser.http classes.

Copyright 2004-2012 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
import logging
import warnings

from imdb._exceptions import IMDbError

from imdb.utils import flatten, _Container
from imdb.Movie import Movie
from imdb.Person import Person
from imdb.Character import Character


# Year, imdbIndex and kind.
re_yearKind_index = re.compile(r'(\([0-9\?]{4}(?:/[IVXLCDM]+)?\)(?: \(mini\)| \(TV\)| \(V\)| \(VG\))?)')

# Match imdb ids in href tags
re_imdbid = re.compile(r'(title/tt|name/nm|character/ch|company/co)([0-9]+)')

def analyze_imdbid(href):
    """Return an imdbID from an URL."""
    if not href:
        return None
    match = re_imdbid.search(href)
    if not match:
        return None
    return str(match.group(2))


_modify_keys = list(Movie.keys_tomodify_list) + list(Person.keys_tomodify_list)
def _putRefs(d, re_titles, re_names, re_characters, lastKey=None):
    """Iterate over the strings inside list items or dictionary values,
    substitutes movie titles and person names with the (qv) references."""
    if isinstance(d, list):
        for i in xrange(len(d)):
            if isinstance(d[i], (unicode, str)):
                if lastKey in _modify_keys:
                    if re_names:
                        d[i] = re_names.sub(ur"'\1' (qv)", d[i])
                    if re_titles:
                        d[i] = re_titles.sub(ur'_\1_ (qv)', d[i])
                    if re_characters:
                        d[i] = re_characters.sub(ur'#\1# (qv)', d[i])
            elif isinstance(d[i], (list, dict)):
                _putRefs(d[i], re_titles, re_names, re_characters,
                        lastKey=lastKey)
    elif isinstance(d, dict):
        for k, v in d.items():
            lastKey = k
            if isinstance(v, (unicode, str)):
                if lastKey in _modify_keys:
                    if re_names:
                        d[k] = re_names.sub(ur"'\1' (qv)", v)
                    if re_titles:
                        d[k] = re_titles.sub(ur'_\1_ (qv)', v)
                    if re_characters:
                        d[k] = re_characters.sub(ur'#\1# (qv)', v)
            elif isinstance(v, (list, dict)):
                _putRefs(d[k], re_titles, re_names, re_characters,
                        lastKey=lastKey)


# Handle HTML/XML/SGML entities.
from htmlentitydefs import entitydefs
entitydefs = entitydefs.copy()
entitydefsget = entitydefs.get
entitydefs['nbsp'] = ' '

sgmlentity = {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': '\'', 'ndash': '-'}
sgmlentityget = sgmlentity.get
_sgmlentkeys = sgmlentity.keys()

entcharrefs = {}
entcharrefsget = entcharrefs.get
for _k, _v in entitydefs.items():
    if _k in _sgmlentkeys: continue
    if _v[0:2] == '&#':
        dec_code = _v[1:-1]
        _v = unichr(int(_v[2:-1]))
        entcharrefs[dec_code] = _v
    else:
        dec_code = '#' + str(ord(_v))
        _v = unicode(_v, 'latin_1', 'replace')
        entcharrefs[dec_code] = _v
    entcharrefs[_k] = _v
del _sgmlentkeys, _k, _v
entcharrefs['#160'] = u' '
entcharrefs['#xA0'] = u' '
entcharrefs['#xa0'] = u' '
entcharrefs['#XA0'] = u' '
entcharrefs['#x22'] = u'"'
entcharrefs['#X22'] = u'"'
# convert &x26; to &amp;, to make BeautifulSoup happy; beware that this
# leaves lone '&' in the html broken, but I assume this is better than
# the contrary...
entcharrefs['#38'] = u'&amp;'
entcharrefs['#x26'] = u'&amp;'
entcharrefs['#x26'] = u'&amp;'

re_entcharrefs = re.compile('&(%s|\#160|\#\d{1,5}|\#x[0-9a-f]{1,4});' %
                            '|'.join(map(re.escape, entcharrefs)), re.I)
re_entcharrefssub = re_entcharrefs.sub

sgmlentity.update(dict([('#34', u'"'), ('#38', u'&'),
                        ('#60', u'<'), ('#62', u'>'), ('#39', u"'")]))
re_sgmlref = re.compile('&(%s);' % '|'.join(map(re.escape, sgmlentity)))
re_sgmlrefsub = re_sgmlref.sub

# Matches XML-only single tags, like <br/> ; they are invalid in HTML,
# but widely used by IMDb web site. :-/
re_xmltags = re.compile('<([a-zA-Z]+)/>')


def _replXMLRef(match):
    """Replace the matched XML/HTML entities and references;
    replace everything except sgml entities like &lt;, &gt;, ..."""
    ref = match.group(1)
    value = entcharrefsget(ref)
    if value is None:
        if ref[0] == '#':
            ref_code = ref[1:]
            if ref_code in ('34', '38', '60', '62', '39'):
                return match.group(0)
            elif ref_code[0].lower() == 'x':
                #if ref[2:] == '26':
                #    # Don't convert &x26; to &amp;, to make BeautifulSoup happy.
                #    return '&amp;'
                return unichr(int(ref[2:], 16))
            else:
                return unichr(int(ref[1:]))
        else:
            return ref
    return value

def subXMLRefs(s):
    """Return the given html string with entity and char references
    replaced."""
    return re_entcharrefssub(_replXMLRef, s)

# XXX: no more used here; move it to mobile (they are imported by helpers, too)?
def _replSGMLRefs(match):
    """Replace the matched SGML entity."""
    ref = match.group(1)
    return sgmlentityget(ref, ref)

def subSGMLRefs(s):
    """Return the given html string with sgml entity and char references
    replaced."""
    return re_sgmlrefsub(_replSGMLRefs, s)


_b_p_logger = logging.getLogger('imdbpy.parser.http.build_person')
def build_person(txt, personID=None, billingPos=None,
                roleID=None, accessSystem='http', modFunct=None):
    """Return a Person instance from the tipical <tr>...</tr> strings
    found in the IMDb's web site."""
    #if personID is None
    #    _b_p_logger.debug('empty name or personID for "%s"', txt)
    notes = u''
    role = u''
    # Search the (optional) separator between name and role/notes.
    if txt.find('....') != -1:
        sep = '....'
    elif txt.find('...') != -1:
        sep = '...'
    else:
        sep = '...'
        # Replace the first parenthesis, assuming there are only
        # notes, after.
        # Rationale: no imdbIndex is (ever?) showed on the web site.
        txt = txt.replace('(', '...(', 1)
    txt_split = txt.split(sep, 1)
    name = txt_split[0].strip()
    if len(txt_split) == 2:
        role_comment = txt_split[1].strip()
        # Strip common endings.
        if role_comment[-4:] == ' and':
            role_comment = role_comment[:-4].rstrip()
        elif role_comment[-2:] == ' &':
            role_comment = role_comment[:-2].rstrip()
        elif role_comment[-6:] == '& ....':
            role_comment = role_comment[:-6].rstrip()
        # Get the notes.
        if roleID is not None:
            if not isinstance(roleID, list):
                cmt_idx = role_comment.find('(')
                if cmt_idx != -1:
                    role = role_comment[:cmt_idx].rstrip()
                    notes = role_comment[cmt_idx:]
                else:
                    # Just a role, without notes.
                    role = role_comment
            else:
                role = role_comment
        else:
            # We're managing something that doesn't have a 'role', so
            # everything are notes.
            notes = role_comment
    if role == '....': role = u''
    roleNotes = []
    # Manages multiple roleIDs.
    if isinstance(roleID, list):
        rolesplit = role.split('/')
        role = []
        for r in rolesplit:
            nidx = r.find('(')
            if nidx != -1:
                role.append(r[:nidx].rstrip())
                roleNotes.append(r[nidx:])
            else:
                role.append(r)
                roleNotes.append(None)
        lr = len(role)
        lrid = len(roleID)
        if lr > lrid:
            roleID += [None] * (lrid - lr)
        elif lr < lrid:
            roleID = roleID[:lr]
        for i, rid in enumerate(roleID):
            if rid is not None:
                roleID[i] = str(rid)
        if lr == 1:
            role = role[0]
            roleID = roleID[0]
            notes = roleNotes[0] or u''
    elif roleID is not None:
        roleID = str(roleID)
    if personID is not None:
        personID = str(personID)
    if (not name) or (personID is None):
        # Set to 'debug', since build_person is expected to receive some crap.
        _b_p_logger.debug('empty name or personID for "%s"', txt)
    # XXX: return None if something strange is detected?
    person = Person(name=name, personID=personID, currentRole=role,
                    roleID=roleID, notes=notes, billingPos=billingPos,
                    modFunct=modFunct, accessSystem=accessSystem)
    if roleNotes and len(roleNotes) == len(roleID):
        for idx, role in enumerate(person.currentRole):
            if roleNotes[idx]:
                role.notes = roleNotes[idx]
    return person


_re_chrIDs = re.compile('[0-9]{7}')

_b_m_logger = logging.getLogger('imdbpy.parser.http.build_movie')
# To shrink spaces.
re_spaces = re.compile(r'\s+')
def build_movie(txt, movieID=None, roleID=None, status=None,
                accessSystem='http', modFunct=None, _parsingCharacter=False,
                _parsingCompany=False, year=None, chrRoles=None,
                rolesNoChar=None, additionalNotes=None):
    """Given a string as normally seen on the "categorized" page of
    a person on the IMDb's web site, returns a Movie instance."""
    # FIXME: Oook, lets face it: build_movie and build_person are now
    # two horrible sets of patches to support the new IMDb design.  They
    # must be rewritten from scratch.
    if _parsingCharacter:
        _defSep = ' Played by '
    elif _parsingCompany:
        _defSep = ' ... '
    else:
        _defSep = ' .... '
    title = re_spaces.sub(' ', txt).strip()
    # Split the role/notes from the movie title.
    tsplit = title.split(_defSep, 1)
    role = u''
    notes = u''
    roleNotes = []
    if len(tsplit) == 2:
        title = tsplit[0].rstrip()
        role = tsplit[1].lstrip()
    if title[-9:] == 'TV Series':
        title = title[:-9].rstrip()
    #elif title[-7:] == '(short)':
    #    title = title[:-7].rstrip()
    #elif title[-11:] == '(TV series)':
    #    title = title[:-11].rstrip()
    #elif title[-10:] == '(TV movie)':
    #    title = title[:-10].rstrip()
    elif title[-14:] == 'TV mini-series':
        title = title[:-14] + ' (mini)'
    if title and title.endswith(_defSep.rstrip()):
        title = title[:-len(_defSep)+1]
    # Try to understand where the movie title ends.
    while True:
        if year:
            break
        if title[-1:] != ')':
            # Ignore the silly "TV Series" notice.
            if title[-9:] == 'TV Series':
                title = title[:-9].rstrip()
                continue
            else:
                # Just a title: stop here.
                break
        # Try to match paired parentheses; yes: sometimes there are
        # parentheses inside comments...
        nidx = title.rfind('(')
        while (nidx != -1 and \
                    title[nidx:].count('(') != title[nidx:].count(')')):
            nidx = title[:nidx].rfind('(')
        # Unbalanced parentheses: stop here.
        if nidx == -1: break
        # The last item in parentheses seems to be a year: stop here.
        first4 = title[nidx+1:nidx+5]
        if (first4.isdigit() or first4 == '????') and \
                title[nidx+5:nidx+6] in (')', '/'): break
        # The last item in parentheses is a known kind: stop here.
        if title[nidx+1:-1] in ('TV', 'V', 'mini', 'VG', 'TV movie',
                'TV series', 'short'): break
        # Else, in parentheses there are some notes.
        # XXX: should the notes in the role half be kept separated
        #      from the notes in the movie title half?
        if notes: notes = '%s %s' % (title[nidx:], notes)
        else: notes = title[nidx:]
        title = title[:nidx].rstrip()
    if year:
        year = year.strip()
        if title[-1:] == ')':
            fpIdx = title.rfind('(')
            if fpIdx != -1:
                if notes: notes = '%s %s' % (title[fpIdx:], notes)
                else: notes = title[fpIdx:]
                title = title[:fpIdx].rstrip()
        title = u'%s (%s)' % (title, year)
    if _parsingCharacter and roleID and not role:
        roleID = None
    if not roleID:
        roleID = None
    elif len(roleID) == 1:
        roleID = roleID[0]
    if not role and chrRoles and isinstance(roleID, (str, unicode)):
        roleID = _re_chrIDs.findall(roleID)
        role = ' / '.join(filter(None, chrRoles.split('@@')))
    # Manages multiple roleIDs.
    if isinstance(roleID, list):
        tmprole = role.split('/')
        role = []
        for r in tmprole:
            nidx = r.find('(')
            if nidx != -1:
                role.append(r[:nidx].rstrip())
                roleNotes.append(r[nidx:])
            else:
                role.append(r)
                roleNotes.append(None)
        lr = len(role)
        lrid = len(roleID)
        if lr > lrid:
            roleID += [None] * (lrid - lr)
        elif lr < lrid:
            roleID = roleID[:lr]
        for i, rid in enumerate(roleID):
            if rid is not None:
                roleID[i] = str(rid)
        if lr == 1:
            role = role[0]
            roleID = roleID[0]
    elif roleID is not None:
        roleID = str(roleID)
    if movieID is not None:
        movieID = str(movieID)
    if (not title) or (movieID is None):
        _b_m_logger.error('empty title or movieID for "%s"', txt)
    if rolesNoChar:
        rolesNoChar = filter(None, [x.strip() for x in rolesNoChar.split('/')])
        if not role:
            role = []
        elif not isinstance(role, list):
            role = [role]
        role += rolesNoChar
    notes = notes.strip()
    if additionalNotes:
        additionalNotes = re_spaces.sub(' ', additionalNotes).strip()
        if notes:
            notes += u' '
        notes += additionalNotes
    if role and isinstance(role, list) and notes.endswith(role[-1].replace('\n', ' ')):
        role = role[:-1]
    m = Movie(title=title, movieID=movieID, notes=notes, currentRole=role,
                roleID=roleID, roleIsPerson=_parsingCharacter,
                modFunct=modFunct, accessSystem=accessSystem)
    if roleNotes and len(roleNotes) == len(roleID):
        for idx, role in enumerate(m.currentRole):
            try:
                if roleNotes[idx]:
                    role.notes = roleNotes[idx]
            except IndexError:
                break
    # Status can't be checked here, and must be detected by the parser.
    if status:
        m['status'] = status
    return m


class DOMParserBase(object):
    """Base parser to handle HTML data from the IMDb's web server."""
    _defGetRefs = False
    _containsObjects = False

    preprocessors = []
    extractors = []
    usingModule = None

    _logger = logging.getLogger('imdbpy.parser.http.domparser')

    def __init__(self, useModule=None):
        """Initialize the parser. useModule can be used to force it
        to use 'BeautifulSoup' or 'lxml'; by default, it's auto-detected,
        using 'lxml' if available and falling back to 'BeautifulSoup'
        otherwise."""
        # Module to use.
        if useModule is None:
            useModule = ('lxml', 'BeautifulSoup')
        if not isinstance(useModule, (tuple, list)):
            useModule = [useModule]
        self._useModule = useModule
        nrMods = len(useModule)
        _gotError = False
        for idx, mod in enumerate(useModule):
            mod = mod.strip().lower()
            try:
                if mod == 'lxml':
                    from lxml.html import fromstring
                    from lxml.etree import tostring
                    self._is_xml_unicode = False
                    self.usingModule = 'lxml'
                elif mod == 'beautifulsoup':
                    from bsouplxml.html import fromstring
                    from bsouplxml.etree import tostring
                    self._is_xml_unicode = True
                    self.usingModule = 'beautifulsoup'
                else:
                    self._logger.warn('unknown module "%s"' % mod)
                    continue
                self.fromstring = fromstring
                self._tostring = tostring
                if _gotError:
                    warnings.warn('falling back to "%s"' % mod)
                break
            except ImportError, e:
                if idx+1 >= nrMods:
                    # Raise the exception, if we don't have any more
                    # options to try.
                    raise IMDbError('unable to use any parser in %s: %s' % \
                                    (str(useModule), str(e)))
                else:
                    warnings.warn('unable to use "%s": %s' % (mod, str(e)))
                    _gotError = True
                continue
        else:
            raise IMDbError('unable to use parsers in %s' % str(useModule))
        # Fall-back defaults.
        self._modFunct = None
        self._as = 'http'
        self._cname = self.__class__.__name__
        self._init()
        self.reset()

    def reset(self):
        """Reset the parser."""
        # Names and titles references.
        self._namesRefs = {}
        self._titlesRefs = {}
        self._charactersRefs = {}
        self._reset()

    def _init(self):
        """Subclasses can override this method, if needed."""
        pass

    def _reset(self):
        """Subclasses can override this method, if needed."""
        pass

    def parse(self, html_string, getRefs=None, **kwds):
        """Return the dictionary generated from the given html string;
        getRefs can be used to force the gathering of movies/persons/characters
        references."""
        self.reset()
        if getRefs is not None:
            self.getRefs = getRefs
        else:
            self.getRefs = self._defGetRefs
        # Useful only for the testsuite.
        if not isinstance(html_string, unicode):
            html_string = unicode(html_string, 'latin_1', 'replace')
        html_string = subXMLRefs(html_string)
        # Temporary fix: self.parse_dom must work even for empty strings.
        html_string = self.preprocess_string(html_string)
        html_string = html_string.strip()
        if self.usingModule == 'beautifulsoup':
            # tag attributes like title="&#x22;Family Guy&#x22;" will be
            # converted to title=""Family Guy"" and this confuses BeautifulSoup.
            html_string = html_string.replace('""', '"')
            # Browser-specific escapes create problems to BeautifulSoup.
            html_string = html_string.replace('<!--[if IE]>', '"')
            html_string = html_string.replace('<![endif]-->', '"')
        #print html_string.encode('utf8')
        if html_string:
            dom = self.get_dom(html_string)
            #print self.tostring(dom).encode('utf8')
            try:
                dom = self.preprocess_dom(dom)
            except Exception, e:
                self._logger.error('%s: caught exception preprocessing DOM',
                                    self._cname, exc_info=True)
            if self.getRefs:
                try:
                    self.gather_refs(dom)
                except Exception, e:
                    self._logger.warn('%s: unable to gather refs: %s',
                                    self._cname, exc_info=True)
            data = self.parse_dom(dom)
        else:
            data = {}
        try:
            data = self.postprocess_data(data)
        except Exception, e:
            self._logger.error('%s: caught exception postprocessing data',
                                self._cname, exc_info=True)
        if self._containsObjects:
            self.set_objects_params(data)
        data = self.add_refs(data)
        return data

    def _build_empty_dom(self):
        from bsouplxml import _bsoup
        return _bsoup.BeautifulSoup('')

    def get_dom(self, html_string):
        """Return a dom object, from the given string."""
        try:
            dom = self.fromstring(html_string)
            if dom is None:
                dom = self._build_empty_dom()
                self._logger.error('%s: using a fake empty DOM', self._cname)
            return dom
        except Exception, e:
            self._logger.error('%s: caught exception parsing DOM',
                                self._cname, exc_info=True)
            return self._build_empty_dom()

    def xpath(self, element, path):
        """Return elements matching the given XPath."""
        try:
            xpath_result = element.xpath(path)
            if self._is_xml_unicode:
                return xpath_result
            result = []
            for item in xpath_result:
                if isinstance(item, str):
                    item = unicode(item)
                result.append(item)
            return result
        except Exception, e:
            self._logger.error('%s: caught exception extracting XPath "%s"',
                                self._cname, path, exc_info=True)
            return []

    def tostring(self, element):
        """Convert the element to a string."""
        if isinstance(element, (unicode, str)):
            return unicode(element)
        else:
            try:
                return self._tostring(element, encoding=unicode)
            except Exception, e:
                self._logger.error('%s: unable to convert to string',
                                    self._cname, exc_info=True)
                return u''

    def clone(self, element):
        """Clone an element."""
        return self.fromstring(self.tostring(element))

    def preprocess_string(self, html_string):
        """Here we can modify the text, before it's parsed."""
        if not html_string:
            return html_string
        # Remove silly &nbsp;&raquo; and &ndash; chars.
        html_string = html_string.replace(u' \xbb', u'')
        html_string = html_string.replace(u'&ndash;', u'-')
        try:
            preprocessors = self.preprocessors
        except AttributeError:
            return html_string
        for src, sub in preprocessors:
            # re._pattern_type is present only since Python 2.5.
            if callable(getattr(src, 'sub', None)):
                html_string = src.sub(sub, html_string)
            elif isinstance(src, str):
                html_string = html_string.replace(src, sub)
            elif callable(src):
                try:
                    html_string = src(html_string)
                except Exception, e:
                    _msg = '%s: caught exception preprocessing html'
                    self._logger.error(_msg, self._cname, exc_info=True)
                    continue
        ##print html_string.encode('utf8')
        return html_string

    def gather_refs(self, dom):
        """Collect references."""
        grParser = GatherRefs(useModule=self._useModule)
        grParser._as = self._as
        grParser._modFunct = self._modFunct
        refs = grParser.parse_dom(dom)
        refs = grParser.postprocess_data(refs)
        self._namesRefs = refs['names refs']
        self._titlesRefs = refs['titles refs']
        self._charactersRefs = refs['characters refs']

    def preprocess_dom(self, dom):
        """Last chance to modify the dom, before the rules in self.extractors
        are applied by the parse_dom method."""
        return dom

    def parse_dom(self, dom):
        """Parse the given dom according to the rules specified
        in self.extractors."""
        result = {}
        for extractor in self.extractors:
            ##print extractor.label
            if extractor.group is None:
                elements = [(extractor.label, element)
                            for element in self.xpath(dom, extractor.path)]
            else:
                groups = self.xpath(dom, extractor.group)
                elements = []
                for group in groups:
                    group_key = self.xpath(group, extractor.group_key)
                    if not group_key: continue
                    group_key = group_key[0]
                    # XXX: always tries the conversion to unicode:
                    #      BeautifulSoup.NavigableString is a subclass
                    #      of unicode, and so it's never converted.
                    group_key = self.tostring(group_key)
                    normalizer = extractor.group_key_normalize
                    if normalizer is not None:
                        if callable(normalizer):
                            try:
                                group_key = normalizer(group_key)
                            except Exception, e:
                                _m = '%s: unable to apply group_key normalizer'
                                self._logger.error(_m, self._cname,
                                                    exc_info=True)
                    group_elements = self.xpath(group, extractor.path)
                    elements.extend([(group_key, element)
                                     for element in group_elements])
            for group_key, element in elements:
                for attr in extractor.attrs:
                    if isinstance(attr.path, dict):
                        data = {}
                        for field in attr.path.keys():
                            path = attr.path[field]
                            value = self.xpath(element, path)
                            if not value:
                                data[field] = None
                            else:
                                # XXX: use u'' , to join?
                                data[field] = ''.join(value)
                    else:
                        data = self.xpath(element, attr.path)
                        if not data:
                            data = None
                        else:
                            data = attr.joiner.join(data)
                    if not data:
                        continue
                    attr_postprocess = attr.postprocess
                    if callable(attr_postprocess):
                        try:
                            data = attr_postprocess(data)
                        except Exception, e:
                            _m = '%s: unable to apply attr postprocess'
                            self._logger.error(_m, self._cname, exc_info=True)
                    key = attr.key
                    if key is None:
                        key = group_key
                    elif key.startswith('.'):
                        # assuming this is an xpath
                        try:
                            key = self.xpath(element, key)[0]
                        except IndexError:
                            self._logger.error('%s: XPath returned no items',
                                                self._cname, exc_info=True)
                    elif key.startswith('self.'):
                        key = getattr(self, key[5:])
                    if attr.multi:
                        if key not in result:
                            result[key] = []
                        result[key].append(data)
                    else:
                        if isinstance(data, dict):
                            result.update(data)
                        else:
                            result[key] = data
        return result

    def postprocess_data(self, data):
        """Here we can modify the data."""
        return data

    def set_objects_params(self, data):
        """Set parameters of Movie/Person/... instances, since they are
        not always set in the parser's code."""
        for obj in flatten(data, yieldDictKeys=True, scalar=_Container):
            obj.accessSystem = self._as
            obj.modFunct = self._modFunct

    def add_refs(self, data):
        """Modify data according to the expected output."""
        if self.getRefs:
            titl_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._titlesRefs.keys()])
            if titl_re != ur'()': re_titles = re.compile(titl_re, re.U)
            else: re_titles = None
            nam_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._namesRefs.keys()])
            if nam_re != ur'()': re_names = re.compile(nam_re, re.U)
            else: re_names = None
            chr_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._charactersRefs.keys()])
            if chr_re != ur'()': re_characters = re.compile(chr_re, re.U)
            else: re_characters = None
            _putRefs(data, re_titles, re_names, re_characters)
        return {'data': data, 'titlesRefs': self._titlesRefs,
                'namesRefs': self._namesRefs,
                'charactersRefs': self._charactersRefs}


class Extractor(object):
    """Instruct the DOM parser about how to parse a document."""
    def __init__(self, label, path, attrs, group=None, group_key=None,
                 group_key_normalize=None):
        """Initialize an Extractor object, used to instruct the DOM parser
        about how to parse a document."""
        # rarely (never?) used, mostly for debugging purposes.
        self.label = label
        self.group = group
        if group_key is None:
            self.group_key = ".//text()"
        else:
            self.group_key = group_key
        self.group_key_normalize = group_key_normalize
        self.path = path
        # A list of attributes to fetch.
        if isinstance(attrs, Attribute):
            attrs = [attrs]
        self.attrs = attrs

    def __repr__(self):
        """String representation of an Extractor object."""
        r = '<Extractor id:%s (label=%s, path=%s, attrs=%s, group=%s, ' \
                'group_key=%s group_key_normalize=%s)>' % (id(self),
                        self.label, self.path, repr(self.attrs), self.group,
                        self.group_key, self.group_key_normalize)
        return r


class Attribute(object):
    """The attribute to consider, for a given node."""
    def __init__(self, key, multi=False, path=None, joiner=None,
                 postprocess=None):
        """Initialize an Attribute object, used to specify the
        attribute to consider, for a given node."""
        # The key under which information will be saved; can be a string or an
        # XPath. If None, the label of the containing extractor will be used.
        self.key = key
        self.multi = multi
        self.path = path
        if joiner is None:
            joiner = ''
        self.joiner = joiner
        # Post-process this set of information.
        self.postprocess = postprocess

    def __repr__(self):
        """String representation of an Attribute object."""
        r = '<Attribute id:%s (key=%s, multi=%s, path=%s, joiner=%s, ' \
                'postprocess=%s)>' % (id(self), self.key,
                        self.multi, repr(self.path),
                        self.joiner, repr(self.postprocess))
        return r


def _parse_ref(text, link, info):
    """Manage links to references."""
    if link.find('/title/tt') != -1:
        yearK = re_yearKind_index.match(info)
        if yearK and yearK.start() == 0:
            text += ' %s' % info[:yearK.end()]
    return (text.replace('\n', ' '), link)


class GatherRefs(DOMParserBase):
    """Parser used to gather references to movies, persons and characters."""
    _attrs = [Attribute(key=None, multi=True,
                        path={
                            'text': './text()',
                            'link': './@href',
                            'info': './following::text()[1]'
                            },
        postprocess=lambda x: _parse_ref(x.get('text') or u'', x.get('link') or '',
                                         (x.get('info') or u'').strip()))]
    extractors = [
        Extractor(label='names refs',
            path="//a[starts-with(@href, '/name/nm')][string-length(@href)=16]",
            attrs=_attrs),

        Extractor(label='titles refs',
            path="//a[starts-with(@href, '/title/tt')]" \
                    "[string-length(@href)=17]",
            attrs=_attrs),

        Extractor(label='characters refs',
            path="//a[starts-with(@href, '/character/ch')]" \
                    "[string-length(@href)=21]",
            attrs=_attrs),
            ]

    def postprocess_data(self, data):
        result = {}
        for item in ('names refs', 'titles refs', 'characters refs'):
            result[item] = {}
            for k, v in data.get(item, []):
                k = k.strip()
                v = v.strip()
                if not (k and v):
                    continue
                if not v.endswith('/'): continue
                imdbID = analyze_imdbid(v)
                if item == 'names refs':
                    obj = Person(personID=imdbID, name=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                elif item == 'titles refs':
                    obj = Movie(movieID=imdbID, title=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                else:
                    obj = Character(characterID=imdbID, name=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                # XXX: companies aren't handled: are they ever found in text,
                #      as links to their page?
                result[item][k] = obj
        return result

    def add_refs(self, data):
        return data



########NEW FILE########
__FILENAME__ = alchemyadapter
"""
parser.sql.alchemyadapter module (imdb.parser.sql package).

This module adapts the SQLAlchemy ORM to the internal mechanism.

Copyright 2008-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import re
import sys
import logging
from sqlalchemy import *
from sqlalchemy import schema
try: from sqlalchemy import exc # 0.5
except ImportError: from sqlalchemy import exceptions as exc # 0.4

_alchemy_logger = logging.getLogger('imdbpy.parser.sql.alchemy')

try:
    import migrate.changeset
    HAS_MC = True
except ImportError:
    HAS_MC = False
    _alchemy_logger.warn('Unable to import migrate.changeset: Foreign ' \
                         'Keys will not be created.')

from imdb._exceptions import IMDbDataAccessError
from dbschema import *

# Used to convert table and column names.
re_upper = re.compile(r'([A-Z])')

# XXX: I'm not sure at all that this is the best method to connect
#      to the database and bind that connection to every table.
metadata = MetaData()

# Maps our placeholders to SQLAlchemy's column types.
MAP_COLS = {
    INTCOL: Integer,
    UNICODECOL: UnicodeText,
    STRINGCOL: String
}


class NotFoundError(IMDbDataAccessError):
    """Exception raised when Table.get(id) returns no value."""
    pass


def _renameTable(tname):
    """Build the name of a table, as done by SQLObject."""
    tname = re_upper.sub(r'_\1', tname)
    if tname.startswith('_'):
        tname = tname[1:]
    return tname.lower()

def _renameColumn(cname):
    """Build the name of a column, as done by SQLObject."""
    cname = cname.replace('ID', 'Id')
    return _renameTable(cname)


class DNNameObj(object):
    """Used to access table.sqlmeta.columns[column].dbName (a string)."""
    def __init__(self, dbName):
        self.dbName = dbName

    def __repr__(self):
        return '<DNNameObj(dbName=%s) [id=%s]>' % (self.dbName, id(self))


class DNNameDict(object):
    """Used to access table.sqlmeta.columns (a dictionary)."""
    def __init__(self, colMap):
        self.colMap = colMap

    def __getitem__(self, key):
        return DNNameObj(self.colMap[key])

    def __repr__(self):
        return '<DNNameDict(colMap=%s) [id=%s]>' % (self.colMap, id(self))


class SQLMetaAdapter(object):
    """Used to access table.sqlmeta (an object with .table, .columns and
    .idName attributes)."""
    def __init__(self, table, colMap=None):
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def __getattr__(self, name):
        if name == 'table':
            return getattr(self.table, name)
        if name == 'columns':
            return DNNameDict(self.colMap)
        if name == 'idName':
            return self.colMap.get('id', 'id')
        return None

    def __repr__(self):
        return '<SQLMetaAdapter(table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.table), repr(self.colMap), id(self))


class QAdapter(object):
    """Used to access table.q attribute (remapped to SQLAlchemy table.c)."""
    def __init__(self, table, colMap=None):
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def __getattr__(self, name):
        try: return getattr(self.table.c, self.colMap[name])
        except KeyError, e: raise AttributeError("unable to get '%s'" % name)

    def __repr__(self):
        return '<QAdapter(table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.table), repr(self.colMap), id(self))


class RowAdapter(object):
    """Adapter for a SQLAlchemy RowProxy object."""
    def __init__(self, row, table, colMap=None):
        self.row = row
        # FIXME: it's OBSCENE that 'table' should be passed from
        #        TableAdapter through ResultAdapter only to land here,
        #        where it's used to directly update a row item.
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap
        self.colMapKeys = colMap.keys()

    def __getattr__(self, name):
        try: return getattr(self.row, self.colMap[name])
        except KeyError, e: raise AttributeError("unable to get '%s'" % name)

    def __setattr__(self, name, value):
        # FIXME: I can't even think about how much performances suffer,
        #        for this horrible hack (and it's used so rarely...)
        #        For sure something like a "property" to map column names
        #        to getter/setter functions would be much better, but it's
        #        not possible (or at least not easy) to build them for a
        #        single instance.
        if name in self.__dict__.get('colMapKeys', ()):
            # Trying to update a value in the database.
            row = self.__dict__['row']
            table = self.__dict__['table']
            colMap = self.__dict__['colMap']
            params = {colMap[name]: value}
            table.update(table.c.id==row.id).execute(**params)
            # XXX: minor bug: after a value is assigned with the
            #      'rowAdapterInstance.colName = value' syntax, for some
            #      reason rowAdapterInstance.colName still returns the
            #      previous value (even if the database is updated).
            #      Fix it?  I'm not even sure it's ever used.
            return
        # For every other attribute.
        object.__setattr__(self, name, value)

    def __repr__(self):
        return '<RowAdapter(row=%s, table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.row), repr(self.table), repr(self.colMap), id(self))


class ResultAdapter(object):
    """Adapter for a SQLAlchemy ResultProxy object."""
    def __init__(self, result, table, colMap=None):
        self.result = result
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def count(self):
        return len(self)

    def __len__(self):
        # FIXME: why sqlite returns -1? (that's wrooong!)
        if self.result.rowcount == -1:
            return 0
        return self.result.rowcount

    def __getitem__(self, key):
        res = list(self.result)[key]
        if not isinstance(key, slice):
            # A single item.
            return RowAdapter(res, self.table, colMap=self.colMap)
        else:
            # A (possible empty) list of items.
            return [RowAdapter(x, self.table, colMap=self.colMap)
                    for x in res]

    def __iter__(self):
        for item in self.result:
            yield RowAdapter(item, self.table, colMap=self.colMap)

    def __repr__(self):
        return '<ResultAdapter(result=%s, table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.result), repr(self.table),
                    repr(self.colMap), id(self))


class TableAdapter(object):
    """Adapter for a SQLAlchemy Table object, to mimic a SQLObject class."""
    def __init__(self, table, uri=None):
        """Initialize a TableAdapter object."""
        self._imdbpySchema = table
        self._imdbpyName = table.name
        self.connectionURI = uri
        self.colMap = {}
        columns = []
        for col in table.cols:
            # Column's paramters.
            params = {'nullable': True}
            params.update(col.params)
            if col.name == 'id':
                params['primary_key'] = True
            if 'notNone' in params:
                params['nullable'] = not params['notNone']
                del params['notNone']
            cname = _renameColumn(col.name)
            self.colMap[col.name] = cname
            colClass = MAP_COLS[col.kind]
            colKindParams = {}
            if 'length' in params:
                colKindParams['length'] = params['length']
                del params['length']
            elif colClass is UnicodeText and col.index:
                # XXX: limit length for UNICODECOLs that will have an index.
                #      this can result in name.name and title.title truncations!
                colClass = Unicode
                # Should work for most of the database servers.
                length = 511
                if self.connectionURI:
                    if self.connectionURI.startswith('mysql'):
                        # To stay compatible with MySQL 4.x.
                        length = 255
                colKindParams['length'] = length
            elif self._imdbpyName == 'PersonInfo' and col.name == 'info':
                if self.connectionURI:
                    if self.connectionURI.startswith('ibm'):
                        # There are some entries longer than 32KB.
                        colClass = CLOB
                        # I really do hope that this space isn't wasted
                        # for each other shorter entry... <g>
                        colKindParams['length'] = 68*1024
            colKind = colClass(**colKindParams)
            if 'alternateID' in params:
                # There's no need to handle them here.
                del params['alternateID']
            # Create a column.
            colObj = Column(cname, colKind, **params)
            columns.append(colObj)
        self.tableName = _renameTable(table.name)
        # Create the table.
        self.table = Table(self.tableName, metadata, *columns)
        self._ta_insert = self.table.insert()
        self._ta_select = self.table.select
        # Adapters for special attributes.
        self.q = QAdapter(self.table, colMap=self.colMap)
        self.sqlmeta = SQLMetaAdapter(self.table, colMap=self.colMap)

    def select(self, conditions=None):
        """Return a list of results."""
        result = self._ta_select(conditions).execute()
        return ResultAdapter(result, self.table, colMap=self.colMap)

    def get(self, theID):
        """Get an object given its ID."""
        result = self.select(self.table.c.id == theID)
        #if not result:
        #    raise NotFoundError, 'no data for ID %s' % theID
        # FIXME: isn't this a bit risky?  We can't check len(result),
        #        because sqlite returns -1...
        #        What about converting it to a list and getting the first item?
        try:
            return result[0]
        except KeyError:
            raise NotFoundError('no data for ID %s' % theID)

    def dropTable(self, checkfirst=True):
        """Drop the table."""
        dropParams = {'checkfirst': checkfirst}
        # Guess what?  Another work-around for a ibm_db bug.
        if self.table.bind.engine.url.drivername.startswith('ibm_db'):
            del dropParams['checkfirst']
        try:
            self.table.drop(**dropParams)
        except exc.ProgrammingError:
            # As above: re-raise the exception, but only if it's not ibm_db.
            if not self.table.bind.engine.url.drivername.startswith('ibm_db'):
                raise

    def createTable(self, checkfirst=True):
        """Create the table."""
        self.table.create(checkfirst=checkfirst)
        # Create indexes for alternateID columns (other indexes will be
        # created later, at explicit request for performances reasons).
        for col in self._imdbpySchema.cols:
            if col.name == 'id':
                continue
            if col.params.get('alternateID', False):
                self._createIndex(col, checkfirst=checkfirst)

    def _createIndex(self, col, checkfirst=True):
        """Create an index for a given (schema) column."""
        # XXX: indexLen is ignored in SQLAlchemy, and that means that
        #      indexes will be over the whole 255 chars strings...
        # NOTE: don't use a dot as a separator, or DB2 will do
        #       nasty things.
        idx_name = '%s_%s' % (self.table.name, col.index or col.name)
        if checkfirst:
            for index in self.table.indexes:
                if index.name == idx_name:
                    return
        idx = Index(idx_name, getattr(self.table.c, self.colMap[col.name]))
        # XXX: beware that exc.OperationalError can be raised, is some
        #      strange circumstances; that's why the index name doesn't
        #      follow the SQLObject convention, but includes the table name:
        #      sqlite, for example, expects index names to be unique at
        #      db-level.
        try:
            idx.create()
        except exc.OperationalError, e:
            _alchemy_logger.warn('Skipping creation of the %s.%s index: %s' %
                                (self.sqlmeta.table, col.name, e))

    def addIndexes(self, ifNotExists=True):
        """Create all required indexes."""
        for col in self._imdbpySchema.cols:
            if col.index:
                self._createIndex(col, checkfirst=ifNotExists)

    def addForeignKeys(self, mapTables, ifNotExists=True):
        """Create all required foreign keys."""
        if not HAS_MC:
            return
        # It seems that there's no reason to prevent the creation of
        # indexes for columns with FK constrains: if there's already
        # an index, the FK index is not created.
        countCols = 0
        for col in self._imdbpySchema.cols:
            countCols += 1
            if not col.foreignKey:
                continue
            fks = col.foreignKey.split('.', 1)
            foreignTableName = fks[0]
            if len(fks) == 2:
                foreignColName = fks[1]
            else:
                foreignColName = 'id'
            foreignColName = mapTables[foreignTableName].colMap.get(
                                                foreignColName, foreignColName)
            thisColName = self.colMap.get(col.name, col.name)
            thisCol = self.table.columns[thisColName]
            foreignTable = mapTables[foreignTableName].table
            foreignCol = getattr(foreignTable.c, foreignColName)
            # Need to explicitly set an unique name, otherwise it will
            # explode, if two cols points to the same table.
            fkName = 'fk_%s_%s_%d' % (foreignTable.name, foreignColName,
                                        countCols)
            constrain = migrate.changeset.ForeignKeyConstraint([thisCol],
                                                        [foreignCol],
                                                        name=fkName)
            try:
                constrain.create()
            except exc.OperationalError:
                continue

    def __call__(self, *args, **kwds):
        """To insert a new row with the syntax: TableClass(key=value, ...)"""
        taArgs = {}
        for key, value in kwds.items():
            taArgs[self.colMap.get(key, key)] = value
        self._ta_insert.execute(*args, **taArgs)

    def __repr__(self):
        return '<TableAdapter(table=%s) [id=%s]>' % (repr(self.table), id(self))


# Module-level "cache" for SQLObject classes, to prevent
# "Table 'tableName' is already defined for this MetaData instance" errors,
# when two or more connections to the database are made.
# XXX: is this the best way to act?
TABLES_REPOSITORY = {}

def getDBTables(uri=None):
    """Return a list of TableAdapter objects to be used to access the
    database through the SQLAlchemy ORM.  The connection uri is optional, and
    can be used to tailor the db schema to specific needs."""
    DB_TABLES = []
    for table in DB_SCHEMA:
        if table.name in TABLES_REPOSITORY:
            DB_TABLES.append(TABLES_REPOSITORY[table.name])
            continue
        tableAdapter = TableAdapter(table, uri)
        DB_TABLES.append(tableAdapter)
        TABLES_REPOSITORY[table.name] = tableAdapter
    return DB_TABLES


# Functions used to emulate SQLObject's logical operators.
def AND(*params):
    """Emulate SQLObject's AND."""
    return and_(*params)

def OR(*params):
    """Emulate SQLObject's OR."""
    return or_(*params)

def IN(item, inList):
    """Emulate SQLObject's IN."""
    if not isinstance(item, schema.Column):
        return OR(*[x == item for x in inList])
    else:
        return item.in_(inList)

def ISNULL(x):
    """Emulate SQLObject's ISNULL."""
    # XXX: Should we use null()?  Can null() be a global instance?
    # XXX: Is it safe to test None with the == operator, in this case?
    return x == None

def ISNOTNULL(x):
    """Emulate SQLObject's ISNOTNULL."""
    return x != None

def CONTAINSSTRING(expr, pattern):
    """Emulate SQLObject's CONTAINSSTRING."""
    return expr.like('%%%s%%' % pattern)


def toUTF8(s):
    """For some strange reason, sometimes SQLObject wants utf8 strings
    instead of unicode; with SQLAlchemy we just return the unicode text."""
    return s


class _AlchemyConnection(object):
    """A proxy for the connection object, required since _ConnectionFairy
    uses __slots__."""
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)


def setConnection(uri, tables, encoding='utf8', debug=False):
    """Set connection for every table."""
    params = {'encoding': encoding}
    # FIXME: why on earth MySQL requires an additional parameter,
    #        is well beyond my understanding...
    if uri.startswith('mysql'):
        if '?' in uri:
            uri += '&'
        else:
            uri += '?'
        uri += 'charset=%s' % encoding
        
        # On some server configurations, we will need to explictly enable
        # loading data from local files
        params['local_infile'] = 1
   
    if debug:
        params['echo'] = True
    if uri.startswith('ibm_db'):
        # Try to work-around a possible bug of the ibm_db DB2 driver.
        params['convert_unicode'] = True
    # XXX: is this the best way to connect?
    engine = create_engine(uri, **params)
    metadata.bind = engine
    eng_conn = engine.connect()
    if uri.startswith('sqlite'):
        major = sys.version_info[0]
        minor = sys.version_info[1]
        if major > 2 or (major == 2 and minor > 5):
            eng_conn.connection.connection.text_factory = str
    # XXX: OH MY, THAT'S A MESS!
    #      We need to return a "connection" object, with the .dbName
    #      attribute set to the db engine name (e.g. "mysql"), .paramstyle
    #      set to the style of the paramters for query() calls, and the
    #      .module attribute set to a module (?) with .OperationalError and
    #      .IntegrityError attributes.
    #      Another attribute of "connection" is the getConnection() function,
    #      used to return an object with a .cursor() method.
    connection = _AlchemyConnection(eng_conn.connection)
    paramstyle = eng_conn.dialect.paramstyle
    connection.module = eng_conn.dialect.dbapi
    connection.paramstyle = paramstyle
    connection.getConnection = lambda: connection.connection
    connection.dbName = engine.url.drivername
    return connection



########NEW FILE########
__FILENAME__ = dbschema
#-*- encoding: utf-8 -*-
"""
parser.sql.dbschema module (imdb.parser.sql package).

This module provides the schema used to describe the layout of the
database used by the imdb.parser.sql package; functions to create/drop
tables and indexes are also provided.

Copyright 2005-2012 Davide Alberani <da@erlug.linux.it>
               2006 Giuseppe "Cowo" Corbelli <cowo --> lugbs.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import logging

_dbschema_logger = logging.getLogger('imdbpy.parser.sql.dbschema')


# Placeholders for column types.
INTCOL = 1
UNICODECOL = 2
STRINGCOL = 3
_strMap = {1: 'INTCOL', 2: 'UNICODECOL', 3: 'STRINGCOL'}

class DBCol(object):
    """Define column objects."""
    def __init__(self, name, kind, **params):
        self.name = name
        self.kind = kind
        self.index = None
        self.indexLen = None
        # If not None, two notations are accepted: 'TableName'
        # and 'TableName.ColName'; in the first case, 'id' is assumed
        # as the name of the pointed column.
        self.foreignKey = None
        if 'index' in params:
            self.index = params['index']
            del params['index']
        if 'indexLen' in params:
            self.indexLen = params['indexLen']
            del params['indexLen']
        if 'foreignKey' in params:
            self.foreignKey = params['foreignKey']
            del params['foreignKey']
        self.params = params

    def __str__(self):
        """Class representation."""
        s = '<DBCol %s %s' % (self.name, _strMap[self.kind])
        if self.index:
            s += ' INDEX'
            if self.indexLen:
                s += '[:%d]' % self.indexLen
        if self.foreignKey:
            s += ' FOREIGN'
        if 'default' in self.params:
            val = self.params['default']
            if val is not None:
                val = '"%s"' % val
            s += ' DEFAULT=%s' % val
        for param in self.params:
            if param == 'default': continue
            s += ' %s' % param.upper()
        s += '>'
        return s

    def __repr__(self):
        """Class representation."""
        s = '<DBCol(name="%s", %s' % (self.name, _strMap[self.kind])
        if self.index:
            s += ', index="%s"' % self.index
        if self.indexLen:
             s += ', indexLen=%d' % self.indexLen
        if self.foreignKey:
            s += ', foreignKey="%s"' % self.foreignKey
        for param in self.params:
            val = self.params[param]
            if isinstance(val, (unicode, str)):
                val = u'"%s"' % val
            s += ', %s=%s' % (param, val)
        s += ')>'
        return s


class DBTable(object):
    """Define table objects."""
    def __init__(self, name, *cols, **kwds):
        self.name = name
        self.cols = cols
        # Default values.
        self.values = kwds.get('values', {})

    def __str__(self):
        """Class representation."""
        return '<DBTable %s (%d cols, %d values)>' % (self.name,
                len(self.cols), sum([len(v) for v in self.values.values()]))

    def __repr__(self):
        """Class representation."""
        s = '<DBTable(name="%s"' % self.name
        col_s = ', '.join([repr(col).rstrip('>').lstrip('<')
                            for col in self.cols])
        if col_s:
            s += ', %s' % col_s
        if self.values:
            s += ', values=%s' % self.values
        s += ')>'
        return s


# Default values to insert in some tables: {'column': (list, of, values, ...)}
kindTypeDefs = {'kind': ('movie', 'tv series', 'tv movie', 'video movie',
                        'tv mini series', 'video game', 'episode')}
companyTypeDefs = {'kind': ('distributors', 'production companies',
                        'special effects companies', 'miscellaneous companies')}
infoTypeDefs = {'info': ('runtimes', 'color info', 'genres', 'languages',
    'certificates', 'sound mix', 'tech info', 'countries', 'taglines',
    'keywords', 'alternate versions', 'crazy credits', 'goofs',
    'soundtrack', 'quotes', 'release dates', 'trivia', 'locations',
    'mini biography', 'birth notes', 'birth date', 'height',
    'death date', 'spouse', 'other works', 'birth name',
    'salary history', 'nick names', 'books', 'agent address',
    'biographical movies', 'portrayed in', 'where now', 'trade mark',
    'interviews', 'article', 'magazine cover photo', 'pictorial',
    'death notes', 'LD disc format', 'LD year', 'LD digital sound',
    'LD official retail price', 'LD frequency response', 'LD pressing plant',
    'LD length', 'LD language', 'LD review', 'LD spaciality', 'LD release date',
    'LD production country', 'LD contrast', 'LD color rendition',
    'LD picture format', 'LD video noise', 'LD video artifacts',
    'LD release country', 'LD sharpness', 'LD dynamic range',
    'LD audio noise', 'LD color information', 'LD group genre',
    'LD quality program', 'LD close captions-teletext-ld-g',
    'LD category', 'LD analog left', 'LD certification',
    'LD audio quality', 'LD video quality', 'LD aspect ratio',
    'LD analog right', 'LD additional information',
    'LD number of chapter stops', 'LD dialogue intellegibility',
    'LD disc size', 'LD master format', 'LD subtitles',
    'LD status of availablility', 'LD quality of source',
    'LD number of sides', 'LD video standard', 'LD supplement',
    'LD original title', 'LD sound encoding', 'LD number', 'LD label',
    'LD catalog number', 'LD laserdisc title', 'screenplay-teleplay',
    'novel', 'adaption', 'book', 'production process protocol',
    'printed media reviews', 'essays', 'other literature', 'mpaa',
    'plot', 'votes distribution', 'votes', 'rating',
    'production dates', 'copyright holder', 'filming dates', 'budget',
    'weekend gross', 'gross', 'opening weekend', 'rentals',
    'admissions', 'studios', 'top 250 rank', 'bottom 10 rank')}
compCastTypeDefs = {'kind': ('cast', 'crew', 'complete', 'complete+verified')}
linkTypeDefs = {'link': ('follows', 'followed by', 'remake of', 'remade as',
                        'references', 'referenced in', 'spoofs', 'spoofed in',
                        'features', 'featured in', 'spin off from', 'spin off',
                        'version of', 'similar to', 'edited into',
                        'edited from', 'alternate language version of',
                        'unknown link')}
roleTypeDefs = {'role': ('actor', 'actress', 'producer', 'writer',
                        'cinematographer', 'composer', 'costume designer',
                        'director', 'editor', 'miscellaneous crew',
                        'production designer', 'guest')}

# Schema of tables in our database.
# XXX: Foreign keys can be used to create constrains between tables,
#      but they create indexes in the database, and this
#      means poor performances at insert-time.
DB_SCHEMA = [
    DBTable('Name',
        # namePcodeCf is the soundex of the name in the canonical format.
        # namePcodeNf is the soundex of the name in the normal format, if
        # different from namePcodeCf.
        # surnamePcode is the soundex of the surname, if different from the
        # other two values.

        # The 'id' column is simply skipped by SQLObject (it's a default);
        # the alternateID attribute here will be ignored by SQLAlchemy.
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('name', UNICODECOL, notNone=True, index='idx_name', indexLen=6),
        DBCol('imdbIndex', UNICODECOL, length=12, default=None),
        DBCol('imdbID', INTCOL, default=None, index='idx_imdb_id'),
        DBCol('gender', STRINGCOL, length=1, default=None),
        DBCol('namePcodeCf', STRINGCOL, length=5, default=None,
                index='idx_pcodecf'),
        DBCol('namePcodeNf', STRINGCOL, length=5, default=None,
                index='idx_pcodenf'),
        DBCol('surnamePcode', STRINGCOL, length=5, default=None,
                index='idx_pcode'),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('CharName',
        # namePcodeNf is the soundex of the name in the normal format.
        # surnamePcode is the soundex of the surname, if different
        # from namePcodeNf.
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('name', UNICODECOL, notNone=True, index='idx_name', indexLen=6),
        DBCol('imdbIndex', UNICODECOL, length=12, default=None),
        DBCol('imdbID', INTCOL, default=None),
        DBCol('namePcodeNf', STRINGCOL, length=5, default=None,
                index='idx_pcodenf'),
        DBCol('surnamePcode', STRINGCOL, length=5, default=None,
                index='idx_pcode'),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('CompanyName',
        # namePcodeNf is the soundex of the name in the normal format.
        # namePcodeSf is the soundex of the name plus the country code.
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('name', UNICODECOL, notNone=True, index='idx_name', indexLen=6),
        DBCol('countryCode', UNICODECOL, length=255, default=None),
        DBCol('imdbID', INTCOL, default=None),
        DBCol('namePcodeNf', STRINGCOL, length=5, default=None,
                index='idx_pcodenf'),
        DBCol('namePcodeSf', STRINGCOL, length=5, default=None,
                index='idx_pcodesf'),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('KindType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('kind', STRINGCOL, length=15, default=None, alternateID=True),
        values=kindTypeDefs
    ),

    DBTable('Title',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('title', UNICODECOL, notNone=True,
                index='idx_title', indexLen=10),
        DBCol('imdbIndex', UNICODECOL, length=12, default=None),
        DBCol('kindID', INTCOL, notNone=True, foreignKey='KindType'),
        DBCol('productionYear', INTCOL, default=None),
        DBCol('imdbID', INTCOL, default=None, index="idx_imdb_id"),
        DBCol('phoneticCode', STRINGCOL, length=5, default=None,
                index='idx_pcode'),
        DBCol('episodeOfID', INTCOL, default=None, index='idx_epof',
                foreignKey='Title'),
        DBCol('seasonNr', INTCOL, default=None, index="idx_season_nr"),
        DBCol('episodeNr', INTCOL, default=None, index="idx_episode_nr"),
        # Maximum observed length is 44; 49 can store 5 comma-separated
        # year-year pairs.
        DBCol('seriesYears', STRINGCOL, length=49, default=None),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('CompanyType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('kind', STRINGCOL, length=32, default=None, alternateID=True),
        values=companyTypeDefs
    ),

    DBTable('AkaName',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('personID', INTCOL, notNone=True, index='idx_person',
                foreignKey='Name'),
        DBCol('name', UNICODECOL, notNone=True),
        DBCol('imdbIndex', UNICODECOL, length=12, default=None),
        DBCol('namePcodeCf',  STRINGCOL, length=5, default=None,
                index='idx_pcodecf'),
        DBCol('namePcodeNf',  STRINGCOL, length=5, default=None,
                index='idx_pcodenf'),
        DBCol('surnamePcode',  STRINGCOL, length=5, default=None,
                index='idx_pcode'),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('AkaTitle',
        # XXX: It's safer to set notNone to False, here.
        #      alias for akas are stored completely in the AkaTitle table;
        #      this means that episodes will set also a "tv series" alias name.
        #      Reading the aka-title.list file it looks like there are
        #      episode titles with aliases to different titles for both
        #      the episode and the series title, while for just the series
        #      there are no aliases.
        #      E.g.:
        #      aka title                                 original title
        # "Series, The" (2005) {The Episode}  "Other Title" (2005) {Other Title}
        # But there is no:
        # "Series, The" (2005)                "Other Title" (2005)
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_movieid',
                foreignKey='Title'),
        DBCol('title', UNICODECOL, notNone=True),
        DBCol('imdbIndex', UNICODECOL, length=12, default=None),
        DBCol('kindID', INTCOL, notNone=True, foreignKey='KindType'),
        DBCol('productionYear', INTCOL, default=None),
        DBCol('phoneticCode',  STRINGCOL, length=5, default=None,
                index='idx_pcode'),
        DBCol('episodeOfID', INTCOL, default=None, index='idx_epof',
                foreignKey='AkaTitle'),
        DBCol('seasonNr', INTCOL, default=None),
        DBCol('episodeNr', INTCOL, default=None),
        DBCol('note', UNICODECOL, default=None),
        DBCol('md5sum', STRINGCOL, length=32, default=None, index='idx_md5')
    ),

    DBTable('RoleType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('role', STRINGCOL, length=32, notNone=True, alternateID=True),
        values=roleTypeDefs
    ),

    DBTable('CastInfo',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('personID', INTCOL, notNone=True, index='idx_pid',
                foreignKey='Name'),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('personRoleID', INTCOL, default=None, index='idx_cid',
                foreignKey='CharName'),
        DBCol('note', UNICODECOL, default=None),
        DBCol('nrOrder', INTCOL, default=None),
        DBCol('roleID', INTCOL, notNone=True, foreignKey='RoleType')
    ),

    DBTable('CompCastType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('kind', STRINGCOL, length=32, notNone=True, alternateID=True),
        values=compCastTypeDefs
    ),

    DBTable('CompleteCast',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, index='idx_mid', foreignKey='Title'),
        DBCol('subjectID', INTCOL, notNone=True, foreignKey='CompCastType'),
        DBCol('statusID', INTCOL, notNone=True, foreignKey='CompCastType')
    ),

    DBTable('InfoType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('info', STRINGCOL, length=32, notNone=True, alternateID=True),
        values=infoTypeDefs
    ),

    DBTable('LinkType',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('link', STRINGCOL, length=32, notNone=True, alternateID=True),
        values=linkTypeDefs
    ),

    DBTable('Keyword',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        # XXX: can't use alternateID=True, because it would create
        #      a UNIQUE index; unfortunately (at least with a common
        #      collation like utf8_unicode_ci) MySQL will consider
        #      some different keywords identical - like
        #      "fiancÃ©e" and "fiancee".
        DBCol('keyword', UNICODECOL, notNone=True,
                index='idx_keyword', indexLen=5),
        DBCol('phoneticCode', STRINGCOL, length=5, default=None,
                index='idx_pcode')
    ),

    DBTable('MovieKeyword',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('keywordID', INTCOL, notNone=True, index='idx_keywordid',
                foreignKey='Keyword')
    ),

    DBTable('MovieLink',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('linkedMovieID', INTCOL, notNone=True, foreignKey='Title'),
        DBCol('linkTypeID', INTCOL, notNone=True, foreignKey='LinkType')
    ),

    DBTable('MovieInfo',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('infoTypeID', INTCOL, notNone=True, foreignKey='InfoType'),
        DBCol('info', UNICODECOL, notNone=True),
        DBCol('note', UNICODECOL, default=None)
    ),

    # This table is identical to MovieInfo, except that both 'infoTypeID'
    # and 'info' are indexed.
    DBTable('MovieInfoIdx',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('infoTypeID', INTCOL, notNone=True, index='idx_infotypeid',
                foreignKey='InfoType'),
        DBCol('info', UNICODECOL, notNone=True, index='idx_info', indexLen=10),
        DBCol('note', UNICODECOL, default=None)
    ),

    DBTable('MovieCompanies',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('movieID', INTCOL, notNone=True, index='idx_mid',
                foreignKey='Title'),
        DBCol('companyID', INTCOL, notNone=True, index='idx_cid',
                foreignKey='CompanyName'),
        DBCol('companyTypeID', INTCOL, notNone=True, foreignKey='CompanyType'),
        DBCol('note', UNICODECOL, default=None)
    ),

    DBTable('PersonInfo',
        DBCol('id', INTCOL, notNone=True, alternateID=True),
        DBCol('personID', INTCOL, notNone=True, index='idx_pid',
                foreignKey='Name'),
        DBCol('infoTypeID', INTCOL, notNone=True, foreignKey='InfoType'),
        DBCol('info', UNICODECOL, notNone=True),
        DBCol('note', UNICODECOL, default=None)
    )
]


# Functions to manage tables.
def dropTables(tables, ifExists=True):
    """Drop the tables."""
    # In reverse order (useful to avoid errors about foreign keys).
    DB_TABLES_DROP = list(tables)
    DB_TABLES_DROP.reverse()
    for table in DB_TABLES_DROP:
        _dbschema_logger.info('dropping table %s', table._imdbpyName)
        table.dropTable(ifExists)

def createTables(tables, ifNotExists=True):
    """Create the tables and insert default values."""
    for table in tables:
        # Create the table.
        _dbschema_logger.info('creating table %s', table._imdbpyName)
        table.createTable(ifNotExists)
        # Insert default values, if any.
        if table._imdbpySchema.values:
            _dbschema_logger.info('inserting values into table %s',
                                    table._imdbpyName)
            for key in table._imdbpySchema.values:
                for value in table._imdbpySchema.values[key]:
                    table(**{key: unicode(value)})

def createIndexes(tables, ifNotExists=True):
    """Create the indexes in the database.
    Return a list of errors, if any."""
    errors = []
    for table in tables:
        _dbschema_logger.info('creating indexes for table %s',
                                table._imdbpyName)
        try:
            table.addIndexes(ifNotExists)
        except Exception, e:
            errors.append(e)
            continue
    return errors

def createForeignKeys(tables, ifNotExists=True):
    """Create Foreign Keys.
    Return a list of errors, if any."""
    errors = []
    mapTables = {}
    for table in tables:
        mapTables[table._imdbpyName] = table
    for table in tables:
        _dbschema_logger.info('creating foreign keys for table %s',
                                table._imdbpyName)
        try:
            table.addForeignKeys(mapTables, ifNotExists)
        except Exception, e:
            errors.append(e)
            continue
    return errors


########NEW FILE########
__FILENAME__ = objectadapter
"""
parser.sql.objectadapter module (imdb.parser.sql package).

This module adapts the SQLObject ORM to the internal mechanism.

Copyright 2008-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
import logging

from sqlobject import *
from sqlobject.sqlbuilder import ISNULL, ISNOTNULL, AND, OR, IN, CONTAINSSTRING

from dbschema import *

_object_logger = logging.getLogger('imdbpy.parser.sql.object')


# Maps our placeholders to SQLAlchemy's column types.
MAP_COLS = {
        INTCOL: IntCol,
        UNICODECOL: UnicodeCol,
        STRINGCOL: StringCol
}


# Exception raised when Table.get(id) returns no value.
NotFoundError = SQLObjectNotFound


# class method to be added to the SQLObject class.
def addIndexes(cls, ifNotExists=True):
    """Create all required indexes."""
    for col in cls._imdbpySchema.cols:
        if col.index:
            idxName = col.index
            colToIdx = col.name
            if col.indexLen:
                colToIdx = {'column': col.name, 'length': col.indexLen}
            if idxName in [i.name for i in cls.sqlmeta.indexes]:
                # Check if the index is already present.
                continue
            idx = DatabaseIndex(colToIdx, name=idxName)
            cls.sqlmeta.addIndex(idx)
    try:
        cls.createIndexes(ifNotExists)
    except dberrors.OperationalError, e:
        _object_logger.warn('Skipping creation of the %s.%s index: %s' %
                            (cls.sqlmeta.table, col.name, e))
addIndexes = classmethod(addIndexes)


# Global repository for "fake" tables with Foreign Keys - need to
# prevent troubles if addForeignKeys is called more than one time.
FAKE_TABLES_REPOSITORY = {}

def _buildFakeFKTable(cls, fakeTableName):
    """Return a "fake" table, with foreign keys where needed."""
    countCols = 0
    attrs = {}
    for col in cls._imdbpySchema.cols:
        countCols += 1
        if col.name == 'id':
            continue
        if not col.foreignKey:
            # A non-foreign key column - add it as usual.
            attrs[col.name] = MAP_COLS[col.kind](**col.params)
            continue
        # XXX: Foreign Keys pointing to TableName.ColName not yet supported.
        thisColName = col.name
        if thisColName.endswith('ID'):
            thisColName = thisColName[:-2]

        fks = col.foreignKey.split('.', 1)
        foreignTableName = fks[0]
        if len(fks) == 2:
            foreignColName = fks[1]
        else:
            foreignColName = 'id'
        # Unused...
        #fkName = 'fk_%s_%s_%d' % (foreignTableName, foreignColName,
        #                        countCols)
        # Create a Foreign Key column, with the correct references.
        fk = ForeignKey(foreignTableName, name=thisColName, default=None)
        attrs[thisColName] = fk
    # Build a _NEW_ SQLObject subclass, with foreign keys, if needed.
    newcls = type(fakeTableName, (SQLObject,), attrs)
    return newcls

def addForeignKeys(cls, mapTables, ifNotExists=True):
    """Create all required foreign keys."""
    # Do not even try, if there are no FK, in this table.
    if not filter(None, [col.foreignKey for col in cls._imdbpySchema.cols]):
        return
    fakeTableName = 'myfaketable%s' % cls.sqlmeta.table
    if fakeTableName in FAKE_TABLES_REPOSITORY:
        newcls = FAKE_TABLES_REPOSITORY[fakeTableName]
    else:
        newcls = _buildFakeFKTable(cls, fakeTableName)
        FAKE_TABLES_REPOSITORY[fakeTableName] = newcls
    # Connect the class with foreign keys.
    newcls.setConnection(cls._connection)
    for col in cls._imdbpySchema.cols:
        if col.name == 'id':
            continue
        if not col.foreignKey:
            continue
        # Get the SQL that _WOULD BE_ run, if we had to create
        # this "fake" table.
        fkQuery = newcls._connection.createReferenceConstraint(newcls,
                                newcls.sqlmeta.columns[col.name])
        if not fkQuery:
            # Probably the db doesn't support foreign keys (SQLite).
            continue
        # Remove "myfaketable" to get references to _real_ tables.
        fkQuery = fkQuery.replace('myfaketable', '')
        # Execute the query.
        newcls._connection.query(fkQuery)
    # Disconnect it.
    newcls._connection.close()
addForeignKeys = classmethod(addForeignKeys)


# Module-level "cache" for SQLObject classes, to prevent
# "class TheClass is already in the registry" errors, when
# two or more connections to the database are made.
# XXX: is this the best way to act?
TABLES_REPOSITORY = {}

def getDBTables(uri=None):
    """Return a list of classes to be used to access the database
    through the SQLObject ORM.  The connection uri is optional, and
    can be used to tailor the db schema to specific needs."""
    DB_TABLES = []
    for table in DB_SCHEMA:
        if table.name in TABLES_REPOSITORY:
            DB_TABLES.append(TABLES_REPOSITORY[table.name])
            continue
        attrs = {'_imdbpyName': table.name, '_imdbpySchema': table,
                'addIndexes': addIndexes, 'addForeignKeys': addForeignKeys}
        for col in table.cols:
            if col.name == 'id':
                continue
            attrs[col.name] = MAP_COLS[col.kind](**col.params)
        # Create a subclass of SQLObject.
        # XXX: use a metaclass?  I can't see any advantage.
        cls = type(table.name, (SQLObject,), attrs)
        DB_TABLES.append(cls)
        TABLES_REPOSITORY[table.name] = cls
    return DB_TABLES


def toUTF8(s):
    """For some strange reason, sometimes SQLObject wants utf8 strings
    instead of unicode."""
    return s.encode('utf_8')


def setConnection(uri, tables, encoding='utf8', debug=False):
    """Set connection for every table."""
    kw = {}
    # FIXME: it's absolutely unclear what we should do to correctly
    #        support unicode in MySQL; with some versions of SQLObject,
    #        it seems that setting use_unicode=1 is the _wrong_ thing to do.
    _uriLower = uri.lower()
    if _uriLower.startswith('mysql'):
        kw['use_unicode'] = 1
        #kw['sqlobject_encoding'] = encoding
        kw['charset'] = encoding

        # On some server configurations, we will need to explictly enable
        # loading data from local files
        kw['local_infile'] = 1
    conn = connectionForURI(uri, **kw)
    conn.debug = debug
    # XXX: doesn't work and a work-around was put in imdbpy2sql.py;
    #      is there any way to modify the text_factory parameter of
    #      a SQLite connection?
    #if uri.startswith('sqlite'):
    #    major = sys.version_info[0]
    #    minor = sys.version_info[1]
    #    if major > 2 or (major == 2 and minor > 5):
    #        sqliteConn = conn.getConnection()
    #        sqliteConn.text_factory = str
    for table in tables:
        table.setConnection(conn)
        #table.sqlmeta.cacheValues = False
        # FIXME: is it safe to set table._cacheValue to False?  Looks like
        #        we can't retrieve correct values after an update (I think
        #        it's never needed, but...)  Anyway, these are set to False
        #        for performance reason at insert time (see imdbpy2sql.py).
        table._cacheValue = False
    # Required by imdbpy2sql.py.
    conn.paramstyle = conn.module.paramstyle
    return conn


########NEW FILE########
__FILENAME__ = Person
"""
Person module (imdb package).

This module provides the Person class, used to store information about
a given person.

Copyright 2004-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from copy import deepcopy

from imdb.utils import analyze_name, build_name, normalizeName, \
                        flatten, _Container, cmpPeople


class Person(_Container):
    """A Person.

    Every information about a person can be accessed as:
        personObject['information']
    to get a list of the kind of information stored in a
    Person object, use the keys() method; some useful aliases
    are defined (as "biography" for the "mini biography" key);
    see the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main', 'filmography', 'biography')

    # Aliases for some not-so-intuitive keys.
    keys_alias = {'biography': 'mini biography',
                  'bio': 'mini biography',
                  'aka': 'akas',
                  'also known as': 'akas',
                  'nick name': 'nick names',
                  'nicks': 'nick names',
                  'nickname': 'nick names',
                  'miscellaneouscrew': 'miscellaneous crew',
                  'crewmembers': 'miscellaneous crew',
                  'misc': 'miscellaneous crew',
                  'guest': 'notable tv guest appearances',
                  'guests': 'notable tv guest appearances',
                  'tv guest': 'notable tv guest appearances',
                  'guest appearances': 'notable tv guest appearances',
                  'spouses': 'spouse',
                  'salary': 'salary history',
                  'salaries': 'salary history',
                  'otherworks': 'other works',
                  "maltin's biography":
                        "biography from leonard maltin's movie encyclopedia",
                  "leonard maltin's biography":
                        "biography from leonard maltin's movie encyclopedia",
                  'real name': 'birth name',
                  'where are they now': 'where now',
                  'personal quotes': 'quotes',
                  'mini-biography author': 'imdb mini-biography by',
                  'biography author': 'imdb mini-biography by',
                  'genre': 'genres',
                  'portrayed': 'portrayed in',
                  'keys': 'keywords',
                  'trademarks': 'trade mark',
                  'trade mark': 'trade mark',
                  'trade marks': 'trade mark',
                  'trademark': 'trade mark',
                  'pictorials': 'pictorial',
                  'magazine covers': 'magazine cover photo',
                  'magazine-covers': 'magazine cover photo',
                  'tv series episodes': 'episodes',
                  'tv-series episodes': 'episodes',
                  'articles': 'article',
                  'keyword': 'keywords'}

    # 'nick names'???
    keys_tomodify_list = ('mini biography', 'spouse', 'quotes', 'other works',
                        'salary history', 'trivia', 'trade mark', 'news',
                        'books', 'biographical movies', 'portrayed in',
                        'where now', 'interviews', 'article',
                        "biography from leonard maltin's movie encyclopedia")

    cmpFunct = cmpPeople

    def _init(self, **kwds):
        """Initialize a Person object.

        *personID* -- the unique identifier for the person.
        *name* -- the name of the Person, if not in the data dictionary.
        *myName* -- the nickname you use for this person.
        *myID* -- your personal id for this person.
        *data* -- a dictionary used to initialize the object.
        *currentRole* -- a Character instance representing the current role
                         or duty of a person in this movie, or a Person
                         object representing the actor/actress who played
                         a given character in a Movie.  If a string is
                         passed, an object is automatically build.
        *roleID* -- if available, the characterID/personID of the currentRole
                    object.
        *roleIsPerson* -- when False (default) the currentRole is assumed
                          to be a Character object, otherwise a Person.
        *notes* -- notes about the given person for a specific movie
                    or role (e.g.: the alias used in the movie credits).
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *modFunct* -- function called returning text fields.
        *billingPos* -- position of this person in the credits list.
        """
        name = kwds.get('name')
        if name and not self.data.has_key('name'):
            self.set_name(name)
        self.personID = kwds.get('personID', None)
        self.myName = kwds.get('myName', u'')
        self.billingPos = kwds.get('billingPos', None)

    def _reset(self):
        """Reset the Person object."""
        self.personID = None
        self.myName = u''
        self.billingPos = None

    def _clear(self):
        """Reset the dictionary."""
        self.billingPos = None

    def set_name(self, name):
        """Set the name of the person."""
        # XXX: convert name to unicode, if it's a plain string?
        d = analyze_name(name, canonical=1)
        self.data.update(d)

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        addkeys = []
        if self.data.has_key('name'):
            addkeys += ['canonical name', 'long imdb name',
                        'long imdb canonical name']
        if self.data.has_key('headshot'):
            addkeys += ['full-size headshot']
        return addkeys

    def _getitem(self, key):
        """Handle special keys."""
        if self.data.has_key('name'):
            if key == 'name':
                return normalizeName(self.data['name'])
            elif key == 'canonical name':
                return self.data['name']
            elif key == 'long imdb name':
                return build_name(self.data, canonical=0)
            elif key == 'long imdb canonical name':
                return build_name(self.data)
        if key == 'full-size headshot' and self.data.has_key('headshot'):
            return self._re_fullsizeURL.sub('', self.data.get('headshot', ''))
        return None

    def getID(self):
        """Return the personID."""
        return self.personID

    def __nonzero__(self):
        """The Person is "false" if the self.data does not contain a name."""
        # XXX: check the name and the personID?
        if self.data.has_key('name'): return 1
        return 0

    def __contains__(self, item):
        """Return true if this Person has worked in the given Movie,
        or if the fiven Character was played by this Person."""
        from Movie import Movie
        from Character import Character
        if isinstance(item, Movie):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m):
                    return 1
        elif isinstance(item, Character):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m.currentRole):
                    return 1
        return 0

    def isSameName(self, other):
        """Return true if two persons have the same name and imdbIndex
        and/or personID.
        """
        if not isinstance(other, self.__class__):
            return 0
        if self.data.has_key('name') and \
                other.data.has_key('name') and \
                build_name(self.data, canonical=1) == \
                build_name(other.data, canonical=1):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.personID and self.personID == other.personID:
            return 1
        return 0
    isSamePerson = isSameName # XXX: just for backward compatiblity.

    def __deepcopy__(self, memo):
        """Return a deep copy of a Person instance."""
        p = Person(name=u'', personID=self.personID, myName=self.myName,
                    myID=self.myID, data=deepcopy(self.data, memo),
                    currentRole=deepcopy(self.currentRole, memo),
                    roleIsPerson=self._roleIsPerson,
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        p.current_info = list(self.current_info)
        p.set_mod_funct(self.modFunct)
        p.billingPos = self.billingPos
        return p

    def __repr__(self):
        """String representation of a Person object."""
        # XXX: add also currentRole and notes, if present?
        r = '<Person id:%s[%s] name:_%s_>' % (self.personID, self.accessSystem,
                                        self.get('long imdb canonical name'))
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short name."""
        return self.get('name', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('name', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the person."""
        if not self: return u''
        s = u'Person\n=====\nName: %s\n' % \
                                self.get('long imdb canonical name', u'')
        bdate = self.get('birth date')
        if bdate:
            s += u'Birth date: %s' % bdate
            bnotes = self.get('birth notes')
            if bnotes:
                s += u' (%s)' % bnotes
            s += u'.\n'
        ddate = self.get('death date')
        if ddate:
            s += u'Death date: %s' % ddate
            dnotes = self.get('death notes')
            if dnotes:
                s += u' (%s)' % dnotes
            s += u'.\n'
        bio = self.get('mini biography')
        if bio:
            s += u'Biography: %s\n' % bio[0]
        director = self.get('director')
        if director:
            d_list = [x.get('long imdb canonical title', u'')
                        for x in director[:3]]
            s += u'Last movies directed: %s.\n' % u'; '.join(d_list)
        act = self.get('actor') or self.get('actress')
        if act:
            a_list = [x.get('long imdb canonical title', u'')
                        for x in act[:5]]
            s += u'Last movies acted: %s.\n' % u'; '.join(a_list)
        return s



########NEW FILE########
__FILENAME__ = utils
"""
utils module (imdb package).

This module provides basic utilities for the imdb package.

Copyright 2004-2013 Davide Alberani <da@erlug.linux.it>
               2009 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import generators
import re
import string
import logging
from copy import copy, deepcopy
from time import strptime, strftime

from imdb import VERSION
from imdb import linguistics
from imdb._exceptions import IMDbParserError


# Logger for imdb.utils module.
_utils_logger = logging.getLogger('imdbpy.utils')

# The regular expression for the "long" year format of IMDb, like
# "(1998)" and "(1986/II)", where the optional roman number (that I call
# "imdbIndex" after the slash is used for movies with the same title
# and year of release.
# XXX: probably L, C, D and M are far too much! ;-)
re_year_index = re.compile(r'\(([0-9\?]{4}(/[IVXLCDM]+)?)\)')
re_extended_year_index = re.compile(r'\((TV episode|TV Series|TV mini-series|TV|Video|Video Game)? ?((?:[0-9\?]{4})(?:-[0-9\?]{4})?)(?:/([IVXLCDM]+)?)?\)')
re_remove_kind = re.compile(r'\((TV episode|TV Series|TV mini-series|TV|Video|Video Game)? ?')

# Match only the imdbIndex (for name strings).
re_index = re.compile(r'^\(([IVXLCDM]+)\)$')

# Match things inside parentheses.
re_parentheses = re.compile(r'(\(.*\))')

# Match the number of episodes.
re_episodes = re.compile('\s?\((\d+) episodes\)', re.I)
re_episode_info = re.compile(r'{\s*(.+?)?\s?(\([0-9\?]{4}-[0-9\?]{1,2}-[0-9\?]{1,2}\))?\s?(\(#[0-9]+\.[0-9]+\))?}')

# Common suffixes in surnames.
_sname_suffixes = ('de', 'la', 'der', 'den', 'del', 'y', 'da', 'van',
                    'e', 'von', 'the', 'di', 'du', 'el', 'al')

def canonicalName(name):
    """Return the given name in canonical "Surname, Name" format.
    It assumes that name is in the 'Name Surname' format."""
    # XXX: some statistics (as of 17 Apr 2008, over 2288622 names):
    #      - just a surname:                 69476
    #      - single surname, single name:  2209656
    #      - composed surname, composed name: 9490
    #      - composed surname, single name:  67606
    #        (2: 59764, 3: 6862, 4: 728)
    #      - single surname, composed name: 242310
    #        (2: 229467, 3: 9901, 4: 2041, 5: 630)
    #      - Jr.: 8025
    # Don't convert names already in the canonical format.
    if name.find(', ') != -1: return name
    if isinstance(name, unicode):
        joiner = u'%s, %s'
        sur_joiner = u'%s %s'
        sur_space = u' %s'
        space = u' '
    else:
        joiner = '%s, %s'
        sur_joiner = '%s %s'
        sur_space = ' %s'
        space = ' '
    sname = name.split(' ')
    snl = len(sname)
    if snl == 2:
        # Just a name and a surname: how boring...
        name = joiner % (sname[1], sname[0])
    elif snl > 2:
        lsname = [x.lower() for x in sname]
        if snl == 3: _indexes = (0, snl-2)
        else: _indexes = (0, snl-2, snl-3)
        # Check for common surname prefixes at the beginning and near the end.
        for index in _indexes:
            if lsname[index] not in _sname_suffixes: continue
            try:
                # Build the surname.
                surn = sur_joiner % (sname[index], sname[index+1])
                del sname[index]
                del sname[index]
                try:
                    # Handle the "Jr." after the name.
                    if lsname[index+2].startswith('jr'):
                        surn += sur_space % sname[index]
                        del sname[index]
                except (IndexError, ValueError):
                    pass
                name = joiner % (surn, space.join(sname))
                break
            except ValueError:
                continue
        else:
            name = joiner % (sname[-1], space.join(sname[:-1]))
    return name

def normalizeName(name):
    """Return a name in the normal "Name Surname" format."""
    if isinstance(name, unicode):
        joiner = u'%s %s'
    else:
        joiner = '%s %s'
    sname = name.split(', ')
    if len(sname) == 2:
        name = joiner % (sname[1], sname[0])
    return name

def analyze_name(name, canonical=None):
    """Return a dictionary with the name and the optional imdbIndex
    keys, from the given string.

    If canonical is None (default), the name is stored in its own style.
    If canonical is True, the name is converted to canonical style.
    If canonical is False, the name is converted to normal format.

    raise an IMDbParserError exception if the name is not valid.
    """
    original_n = name
    name = name.strip()
    res = {}
    imdbIndex = ''
    opi = name.rfind('(')
    cpi = name.rfind(')')
    # Strip  notes (but not if the name starts with a parenthesis).
    if opi not in (-1, 0) and cpi > opi:
        if re_index.match(name[opi:cpi+1]):
            imdbIndex = name[opi+1:cpi]
            name = name[:opi].rstrip()
        else:
            # XXX: for the birth and death dates case like " (1926-2004)"
            name = re_parentheses.sub('', name).strip()
    if not name:
        raise IMDbParserError('invalid name: "%s"' % original_n)
    if canonical is not None:
        if canonical:
            name = canonicalName(name)
        else:
            name = normalizeName(name)
    res['name'] = name
    if imdbIndex:
        res['imdbIndex'] = imdbIndex
    return res


def build_name(name_dict, canonical=None):
    """Given a dictionary that represents a "long" IMDb name,
    return a string.
    If canonical is None (default), the name is returned in the stored style.
    If canonical is True, the name is converted to canonical style.
    If canonical is False, the name is converted to normal format.
    """
    name = name_dict.get('canonical name') or name_dict.get('name', '')
    if not name: return ''
    if canonical is not None:
        if canonical:
            name = canonicalName(name)
        else:
            name = normalizeName(name)
    imdbIndex = name_dict.get('imdbIndex')
    if imdbIndex:
        name += ' (%s)' % imdbIndex
    return name


# XXX: here only for backward compatibility.  Find and remove any dependency.
_articles = linguistics.GENERIC_ARTICLES
_unicodeArticles = linguistics.toUnicode(_articles)
articlesDicts = linguistics.articlesDictsForLang(None)
spArticles = linguistics.spArticlesForLang(None)

def canonicalTitle(title, lang=None, imdbIndex=None):
    """Return the title in the canonic format 'Movie Title, The';
    beware that it doesn't handle long imdb titles.
    The 'lang' argument can be used to specify the language of the title.
    """
    isUnicode = isinstance(title, unicode)
    articlesDicts = linguistics.articlesDictsForLang(lang)
    try:
        if title.split(', ')[-1].lower() in articlesDicts[isUnicode]:
            return title
    except IndexError:
        pass
    if isUnicode:
        _format = u'%s%s, %s'
    else:
        _format = '%s%s, %s'
    ltitle = title.lower()
    if imdbIndex:
        imdbIndex = ' (%s)' % imdbIndex
    else:
        imdbIndex = ''
    spArticles = linguistics.spArticlesForLang(lang)
    for article in spArticles[isUnicode]:
        if ltitle.startswith(article):
            lart = len(article)
            title = _format % (title[lart:], imdbIndex, title[:lart])
            if article[-1] == ' ':
                title = title[:-1]
            break
    ## XXX: an attempt using a dictionary lookup.
    ##for artSeparator in (' ', "'", '-'):
    ##    article = _articlesDict.get(ltitle.split(artSeparator)[0])
    ##    if article is not None:
    ##        lart = len(article)
    ##        # check titles like "una", "I'm Mad" and "L'abbacchio".
    ##        if title[lart:] == '' or (artSeparator != ' ' and
    ##                                title[lart:][1] != artSeparator): continue
    ##        title = '%s, %s' % (title[lart:], title[:lart])
    ##        if artSeparator == ' ': title = title[1:]
    ##        break
    return title

def normalizeTitle(title, lang=None):
    """Return the title in the normal "The Title" format;
    beware that it doesn't handle long imdb titles, but only the
    title portion, without year[/imdbIndex] or special markup.
    The 'lang' argument can be used to specify the language of the title.
    """
    isUnicode = isinstance(title, unicode)
    stitle = title.split(', ')
    articlesDicts = linguistics.articlesDictsForLang(lang)
    if len(stitle) > 1 and stitle[-1].lower() in articlesDicts[isUnicode]:
        sep = ' '
        if stitle[-1][-1] in ("'", '-'):
            sep = ''
        if isUnicode:
            _format = u'%s%s%s'
            _joiner = u', '
        else:
            _format = '%s%s%s'
            _joiner = ', '
        title = _format % (stitle[-1], sep, _joiner.join(stitle[:-1]))
    return title


def _split_series_episode(title):
    """Return the series and the episode titles; if this is not a
    series' episode, the returned series title is empty.
    This function recognize two different styles:
        "The Series" An Episode (2005)
        "The Series" (2004) {An Episode (2005) (#season.episode)}"""
    series_title = ''
    episode_or_year = ''
    if title[-1:] == '}':
        # Title of the episode, as in the plain text data files.
        begin_eps = title.rfind('{')
        if begin_eps == -1: return '', ''
        series_title = title[:begin_eps].rstrip()
        # episode_or_year is returned with the {...}
        episode_or_year = title[begin_eps:].strip()
        if episode_or_year[:12] == '{SUSPENDED}}': return '', ''
    # XXX: works only with tv series; it's still unclear whether
    #      IMDb will support episodes for tv mini series and tv movies...
    elif title[0:1] == '"':
        second_quot = title[1:].find('"') + 2
        if second_quot != 1: # a second " was found.
            episode_or_year = title[second_quot:].lstrip()
            first_char = episode_or_year[0:1]
            if not first_char: return '', ''
            if first_char != '(':
                # There is not a (year) but the title of the episode;
                # that means this is an episode title, as returned by
                # the web server.
                series_title = title[:second_quot]
            ##elif episode_or_year[-1:] == '}':
            ##        # Title of the episode, as in the plain text data files.
            ##        begin_eps = episode_or_year.find('{')
            ##        if begin_eps == -1: return series_title, episode_or_year
            ##        series_title = title[:second_quot+begin_eps].rstrip()
            ##        # episode_or_year is returned with the {...}
            ##        episode_or_year = episode_or_year[begin_eps:]
    return series_title, episode_or_year


def is_series_episode(title):
    """Return True if 'title' is an series episode."""
    title = title.strip()
    if _split_series_episode(title)[0]: return 1
    return 0


def analyze_title(title, canonical=None, canonicalSeries=None,
                    canonicalEpisode=None, _emptyString=u''):
    """Analyze the given title and return a dictionary with the
    "stripped" title, the kind of the show ("movie", "tv series", etc.),
    the year of production and the optional imdbIndex (a roman number
    used to distinguish between movies with the same title and year).

    If canonical is None (default), the title is stored in its own style.
    If canonical is True, the title is converted to canonical style.
    If canonical is False, the title is converted to normal format.

    raise an IMDbParserError exception if the title is not valid.
    """
    # XXX: introduce the 'lang' argument?
    if canonical is not None:
        canonicalSeries = canonicalEpisode = canonical
    original_t = title
    result = {}
    title = title.strip()
    year = _emptyString
    kind = _emptyString
    imdbIndex = _emptyString
    series_title, episode_or_year = _split_series_episode(title)
    if series_title:
        # It's an episode of a series.
        series_d = analyze_title(series_title, canonical=canonicalSeries)
        oad = sen = ep_year = _emptyString
        # Plain text data files format.
        if episode_or_year[0:1] == '{' and episode_or_year[-1:] == '}':
            match = re_episode_info.findall(episode_or_year)
            if match:
                # Episode title, original air date and #season.episode
                episode_or_year, oad, sen = match[0]
                episode_or_year = episode_or_year.strip()
                if not oad:
                    # No year, but the title is something like (2005-04-12)
                    if episode_or_year and episode_or_year[0] == '(' and \
                                    episode_or_year[-1:] == ')' and \
                                    episode_or_year[1:2] != '#':
                        oad = episode_or_year
                        if oad[1:5] and oad[5:6] == '-':
                            try:
                                ep_year = int(oad[1:5])
                            except (TypeError, ValueError):
                                pass
                if not oad and not sen and episode_or_year.startswith('(#'):
                    sen = episode_or_year
        elif episode_or_year.startswith('Episode dated'):
            oad = episode_or_year[14:]
            if oad[-4:].isdigit():
                try:
                    ep_year = int(oad[-4:])
                except (TypeError, ValueError):
                    pass
        episode_d = analyze_title(episode_or_year, canonical=canonicalEpisode)
        episode_d['kind'] = u'episode'
        episode_d['episode of'] = series_d
        if oad:
            episode_d['original air date'] = oad[1:-1]
            if ep_year and episode_d.get('year') is None:
                episode_d['year'] = ep_year
        if sen and sen[2:-1].find('.') != -1:
            seas, epn = sen[2:-1].split('.')
            if seas:
                # Set season and episode.
                try: seas = int(seas)
                except: pass
                try: epn = int(epn)
                except: pass
                episode_d['season'] = seas
                if epn:
                    episode_d['episode'] = epn
        return episode_d
    # First of all, search for the kind of show.
    # XXX: Number of entries at 17 Apr 2008:
    #      movie:        379,871
    #      episode:      483,832
    #      tv movie:      61,119
    #      tv series:     44,795
    #      video movie:   57,915
    #      tv mini series: 5,497
    #      video game:     5,490
    #      More up-to-date statistics: http://us.imdb.com/database_statistics
    if title.endswith('(TV)'):
        kind = u'tv movie'
        title = title[:-4].rstrip()
    elif title.endswith('(TV Movie)'):
        kind = u'tv movie'
        title = title[:-10].rstrip()
    elif title.endswith('(V)'):
        kind = u'video movie'
        title = title[:-3].rstrip()
    elif title.lower().endswith('(video)'):
        kind = u'video movie'
        title = title[:-7].rstrip()
    elif title.endswith('(TV Short)'):
        kind = u'tv short'
        title = title[:-10].rstrip()
    elif title.endswith('(TV Mini-Series)'):
        kind = u'tv mini series'
        title = title[:-16].rstrip()
    elif title.endswith('(mini)'):
        kind = u'tv mini series'
        title = title[:-6].rstrip()
    elif title.endswith('(VG)'):
        kind = u'video game'
        title = title[:-4].rstrip()
    elif title.endswith('(Video Game)'):
        kind = u'video game'
        title = title[:-12].rstrip()
    elif title.endswith('(TV Series)'):
        epindex = title.find('(TV Episode) - ')
        if epindex >= 0:
            # It's an episode of a series.
            kind = u'episode'
            series_info = analyze_title(title[epindex + 15:])
            result['episode of'] = series_info.get('title')
            result['series year'] = series_info.get('year')
            title = title[:epindex]
        else:
            kind = u'tv series'
            title = title[:-11].rstrip()
    # Search for the year and the optional imdbIndex (a roman number).
    yi = re_year_index.findall(title)
    if not yi:
        yi = re_extended_year_index.findall(title)
        if yi:
            yk, yiy, yii = yi[-1]
            yi = [(yiy, yii)]
            if yk == 'TV episode':
                kind = u'episode'
            elif yk == 'TV':
                kind = u'tv movie'
            elif yk == 'TV Series':
                kind = u'tv series'
            elif yk == 'Video':
                kind = u'video movie'
            elif yk == 'TV mini-series':
                kind = u'tv mini series'
            elif yk == 'Video Game':
                kind = u'video game'
            title = re_remove_kind.sub('(', title)
    if yi:
        last_yi = yi[-1]
        year = last_yi[0]
        if last_yi[1]:
            imdbIndex = last_yi[1][1:]
            year = year[:-len(imdbIndex)-1]
        i = title.rfind('(%s)' % last_yi[0])
        if i != -1:
            title = title[:i-1].rstrip()
    # This is a tv (mini) series: strip the '"' at the begin and at the end.
    # XXX: strip('"') is not used for compatibility with Python 2.0.
    if title and title[0] == title[-1] == '"':
        if not kind:
            kind = u'tv series'
        title = title[1:-1].strip()
    if not title:
        raise IMDbParserError('invalid title: "%s"' % original_t)
    if canonical is not None:
        if canonical:
            title = canonicalTitle(title)
        else:
            title = normalizeTitle(title)
    # 'kind' is one in ('movie', 'episode', 'tv series', 'tv mini series',
    #                   'tv movie', 'video movie', 'video game')
    result['title'] = title
    result['kind'] = kind or u'movie'
    if year and year != '????':
        if '-' in year:
            result['series years'] = year
            year = year[:4]
        try:
            result['year'] = int(year)
        except (TypeError, ValueError):
            pass
    if imdbIndex:
        result['imdbIndex'] = imdbIndex
    if isinstance(_emptyString, str):
        result['kind'] = str(kind or 'movie')
    return result


_web_format = '%d %B %Y'
_ptdf_format = '(%Y-%m-%d)'
def _convertTime(title, fromPTDFtoWEB=1, _emptyString=u''):
    """Convert a time expressed in the pain text data files, to
    the 'Episode dated ...' format used on the web site; if
    fromPTDFtoWEB is false, the inverted conversion is applied."""
    try:
        if fromPTDFtoWEB:
            from_format = _ptdf_format
            to_format = _web_format
        else:
            from_format = u'Episode dated %s' % _web_format
            to_format = _ptdf_format
        t = strptime(title, from_format)
        title = strftime(to_format, t)
        if fromPTDFtoWEB:
            if title[0] == '0': title = title[1:]
            title = u'Episode dated %s' % title
    except ValueError:
        pass
    if isinstance(_emptyString, str):
        try:
            title = str(title)
        except UnicodeDecodeError:
            pass
    return title


def build_title(title_dict, canonical=None, canonicalSeries=None,
                canonicalEpisode=None, ptdf=0, lang=None, _doYear=1,
                _emptyString=u'', appendKind=True):
    """Given a dictionary that represents a "long" IMDb title,
    return a string.

    If canonical is None (default), the title is returned in the stored style.
    If canonical is True, the title is converted to canonical style.
    If canonical is False, the title is converted to normal format.

    lang can be used to specify the language of the title.

    If ptdf is true, the plain text data files format is used.
    """
    if canonical is not None:
        canonicalSeries = canonical
    pre_title = _emptyString
    kind = title_dict.get('kind')
    episode_of = title_dict.get('episode of')
    if kind == 'episode' and episode_of is not None:
        # Works with both Movie instances and plain dictionaries.
        doYear = 0
        if ptdf:
            doYear = 1
        # XXX: for results coming from the new search page.
        if not isinstance(episode_of, (dict, _Container)):
            episode_of = {'title': episode_of, 'kind': 'tv series'}
            if 'series year' in title_dict:
                episode_of['year'] = title_dict['series year']
        pre_title = build_title(episode_of, canonical=canonicalSeries,
                                ptdf=0, _doYear=doYear,
                                _emptyString=_emptyString)
        ep_dict = {'title': title_dict.get('title', ''),
                    'imdbIndex': title_dict.get('imdbIndex')}
        ep_title = ep_dict['title']
        if not ptdf:
            doYear = 1
            ep_dict['year'] = title_dict.get('year', '????')
            if ep_title[0:1] == '(' and ep_title[-1:] == ')' and \
                    ep_title[1:5].isdigit():
                ep_dict['title'] = _convertTime(ep_title, fromPTDFtoWEB=1,
                                                _emptyString=_emptyString)
        else:
            doYear = 0
            if ep_title.startswith('Episode dated'):
                ep_dict['title'] = _convertTime(ep_title, fromPTDFtoWEB=0,
                                                _emptyString=_emptyString)
        episode_title = build_title(ep_dict,
                            canonical=canonicalEpisode, ptdf=ptdf,
                            _doYear=doYear, _emptyString=_emptyString)
        if ptdf:
            oad = title_dict.get('original air date', _emptyString)
            if len(oad) == 10 and oad[4] == '-' and oad[7] == '-' and \
                        episode_title.find(oad) == -1:
                episode_title += ' (%s)' % oad
            seas = title_dict.get('season')
            if seas is not None:
                episode_title += ' (#%s' % seas
                episode = title_dict.get('episode')
                if episode is not None:
                    episode_title += '.%s' % episode
                episode_title += ')'
            episode_title = '{%s}' % episode_title
        return _emptyString + '%s %s' % (_emptyString + pre_title,
                            _emptyString + episode_title)
    title = title_dict.get('title', '')
    imdbIndex = title_dict.get('imdbIndex', '')
    if not title: return _emptyString
    if canonical is not None:
        if canonical:
            title = canonicalTitle(title, lang=lang, imdbIndex=imdbIndex)
        else:
            title = normalizeTitle(title, lang=lang)
    if pre_title:
        title = '%s %s' % (pre_title, title)
    if kind in (u'tv series', u'tv mini series'):
        title = '"%s"' % title
    if _doYear:
        year = title_dict.get('year') or '????'
        if isinstance(_emptyString, str):
            year = str(year)
        imdbIndex = title_dict.get('imdbIndex')
        if not ptdf:
            if imdbIndex and (canonical is None or canonical):
                title += ' (%s)' % imdbIndex
            title += ' (%s)' % year
        else:
            title += ' (%s' % year
            if imdbIndex and (canonical is None or canonical):
                title += '/%s' % imdbIndex
            title += ')'
    if appendKind and kind:
        if kind == 'tv movie':
            title += ' (TV)'
        elif kind == 'video movie':
            title += ' (V)'
        elif kind == 'tv mini series':
            title += ' (mini)'
        elif kind == 'video game':
            title += ' (VG)'
    return title


def split_company_name_notes(name):
    """Return two strings, the first representing the company name,
    and the other representing the (optional) notes."""
    name = name.strip()
    notes = u''
    if name.endswith(')'):
        fpidx = name.find('(')
        if fpidx != -1:
            notes = name[fpidx:]
            name = name[:fpidx].rstrip()
    return name, notes


def analyze_company_name(name, stripNotes=False):
    """Return a dictionary with the name and the optional 'country'
    keys, from the given string.
    If stripNotes is true, tries to not consider optional notes.

    raise an IMDbParserError exception if the name is not valid.
    """
    if stripNotes:
        name = split_company_name_notes(name)[0]
    o_name = name
    name = name.strip()
    country = None
    if name.endswith(']'):
        idx = name.rfind('[')
        if idx != -1:
            country = name[idx:]
            name = name[:idx].rstrip()
    if not name:
        raise IMDbParserError('invalid name: "%s"' % o_name)
    result = {'name': name}
    if country:
        result['country'] = country
    return result


def build_company_name(name_dict, _emptyString=u''):
    """Given a dictionary that represents a "long" IMDb company name,
    return a string.
    """
    name = name_dict.get('name')
    if not name:
        return _emptyString
    country = name_dict.get('country')
    if country is not None:
        name += ' %s' % country
    return name


class _LastC:
    """Size matters."""
    def __cmp__(self, other):
        if isinstance(other, self.__class__): return 0
        return 1

_last = _LastC()

def cmpMovies(m1, m2):
    """Compare two movies by year, in reverse order; the imdbIndex is checked
    for movies with the same year of production and title."""
    # Sort tv series' episodes.
    m1e = m1.get('episode of')
    m2e = m2.get('episode of')
    if m1e is not None and m2e is not None:
        cmp_series = cmpMovies(m1e, m2e)
        if cmp_series != 0:
            return cmp_series
        m1s = m1.get('season')
        m2s = m2.get('season')
        if m1s is not None and m2s is not None:
            if m1s < m2s:
                return 1
            elif m1s > m2s:
                return -1
            m1p = m1.get('episode')
            m2p = m2.get('episode')
            if m1p < m2p:
                return 1
            elif m1p > m2p:
                return -1
    try:
        if m1e is None: m1y = int(m1.get('year', 0))
        else: m1y = int(m1e.get('year', 0))
    except ValueError:
        m1y = 0
    try:
        if m2e is None: m2y = int(m2.get('year', 0))
        else: m2y = int(m2e.get('year', 0))
    except ValueError:
        m2y = 0
    if m1y > m2y: return -1
    if m1y < m2y: return 1
    # Ok, these movies have the same production year...
    #m1t = m1.get('canonical title', _last)
    #m2t = m2.get('canonical title', _last)
    # It should works also with normal dictionaries (returned from searches).
    #if m1t is _last and m2t is _last:
    m1t = m1.get('title', _last)
    m2t = m2.get('title', _last)
    if m1t < m2t: return -1
    if m1t > m2t: return 1
    # Ok, these movies have the same title...
    m1i = m1.get('imdbIndex', _last)
    m2i = m2.get('imdbIndex', _last)
    if m1i > m2i: return -1
    if m1i < m2i: return 1
    m1id = getattr(m1, 'movieID', None)
    # Introduce this check even for other comparisons functions?
    # XXX: is it safe to check without knowning the data access system?
    #      probably not a great idea.  Check for 'kind', instead?
    if m1id is not None:
        m2id = getattr(m2, 'movieID', None)
        if m1id > m2id: return -1
        elif m1id < m2id: return 1
    return 0


def cmpPeople(p1, p2):
    """Compare two people by billingPos, name and imdbIndex."""
    p1b = getattr(p1, 'billingPos', None) or _last
    p2b = getattr(p2, 'billingPos', None) or _last
    if p1b > p2b: return 1
    if p1b < p2b: return -1
    p1n = p1.get('canonical name', _last)
    p2n = p2.get('canonical name', _last)
    if p1n is _last and p2n is _last:
        p1n = p1.get('name', _last)
        p2n = p2.get('name', _last)
    if p1n > p2n: return 1
    if p1n < p2n: return -1
    p1i = p1.get('imdbIndex', _last)
    p2i = p2.get('imdbIndex', _last)
    if p1i > p2i: return 1
    if p1i < p2i: return -1
    return 0


def cmpCompanies(p1, p2):
    """Compare two companies."""
    p1n = p1.get('long imdb name', _last)
    p2n = p2.get('long imdb name', _last)
    if p1n is _last and p2n is _last:
        p1n = p1.get('name', _last)
        p2n = p2.get('name', _last)
    if p1n > p2n: return 1
    if p1n < p2n: return -1
    p1i = p1.get('country', _last)
    p2i = p2.get('country', _last)
    if p1i > p2i: return 1
    if p1i < p2i: return -1
    return 0


# References to titles, names and characters.
# XXX: find better regexp!
re_titleRef = re.compile(r'_(.+?(?: \([0-9\?]{4}(?:/[IVXLCDM]+)?\))?(?: \(mini\)| \(TV\)| \(V\)| \(VG\))?)_ \(qv\)')
# FIXME: doesn't match persons with ' in the name.
re_nameRef = re.compile(r"'([^']+?)' \(qv\)")
# XXX: good choice?  Are there characters with # in the name?
re_characterRef = re.compile(r"#([^']+?)# \(qv\)")

# Functions used to filter the text strings.
def modNull(s, titlesRefs, namesRefs, charactersRefs):
    """Do nothing."""
    return s

def modClearTitleRefs(s, titlesRefs, namesRefs, charactersRefs):
    """Remove titles references."""
    return re_titleRef.sub(r'\1', s)

def modClearNameRefs(s, titlesRefs, namesRefs, charactersRefs):
    """Remove names references."""
    return re_nameRef.sub(r'\1', s)

def modClearCharacterRefs(s, titlesRefs, namesRefs, charactersRefs):
    """Remove characters references"""
    return re_characterRef.sub(r'\1', s)

def modClearRefs(s, titlesRefs, namesRefs, charactersRefs):
    """Remove titles, names and characters references."""
    s = modClearTitleRefs(s, {}, {}, {})
    s = modClearCharacterRefs(s, {}, {}, {})
    return modClearNameRefs(s, {}, {}, {})


def modifyStrings(o, modFunct, titlesRefs, namesRefs, charactersRefs):
    """Modify a string (or string values in a dictionary or strings
    in a list), using the provided modFunct function and titlesRefs
    namesRefs and charactersRefs references dictionaries."""
    # Notice that it doesn't go any deeper than the first two levels in a list.
    if isinstance(o, (unicode, str)):
        return modFunct(o, titlesRefs, namesRefs, charactersRefs)
    elif isinstance(o, (list, tuple, dict)):
        _stillorig = 1
        if isinstance(o, (list, tuple)): keys = xrange(len(o))
        else: keys = o.keys()
        for i in keys:
            v = o[i]
            if isinstance(v, (unicode, str)):
                if _stillorig:
                    o = copy(o)
                    _stillorig = 0
                o[i] = modFunct(v, titlesRefs, namesRefs, charactersRefs)
            elif isinstance(v, (list, tuple)):
                modifyStrings(o[i], modFunct, titlesRefs, namesRefs,
                            charactersRefs)
    return o


def date_and_notes(s):
    """Parse (birth|death) date and notes; returns a tuple in the
    form (date, notes)."""
    s = s.strip()
    if not s: return (u'', u'')
    notes = u''
    if s[0].isdigit() or s.split()[0].lower() in ('c.', 'january', 'february',
                                                'march', 'april', 'may', 'june',
                                                'july', 'august', 'september',
                                                'october', 'november',
                                                'december', 'ca.', 'circa',
                                                '????,'):
        i = s.find(',')
        if i != -1:
            notes = s[i+1:].strip()
            s = s[:i]
    else:
        notes = s
        s = u''
    if s == '????': s = u''
    return s, notes


class RolesList(list):
    """A list of Person or Character instances, used for the currentRole
    property."""
    def __unicode__(self):
        return u' / '.join([unicode(x) for x in self])

    def __str__(self):
        # FIXME: does it make sense at all?  Return a unicode doesn't
        #        seem right, in __str__.
        return u' / '.join([unicode(x).encode('utf8') for x in self])


# Replace & with &amp;, but only if it's not already part of a charref.
#_re_amp = re.compile(r'(&)(?!\w+;)', re.I)
#_re_amp = re.compile(r'(?<=\W)&(?=[^a-zA-Z0-9_#])')
_re_amp = re.compile(r'&(?![^a-zA-Z0-9_#]{1,5};)')

def escape4xml(value):
    """Escape some chars that can't be present in a XML value."""
    if isinstance(value, int):
        value = str(value)
    value = _re_amp.sub('&amp;', value)
    value = value.replace('"', '&quot;').replace("'", '&apos;')
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    if isinstance(value, unicode):
        value = value.encode('ascii', 'xmlcharrefreplace')
    return value


def _refsToReplace(value, modFunct, titlesRefs, namesRefs, charactersRefs):
    """Return three lists - for movie titles, persons and characters names -
    with two items tuples: the first item is the reference once escaped
    by the user-provided modFunct function, the second is the same
    reference un-escaped."""
    mRefs = []
    for refRe, refTemplate in [(re_titleRef, u'_%s_ (qv)'),
                                (re_nameRef, u"'%s' (qv)"),
                                (re_characterRef, u'#%s# (qv)')]:
        theseRefs = []
        for theRef in refRe.findall(value):
            # refTemplate % theRef values don't change for a single
            # _Container instance, so this is a good candidate for a
            # cache or something - even if it's so rarely used that...
            # Moreover, it can grow - ia.update(...) - and change if
            # modFunct is modified.
            goodValue = modFunct(refTemplate % theRef, titlesRefs, namesRefs,
                                charactersRefs)
            # Prevents problems with crap in plain text data files.
            # We should probably exclude invalid chars and string that
            # are too long in the re_*Ref expressions.
            if '_' in goodValue or len(goodValue) > 128:
                continue
            toReplace = escape4xml(goodValue)
            # Only the 'value' portion is replaced.
            replaceWith = goodValue.replace(theRef, escape4xml(theRef))
            theseRefs.append((toReplace, replaceWith))
        mRefs.append(theseRefs)
    return mRefs


def _handleTextNotes(s):
    """Split text::notes strings."""
    ssplit = s.split('::', 1)
    if len(ssplit) == 1:
        return s
    return u'%s<notes>%s</notes>' % (ssplit[0], ssplit[1])


def _normalizeValue(value, withRefs=False, modFunct=None, titlesRefs=None,
                    namesRefs=None, charactersRefs=None):
    """Replace some chars that can't be present in a XML text."""
    # XXX: use s.encode(encoding, 'xmlcharrefreplace') ?  Probably not
    #      a great idea: after all, returning a unicode is safe.
    if isinstance(value, (unicode, str)):
        if not withRefs:
            value = _handleTextNotes(escape4xml(value))
        else:
            # Replace references that were accidentally escaped.
            replaceLists = _refsToReplace(value, modFunct, titlesRefs,
                                        namesRefs, charactersRefs)
            value = modFunct(value, titlesRefs or {}, namesRefs or {},
                            charactersRefs or {})
            value = _handleTextNotes(escape4xml(value))
            for replaceList in replaceLists:
                for toReplace, replaceWith in replaceList:
                    value = value.replace(toReplace, replaceWith)
    else:
        value = unicode(value)
    return value


def _tag4TON(ton, addAccessSystem=False, _containerOnly=False):
    """Build a tag for the given _Container instance;
    both open and close tags are returned."""
    tag = ton.__class__.__name__.lower()
    what = 'name'
    if tag == 'movie':
        value = ton.get('long imdb title') or ton.get('title', '')
        what = 'title'
    else:
        value = ton.get('long imdb name') or ton.get('name', '')
    value = _normalizeValue(value)
    extras = u''
    crl = ton.currentRole
    if crl:
        if not isinstance(crl, list):
            crl = [crl]
        for cr in crl:
            crTag = cr.__class__.__name__.lower()
            crValue = cr['long imdb name']
            crValue = _normalizeValue(crValue)
            crID = cr.getID()
            if crID is not None:
                extras += u'<current-role><%s id="%s">' \
                            u'<name>%s</name></%s>' % (crTag, crID,
                                                        crValue, crTag)
            else:
                extras += u'<current-role><%s><name>%s</name></%s>' % \
                               (crTag, crValue, crTag)
            if cr.notes:
                extras += u'<notes>%s</notes>' % _normalizeValue(cr.notes)
            extras += u'</current-role>'
    theID = ton.getID()
    if theID is not None:
        beginTag = u'<%s id="%s"' % (tag, theID)
        if addAccessSystem and ton.accessSystem:
            beginTag += ' access-system="%s"' % ton.accessSystem
        if not _containerOnly:
            beginTag += u'><%s>%s</%s>' % (what, value, what)
        else:
            beginTag += u'>'
    else:
        if not _containerOnly:
            beginTag = u'<%s><%s>%s</%s>' % (tag, what, value, what)
        else:
            beginTag = u'<%s>' % tag
    beginTag += extras
    if ton.notes:
        beginTag += u'<notes>%s</notes>' % _normalizeValue(ton.notes)
    return (beginTag, u'</%s>' % tag)


TAGS_TO_MODIFY = {
    'movie.parents-guide': ('item', True),
    'movie.number-of-votes': ('item', True),
    'movie.soundtrack.item': ('item', True),
    'movie.quotes': ('quote', False),
    'movie.quotes.quote': ('line', False),
    'movie.demographic': ('item', True),
    'movie.episodes': ('season', True),
    'movie.episodes.season': ('episode', True),
    'person.merchandising-links':  ('item', True),
    'person.genres':  ('item', True),
    'person.quotes':  ('quote', False),
    'person.keywords':  ('item', True),
    'character.quotes': ('item', True),
    'character.quotes.item': ('quote', False),
    'character.quotes.item.quote': ('line', False)
    }

_allchars = string.maketrans('', '')
_keepchars = _allchars.translate(_allchars, string.ascii_lowercase + '-' +
                                 string.digits)

def _tagAttr(key, fullpath):
    """Return a tuple with a tag name and a (possibly empty) attribute,
    applying the conversions specified in TAGS_TO_MODIFY and checking
    that the tag is safe for a XML document."""
    attrs = {}
    _escapedKey = escape4xml(key)
    if fullpath in TAGS_TO_MODIFY:
        tagName, useTitle = TAGS_TO_MODIFY[fullpath]
        if useTitle:
            attrs['key'] = _escapedKey
    elif not isinstance(key, unicode):
        if isinstance(key, str):
            tagName = unicode(key, 'ascii', 'ignore')
        else:
            strType = str(type(key)).replace("<type '", "").replace("'>", "")
            attrs['keytype'] = strType
            tagName = unicode(key)
    else:
        tagName = key
    if isinstance(key, int):
        attrs['keytype'] = 'int'
    origTagName = tagName
    tagName = tagName.lower().replace(' ', '-')
    tagName = str(tagName).translate(_allchars, _keepchars)
    if origTagName != tagName:
        if 'key' not in attrs:
            attrs['key'] = _escapedKey
    if (not tagName) or tagName[0].isdigit() or tagName[0] == '-':
        # This is a fail-safe: we should never be here, since unpredictable
        # keys must be listed in TAGS_TO_MODIFY.
        # This will proably break the DTD/schema, but at least it will
        # produce a valid XML.
        tagName = 'item'
        _utils_logger.error('invalid tag: %s [%s]' % (_escapedKey, fullpath))
        attrs['key'] = _escapedKey
    return tagName, u' '.join([u'%s="%s"' % i for i in attrs.items()])


def _seq2xml(seq, _l=None, withRefs=False, modFunct=None,
            titlesRefs=None, namesRefs=None, charactersRefs=None,
            _topLevel=True, key2infoset=None, fullpath=''):
    """Convert a sequence or a dictionary to a list of XML
    unicode strings."""
    if _l is None:
        _l = []
    if isinstance(seq, dict):
        for key in seq:
            value = seq[key]
            if isinstance(key, _Container):
                # Here we're assuming that a _Container is never a top-level
                # key (otherwise we should handle key2infoset).
                openTag, closeTag = _tag4TON(key)
                # So that fullpath will contains something meaningful.
                tagName = key.__class__.__name__.lower()
            else:
                tagName, attrs = _tagAttr(key, fullpath)
                openTag = u'<%s' % tagName
                if attrs:
                    openTag += ' %s' % attrs
                if _topLevel and key2infoset and key in key2infoset:
                    openTag += u' infoset="%s"' % key2infoset[key]
                if isinstance(value, int):
                    openTag += ' type="int"'
                elif isinstance(value, float):
                    openTag += ' type="float"'
                openTag += u'>'
                closeTag = u'</%s>' % tagName
            _l.append(openTag)
            _seq2xml(value, _l, withRefs, modFunct, titlesRefs,
                    namesRefs, charactersRefs, _topLevel=False,
                    fullpath='%s.%s' % (fullpath, tagName))
            _l.append(closeTag)
    elif isinstance(seq, (list, tuple)):
        tagName, attrs = _tagAttr('item', fullpath)
        beginTag = u'<%s' % tagName
        if attrs:
            beginTag += u' %s' % attrs
        #beginTag += u'>'
        closeTag = u'</%s>' % tagName
        for item in seq:
            if isinstance(item, _Container):
                _seq2xml(item, _l, withRefs, modFunct, titlesRefs,
                         namesRefs, charactersRefs, _topLevel=False,
                         fullpath='%s.%s' % (fullpath,
                                    item.__class__.__name__.lower()))
            else:
                openTag = beginTag
                if isinstance(item, int):
                    openTag += ' type="int"'
                elif isinstance(item, float):
                    openTag += ' type="float"'
                openTag += u'>'
                _l.append(openTag)
                _seq2xml(item, _l, withRefs, modFunct, titlesRefs,
                        namesRefs, charactersRefs, _topLevel=False,
                        fullpath='%s.%s' % (fullpath, tagName))
                _l.append(closeTag)
    else:
        if isinstance(seq, _Container):
            _l.extend(_tag4TON(seq))
        else:
            # Text, ints, floats and the like.
            _l.append(_normalizeValue(seq, withRefs=withRefs,
                                        modFunct=modFunct,
                                        titlesRefs=titlesRefs,
                                        namesRefs=namesRefs,
                                        charactersRefs=charactersRefs))
    return _l


_xmlHead = u"""<?xml version="1.0"?>
<!DOCTYPE %s SYSTEM "http://imdbpy.sf.net/dtd/imdbpy{VERSION}.dtd">

"""
_xmlHead = _xmlHead.replace('{VERSION}',
        VERSION.replace('.', '').split('dev')[0][:2])


class _Container(object):
    """Base class for Movie, Person, Character and Company classes."""
    # The default sets of information retrieved.
    default_info = ()

    # Aliases for some not-so-intuitive keys.
    keys_alias = {}

    # List of keys to modify.
    keys_tomodify_list = ()

    # Function used to compare two instances of this class.
    cmpFunct = None

    # Regular expression used to build the 'full-size (headshot|cover url)'.
    _re_fullsizeURL = re.compile(r'\._V1\._SX(\d+)_SY(\d+)_')

    def __init__(self, myID=None, data=None, notes=u'',
                currentRole=u'', roleID=None, roleIsPerson=False,
                accessSystem=None, titlesRefs=None, namesRefs=None,
                charactersRefs=None, modFunct=None, *args, **kwds):
        """Initialize a Movie, Person, Character or Company object.
        *myID* -- your personal identifier for this object.
        *data* -- a dictionary used to initialize the object.
        *notes* -- notes for the person referred in the currentRole
                    attribute; e.g.: '(voice)' or the alias used in the
                    movie credits.
        *accessSystem* -- a string representing the data access system used.
        *currentRole* -- a Character instance representing the current role
                         or duty of a person in this movie, or a Person
                         object representing the actor/actress who played
                         a given character in a Movie.  If a string is
                         passed, an object is automatically build.
        *roleID* -- if available, the characterID/personID of the currentRole
                    object.
        *roleIsPerson* -- when False (default) the currentRole is assumed
                          to be a Character object, otherwise a Person.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to characters.
        *modFunct* -- function called returning text fields.
        """
        self.reset()
        self.accessSystem = accessSystem
        self.myID = myID
        if data is None: data = {}
        self.set_data(data, override=1)
        self.notes = notes
        if titlesRefs is None: titlesRefs = {}
        self.update_titlesRefs(titlesRefs)
        if namesRefs is None: namesRefs = {}
        self.update_namesRefs(namesRefs)
        if charactersRefs is None: charactersRefs = {}
        self.update_charactersRefs(charactersRefs)
        self.set_mod_funct(modFunct)
        self.keys_tomodify = {}
        for item in self.keys_tomodify_list:
            self.keys_tomodify[item] = None
        self._roleIsPerson = roleIsPerson
        if not roleIsPerson:
            from imdb.Character import Character
            self._roleClass = Character
        else:
            from imdb.Person import Person
            self._roleClass = Person
        self.currentRole = currentRole
        if roleID:
            self.roleID = roleID
        self._init(*args, **kwds)

    def _get_roleID(self):
        """Return the characterID or personID of the currentRole object."""
        if not self.__role:
            return None
        if isinstance(self.__role, list):
            return [x.getID() for x in self.__role]
        return self.currentRole.getID()

    def _set_roleID(self, roleID):
        """Set the characterID or personID of the currentRole object."""
        if not self.__role:
            # XXX: needed?  Just ignore it?  It's probably safer to
            #      ignore it, to prevent some bugs in the parsers.
            #raise IMDbError,"Can't set ID of an empty Character/Person object."
            pass
        if not self._roleIsPerson:
            if not isinstance(roleID, (list, tuple)):
                self.currentRole.characterID = roleID
            else:
                for index, item in enumerate(roleID):
                    self.__role[index].characterID = item
        else:
            if not isinstance(roleID, (list, tuple)):
                self.currentRole.personID = roleID
            else:
                for index, item in enumerate(roleID):
                    self.__role[index].personID = item

    roleID = property(_get_roleID, _set_roleID,
                doc="the characterID or personID of the currentRole object.")

    def _get_currentRole(self):
        """Return a Character or Person instance."""
        if self.__role:
            return self.__role
        return self._roleClass(name=u'', accessSystem=self.accessSystem,
                                modFunct=self.modFunct)

    def _set_currentRole(self, role):
        """Set self.currentRole to a Character or Person instance."""
        if isinstance(role, (unicode, str)):
            if not role:
                self.__role = None
            else:
                self.__role = self._roleClass(name=role, modFunct=self.modFunct,
                                        accessSystem=self.accessSystem)
        elif isinstance(role, (list, tuple)):
            self.__role = RolesList()
            for item in role:
                if isinstance(item, (unicode, str)):
                    self.__role.append(self._roleClass(name=item,
                                        accessSystem=self.accessSystem,
                                        modFunct=self.modFunct))
                else:
                    self.__role.append(item)
            if not self.__role:
                self.__role = None
        else:
            self.__role = role

    currentRole = property(_get_currentRole, _set_currentRole,
                            doc="The role of a Person in a Movie" + \
                            " or the interpreter of a Character in a Movie.")

    def _init(self, **kwds): pass

    def reset(self):
        """Reset the object."""
        self.data = {}
        self.myID = None
        self.notes = u''
        self.titlesRefs = {}
        self.namesRefs = {}
        self.charactersRefs = {}
        self.modFunct = modClearRefs
        self.current_info = []
        self.infoset2keys = {}
        self.key2infoset = {}
        self.__role = None
        self._reset()

    def _reset(self): pass

    def clear(self):
        """Reset the dictionary."""
        self.data.clear()
        self.notes = u''
        self.titlesRefs = {}
        self.namesRefs = {}
        self.charactersRefs = {}
        self.current_info = []
        self.infoset2keys = {}
        self.key2infoset = {}
        self.__role = None
        self._clear()

    def _clear(self): pass

    def get_current_info(self):
        """Return the current set of information retrieved."""
        return self.current_info

    def update_infoset_map(self, infoset, keys, mainInfoset):
        """Update the mappings between infoset and keys."""
        if keys is None:
            keys = []
        if mainInfoset is not None:
            theIS = mainInfoset
        else:
            theIS = infoset
        self.infoset2keys[theIS] = keys
        for key in keys:
            self.key2infoset[key] = theIS

    def set_current_info(self, ci):
        """Set the current set of information retrieved."""
        # XXX:Remove? It's never used and there's no way to update infoset2keys.
        self.current_info = ci

    def add_to_current_info(self, val, keys=None, mainInfoset=None):
        """Add a set of information to the current list."""
        if val not in self.current_info:
            self.current_info.append(val)
            self.update_infoset_map(val, keys, mainInfoset)

    def has_current_info(self, val):
        """Return true if the given set of information is in the list."""
        return val in self.current_info

    def set_mod_funct(self, modFunct):
        """Set the fuction used to modify the strings."""
        if modFunct is None: modFunct = modClearRefs
        self.modFunct = modFunct

    def update_titlesRefs(self, titlesRefs):
        """Update the dictionary with the references to movies."""
        self.titlesRefs.update(titlesRefs)

    def get_titlesRefs(self):
        """Return the dictionary with the references to movies."""
        return self.titlesRefs

    def update_namesRefs(self, namesRefs):
        """Update the dictionary with the references to names."""
        self.namesRefs.update(namesRefs)

    def get_namesRefs(self):
        """Return the dictionary with the references to names."""
        return self.namesRefs

    def update_charactersRefs(self, charactersRefs):
        """Update the dictionary with the references to characters."""
        self.charactersRefs.update(charactersRefs)

    def get_charactersRefs(self):
        """Return the dictionary with the references to characters."""
        return self.charactersRefs

    def set_data(self, data, override=0):
        """Set the movie data to the given dictionary; if 'override' is
        set, the previous data is removed, otherwise the two dictionary
        are merged.
        """
        if not override:
            self.data.update(data)
        else:
            self.data = data

    def getID(self):
        """Return movieID, personID, characterID or companyID."""
        raise NotImplementedError('override this method')

    def __cmp__(self, other):
        """Compare two Movie, Person, Character or Company objects."""
        # XXX: raise an exception?
        if self.cmpFunct is None: return -1
        if not isinstance(other, self.__class__): return -1
        return self.cmpFunct(other)

    def __hash__(self):
        """Hash for this object."""
        # XXX: does it always work correctly?
        theID = self.getID()
        if theID is not None and self.accessSystem not in ('UNKNOWN', None):
            # Handle 'http' and 'mobile' as they are the same access system.
            acs = self.accessSystem
            if acs in ('mobile', 'httpThin'):
                acs = 'http'
            # There must be some indication of the kind of the object, too.
            s4h = '%s:%s[%s]' % (self.__class__.__name__, theID, acs)
        else:
            s4h = repr(self)
        return hash(s4h)

    def isSame(self, other):
        """Return True if the two represent the same object."""
        if not isinstance(other, self.__class__): return 0
        if hash(self) == hash(other): return 1
        return 0

    def __len__(self):
        """Number of items in the data dictionary."""
        return len(self.data)

    def getAsXML(self, key, _with_add_keys=True):
        """Return a XML representation of the specified key, or None
        if empty.  If _with_add_keys is False, dinamically generated
        keys are excluded."""
        # Prevent modifyStrings in __getitem__ to be called; if needed,
        # it will be called by the _normalizeValue function.
        origModFunct = self.modFunct
        self.modFunct = modNull
        # XXX: not totally sure it's a good idea, but could prevent
        #      problems (i.e.: the returned string always contains
        #      a DTD valid tag, and not something that can be only in
        #      the keys_alias map).
        key = self.keys_alias.get(key, key)
        if (not _with_add_keys) and  (key in self._additional_keys()):
            self.modFunct = origModFunct
            return None
        try:
            withRefs = False
            if key in self.keys_tomodify and \
                    origModFunct not in (None, modNull):
                withRefs = True
            value = self.get(key)
            if value is None:
                return None
            tag = self.__class__.__name__.lower()
            return u''.join(_seq2xml({key: value}, withRefs=withRefs,
                                        modFunct=origModFunct,
                                        titlesRefs=self.titlesRefs,
                                        namesRefs=self.namesRefs,
                                        charactersRefs=self.charactersRefs,
                                        key2infoset=self.key2infoset,
                                        fullpath=tag))
        finally:
            self.modFunct = origModFunct

    def asXML(self, _with_add_keys=True):
        """Return a XML representation of the whole object.
        If _with_add_keys is False, dinamically generated keys are excluded."""
        beginTag, endTag = _tag4TON(self, addAccessSystem=True,
                                    _containerOnly=True)
        resList = [beginTag]
        for key in self.keys():
            value = self.getAsXML(key, _with_add_keys=_with_add_keys)
            if not value:
                continue
            resList.append(value)
        resList.append(endTag)
        head = _xmlHead % self.__class__.__name__.lower()
        return head + u''.join(resList)

    def _getitem(self, key):
        """Handle special keys."""
        return None

    def __getitem__(self, key):
        """Return the value for a given key, checking key aliases;
        a KeyError exception is raised if the key is not found.
        """
        value = self._getitem(key)
        if value is not None: return value
        # Handle key aliases.
        key = self.keys_alias.get(key, key)
        rawData = self.data[key]
        if key in self.keys_tomodify and \
                self.modFunct not in (None, modNull):
            try:
                return modifyStrings(rawData, self.modFunct, self.titlesRefs,
                                    self.namesRefs, self.charactersRefs)
            except RuntimeError, e:
                # Symbian/python 2.2 has a poor regexp implementation.
                import warnings
                warnings.warn('RuntimeError in '
                        "imdb.utils._Container.__getitem__; if it's not "
                        "a recursion limit exceeded and we're not running "
                        "in a Symbian environment, it's a bug:\n%s" % e)
        return rawData

    def __setitem__(self, key, item):
        """Directly store the item with the given key."""
        self.data[key] = item

    def __delitem__(self, key):
        """Remove the given section or key."""
        # XXX: how to remove an item of a section?
        del self.data[key]

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        return []

    def keys(self):
        """Return a list of valid keys."""
        return self.data.keys() + self._additional_keys()

    def items(self):
        """Return the items in the dictionary."""
        return [(k, self.get(k)) for k in self.keys()]

    # XXX: is this enough?
    def iteritems(self): return self.data.iteritems()
    def iterkeys(self): return self.data.iterkeys()
    def itervalues(self): return self.data.itervalues()

    def values(self):
        """Return the values in the dictionary."""
        return [self.get(k) for k in self.keys()]

    def has_key(self, key):
        """Return true if a given section is defined."""
        try:
            self.__getitem__(key)
        except KeyError:
            return 0
        return 1

    # XXX: really useful???
    #      consider also that this will confuse people who meant to
    #      call ia.update(movieObject, 'data set') instead.
    def update(self, dict):
        self.data.update(dict)

    def get(self, key, failobj=None):
        """Return the given section, or default if it's not found."""
        try:
            return self.__getitem__(key)
        except KeyError:
            return failobj

    def setdefault(self, key, failobj=None):
        if not self.has_key(key):
            self[key] = failobj
        return self[key]

    def pop(self, key, *args):
        return self.data.pop(key, *args)

    def popitem(self):
        return self.data.popitem()

    def __repr__(self):
        """String representation of an object."""
        raise NotImplementedError('override this method')

    def __str__(self):
        """Movie title or person name."""
        raise NotImplementedError('override this method')

    def __contains__(self, key):
        raise NotImplementedError('override this method')

    def append_item(self, key, item):
        """The item is appended to the list identified by the given key."""
        self.data.setdefault(key, []).append(item)

    def set_item(self, key, item):
        """Directly store the item with the given key."""
        self.data[key] = item

    def __nonzero__(self):
        """Return true if self.data contains something."""
        if self.data: return 1
        return 0

    def __deepcopy__(self, memo):
        raise NotImplementedError('override this method')

    def copy(self):
        """Return a deep copy of the object itself."""
        return deepcopy(self)


def flatten(seq, toDescend=(list, dict, tuple), yieldDictKeys=0,
            onlyKeysType=(_Container,), scalar=None):
    """Iterate over nested lists and dictionaries; toDescend is a list
    or a tuple of types to be considered non-scalar; if yieldDictKeys is
    true, also dictionaries' keys are yielded; if scalar is not None, only
    items of the given type(s) are yielded."""
    if scalar is None or isinstance(seq, scalar):
        yield seq
    if isinstance(seq, toDescend):
        if isinstance(seq, (dict, _Container)):
            if yieldDictKeys:
                # Yield also the keys of the dictionary.
                for key in seq.iterkeys():
                    for k in flatten(key, toDescend=toDescend,
                                yieldDictKeys=yieldDictKeys,
                                onlyKeysType=onlyKeysType, scalar=scalar):
                        if onlyKeysType and isinstance(k, onlyKeysType):
                            yield k
            for value in seq.itervalues():
                for v in flatten(value, toDescend=toDescend,
                                yieldDictKeys=yieldDictKeys,
                                onlyKeysType=onlyKeysType, scalar=scalar):
                    yield v
        elif not isinstance(seq, (str, unicode, int, float)):
            for item in seq:
                for i in flatten(item, toDescend=toDescend,
                                yieldDictKeys=yieldDictKeys,
                                onlyKeysType=onlyKeysType, scalar=scalar):
                    yield i



########NEW FILE########
__FILENAME__ = _compat
"""
_compat module (imdb package).

This module provides compatibility functions used by the imdb package
to deal with unusual environments.

Copyright 2008-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

# TODO: now we're heavily using the 'logging' module, which was not
#       present in Python 2.2.  To work in a Symbian environment, we
#       need to create a fake 'logging' module (its functions may call
#       the 'warnings' module, or do nothing at all).


import os
# If true, we're working on a Symbian device.
if os.name == 'e32':
    # Replace os.path.expandvars and os.path.expanduser, if needed.
    def _noact(x):
        """Ad-hoc replacement for IMDbPY."""
        return x
    try:
        os.path.expandvars
    except AttributeError:
        os.path.expandvars = _noact
    try:
        os.path.expanduser
    except AttributeError:
        os.path.expanduser = _noact

    # time.strptime is missing, on Symbian devices.
    import time
    try:
        time.strptime
    except AttributeError:
        import re
        _re_web_time = re.compile(r'Episode dated (\d+) (\w+) (\d+)')
        _re_ptdf_time = re.compile(r'\((\d+)-(\d+)-(\d+)\)')
        _month2digit = {'January': '1', 'February': '2', 'March': '3',
                'April': '4', 'May': '5', 'June': '6', 'July': '7',
                'August': '8', 'September': '9', 'October': '10',
                'November': '11', 'December': '12'}
        def strptime(s, format):
            """Ad-hoc strptime replacement for IMDbPY."""
            try:
                if format.startswith('Episode'):
                    res = _re_web_time.findall(s)[0]
                    return (int(res[2]), int(_month2digit[res[1]]), int(res[0]),
                            0, 0, 0, 0, 1, 0)
                else:
                    res = _re_ptdf_time.findall(s)[0]
                    return (int(res[0]), int(res[1]), int(res[2]),
                            0, 0, 0, 0, 1, 0)
            except:
                raise ValueError('error in IMDbPY\'s ad-hoc strptime!')
        time.strptime = strptime


########NEW FILE########
__FILENAME__ = _exceptions
"""
_exceptions module (imdb package).

This module provides the exception hierarchy used by the imdb package.

Copyright 2004-2009 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import logging


class IMDbError(Exception):
    """Base class for every exception raised by the imdb package."""
    _logger = logging.getLogger('imdbpy')

    def __init__(self, *args, **kwargs):
        """Initialize the exception and pass the message to the log system."""
        # Every raised exception also dispatch a critical log.
        self._logger.critical('%s exception raised; args: %s; kwds: %s',
                                self.__class__.__name__, args, kwargs,
                                exc_info=True)
        Exception.__init__(self, *args, **kwargs)

class IMDbDataAccessError(IMDbError):
    """Exception raised when is not possible to access needed data."""
    pass

class IMDbParserError(IMDbError):
    """Exception raised when an error occurred parsing the data."""
    pass


########NEW FILE########
__FILENAME__ = _logging
"""
_logging module (imdb package).

This module provides the logging facilities used by the imdb package.

Copyright 2009-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import logging

LEVELS = {'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL}


imdbpyLogger = logging.getLogger('imdbpy')
imdbpyStreamHandler = logging.StreamHandler()
imdbpyFormatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]' \
                                    ' %(pathname)s:%(lineno)d: %(message)s')
imdbpyStreamHandler.setFormatter(imdbpyFormatter)
imdbpyLogger.addHandler(imdbpyStreamHandler)

def setLevel(level):
    """Set logging level for the main logger."""
    level = level.lower().strip()
    imdbpyLogger.setLevel(LEVELS.get(level, logging.NOTSET))
    imdbpyLogger.log(imdbpyLogger.level, 'set logging threshold to "%s"',
                    logging.getLevelName(imdbpyLogger.level))


#imdbpyLogger.setLevel(logging.DEBUG)


# It can be an idea to have a single function to log and warn:
#import warnings
#def log_and_warn(msg, args=None, logger=None, level=None):
#    """Log the message and issue a warning."""
#    if logger is None:
#        logger = imdbpyLogger
#    if level is None:
#        level = logging.WARNING
#    if args is None:
#        args = ()
#    #warnings.warn(msg % args, stacklevel=0)
#    logger.log(level, msg % args)


########NEW FILE########
