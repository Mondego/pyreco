__FILENAME__ = ColorStreamHandler
import logging
import curses

class ColorStreamHandler(logging.Handler):

	def __init__(self, use_colors):
		logging.Handler.__init__(self)
		self.use_colors = use_colors

		# Initialize environment
		curses.setupterm()

		# Get the foreground color attribute for this environment
		self.fcap = curses.tigetstr('setaf')

		#Get the normal attribute
		self.COLOR_NORMAL = curses.tigetstr('sgr0')

		# Get + Save the color sequences
		self.COLOR_INFO = curses.tparm(self.fcap, curses.COLOR_GREEN)
		self.COLOR_ERROR = curses.tparm(self.fcap, curses.COLOR_RED)
		self.COLOR_WARNING = curses.tparm(self.fcap, curses.COLOR_YELLOW)
		self.COLOR_DEBUG = curses.tparm(self.fcap, curses.COLOR_BLUE)

	def color(self, msg, level):
		if level == "INFO":
			return "%s%s%s" % (self.COLOR_INFO, msg, self.COLOR_NORMAL)
		elif level == "WARNING":
			return "%s%s%s" % (self.COLOR_WARNING, msg, self.COLOR_NORMAL)
		elif level == "ERROR":
			return "%s%s%s" % (self.COLOR_ERROR, msg, self.COLOR_NORMAL)
		elif level == "DEBUG":
			return "%s%s%s" % (self.COLOR_DEBUG, msg, self.COLOR_NORMAL)
		else:
			return msg
	
	def emit(self, record):
		record.msg = record.msg.encode('utf-8', 'ignore')
		msg = self.format(record)

		# This just removes the date and milliseconds from asctime
		temp = msg.split(']')
		msg = '[' + temp[0].split(' ')[1].split(',')[0] + ']' + temp[1]

		if self.use_colors:
			msg = self.color(msg, record.levelname)
		print msg

# 'record' has the following attributes:
# threadName
# name
# thread
# created
# process
# processName
# args
# module
# filename
# levelno
# exc_text
# pathname
# lineno
# msg
# exc_info
# funcName
# relativeCreated
# levelname
# msecs
########NEW FILE########
__FILENAME__ = content_processor
from multiprocessing import Pool
import re, sys, logging, string

from ready_queue import ready_queue

logger = logging.getLogger("crawler_logger")

def rankKeywords(text):
	invalid_keywords = ['', ' ', "i", "a", "an", "and", "the", "for", "be", "to", "or", "too", "also"]
	ranks = {}
	text = text.split(' ')
	exclude = set(string.punctuation)
	for t in text:
		#remove punctuation if attached to word
		temp = t
		t = ''
		for i in range(len(temp)):
			if(temp[i] not in exclude):
				t += temp[i]
		t = t.strip()
		if t in invalid_keywords:
			continue
		if not ranks.has_key(t):
			ranks[t] = 1
		else:
			ranks[t] += 1 
	return ranks

def stripPunctuation(text):
	pattern = re.compile(r'[^\w\s]')
	return pattern.sub(' ', text)

def stripScript(text):
	pattern = re.compile(r'<script.*?\/script>')
	return pattern.sub(' ', text)

class ContentProcessor:
	
	def __init__(self, url, status, text):
		self.keyword_dicts = []
		self.invalid_keywords = ['', ' ', "i", "a", "an", "and", "the", "for", "be", "to", "or", "too", "also"]
		self.keywords = {}
		self.text = text
		self.size = 0
		self.url = url
		self.status = status

	def setText(self, text):
		self.text = text
		self.size = len(text)

	def setUrl(self, url):
		self.url = url

	def setStatus(self, status):
		self.status = status

	def setInfo(self, url, status, text):
		self.url = url
		self.status = status
		self.text = text
		self.size = len(text)

	def reset(self):
		self.keyword_dicts = []
		self.keywords = {}
		self.text = None
		self.head = None
		self.body = None
		self.title = None
		self.size = 0
		self.status = None

	def combineKeywordLists(self):
		if len(self.keyword_dicts) == 1:
			self.keywords = self.keyword_dicts[0]
			return
		for l in self.keyword_dicts:
			for k,v in l.items():
				if self.keywords.has_key(k):
					self.keywords[k] += v
				else:
					self.keywords[k] = v
	
	# returns links to queue	
	def processBody(self):
		queue = ready_queue(self.url, self.body)
		#print "found %i links to queue" % len(queue)
		self.text = stripPunctuation(self.remove_html_tags(stripScript(self.body)))
		if len(self.text) > 5000:
			offset = 0
			i = 0
			l = []
			cont = True
			while cont:
				#this divides the text into sets of 500 words
				#set j to the index of the last letter of the 500th word
				j = self.findnth(self.text[i:],' ',500)
				#if only 500 words or less are left
				if j == -1:
					cont = False
				#Should append a string that contains 500 words for each loop(except the last loop) to l
				#last loop should append a string with 500 words or less to l
				l.append(self.text[i:i+j])
				i += j+1
			logger.debug("processing with %i threads" % len(l))
			try:
				if len(l) == 0:
					return []
				pool = Pool(processes=(len(l)))
				self.keyword_dicts = pool.map(rankKeywords, l)
			except KeyboardInterrupt:
				pool.terminate()
				pool.join()
				sys.exit()
			else:
				pool.close()
				pool.join()
			logger.debug("processed, returned %i dicts" % len(self.keyword_dicts))
		else:
			self.keyword_dicts.append(rankKeywords(self.text))
		return queue
		
	def processHead(self):
		pass

	def remove_html_tags(self, data):
		p = re.compile(r'<.*?>')
		return p.sub('', data)

	def findnth(self, haystack, needle, n):
		parts = haystack.split(needle, n)
		if len(parts) <= n:
			return -1
		return len(haystack)-len(parts[-1])-len(needle)

	# returns the queue from processBody
	def process(self):
		text_lower = self.text.lower()
		self.title = self.text[text_lower.find('<title')+6:text_lower.find('</title>')]
		self.head = self.text[text_lower.find('<head')+5:text_lower.find('</head>')]
		self.processHead()
		self.body = self.text[text_lower.find('<body'):text_lower.find('</body>')]
		queue = self.processBody()
		self.combineKeywordLists()
		return queue

	def getDataDict(self):
		for k,v in self.keywords.items():
			if v < 3:
				del self.keywords[k]
		return {"address":self.url, "title":self.title, "status":self.status, "size":self.size, "keywords":self.keywords}

########NEW FILE########
__FILENAME__ = PyCrawler
from query import CrawlerDb
from content_processor import ContentProcessor
from settings import LOGGING
import sys, urlparse, urllib2, shutil, glob, robotparser
import logging, logging.config
import traceback

# ===== Init stuff =====

# db init
cdb = CrawlerDb()
cdb.connect()

# content processor init
processor = ContentProcessor(None, None, None)

# logging setup
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("crawler_logger")

# robot parser init
robot = robotparser.RobotFileParser()

if len(sys.argv) < 2:
	logger.info("Error: No start url was passed")
	sys.exit()

l = sys.argv[1:]

cdb.enqueue(l)

def crawl():
	logger.info("Starting (%s)..." % sys.argv[1])
	while True:
		url = cdb.dequeue()
		u = urlparse.urlparse(url)
		robot.set_url('http://'+u[1]+"/robots.txt")
		if not robot.can_fetch('PyCrawler', url.encode('ascii', 'replace')):
			logger.warning("Url disallowed by robots.txt: %s " % url)
			continue
		if not url.startswith('http'):
			logger.warning("Unfollowable link found at %s " % url)
			continue

		if cdb.checkCrawled(url):
			continue
		if url is False:
			break
		status = 0
		req = urllib2.Request(str(url))
		req.add_header('User-Agent', 'PyCrawler 0.2.0')
		request = None

		try:
			request = urllib2.urlopen(req)
		except urllib2.URLError, e:
			logger.error("Exception at url: %s\n%s" % (url, e))
			continue
		except urllib2.HTTPError, e:
			status = e.code
		if status == 0:
			status = 200
		data = request.read()
		processor.setInfo(str(url), status, data)
		ret = processor.process()
		if status != 200:
			continue
		add_queue = []
		for q in ret:
			if not cdb.checkCrawled(q):
				add_queue.append(q)

		processor.setInfo(str(url), status, data)
		add_queue = processor.process()
		l = len(add_queue)
		logger.info("Got %s status from %s (Found %i links)" % (status, url, l))
		if l > 0:
			cdb.enqueue(add_queue)	
		cdb.addPage(processor.getDataDict())
		processor.reset()

	logger.info("Finishing...")
	cdb.close()
	logger.info("Done! Goodbye!")

if __name__ == "__main__":
	try:
		crawl()
	except KeyboardInterrupt:
		logger.error("Stopping (KeyboardInterrupt)")
		sys.exit()
	except Exception, e:
		logger.error("EXCEPTION: %s " % e)
		traceback.print_exc()
	

########NEW FILE########
__FILENAME__ = query
from datetime import datetime

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, select

import settings

class CrawlerDb:

	def __init__(self):
		self.connected = False

	def connect(self):
		e = settings.DATABASE_ENGINE + "://"
		p = ""
		if settings.DATABASE_ENGINE == "mysql":
			e += settings.DATABASE_USER + ":" + settings.DATABASE_PASS + "@"
			p = ":" + settings.DATABASE_PORT

		e += settings.DATABASE_HOST + p
		if settings.DATABASE_ENGINE != "sqlite":
			e += "/" +settings.DATABASE_NAME
		self.engine = create_engine(e)
		self.connection = self.engine.connect()
		self.connected = True if self.connection else False
		self.metadata = MetaData()

		# Define the tables
		self.queue_table = Table('queue', self.metadata,
			Column('id', Integer, primary_key=True),
			Column('address', String, nullable=False),
			Column('added', DateTime, nullable=False, default=datetime.now())
		)

		self.crawl_table = Table('crawl', self.metadata,
			Column('id', Integer, primary_key=True),
			Column('address', String, nullable=False),
			Column('http_status', String, nullable=False),
			Column('title', String, nullable=True),
			Column('size', Integer, nullable=True),

		)

		self.keyword_table = Table('keywords', self.metadata,
			Column('id', Integer, primary_key=True),
			Column('page_id', None, ForeignKey('crawl.id')),
			Column('keyword', String, nullable=False),
			Column('weight', Integer, nullable=False),
		)

		# Create the tables
		self.metadata.create_all(self.engine)


	def enqueue(self, urls):
		if not self.connected:
			return False
		if len(urls) == 0:
			return True
		args = [{'address':u.decode("utf8")} for u in urls]
		result = self.connection.execute(self.queue_table.insert(), args)
		if result:
			return True
		return False

	def dequeue(self):
		if not self.connected:
			return False
		# Get the first thing in the queue
		s = select([self.queue_table]).limit(1)
		res = self.connection.execute(s)
		result = res.fetchall()
		res.close()
		# If we get a result
		if len(result) > 0:
			# Remove from the queue
			delres = self.connection.execute(self.queue_table.delete().where(self.queue_table.c.id == result[0][0]))
			if not delres:
				return False
			# Return the row
			return result[0][1]
		return False
	
	def checkCrawled(self, url):
		s =  select([self.crawl_table]).where(self.crawl_table.c.address == url.decode("utf8"))
		result = self.connection.execute(s)
		if len(result.fetchall()) > 0:
			result.close()
			return True
		else:
			result.close()
			return False

	# Data should be a dictionary containing the following
	# key : desc
	# 	address : the url of the page
	# 	http_status : the status code returned by the request
	# 	title : the contents of the <title> element
	# 	size : the of the returned content in bytes
	def addPage(self, data):
		if not self.connected:
			return False
		# Add the page to the crawl table
		try:
			result = self.connection.execute(self.crawl_table.insert().values(address=unicode(data['address']),http_status=data['status'],title=unicode(data['title']),size=data['size']))
		except UnicodeDecodeError:
			return False
		if not result:
			return False
		# generate list of argument dictionaries for the insert many statement
		args = [{"page_id":result.inserted_primary_key[0], "keyword":unicode(k), "weight":w} for k,w in data["keywords"].items()]
		# Add all the keywords
		if len(args) > 0:
			result2 = self.connection.execute(self.keyword_table.insert(),args)
			if not result2:
				return False
		return True

	def close(self):
		self.connection.close()

########NEW FILE########
__FILENAME__ = ready_queue
import re, urlparse

linkregex = re.compile('<a\s(?:.*?\s)*?href=[\'"](.*?)[\'"].*?>')

def ready_queue(address, html):
	url = urlparse.urlparse(str(address))
	links = linkregex.findall(html)
	queue = []
	for link in links:
		if link.startswith("/"):
			queue.append('http://'+url[1]+link)
		elif link.startswith("http") or link.startswith("https"):
			queue.append(link)
		elif link.startswith("#"):
			continue
		else:
			queue.append(urlparse.urljoin(url.geturl(),link))
	return queue
	
########NEW FILE########
__FILENAME__ = settings
import logging

DATABASE_ENGINE = "sqlite"		# sqlite or mysql
DATABASE_NAME = "PyCrawler"		# Database name
DATABASE_HOST = "/PyCrawler.db"	# Host address of mysql server or file location of sqlite db
DATABASE_PORT = ""				# Port number as a string. Not used with sqlite
DATABASE_USER = ""				# Not used with sqlite
DATABASE_PASS = ""				# Not used with sqlite

DEBUG = True 					# Whether or not to show DEBUG level messages
USE_COLORS = True 				# Whether or not colors should be used when outputting text

LOGGING = {						# dictConfig for output stream and file logging
	'version': 1,              
    'disable_existing_loggers': False,

	'formatters': {
		'console': {
			'format': '[%(asctime)s] %(levelname)s::%(module)s - %(message)s',
		},
		'file': {
			'format': '[%(asctime)s] %(levelname)s::(P:%(process)d T:%(thread)d)::%(module)s - %(message)s',
		},
	},

	'handlers': {
		'console': {
			'class': 'ColorStreamHandler.ColorStreamHandler',
			'formatter':'console',
			'level': 'DEBUG',
			'use_colors': USE_COLORS,
		},
		'file': {
			'class': 'logging.handlers.TimedRotatingFileHandler',
			'formatter':'file',
			'level': 'INFO',
			'when': 'midnight',
			'filename': 'pycrawler.log',
			'interval': 1,
			'backupCount': 0,
			'encoding': None,
			'delay': False,
			'utc': False,
		},
	},

	'loggers': {
		'crawler_logger': {
			'handlers': ['console', 'file'],
			'level': 'DEBUG' if DEBUG else 'INFO',
			'propagate': True,
		},
	}
}   
########NEW FILE########
