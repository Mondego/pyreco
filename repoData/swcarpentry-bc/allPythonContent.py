__FILENAME__ = gloss
#!/usr/bin/env python

'''
Check glossary entries.
Usage: gloss.py glossary_file html_file...
Typically, bin/gloss.py ./gloss.md _site/*/novice/*.html
'''

import sys
import re

def main(gloss_filename, html_filenames):
    '''Main driver.'''
    known = get_gloss_entries(gloss_filename)
    for f in html_filenames:
        report_missing(f, known)
    report_unused(known)

def get_gloss_entries(filename):
    '''Get entries from glossary, reporting any that are out of order or
    duplicated.  Result is a dictionary of anchors to counts
    (initially all 0).  Checks along the way that internal definitions
    resolve.'''

    # Entry pattern: 1 = key, 2 = term, optional 3 = abbrev
    p_entry = re.compile(r'\*\*<a\s+name="([^"]+)">(.+)</a>\*\*(\s+\((.+)\))?:')

    # Use pattern: 0 = key
    p_use = re.compile(r'\([^\)]+\)\[\#([^\]]+)\]')

    result = {}
    internal = set()
    undone = 0
    last_seen = ''
    out_of_order = []

    with open(filename, 'r') as reader:
        for line in reader:
            m = p_entry.search(line)
            if m:
                key = m.group(1)
                text = m.group(2)
                abbrev = m.group(3)
                if text.lower() < last_seen:
                    out_of_order.append(text)
                last_seen = text.lower()
                if key in result:
                    print 'Duplicate key {0} in {1}'.format(key, filename)
                result[key] = 0
            for ref in p_use.findall(line):
                internal.add(ref)

    if undone:
        print '{0} UNDONE'.format(undone)

    if out_of_order:
        print 'OUT OF ORDER:'
        for term in out_of_order:
            print '   ', term

    missing_internal = internal - set(result.keys())
    if missing_internal:
        print 'MISSING (INTERNAL):'
        for term in sorted(missing_internal):
            print '   ', term

    return result

def report_missing(f, known):
    '''Read HTML files to find glossary definitions not in the glossary
    file.  Counts the number of times each term used so that unused
    glossary entries can be reported.'''

    # Use pattern: 0 == upward ref to glossary file, 1 == key
    p_use = re.compile(r'<a href="(\.\./)*gloss.html#([^"]+)">')

    with open(f, 'r') as reader:
        unknown = set()
        for line in reader:
            matches = p_use.findall(line)
            for (prefix, m) in matches:
                if m in known:
                    known[m] += 1
                else:
                    unknown.add(m)
        if unknown:
            print 'UNDEFINED FROM {0}'.format(f)
            for term in sorted(unknown):
                print '   ', term

def report_unused(known):
    '''Report unused glossary entries.'''
    temp = [k for k in known if not known[k]]
    if not temp:
        return
    print 'UNUSED'
    for term in sorted(temp):
        print '   ', term

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])

########NEW FILE########
__FILENAME__ = make-book
from __future__ import print_function
import sys
import os.path

# Header required to make this a Jekyll file.
HEADER = '''---
layout: book
root: .
---'''

def main():
    print(HEADER)
    for filename in sys.argv[1:]:
        with open(filename, 'r') as reader:
            lines = reader.readlines()

        title = None
        if lines[0].startswith('---'):
            lines, skipped = skip(filename, lines, '---', '---')
            title = extract_title(filename, skipped)

        lines, _ = skip(filename, lines, '<div class="toc"', '</div>')

        lines = fix_image_paths(filename, lines)
        lines = fix_gloss(filename, lines)

        if title:
            print(format_title(filename, title))
        for line in lines:
            print(line.rstrip())

        print()

def skip(filename, lines, open, close):
    '''Skip a block of lines starting with open and ending with close.'''
    i_open = None
    i_close = None
    for (i, ln) in enumerate(lines):
        if (i_open is None) and ln.startswith(open):
            i_open = i
        elif (i_open is not None) and ln.startswith(close):
            i_close = i
            return lines[:i_open] + lines[i_close+1:], lines[i_open:i_close]
    else:
        return lines, None

def fix_image_paths(filename, lines):
    '''Modify image paths to include directory.'''
    front, _ = os.path.split(filename)
    front = front.replace('cached/', '')
    src = '<img src="'
    dst = '<img src="{0}/'.format(front)
    for (i, ln) in enumerate(lines):
        lines[i] = ln.replace(src, dst)
    return lines

def fix_gloss(filename, lines):
    '''Fix up glossary entries.'''
    is_glossary = 'gloss.md' in filename
    for (i, ln) in enumerate(lines):
        lines[i] = ln.replace('href="../../gloss.html#', 'href="#g:')
        if is_glossary:
            lines[i] = ln.replace('](#', '](#g:').replace('<a name="', '<a name="g:')
    return lines

def extract_title(filename, lines):
    '''Extract title from YAML header.'''
    for ln in lines:
        if ln.startswith('title:'):
            return ln.split(':', 1)[1].strip()
    return None

def format_title(filename, title):
    title = '## {0}'.format(title)
    f = os.path.split(filename)[-1]
    if f in ('index.md', 'intro.md'):
        return '\n'.join(['<div class="chapter" markdown="1">', title, '</div>'])
    else:
        return title

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = swc_index_validator
#!/usr/bin/env python

'''Test script to check whether index.html is valid.

Prints out warnings and errors when the header in index.html is malformed,
or when the information for 

Checks for:
    1. There should be the right number of categories
    2. Categories are allowed to appear only once
    3. Contact email should be valid (letters + @ + letters + . + letters)
    4. Latitute/longitude should be 2 floating point numbers separated by comma
    5. startdate should be a valid date; if enddate is present, it should be valid as well
    6. country should be a string with no spaces
    7. instructor and helper lists should be valid Python/Ruby lists
    8. Template header should not exist
    9. humandate should have three-letter month and four-letter year
    10. layout should be 'bootcamp'
    11. root must be '.'
    12. humantime should have 'am' or 'pm' or both
    13. address, venue should be non-empty
    14. registration should be 'open' or 'restricted'
'''

import sys
import re

import yaml
from collections import Counter

__version__ = '0.4'

REGISTRATIONS = set(['open', 'restricted', 'closed'])

EMAIL_PATTERN = r'[^@]+@[^@]+\.[^@]+'
HUMANTIME_PATTERN = r'((0?\d|1[0-1]):[0-5]\d(am|pm)(-|to)(0?\d|1[0-1]):[0-5]\d(am|pm))|((0?\d|1\d|2[0-3]):[0-5]\d(-|to)(0?\d|1\d|2[0-3]):[0-5]\d)'
EVENTBRITE_PATTERN = r'\d{9,10}'

ERROR = 'ERROR:\t{0}\n'
SUB_ERROR = '\t{0}\n'

def check_layout(layout):
    '''Checks whether layout equals "bootcamp".'''
    return layout == 'bootcamp'

def check_root(root):
    '''Checks root - can only be "."'''
    return root == '.'

def check_country(country):
    '''A valid country has no spaces, is one string, isn't empty'''
    return (country is not None) and (' ' not in country)

def check_humandate(date):
    '''A valid human date starts with a three-letter month and ends with four-letter year,
    Example: "Feb 18-20, 2525"
    other example: "Feb 18 and 20, 2014"
    '''
    if "," not in date:
        return False

    month_dates, year = date.split(",")

    # The first three characters of month_dates are not empty
    month = month_dates[:3]
    if any(char == " " for char in month):
        return False

    # But the fourth character is empty ("February" is illegal)
    if month_dates[3] != " ":
        return False

    # year contains *only* numbers
    try:
        int(year)
    except:
        return False

    return True

def check_humantime(time):
    '''A valid humantime contains at least one number'''
    return bool(re.match(HUMANTIME_PATTERN, time.replace(" ","")))

def check_date(this_date):
    '''A valid date is YEAR-MONTH-DAY, example: 2014-06-30'''
    from datetime import date
    # yaml automatically loads valid dates as datetime.date
    return isinstance(this_date, date)

def check_latitude_longitude(latlng):
    '''A valid latitude/longitude listing is two floats, separated by comma'''
    try:
        # just one of them has to break
        lat, lng = latlng.split(',')
        float(lat)
        float(lng)
    except ValueError:
        return False
    return True

def check_registration(registration):
    '''Legal registrations are defined in REGISTRATIONS'''
    return registration in REGISTRATIONS

def check_instructors(instructors):
    '''Checks whether instructor list is of format ['First name', 'Second name', ...']'''
    # yaml automatically loads list-like strings as lists
    return isinstance(instructors, list) and len(instructors) > 0

def check_helpers(helpers):
    '''Checks whether helpers list is of format ['First name', 'Second name', ...']'''
    # yaml automatically loads list-like strings as lists
    return isinstance(helpers, list) and len(helpers) >= 0

def check_email(email):
    '''A valid email has letters, then an @, followed by letters, followed by a dot, followed by letters.'''
    return bool(re.match(EMAIL_PATTERN, email))

def check_eventbrite(eventbrite):
    '''A valid EventBrite key is 9 or more digits.'''
    return bool(re.match(EVENTBRITE_PATTERN, eventbrite))

def check_pass(value):
    '''A test that always passes, used for things like addresses.'''
    return True

HANDLERS = {
    'layout' :       (True,  check_layout, 'layout isn\'t "bootcamp".'),
    'root' :         (True,  check_root, 'root can only be ".".'), 
    'country' :      (True,  check_country, 'country invalid. Please check whether there are spaces inside the country-name.'),
    'humandate' :    (True,  check_humandate, 'humandate invalid. Please use three-letter months like "Jan" and four-letter years like "2025".'),
    'humantime' :    (True,  check_humantime, 'humantime doesn\'t include numbers.'),
    'startdate' :    (True,  check_date, 'startdate invalid. Must be of format year-month-day, i.e., 2014-01-31.'),
    'enddate' :      (False, check_date, 'enddate invalid. Must be of format year-month-day, i.e., 2014-01-31.'),
    'latlng' :       (True,  check_latitude_longitude, 'latlng invalid. Check that it is two floating point numbers, separated by a comma.'),
    'registration' : (True,  check_registration, 'registration can only be {0}.'.format(REGISTRATIONS)), 
    'instructor' :   (True,  check_instructors, 'instructor list isn\'t a valid list of format ["First instructor", "Second instructor",..].'),
    'helper' :       (True,  check_helpers, 'helper list isn\'t a valid list of format ["First helper", "Second helper",..].'),
    'contact' :      (True,  check_email, 'contact email invalid.'),
    'eventbrite' :   (False, check_eventbrite, 'Eventbrite key appears invalid.'),
    'venue' :        (False, check_pass, ''),
    'address' :      (False, check_pass, '')
}

# REQUIRED is all required categories.
REQUIRED = set([k for k in HANDLERS if HANDLERS[k][0]])

# OPTIONAL is all optional categories.
OPTIONAL = set([k for k in HANDLERS if not HANDLERS[k][0]])

def check_validity(data, function, error):
    '''Wrapper-function around the various check-functions.'''
    valid = function(data)
    if not valid:
        sys.stderr.write(ERROR.format(error))
        sys.stderr.write(SUB_ERROR.format('Offending entry is: "{0}"'.format(data)))
    return valid

def check_categories(left, right, message):
    result = left - right
    if result:
        sys.stderr.write(ERROR.format(message))
        sys.stderr.write(SUB_ERROR.format('Offending entries: {0}'.format(result)))
        return False
    return True

def check_double_categories(seen_categories, message):
    category_counts = Counter(seen_categories)
    double_categories = [category for category in category_counts if category_counts[category] > 1]
    if double_categories:
        sys.stderr.write(ERROR.format(message))
        sys.stderr.write(SUB_ERROR.format('"{0}" appears more than once.\n'.format(double_categories)))
        return False
    return True

def get_header(index_fh):
    '''Parses index.html file, returns just the header'''
    # We stop the header once we see the second '---'
    header_counter = 0
    header = []
    this_categories = []
    for line in index_fh:
        line = line.rstrip()
        if line == '---':
            header_counter += 1
            continue
        if header_counter != 2:
            header.append(line)
            this_categories.append(line.split(":")[0].strip())

        if "This page is a template for bootcamp home pages." in line:
            sys.stderr.write('WARN:\tYou seem to still have the template header in your index.html. Please remove that.\n')
            sys.stderr.write('\tLook for: "<!-- Remove the block below. -->" in the index.html.\n')
            break # we can stop here - for now, just check header and template header

    return yaml.load("\n".join(header)), this_categories

def check_file(index_fh):
    '''Gets header from index.html, calls all other functions and checks file for validity.
    Returns True when 'index.html' has no problems and False when there are problems.
    '''
    header_data, seen_categories = get_header(index_fh)

    if not header_data:
        msg = 'Cannot find header in given file "{0}". Please check path, is this the bc index.html?\n'.format(filename)
        sys.stderr.write(ERROR.format(msg))
        sys.exit(1)

    is_valid = True

    # look through all header entries
    for category in HANDLERS:
        required, handler_function, error_message = HANDLERS[category]
        if category in header_data:
            is_valid &= check_validity(header_data[category], handler_function, error_message)
        elif required:
            sys.stderr.write(ERROR.format('index file is missing mandatory key "%s".'))
            is_valid &= False

    # Do we have double categories?
    is_valid &= check_double_categories(seen_categories, 'There are categories appearing twice or more.')

    # Check whether we have missing or too many categories
    seen_categories = set(seen_categories)
    is_valid &= check_categories(REQUIRED, seen_categories, 'There are missing categories.')
    is_valid &= check_categories(seen_categories, REQUIRED.union(OPTIONAL), 'There are superfluous categories.')

    return is_valid

if __name__ == '__main__':
    args = sys.argv
    if len(args) > 2:
        sys.stderr.write('Usage: "python swc_index_validator.py" or "python swc_index_validator.py path/to/index.html"\n')
        sys.exit(0)
    elif len(args) == 1:
        filename = '../index.html'
    else:
        filename = args[1]

    sys.stderr.write('Testing file "{0}".\n'.format(filename))

    with open(filename) as index_fh:
        is_valid = check_file(index_fh)

    if is_valid:
        sys.stderr.write('Everything seems to be in order.\n')
        sys.exit(0)
    else:
        sys.stderr.write('There were problems, please see above.\n')
        sys.exit(1)

########NEW FILE########
__FILENAME__ = test_swc_index_validator
"""
Test suite for ``validate_index.py``

Bootcamp metadata is stored in yaml header and PyYaml
strip all the strings.
"""

from io import StringIO
from datetime import date
import swc_index_validator as validator

def make_file(text):
    try: # this happens in Python3
        f = StringIO(text)
    except TypeError: # this happens in Python2
        f = StringIO(unicode(text))
    return f


def test_check_layout():
    assert validator.check_layout("bootcamp")

def test_check_layout_fail():
    assert not validator.check_layout("lesson")

def test_check_root():
    assert validator.check_root(".")

def test_check_root_fail():
    assert not validator.check_root("setup")

def test_check_contry():
    assert validator.check_country("Country")

def test_check_contry_none():
    assert not validator.check_country(None)

def test_check_contry_two_words():
    assert not validator.check_country("Some Country")

def test_check_humandate():
    assert validator.check_humandate("Feb 18-20, 2525")

def test_check_humandate_fail():
    assert not validator.check_humandate("February 18-20, 2525")

def test_check_humandate_chars():
    assert not validator.check_humandate("XXX SomeDay, Year")

def test_check_humantime():
    assert not validator.check_humantime("09:00am")

def test_check_euro_humantime():
    assert validator.check_humantime("09:00-17:00")

def test_check_humantime_fail():
    assert not validator.check_humantime("09:00")

def test_check_humantime_only_am():
    assert not validator.check_humantime("am")

def test_check_humantime_without_spaces():
    assert validator.check_humantime("9:00am-5:00pm")

def test_check_humantime_with_spaces():
    assert validator.check_humantime("9:00am - 5:00pm")

def test_check_humantime_with_extra_spaces():
    assert validator.check_humantime("9:00 am - 5:00 pm")

def test_check_humantime_with_to():
    assert validator.check_humantime("9:00am to 5:00pm")

def test_check_humantime_with_to_and_spaces():
    assert validator.check_humantime("9:00 am to 5:00 pm")

def test_check_humantime_without_am_pm():
    assert validator.check_humantime("9:00-17:00")

def test_check_humantime_without_am_pm_with_to():
    assert validator.check_humantime("9:00 to 17:00")

def test_check_date():
    assert validator.check_date(date(2525, 2, 20))

def test_check_date_fail():
    assert not validator.check_date("Feb 18-20, 2525")

def test_check_latitude_longitude():
    assert validator.check_latitude_longitude("0.0,0.0")

def test_check_latitude_longitude_chars():
    assert not validator.check_latitude_longitude("foo,bar")

def test_check_registration_open():
    assert validator.check_registration("open")

def test_check_registration_restricted():
    assert validator.check_registration("restricted")

def test_check_registration_closed():
    assert validator.check_registration("closed")

def test_check_registration_fail():
    assert not validator.check_registration("close")

def test_check_instructor():
    assert validator.check_instructor(["John Doe", "Jane Doe"])

def test_check_instructor_only_one():
    assert validator.check_instructor(["John Doe"])

def test_check_instructor_empty():
    assert not validator.check_instructor([])

def test_check_instructor_string():
    assert not validator.check_instructor("John Doe")

def test_check_email():
    assert validator.check_email("user@box.com")

def test_check_email_obfuscate():
    assert not validator.check_email("user AT box DOT com")

def test_check_eventbrite_9_digits():
    assert validator.check_eventbrite('1' * 9)

def test_check_eventbrite_10_digits():
    assert validator.check_eventbrite('1' * 10)

def test_check_not_eventbrite_8_digits():
    assert not validator.check_eventbrite('1' * 8)

def test_check_not_eventbrite_empty():
    assert not validator.check_eventbrite('')

def test_check_not_eventbrite_non_digits():
    assert not validator.check_eventbrite('1' * 8 + 'a')

def test_check_with_enddate():
    header_sample = """---
layout: bootcamp
root: .
venue: Euphoric State University
address: 123 College Street, Euphoria
country: United-States
humandate: Feb 17-18, 2020
humantime: 9:00 am - 4:30 pm
startdate: 2020-06-17
enddate: 2020-06-18
latlng: 41.7901128,-87.6007318
registration: restricted
instructor: ["Grace Hopper", "Alan Turing"]
contact: admin@software-carpentry.org
---"""

    assert validator.check_file(make_file(header_sample))

def test_check_without_enddate():
    header_sample = """---
layout: bootcamp
root: .
venue: Euphoric State University
address: 123 College Street, Euphoria
country: United-States
humandate: Feb 17-18, 2020
humantime: 9:00 am - 4:30 pm
startdate: 2020-06-17
latlng: 41.7901128,-87.6007318
registration: restricted
instructor: ["Grace Hopper", "Alan Turing"]
contact: admin@software-carpentry.org
---"""

    assert validator.check_file(make_file(header_sample))

########NEW FILE########
__FILENAME__ = unwarn
#!/usr/bin/env python

import sys
while True:
    line = sys.stdin.readline()
    if not line:
        break
    if ('Entity' in line):
        sys.stdin.readline()
        sys.stdin.readline()
    else:
        sys.stdout.write(line)

########NEW FILE########
__FILENAME__ = convert-to-function
import requests
import cStringIO
import csv

def get_country_temperatures(country):
    '''
    Get average surface temperature by country from the World Bank.
    Result is [ [year, value], [year, value], ...].
    '''

    base_url = 'http://climatedataapi.worldbank.org/climateweb/rest/v1/country/cru/tas/year/{0}.csv'
    actual_url = base_url.format(country)
    response = requests.get(actual_url)
    reader = cStringIO.StringIO(response.text)
    wrapper = csv.reader(reader)
    result = []
    for record in wrapper:
        if record[0] != 'year':
            year = int(record[0])
            value = float(record[1])
            result.append([year, value])
    return result

def test_nonexistent_country():
    values = get_country_temperatures('XYZ')
    assert len(values) == 0, 'Should not have succeeded for country XYZ'

def test_canada():
    values = get_country_temperatures('CAN')
    assert len(values) > 0, 'Should have had data for country CAN'

def run_tests():
    test_nonexistent_country()
    test_canada()
    print 'all tests passed'

if __name__ == '__main__':
    run_tests()

########NEW FILE########
__FILENAME__ = cstringio-demo
import cStringIO

data = 'first\nsecond\nthird\n'
reader = cStringIO.StringIO(data)
for line in reader:
    print line

########NEW FILE########
__FILENAME__ = csv-demo-2
import cStringIO
import csv

data = '1901,12.3\n1902,45.6\n1903,78.9\n'
reader = cStringIO.StringIO(data)
wrapper = csv.reader(reader)
for record in wrapper:
    print record

########NEW FILE########
__FILENAME__ = csv-demo
import cStringIO
import csv

data = 'first\nsecond\nthird\n'
reader = cStringIO.StringIO(data)
wrapper = csv.reader(reader)
for record in wrapper:
    print record

########NEW FILE########
__FILENAME__ = final
import requests
import cStringIO
import csv

def compare_countries(left_country, right_country):
    '''
    Compare average surface temperatures for two countries over time.
    '''
    left_data = get_country_temperatures(left_country)
    right_data = get_country_temperatures(right_country)
    result = []
    for ( (left_year, left_value), (right_year, right_value) ) in zip(left_country, right_country):
        assert left_year == right_year, 'Year mismatch: {0} vs {1}'.format(left_year, right_year)
        result.append([left_year, left_value - right_value])
    return result

def get_country_temperatures(country):
    '''
    Get average surface temperature by country from the World Bank.
    Result is [ [year, value], [year, value], ...].
    '''

    base_url = 'http://climatedataapi.worldbank.org/climateweb/rest/v1/country/cru/tas/year/{0}.csv'
    actual_url = base_url.format(country)
    response = requests.get(actual_url)
    reader = cStringIO.StringIO(response.text)
    wrapper = csv.reader(reader)
    result = []
    for record in wrapper:
        if record[0] != 'year':
            year = int(record[0])
            value = float(record[1])
            result.append([year, value])
    return result

########NEW FILE########
__FILENAME__ = get-data
import requests

url = 'http://climatedataapi.worldbank.org/climateweb/rest/v1/country/cru/tas/year/CAN.csv'
response = requests.get(url)
if response.status_code != 200:
    print 'Failed to get data:', response.status_code
else:
    print response.text

########NEW FILE########
__FILENAME__ = get-parse-data-correctly
import requests
import cStringIO
import csv

url = 'http://climatedataapi.worldbank.org/climateweb/rest/v1/country/cru/tas/year/CAN.csv'
response = requests.get(url)
if response.status_code != 200:
    print 'Failed to get data:', response.status_code
else:
    reader = cStringIO.StringIO(response.text)
    wrapper = csv.reader(reader)
    for record in wrapper:
        if record[0] != 'year':
            year = int(record[0])
            value = float(record[1])
            print year, ':', value

########NEW FILE########
__FILENAME__ = get-parse-data
import requests
import cStringIO
import csv

url = 'http://climatedataapi.worldbank.org/climateweb/rest/v1/country/cru/tas/year/CAN.csv'
response = requests.get(url)
if response.status_code != 200:
    print 'Failed to get data:', response.status_code
else:
    reader = cStringIO.StringIO(response.text)
    wrapper = csv.reader(reader)
    for record in wrapper:
        year = int(record[0])
        value = float(record[1])
        print year, ':', value

########NEW FILE########
__FILENAME__ = parse-manually
input_data = '1901,12.3\n1902,45.6\n1903,78.9\n'
print 'input data is:'
print input_data

as_lines = input_data.split('\n')
print 'as lines:'
print as_lines

for line in as_lines:
    fields = line.split(',')
    year = int(fields[0])
    value = float(fields[1])
    print year, ':', value

########NEW FILE########
__FILENAME__ = zip-demo
lows = [1, 2, 3]
highs = [40, 50, 60]
for thing in zip(lows, highs):
    print thing

pairs = [ [1, 10], [2, 20], [3, 30] ]
for (left, right) in pairs:
    print 'left:', left, 'and right:', right

canada = [ [1901, -1.0], [1902, -2.0], [1903, -3.0] ]
brazil = [ [1901, 20.0], [1902, 20.0], [1903, 30.0] ]
for ( (left_year, left_value), (right_year, right_value) ) in zip(canada, brazil):
    print 'years are:', left_year, right_year, 'and values are:', left_value, right_value

########NEW FILE########
__FILENAME__ = doitmagic
"""doitmagic provices a simple magic for running
tasks through doit in the ipython notebook

Usage:

%%doit doit_args

def task_example():
    return { 'actions' : ['echo "Hello world!"'] }

"""

# This file is copyright 2014 by Rob Beagrie: see
# https://github.com/gvwilson/sqlitemagic/blob/master/LICENSE
# for the license.
# Inspired by https://github.com/tkf/ipython-sqlitemagic
# and Greg Wilson's sqlitemagic elsewhere in the SWC repo

from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE
import signal
import time
import sys
import os
from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.utils import py3compat

@magics_class
class DoitMagic(Magics):
    '''Provide the 'doit' calling point.'''

    def __init__(self, shell):
        """
        Parameters
        ----------
        shell : IPython shell

        """
        super(DoitMagic, self).__init__(shell)
        self._temp_file = NamedTemporaryFile()

    @cell_magic
    def doit(self, doit_args, cell):
        with NamedTemporaryFile(delete=False, suffix='.py') as tmp_file:
            tmp_name = tmp_file.name
            tmp_file.write(cell)

        cur_dir = os.getcwd()
        doit_args = doit_args.split()
        if doit_args:
            doit_command = [doit_args.pop(0)]
        else:
            doit_command = []

        cmd = ['doit']
        cmd += doit_command
        cmd += [ '-d', cur_dir, '-f', tmp_name]
        cmd += doit_args

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)

        try:
            out, err = p.communicate(cell)
        except KeyboardInterrupt:
            try:
                p.send_signal(signal.SIGINT)
                time.sleep(0.1)
                if p.poll() is not None:
                    print("Process is interrupted.")
                    return
                p.terminate()
                time.sleep(0.1)
                if p.poll() is not None:
                    print("Process is terminated.")
                    return
                p.kill()
                print("Process is killed.")
            except OSError:
                pass
            except Exception as e:
                print("Error while terminating subprocess (pid=%i): %s" \
                    % (p.pid, e))
            return

        out = py3compat.bytes_to_str(out)
        err = py3compat.bytes_to_str(err)

        sys.stdout.write(out)
        sys.stdout.flush()
        sys.stderr.write(err)
        sys.stderr.flush()

        os.remove(tmp_name)

def load_ipython_extension(ipython):
    ipython.register_magics(DoitMagic)

########NEW FILE########
__FILENAME__ = automatic_variables

# automatic_variables.py

def task_reformat_temperature_data():
    """Reformats the raw temperature data file for easier analysis"""
    
    return {
        'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
        'file_dep': ['UK_Tmean_data.txt'],
        'targets': ['UK_Tmean_data.reformatted.txt'],
    }

def task_reformat_sunshine_data():
    """Reformats the raw sunshine data file for easier analysis"""
    
    return {
        'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
        'file_dep': ['UK_Sunshine_data.txt'],
        'targets': ['UK_Sunshine_data.reformatted.txt'],
    }
########NEW FILE########
__FILENAME__ = download_all_data

# download_all_data.py

data_sets = ['Tmean', 'Sunshine']

def get_data_file_parameters(data_type):
    """Takes a string describing the type of climate data, returns url and file name for that data"""
    
    base_url = 'http://www.metoffice.gov.uk/climate/uk/datasets/{0}/ranked/UK.txt'
    data_url = base_url.format(data_type)
    data_target = 'UK_{0}_data.txt'.format(data_type)
    return data_url, data_target

def task_download_data():
    """Downloads all raw data files from the Met Office website"""

    for data_type in data_sets:
        data_url, data_target = get_data_file_parameters(data_type)
        yield {
            'actions': ['wget -O %(targets)s {0}'.format(data_url)],
            'targets': [ data_target ],
            'name' : data_type,
        }

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
            'name': 'UK_{}_data.txt'.format(data_type),
        }
########NEW FILE########
__FILENAME__ = download_temp_data

# download_temp_data.py

import datetime
from doit.tools import timeout 

data_sets = ['Tmean', 'Sunshine']

def task_get_temp_data():
    """Downloads the raw temperature data from the Met Office"""

    return {
        'actions': ['wget -O %(targets)s http://www.metoffice.gov.uk/climate/uk/datasets/Tmean/ranked/UK.txt'],
        'targets': ['UK_Tmean_data.txt'],
    }

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
            'name': 'UK_{}_data.txt'.format(data_type),
        }
########NEW FILE########
__FILENAME__ = monthly_raw_data_update

# monthly_raw_data_update.py

import datetime
from doit.tools import timeout 

data_sets = ['Tmean', 'Sunshine']

def get_data_file_parameters(data_type):
    """Takes a string describing the type of climate data, returns url and file name for that data"""

    base_url = 'http://www.metoffice.gov.uk/climate/uk/datasets/{0}/ranked/UK.txt'
    data_url = base_url.format(data_type)
    data_target = 'UK_{0}_data.txt'.format(data_type)
    return data_url, data_target

def task_download_data():
    """Downloads all raw data files from the Met Office website"""

    for data_type in data_sets:
        data_url, data_target = get_data_file_parameters(data_type)
        yield {
            'actions': ['wget -O %(targets)s {0}'.format(data_url)],
            'targets': [ data_target ],
            'name' : data_type,
            'uptodate': [timeout(datetime.timedelta(weeks=4))],

        }

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
            'name': 'UK_{}_data.txt'.format(data_type),
        }
########NEW FILE########
__FILENAME__ = one_task

# one_task.py

def task_reformat_temperature_data():
    """Reformats the raw temperature data file for easier analysis"""
    
    return {
        'file_dep': ['UK_Tmean_data.txt'],
        'targets': ['UK_Tmean_data.reformatted.txt'],
        'actions': ['python reformat_weather_data.py UK_Tmean_data.txt > UK_Tmean_data.reformatted.txt'],
    }

########NEW FILE########
__FILENAME__ = rainfall_data

# rainfall_data.py

import datetime
from doit.tools import timeout 

data_sets = ['Tmean', 'Sunshine', 'Rainfall']

def get_data_file_parameters(data_type):
    """Takes a string describing the type of climate data, returns url and file name for that data"""

    base_url = 'http://www.metoffice.gov.uk/climate/uk/datasets/{0}/ranked/UK.txt'
    data_url = base_url.format(data_type)
    data_target = 'UK_{0}_data.txt'.format(data_type)
    return data_url, data_target

def task_download_data():
    """Downloads all raw data files from the Met Office website"""

    for data_type in data_sets:
        data_url, data_target = get_data_file_parameters(data_type)
        yield {
            'actions': ['wget -O %(targets)s {0}'.format(data_url)],
            'targets': [ data_target ],
            'name' : data_type,
            'uptodate': [timeout(datetime.timedelta(weeks=4))],

        }

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
            'name': 'UK_{}_data.txt'.format(data_type),
        }
########NEW FILE########
__FILENAME__ = sub_tasks

# sub_tasks.py

data_sets = ['Tmean', 'Sunshine']

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
            'name': 'UK_{}_data.txt'.format(data_type),
        }
    
########NEW FILE########
__FILENAME__ = sub_tasks_no_name

# sub_tasks_no_name.py

data_sets = ['Tmean', 'Sunshine']

def task_reformat_data():
    """Reformats all raw files for easier analysis"""

    for data_type in data_sets:
        yield {
            'actions': ['python reformat_weather_data.py %(dependencies)s > %(targets)s'],
            'file_dep': ['UK_{}_data.txt'.format(data_type)],
            'targets': ['UK_{}_data.reformatted.txt'.format(data_type)],
        }
    
########NEW FILE########
__FILENAME__ = two_tasks

# two_tasks.py

def task_reformat_temperature_data():
    """Reformats the raw temperature data file for easier analysis"""
        
    return {
        'file_dep': ['UK_Tmean_data.txt'],
        'targets': ['UK_Tmean_data.reformatted.txt'],
        'actions': ['python reformat_weather_data.py UK_Tmean_data.txt > UK_Tmean_data.reformatted.txt'],
}

def task_reformat_sunshine_data():
    """Reformats the raw sunshine data file for easier analysis"""

    return {
        'file_dep': ['UK_Sunshine_data.txt'],
        'targets': ['UK_Sunshine_data.reformatted.txt'],
        'actions': ['python reformat_weather_data.py UK_Sunshine_data.txt > UK_Sunshine_data.reformatted.txt'],
    }
########NEW FILE########
__FILENAME__ = reformat_weather_data
import pandas as pd
import argparse
import sys

parser = argparse.ArgumentParser(description='Reformats a met-office weather data file. Input data has one row per year and one column per month. Output data has a date column and a value column.')
parser.add_argument('data_file',metavar='DATA_FILE', help='Data file containing met office weather stats.')

def get_month_data(month_data):
    """Takes a two column DataFrame and returns a one column DataFrame where the index is a pandas period""" 
    
    # Each pair of columns contains data for a specific month. What month is this?
    month = month_data.columns[0]
        
    # Given a year, return a Period object representing this month in that year
    def get_period(year):
        return pd.Period('{0} {1}'.format(month,year))
    
    # Change the index of the dataframe to be the monthly period
    month_data.index = map(get_period, full_data.iloc[:,2])
    
    # Rename the columns
    month_data.columns = ['value', 'year']
    month_data.index.name = 'month'
        
    # Remove the year column, we don't need it anymore.
    return month_data.drop('year', axis=1)

def unstack_data(full_data):
    """
    Takes a dataframe with monthly columns and yearly rows. Returns a single column
    dataframe where each row is a specific month of a specific year.
    """

    # Loop over columns of the DataFrame in groups of 2
    # and feed them to get_month_data
    monthly_data = [ get_month_data(full_data.iloc[:, i:i+2]) for i in range(1,25,2)]

    # Add all the data for the individual months together
    unstacked_data = pd.concat(monthly_data)

    return unstacked_data.sort()

if __name__ == '__main__':

    args = parser.parse_args()

    full_data = pd.read_csv(args.data_file, delim_whitespace=True,
            skiprows=7)

    unstacked_data = unstack_data(full_data)

    # Write the new dataframe to stdout
    try:
        unstacked_data.to_csv(sys.stdout)

    # Don't fall over if we pipe the output to head
    except IOError:
        pass

    

########NEW FILE########
__FILENAME__ = sync_doit_examples
""" 
This script is intended to keep the example doit scripts
in doit_examples/ in sync with the contents of the
iPython notebooks used for teaching. It iterates over
all iPython notebooks in the current directory and looks
for cells that contain the doit magic. If the first
comment line contains a filename, it writes the contents
of that cell to the relevant file in doit_examples/
"""

import simplejson
import os
import glob

# Iterate over notebooks in this directory
for nbpath in glob.glob('0?-*.ipynb'):

    # Open notebook and load as json
    with open(nbpath, 'r') as nbtxt:
        nbdata = simplejson.load(nbtxt)
        
    # Iterate over cells
    for cell in nbdata['worksheets'][0]['cells']:
        
        # If a code cell, check if the first line starts with %%doit
        if cell['cell_type'] == 'code':
            lines = cell['input']
            if lines and lines[0][:6] == '%%doit':
                
                # If it does, find the first comment line and check that it looks like a filename
                for line in lines:
                    if line[0] == '#':
                    
                        if line[-4:-1] == '.py':

                            # Extract the filename
                            fname = line[1:].strip()
                            fpath = os.path.join('doit_examples', fname)

                            print 'Found an example. Writing to {0}'.format(fpath)
                            
                            # Write the contents of the cell to the filename
                            with open(fpath, 'w') as example_file:
                                example_file.writelines(lines[1:])
                            
                        break

########NEW FILE########
__FILENAME__ = create_inter_python_data
"""Create the data for the Software Carpentry Intermediate Python lectures"""

import numpy as np
import pandas as pd

np.random.seed(26)
datasets = {'A1': [0, 0.5, 0.7, 10],
            'A2': [0, 0.5, 0.7, 50],
            'A3': [0, 0.5, 0.3, 50],
            'B1': [3, 0.7, 0.2, 50],
            'B2': [3, 0.7, 0.7, 50]}

def make_data(intercept, tempslope, rainfallslope, numyears):
    years = np.arange(2010 - numyears, 2011)
    temps = np.random.uniform(70, 90, len(years))
    rainfalls = np.random.uniform(100, 300, len(years))
    noise = 2 * np.random.randn(len(years))
    mosquitos = intercept + tempslope * temps + rainfallslope * rainfalls + noise
    return zip(years, temps, rainfalls, mosquitos)

def export_data(data, filename):
    df = pd.DataFrame(data, columns=['year', 'temperature', 'rainfall','mosquitos'])
    df.to_csv(filename, index=False, float_format='%.0f')

for site in datasets:
    data = make_data(*datasets[site])
    if site == 'A1':
        #create a shorter dataset for first example
        data = data[-10:]
    export_data(data, '%s_mosquito_data.csv' % site)

########NEW FILE########
__FILENAME__ = ears
"""
ears.py : a simple unit testing library for teaching in the IPython Notebook.

ears.run() looks for all the functions defined in the calling stack frame
(hopefully the top level interpreter session) whose names begin with the
characters 'test_' and calls them in an undetermined order, collecting and
reporting results.

Usage:

    import ears

    def test_pass(): pass
    def test_fail(): assert False, 'Error message'
    def test_error(): 1/0 # zero division error

    ears.run()
"""

import sys
import inspect
import traceback

def run(prefix='test_', verbose=False):
    """
    Look for test functions defined by caller, execute, and report.
    """
    # Collect functions defined in calling context.
    caller_defs = inspect.stack()[1][0].f_globals
    test_functions = dict([(n, caller_defs[n]) for n in caller_defs
                           if n.startswith(prefix) and callable(caller_defs[n])])
    setup = caller_defs.get('setup', None)
    teardown = caller_defs.get('teardown', None)

    # Execute and record.
    passes = []
    fails = []
    errors = []
    for (name, test) in test_functions.iteritems():
        if verbose:
            print name
        if setup is not None:
            setup()
        try:
            test()
            passes.append((name, None))
            sys.stdout.write('.')
        except AssertionError as e:
            fails.append((name, traceback.format_exc()))
            sys.stdout.write('f')
        except Exception as e:
            errors.append((name, traceback.format_exc()))
            sys.stdout.write('E')
        if teardown is not None:
            teardown()

    # Report.
    print
    print '{0} pass, {1} fail, {2} error'.format(len(passes),
                                                 len(fails),
                                                 len(errors))
    for (title, group) in (('fail', fails),
                           ('error', errors)):
        for (name, exc) in group:
            print '{0}\n{1}: {2}'.format('-'*40, title, name)
            print exc

if __name__ == '__main__':

    def test_pass():
        pass

    def test_fail():
        assert False, 'Error message'

    def test_error():
        1/0

    run()

########NEW FILE########
__FILENAME__ = plot_rand_mp
#!/usr/bin/env python

import os, sys, errno
import re
import argparse
from time import time
import multiprocessing

import numpy as np
import matplotlib.pyplot as plt

def plotData(outputDir, plotNum):
	outFilename = "plot_%d.pdf" % (plotNum,)
	outFilepath = os.path.join(outputDir, outFilename)
	
	# Plot some random data
	# Adapted from: http://matplotlib.org/examples/shapes_and_collections/scatter_demo.html
	N = 500
	# First we need to re-initialize the random number generator for each worker
	# See: https://groups.google.com/forum/#!topic/briansupport/9ErDidIBBFM
	np.random.seed( int( time() ) + plotNum )
	x = np.random.rand(N)
	y = np.random.rand(N)
	area = np.pi * (15 * np.random.rand(N))**2 # 0 to 15 point radiuses

	print("\tMaking plot %d" % (plotNum,) )
	plt.scatter(x, y, s=area, alpha=0.5)
	plt.savefig(outFilepath)
	# Clear figure so that the next plot this worker makes will not contain
	# data from previous plots
	plt.clf() 
	
	return (plotNum, outFilepath)


if __name__ == '__main__':
    # Handle command line options
    parser = argparse.ArgumentParser(description='Plot random data in parallel')
    parser.add_argument('-o', '--outputDir', required=True,
                        help='The directory to which plot files should be saved')
    parser.add_argument('-n', '--numPlots', required=False, type=int, default=32,
    					help='The number of plots to make')
    parser.add_argument('--numProcessors', required=False, type=int, 
    					default=multiprocessing.cpu_count(),
    					help='Number of processors to use. ' + \
    					"Default for this machine is %d" % (multiprocessing.cpu_count(),) )
    args = parser.parse_args()

    if not os.path.isdir(args.outputDir) or not os.access(args.outputDir, os.W_OK):
    	sys.exit("Unable to write to output directory %s" % (args.outputDir,) )
    
    if args.numPlots < 1:
    	sys.exit('Number of plots must be greater than 0')
    
    if args.numProcessors < 1:
    	sys.exit('Number of processors to use must be greater than 0')
    
    # Start my pool
    pool = multiprocessing.Pool( args.numProcessors )

    print("Making %d plots of random data using %d processors..." % \
    		(args.numPlots, args.numProcessors) )

    # Build task list
    tasks = []
    plotNum = 0
    while plotNum < args.numPlots:
    	plotNum += 1
    	tasks.append( (args.outputDir, plotNum, ) )
    
    # Run tasks
    results = [pool.apply_async( plotData, t ) for t in tasks]

    # Process results
    for result in results:
        (plotNum, plotFilename) = result.get()
        print("Result: plot %d written to %s" % (plotNum, plotFilename) )

    pool.close()
    pool.join()

########NEW FILE########
__FILENAME__ = argv-list
import sys
print 'sys.argv is', sys.argv

########NEW FILE########
__FILENAME__ = count-stdin
import sys

count = 0
for line in sys.stdin:
    count += 1

print count, 'lines in standard input'

########NEW FILE########
__FILENAME__ = gen-inflammation
#!/usr/bin/env python

'''Generate pseudo-random patient inflammation data for use in Python lessons.'''

import sys
import random

n_patients = 60
n_days = 40
n_range = 20

middle = n_days / 2

for p in range(n_patients):
    vals = []
    for d in range(n_days):
        upper = max(n_range - abs(d - middle), 0)
        vals.append(random.randint(upper/4, upper))
    print ','.join([str(v) for v in vals])

########NEW FILE########
__FILENAME__ = readings-01
import sys
import numpy as np

def main():
    script = sys.argv[0]
    filename = sys.argv[1]
    data = np.loadtxt(filename, delimiter=',')
    for m in data.mean(axis=1):
        print m

########NEW FILE########
__FILENAME__ = readings-02
import sys
import numpy as np

def main():
    script = sys.argv[0]
    filename = sys.argv[1]
    data = np.loadtxt(filename, delimiter=',')
    for m in data.mean(axis=1):
        print m

main()

########NEW FILE########
__FILENAME__ = readings-03
import sys
import numpy as np

def main():
    script = sys.argv[0]
    for filename in sys.argv[1:]:
        data = np.loadtxt(filename, delimiter=',')
        for m in data.mean(axis=1):
            print m

main()

########NEW FILE########
__FILENAME__ = readings-04
import sys
import numpy as np

def main():
    script = sys.argv[0]
    action = sys.argv[1]
    filenames = sys.argv[2:]

    for f in filenames:
        data = np.loadtxt(f, delimiter=',')

        if action == '--min':
            values = data.min(axis=1)
        elif action == '--mean':
            values = data.mean(axis=1)
        elif action == '--max':
            values = data.max(axis=1)

        for m in values:
            print m

main()

########NEW FILE########
__FILENAME__ = readings-05
import sys
import numpy as np

def main():
    script = sys.argv[0]
    action = sys.argv[1]
    filenames = sys.argv[2:]
    assert action in ['--min', '--mean', '--max'], \
           'Action is not one of --min, --mean, or --max: ' + action
    for f in filenames:
        process(f, action)

def process(filename, action):
    data = np.loadtxt(filename, delimiter=',')

    if action == '--min':
        values = data.min(axis=1)
    elif action == '--mean':
        values = data.mean(axis=1)
    elif action == '--max':
        values = data.max(axis=1)

    for m in values:
        print m

main()

########NEW FILE########
__FILENAME__ = readings-06
import sys
import numpy as np

def main():
    script = sys.argv[0]
    action = sys.argv[1]
    filenames = sys.argv[2:]
    assert action in ['--min', '--mean', '--max'], \
           'Action is not one of --min, --mean, or --max: ' + action
    if len(filenames) == 0:
        process(sys.stdin, action)
    else:
        for f in filenames:
            process(f, action)

def process(filename, action):
    data = np.loadtxt(filename, delimiter=',')

    if action == '--min':
        values = data.min(axis=1)
    elif action == '--mean':
        values = data.mean(axis=1)
    elif action == '--max':
        values = data.max(axis=1)

    for m in values:
        print m

main()

########NEW FILE########
__FILENAME__ = rectangle
def rectangle_area(coords):
    x0, y0, x1, y1 = coords
    return (x1 - x0) * (x1 - y0)

########NEW FILE########
__FILENAME__ = sys-version
import sys
print 'version is', sys.version

########NEW FILE########
__FILENAME__ = gen-nene
#!/usr/bin/env python

'''Generate random data for files in `filesystem/users/nelle/north-pacific-gyre/2012-07-03/NENE*.txt`.'''

import sys
import os
import random

assert len(sys.argv) >= 5, \
    'Usage: {0} mean length output_directory filenames'.format(sys.argv[0])

mean, length, output_directory, filenames = \
    float(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4:]

assert mean > 0.0, \
    'Mean {0} must be positive'.format(mean)
assert length > 0, \
    'File length {0} must be positive'.format(length)
assert os.path.isdir(output_directory), \
    'Output directory "{0}" does not exist'.format(output_directory)
assert len(filenames) > 0, \
    'No filenames provided'

for f in filenames:
    with open(os.path.join(output_directory, f), 'w') as writer:
        for i in range(length):
            print >> writer, random.expovariate(1.0/mean)

########NEW FILE########
__FILENAME__ = gen-sequence
#!/usr/bin/env python

'''Generate random seuqence data for files in `creatures` directory.'''

import sys
import random

assert len(sys.argv) == 3, 'Usage: gen-sequence lines seed'
num_lines = int(sys.argv[1])
random.seed(sys.argv[2])
for i in range(num_lines):
    print ''.join(random.choice('ACGT') for j in range(10))

########NEW FILE########
__FILENAME__ = sqlitemagic
"""sqlitemagic provices a simple magic for interacting with SQLite
databases stored on disk.

Usage:

%%sqlite filename.db
select personal, family from person;

produces:

Alan|Turing
Grace|Hopper
"""

# This file is copyright 2013 by Greg Wilson: see
# https://github.com/gvwilson/sqlitemagic/blob/master/LICENSE
# for the license.
# Inspired by https://github.com/tkf/ipython-sqlitemagic.

import sqlite3
from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.display import display, HTML

@magics_class
class SqliteMagic(Magics):
    '''Provide the 'sqlite' calling point.'''

    @cell_magic
    def sqlite(self, filename, query):
        connection = sqlite3.connect(filename)
        cursor = connection.cursor()
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            display(HTML(self.tablify(results)))
        except Exception, e:
            import sys
            print >> sys.stderr, "exception", e
        cursor.close()
        connection.close()

    def tablify(self, rows):
        return '<table>\n' + '\n'.join(self.rowify(r) for r in rows) + '\n</table>'

    def rowify(self, row):
        return '<tr>' + ''.join('<td>' + str(r) + '</td>' for r in row) + '</tr>'

def load_ipython_extension(ipython):
    ipython.register_magics(SqliteMagic)

########NEW FILE########
__FILENAME__ = swc-installation-test-1
#!/usr/bin/env python

"""Test script to check required Python version.

Execute this code at the command line by typing:

  python swc-installation-test-1.py

How to get a command line:

- On OSX run this with the Terminal application.

- On Windows, go to the Start menu, select 'Run' and type 'cmd'
(without the quotes) to run the 'cmd.exe' Windows Command Prompt.

- On Linux, either use your login shell directly, or run one of a
  number of graphical terminals (e.g. 'xterm', 'gnome-terminal', ...).

For some screen shots, see:

  http://software-carpentry.org/setup/terminal.html

Run the script and follow the instructions it prints at the end.  If
you see an error saying that the 'python' command was not found, than
you may not have any version of Python installed.  See:

  http://www.python.org/download/releases/2.7.3/#download

for installation instructions.

This test is separate to avoid Python syntax errors parsing the more
elaborate `swc-installation-test-2.py`.
"""

import sys as _sys


__version__ = '0.1'


def check():
    if _sys.version_info < (2, 6):
        print('check for Python version (python):')
        print('outdated version of Python: ' + _sys.version)
        return False
    return True


if __name__ == '__main__':
    if check():
        print('Passed')
    else:
        print('Failed')
        print('Install a current version of Python!')
        print('http://www.python.org/download/releases/2.7.3/#download')
        _sys.exit(1)

########NEW FILE########
__FILENAME__ = swc-installation-test-2
#!/usr/bin/env python

"""Test script to check for required functionality.

Execute this code at the command line by typing:

  python swc-installation-test-2.py

Run the script and follow the instructions it prints at the end.

This script requires at least Python 2.6.  You can check the version
of Python that you have installed with 'swc-installation-test-1.py'.

By default, this script will test for all the dependencies your
instructor thinks you need.  If you want to test for a different set
of packages, you can list them on the command line.  For example:

  python swc-installation-test-2.py git virtual-editor

This is useful if the original test told you to install a more recent
version of a particular dependency, and you just want to re-test that
dependency.
"""

from __future__ import print_function  # for Python 2.6 compatibility

import distutils.ccompiler as _distutils_ccompiler
import fnmatch as _fnmatch
try:  # Python 2.7 and 3.x
    import importlib as _importlib
except ImportError:  # Python 2.6 and earlier
    class _Importlib (object):
        """Minimal workarounds for functions we need
        """
        @staticmethod
        def import_module(name):
            module = __import__(name)
            for n in name.split('.')[1:]:
                module = getattr(module, n)
            return module
    _importlib = _Importlib()
import logging as _logging
import os as _os
import platform as _platform
import re as _re
import shlex as _shlex
import subprocess as _subprocess
import sys as _sys
try:  # Python 3.x
    import urllib.parse as _urllib_parse
except ImportError:  # Python 2.x
    import urllib as _urllib_parse  # for quote()


if not hasattr(_shlex, 'quote'):  # Python versions older than 3.3
    # Use the undocumented pipes.quote()
    import pipes as _pipes
    _shlex.quote = _pipes.quote


__version__ = '0.1'

# Comment out any entries you don't need
CHECKS = [
# Shell
    'virtual-shell',
# Editors
    'virtual-editor',
# Browsers
    'virtual-browser',
# Version control
    'git',
    'hg',              # Command line tool
    #'mercurial',       # Python package
    'EasyMercurial',
# Build tools and packaging
    'make',
    'virtual-pypi-installer',
    'setuptools',
    #'xcode',
# Testing
    'nosetests',       # Command line tool
    'nose',            # Python package
    'py.test',         # Command line tool
    'pytest',          # Python package
# SQL
    'sqlite3',         # Command line tool
    'sqlite3-python',  # Python package
# Python
    'python',
    'ipython',         # Command line tool
    'IPython',         # Python package
    'argparse',        # Useful for utility scripts
    'numpy',
    'scipy',
    'matplotlib',
    'pandas',
    'sympy',
    'Cython',
    'networkx',
    'mayavi.mlab',
    ]

CHECKER = {}

_ROOT_PATH = _os.sep
if _platform.system() == 'win32':
    _ROOT_PATH = 'c:\\'


class InvalidCheck (KeyError):
    def __init__(self, check):
        super(InvalidCheck, self).__init__(check)
        self.check = check

    def __str__(self):
        return self.check


class DependencyError (Exception):
    _default_url = 'http://software-carpentry.org/setup/'
    _setup_urls = {  # (system, version, package) glob pairs
        ('*', '*', 'Cython'): 'http://docs.cython.org/src/quickstart/install.html',
        ('Linux', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-linux',
        ('Darwin', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-mac',
        ('Windows', '*', 'EasyMercurial'): 'http://easyhg.org/download.html#download-windows',
        ('*', '*', 'EasyMercurial'): 'http://easyhg.org/download.html',
        ('*', '*', 'argparse'): 'https://pypi.python.org/pypi/argparse#installation',
        ('*', '*', 'ash'): 'http://www.in-ulm.de/~mascheck/various/ash/',
        ('*', '*', 'bash'): 'http://www.gnu.org/software/bash/manual/html_node/Basic-Installation.html#Basic-Installation',
        ('Linux', '*', 'chromium'): 'http://code.google.com/p/chromium/wiki/LinuxBuildInstructions',
        ('Darwin', '*', 'chromium'): 'http://code.google.com/p/chromium/wiki/MacBuildInstructions',
        ('Windows', '*', 'chromium'): 'http://www.chromium.org/developers/how-tos/build-instructions-windows',
        ('*', '*', 'chromium'): 'http://www.chromium.org/developers/how-tos',
        ('Windows', '*', 'emacs'): 'http://www.gnu.org/software/emacs/windows/Installing-Emacs.html',
        ('*', '*', 'emacs'): 'http://www.gnu.org/software/emacs/#Obtaining',
        ('*', '*', 'firefox'): 'http://www.mozilla.org/en-US/firefox/new/',
        ('Linux', '*', 'gedit'): 'http://www.linuxfromscratch.org/blfs/view/svn/gnome/gedit.html',
        ('*', '*', 'git'): 'http://git-scm.com/downloads',
        ('*', '*', 'google-chrome'): 'https://www.google.com/intl/en/chrome/browser/',
        ('*', '*', 'hg'): 'http://mercurial.selenic.com/',
        ('*', '*', 'mercurial'): 'http://mercurial.selenic.com/',
        ('*', '*', 'IPython'): 'http://ipython.org/install.html',
        ('*', '*', 'ipython'): 'http://ipython.org/install.html',
        ('*', '*', 'jinja'): 'http://jinja.pocoo.org/docs/intro/#installation',
        ('*', '*', 'kate'): 'http://kate-editor.org/get-it/',
        ('*', '*', 'make'): 'http://www.gnu.org/software/make/',
        ('Darwin', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#building-on-osx',
        ('Windows', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#installing-on-windows',
        ('*', '*', 'matplotlib'): 'http://matplotlib.org/users/installing.html#installing',
        ('*', '*', 'mayavi.mlab'): 'http://docs.enthought.com/mayavi/mayavi/installation.html',
        ('*', '*', 'nano'): 'http://www.nano-editor.org/dist/latest/faq.html#3',
        ('*', '*', 'networkx'): 'http://networkx.github.com/documentation/latest/install.html#installing',
        ('*', '*', 'nose'): 'https://nose.readthedocs.org/en/latest/#installation-and-quick-start',
        ('*', '*', 'nosetests'): 'https://nose.readthedocs.org/en/latest/#installation-and-quick-start',
        ('*', '*', 'notepad++'): 'http://notepad-plus-plus.org/download/v6.3.html',
        ('*', '*', 'numpy'): 'http://docs.scipy.org/doc/numpy/user/install.html',
        ('*', '*', 'pandas'): 'http://pandas.pydata.org/pandas-docs/stable/install.html',
        ('*', '*', 'pip'): 'http://www.pip-installer.org/en/latest/installing.html',
        ('*', '*', 'pytest'): 'http://pytest.org/latest/getting-started.html',
        ('*', '*', 'python'): 'http://www.python.org/download/releases/2.7.3/#download',
        ('*', '*', 'pyzmq'): 'https://github.com/zeromq/pyzmq/wiki/Building-and-Installing-PyZMQ',
        ('*', '*', 'py.test'): 'http://pytest.org/latest/getting-started.html',
        ('Linux', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Linux',
        ('Darwin', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Mac_OS_X',
        ('Windows', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy/Windows',
        ('*', '*', 'scipy'): 'http://www.scipy.org/Installing_SciPy',
        ('*', '*', 'setuptools'): 'https://pypi.python.org/pypi/setuptools#installation-instructions',
        ('*', '*', 'sqlite3'): 'http://www.sqlite.org/download.html',
        ('*', '*', 'sublime-text'): 'http://www.sublimetext.com/2',
        ('*', '*', 'sympy'): 'http://docs.sympy.org/dev/install.html',
        ('Darwin', '*', 'textmate'): 'http://macromates.com/',
        ('Darwin', '*', 'textwrangler'): 'http://www.barebones.com/products/textwrangler/download.html',
        ('*', '*', 'tornado'): 'http://www.tornadoweb.org/',
        ('*', '*', 'vim'): 'http://www.vim.org/download.php',
        ('Darwin', '*', 'xcode'): 'https://developer.apple.com/xcode/',
        ('*', '*', 'xemacs'): 'http://www.us.xemacs.org/Install/',
        ('*', '*', 'zsh'): 'http://www.zsh.org/',
        }

    def _get_message(self):
        return self._message
    def _set_message(self, message):
        self._message = message
    message = property(_get_message, _set_message)

    def __init__(self, checker, message, causes=None):
        super(DependencyError, self).__init__(message)
        self.checker = checker
        self.message = message
        if causes is None:
            causes = []
        self.causes = causes

    def get_url(self):
        system = _platform.system()
        version = None
        for pversion in (
            'linux_distribution',
            'mac_ver',
            'win32_ver',
            ):
            value = getattr(_platform, pversion)()
            if value[0]:
                version = value[0]
                break
        package = self.checker.name
        for (s,v,p),url in self._setup_urls.items():
            if (_fnmatch.fnmatch(system, s) and
                    _fnmatch.fnmatch(version, v) and
                    _fnmatch.fnmatch(package, p)):
                return url
        return self._default_url

    def __str__(self):
        url = self.get_url()
        lines = [
            'check for {0} failed:'.format(self.checker.full_name()),
            '  ' + self.message,
            '  For instructions on installing an up-to-date version, see',
            '  ' + url,
            ]
        if self.causes:
            lines.append('  causes:')
            for cause in self.causes:
                lines.extend('  ' + line for line in str(cause).splitlines())
        return '\n'.join(lines)


def check(checks=None):
    successes = []
    failures = []
    if not checks:
        checks = CHECKS
    for check in checks:
        try:
            checker = CHECKER[check]
        except KeyError as e:
            raise InvalidCheck(check)# from e
        _sys.stdout.write('check {0}...\t'.format(checker.full_name()))
        try:
            version = checker.check()
        except DependencyError as e:
            failures.append(e)
            _sys.stdout.write('fail\n')
        else:
            _sys.stdout.write('pass\n')
            successes.append((checker, version))
    if successes:
        print('\nSuccesses:\n')
        for checker,version in successes:
            print('{0} {1}'.format(
                    checker.full_name(),
                    version or 'unknown'))
    if failures:
        print('\nFailures:')
        printed = []
        for failure in failures:
            if failure not in printed:
                print()
                print(failure)
                printed.append(failure)
        return False
    return True


class Dependency (object):
    def __init__(self, name, long_name=None, minimum_version=None,
                 version_delimiter='.', and_dependencies=None,
                 or_dependencies=None):
        self.name = name
        self.long_name = long_name or name
        self.minimum_version = minimum_version
        self.version_delimiter = version_delimiter
        if not and_dependencies:
            and_dependencies = []
        self.and_dependencies = and_dependencies
        if not or_dependencies:
            or_dependencies = []
        self.or_dependencies = or_dependencies
        self._check_error = None

    def __str__(self):
        return '<{0} {1}>'.format(type(self).__name__, self.name)

    def full_name(self):
        if self.name == self.long_name:
            return self.name
        else:
            return '{0} ({1})'.format(self.long_name, self.name)

    def check(self):
        if self._check_error:
            raise self._check_error
        try:
            self._check_dependencies()
            return self._check()
        except DependencyError as e:
            self._check_error = e  # cache for future calls
            raise

    def _check_dependencies(self):
        for dependency in self.and_dependencies:
            if not hasattr(dependency, 'check'):
                dependency = CHECKER[dependency]
            try:
                dependency.check()
            except DependencyError as e:
                raise DependencyError(
                    checker=self,
                    message=(
                        'some dependencies for {0} were not satisfied'
                        ).format(self.full_name()),
                    causes=[e])
        self.or_pass = None
        or_errors = []
        for dependency in self.or_dependencies:
            if not hasattr(dependency, 'check'):
                dependency = CHECKER[dependency]
            try:
                version = dependency.check()
            except DependencyError as e:
                or_errors.append(e)
            else:
                self.or_pass = {
                    'dependency': dependency,
                    'version': version,
                    }
                break  # no need to test other dependencies
        if self.or_dependencies and not self.or_pass:
            raise DependencyError(
                checker=self,
                message=(
                    '{0} requires at least one of the following dependencies'
                    ).format(self.full_name()),
                    causes=or_errors)

    def _check(self):
        version = self._get_version()
        parsed_version = None
        if hasattr(self, '_get_parsed_version'):
            parsed_version = self._get_parsed_version()
        if self.minimum_version:
            self._check_version(version=version, parsed_version=parsed_version)
        return version

    def _get_version(self):
        raise NotImplementedError(self)

    def _minimum_version_string(self):
        return self.version_delimiter.join(
            str(part) for part in self.minimum_version)

    def _check_version(self, version, parsed_version=None):
        if not parsed_version:
            parsed_version = self._parse_version(version=version)
        if not parsed_version or parsed_version < self.minimum_version:
            raise DependencyError(
                checker=self,
                message='outdated version of {0}: {1} (need >= {2})'.format(
                    self.full_name(), version, self._minimum_version_string()))

    def _parse_version(self, version):
        if not version:
            return None
        parsed_version = []
        for part in version.split(self.version_delimiter):
            try:
                parsed_version.append(int(part))
            except ValueError as e:
                raise DependencyError(
                    checker=self,
                    message=(
                        'unparsable {0!r} in version {1} of {2}, (need >= {3})'
                        ).format(
                        part, version, self.full_name(),
                        self._minimum_version_string()))# from e
        return tuple(parsed_version)


class PythonDependency (Dependency):
    def __init__(self, name='python', long_name='Python version',
                 minimum_version=(2, 6), **kwargs):
        super(PythonDependency, self).__init__(
            name=name, long_name=long_name, minimum_version=minimum_version,
            **kwargs)

    def _get_version(self):
        return _sys.version

    def _get_parsed_version(self):
        return _sys.version_info


CHECKER['python'] = PythonDependency()


class CommandDependency (Dependency):
    exe_extension = _distutils_ccompiler.new_compiler().exe_extension

    def __init__(self, command, paths=None, version_options=('--version',),
                 stdin=None, version_regexp=None, version_stream='stdout',
                 **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = command
        super(CommandDependency, self).__init__(**kwargs)
        self.command = command
        self.paths = paths
        self.version_options = version_options
        self.stdin = None
        if not version_regexp:
            regexp = r'([\d][\d{0}]*[\d])'.format(self.version_delimiter)
            version_regexp = _re.compile(regexp)
        self.version_regexp = version_regexp
        self.version_stream = version_stream

    def _get_command_version_stream(self, command=None, stdin=None,
                                    expect=(0,)):
        if command is None:
            command = self.command + (self.exe_extension or '')
        if not stdin:
            stdin = self.stdin
        if stdin:
            popen_stdin = _subprocess.PIPE
        else:
            popen_stdin = None
        try:
            p = _subprocess.Popen(
                [command] + list(self.version_options), stdin=popen_stdin,
                stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
                universal_newlines=True)
        except OSError as e:
            raise DependencyError(
                checker=self,
                message="could not find '{0}' executable".format(command),
                )# from e
        stdout,stderr = p.communicate(stdin)
        status = p.wait()
        if status not in expect:
            lines = [
                "failed to execute: {0} {1}".format(
                    command,
                    ' '.join(_shlex.quote(arg)
                             for arg in self.version_options)),
                'status: {0}'.format(status),
                ]
            for name,string in [('stdout', stdout), ('stderr', stderr)]:
                if string:
                    lines.extend([name + ':', string])
            raise DependencyError(checker=self, message='\n'.join(lines))
        for name,string in [('stdout', stdout), ('stderr', stderr)]:
            if name == self.version_stream:
                if not string:
                    raise DependencyError(
                        checker=self,
                        message='empty version stream on {0} for {1}'.format(
                            self.version_stream, command))
                return string
        raise NotImplementedError(self.version_stream)

    def _get_version_stream(self, **kwargs):
        paths = [self.command + (self.exe_extension or '')]
        if self.exe_extension:
            paths.append(self.command)  # also look at the extension-less path
        if self.paths:
            paths.extend(self.paths)
        or_errors = []
        for path in paths:
            try:
                return self._get_command_version_stream(command=path, **kwargs)
            except DependencyError as e:
                or_errors.append(e)
        raise DependencyError(
            checker=self,
            message='errors finding {0} version'.format(
                self.full_name()),
            causes=or_errors)

    def _get_version(self):
        version_stream = self._get_version_stream()
        match = self.version_regexp.search(version_stream)
        if not match:
            raise DependencyError(
                checker=self,
                message='no version string in output:\n{0}'.format(
                    version_stream))
        return match.group(1)


def _program_files_paths(*args):
    "Utility for generating MS Windows search paths"
    pf = _os.environ.get('ProgramFiles', '/usr/bin')
    pfx86 = _os.environ.get('ProgramFiles(x86)', pf)
    paths = [_os.path.join(pf, *args)]
    if pfx86 != pf:
        paths.append(_os.path.join(pfx86, *args))
    return paths


for command,long_name,minimum_version,paths in [
        ('sh', 'Bourne Shell', None, None),
        ('ash', 'Almquist Shell', None, None),
        ('bash', 'Bourne Again Shell', None, None),
        ('csh', 'C Shell', None, None),
        ('ksh', 'KornShell', None, None),
        ('dash', 'Debian Almquist Shell', None, None),
        ('tcsh', 'TENEX C Shell', None, None),
        ('zsh', 'Z Shell', None, None),
        ('git', 'Git', (1, 7, 0), None),
        ('hg', 'Mercurial', (2, 0, 0), None),
        ('EasyMercurial', None, (1, 3), None),
        ('pip', None, None, None),
        ('sqlite3', 'SQLite 3', None, None),
        ('nosetests', 'Nose', (1, 0, 0), None),
        ('ipython', 'IPython script', (0, 13), None),
        ('emacs', 'Emacs', None, None),
        ('xemacs', 'XEmacs', None, None),
        ('vim', 'Vim', None, None),
        ('vi', None, None, None),
        ('nano', 'Nano', None, None),
        ('gedit', None, None, None),
        ('kate', 'Kate', None, None),
        ('notepad++', 'Notepad++', None,
         _program_files_paths('Notepad++', 'notepad++.exe')),
        ('firefox', 'Firefox', None,
         _program_files_paths('Mozilla Firefox', 'firefox.exe')),
        ('google-chrome', 'Google Chrome', None,
         _program_files_paths('Google', 'Chrome', 'Application', 'chrome.exe')
         ),
        ('chromium', 'Chromium', None, None),
        ]:
    if not long_name:
        long_name = command
    CHECKER[command] = CommandDependency(
        command=command, paths=paths, long_name=long_name,
        minimum_version=minimum_version)
del command, long_name, minimum_version, paths  # cleanup namespace


class MakeDependency (CommandDependency):
    makefile = '\n'.join([
            'all:',
            '\t@echo "MAKE_VERSION=$(MAKE_VERSION)"',
            '\t@echo "MAKE=$(MAKE)"',
            '',
            ])

    def _get_version(self):
        try:
            return super(MakeDependency, self)._get_version()
        except DependencyError as e:
            version_options = self.version_options
            self.version_options = ['-f', '-']
            try:
                stream = self._get_version_stream(stdin=self.makefile)
                info = {}
                for line in stream.splitlines():
                    try:
                        key,value = line.split('=', 1)
                    except ValueError as ve:
                        raise e# from NotImplementedError(stream)
                    info[key] = value
                if info.get('MAKE_VERSION', None):
                    return info['MAKE_VERSION']
                elif info.get('MAKE', None):
                    return None
                raise e
            finally:
                self.version_options = version_options


CHECKER['make'] = MakeDependency(command='make', minimum_version=None)


class EasyInstallDependency (CommandDependency):
    def _get_version(self):
        try:
            return super(EasyInstallDependency, self)._get_version()
        except DependencyError as e:
            version_stream = self.version_stream
            try:
                self.version_stream = 'stderr'
                stream = self._get_version_stream(expect=(1,))
                if 'option --version not recognized' in stream:
                    return 'unknown (possibly Setuptools?)'
            finally:
                self.version_stream = version_stream


CHECKER['easy_install'] = EasyInstallDependency(
    command='easy_install', long_name='Setuptools easy_install',
    minimum_version=None)


CHECKER['py.test'] = CommandDependency(
    command='py.test', version_stream='stderr',
    minimum_version=None)


class PathCommandDependency (CommandDependency):
    """A command that doesn't support --version or equivalent options

    On some operating systems (e.g. OS X), a command's executable may
    be hard to find, or not exist in the PATH.  Work around that by
    just checking for the existence of a characteristic file or
    directory.  Since the characteristic path may depend on OS,
    installed version, etc., take a list of paths, and succeed if any
    of them exists.
    """
    def _get_command_version_stream(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_version_stream(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_version(self):
        for path in self.paths:
            if _os.path.exists(path):
                return None
        raise DependencyError(
            checker=self,
            message=(
                'nothing exists at any of the expected paths for {0}:\n    {1}'
                ).format(
                self.full_name(),
                '\n    '.join(p for p in self.paths)))


for paths,name,long_name in [
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Sublime Text 2.app')],
         'sublime-text', 'Sublime Text'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'TextMate.app')],
         'textmate', 'TextMate'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'TextWrangler.app')],
         'textwrangler', 'TextWrangler'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Safari.app')],
         'safari', 'Safari'),
        ([_os.path.join(_ROOT_PATH, 'Applications', 'Xcode.app'),  # OS X >=1.7
          _os.path.join(_ROOT_PATH, 'Developer', 'Applications', 'Xcode.app'
                        )  # OS X 1.6,
          ],
         'xcode', 'Xcode'),
        ]:
    if not long_name:
        long_name = name
    CHECKER[name] = PathCommandDependency(
        command=None, paths=paths, name=name, long_name=long_name)
del paths, name, long_name  # cleanup namespace


class PythonPackageDependency (Dependency):
    def __init__(self, package, **kwargs):
        if 'name' not in kwargs:
            kwargs['name'] = package
        if 'and_dependencies' not in kwargs:
            kwargs['and_dependencies'] = []
        if 'python' not in kwargs['and_dependencies']:
            kwargs['and_dependencies'].append('python')
        super(PythonPackageDependency, self).__init__(**kwargs)
        self.package = package

    def _get_version(self):
        package = self._get_package(self.package)
        return self._get_version_from_package(package)

    def _get_package(self, package):
        try:
            return _importlib.import_module(package)
        except ImportError as e:
            raise DependencyError(
                checker=self,
                message="could not import the '{0}' package for {1}".format(
                    package, self.full_name()),
                )# from e

    def _get_version_from_package(self, package):
        try:
            version = package.__version__
        except AttributeError:
            version = None
        return version


for package,name,long_name,minimum_version,and_dependencies in [
        ('nose', None, 'Nose Python package',
         CHECKER['nosetests'].minimum_version, None),
        ('pytest', None, 'pytest Python package',
         CHECKER['py.test'].minimum_version, None),
        ('jinja2', 'jinja', 'Jinja', (2, 6), None),
        ('zmq', 'pyzmq', 'PyZMQ', (2, 1, 4), None),
        ('IPython', None, 'IPython Python package',
         CHECKER['ipython'].minimum_version, ['jinja', 'tornado', 'pyzmq']),
        ('argparse', None, 'Argparse', None, None),
        ('numpy', None, 'NumPy', None, None),
        ('scipy', None, 'SciPy', None, None),
        ('matplotlib', None, 'Matplotlib', None, None),
        ('pandas', None, 'Pandas', (0, 8), None),
        ('sympy', None, 'SymPy', None, None),
        ('Cython', None, None, None, None),
        ('networkx', None, 'NetworkX', None, None),
        ('mayavi.mlab', None, 'MayaVi', None, None),
        ('setuptools', None, 'Setuptools', None, None),
        ]:
    if not name:
        name = package
    if not long_name:
        long_name = name
    kwargs = {}
    if and_dependencies:
        kwargs['and_dependencies'] = and_dependencies
    CHECKER[name] = PythonPackageDependency(
        package=package, name=name, long_name=long_name,
        minimum_version=minimum_version, **kwargs)
# cleanup namespace
del package, name, long_name, minimum_version, and_dependencies, kwargs


class MercurialPythonPackage (PythonPackageDependency):
    def _get_version(self):
        try:  # mercurial >= 1.2
            package = _importlib.import_module('mercurial.util')
        except ImportError as e:  # mercurial <= 1.1.2
            package = self._get_package('mercurial.version')
            return package.get_version()
        else:
            return package.version()


CHECKER['mercurial'] = MercurialPythonPackage(
    package='mercurial.util', name='mercurial',
    long_name='Mercurial Python package',
    minimum_version=CHECKER['hg'].minimum_version)


class TornadoPythonPackage (PythonPackageDependency):
    def _get_version_from_package(self, package):
        return package.version

    def _get_parsed_version(self):
        package = self._get_package(self.package)
        return package.version_info


CHECKER['tornado'] = TornadoPythonPackage(
    package='tornado', name='tornado', long_name='Tornado', minimum_version=(2, 0))


class SQLitePythonPackage (PythonPackageDependency):
    def _get_version_from_package(self, package):
        return _sys.version

    def _get_parsed_version(self):
        return _sys.version_info


CHECKER['sqlite3-python'] = SQLitePythonPackage(
    package='sqlite3', name='sqlite3-python',
    long_name='SQLite Python package',
    minimum_version=CHECKER['sqlite3'].minimum_version)


class UserTaskDependency (Dependency):
    "Prompt the user to complete a task and check for success"
    def __init__(self, prompt, **kwargs):
        super(UserTaskDependency, self).__init__(**kwargs)
        self.prompt = prompt

    def _check(self):
        if _sys.version_info >= (3, ):
            result = input(self.prompt)
        else:  # Python 2.x
            result = raw_input(self.prompt)
        return self._check_result(result)

    def _check_result(self, result):
        raise NotImplementedError()


class EditorTaskDependency (UserTaskDependency):
    def __init__(self, **kwargs):
        self.path = _os.path.expanduser(_os.path.join(
                '~', 'swc-installation-test.txt'))
        self.contents = 'Hello, world!'
        super(EditorTaskDependency, self).__init__(
            prompt=(
                'Open your favorite text editor and create the file\n'
                '  {0}\n'
                'containing the line:\n'
                '  {1}\n'
                'Press enter here after you have done this.\n'
                'You may remove the file after you have finished testing.'
                ).format(self.path, self.contents),
            **kwargs)

    def _check_result(self, result):
        message = None
        try:
            with open(self.path, 'r') as f:
                contents = f.read()
        except IOError as e:
            raise DependencyError(
                checker=self,
                message='could not open {0!r}: {1}'.format(self.path, e)
                )# from e
        if contents.strip() != self.contents:
            raise DependencyError(
                checker=self,
                message=(
                    'file contents ({0!r}) did not match the expected {1!r}'
                    ).format(contents, self.contents))


CHECKER['other-editor'] = EditorTaskDependency(
    name='other-editor', long_name='')


class VirtualDependency (Dependency):
    def _check(self):
        return '{0} {1}'.format(
            self.or_pass['dependency'].full_name(),
            self.or_pass['version'])


for name,long_name,dependencies in [
        ('virtual-shell', 'command line shell', (
            'bash',
            'dash',
            'ash',
            'zsh',
            'ksh',
            'csh',
            'tcsh',
            'sh',
            )),
        ('virtual-editor', 'text/code editor', (
            'emacs',
            'xemacs',
            'vim',
            'vi',
            'nano',
            'gedit',
            'kate',
            'notepad++',
            'sublime-text',
            'textmate',
            'textwrangler',
            'other-editor',  # last because it requires user interaction
            )),
        ('virtual-browser', 'web browser', (
            'firefox',
            'google-chrome',
            'chromium',
            'safari',
            )),
        ('virtual-pypi-installer', 'PyPI installer', (
            'pip',
            'easy_install',
            )),
        ]:
    CHECKER[name] = VirtualDependency(
        name=name, long_name=long_name, or_dependencies=dependencies)
del name, long_name, dependencies  # cleanup namespace


def _print_info(key, value, indent=19):
    print('{0}{1}: {2}'.format(key, ' '*(indent-len(key)), value))

def print_system_info():
    print("If you do not understand why the above failures occurred,")
    print("copy and send the *entire* output (all info above and summary")
    print("below) to the instructor for help.")
    print()
    print('==================')
    print('System information')
    print('==================')
    _print_info('os.name', _os.name)
    _print_info('os.uname', _platform.uname())
    _print_info('platform', _sys.platform)
    _print_info('platform+', _platform.platform())
    for pversion in (
            'linux_distribution',
            'mac_ver',
            'win32_ver',
            ):
        value = getattr(_platform, pversion)()
        if value[0]:
            _print_info(pversion, value)
    _print_info('prefix', _sys.prefix)
    _print_info('exec_prefix', _sys.exec_prefix)
    _print_info('executable', _sys.executable)
    _print_info('version_info', _sys.version_info)
    _print_info('version', _sys.version)
    _print_info('environment', '')
    for key,value in sorted(_os.environ.items()):
        print('  {0}={1}'.format(key, value))
    print('==================')

def print_suggestions(instructor_fallback=True):
    print()
    print('For suggestions on installing missing packages, see')
    print('http://software-carpentry.org/setup/')
    print('')
    print('For instructings on installing a particular package,')
    print('see the failure message for that package printed above.')
    if instructor_fallback:
        print('')
        print('For help, email the *entire* output of this script to')
        print('your instructor.')


if __name__ == '__main__':
    import optparse as _optparse

    parser = _optparse.OptionParser(usage='%prog [options] [check...]')
    epilog = __doc__
    parser.format_epilog = lambda formatter: '\n' + epilog
    parser.add_option(
        '-v', '--verbose', action='store_true',
        help=('print additional information to help troubleshoot '
              'installation issues'))
    options,args = parser.parse_args()
    try:
        passed = check(args)
    except InvalidCheck as e:
        print("I don't know how to check for {0!r}".format(e.check))
        print('I do know how to check for:')
        for key,checker in sorted(CHECKER.items()):
            if checker.long_name != checker.name:
                print('  {0} {1}({2})'.format(
                        key, ' '*(20-len(key)), checker.long_name))
            else:
                print('  {0}'.format(key))
        _sys.exit(1)
    if not passed:
        if options.verbose:
            print()
            print_system_info()
            print_suggestions(instructor_fallback=True)
        _sys.exit(1)

########NEW FILE########
__FILENAME__ = swc-windows-installer
#!/usr/bin/env python

"""Software Carpentry Windows Installer

Helps mimic a *nix environment on Windows with as little work as possible.

The script:
* Installs nano and makes it accessible from msysgit
* Installs sqlite3 and makes it accessible from msysGit
* Creates ~/nano.rc with links to syntax highlighting configs
* Provides standard nosetests behavior for msysgit

To use:

1. Install Python, IPython, and Nose.  An easy way to do this is with
   the Anaconda CE Python distribution
   http://continuum.io/anacondace.html
2. Install msysgit
   http://code.google.com/p/msysgit/downloads/list
3. Run swc_windows_installer.py
   You should be able to simply double click the file in Windows

"""

import hashlib
try:  # Python 3
    from io import BytesIO as _BytesIO
except ImportError:  # Python 2
    from StringIO import StringIO as _BytesIO
import os
import re
import sys
import tarfile
try:  # Python 3
    from urllib.request import urlopen as _urlopen
except ImportError:  # Python 2
    from urllib2 import urlopen as _urlopen
import zipfile


if sys.version_info >= (3, 0):  # Python 3
    open3 = open
else:
    def open3(file, mode='r', newline=None):
        if newline:
            if newline != '\n':
                raise NotImplementedError(newline)
            f = open(file, mode + 'b')
        else:
            f = open(file, mode)
        return f


def download(url, sha1):
    """Download a file and verify it's hash"""
    r = _urlopen(url)
    byte_content = r.read()
    download_sha1 = hashlib.sha1(byte_content).hexdigest()
    if download_sha1 != sha1:
        raise ValueError(
            'downloaded {!r} has the wrong SHA1 hash: {} != {}'.format(
                url, download_sha1, sha1))
    return byte_content


def splitall(path):
    """Split a path into a list of components

    >>> splitall('nano-2.2.6/doc/Makefile.am')
    ['nano-2.2.6', 'doc', 'Makefile.am']
    """
    parts = []
    while True:
        head, tail = os.path.split(path)
        if tail:
            parts.insert(0, tail)
        elif head:
            parts.insert(0, head)
            break
        else:
            break
        path = head
    return parts


def transform(tarinfo, strip_components=0):
    """Transform TarInfo objects for extraction"""
    path_components = splitall(tarinfo.name)
    try:
        tarinfo.name = os.path.join(*path_components[strip_components:])
    except TypeError:
        if len(path_components) <= strip_components:
            return None
        raise
    return tarinfo


def tar_install(url, sha1, install_directory, compression='*',
                strip_components=0):
    """Download and install a tar bundle"""
    if not os.path.isdir(install_directory):
        tar_bytes = download(url=url, sha1=sha1)
        tar_io = _BytesIO(tar_bytes)
        filename = os.path.basename(url)
        mode = 'r:{}'.format(compression)
        tar_file = tarfile.open(filename, mode, tar_io)
        os.makedirs(install_directory)
        members = [
            transform(tarinfo=tarinfo, strip_components=strip_components)
            for tarinfo in tar_file]
        tar_file.extractall(
            path=install_directory,
            members=[m for m in members if m is not None])


def zip_install(url, sha1, install_directory):
    """Download and install a zipped bundle"""
    if not os.path.isdir(install_directory):
        zip_bytes = download(url=url, sha1=sha1)
        zip_io = _BytesIO(zip_bytes)
        zip_file = zipfile.ZipFile(zip_io)
        os.makedirs(install_directory)
        zip_file.extractall(install_directory)


def install_nano(install_directory):
    """Download and install the nano text editor"""
    zip_install(
        url='http://www.nano-editor.org/dist/v2.2/NT/nano-2.2.6.zip',
        sha1='f5348208158157060de0a4df339401f36250fe5b',
        install_directory=install_directory)


def install_nanorc(install_directory):
    """Download and install nano syntax highlighting"""
    tar_install(
        url='http://www.nano-editor.org/dist/v2.2/nano-2.2.6.tar.gz',
        sha1='f2a628394f8dda1b9f28c7e7b89ccb9a6dbd302a',
        install_directory=install_directory,
        strip_components=1)
    home = os.path.expanduser('~')
    nanorc = os.path.join(home, 'nano.rc')
    if not os.path.isfile(nanorc):
        syntax_dir = os.path.join(install_directory, 'doc', 'syntax')
        with open3(nanorc, 'w', newline='\n') as f:
            for filename in os.listdir(syntax_dir):
                if filename.endswith('.nanorc'):
                    path = os.path.join(syntax_dir, filename)
                    rel_path = os.path.relpath(path, home)
                    include_path = make_posix_path(os.path.join('~', rel_path))
                    f.write('include {}\n'.format(include_path))


def install_sqlite(install_directory):
    """Download and install the sqlite3 shell"""
    zip_install(
        url='https://sqlite.org/2014/sqlite-shell-win32-x86-3080403.zip',
        sha1='1a8ab0ca9f4c51afeffeb49bd301e1d7f64741bb',
        install_directory=install_directory)


def create_nosetests_entry_point(python_scripts_directory):
    """Creates a terminal-based nosetests entry point for msysgit"""
    contents = '\n'.join([
            '#!/usr/bin/env/ python',
            'import sys',
            'import nose',
            "if __name__ == '__main__':",
            '    sys.exit(nose.core.main())',
            '',
            ])
    if not os.path.isdir(python_scripts_directory):
        os.makedirs(python_scripts_directory)
    with open(os.path.join(python_scripts_directory, 'nosetests'), 'w') as f:
        f.write(contents)


def update_bash_profile(extra_paths=()):
    """Create or append to a .bash_profile for Software Carpentry

    Adds nano to the path, sets the default editor to nano, and adds
    additional paths for other executables.
    """
    lines = [
        '',
        '# Add paths for Software-Carpentry-installed scripts and executables',
        'export PATH=\"$PATH:{}\"'.format(':'.join(
            make_posix_path(path) for path in extra_paths),),
        '',
        '# Make nano the default editor',
        'export EDITOR=nano',
        '',
        ]
    config_path = os.path.join(os.path.expanduser('~'), '.bash_profile')
    with open(config_path, 'a') as f:
        f.write('\n'.join(lines))


def make_posix_path(windows_path):
    """Convert a Windows path to a posix path"""
    for regex, sub in [
            (re.compile(r'\\'), '/'),
            (re.compile('^[Cc]:'), '/c'),
            ]:
        windows_path = regex.sub(sub, windows_path)
    return windows_path


def main():
    swc_dir = os.path.join(os.path.expanduser('~'), '.swc')
    bin_dir = os.path.join(swc_dir, 'bin')
    nano_dir = os.path.join(swc_dir, 'lib', 'nano')
    nanorc_dir = os.path.join(swc_dir, 'share', 'nanorc')
    sqlite_dir = os.path.join(swc_dir, 'lib', 'sqlite')
    create_nosetests_entry_point(python_scripts_directory=bin_dir)
    install_nano(install_directory=nano_dir)
    install_nanorc(install_directory=nanorc_dir)
    install_sqlite(install_directory=sqlite_dir)
    update_bash_profile(extra_paths=(nano_dir, sqlite_dir, bin_dir))


if __name__ == '__main__':
    print("Preparing your Software Carpentry awesomeness!")
    main()

########NEW FILE########
