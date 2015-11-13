__FILENAME__ = download_and_parse_fms_fixies
#!/usr/bin/env python
import datetime
import download_fms_fixies
import os
import pandas as pd
import pandas.io.sql
import parse_fms_fixies
import re
import sqlite3
import sys

# script must be run from fms_parser/parser directory
if not os.path.split(os.getcwd())[-1] == 'parser':
	if os.path.split(os.getcwd())[-1] == 'federal-treasury-api' or os.path.split(os.getcwd())[-1]  =='fms_parser':
		os.chdir('parser')
		print '\n*INFO: current working directory set to', os.getcwd()
	else:
		raise Exception('This script must be run from the /parser directory!')

# auto-make data directories, if not present
FIXIE_DIR = os.path.join('..', 'data', 'fixie')
DAILY_CSV_DIR = os.path.join('..', 'data', 'daily_csv')
LIFETIME_CSV_DIR = os.path.join('..', 'data', 'lifetime_csv')
os.system('mkdir -pv ' + FIXIE_DIR)
os.system('mkdir -pv ' + DAILY_CSV_DIR)
os.system('mkdir -pv ' + LIFETIME_CSV_DIR)

## DOWNLOAD! ##################################################################
# test for existence of downloaded fixies
test_fixies = sorted([f for f in os.listdir(FIXIE_DIR) if f.endswith('.txt')])
# if none, start from THE BEGINNING
if len(test_fixies) == 0:
	start_date = datetime.date(2005, 6, 9)
# else start from last available fixie date
else:
	start_date = parse_fms_fixies.get_date_from_fname(test_fixies[-1])
# always end with today
end_date = datetime.date.today()

# download all teh fixies!
download_fms_fixies.download_fixies(start_date, end_date)

# check all downloaded fixies against all parsed csvs
downloaded_files = set([fixie.split('.')[0] for fixie in os.listdir(FIXIE_DIR) if fixie.endswith('.txt')])
def parsed_files():
	return set([csv.split('_')[0] for csv in os.listdir(DAILY_CSV_DIR) if csv.endswith('.csv')])


## PARSE! #####################################################################
# fixies that have not yet been parsed into csvs
new_files = sorted(list(downloaded_files.difference(parsed_files())))

# parse all teh fixies!
for f in new_files:
	fname = os.path.join(FIXIE_DIR, f+'.txt')
	#print '\n', fname
	dfs = parse_fms_fixies.parse_file(fname, verbose=False)

	# each table for each date stored in separate csv files
	for df in dfs.values():
		try:
			t_name = df.ix[0,'table']
			t_name_match = re.search(r'TABLE [\w-]+', t_name)
			t_name_short = re.sub(r'-| ', '_', t_name_match.group().lower())
		except Exception as e:
			print '***ERROR: tables failed to parse!', e
			# go on
			continue

		daily_csv = os.path.join(DAILY_CSV_DIR, f.split('.')[0]+'_'+t_name_short+'.csv')
		df.to_csv(daily_csv, index=False, header=True, encoding='utf-8', na_rep='')

# iterate over all fms tables
for i in ['i', 'ii', 'iii_a', 'iii_b', 'iii_c', 'iv', 'v', 'vi']:

	# create the lifetime csv files it they don't exist
	lifetime_csv = os.path.join(LIFETIME_CSV_DIR, 'table_'+str(i)+'.csv')

	# if it doesn't exist
	if not os.path.isfile(lifetime_csv):
		lifetime = open(lifetime_csv, 'ab')
		# add the header
		lifetime.write(open(os.path.join(DAILY_CSV_DIR, list(parsed_files())[0]+'_table_'+str(i)+'.csv')).readline())
		lifetime.close()

	# append new csvs to lifetime csvs
	for f in new_files:

		# we have no idea why it's giving us a blank file
		if len(f) == 0: continue

		daily_csv = os.path.join(DAILY_CSV_DIR, f.split('.')[0]+'_table_'+str(i)+'.csv')
		if not os.path.isfile(daily_csv): continue

		lifetime = open(lifetime_csv, 'ab')
		daily = open(daily_csv, 'rb')

		daily.readline() # burn header
		for line in daily:
			lifetime.write(line)
		daily.close()


## SQL-IZE! ###################################################################
TABLES = [
	{
		'raw-table': 'i',
		'new-table': 't1',
	},
	{
		'raw-table': 'ii',
		'new-table': 't2',
	},
	{
		'raw-table': 'iii_a',
		'new-table': 't3a',
	},
	{
		'raw-table': 'iii_b',
		'new-table': 't3b',
	},
	{
		'raw-table': 'iii_c',
		'new-table': 't3c',
	},
	{
		'raw-table': 'iv',
		'new-table': 't4',
	},
	{
		'raw-table': 'v',
		'new-table': 't5',
	},
	{
		'raw-table': 'vi',
		'new-table': 't6',
	},
]

# delete the db and promptly rewrite it from csvs
print "INFO: building sqlite database"
db = os.path.join('..', 'data', 'treasury_data.db')
os.system("rm " + db)

connection = sqlite3.connect(db)
connection.text_factory = str # bad, but pandas doesn't work otherwise

for table in TABLES:
	df = pandas.read_csv(os.path.join('..', 'data', 'lifetime_csv', 'table_%s.csv' % table['raw-table']))

	# WARNING SERIOUS HACKS FOLLOW #
	# FILTER OUT TABLE 5 AFTER  2012-04-02 - HACK BUT WORKS FOR NOW #
	if table['new-table']=="t5":
		print "INFO: filtering out invalid dates for TABLE V (deprecated as of 2012-04-02) "
		table_v_end = datetime.date(2012, 4, 2)
		df.date = df.date.apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date())
		df = df[df.date < table_v_end]

	pandas.io.sql.write_frame(df, table['new-table'], connection)

# Commit
connection.commit()


## CELEBRATE! #################################################################
csv_txt = r"""
  ,----..    .--.--.
 /   /   \  /  /    '.       ,---.
|   :     :|  :  /`. /      /__./|
.   |  ;. /;  |  |--`  ,---.;  ; |
.   ; /--` |  :  ;_   /___/ \  | |
;   | ;     \  \    `.\   ;  \ ' |
|   : |      `----.   \\   \  \: |
.   | '___   __ \  \  | ;   \  ' .
'   ; : .'| /  /`--'  /  \   \   '
'   | '/  :'--'.     /    \   `  ;
|   :    /   `--'---'      :   \ |
 \   \ .'                   '---"
  `---`
"""
soundsystem_txt = r"""
.-. .-. . . . . .-. .-. . . .-. .-. .-. .  .
`-. | | | | |\| |  )`-.  |  `-.  |  |-  |\/|
`-' `-' `-' ' ` `-' `-'  `  `-'  '  `-' '  `
"""
welcome_msg = r"""
Everything you just downloaded is in the data/ directory.
The raw files are in data/fixie.
They were parsed and converted to CSVs in the data/daily_csv directory.
These are combined by table in the data/lifetime_csv directory.
Those tables were made into a SQLite database at data/treasury_data.db, which you can load using your favorite SQLite viewer.
If you have any questions, check out http://treasury.io for usage and a link to the support Google Group.
"""
print csv_txt
print soundsystem_txt
print '*http://csvsoundsystem.com/'
print welcome_msg

########NEW FILE########
__FILENAME__ = download_fms_fixies
#!/usr/bin/env python
import codecs
import datetime
import os
import pandas as pd
import requests
import sys

BASE_URL = 'https://www.fms.treas.gov/fmsweb/viewDTSFiles'
SAVE_DIR = os.path.join('..', 'data', 'fixie')
HOLIDAYS = [datetime.datetime.strptime(d, '%Y%m%d').date() for d in [
	'20050117', '20050221', '20050530', '20050704', '20050905', '20051010', '20051111', '20051124', '20051226',
	'20060102', '20060116', '20060220', '20060529', '20060704', '20060904', '20061009', '20061110', '20061123', '20061225',
	'20070101', '20070115', '20070219', '20070528', '20070704', '20070903', '20071008', '20071112', '20071122', '20071225',
	'20080101', '20080121', '20080218', '20080526', '20080704', '20080901', '20081013', '20081111', '20081127', '20081225',
	'20090101', '20090119', '20090216', '20090525', '20090703', '20090907', '20091012', '20091111', '20091126', '20091225',
	'20100101', '20100118', '20100215', '20100531', '20100705', '20100906', '20101011', '20101111', '20101125', '20101224',
	'20101231', '20110117', '20110221', '20110530', '20110704', '20110905', '20111010', '20111111', '20111124', '20111226',
	'20120102', '20120116', '20120220', '20120528', '20120704', '20120903', '20121008', '20121112', '20121122', '20121225',
	'20130101', '20130121', '20130218', '20130527', '20130704', '20131014', '20131111', '20131128', '20131225'
	]]

################################################################################
def check_dates(start_date, end_date):
	# fixie files not available before this date
	# PDFs *are* available, for the brave soul who wants to parse them
	earliest_date = datetime.date(2005, 6, 9)
	if start_date < earliest_date:
		print '\n**WARNING:', start_date, 'before earliest available date (',
		print str(earliest_date), ')'
		print '... setting start_date to', str(earliest_date)
		start_date = earliest_date
	if start_date > end_date:
		temp = start_date
		start_date = end_date
		end_date = temp

	return start_date, end_date

################################################################################
def generate_date_range(start_date, end_date):
	start_date, end_date = check_dates(start_date, end_date)
	dates = []
	td = datetime.timedelta(days=1)
	current_date = start_date
	while current_date <= end_date:
		dates.append(current_date)
		current_date += td
	return dates

################################################################################
def remove_weekends_and_holidays(all_dates):
	good_dates = [date for date in all_dates
				  if datetime.datetime.strftime(date, '%A') not in ['Saturday', 'Sunday']
				  and date not in HOLIDAYS]
	return good_dates

################################################################################
def request_fixie(fname):
	response = requests.get(BASE_URL,
							params={'dir': 'a',
									'fname': fname}
							)
	if response.status_code == 200:
		return response.text
	# check in working directory instead
	else:
		response = requests.get(BASE_URL,
						params={'dir': 'w',
								'fname': fname}
						)
		if response.status_code == 200:
			return response.text
		else:
			return None

################################################################################
def request_all_fixies(fnames):
	for fname in reversed(fnames):
		alt_fnames = [fname]
		alt_fnames.extend([fname[:-5] + i +'.txt' for i in ['1', '2', '3']])
		for alt_fname in alt_fnames:
			fixie = request_fixie(alt_fname)
			if fixie:
				print 'INFO: saving', os.path.join(SAVE_DIR, alt_fname)
				f = codecs.open(os.path.join(SAVE_DIR, alt_fname), 'wb', 'utf-8')
				f.write(fixie)
				f.close()
				break

		if fixie is None:
			print 'WARNING:', fname, '(',
			print str(datetime.datetime.strptime(fname[:6], '%y%m%d').date()),
			print ')', 'not available'

	return fnames

################################################################################
def download_fixies(start_date, end_date=None):
	start_date = datetime.datetime.strptime(str(start_date), '%Y-%m-%d').date()
	if end_date:
		end_date = datetime.datetime.strptime(str(end_date), '%Y-%m-%d').date()
	else:
		end_date = start_date

	all_dates = generate_date_range(start_date, end_date)
	print '\nINFO: Downloading FMS fixies from', all_dates[0], 'to', all_dates[-1], "!\n"

	good_dates = remove_weekends_and_holidays(all_dates)
	fnames = [''.join([datetime.datetime.strftime(date, '%y%m%d'), '00.txt']) for date in good_dates]
	request_all_fixies(fnames)

################################################################################
if __name__ == '__main__':
	try:
		start_date = datetime.datetime.strptime(str(sys.argv[1]), '%Y-%m-%d').date()
	except IndexError:
		print 'ERROR: must provide date as argument!'
		sys.exit()
	try:
		end_date = datetime.datetime.strptime(str(sys.argv[2]), '%Y-%m-%d').date()
	except IndexError:
		end_date = start_date

	download_fixies(start_date, end_date)



########NEW FILE########
__FILENAME__ = parse_fms_fixies
#!/usr/bin/env python
import json
import datetime
import pandas as pd
import re
import requests

# Global Vars
NORMALIZE_FIELD_TABLE = json.load(open("../parser/normalize_field_table.json"))

T4_USE_ITEMS = [
	'Tax and Loan Accounts',
	'Inter agency Transfers',
	'Federal Reserve Account Direct',
	'Federal Reserve Account Total',
	'Federal Reserve Account Depositaries'
]

ERRANT_FOOTNOTE_PATTERNS = [p for p in open("../parser/errant_footnote_patterns.txt").read().split('\n') if p is not '']

NULL_TEST_PARAMS = json.load(open("../tests/null_test_params.json"))

re_net = re.compile(".*\(.*net.*\).*", flags=re.IGNORECASE)
re_net_remove = re.compile('\(.*net.*\)', flags=re.IGNORECASE)

################################################################################
def is_errant_footnote(line):
	return any([re.search(p, line, flags=re.IGNORECASE) for p in ERRANT_FOOTNOTE_PATTERNS])

################################################################################
def normalize_fields(text, table, field):
	table_lookup = NORMALIZE_FIELD_TABLE[table]
	try:
		value_lookup = table_lookup[field]
	except KeyError:
		return text
	else:
		try:
			value = value_lookup[text]
		except KeyError:
			return text
		else:
			return value

################################################################################
def get_date_from_fname(f_name):
	raw_date = re.search(r'(\d+).txt', f_name).group(1)
	date = datetime.date(2000+int(raw_date[0:2]), int(raw_date[2:4]), int(raw_date[4:6]))
	return date


################################################################################
def get_table_name(line):
	try:
		table_line = re.search(r'\s+TABLE\s+[\w-]+.*', line).group()
		table_name = table_line.strip()
	except AttributeError:
		table_name = None
	return table_name

################################################################################
def normalize_page_text(page):
	# ignore unicode errors
	# i.e. remove superscript 3 symbols ('\xc2\xb3') by way of ignoring their errors
	# hopefully this doesn't have any undesirable side-effects
	page = re.sub("\xc2\xa0|\xc2\xb3", "", page)
	# split on line breaks, usually '\r\n' and rarely just '\n'
	lines = re.split(r'\r\n|\n', page)
	# get rid of pipe delimiters and divider lines
	lines = [re.sub(r'^ \|', '       ', line) for line in lines]
	lines = [re.sub(r'\|', '', line) for line in lines]
	lines = [re.sub(r'\s?_{5,}', '', line) for line in lines]
	# get rid of dollar signs and thousand commas
	lines = [re.sub(r'\$', '', line) for line in lines]
	lines = [re.sub(r'(\d),(\d)', r'\1\2', line) for line in lines]
	# normalize non-leading white space
	lines = [line[:6] + re.sub(r'\s{2,}', ' ', line[6:]) for line in lines]
	lines = [line.rstrip() for line in lines]
	# get rid of blank lines
	lines = [line for line in lines if line!='' and line!=' ']
	return lines

################################################################################
def get_footnote(line):
	footnote = re.search(r'^\s*(\d)\/([\w\s\./,]+.*)', line)
	if footnote:
		return [footnote.group(1), footnote.group(2)]
	return None

################################################################################
def check_fixie_url(url):
	print "INFO: checking %s to make sure it's valid" % url
	r = requests.get(url)
	if r.status_code==200:
		return url
	else:
		# what directory are we in?
		bad_dir = re.search('.*dir=([aw])$', url).group(1)
		if bad_dir == 'a':
			good_dir = 'w'
		elif bad_dir == 'w':
			good_dir = 'a'
		return re.sub("dir="+bad_dir, "dir="+good_dir, url)

################################################################################
def gen_fixie_url(f_name, date):
	# simplify file name for url creation
	new_f_name = re.sub(r'\.\./data/fixie/', '', f_name)

	# arbitrary cutoff to determine archive and working directories
	rolling_cutoff = datetime.datetime.now().date() - datetime.timedelta(days=50)
	if date < rolling_cutoff:
		f_dir = "a"
	else:
		f_dir = "w"

	# format the url
	url = "https://www.fms.treas.gov/fmsweb/viewDTSFiles?fname=%s&dir=%s" % (new_f_name, f_dir)
	
	# now lets check urls that fall within 15 days before and after our rolling cutoff
	check_cutoff_start = rolling_cutoff - datetime.timedelta(days=15)
	check_cutoff_end = rolling_cutoff + datetime.timedelta(days=15)
	if date > check_cutoff_start and date < check_cutoff_end:
		url = check_fixie_url(url)

	return url

################################################################################
def check_for_nulls(df, table):
	print "TO DO"
	# test_params = NULL_TEST_PARAMS[table]
	# null_rows = []
	# for v in test_params["values"]:
	# 	null_row = df.loc(i, ) for i in df.index if pd.isnull(df[v][i])
	# 	null_rows.append(null_row)
	# null_field_values = []
	# for f in test_params['fields']
	# 	[r[f] for r in null_rows


################################################################################
def parse_file(f_name, verbose=False):
	f = open(f_name, 'rb').read()

	#raw_tables = re.split(r'(\s+TABLE\s+[\w-]+.*)', f)
	raw_tables = re.split(r'([\s_]+TABLE[\s_]+[\w_-]+.*)', f)
	tables = []
	for raw_table in raw_tables[1:]:
		#if re.search(r'\s+TABLE\s+[\w-]+.*', raw_table):
		if re.search(r'([\s_]+TABLE[\s_]+[\w_-]+.*)', raw_table):
			table_name = raw_table
			# fix malformed fixie table names, BLERGH GOV'T!
			table_name = re.sub(r'_+', ' ', table_name)
			continue
		raw_table = table_name + raw_table
		table = normalize_page_text(raw_table)
		tables.append(table)

	# file metadata
	date = get_date_from_fname(f_name)
	url = gen_fixie_url(f_name, date)

	print 'INFO: parsing', f_name, '(', date, ')'
	dfs = {}
	for table in tables:
		table_index = tables.index(table)
		dfs[table_index] = parse_table(table, date, url, verbose=verbose)

	return dfs

################################################################################
def parse_table(table, date, url, verbose=False):

	# table defaults
	t4_total_count = 0
	indent = 0
	footnotes = {}
	index = surtype_index = type_index = subtype_index = used_index = -1
	type_indent = subtype_indent = -1
	page_number = -1
	type_ = subtype = None
	table_name = None

	# total hack for when the treasury decided to switch
	# which (upper or lower) line of two-line items gets the 0s
	# NOTE: THIS IS ONLY FOR TABLE I, BECAUSE OF COURSE
	if date > datetime.date(2013, 1, 3) or date < datetime.date(2012, 6, 1):
		two_line_delta = 1
	else:
		two_line_delta = -1

	parsed_table = []
	for i, line in enumerate(table):
		# print '|' + line + '|', '<', i, '>'
		row = {}
		# a variety of date formats -- for your convenience
		row['date'] = date
		row['year'] = date.year
		row['month'] = date.month
		row['day'] = date.day
		row['year_month'] = datetime.date.strftime(date, '%Y-%m')
		row['weekday'] = datetime.datetime.strftime(date, '%A')
		row['url'] = url

		# what's our line number? shall we bail out?
		index += 1
		if index <= used_index: continue
		indent = len(re.search(r'^\s*', line).group())

		# Rows that we definitely want to skip
		# empty rows or centered header rows
		if re.match(r'^\s{7,}', line): continue

		# page number rows
		page_number_match = re.search(r'\d+.*DAILY\s+TREASURY\s+STATEMENT.*PAGE:\s+(\d+)', line)
		if page_number_match:
			page_number = page_number_match.group(1)
			continue

		# HARD CODED HACKS
		# catch rare exceptions to the above
		if re.search(r'DAILY\s+TREASURY\s+STATEMENT', line):
			continue #ok
		# comment on statutory debt limit at end of Table III-C, and beyond
		elif re.search(r'(As|Act) of ([A-Z]\w+ \d+, \d+|\d+\/\d+\/\d+)', line) and re.search(r'(statutory )*debt( limit)*', line):
			break #ok
		# comment on whatever this is; above line may make this redundant
		elif re.search(r'\s*Unamortized Discount represents|amortization is calculated daily', line, flags=re.IGNORECASE):
			break #ok
		# more cruft of a similar sort
		elif re.search(r'billion after \d+\/\d+\/\d+', line):
			continue #ok
		elif re.search(r'.*r\-revised.*', line):
			continue #ok
		elif is_errant_footnote(line):
			break #ok

		# skip table header rows
		if get_table_name(line):
			table_name = get_table_name(line)
			continue
			
		row['table'] = table_name

		# save footnotes for later assignment to their rows
		footnote = get_footnote(line)
		
		if footnote is not None:
			# while footnote does not end in valid sentence-ending punctuation...
			i = 1
			while True:
				# get next line, if it exists
				try:
					next_line = table[index + i]
				except IndexError:
					break
				# and next line is not itself a new footnote...
				else:
					if re.search('\d+.*DAILY\s+TREASURY\s+STATEMENT.*PAGE:\s+(\d+)', next_line):
						break #ok
					if not get_footnote(next_line):
						# add next line text to current footnote
						footnote[1] = ''.join([footnote[1], next_line])
						used_index = index + i
						i += 1
					if footnote[1].endswith("program."):
						continue #ok
					elif re.search(r'[.!?]$', footnote[1]):
						break #ok

			# make our merged footnote hack official!
			footnotes[footnote[0]] = re.sub("\s{2,}", "", footnote[1])

			# if next line after footnote is not another footnote
			# it is most assuredly extra comments we don't need
			try:
				last_line = table[index + i]

			except IndexError:
				break #ok

			else:
				if re.search('\d+.*DAILY\s+TREASURY\s+STATEMENT.*PAGE:\s+(\d+)', last_line):
					continue #ok
				elif re.search(r'\.aspx\.', last_line):
					continue #ok
				elif not get_footnote(last_line):
					break #ok

			# *****THIS LINE MUST BE HERE TO ENSURE THAT FOOTNOTES AREN'T INCLUDED AS ITEMS ******#
			continue

		# note rows with footnote markers for later assignment
		if re.search(r'\d+\/', line):
			row['footnote'] = re.search(r'(\d+)\/', line).group(1)

		# separate digits and words
		digits = re.findall(r'(-{,1}\d+)', line)
		words = re.findall(r'\(\-\)|[()]|[^\W\d]+:?', line)

		# check for (-) in words => multiply all digits by -1
		if '(-)' in words:
			digits = [str((-1)*int(digit)) for digit in digits]

		# bug fix, to remove the govt's usage of 'r/' in front of numbers
		# to denote revised values, and the abhorrent usage of '(-)''
		text = ' '.join(word for word in words if word not in ['r', '(-)'])

		# get type row
		if len(digits) == 0 and text.endswith(':') and indent == 1:
			type_ = text[:-1]
			type_indent = indent
			type_index = index
			continue

		elif indent <= type_indent:
			type_ = None

		row['type'] = type_

		# special handling for table 3c
		if re.search(r'TABLE III-C', row.get('table', '')):
			if re.search(r'Less: Debt Not', text):
				subtype = 'Debt Not Subject to Limit'
				subtype_indent = indent
				subtype_index = index
				continue
			elif re.search(r'Plus: Other Debt', text):
				subtype = 'Other Debt Subject to Limit'
				subtype_indent = indent
				subtype_index = index
				continue
		# get subtype row
		elif len(digits) == 0 and text.endswith(':'):
			subtype = text[:-1]
			subtype_indent = indent
			subtype_index = index
			continue

		if index == subtype_index + 1:
			pass # possibly unnecessary
		elif indent <= subtype_indent:
			subtype = None

		row['subtype'] = subtype

		# get and merge two-line rows
		if len(digits) == 0 and not text.endswith(':'):

			if two_line_delta == 1 or not re.search(r'TABLE I\s', row.get('table', '')):

				try:
					next_line = table[index + 1]

					# check for footnotes, then note and erase them if present!
					if re.search(r'\d+\/', next_line):
						row['footnote'] = re.search(r'(\d+)\/', next_line).group(1)
						next_line = re.sub(r'\d+\/', '', next_line)

					next_digits = re.findall(r'(\d+)', next_line)
					next_words = re.findall(r'[^\W\d]+:?', next_line)

					if len(next_digits) != 0:
						text = text + ' ' + ' '.join(next_words)
						digits = next_digits
						used_index = index + 1

				except IndexError:
					pass

			elif two_line_delta == -1 and re.search(r'TABLE I\s', row.get('table', '')):

				try:
					prev_line = table[index - 1]
					prev_digits = re.findall(r'(\d+)', prev_line)
					prev_words = re.findall(r'[^\W\d]+:?', prev_line)

					if len(prev_digits) != 0:
						text = ' '.join(prev_words) + ' ' + text
						digits = prev_digits
						get_rid_of_prev_line = parsed_table.pop()

				except IndexError:
					pass

		# skip table annotations that aren't footnotes
		# this is a band-aid at best, sorry folks
		if len(digits) == 0:
			continue
		if len(text) > 80:
			continue

		row['is_total'] = int('total' in text.lower())

		# parse one table at a time...
		if re.search(r'TABLE I\s', row.get('table', '')):
			try:
				row['account_raw'] = text
				row['account'] = normalize_fields(text, 't1', 'account')
				row['close_today'] = digits[-4]
				row['open_today'] = digits[-3]
				row['open_mo'] = digits[-2]
				row['open_fy'] = digits[-1]
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE II\s', row.get('table', '')):
			try:
				row['item_raw'] = text

				# determine whether item is calculated as a net
				if re_net.search(text):
					row['is_net'] = 1
				else:
					row['is_net'] = 0

				# remove net from items
				text = re_net_remove.sub("", text).strip()

				# proceed
				row['item'] = normalize_fields(text, 't2', 'item')
				row['today'] = digits[-3]
				row['mtd'] = digits[-2]
				row['fytd'] = digits[-1]
				# tweak column names
				row['account'] = row.get('type')
				# this is a hack, deal with it :-/
				row['transaction_type'] = 'deposit'
				if int(page_number) == 3:
					row['transaction_type'] = 'withdrawal'
				# now handle items with sub-classification
				if row.get('subtype') is not None:
					row_subtype = row['subtype']
					row_item = row['item']
					row['parent_item'] = row_subtype
					row['item'] = row_item
					row['item_raw'] = row_item_raw
					row.pop('subtype')
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE III-A', row.get('table', '')):
			try:
				row['item_raw'] = text
				row['item'] = normalize_fields(text, "t3a", 'item')
				row['today'] = digits[-3]
				row['mtd'] = digits[-2]
				row['fytd'] = digits[-1]
				# tweak column names
				row['debt_type'] = row.get('type')
				# now handle items with sub-classification
				if row.get('subtype') is not None:
					row_subtype = row['subtype']
					row_item = row['item']
					row['parent_item'] = row_subtype
					row['item'] = row_item
					row['item_raw'] = row_item_raw
					row.pop('subtype')
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE III-B', row.get('table', '')):
			try:
				row['item_raw'] = text
				row['item'] = normalize_fields(text, "t3b", 'item')
				row['today'] = digits[-3]
				row['mtd'] = digits[-2]
				row['fytd'] = digits[-1]
				# tweak column names
				row['transaction_type'] = row.get('type')
				# now handle items with sub-classification
				if row.get('subtype') is not None:
					row_subtype = row['subtype']
					row_item = row['item']
					row['parent_item'] = row_subtype
					row['item'] = row_item
					row['item_raw'] = row_item_raw
					row.pop('subtype')
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE III-C', row.get('table', '')):
			try:
				row['item_raw'] = text
				row['item'] = normalize_fields(text, 't3c', 'item')
				row['close_today'] = digits[-4]
				row['open_today'] = digits[-3]
				row['open_mo'] = digits[-2]
				row['open_fy'] = digits[-1]
				# now handle items with sub-classification
				if row.get('subtype') is not None:
					row['parent_item'] = row['subtype']
					row.pop('subtype')
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE IV', row.get('table', '')):
			try:
				row['type'] = ''
				row['classification_raw'] = text
				this_class = normalize_fields(text, 't4', 'classification')
				row['classification'] = this_class
				row['today'] = digits[-3]
				row['mtd'] = digits[-2]
				row['fytd'] = digits[-1]
				# increment Total counts
				if this_class == "Total": t4_total_count += 1
				# assign source and use types
				if t4_total_count == 1 and this_class == "Total":
					row['type'] = "source"
				elif t4_total_count == 2 and this_class == "Total":
					row['type'] = "use"
				elif this_class not in T4_USE_ITEMS:
					row['type'] = "source"
				else:
					row['type'] = "use"
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE V\s', row.get('table', '')):
			try:
				row['balance_transactions'] = text
				row['depositary_type_a'] = digits[-4]
				row['depositary_type_b'] = digits[-3]
				row['depositary_type_c'] = digits[-2]
				row['total'] = digits[-1]
				# tweak column names
				row['transaction_type'] = row.get('type')
			except:
				if verbose is True:
					print 'WARNING:', line

		elif re.search(r'TABLE VI', row.get('table', '')):
			try:
				row['refund_type_raw'] = text
				row['refund_type'] = normalize_fields(text, 't6', 'classification')
				row['today'] = digits[-3]
				row['mtd'] = digits[-2]
				row['fytd'] = digits[-1]
				if '( eft )' in row.get('refund_type_raw', '').lower():
					row['refund_method'] = 'EFT'

				elif '( checks )' in row.get('refund_type_raw', '').lower():
					row['refund_method'] = 'CHECKS'
			except:
				if verbose is True:
					print 'WARNING:', line

		parsed_table.append(row)

	# assign footnotes to rows
	# and split table III-a by surtype
	for row in parsed_table:
		if row.get('footnote'):
			row['footnote'] = footnotes.get(row['footnote'])
		if row.get('item'):
			if row['item'].lower().strip() == 'total issues':
				surtype_index = parsed_table.index(row)
				row['transaction_type'] = 'issue'

	# after-the-fact surtype assignment
	if surtype_index != -1:
		for row in parsed_table[:surtype_index]:
			row['transaction_type'] = 'issue'
		for row in parsed_table[surtype_index + 1:]:
			row['transaction_type'] = 'redemption'

	# create data frame from table list of row dicts
	df = pd.DataFrame(parsed_table)

	# and pretty them up
	if re.search(r'TABLE I\s', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'is_total', 'account', 'account_raw', 'close_today', 'open_today', 'open_mo', 'open_fy', 'footnote'])
		# check_for_nulls(df, "t1")
	elif re.search(r'TABLE II\s', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'account', 'transaction_type', 'parent_item','is_total', 'is_net', 'item', 'item_raw', 'today', 'mtd', 'fytd', 'footnote'])
		if 'withdrawal' not in set(list(df['transaction_type'])):
			print "ERROR: No withdrawal items in t2 for %s" % df['date'][0]
		# check_for_nulls(df, "t2")
	elif re.search(r'TABLE III-A', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'transaction_type', 'debt_type', 'parent_item', 'is_total', 'item', 'item_raw', 'today', 'mtd', 'fytd', 'footnote'])
		# check_for_nulls(df, "t3a")
	elif re.search(r'TABLE III-B', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'transaction_type', 'parent_item', 'is_total', 'item', 'item_raw', 'today', 'mtd', 'fytd', 'footnote'])
		# check_for_nulls(df, "t3b")
	elif re.search(r'TABLE III-C', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'is_total', 'parent_item', 'item', 'item_raw', 'close_today', 'open_today', 'open_mo', 'open_fy', 'footnote'])
		# check_for_nulls(df, "t3c")
	elif re.search(r'TABLE IV', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'type', 'is_total', 'classification', 'classification_raw', 'today', 'mtd', 'fytd', 'footnote'])
		# check_for_nulls(df, "t4")
	elif re.search(r'TABLE V\s', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'transaction_type', 'is_total', 'balance_transactions', 'depositary_type_a', 'depositary_type_b', 'depositary_type_c', 'total', 'footnote'])
		# check_for_nulls(df, "t5")
	elif re.search(r'TABLE VI', row.get('table', '')):
		df = df.reindex(columns=['table', 'url', 'date', 'year_month', 'year', 'month', 'day', 'weekday', 'refund_method', 'refund_type', 'refund_type_raw', 'today', 'mtd', 'fytd', 'footnote'])
		# check_for_nulls(df, "t6")

	return df

# BJD: Does this function serve a purpose...?
def strip_table_name(table_name):
    return re.sub('[^a-zA-Z]*$', '', table_name)

########NEW FILE########
__FILENAME__ = distinct_tests
#!/usr/bin/env python
# Tested by Tom on Python 2.7.5 and Python 3.3.1 running on Arch Linux
import json
import datetime
from requests import get
from postmark import email
from collections import defaultdict
from collections import Counter
# null tests
# are there null values in any of the tables today?

today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
subject = "[treasury.io tests] distinct_tests.py | %s" % today

def query(sql):
    url = 'https://premium.scraperwiki.com/cc7znvq/47d80ae900e04f2/sql'
    r = get(url, params = {'q': sql})
    return r.json()

def gen_queries(params):
    sql_pattern = "SELECT DISTINCT(%s) as %s FROM %s"

    queries = defaultdict(list)
    for t, param in params.iteritems():
        for f in param['fields']:
            queries[t].append({
                'table': t,
                'field': f,
                'query': sql_pattern % (f, f, t)
                })
    return queries

def parse_output(q, o):
    output = defaultdict(list)
    output["table"] = q["table"]
    output["field"] = q["field"]
    for i in o:
        output["values"].append(i[f])
    return output

def test_data(output, distinct_fields):
    msgs = []
    for o in output:
        d = [d for d in distinct_fields if d['table'] == o['table'] and d['field'] == o['field']][0]
        expected = Counter(d['values'])
        found = Counter(o['values'])
        new_values = list((found - expected).elements())
        if len(new_values) > 0:
            msg = """
            <p> <strong> There are %d new values for <em>%s</em> in <em>%s</em>: </strong> </p> %s
            """  % (len(new_values), d['field'], d['table'], "<br></br>".join(new_values))

            msgs.append(msg)
    if len(msgs)==0:
        return "There are no new values in the database today."
    else:
        return "<br></br>".join(msgs)  
@email
def distinct_tests():
    print "\nINFO: Testing for new values in the dataset\n"
    # setup
    params = json.load(open('distinct_test_params.json'))
    distinct_fields = json.load(open('distinct_fields.json'))
    queries = gen_queries(params)
    output = []
    for t, qs in queries.iteritems():
        for q in qs:
            oo = query(q['query'])
            o_dict = {
            "table": q['table'],
            "field": q['field'],
            "values": sorted([o.values()[0] for o in oo if o.values()[0]])
            }
            output.append(o_dict)
    msg = test_data(output, distinct_fields)
    salutation = """ 
             <p>Hello,</p> 
             """
    postscript = """
                <p> The parameters for these tests can be set in: </p>  
                <p> https://github.com/csvsoundsystem/federal-treasury-api/blob/master/tests/distinct_fields.json </p> 
                <p> https://github.com/csvsoundsystem/federal-treasury-api/blob/master/tests/distinct_tests_params.json </p>
                <p> xoxo, </p>
                <p> \t treasury.io</p>
                """ 
    print msg
    return  subject, salutation + "<p>" + msg + "</p>" + postscript

if __name__ == '__main__':
    try:
       distinct_tests()
    except TypeError:
        pass

########NEW FILE########
__FILENAME__ = integrity_tests
#!/usr/bin/env python

from datetime import datetime, date
import pandas as pd
import os
from collections import defaultdict
import types
import re
import csv

NUM = (int, long, float, complex)
STR = (str, unicode)
NONE = (types.NoneType)
DATE = (datetime)
SIMPLE = (int, long, float, complex, str, unicode, types.NoneType)

# default date format
DATE_FORMAT = re.compile(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}")

def is_str(val):
    if pd.isnull(val):
        return "missing"
    if isinstance(val, STR):
        return "passed"
    else:
        return "failed"

def is_num(val):
    if pd.isnull(val):
        return "missing"
    elif isinstance(val, NUM):
        return "passed"
    else:
        return "failed"

def is_date(val):
    if pd.isnull(val):
        return "missing"
    elif isinstance(val, DATE):
        return "passed"
    elif isinstance(val, STR):
        if DATE_FORMAT.search(val):
            return "passed"
        else:
            return "failed"
    else:
        "failed"

def is_bool(val):
    if pd.isnull(val):
        return "missing"
    elif val in [0,1]:
        return "passed"
    elif val in[True, False]:
        return "passed"
    else:
        return "failed"

def is_table(val):
    if pd.isnull(val):
        return "missing"
    if re.match("TABLE.*", val):
        return "passed"
    else:
        return "failed"

def is_wkdy(wkdy):

    WKDYS = [
        "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Satuday", "Sunday"
    ]

    if pd.isnull(wkdy):
        return "missing"
    elif wkdy.strip() in frozenset(WKDYS):
        return "passed"
    else:
        return "failed"

def test_text_field(text):
    if pd.isnull(text):
        return "missing"
    if is_str(text):
        if re.match("[A-Za-z0-9_-: ]+", text):
            return "passed"
        else:
            return "failed"

def apply_test(val, fx):

    # run tests
    tests = [fx(v) for v in val]

    # count passed, missing, failed
    n_p = n_m = n_f = 0
    for t in tests:
        if t=='passed': n_p+=1
        elif t=='missing': n_m+=1
        else: n_f+=1

    # determine if all tests passes
    if n_m + n_f==0:
        a_t = 1
    else:
        a_t = 0

    return [n_p, n_m, n_f, a_t]

def get_missing_cols(tab, expected):
    return [c for c in tab.keys() if c not in frozenset(expected)]

def test_table_columns(tab, ti):

    T1_COLS = ['table', 'date', 'day', 'account', 'is_total', 'close_today', 'open_today', 'open_mo', 'open_fy', 'footnote']
    T23_COLS = ['table', 'date', 'day', 'account', 'type', 'subtype', 'item', 'is_total', 'today', 'mtd', 'fytd', 'footnote']
    T45_COLS = ['table', 'date', 'day', 'surtype', 'type', 'subtype', 'item', 'is_total', 'today', 'mtd', 'fytd', 'footnote']
    T6_COLS = ['table', 'date', 'day', 'type', 'item', 'is_total', 'close_today', 'open_today', 'open_mo', 'open_fy', 'footnote']
    T78_COLS = ['table', 'date', 'day', 'type', 'classification', 'is_total', 'today', 'mtd', 'fytd', 'footnote']

    # text indiviable tables for proper columns
    if ti=="t1":
        return get_missing_cols(tab, T1_COLS)
    elif ti in ["t2", "t3"]:
        return get_missing_cols(tab, T23_COLS)
    elif ti in ["t4", "t5"]:
        return get_missing_cols(tab, T45_COLS)
    elif ti=="t6":
        return get_missing_cols(tab, T6_COLS)
    elif ti in ["t7", "t8"]:
        return get_missing_cols(tab, T78_COLS)
    else:
        raise ValueError("tab index must be in \"t1\":\"t8\"")

# extract table_index
def extract_ti(fp):
    fp_re = re.compile(r"[0-9]+_([a-z0-9]{2,3})\.csv")
    return fp_re.search(fp).group(1)

#Columns to output in testing


def test_table(fp):
    tab = pd.read_csv(fp) # read in csv
    ti = extract_ti(fp) # extract tab index from filepath
    l = len(tab['table']) # number of rows for this table
    d = tab['date'][0] # the date this file was released
    missing_cols = " ".join(test_table_columns(tab, ti)).strip() # a string of missing columns
    attr = [ti, fp, l, d, missing_cols] # add static fiels to "attr"

    #output shell
    tests = []
    # add column test

    for c in tab.keys():

        if c=="table":
            tests.append(attr + [c] + apply_test(tab[c], is_table))
        # unit tests ?
        elif c=="date":
            tests.append(attr + [c] + apply_test(tab[c], is_date))

        elif c=="open_today":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="surtype":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="account":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="close_today":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="classification":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="item":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="footnote":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="open_fy":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="open_mo":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="subtype":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="mtd":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="day":
            tests.append(attr + [c] + apply_test(tab[c], is_wkdy))

        elif c=="type":
            tests.append(attr + [c] + apply_test(tab[c], is_str))

        elif c=="today":
            tests.append(attr + [c] + apply_test(tab[c], is_num))

        elif c=="fytd":
             tests.append(attr + [c] + apply_test(tab[c], is_num))
        # else:
        #     raise ValueError("%s has keys that shouldn't be in the Data Set" % fp)

    return tests

# test ALL the data
CSV_DIR = os.path.join('..', 'data', 'daily_csv')
filenames = os.listdir(CSV_DIR)
filenames.remove('.gitignore')
if filenames == []:
    raise ValueError('No daily csv files were found.')

filepaths = [os.path.join(CSV_DIR, f) for f in filenames]
o = []
for i, fp in enumerate(filepaths):
    print str(i + 1), "of", str(len(filepaths))
    try:
        o.extend(test_table(fp))
    except IndexError:
        pass
cols = [
    'tab_index', 'filepath', 'row_count', 'date', 'missing_cols',
    'variable', 'n_pass', 'n_miss', 'n_fail', 'all_true'
]
df = pd.DataFrame(o, columns=cols)
outdir = os.path.join('..', 'tests', 'test_output')
try:
    os.makedirs(outdir)
except OSError:
    pass
df.to_csv(os.path.join(outdir, date.today().isoformat() + '.csv'))

########NEW FILE########
__FILENAME__ = is_it_running
#!/usr/bin/env python
# Tested by Tom on Python 2.7.5 and Python 3.3.1 running on Arch Linux
import json
import datetime
from requests import get
from optparse import OptionParser
from postmark import email


# gmail helper

def query(sql):
    url = 'https://premium.scraperwiki.com/cc7znvq/47d80ae900e04f2/sql'
    r = get(url, params = {'q': sql})
    return r.json()

# is it running?
def date_pair(date_date):
    return {
        'days': (datetime.date.today() - date_date).days,
        'date': date_date.strftime('%A, %B %d, %Y'),
    }

def observed_data():
    sql = '''SELECT MAX(date) FROM t1;'''
    date_string = query(sql)[0]['MAX(date)']
    date_date = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()

    return date_pair(date_date)

def expected_data():
    'The date when the script should have last run'
    adate = datetime.date.today()
    adate -= datetime.timedelta(days=1)
    while adate.weekday() >= 4: # Mon-Fri are 0-4
        adate -= datetime.timedelta(days=1)
    return date_pair(adate)

@email
def is_it_running():
    print "\nINFO: Testing whether the server is running as it should\n"
    observed = observed_data()
    expected = expected_data()
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = "[treasury.io tests] is_it_running.py | %s" % today

    if (expected['days']  - observed['days']) > 3:
        msg =   """
                <p> Hello, </p>
                <p> The parser last ran on <em>%s.</em> Something is up!</p> 
                <p> xoxo, </p>
                <p> \t treasury.io</p>
                """ % expected['date']

        print "\nEMAIL: %s" % msg
        return "ERROR: " + subject, msg
        
    else:
        msg =   """
                <p> Hello, </p>
                <p> All seems well at <em>%s</em></p> 
                <p> xoxo, </p>
                <p> \t treasury.io</p>
                """ % today

        print "\nEMAIL: %s" % msg
        return subject, msg

if __name__ == '__main__':
    try:
        is_it_running()
    except TypeError:
        pass

########NEW FILE########
__FILENAME__ = null_tests
#!/usr/bin/env python
# Tested by Tom on Python 2.7.5 and Python 3.3.1 running on Arch Linux
import json
import datetime
from requests import get
from postmark import email
from collections import defaultdict
# null tests
# are there null values in any of the tables today?

today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
subject = "[treasury.io tests] null_tests.py | %s" % today

def query(sql):
    url = 'https://premium.scraperwiki.com/cc7znvq/47d80ae900e04f2/sql'
    r = get(url, params = {'q': sql})
    return r.json()

def gen_queries(params):
    sql_pattern = "SELECT %s FROM %s WHERE %s IS NULL"

    queries = defaultdict(list)
    for t, param in params.iteritems():
        for f in param['fields']:
            for v in param['values']:
                queries[t].append({
                    'table': t,
                    'field': f,
                    'ignore': param['ignore'] if param.has_key("ignore") else [],
                    'value': v,
                    'query': sql_pattern % (f, t, v)
                })
    return queries

def parse_query_results(q, results):
    if len(q['ignore']) > 0:
        for i in q['ignore']:
            if q['field']==i.keys()[0]:
                print "IGNORING: %s" % i.values()[0]
                return list(set([r[q['field']] for r in results if r[q['field']]!=i.values()[0]]))
    else:
        return list(set([r[q['field']] for r in results if r[q['field']] is not None]))

def format_err_msg(q, results):
    null_strings = "<br></br>\t".join(results)
    if null_strings is not None and len(results)>0:
        return """
            <strong><p>These are the current values of <em>%s</em> in <em>%s</em> where <em>%s</em> is NULL:</p></strong>
            <p>%s</p> 
            """ % (q['field'], q['table'], q['value'], null_strings)
    else:
        return ""

def gen_msgs(msgs):
        # generate emails
    

    if len(msgs)>0:
        salutation = """ 
                     <p>Hello,</p> 
                     <p>Here are all the null values in the treasury.io database at 
                        <em>%s</em>:
                     </p>
                     """ % today

        postscript = """
                    <p> The parameters for these tests can be set in: \r\n 
                    https://github.com/csvsoundsystem/federal-treasury-api/blob/master/tests/null_test_params.json
                    </p> 
                     <p> xoxo, </p>
                     <p> \t treasury.io</p>
                     """ 

        msg =  salutation + "<br></br>".join(msgs) + postscript
        print "\nEMAIL: %s" % msg
        return "ERROR: " + subject, msg

    else:
        msg =  """
                <p>Hello,</p> 
                <p> There are no relevant null values in the treasury.io database at <em>%s</em></p>
                <p> The parameters for these tests can be set in: <br></br>
                https://github.com/csvsoundsystem/federal-treasury-api/blob/master/tests/null_test_params.json
                </p>
                <p> Additional errant footnotes to remove may be placed here: <br></br>
                https://github.com/csvsoundsystem/federal-treasury-api/blob/master/parser/errant_footnote_patterns.txt
                </p> 
                <p> xoxo, </p>
                <p> \t treasury.io</p>
                """ % today
        print "\nEMAIL: %s" % msg
        return subject, msg

@email
def null_tests():
    print "\nINFO: Testing for null values in the dataset\n"
    # setup
    params = json.load(open('null_test_params.json'))
    queries = gen_queries(params)
    # generate error messages
    msg_list = []
    for t, qs in queries.iteritems():
        for q in qs:
            print "QUERY: %s" % q['query']
            results = query(q['query'])
            parsed_results = parse_query_results(q, results)
            msg_list.append(format_err_msg(q, parsed_results))

    # filter generated messages
    filtered_msgs = [m for m in msg_list if m is not None and m is not ""]

    return gen_msgs(filtered_msgs)

if __name__ == '__main__':
    try:
        null_tests()
    except TypeError:
        pass

########NEW FILE########
__FILENAME__ = postmark
import pystmark
import yaml

# gmail helper
def _send_email(tupl):
    subject, message = tupl
    try:
        c = yaml.safe_load(open('../postmark.yml'))
    except:
        return
    """
    a decorator to send an email

    """
    msg = pystmark.Message(sender=c['from'], to=c['to'], subject=subject,
                            html=message, tag="tests")
    response = pystmark.send(msg, api_key=c['api_key'])
    try:
      response.raise_for_status()
    except Exception as e:
      print e.message

def email(test_func):
    return _send_email(test_func())
########NEW FILE########
__FILENAME__ = test_parse_fms_fixies
#!/usr/bin/env python
import os, datetime
import re
import StringIO

import nose.tools as n
import pandas

from parse_fms_fixies import parse_file, strip_table_name

def check_parse(fixie_basename, i):
    observed_dict = parse_file(os.path.join('fixtures', fixie_basename + '.txt'), 'r')[i - 1]
    observed_csv  =  StringIO.StringIO()
    observed_dict.to_csv(observed_csv, index=False, header=True, encoding='utf-8', na_rep='')

    observed = observed_csv.getvalue()
    expected = open(os.path.join('fixtures', '%s_t%d.csv' % (fixie_basename, i ))).read()

    for o,e in zip(observed.split('\n'), expected.split('\n')):
        n.assert_equal(len(o), len(e))

def test_strip_clean_table_name():
    observed = strip_table_name(u'TABLE I Operating Cash Balance')
    assert observed == u'TABLE I Operating Cash Balance'

def test_strip_dirty_table_name():
    observed = strip_table_name(u'TABLE I Operating Cash Balance \xb3')
    assert observed == u'TABLE I Operating Cash Balance'


def test_daily_csv():
    for csv in filter(lambda f: '.csv' in f, os.listdir('fixtures')):
        basename, _, table, _= re.split(r'[_.t]', csv)
        yield check_parse, basename, int(table)

########NEW FILE########
__FILENAME__ = tweetbot
#!/usr/bin/env python
import humanize
import math
import datetime
import bitly_api
from optparse import OptionParser
import os, re, yaml, json
import tweepy
from random import choice
from json import load
from urllib2 import urlopen
from urllib import urlencode
from pandas import DataFrame
from requests import get

######################################
# HELPERS
######################################
T_IO = "http://treasury.io"

def load_options():
    parser = OptionParser()
    parser.add_option("-t", "--tweet-type", dest="tweet_type", default="total_debt",
                  help="write report to FILE", metavar="FILE")
    (options, args) = parser.parse_args()
    return options

# Helpers to humanize numbers / dates
def human_number(num):
    n = humanize.intword(int(math.ceil(num))).lower()
    if re.search(r"^(\d+)\.0 ([A-Za-z]+)$", n):
        m = re.search(r"^(\d+)\.0 ([A-Za-z]+)$", n)
        n = m.group(1) + " " + m.group(2)
    return n

def human_date(date):

    def style_day(n):
        n = int(n)
        return str(n)+("th" if 4<=n%100<=20 else {1:"st",2:"nd",3:"rd"}.get(n%10, "th"))

    # apply humanization fx
    h = humanize.naturalday(datetime.datetime.strptime(date, "%Y-%m-%d")).title()

    # remove zeros
    m0 = re.search(r"([A-Za-z]+) 0([0-9])", h)
    if m0: h = "%s %s" % ( m0.group(1), m0.group(2) )

    # style day
    m_day = re.search(r"([A-Za-z]+) (\d+)", h)
    if m_day: h = "%s %s" % ( m_day.group(1), style_day(m_day.group(2)) )

    # lowercase yesterday and today
    if h in ['Yesterday', 'Today']: h = h.lower()

    return h

def gen_bitly_link(long_url):
    try:
        access_token = yaml.safe_load(open("%s/%s" % (os.getenv("HOME"), 'bitly.yml')))['access_token']
    except:
        return long_url
    else:
        if access_token is None:
            return long_url
        else:
            btly = bitly_api.Connection(access_token = access_token)
            blob = btly.shorten(long_url)
            return re.sub("http://", "", str(blob['url']))

######################################
# DATA
######################################

def query(sql):
    '''
    Submit an `sql` query (string) to treasury.io and return a pandas DataFrame.

    For example::

        print('Operating cash balances for May 22, 2013')
        print(treasury.io('SELECT * FROM "t1" WHERE "date" = \'2013-05-22\';'))
    '''
    url = 'https://premium.scraperwiki.com/cc7znvq/47d80ae900e04f2/sql/'
    query_string = urlencode({'q':sql})
    handle = urlopen(url + '?' + query_string)
    if handle.code == 200:
        d = load(handle)
        return DataFrame(d)
    else:
        raise ValueError(handle.read())

######################################
# TWITTER
######################################

def connect_to_twitter(config = os.path.expanduser("~/.twitter.yml")):
    conf = yaml.safe_load(open(config))
    auth = tweepy.OAuthHandler(conf['consumer_key'], conf['consumer_secret'])
    auth.set_access_token(conf['access_token'], conf['access_token_secret'])
    api = tweepy.API(auth)
    return api

def tweet(tweet_text_func):
    '''
    A decorator to make a function Tweet

    Parameters

    - `tweet_text_func` is a function that takes no parameters and returns a tweetable string

    For example::

        @tweet
        def total_deposits_this_week():
            # ...

        @tweet
        def not_an_interesting_tweet():
            return 'This tweet is not data-driven.'
    '''
    def tweet_func():
        api = connect_to_twitter()
        tweet = tweet_text_func()
        print "Tweeting: %s" % tweet
        try:
            api.update_status(tweet)
        except tweepy.error.TweepError as e:
            print e
            pass
        else:
            return tweet

    return tweet_func

######################################
# TWEETS
######################################
T2_ITEM_DICT = {
    "Unemployment": "Unemployment",
    "Education Department programs": "the Education Dept.",
    "Energy Department programs": "the Energy Dept.",
    "Medicaid": "Medicaid",
    "Medicare": "Medicare",
    "Social Security Benefits ( EFT )": "social security benefits",
    "NASA programs": "NASA",
    "Housing and Urban Development programs": "housing and urban development programs",
    "Justice Department programs": "justice dept. programs",
    "Postal Service": "the postal service",
    "Defense Vendor Payments ( EFT )": "military contractors",
    "Federal Employees Insurance Payments": "fed. employees ins. payments",
    "Fed Highway Administration programs": "the federal hwy admin",
    "Federal Salaries ( EFT )": "federal salaries",
    "Food Stamps": "food stamps",
    "Postal Service Money Orders and Other": "postal service money orders",
    "Interest on Treasury Securities": "interest on treasury securities",
    "Temporary Assistance for Needy Families ( HHS )": "Welfare",
    "Veterans Affairs Programs": "veterans affairs programs",
    "Air Transport Security Fees": "air transport security fees",
    "Railroad Unemployment Ins": "railroad unemployement insurance",
    "FSA Tobacco Assessments": "Tobacco Taxes",
    "Agency for International Development": "USAID",
    "Securities and Exchange Commission": "the SEC",
    "Natl Railroad Retirement Inv Trust": "the Nat'l Railroad Retirement Inv. Trust",
    "Federal Communications Commission": "the FCC",
    "SEC: Stock Exchange Fees": "stock exchange fees",
    "Environmental Protection Agency": "the EPA",
    "IRS Tax Refunds Business ( EFT )": "tax refunds for businesses",
    "IRS Tax Refunds Individual ( EFT )": "tax refunds for individuals",
    "Military Active Duty Pay ( EFT )": "military active duty pay",
    "Veterans Benefits ( EFT )": "veterans benefits",
    "State Department": "the State dept.",
    "Library of Congress": "the Lib. of Congress",
    "Federal Trade Commission": "the FTC",
    "Transportation Security Admin ( DHS )": "the TSA",
    "TARP": "TARP",
    "Interior": "Interior",
    "USDA: Forest Service": "the forest service"
}

@tweet
def random_comparison_tweet():

    df = query('''SELECT date, item, fytd, url
                  FROM t2
                  WHERE transaction_type = 'withdrawal' AND date = (SELECT max(date) FROM t2)''')

    # get two random items to compare
    item_1_df = df[df.item==choice([i for i in df.item if i in set(T2_ITEM_DICT.keys())])]
    item_2_df = item_1_df
    while item_2_df.item == item_1_df.item:
        item_2_df = df[df.item==choice([i for i in df.item if i in set(T2_ITEM_DICT.keys())])]

    item_1 = T2_ITEM_DICT[str([i for i in item_1_df.item][0])]
    item_2 = T2_ITEM_DICT[str([i for i in item_2_df.item][0])]

    # detmine diff and value
    if int(item_1_df.fytd) > int(item_2_df.fytd):
        per_diff = 100*(float(item_1_df.fytd) / float(item_2_df.fytd))

    else:
        per_diff = 100*(float(item_2_df.fytd) / float(item_1_df.fytd))

        # switch item 1 and 2
        item_3 = item_1
        item_1 = item_2
        item_2 = item_3

    per = str(int(math.ceil(per_diff))) + "%"
    btly = gen_bitly_link(str(df['url'][0]))
    vals = (per, item_1, item_2, btly)

    return "The US Gov has spent %s more on %s than on %s this fiscal year - %s" % vals

@tweet
def random_item_tweet():

    df = query('''SELECT date, item, today, transaction_type, url
                  FROM t2
                  WHERE date = (SELECT max(date) FROM t2)''')

    the_df = df[df.item==choice([i for i in df.item if i in set(T2_ITEM_DICT.keys())])]

    # determine change
    if len(the_df) == 1:
        if the_df['transaction_type'] == "deposit":
            change = "took in"
            preposition = "from"
        elif the_df['transaction_type'] == "withdrawal":
            change = "spent"
            preposition = "on"
        val = int(the_df['today'])
    else:
        val = sum(the_df[the_df.transaction_type == 'deposit']['today']) - sum(the_df[the_df.transaction_type == 'withdrawal']['today'])
        if val > 0:
            change = "took in"
            preposition = "from"
        else:
            change = "spent"
            preposition = "on"

    # gen values
    btly = gen_bitly_link(df['url'][0])
    the_date = human_date(df['date'][0])
    if the_date in ["Yesterday", "Today"]:
        intro = ""
    else:
        intro = "On "
    the_val = human_number(abs(val*1e6))
    the_item = T2_ITEM_DICT[str([i for i in the_df.item][0])]
    vals = (intro, the_date, change, the_val, preposition, the_item, btly, T_IO)
    return "%s%s, the US Gov %s $%s %s %s %s \r\n - %s" % vals

@tweet
def total_debt_tweet():
    df = query('''SELECT date, close_today, url
                  FROM t3c
                  WHERE (item LIKE \'%subject to limit%\' AND year = 2013 AND month >=1)
                  ORDER BY date DESC''')

    # determine length of DataFrame
    end = len(df)-1

    # extract current amount and amount at the beginning of the year
    current_amt = df['close_today'][0]*1e6
    previous_amt = df['close_today'][end]*1e6

    # calculate change
    delta = abs(current_amt - previous_amt)

    # generate word to represnet the direction of change
    if current_amt > previous_amt:
        change = "increased"
    elif current_amt < previous_amt:
        change = "decreased"

    # humanize values
    # Notice the included ``human_date`` and ``human_number`` functions which simplify these values for you
    btly = gen_bitly_link(df['url'][0])
    current_date = human_date(df['date'][0])
    amt = human_number(current_amt)
    delta = human_number(delta)
    previous_date = human_date(df['date'][end])

    # generate tweet
    vals = (current_date, amt, btly, T_IO)
    return "Think you're in debt? As of %s, the US Gov is $%s in the hole! %s \r\n - %s" % vals

def dist_to_debt_ceiling_tweet():

    df = query('''SELECT a.date, a.close_today AS debt_ceiling,
                          b.close_today AS debt_subject_to_ceiling,
                          a.close_today - b.close_today as distance_from_debt_ceiling
                   FROM t3c a
                   INNER JOIN t3c b ON a.date = b.date
                   WHERE a.item = "Statutory Debt Limit" AND b.item = "Total Public Debt Subject to Limit"
                   AND a.year = "2008"
                   ORDER BY a.date DESC
                   LIMIT 100
                ''')

@tweet
def change_in_balance_tweet():
    df = query('''SELECT close_today - open_today AS change, date, weekday, url
                   FROM t1
                   WHERE account = 'Total Operating Balance'
                   ORDER BY date DESC
                   LIMIT 1''')

    # calculate change
    raw_amt = df['change'][0]
    if raw_amt < 0:
        change = "dropped"
    elif raw_amt > 0:
        change = "rose"

    # humanize number and date
    amt = human_number(abs(raw_amt)*1e6)
    btly = gen_bitly_link(df['url'][0])
    the_date = human_date(df['date'][0])

    # generate tweet
    vals = (change, amt, the_date, btly, T_IO)
    return "The US Gov's total operating balance %s $%s on %s %s \r\n - %s" % vals

@tweet
def is_it_running_tweet():

    def date_pair(date_date):
        return {
            'days': (datetime.date.today() - date_date).days,
            'date': date_date,
        }

    def observed_data():
        url = 'https://premium.scraperwiki.com/cc7znvq/47d80ae900e04f2/sql'
        sql = '''SELECT MAX(date) AS max_date FROM t1;'''

        r = get(url, params = {'q': sql})
        date_string = json.loads(r.text)[0]['max_date']
        date_date = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()

        return date_pair(date_date)

    def expected_data():
        'The date when the script should have last run'
        adate = datetime.date.today()
        adate -= datetime.timedelta(days=1)
        while adate.weekday() >= 4: # Mon-Fri are 0-4
            adate -=  datetime.timedelta(days=1)
        return date_pair(adate)

    def gen_test_tweet():
        peeps = "@brianabelson @mhkeller @jbialer @thomaslevine @bdewilde @Cezary"
        current_date = datetime.datetime.now()

        observed = observed_data()
        expected = expected_data()

        if observed['days'] > 7:
            return "Yo %s! Something is probably wrong - @%s" % (peeps, current_date.date().strftime("%S"))
        elif observed['days']  - expected['days'] > 3:
            return "Hey %s, something might be wrong unless %s is a holiday! " % (peeps, expected['date'].strftime("%B %d"))
        else:
            return None

    return gen_test_tweet()

######################################
# SELECTOR
######################################

if __name__ == '__main__':

    options = load_options()
    t = options.tweet_type

    if t == 'total_debt':
        total_debt_tweet()
    elif t == 'change_in_balance':
        change_in_balance_tweet()
    elif t == 'is_it_running':
        is_it_running_tweet()
    elif t == 'random_item':
        random_item_tweet()
    elif t == 'random_comparison':
        random_comparison_tweet()


########NEW FILE########
__FILENAME__ = update_urls
import pandas as pd
import requests
from Queue import Queue
from threading import Thread
import logging

log = logging.getLogger(__name__)


def threaded(items, func, num_threads=5, max_queue=200):
    def queue_consumer():
        while True:
            try:
                item = queue.get(True)
                func(item)
            except Exception, e:
                log.exception(e)
            except KeyboardInterrupt:
                raise
            except:
                pass
            finally:
                queue.task_done()

    queue = Queue(maxsize=max_queue)

    for i in range(num_threads):
        t = Thread(target=queue_consumer)
        t.daemon = True
        t.start()

    for item in items:
        queue.put(item, True)

    queue.join()
########NEW FILE########
