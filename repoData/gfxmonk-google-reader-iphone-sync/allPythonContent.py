__FILENAME__ = feeditem
class FeedItem(object):
	def __init__(self, attrs):
		for k,v in attrs:
			setattr(self, k, v)
	
	def html(self):
			# self.feed_name = tag_name
			# self.tag_name = tag_name
			# self.title = strip_html_tags(feed_item['title'])
			# self.title = unicode(BeautifulSoup(self.title, convertEntities = BeautifulSoup.HTML_ENTITIES))
			# self.google_id = feed_item['google_id']
			# self.date = time.strftime('%Y%m%d%H%M%S', time.localtime(float(feed_item['updated'])))
			# self.is_read = 'read' in feed_item['categories']
			# self.is_starred = 'starred' in feed_item['categories']
			# self.is_shared = 'broadcast' in feed_item['categories']
			# self.url = feed_item['link']
			# self.content = feed_item['content']
			# self.original_id = feed_item['original_id']
			# self.media = try_lookup(feed_item, 'media')
			# self.is_dirty = False
		return """
			<html>
				<head>
					<link rel='stylesheet' href='template/style.css' type='text/css' />
				</head>
				<body>
					<div class='post-info header'>
						<h1 id='title'>
							<a href='%s'>%s</a>""" % (self.url, self.title) + """
						</h1>
						<div class='via'>
							%s""" % (self.feed_name,) + """
						</div>
					</div>
					<div class='content'><p>
						%s""" % (self.content,) + """
					</div>
					<div class='post-info footer'>
						<div class='date'>
							<b>%s</b> in <b>%s</b>""" % (self.date, self.tag_name) + """
						</div>
						<div>
							(<i>%s</i>)""" % (self.url,) + """
						</div>
					</div>
				</body>
			</html>"""

########NEW FILE########
__FILENAME__ = main
#!/opt/local/bin/python2.5
# to run (in vim)
# !`pwd`/%
import sys
import os
import urllib

import gtk
import gobject
import webkit

class Gris(object):
	def __init__(self):
		self.folders = ("images", "text", "foo")
		self.init_ui()

	def on_window_destroy(self, widget, data=None):
		gtk.main_quit()
	
	def init_ui(self):
		builder = gtk.Builder()
		builder.add_from_file("main.glade")

		def set_object(name):
			setattr(self, name, builder.get_object(name))
			
		map(set_object, ("window", "feed_tree_view", "content_scroll_view"))
		builder.connect_signals(self)
		self.init_feeds()
		self.init_columns()
		self.init_content()

	def on_feed_tree_view_select_row(self, widget, data=None):
		_dir = os.path.dirname(os.path.abspath(__file__))
		base = 'file://' + urllib.quote(_dir)
		selected = []
		col = 0
		store, iter = self.feed_tree_view.get_selection().get_selected()
		feed_name = store.get_value(iter, col)
		self.content_view.load_html_string("<h1>yay!</h1><pre>loaded: %r</pre>" % (feed_name,), base)

	def init_content(self):
		self.content_view = webkit.WebView()
		self.content_scroll_view.add(self.content_view)
		self.content_scroll_view.show_all()

	def init_feeds(self):
		store = self.feed_tree_store = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_INT)
		store.set(store.append(None), 0, "all feeds", 1, 500)
		store.set(store.append(None), 0, "more feeds", 1, 200)
		self.feed_tree_view.set_model(store)
	
	def init_columns(self):
		view = self.feed_tree_view
		view.append_column(gtk.TreeViewColumn('title', gtk.CellRendererText(), text=0))
		view.append_column(gtk.TreeViewColumn('items', gtk.CellRendererText(), text=1))

if __name__ == "__main__":
	gris = Gris()
	gris.window.show()
	gtk.main()


########NEW FILE########
__FILENAME__ = app_globals
# These are some defaults and other globals.
# anything in OPTIONS can be overrided / extended by config.py in reaction to command-line or config.yml input
import os

PLACEHOLDER = object()

CONFIG = {
	'pickle_file': '.entries.pickle',
	'test_output_dir': 'test_entries',
	'resources_path': '_resources',
	'pagefeed_feed_url_prefix': 'feed/http://pagefeed.appspot.com/feed/',
}

OPTIONS = {
	'user_config_file': 'config.plist',
	'output_path':      '/tmp/GRiS_test',
	'num_items':        300,
	'no_download':      False,
	'cautious':         False,
	'test':             False,
	'tag_list_only':    False,
	'report_pid':       False,
	'newest_first':     False,
	'show_status':      False,
	'aggressive':       False,
	'tag_list':         [],
	'user':             PLACEHOLDER,
	'password':         PLACEHOLDER,
	'ipaper_user':      PLACEHOLDER,
	'ipaper_password':  PLACEHOLDER,
	'url_save_service': 'instapaper', # can also be 'pagefeed'
	'logging':          os.path.join(os.path.dirname(__file__), 'logging.conf'),
	'logdir':           'log',
	'loglevel':         'info',
}

STATS = {
	'items':       0,
	'failed':      0,
	'new':         0,
	'read':        0,
	'reprocessed': 0,
}

# These ones get set to useful values in main.py

READER = None
DATABASE = None
URLSAVE = None

########NEW FILE########
__FILENAME__ = auth
class LoginError(RuntimeError):
	pass

########NEW FILE########
__FILENAME__ = config
"""
Exports:
CONFIG
OPTIONS
parse_options()
load_config()
"""
from getopt import getopt
import sys
import re
import lib
import logging
import logging.config
import ConfigParser

# local imports
from misc import *
from output import *
import app_globals


required_keys = ['user','password']

bootstrap_options = ('c:so', ['config=','show-status','output-path=', 'logging=','logdir=','loglevel='])
main_options = ("n:Co:dth", [
		'num-items=',
		'cautious',
		'aggressive',
		'no-download',
		'test',
		'help',
		'user=',
		'password=',
		'tag=',
		'tag-list-only',
		'newest-first',
		'report-pid',
		])
all_options = (bootstrap_options[0] + main_options[0],
               bootstrap_options[1] + main_options[1])

def unicode_argv(args = None):
	if args is None:
		args = sys.argv[1:]
	return [unicode(arg, 'utf-8') for arg in args]

def bootstrap(argv = None):
	argv = unicode_argv(argv)
	(opts, argv) = getopt(argv, *all_options)
	for (key,val) in opts:
		if key == '--config' or key == '-c':
			set_opt('user_config_file', val)
		elif key == '--show-status' or key == '-s':
			set_opt('show_status', True)
		elif key == '-o' or key == '--output-path':
			set_opt('output_path', val)
		elif key == '--logging':
			set_opt('logging', val)
		elif key == '--logdir':
			set_opt('logdir', val)
		elif key == '--loglevel':
			set_opt('loglevel', val)


def defaults(*args):
	return tuple(["(default: %s)" % app_globals.OPTIONS[pythonise_option_key(key)] for key in args])

def parse_options(argv = None):
	"""
Usage:
  -n, --num-items=[val]  set the number of items to download (per feed)
  -c, --config=[file]    load config from file (must be in yaml format)
  -d, --no-download      don't download new items, just tell google reader about read items
  -t, --test             run in test mode (don't notify google reader of anything)
  -c, --cautious         cautious mode - prompt before performing destructive actions
  -o, --output-path=[p]  set the base output path (where items and resources are saved)
  --tag-list-only        just get the current list of tags and exit
  --newest-first         get newest items first instead of oldest
  --user=[username]      set the username
  --password=[pass]      set password
  --tag=[tag_name]       add a tag to the list of tags to be downloaded. Can be used multiple times
  --report-pid           report any existing sync PID
  --aggressive           KILL any other running sync process
                         (the default is to fail to start if another sync process is running)
  --logdir=[log_dir]     logging base directory
  --logging=[log_conf]   override log configuration file
  --loglevel=[log_conf]  set the console output log level
"""
	tag_list = []
	argv = unicode_argv(argv)

	(opts, argv) = getopt(argv, *all_options)
	for (key,val) in opts:
		if key in ['-c','--config','-s','--show-status', '--logging', '--logdir', '--loglevel']:
			# already processed
			pass
		
		elif key == '-C' or key == '--cautious':
			set_opt('cautious', True)
			info("Cautious mode enabled...")
		elif key == '-n' or key == '--num-items':
			set_opt('num_items', int(val))
			info("Number of items set to %s" % app_globals.OPTIONS['num_items'])
		elif key == '-d' or key == '--no-download':
			set_opt('no_download', True)
			info("Downloading turned off..")
		elif key == '-t' or key == '--test':
			set_opt('test', True)
		elif key == '-h' or key == '--help':
			print parse_options.__doc__
			sys.exit(1)
		elif key == '--password':
			set_opt('password',val, disguise = True);
		elif key == '--tag':
			tag_list.append(val)
			set_opt('tag_list', tag_list)

		else:
			if key.startswith('--') and key[2:] in main_options[1]:
				# it's a flag
				val = True
			success = set_opt(key, val)
			if not success:
				print "unknown option: %s" % (key,)
				print parse_options.__doc__ 
				sys.exit(1)

	if len(argv) > 0:
		set_opt('num_items', int(argv[0]))
		info("Number of items set to %s" % app_globals.OPTIONS['num_items'])

	

def pythonise_option_key(key):
	"""
	Convert `CamelCase` and `option-style` keys into `python_style` keys
		>>> pythonise_option_key('Capital')
		'capital'
		>>> pythonise_option_key('CamelCase')
		'camel_case'
		>>> pythonise_option_key('Camel_Case')
		'camel_case'
		>>> pythonise_option_key('option-Style')
		'option_style'
		>>> pythonise_option_key('option-style')
		'option_style'
	"""
	key = re.sub('([a-z0-9])([A-Z])', '\\1_\\2', key)
	key = key.replace('-', '_')
	key = key.replace('__', '_')
	key = key.lower()
	return key

path_keys = ['output_path','user_config_file']
def set_opt(key, val, disguise = False):
	if key.startswith('--'):
		key = key[2:]
	key = pythonise_option_key(key)
	if "pass" in key or "Pass" in key:
		disguise = True
	if key in path_keys:
		val = os.path.expanduser(val)
	debug("set option %s = %s" % (key, val if disguise is False else "*****"))
	if key not in app_globals.OPTIONS:
		debug("Ignoring key: %s" % (key,))
		return False
	app_globals.OPTIONS[key] = val
	return True

def init_logging():
	logdir = app_globals.OPTIONS['logdir']
	ensure_dir_exists(logdir)
	env = {
		'logdir':logdir,
		'loglevel': app_globals.OPTIONS['loglevel'].upper(),
	}
	try:
		logging.config.fileConfig(app_globals.OPTIONS['logging'], env)
	except ConfigParser.Error:
		print "ERROR: logging setup FAILED with file: %s, env: %r" % (app_globals.OPTIONS['logging'],env)
		raise

def load(filename = None):
	"""
	Loads config.yml (or OPTIONS['user_config_file']) and merges it with the global OPTIONS hash
	"""
	if filename is None:
		filename = app_globals.OPTIONS['user_config_file']
		if not (os.path.isfile(filename) or os.path.isabs(filename)):
			filename = os.path.join(app_globals.OPTIONS['output_path'], filename)

	debug("Loading configuration from %s" % filename)
	
	try:
		extension = filename.split('.')[-1].lower()
		if extension == 'yml':
			config_hash = load_yaml(filename)
		elif extension == 'plist':
			config_hash = load_plist(filename)
		else:
			warning("unknown filetype: %s" % (extension,))
			config_hash = {}

		if config_hash is not None:
			for key,val in config_hash.items():
				set_opt(key, val)

	except IOError, e:
		warning("Can't load %s: %s" % (filename,e))

def load_yaml(filename):
	try:
		import yaml
		return do_with_file(filename, 'r', yaml.load)
	except ImportError, e:
		warning("YAML library failed to load: %s" % (e, ))

def load_plist(filename):
	import plistlib
	return do_with_file(filename, 'r', plistlib.readPlist)


def check():
	for k in required_keys:
		if not k in app_globals.OPTIONS or app_globals.OPTIONS[k] is app_globals.PLACEHOLDER:
			raise RuntimeError("Required setting \"%s\" is not set." % (k,))

if __name__ == '__main__':
	import doctest
	doctest.testmod()

########NEW FILE########
__FILENAME__ = config_test
from mocktest import *
import config
import test_helper
from misc import *

import os

class ConfigTest(TestCase):
	def setUp(self):
		self.yaml_file = '/tmp/gris_config.yml'
		self.plist_file = '/tmp/gris_config.plist'
		self.__options = app_globals.OPTIONS.copy()
	
	def rm(self, f):
		try: os.remove(f)
		except OSError: pass
		
	def tearDown(self):
		self.rm(self.yaml_file)
		self.rm(self.plist_file)
		app_globals.OPTIONS = self.__options
		
	def test_should_not_fail_setting_any_options(self):
		for opt in config.all_options[1]:
			opt = '--' + opt
			args = [opt]
			if opt.endswith('='):
				args = [opt[:-1], '123']

			if opt == '--help':
				try: config.bootstrap([opt])
				except SystemExit: pass
				continue
				
			print "bootstrapping with %s" % args
			config.bootstrap(args)
			print "configging with %s" % args
			config.parse_options(args)
		
	def test_should_load_plist(self):
		write_file(self.plist_file, """<?xml version="1.0" encoding="UTF-8"?>
			<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
			<plist version="1.0">
				<dict>
					<key>num_items</key>
					<integer>5</integer>
				</dict> 
			</plist>
			 """)
		config.load(self.plist_file)
		self.assertEqual(config.app_globals.OPTIONS['num_items'], 5) 
		
	def test_should_load_yaml(self):
		write_file(self.yaml_file, "num_items: 1234")
		config.load(self.yaml_file)
		self.assertEqual(config.app_globals.OPTIONS['num_items'], 1234)
	
	def test_should_set_global_options(self):
		config.app_globals.OPTIONS = {'foo':1}
		config.set_opt('foo',2)
		self.assertEqual(config.app_globals.OPTIONS['foo'], 2)

	def test_should_not_set_nonexistant_global_options(self):
		config.app_globals.OPTIONS = {'foo':1}
		config.set_opt('bar',2)
		self.assertFalse('bar' in app_globals.OPTIONS.keys())
		
########NEW FILE########
__FILENAME__ = db
"""
Exports:
DB class
"""
import glob
import os

# local imports
import config
import app_globals
from misc import *
from output import *
from item import Item

import sqlite3 as sqlite

# to support data migration, we currently have all versions / modifications to the schema
# hopefully this won't become too ungainly
schema_history = [
	'CREATE TABLE items(google_id TEXT primary key, date TIMESTAMP, url TEXT, original_id TEXT, title TEXT, content TEXT, feed_name TEXT, is_read BOOLEAN, is_starred BOOLEAN, is_dirty BOOLEAN default 0)',
	'CREATE UNIQUE INDEX item_id_index on items(google_id)',
	'ALTER TABLE items ADD COLUMN had_errors BOOLEAN default 0',
	'ALTER TABLE items ADD COLUMN is_stale BOOLEAN default 0',
	'ALTER TABLE items ADD COLUMN tag_name BOOLEAN default ""',
	'ALTER TABLE items ADD COLUMN is_shared BOOLEAN default 0',
	'ALTER TABLE items ADD COLUMN instapaper_url TEXT default ""',
	'ALTER TABLE items ADD COLUMN is_pagefeed BOOLEAN default 0',
	]

class VersionDB:
	@staticmethod
	def version(db):
		version = 0
		tables = map(first, db.execute('select tbl_name from sqlite_master').fetchall())
		if 'db_version' in tables:
			version = int(first(db.execute('select version from db_version').fetchone()))
		else:
			db.execute('CREATE TABLE db_version(version INT)')
			db.execute('INSERT INTO db_version(version) VALUES (0)')
		return version

	@staticmethod
	def migrate(db, schema_history):
		version = VersionDB.version(db)
		unapplied_schema_steps = schema_history[version:]
		if len(unapplied_schema_steps) > 0:
			info("Your database is at version %s, the latest is version %s. Upgrading" % (version, len(schema_history)))
			print unapplied_schema_steps
			for step in unapplied_schema_steps:
				debug("Appling the following query to your database:\n%s" % (step,))
				db.execute(step)
				version += 1
				db.execute('update db_version set version = ?', (version,))
			debug("database is up to date! (version %s)" % len(schema_history))
			db.commit()
		return len(unapplied_schema_steps)


class DB:
	def __init__(self, filename = 'items.sqlite'):
		if app_globals.OPTIONS['test']:
			filename = os.path.dirname(filename) + 'test_' + os.path.basename(filename)
		self.filename = filename = os.path.join(app_globals.OPTIONS['output_path'], os.path.basename(filename))
		debug("loading db: %s" % filename)
		self.db = sqlite.connect(filename)

		# commit immediately after statements.
		# doing commits every now and then seems buggy, and we don't need it.
		self.db.isolation_level = "IMMEDIATE"

		self.schema = {
			'columns': [
				('google_id','TEXT primary key'),
				('date', 'TIMESTAMP'),
				('url', 'TEXT'),
				('original_id', 'TEXT'),
				('title', 'TEXT'),
				('content', 'TEXT'),
				('feed_name', 'TEXT'),
				('is_read', 'BOOLEAN'),
				('is_starred', 'BOOLEAN'),
				('is_dirty', 'BOOLEAN default 0'),
				('had_errors', 'BOOLEAN default 0'),
				('is_stale', 'BOOLEAN default 0'),
				('tag_name', 'TEXT'),
				('is_shared', 'BOOLEAN'),
				('instapaper_url', 'TEXT'),
				('is_pagefeed', 'BOOLEAN'),
			],
			'indexes' : [ ('item_id_index', 'items(google_id)') ]
		}
		self.cols = [x for (x,y) in self.schema['columns']]
		self.setup_db()

	def reload(self):
		"""
		reload the database
		"""
		self.close()
		self.db = sqlite.connect(self.filename)

	def sql(self, stmt, data = None):
		args = [stmt]
		if data is not None:
			args.append(data)

		return self.db.execute(*args)
	
	def get(self, google_id, default=None):
		items = list(self.get_items('google_id = ?', (google_id,)))
		if len(items) == 0:
			return default
		return items[0]
	
	def erase(self):
		if not app_globals.OPTIONS['test']:
			raise Exception("erase() called, but we're not in test mode...")
		self.sql('delete from items')

	def reset(self):
		self.erase()
		self.setup_db()
	
	def tables(self):
		return [row[0] for row in self.db.execute('select name from sqlite_master where type = "table"')]

	def setup_db(self):
		global schema_history
		if VersionDB.migrate(self.db, schema_history) > 0:
			self.reload()
		
	def add_item(self, item):
		self.sql("insert into items (%s) values (%s)" % (', '.join(self.cols), ', '.join(['?'] * len(self.cols))),
			[getattr(item, attr) for attr in self.cols])
	
	def update_content_for_item(self, item):
		self.sql("update items set content=?, tag_name=?, is_stale=? where google_id=?", (item.content, item.tag_name, False, item.google_id))
	
	def remove_item(self, item):
		google_id = item.google_id
		self.sql("delete from items where google_id = ?", (google_id,))
	
	def update_item(self, item):
		self.sql("update items set is_read=?, is_starred=?, is_shared=?, is_dirty=?, instapaper_url=? where google_id=?",
			(item.is_read, item.is_starred, item.is_shared, item.is_dirty, item.instapaper_url, item.google_id));

	def get_items(self, condition=None, args=None):
		sql = "select * from items"
		if condition is not None:
			sql += " where %s" % condition
		cursor = self.sql(sql, args)
		for row_tuple in cursor:
			yield self.item_from_row(row_tuple)
	
	def get_item_count(self, condition=None, args=None):
		sql = "select count(*) from items"
		if condition is not None:
			sql += " where %s" % condition
		cursor = self.sql(sql, args)
		return cursor.next()[0]

	def get_items_list(self, *args, **kwargs):
		return [x for x in self.get_items(*args, **kwargs)]

	def item_from_row(self, row_as_tuple):
		i = 0
		item = {}
		for i in range(len(row_as_tuple)):
			val = row_as_tuple[i]
			col_description = self.schema['columns'][i][1]
			if 'BOOLEAN' in col_description:
				# convert to a python boolean
				val = val == 1
			else:
				val = unicode(val)
			item[self.cols[i]] = val
		return Item(raw_data = item)
	
	def cleanup(self):
		"""Clean up any stale items / resources"""
		self.cleanup_stale_items()
		self.cleanup_resources_directory()
		
	def close(self):
		"""close the db"""
		debug("closing DB")
		# despite our insistance of "IMMEDIATE" isolation level, this seems to be necessary
		self.db.commit()
		self.db.close()
		self.db = None

	def sync_to_google(self):
		info("Syncing with google...")
		status("SUBTASK_TOTAL", self.get_item_count('is_dirty = 1'))
		item_number = 0
		for item in self.get_items('is_dirty = 1'):
			debug('syncing item state \"%s\"' % item.title)
			item.save_to_web()
			self.update_item(item)

			item_number += 1
			status("SUBTASK_PROGRESS",item_number)

		for item in self.get_items('is_read = 1'):
			debug('deleting item \"%s\"' % item.title)
			item.delete()
		danger("about to delete %s read items from db" % self.get_item_count('is_read = 1'))
		self.sql('delete from items where is_read = 1')
		
	def prepare_for_download(self):
		self.sql('update items set is_stale = ?', (True,))
	
	def cleanup_stale_items(self):
		self.sql('delete from items where is_stale = ?', (True,))
	
	def cleanup_resources_directory(self):
		res_prefix = "%s/%s/" % (app_globals.OPTIONS['output_path'], app_globals.CONFIG['resources_path'])
		glob_str = res_prefix + "*"
		current_keys = set([os.path.basename(x) for x in glob.glob(glob_str)])
		unread_keys = set([Item.escape_google_id(row[0]) for row in self.sql('select google_id from items where is_read = 0')])

		current_but_read = current_keys.difference(unread_keys)
		if len(current_but_read) > 0:
			info("Cleaning up %s old resource directories" % len(current_but_read))
			danger("remove %s old resource directories" % len(current_but_read))
			for key in current_but_read:
				rm_rf(res_prefix + key)

if __name__ == '__main__':
	print "running DB migration..."
	app_globals.OPTIONS['loglevel'] = 'DEBUG'
	app_globals.OPTIONS['output_path'] = '.'
	config.init_logging()
	db = DB()
	db.close()

########NEW FILE########
__FILENAME__ = db_test
# the tested module
from db import *
from output import *
import os

# test helpers
import test_helper
from test_helper import fake_item, google_ids
import unittest

def test_migrated_persistance():
	# make sure the migrations actually get saved to disk.
	# You might not think this would be a necessary test, but you'd be surprised...
	fname = '/tmp/test_items.sqlite'
	schema = ['create table items(id TEXT)', 'create table items2(id TEXT)']
	try:
		os.remove(fname)
	except EnvironmentError:
		pass # that's ok...
	db = sqlite.connect(fname)
	assert VersionDB.migrate(db, schema) == 2 # 2 steps applied
	db.close()
	
	db = sqlite.connect(fname)
	assert VersionDB.migrate(db, schema) == 0
	
	db.close()
	os.remove(fname)

class VersionDBTest(unittest.TestCase):
	def setUp(self):
		self.output_folder = test_helper.init_output_folder()
		self.db = sqlite.connect(':memory:')
		assert self.tables() == []
	
	def tearDown(self):
		self.db.close()
		self.db = None
		
		
	def tables(self):
		return map(first, self.db.execute('select name from sqlite_master where type = \'table\'').fetchall())
	
	def test_zero_migration(self):
		assert VersionDB.migrate(self.db, []) == 0
		assert self.tables() == ['db_version']
		assert VersionDB.version(self.db) == 0
		assert self.tables() == ['db_version']

	def test_zero_up_migration(self):
		assert VersionDB.migrate(self.db, ['create table items(id TEXT)', 'create table items2(id TEXT)']) == 2 # 2 steps applied
		assert sorted(self.tables()) == ['db_version', 'items', 'items2']
		assert VersionDB.version(self.db) == 2

		# make sure it's idempotent
		assert VersionDB.migrate(self.db, ['create table items(id TEXT)', 'create table items2(id TEXT)']) == 0 # 0 steps applied
		assert sorted(self.tables()) == ['db_version', 'items', 'items2']
		assert VersionDB.version(self.db) == 2
	
	def test_nonzero_migration(self):
		schema = ['create table items(id TEXT)']
		assert VersionDB.migrate(self.db, schema) == 1 # 1 step applied
		assert sorted(self.tables()) == ['db_version', 'items']
		assert VersionDB.version(self.db) == 1

		schema.append('create table items2(id TEXT)')
		assert VersionDB.migrate(self.db, schema) == 1 # 1 more step applied
		assert sorted(self.tables()) == ['db_version', 'items', 'items2']
		assert VersionDB.version(self.db) == 2
	
	def test_invalid_migration(self):
		self.assertRaises(sqlite.OperationalError, VersionDB.migrate, self.db, ['clearly this is invalid sql'])
		assert VersionDB.version(self.db) == 0


class DBTest(unittest.TestCase):

	def setUp(self):
		self.output_folder = test_helper.init_output_folder()

		# initialise the DB
		touch_file(self.output_folder + '/test.sqlite')
		app_globals.DATABASE = self.db = DB('test.sqlite')
		print "running db reset: %r" % self.db
		self.db.reset()
		self.assertEqual( sorted(self.db.tables()), ['db_version','items'] )
		
	def tearDown(self):
		self.db.close()
		rm_rf(self.output_folder)
	
	# ------------------------------------------------------------------
	
	def test_adding_items(self):
		# add to DB
		input_item = fake_item()
		self.db.add_item(input_item)
		
		# grab it out
		items = list(self.db.get_items())
		assert len(items) == 1
		item = items[0]
		
		# and check it still looks the same:
		for attr in ['url','title','feed_name','tag_name','google_id','is_read','is_dirty','is_shared','is_starred','date','content']:
			self.assertEqual( getattr(item, attr), getattr(input_item, attr) )

		# test updating
		item.is_read = True
		self.db.update_item(item)
		items = list(self.db.get_items())
		assert len(items) == 1
		item = items[0]
		assert item.is_read == True
		
	def test_adding_unicode(self):
		# add to DB
		input_item = fake_item(title=u'caf\xe9')
		self.db.add_item(input_item)
		
		# grab it out
		items = list(self.db.get_items())
		assert len(items) == 1
		item = items[0]
		
		# and check it still looks the same:
		assert item.title == u'caf\xe9'
	
	def test_deleting_an_item(self):
		a = fake_item(google_id = 'a')
		b = fake_item(google_id = 'b')
		self.db.add_item(a)
		self.db.add_item(b)
		items = list(self.db.get_items())
		assert len(items) == 2
		
		# now remove it
		self.db.remove_item(a)
		items = list(self.db.get_items())
		assert len(items) == 1
		assert items[0].google_id == 'b'
	
	def test_deleting_stale_items(self):
		old_1 = fake_item(google_id = 'old_1')
		old_2 = fake_item(google_id = 'old_2')
		new_1 = fake_item(google_id = 'new_1')
		new_2 = fake_item(google_id = 'new_2')
		new_3 = fake_item(google_id = 'new_3')
		
		old_items = [old_1, old_2]
		new_items = [new_1, new_2, new_3]
		all_items = old_items + new_items

		for the_item in all_items:
			self.db.add_item(the_item)
		
		self.db.prepare_for_download()
		
		# simulate getting of the new items again:
		for item_id in google_ids(new_items):
			self.db.update_content_for_item(self.db.get(item_id))
		
		self.assertEqual(sorted(google_ids(self.db.get_items_list())), sorted(google_ids(all_items)))

		self.db.cleanup_stale_items()
		print google_ids(self.db.get_items_list())
		
		self.assertEqual(sorted(google_ids(self.db.get_items_list())), sorted(google_ids(new_items)))
	
	def test_updating_item_contents(self):
		assert self.db.get('sample_id') == None
		item = fake_item()
		self.db.add_item(fake_item())
		item = fake_item(content='content2', tag_name='tagname2')
		self.db.update_content_for_item(item)
		self.assertEqual(1 , len(self.db.get_items_list('is_stale = 0 and google_id = \'sample_id\'')))
		item = list(self.db.get_items('google_id = "sample_id"'))[0]
		self.assertEqual(item.content, 'content2')
		self.assertEqual(item.tag_name, 'tagname2')
	
	def test_google_sync(self):
		# mock out the google reader
		reader = app_globals.READER.gr
		reader.set_read.return_value = 'OK'
		reader.add_star.return_value = 'OK'
		reader.set_unread.return_value = 'OK'
		reader.del_star.return_value = 'OK'
		
		self.db.add_item(fake_item(google_id = 'b', title='item b', is_read = False, is_dirty = True))
		self.db.add_item(fake_item(google_id = 'd', title='item d', is_read = False, is_dirty = True))
		self.db.add_item(fake_item(google_id = 'c', title='item c', is_starred = True, is_read = True, is_dirty = True))

		self.db.sync_to_google()
		assert reader.method_calls == [
			('set_read', ('c',), {}),
			('add_star', ('c',), {})]
		
		assert self.db.get_items_list('is_dirty = 1') == []
		# c should have been deleted because it was read
		assert sorted(map(lambda x: x.title, self.db.get_items_list('is_dirty = 0'))) == ['item b','item d']
		self.db.reload()
		# check that changes have been saved
		assert sorted(map(lambda x: x.title, self.db.get_items_list('is_dirty = 0'))) == ['item b','item d']
	
	def test_google_sync_failures(self):
		self.db.add_item(fake_item(google_id = 'b', is_read = True, is_dirty = True))
		app_globals.READER.gr.set_read.return_value = False
		self.assertRaises(Exception, self.db.sync_to_google)
		
		# item should still be marked as read (and dirty)
		assert self.db.get_items_list('is_dirty = 0') == []
		assert len(self.db.get_items_list('is_dirty = 1')) == 1
		assert len(self.db.get_items_list('is_read = 1')) == 1
	
	def test_cleanup(self):
		res_folders = ['a','b','blah','blah2','c','d']
		ensure_dir_exists(self.output_folder + '/_resources')
		for res_folder in res_folders:
			ensure_dir_exists(self.output_folder + '/_resources/' + res_folder)
			touch_file(self.output_folder + '/_resources/' + res_folder + '/image.jpg')
	
		assert os.listdir(self.output_folder + '/_resources') == res_folders
		
		# insert some existing items
		self.db.add_item(fake_item(google_id = 'b', is_read = False))
		self.db.add_item(fake_item(google_id = 'd', is_read = False))
		self.db.add_item(fake_item(google_id = 'c', is_read = True))
		
		# clean up that mess!
		self.db.sync_to_google() # remove all the read items
		self.db.cleanup()
		
		assert os.listdir(self.output_folder + '/_resources') == ['b','d']
	


########NEW FILE########
__FILENAME__ = google_reader_test
import os
import main

# test helpers
import test_helper
from test_helper import *
import unittest
import config
import app_globals
from reader import Reader, CONST

# These are (relatively) long running tests, which require an active google reader account and network connection.
# They should be separated from the main tests for this reason, but currenly they aren't.
class GoogleReaderLiveTest(unittest.TestCase):

	def setUp(self):
		yaml_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yml')
		config.load(yaml_file)
		config.bootstrap(['--loglevel=DEBUG'])
		# make sure we're not mocking out google reader
		app_globals.OPTIONS['test'] = False
		config.parse_options(['--output-path=/tmp/gris-test', '--num-items=1'])
		config.check()
		self.reader = app_globals.READER = Reader()
		
	def tearDown(self):
		rm_rf('/tmp/gris-test')
	
	# these don't explicitly check anything, their acceptance is by virtue of not throwing any exceptions
	def test_standard_tag(self):
		main.download_feed(self.reader.get_tag_feed('i-am-a-tag-without-spaces'),'feed')
		
	def test_tag_with_spaces(self):
		main.download_feed(self.reader.get_tag_feed('i am a tag with lots of spaces'),'feed')
	
	@test_helper.pending
	def test_tag_with_all_manner_of_crazy_characters_except_spaces(self):
		main.download_feed(main.get_feed_from_tag('abc\'"~!@#$%^&*()-+_=,.<>?/\\'))

	@test_helper.pending	
	def test_tag_with_non_ascii_characters(self):
		main.download_feed(main.get_feed_from_tag(u'caf\xe9'))

	# helper for the below test
	def get_tag_items(self, tag, is_read = None):
		kwargs = {}
		if is_read is not None:
			kwargs['exclude_target'] = CONST.ATOM_STATE_UNREAD if is_read else CONST.ATOM_STATE_READ
		feed = CONST.ATOM_PREFIXE_LABEL + tag
		return list(self.reader.get_feed(None, feed, count=1, **kwargs).get_entries())
			
	# For this test to pass, you need to have exactly one item tagged with "gris-test" in your google reader account.
	# I'm afraid you're on your own setting this up - doing it in code is just too cumbersome.
	@pending("behaviour is not reliable")
	def test_changing_item_status(self):
		pass
		# entries = self.get_tag_items('gris-test')
		# assert len(entries) == 1
		# entry = entries[0]
		# entry_id = entry['google_id']
		# 
		# # make sure it's unread
		# self.reader.set_unread(entry_id)
		# entries = self.get_tag_items('gris-test', is_read = False)
		# assert len(entries) == 1
		# entry = entries[0]
		# assert entry_id == entry['google_id']
		# 
		# # now mark it as read
		# self.reader.set_read(entry_id)
		# entries = self.get_tag_items('gris-test', is_read = True)
		# entry = entries[0]
		# assert len(entries) == 1
		# assert entry_id == entry['google_id']
		# entry = entries[0]

########NEW FILE########
__FILENAME__ = instapaper
import urllib2
import urllib

import app_globals
from output import *
from auth import LoginError

class Ipaper(object):
	def __init__(self):
		self.is_setup = False
	
	def _setup(self):
		"""ensure login details are setup"""
		if not self.is_setup:
			self.user = app_globals.OPTIONS['ipaper_user']
			self.password = app_globals.OPTIONS['ipaper_password']
			self.is_setup = True
		
	def missing(self, obj):
		return (not isinstance(obj, str)) or len(obj) == 0
	
	def add_urls(self, urls):
		map(self.add_url, urls)
	
	def add_url(self, url, title = None):
		self._setup()
		if self.missing(self.user) or not isinstance(self.password, str):
			warning("Instapaper url dropped: %s" % (url,))
			return

		debug("saving instapaper URL: %s" % (url,))
		
		post_url = 'https://www.instapaper.com/api/add'
		params = {
			'username': self.user,
			'password': self.password,
			'url': url
			}
		if title:
			params['title'] = title
		else:
			params['auto-title'] = '1'
		
		self._post(post_url, params)
	
	def _post(self, url, params):
		post_data = urllib.urlencode(params)
		
		result = None
		try:
			result = urllib2.urlopen(url, data=post_data)
		except urllib2.HTTPError, e:
			result = e.code
		if result != 201:
			if e.code == 403: # permission denied
				raise RuntimeError("instapaper login failed")
			raise RuntimeError("instapaper post failed: response=%s" % (result))


########NEW FILE########
__FILENAME__ = instapaper_test
from mocktest import *
from instapaper import Ipaper
from auth import LoginError
import test_helper
import urllib
import urllib2
from misc import *

class InstapaperTest(TestCase):
	def setUp(self):
		# test_helper.init_output_folder()
		app_globals.OPTIONS['ipaper_user'] = 'ipaper_user'
		app_globals.OPTIONS['ipaper_password'] = 'ipaper_password'
		self.ip = Ipaper()
	
	def httpStatus(self, code):
		class FakeFP(object):
			def read(self):
				return EOFError
			def readline(self):
				return EOFError
		return urllib2.HTTPError('url',code,'msg','headers',FakeFP())
		
	def test_should_add_url_with_title(self):
		def check_args(url, data):
			self.assertEqual(url, 'https://www.instapaper.com/api/add')
			pairs = data.split('&')
			self.assertEqual(sorted(pairs), sorted([
				'username=ipaper_user',
				'password=ipaper_password',
				'url=http%3A%2F%2Flocalhost%2F',
				'title=the+title']))
			return True
		
		mock_on(urllib2).urlopen.raising(self.httpStatus(201)).is_expected.where_args(check_args)
		self.ip.add_url('http://localhost/', 'the title')

	def test_should_add_url_without_title(self):
		def check_args(url, data):
			self.assertEqual(url, 'https://www.instapaper.com/api/add')
			pairs = data.split('&')
			self.assertEqual(sorted(pairs), sorted([
				'username=ipaper_user',
				'password=ipaper_password',
				'url=http%3A%2F%2Flocalhost%2F',
				'auto-title=1']))
			return True
		
		mock_on(urllib2).urlopen.raising(self.httpStatus(201)).is_expected.where_args(check_args)
		self.ip.add_url('http://localhost/')
	
	def test_should_silently_fail_if_username_and_pass_are_blank(self):
		app_globals.OPTIONS['ipaper_user'] = ''
		app_globals.OPTIONS['ipaper_password'] = ''
		mock_on(urllib2).urlopen.is_expected.no_times()
		self.ip.add_url('http://localhost/', 'the title')
		
	def test_should_silently_fail_if_username_and_pass_are_none(self):
		app_globals.OPTIONS['ipaper_user'] = None
		app_globals.OPTIONS['ipaper_password'] = None
		mock_on(urllib2).urlopen.is_expected.no_times()
		self.ip.add_url('http://localhost/', 'the title')
	
	def test_should_add_multiple_urls(self):
		add_url = mock_on(self.ip).add_url
		add_url.is_expected.twice()
		add_url.is_expected.with_('a')
		add_url.is_expected.with_('b')
		
		self.ip.add_urls(['a','b'])
		

########NEW FILE########
__FILENAME__ = item
import glob
import time
import re
import urllib

# local imports
import app_globals
from misc import *
from output import *
import thread_pool

# processing modules
from lib.BeautifulSoup import BeautifulSoup
import process


def esc(s):   return urllib.quote(s)
def unesc(s): return urllib.unquote(s)

def strip_html_tags(s):
	flags = re.DOTALL | re.UNICODE
	double_tag_match = re.compile('<(?P<tagname>[a-zA-Z0-9]+)[^<>]*>(?P<content>.*?)</(?P=tagname)>', flags)
	single_tag_match = re.compile('<(?P<tagname>[a-zA-Z0-9]+)[^<>]*/>', flags)
	
	while re.search(double_tag_match, s) is not None:
		s = re.sub(double_tag_match, '\g<content>', s)
	s = re.sub(single_tag_match, '', s)
	return s

class Item:
	"""
	A wrapper around a GoogleReader item
	"""
	def __init__(self, feed_item = None, tag_name = '(unknown)', raw_data = None):
		self.had_errors = False
		if feed_item is not None:
			try: self.feed_name = feed_item['feed_name']
			except (KeyError, TypeError):
				self.feed_name = tag_name
			self.tag_name = tag_name
			self.title = strip_html_tags(utf8(feed_item['title']))
			self.title = unicode(BeautifulSoup(self.title, convertEntities = BeautifulSoup.HTML_ENTITIES))
			self.google_id = feed_item['google_id']
			self.date = time.strftime('%Y%m%d%H%M%S', time.localtime(float(feed_item['updated'])))
			self.is_read = 'read' in feed_item['categories']
			self.is_starred = 'starred' in feed_item['categories']
			self.is_shared = 'broadcast' in feed_item['categories']
			self.url = utf8(feed_item['link'])
			self.content = utf8(feed_item['content'])
			self.original_id = utf8(feed_item['original_id'])
			self.media = try_lookup(feed_item, 'media')
			self.is_pagefeed = self.any_source_is_pagefeed(map(utf8, feed_item['sources']))
			self.instapaper_url = ""
			self.is_dirty = False
			self.is_stale = False
		else:
			# just copy the dict's keys to my instance vars
			for key,value in raw_data.items():
				setattr(self, key, value)
		
		# calculated attributes that aren't stored in the DB
		self.safe_google_id = Item.escape_google_id(self.google_id)
		self.resources_path = "%s/%s/%s" % (app_globals.OPTIONS['output_path'], app_globals.CONFIG['resources_path'], self.safe_google_id)
		self.basename = self.get_basename()
	
	@staticmethod
	def unescape_google_id(safe_google_id):
		return urllib.unquote(safe_google_id)

	@staticmethod
	def escape_google_id(unsafe_google_id):
		return urllib.quote(unsafe_google_id, safe='')

	def get_basename(self):
		"""A filesystem-safe key, unique to this item"""
		return utf8(
			self.date + ' ' +
			filter(lambda x: x not in '"\':#!+/$\\?*', ascii(self.title))[:120] + ' .||' +
			self.safe_google_id + '||' )

	def soup_setup(self):
		self.soup = BeautifulSoup(self.content)
		try:
			self.base = url_dirname(self.original_id)
		except TypeError:
			self.base = None
	
	def soup_teardown(self):
		self.soup 
		self.content = self.soup.prettify()
		
	def process(self):
		debug("item %s -> process()" % self.title)
		self.soup_setup()
		thread_pool.ping()
		
		# process
		debug("item %s -> insert_alt_text()" % self.title)
		process.insert_alt_text(self.soup)
		thread_pool.ping()
		
		self.download_images(need_soup = False)
		thread_pool.ping()
		
		# save changes back as content
		self.soup_teardown()
	
	def redownload_images(self):
		self.had_errors = False
		self.download_images()
		self.update()
	
	def download_images(self, need_soup=True):
		self.had_errors = False

		if need_soup:
			self.soup_setup()
		
		try: media = self.media
		except AttributeError: media = None

		if media is not None:
			success = process.insert_enclosure_images(self.soup, url_list = self.media)
			if not success:
				self.had_errors = True
		
		debug("item %s -> download_images()" % (self.title,))
		success = process.download_images(self.soup,
			dest_folder = self.resources_path,
			href_prefix = app_globals.CONFIG['resources_path'] + '/' + self.safe_google_id + '/',
			base_href = self.base)
		if not success:
			self.had_errors = True

		if need_soup:
			self.soup_teardown()
	
	def save(self):
		app_globals.DATABASE.add_item(self)
	
	def update(self):
		app_globals.DATABASE.update_content_for_item(self)

	def delete(self):
		app_globals.DATABASE.remove_item(self)
		for f in glob.glob(app_globals.OPTIONS['output_path'] + '/*.' + self.safe_google_id + '.*'):
			rm_rf(f)
		rm_rf(self.resources_path)
	
	def get_instpapaer_urls(self):
		return set(self.instapaper_url.split('|'))
	instapaper_urls = property(get_instpapaer_urls)
	
	def save_to_web(self):
		if not self.is_dirty:
			return
		
		# instapaper / pagefeed URLs
		if self.instapaper_url and len(self.instapaper_url) > 0:
			app_globals.URLSAVE.add_urls(self.instapaper_urls)
			self.instapaper_url = ''
		
		# read status
		if self.is_read:
			self._google_do(app_globals.READER.set_read)

		# stars
		if self.is_starred:
			self._google_do(app_globals.READER.add_star)
		
		# share
		if self.is_shared:
			self._google_do(app_globals.READER.add_public)
		
		self.delete_from_web_if_required()
		self.is_dirty = False

	def still_needed(self):
		is_unread = not self.is_read
		needed = is_unread or self.is_starred or self.is_shared
		return needed
	
	def any_source_is_pagefeed(self, sources):
		source_is_pagefeed = lambda source: source.startswith(app_globals.CONFIG['pagefeed_feed_url_prefix'])
		return any(map(source_is_pagefeed, sources))
	
	def delete_from_web_if_required(self):
		if (not self.is_pagefeed) or self.still_needed():
			return
		
		try:
			debug("deleting saved url: %s" % (self.url,))
			app_globals.URLSAVE.delete(url=self.url)
		except AttributeError:
			warning("url save mechanism has no delete function")
			return

	def _google_do(self, action):
		return action(self.google_id)

########NEW FILE########
__FILENAME__ = item_test
# the tested module
from item import *

# test helpers
import test_helper
from lib.mock import Mock
import unittest

import mocktest as mt

sample_item = {
	'author': u'pizzaburger',
	'categories': {u'user/-/label/03-comics---imagery': u'03-comics---imagery',
	               u'user/-/state/com.google/fresh': u'fresh',
	               u'user/-/state/com.google/reading-list': u'reading-list'},
	'content': u'<div><br><p>Thx Penntastic</p>\n<p><img src="http://failblog.files.wordpress.com/2008/06/assembly-fail.jpg" alt="fail owned pwned pictures"></p>\n<img alt="" border="0" src="http://feeds.wordpress.com/1.0/categories/failblog.wordpress.com/1234/"> <img alt="" border="0" src="http://feeds.wordpress.com/1.0/tags/failblog.wordpress.com/1234/"> <a rel="nofollow" href="http://feeds.wordpress.com/1.0/gocomments/failblog.wordpress.com/1234/"><img alt="" border="0" src="http://feeds.wordpress.com/1.0/comments/failblog.wordpress.com/1234/"></a> <a rel="nofollow" href="http://feeds.wordpress.com/1.0/godelicious/failblog.wordpress.com/1234/"><img alt="" border="0" src="http://feeds.wordpress.com/1.0/delicious/failblog.wordpress.com/1234/"></a> <a rel="nofollow" href="http://feeds.wordpress.com/1.0/gostumble/failblog.wordpress.com/1234/"><img alt="" border="0" src="http://feeds.wordpress.com/1.0/stumble/failblog.wordpress.com/1234/"></a> <a rel="nofollow" href="http://feeds.wordpress.com/1.0/godigg/failblog.wordpress.com/1234/"><img alt="" border="0" src="http://feeds.wordpress.com/1.0/digg/failblog.wordpress.com/1234/"></a> <a rel="nofollow" href="http://feeds.wordpress.com/1.0/goreddit/failblog.wordpress.com/1234/"><img alt="" border="0" src="http://feeds.wordpress.com/1.0/reddit/failblog.wordpress.com/1234/"></a> <img alt="" border="0" src="http://stats.wordpress.com/b.gif?host=failblog.org&amp;blog=2441444&amp;post=1234&amp;subd=failblog&amp;ref=&amp;feed=1"></div><img src="http://feeds.feedburner.com/~r/failblog/~4/318806514" height="1" width="1">',
	'crawled': 1214307453013L,
	'google_id': u'tag:google.com,2005:reader/item/dcb79527f18794d0',
	'link': u'http://feeds.feedburner.com/~r/failblog/~3/318806514/',
	'original_id': u'http://failblog.wordpress.com/?p=1234',
	'published': 1214269209.0,
	'sources': {u'feed/http://feeds.feedburner.com/failblog': u'tag:google.com,2005:reader/feed/http://feeds.feedburner.com/failblog'},
	'summary': u'',
	'title': u'Assembly Fail',
	'updated': 1214269209.0}

def item_with_title(title):
	item = sample_item.copy()
	item['title'] = title
	return item

def item_with(**kwargs):
	item = sample_item.copy()
	item.update(kwargs)
	return item

class ItemTest(mt.TestCase):

	def setUp(self):
		self.output_folder = test_helper.init_output_folder()

		# initialise the DB mock
		app_globals.DATABASE = self.mock_db = Mock()

	def tearDown(self):
		rm_rf(self.output_folder)
		self.mock_db.clear()
	
	# ------------------------------------------------------------------

	def test_basename(self):
		item = Item(sample_item, 'feed-name')
		assert item.basename == '20080624110009 Assembly Fail .||tag%3Agoogle.com%2C2005%3Areader%2Fitem%2Fdcb79527f18794d0||'
	
	def test_read(self):
		item = Item(sample_item, 'feed-name')
		
	def test_remove_open_and_close_html_tags(self):
		item = Item(item_with_title('<openTag attr="dsdjas">some title</openTag>'), 'feed-name')
		self.assertEqual(item.title, 'some title')

	@test_helper.pending("using beautiful soup breaks this")
	def test_dont_remove_tags_when_there_is_no_matching_open_or_close_tag(self):
		item = Item(item_with_title('<notATag>some title'), 'feed-name')
		self.assertEqual(item.title, '<notATag>some title')
		
		item = Item(item_with_title('some title</notATag>'), 'feed-name')
		self.assertEqual(item.title, 'some title</notATag>')
		
		item = Item(item_with_title('<noEndTag>some title</noStartTag>'), 'feed-name')
		self.assertEqual(item.title, '<noEndTag>some title</noStartTag>')
	
	def test_remove_self_closing_tags(self):
		item = Item(item_with_title('<self_ending_tag />some title'), 'feed-name')
		self.assertEqual(item.title, 'some title')
		
		item = Item(item_with_title('<self_ending_tag/>some title'), 'feed-name')
		self.assertEqual(item.title, 'some title')

	def test_remove_multiple_tags(self):
		item = Item(item_with_title('<a>some</a> <a>title</a>'), 'feed-name')
		self.assertEqual(item.title, 'some title')
	
	def test_remove_nested_tags(self):
		item = Item(item_with_title('<div>some <div><a>title</a></div></div>'), 'feed-name')
		self.assertEqual(item.title, 'some title')
	
	def test_convert_html_entities(self):
		item = Item(item_with_title('caf&eacute;&#233;&#39;s'), 'feed-name')
		self.assertEqual(item.title, u'caf\xe9\xe9\'s')
	
	def test_strip_unicode_from_basename(self):
		item = Item(item_with_title('caf&eacute;&#39;s'), 'feed-name')
		self.assertTrue(' cafs .||' in item.basename)
	
	def test_should_sync_unique_instapaper_urls(self):
		ipaper = mt.mock()
		app_globals.URLSAVE = ipaper.raw
		ipaper.expects('add_urls').with_(set(['url1', 'url2']))
		
		item = Item(item_with_title('blah'))
		item.instapaper_url = 'url1|url2|url2'
		item.is_dirty = True
		item.save_to_web()
		
	def test_should_indicate_if_item_came_from_pagefeed(self):
		pagefeed_item = Item(item_with(sources=['feed1', 'feed/http://pagefeed.appspot.com/feed/whatever']))
		non_pagefeed_item = Item(item_with(sources=['feed1', 'feed/http://somewhere_else.appspot.com/feed/whatever']))
		self.assertTrue(pagefeed_item.is_pagefeed)
		self.assertFalse(non_pagefeed_item.is_pagefeed)
	
	def test_should_delete_unneeded_pagefeed_items(self):
		ipaper = mt.mock()
		app_globals.URLSAVE = ipaper.raw
		mt.mock_on(app_globals.READER).set_read
		ipaper.expects('delete').with_(url='url')
		
		item = Item(item_with(link='url'))
		item.is_pagefeed = True
		item.is_dirty = True
		item.is_read = True
		item.save_to_web()
	
	def test_should_not_delete_needed_pagefeed_items(self):
		ipaper = mt.mock()
		app_globals.URLSAVE = ipaper.raw
		mt.mock_on(app_globals.READER).add_star
		ipaper.method('delete').returning('OK').is_not_expected
		
		item = Item(item_with(url='url'))
		item.is_pagefeed = True
		item.is_starred = True
		item.is_dirty = True
		item.save_to_web()
	
	def test_insert_media_items(self):
		global process
		media = ['http://example.com/image.jpg']
		item = Item(item_with(media = media))
		self.assertEqual(item.media, media)
		process.insert_enclosure_images = Mock()
		process.download_images = Mock()
		item.download_images()
		self.assertEqual(process.insert_enclosure_images.call_args[1]['url_list'], media)
	

########NEW FILE########
__FILENAME__ = app_engine_auth
import urllib
import urllib2
import cookielib

AUTH_URI = 'https://www.google.com/accounts/ClientLogin'
AUTH_TYPE = "HOSTED_OR_GOOGLE"

# adapted from:
# http://stackoverflow.com/questions/101742/how-do-you-access-an-authenticated-google-app-engine-service-from-a-non-web-pyt

class AppEngineAuth(object):
	def __init__(self, email, password, auth_uri=AUTH_URI, auth_type=AUTH_TYPE):
		self.email = email
		self.password = password
		self.auth_uri = auth_uri
		self.auth_type = auth_type
	
	def _install_cookie_jar(self):
		# we use a cookie to authenticate with Google App Engine
		#  by registering a cookie handler here, this will automatically store the 
		#  cookie returned when we use urllib2 to open http://currentcost.appspot.com/_ah/login
		cookiejar = cookielib.LWPCookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
		urllib2.install_opener(opener)
	
	def login(self, app_name, app_uri):
		self._install_cookie_jar()
		# get an AuthToken from Google accounts
		authreq_data = urllib.urlencode({
			"Email": self.email,
			"Passwd": self.password,
			"service": "ah",
			"source": app_name,
			"accountType": self.auth_type })
		auth_req = urllib2.Request(self.auth_uri, data=authreq_data)
		auth_resp = urllib2.urlopen(auth_req)
		auth_resp_body = auth_resp.read()
		# auth response includes several fields - we're interested in 
		#  the bit after Auth=
		auth_resp_dict = dict(x.split("=") for x in auth_resp_body.split("\n") if x)
		self.key = auth_resp_dict["Auth"]
		
		# now authenicate to the app in question
		serv_args = dict(auth=self.key)
		serv_args['continue'] = '/'
		full_serv_uri = app_uri + "_ah/login?%s" % (urllib.urlencode(serv_args))
		serv_req = urllib2.Request(full_serv_uri)
		serv_resp = urllib2.urlopen(serv_req)
		serv_resp_body = serv_resp.read()
		return self.key
	
	def logout(self, app_uri):
		raise StandardError("not yet implemented")


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
__version__ = "3.0.7"
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
__FILENAME__ = eggs
import sys, os, re

for file_ in os.listdir(os.path.dirname(__file__)):
	if re.search('.egg$', file_, re.IGNORECASE):
		sys.path.insert(0, os.path.join(os.path.dirname(__file__), file_))

########NEW FILE########
__FILENAME__ = const
class CONST(object) :
    URI_LOGIN = 'https://www.google.com/accounts/ClientLogin'
    URI_PREFIXE_READER = 'http://www.google.com/reader/'
    URI_PREFIXE_ATOM = URI_PREFIXE_READER + 'atom/'
    URI_PREFIXE_API = URI_PREFIXE_READER + 'api/0/'
    URI_PREFIXE_VIEW = URI_PREFIXE_READER + 'view/'

    ATOM_GET_FEED = 'feed/'

    ATOM_PREFIXE_USER = 'user/-/'
    ATOM_PREFIXE_USER_NUMBER = 'user/'+'0'*20+'/'
    ATOM_PREFIXE_LABEL = ATOM_PREFIXE_USER + 'label/'
    ATOM_PREFIXE_STATE_GOOGLE = ATOM_PREFIXE_USER + 'state/com.google/'

    ATOM_STATE_READ = ATOM_PREFIXE_STATE_GOOGLE + 'read'
    ATOM_STATE_UNREAD = ATOM_PREFIXE_STATE_GOOGLE + 'kept-unread'
    ATOM_STATE_FRESH = ATOM_PREFIXE_STATE_GOOGLE + 'fresh'
    ATOM_STATE_READING_LIST = ATOM_PREFIXE_STATE_GOOGLE + 'reading-list'
    ATOM_STATE_BROADCAST = ATOM_PREFIXE_STATE_GOOGLE + 'broadcast'
    ATOM_STATE_STARRED = ATOM_PREFIXE_STATE_GOOGLE + 'starred'
    ATOM_SUBSCRIPTIONS = ATOM_PREFIXE_STATE_GOOGLE + 'subscriptions'

    API_EDIT_SUBSCRIPTION = 'subscription/edit'
    API_EDIT_TAG = 'edit-tag'

    API_LIST_PREFERENCE = 'preference/list'
    API_LIST_SUBSCRIPTION = 'subscription/list'
    API_LIST_TAG = 'tag/list'
    API_LIST_UNREAD_COUNT = 'unread-count'
    API_TOKEN = 'token'

    URI_QUICKADD = URI_PREFIXE_READER + 'quickadd'

    OUTPUT_XML = 'xml'
    OUTPUT_JSON = 'json'

    AGENT='python-googlereader-contact:pyrfeed-at-gmail/0.1'

    ATOM_ARGS = {
        'start_time' : 'ot',
        'order' : 'r',
        'exclude_target' : 'xt',
        'count' : 'n',
        'continuation' : 'c',
        'client' : 'client',
        'timestamp' : 'ck',
        }

    EDIT_TAG_ARGS = {
        'feed' : 's',
        'entry' : 'i',
        'add' : 'a',
        'remove' : 'r',
        'action' : 'ac',
        'token' : 'T',
        }

    EDIT_SUBSCRIPTION_ARGS = {
        'feed' : 's',
        'entry' : 'i',
        'title' : 't',
        'add' : 'a',
        'remove' : 'r',
        'action' : 'ac',
        'token' : 'T',
        }

    LIST_ARGS = {
        'output' : 'output',
        'client' : 'client',
        'timestamp' : 'ck',
        'all' : 'all'
        }

    QUICKADD_ARGS = {
        'url' : 'quickadd',
        'token' : 'T',
    }

    ORDER_REVERSE = 'o'
    ACTION_REVERSE = 'o'

    GOOGLE_SCHEME = 'http://www.google.com/reader/'


########NEW FILE########
__FILENAME__ = feed
import time
from xml.dom import minidom

# TODO : Use those line when python 2.6 will be out, for now, there is no
#		 reasons to not be compatible with python 2.4 just to please PEP 238 !
#		 (lines will be mandatory only with python 2.7)
# from .const import CONST
from const import CONST


class GoogleFeed(object) :
	def __init__(self,xmlfeed) :
		# Need a lot more check !!!
		self._document = minidom.parseString(xmlfeed)
		# print xmlfeed
		self._entries = []
		self._properties = {}
		self._continuation = None
		self._isotime_pos = [(0,4),(5,7),(8,10),(11,13),(14,16),(17,19)]
		for feedelements in self._document.childNodes[0].childNodes :
			if feedelements.localName == 'entry' :
				self._entries.append(feedelements)
			elif feedelements.localName == 'continuation' :
				self._continuation = feedelements.firstChild.data
			else :
				self._properties[feedelements.localName] = feedelements
	def get_title(self) :
		if 'title' in self._properties :
			return self._properties['title'].childNodes[0].data

	def __len__(self):
		return len(self._entries)
	
	@staticmethod
	def _add_enclosure(entry, url):
		if not 'media' in entry:
			entry['media'] = []
		# print "entry getting url: %s" % url
		entry['media'].append(url)
		
	def get_entries(self) :
		for dom_entry in self._entries :
			try:
				entry = {}
				entry['categories'] = {}
				entry['sources'] = {}
				entry['crawled'] = int(dom_entry.getAttribute('gr:crawl-timestamp-msec'))
				for dom_entry_element in dom_entry.childNodes :
					# print repr(dom_entry_element)
					if dom_entry_element.localName == 'id' :
						entry['google_id'] = dom_entry_element.firstChild.data
						entry['original_id'] = dom_entry_element.getAttribute('gr:original-id')
					elif dom_entry_element.localName == 'link' :
						if dom_entry_element.getAttribute('rel') == 'alternate':
							entry['link'] = dom_entry_element.getAttribute('href')
							
						## <added by gfxmonk>
						elif dom_entry_element.getAttribute('rel') == 'enclosure':
							self._add_enclosure(entry, dom_entry_element.getAttribute('href'))
						## </ added by gfxmonk>

					elif dom_entry_element.localName == 'category' :
						if dom_entry_element.getAttribute('scheme')==CONST.GOOGLE_SCHEME :
							term = dom_entry_element.getAttribute('term')
							digit_table = {
								ord('0'):ord('0'),
								ord('1'):ord('0'),
								ord('2'):ord('0'),
								ord('3'):ord('0'),
								ord('4'):ord('0'),
								ord('5'):ord('0'),
								ord('6'):ord('0'),
								ord('7'):ord('0'),
								ord('8'):ord('0'),
								ord('9'):ord('0'),
								}
							if term.translate(digit_table).startswith(CONST.ATOM_PREFIXE_USER_NUMBER) :
								term = CONST.ATOM_PREFIXE_USER + term[len(CONST.ATOM_PREFIXE_USER_NUMBER):]
							entry['categories'][term] = dom_entry_element.getAttribute('label')
					elif dom_entry_element.localName == 'summary' :
						entry['summary'] = dom_entry_element.firstChild.data
					elif dom_entry_element.localName == 'content' :
						entry['content'] = dom_entry_element.firstChild.data
					elif dom_entry_element.localName == 'author' :
						entry['author'] = dom_entry_element.getElementsByTagName('name')[0].firstChild.data
					elif dom_entry_element.localName == 'title' :
						entry['title'] = dom_entry_element.firstChild.data
					elif dom_entry_element.localName == 'source' :
						entry['sources'][dom_entry_element.getAttribute('gr:stream-id')] = dom_entry_element.getElementsByTagName('id')[0].firstChild.data

					## <added by gfxmonk>
						entry['feed_name'] = dom_entry_element.getElementsByTagName('title')[0].firstChild.data
					elif dom_entry_element.nodeName == 'media:group' :
						for dom_entry_element in dom_entry_element.childNodes :
							if dom_entry_element.nodeName == 'media:content' :
								self._add_enclosure(entry, dom_entry_element.getAttribute('url'))
					## </added by gfxmonk>
					
					elif dom_entry_element.localName == 'published' :
						entry['published'] = self.iso2time(dom_entry_element.firstChild.data)
					elif dom_entry_element.localName == 'updated' :
						entry['updated'] = self.iso2time(dom_entry_element.firstChild.data)
				for entry_key in ('link','summary','author','title') :
					if entry_key not in entry :
						entry[entry_key] = u''
				for entry_key in ('published','updated','crawled') :
					if entry_key not in entry :
						entry[entry_key] = None
				if 'content' not in entry :
					entry['content'] = entry['summary']
			except StandardError, e:
				print "Exception retrieving entry: " + str(e)
				entry = None
			yield entry
			
	def get_continuation(self) :
		return self._continuation
	def iso2time(self,isodate) :
		# Ok, it's unreadable ! So, I have z == '2006-12-17T12:07:19Z',
		# I take z[0:4] and z[5:7] and etc.,
		# ('2006','12', etc.)
		# I convert them into int, And I add [0,0,0]
		# Once converted in tuple, I got (2006,12,17,12,07,19,0,0,0), which is what mktime want...
		return time.mktime(tuple(map(lambda x:int(isodate.__getslice__(*x)),self._isotime_pos)+[0,0,0]))


########NEW FILE########
__FILENAME__ = object
# TODO : Use those line when python 2.6 will be out, for now, there is no
#        reasons to not be compatible with python 2.4 just to please PEP 238 !
#        (lines will be mandatory only with python 2.7)
# from .const import CONST
from const import CONST

from xml.dom import minidom

class GoogleObject(object) :
    """ This class aims at reading 'object' xml structure.
        Look like it's based on something jsoinsable.
        ( http://json.org/ )
        Yes I'm a moron ( in the sense defined by the asshole/moron spec
        http://www.diveintomark.org/archives/2004/08/16/specs ),
        which means everything is just supposition.

        A json can contains only string, number, object, array, true,
        false, null.

        It look like Google Reader use string for true and false.
        Never seen 'null' neither.

        A GoogleObject can only contains string, number, object, array
        """
    def __init__(self,xmlobject) :
        """ 'xmlobject' is the string containing the answer from Google as
            an object jsonizable. """
        self._document = minidom.parseString(xmlobject)
    def parse(self) :
        """ 'parse' parse the object and return the pythonic version of
            the object. """
        return self._parse_dom_element(self._document.childNodes[0])
    def _parse_dom_element(self,dom_element) :
        value = None
        if dom_element.localName == 'object' :
            value = {}
            for childNode in dom_element.childNodes :
                if childNode.localName != None :
                    name = childNode.getAttribute('name')
                    value[name] = self._parse_dom_element(childNode)
        elif dom_element.localName == 'list' :
            value = []
            for childNode in dom_element.childNodes :
                if childNode.localName != None :
                    value.append(self._parse_dom_element(childNode))
        elif dom_element.localName == 'number' :
            value = int(dom_element.firstChild.data)
        elif dom_element.localName == 'string' :
            value = dom_element.firstChild.data
        # let's act as a total moron : Never seen those balise, but
        # I can imagine them may exist by reading http://json.org/
        elif dom_element.localName == 'true' :
            value = True
        elif dom_element.localName == 'false' :
            value = False
        elif dom_element.localName == 'null' :
            value = None
        return value


########NEW FILE########
__FILENAME__ = reader
import time
import urllib
import cookielib
# TODO : Get rise of web package.
from web import web

# TODO : Use those line when python 2.6 will be out, for now, there is no
#		 reasons to not be compatible with python 2.4 just to please PEP 238 !
#		 (lines will be mandatory only with python 2.7)
# from .feed import GoogleFeed
# from .object import GoogleObject
# from .const import CONST
from feed import GoogleFeed
from object import GoogleObject
from const import CONST

def utf8(s):  return s.encode('utf-8','ignore') if isinstance(s, unicode) else str(s)

class GoogleReader(object) :
	'''This class provide python binding for GoogleReader http://google.com/reader/'''
	def __init__(self,agent=None,http_proxy=None) :
		self._login = None
		self._passwd = None

		self._agent = agent or CONST.AGENT
		self._web = web(agent=self._agent,http_proxy=http_proxy)
		self._sid = None

		self._token = None

	# ---------------------------------------------------------------
	# Login process
	# ---------------------------------------------------------------

	def identify(self,login,passwd) :
		''' Provide login and passwd to the GoogleReader object. You must call this before login.'''
		self._login = login
		self._passwd = passwd

	def login(self) :
		''' Login into GoogleReader. You must call identify before calling this.
			You must call this before anything else that acces to GoogleReader data.'''
		if self._login==None or self._passwd == None :
			return


		data = {
			'service':'reader',
			'Email':self._login,
			'Passwd':self._passwd,
			'source':CONST.AGENT,
			'continue':'http://www.google.com/',
			}

		sidinfo = self._web.get( CONST.URI_LOGIN, data )
		# print sidinfo

		self._sid = None
		SID_ID = 'Auth='
		if SID_ID in sidinfo :
			pos_beg = sidinfo.find(SID_ID)
			pos_end = sidinfo.find('\n',pos_beg)
			self._sid = sidinfo[pos_beg+len(SID_ID):pos_end]
		if self._sid != None :
			self._web.set_auth(self._sid)

			return True

	# ---------------------------------------------------------------
	# Very low
	# ---------------------------------------------------------------

	def get_token(self,force=False) :
		'''Return a tokey. A token is a special string that is used like a session identification, but that expire rather quickly.'''
		if ( force or (self._token == None) ) :
			feedurl = CONST.URI_PREFIXE_API + CONST.API_TOKEN + '?client=' + CONST.AGENT
			# print feedurl
			self._token = self._web.get(feedurl)
		return self._token

	def get_timestamp(self) :
		return str(int(1000*time.time()))

	def _translate_args(self, dictionary, googleargs, kwargs) :
		""" _translate_args takes a 'dictionary' to translate argument names
			in 'kwargs' from this API to google names.
			It also serve as a filter.
			Nothing is returned 'googleargs' is just updated.
			"""
		for arg in dictionary :
			if arg in kwargs :
				googleargs[dictionary[arg]] = kwargs[arg]
			if dictionary[arg] in kwargs :
				googleargs[dictionary[arg]] = kwargs[dictionary[arg]]

	# ---------------------------------------------------------------
	# Low
	# ---------------------------------------------------------------
	def get_feed(self,url=None,feed=None,**kwargs) :
		""" 'get_feed' returns a GoogleFeed, giving either an 'url' or a 'feed' internal name.
			other arguments may be any keys of CONST.ATOM_ARGS keys
			"""
		if url != None :
			feedurl = CONST.ATOM_GET_FEED + urllib.quote_plus(url)
		if feed == None :
			feedurl = CONST.ATOM_STATE_READING_LIST
		else:
			feedurl = urllib.quote(utf8(feed))
		
		feedurl = CONST.URI_PREFIXE_ATOM + feedurl
		
		urlargs = {}
		kwargs['client'] = CONST.AGENT
		kwargs['timestamp'] = self.get_timestamp()
		self._translate_args( CONST.ATOM_ARGS, urlargs, kwargs )

		atomfeed = self._web.get(feedurl + '?' + urllib.urlencode(urlargs))

		if atomfeed != '' :
			return GoogleFeed(atomfeed)

		return None

	def get_api_list(self,apiurl,**kwargs) :
		""" 'get_api_list' returns a structure than can be send either
			by json or xml, I used xml because... I felt like it.
			"""
		urlargs = {}
		kwargs['output'] = CONST.OUTPUT_XML
		kwargs['client'] = CONST.AGENT
		kwargs['timestamp'] = self.get_timestamp()
		self._translate_args( CONST.LIST_ARGS, urlargs, kwargs )
		xmlobject = self._web.get(apiurl + '?' + urllib.urlencode(urlargs))
		if xmlobject != '' :
			return GoogleObject(xmlobject).parse()
		return None

	def edit_api( self, target_edit, dict_args, **kwargs ) :
		""" 'edit_api' wrap Google Reader API for editting database.
			"""
		urlargs = {}
		urlargs['client'] = CONST.AGENT

		postargs = {}
		kwargs['token'] = self.get_token()
		self._translate_args( dict_args, postargs, kwargs )

		feedurl = CONST.URI_PREFIXE_API + target_edit + '?' + urllib.urlencode(urlargs)
		result_edit = self._web.post(feedurl,postargs)
		# print "result_edit:[%s]"%result_edit
		if result_edit != 'OK' :
			# just change the token and try one more time !
			kwargs['token'] = self.get_token(force=True)
			self._translate_args( dict_args, postargs, kwargs )
			result_edit = self._web.post(feedurl,postargs)
			# print "result_edit_bis:[%s]"%result_edit
		return result_edit

	# ---------------------------------------------------------------
	# Middle
	# ---------------------------------------------------------------

	def edit_tag( self, **kwargs ) :
		if 'feed' not in kwargs :
			kwargs['feed'] = CONST.ATOM_STATE_READING_LIST
		kwargs['action'] = 'edit-tags'

		return self.edit_api( CONST.API_EDIT_TAG, CONST.EDIT_TAG_ARGS, **kwargs )

	def edit_subscription( self, **kwargs ) :
		if 'action' not in kwargs :
			kwargs['action'] = 'edit'
		if 'item' not in kwargs :
			kwargs['item'] = 'null'
		return self.edit_api( CONST.API_EDIT_SUBSCRIPTION, CONST.EDIT_SUBSCRIPTION_ARGS, **kwargs )

	def get_preference(self) :
		""" 'get_preference' returns a structure containing preferences.
			"""
		return self.get_api_list(CONST.URI_PREFIXE_API + CONST.API_LIST_PREFERENCE)

	def get_subscription_list(self) :
		""" 'get_subscription_list' returns a structure containing subscriptions.
			"""
		return self.get_api_list(CONST.URI_PREFIXE_API + CONST.API_LIST_SUBSCRIPTION)

	def get_tag_list(self) :
		""" 'get_tag_list' returns a structure containing tags.
			"""
		return self.get_api_list(CONST.URI_PREFIXE_API + CONST.API_LIST_TAG)

	def get_unread_count_list(self) :
		""" 'get_unread_count_list' returns a structure containing the number
			of unread items in each subscriptions/tags.
			"""
		return self.get_api_list(CONST.URI_PREFIXE_API + CONST.API_LIST_UNREAD_COUNT, all='true')

	# ---------------------------------------------------------------
	# High
	# ---------------------------------------------------------------

	def get_all(self) :
		return self.get_feed()

	def get_unread(self) :
		return self.get_feed( exclude_target=CONST.ATOM_STATE_READ )

	def set_read(self,entry) :
		return self.edit_tag( entry=entry, add=CONST.ATOM_STATE_READ, remove=CONST.ATOM_STATE_UNREAD )

	def set_unread(self,entry) :
		return self.edit_tag( entry=entry, add=CONST.ATOM_STATE_UNREAD, remove=CONST.ATOM_STATE_READ )

	def add_star(self,entry) :
		return self.edit_tag( entry=entry, add=CONST.ATOM_STATE_STARRED )

	def del_star(self,entry) :
		return self.edit_tag( entry=entry, remove=CONST.ATOM_STATE_STARRED )

	def add_public(self,entry) :
		return self.edit_tag( entry=entry, add=CONST.ATOM_STATE_BROADCAST )

	def del_public(self,entry) :
		return self.edit_tag( entry=entry, remove=CONST.ATOM_STATE_BROADCAST )

	def add_label(self,entry,labelname) :
		return self.edit_tag( entry=entry, add=CONST.ATOM_PREFIXE_LABEL+labelname )

	def del_label(self,entry,labelname) :
		return self.edit_tag( entry=entry, remove=CONST.ATOM_PREFIXE_LABEL+labelname )

	def add_subscription(self,url=None,feed=None,labels=[],**kwargs) :
		postargs = {}
		result_edit = None
		if (feed is not None) or (url is not None) :
			if feed is None :
				kwargs['url'] = url
				kwargs['token'] = self.get_token(force=True)
				self._translate_args( CONST.QUICKADD_ARGS, postargs, kwargs )
				result_edit = self._web.post(CONST.URI_QUICKADD,postargs)
				# print "result_edit:[%s]"%result_edit
				if "QuickAdd_success('" in result_edit :
					start_pos = result_edit.find("QuickAdd_success('")
					stop_pos = result_edit.rfind("')")
					uri_orig, feed = result_edit[start_pos+len("QuickAdd_success('"):stop_pos].split("','")
			else :
				result_edit = self.edit_subscription(feed=feed,action='subscribe')
			for label in labels :
				# print feed,CONST.ATOM_PREFIXE_LABEL+label
				self.edit_subscription(feed=feed,add=CONST.ATOM_PREFIXE_LABEL+label.lower())
		return result_edit

	def del_subscription(self,feed,**kwargs) :
		postargs = {}
		result_edit = None
		if feed is not None :
			result_edit = self.edit_subscription(feed=feed,action='unsubscribe')
		return result_edit

def test() :
	from private import login_info

	gr = GoogleReader()
	gr.identify(**login_info)
	if gr.login():
		print "Login OK"
	else :
		print "Login KO"
		return
	#print "[%s]" % gr.get_token()

	# print gr.set_read("tag:google.com,2005:reader/item/c3abf620979a5d06")
	# print gr.set_unread("tag:google.com,2005:reader/item/8b1030db93c70e9e")
	# print gr.del_label(entry="tag:google.com,2005:reader/item/8b1030db93c70e9e",labelname="vorkana")
	# xmlfeed = gr.get_feed(feed=CONST.ATOM_PREFIXE_LABEL+'url',order=CONST.ORDER_REVERSE,start_time=1165482202,count=15)
	# print xmlfeed
	# print xmlfeed.get_title()
	# for entry in xmlfeed.get_entries() :
	#	  print "	 %s\n"%entry['title']
	#	  print "	   %s\n"%entry['published']
	# continuation = xmlfeed.get_continuation()
	# print "(%s)\n"%continuation
	#
	# while continuation != None :
	#	  xmlfeed = gr.get_feed(feed=CONST.ATOM_PREFIXE_LABEL+'url',order=CONST.ORDER_REVERSE,start_time=1165482202,count=2,continuation=continuation)
	#	  print xmlfeed
	#	  print xmlfeed.get_title()
	#	  for entry in xmlfeed.get_entries() :
	#		  print "	 %s\n"%entry['title']
	#		  print "	   %s\n"%entry['published']
	#	  continuation = xmlfeed.get_continuation()
	#	  print "(%s)\n"%continuation

	# print gr.get_preference()
	# print gr.get_subscription_list()
	# print gr.get_tag_list()


	# print gr.get_feed("http://action.giss.ath.cx/RSSRewriter.py/freenews",order=CONST.ORDER_REVERSE,start_time=1165482202,count=2)

	#gf = GoogleFeed(xmlfeed)
	#print gf.get_title()


	xmlfeed = gr.get_feed(order=CONST.ORDER_REVERSE,count=3,ot=1166607627)
	print xmlfeed.get_title()
	for entry in xmlfeed.get_entries() :
		print "	   %s %s %s\n" % (entry['google_id'],entry['published'],entry['title'])
	print xmlfeed.get_continuation()

	xmlfeed = gr.get_feed(order=CONST.ORDER_REVERSE,count=3)
	print xmlfeed.get_title()
	for entry in xmlfeed.get_entries() :
		print "	   %s %s %s\n" % (entry['google_id'],entry['published'],entry['title'])
	print xmlfeed.get_continuation()

if __name__=='__main__' :
	test()

########NEW FILE########
__FILENAME__ = resolvUrl
#!/usr/bin/env python

import urllib2

def resolvUrl( base, rel ) :
    urlbase = urllib2.urlparse.urlparse(base)
    urlrel = urllib2.urlparse.urlparse(rel)
    urlfinal = ('','','','','','')
    # Let's assume len(urlrel[0])==0 <=> len(urlrel[1])==0
    # (they are both empty or both non empty)

    # Let's ignore 3 !
    if urlrel[1] == '' :
        if urlrel[2]=='' :
            # this is a '?p=1' or a '#anchor' url...
            if urlrel[4]=='' :
                urlfinal = urlbase[0:5] + urlrel[5:6]
            else :
                urlfinal = urlbase[0:4] + urlrel[4:6]
        else :
            if urlrel[2][0] == '/' :
                # The path is absolute, but without server...
                urlfinal = urlbase[0:2] + urlrel[2:6]
            else :
                # The path is relative, without server...
                urlfinal = urlbase[0:2] + ( urllib2.posixpath.join( urllib2.posixpath.dirname(urlbase[2]), urlrel[2] ), ) + urlrel[3:6]
    else :
        # The rel is absolute...
        urlfinal = urlrel

    return urllib2.urlparse.urlunparse(urlfinal)



########NEW FILE########
__FILENAME__ = SSLproxy
# urllib2 opener to connection through a proxy using the CONNECT method, (useful for SSL)
# tested with python 2.4

"""Code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/456195 modified by comments on the same page."""

import urllib2
import urllib
import httplib
import socket


class ProxyHTTPConnection(httplib.HTTPConnection):

    _ports = {'http' : 80, 'https' : 443}


    def request(self, method, url, body=None, headers={}):
        #request is called before connect, so can interpret url and get
        #real host/port to be used to make CONNECT request to proxy
        proto, rest = urllib.splittype(url)
        if proto is None:
            raise ValueError, "unknown URL type: %s" % url
        #get host
        host, rest = urllib.splithost(rest)
        #try to get port
        host, port = urllib.splitport(host)
        #if port is not defined try to get from proto
        if port is None:
            try:
                port = self._ports[proto]
            except KeyError:
                raise ValueError, "unknown protocol for: %s" % url
        self._real_host = host
        self._real_port = port
        httplib.HTTPConnection.request(self, method, url, body, headers)


    def connect(self):
        httplib.HTTPConnection.connect(self)
        #send proxy CONNECT request
        self.send("CONNECT %s:%d HTTP/1.0\r\n\r\n" % (self._real_host, self._real_port))
        #expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict, method=self._method)
        (version, code, message) = response._read_status()
        #probably here we can handle auth requests...
        if code != 200:
            #proxy returned and error, abort connection, and raise exception
            self.close()
            raise socket.error, "Proxy connection failed: %d %s" % (code, message.strip())
        #eat up header block from proxy....
        while True:
            #should not use directly fp probablu
            line = response.fp.readline()
            if line == '\r\n': break


class ProxyHTTPSConnection(ProxyHTTPConnection):

    default_port = 443

    def __init__(self, host, port = None, key_file = None, cert_file = None, strict = None):
        ProxyHTTPConnection.__init__(self, host, port)
        self.key_file = key_file
        self.cert_file = cert_file

    def connect(self):
        ProxyHTTPConnection.connect(self)
        #make the sock ssl-aware
        ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
        self.sock = httplib.FakeSocket(self.sock, ssl)

class ConnectHTTPHandler(urllib2.HTTPHandler):
    """Code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/456195 from comment Norm Petterson, 2006/05/04"""
    def __init__(self, proxy=None, debuglevel=0):
        self.proxy = proxy
        urllib2.HTTPHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):
        if self.proxy is not None:
            req.set_proxy(self.proxy, 'http')
        return urllib2.HTTPHandler.do_open(self, ProxyHTTPConnection, req)

class ConnectHTTPSHandler(urllib2.HTTPSHandler):
    """Code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/456195 from comment Norm Petterson, 2006/05/04"""

    def __init__(self, proxy=None, debuglevel=0):
        self.proxy = proxy
        urllib2.HTTPSHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):
        if self.proxy is not None:
            req.set_proxy(self.proxy, 'https')
        return urllib2.HTTPSHandler.do_open(self, ProxyHTTPSConnection, req)

class ConnectHTTPSOverHTTPHandler(urllib2.HTTPHandler):
    """ Try to include code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/456195 from comment yin sun, 2006/06/16 """
    def __init__(self, proxy=None, debuglevel=0):
        self.proxy = proxy
        urllib2.HTTPSHandler.__init__(self, debuglevel)

    def do_open(self, http_class, req):
        if self.proxy is not None:
            req.set_proxy(self.proxy, 'https')
        return urllib2.HTTPHandler.do_open(self, ProxyHTTPSConnection, req)

if __name__ == '__main__':

    import sys

    opener = urllib2.build_opener(ConnectHTTPHandler, ConnectHTTPSHandler)
    urllib2.install_opener(opener)
    req = urllib2.Request(url='https://192.168.1.1')
    req.set_proxy('192.168.1.254:3128', 'https')
    f = urllib2.urlopen(req)
    print f.read()

########NEW FILE########
__FILENAME__ = web
#!/usr/bin/perl

# --------------------------------------------------------------

import socket
import urllib
import urllib2
import cookielib

from resolvUrl.resolvUrl import resolvUrl
# from SSLproxy import ConnectHTTPHandler
from SSLproxy import ConnectHTTPSHandler

# --------------------------------------------------------------

DEFAULT_AGENT = "Mozilla/4.0 (compatible; MSIE 5.5; Windows 98; Win 9x 4.90)"

# --------------------------------------------------------------

class AppURLopener(urllib.FancyURLopener):
	def __init__(self, version, *args):
		self.version = version
		urllib.FancyURLopener.__init__(self, *args)

# --------------------------------------------------------------

class webUrllib :
	def __init__( self, agent = DEFAULT_AGENT, http_proxy=None	) :
		# http_proxy is not used now.

		self._agent = agent
		urllib._urlopener = AppURLopener(agent)

	def get ( self, url, file=None, encoding='utf-8' ) :
		result = ""
		url = url.encode(encoding)
		try :
			if file == None :
				f = urllib.urlopen( url )
				for line in f.readlines() :
					result += line
			else :
				result = urllib.urlretrieve( url, file )
				result = result[0]
		except IOError :
			pass
		except socket.error :
			pass
		return result

	def post(self, *args, **kwargs) :
		raise Exception("Not Implemented")

	def cookies(self) :
		return None

# --------------------------------------------------------------

class webUrllib2 :
	def __init__( self, agent = DEFAULT_AGENT, http_proxy=None ) :
		self.auth = None
		self._agent = agent

		openers = []

		proxy_support = None
		if http_proxy is not None :
			# Look like urllib2 default proxy works better than ConnectHTTPHandler
			#openers.append(ConnectHTTPHandler(proxy="%s:%s" % (http_proxy[0],http_proxy[1]),debuglevel=1))
			openers.append(urllib2.ProxyHandler({"http" : "http://%s:%s" % (http_proxy[0],http_proxy[1])}))

			openers.append(ConnectHTTPSHandler(proxy="%s:%s" % (http_proxy[0],http_proxy[1])))


		self._cookiejar = cookielib.LWPCookieJar()
		openers.append(urllib2.HTTPCookieProcessor(self._cookiejar))

		opener = urllib2.build_opener(*openers)
		urllib2.install_opener(opener)
	
	def set_auth(self, auth):
		self.auth = auth

	def get ( self, url, postargs=None, file=None, encoding='utf-8', cookie=None ) :
		result = ""

		url = url.encode(encoding)

		postdata = None

		if postargs != None :
			postdata = urllib.urlencode(postargs)

		header = {'User-agent' : self._agent}
		if cookie :
			header['Cookie']=cookie
		if self.auth:
			header['Authorization']="GoogleLogin auth=%s" % (self.auth,)

		#print self._cookiejar
		#print url
		request = urllib2.Request(url, postdata, header)

		#print "[ %s ]" % self._cookiejar._cookies_for_request(request)
		# print repr(header)
		self._cookiejar.add_cookie_header(request)

		f = urllib2.urlopen( request )
		result = f.read()
		if file != None :
			handle = open(file,'wb')
			handle.write(result)
			handle.close()
			result = file
			
		return result

	def post ( self, *args, **kwargs ) :
		return self.get(*args,**kwargs)

	def cookies(self) :
		return self._cookiejar

# --------------------------------------------------------------

web = webUrllib2

# --------------------------------------------------------------

if __name__ == "__main__" :
	w = web()
	print "%s\n-------------------" % w.get("http://giss.mine.nu/")

# --------------------------------------------------------------

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2008 Michael Foord
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.4.0
# http://www.voidspace.org.uk/python/mock.html

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.

__all__ = (
    'Mock',
    'patch',
    'patch_object',
    'sentinel',
    '__version__'
)

__version__ = '0.4.0'

DEFAULT = object()


class Mock(object):
    def __init__(self, methods=None, spec=None, side_effect=None, 
                 return_value=DEFAULT, name=None, parent=None):
        self._parent = parent
        self._name = name
        if spec is not None and methods is None:
            methods = [member for member in dir(spec) if not 
                       (member.startswith('__') and  member.endswith('__'))]
        self._methods = methods
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        
        self.reset()
        
        
    def reset(self):
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.itervalues():
            child.reset()
        if isinstance(self._return_value, Mock):
            self._return_value.reset()
        
    
    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = Mock()
        return self._return_value
    
    def __set_return_value(self, value):
        self._return_value = value
        
    return_value = property(__get_return_value, __set_return_value)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = (args, kwargs)
        self.call_args_list.append((args, kwargs))
        
        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append((name, args, kwargs))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        if self.side_effect is not None:
            self.side_effect()
            
        return self.return_value
    
    
    def __getattr__(self, name):
        if self._methods is not None and name not in self._methods:
            raise AttributeError("object has no attribute '%s'" % name)
        
        if name not in self._children:
            self._children[name] = Mock(parent=self, name=name)
            
        return self._children[name]
    
    
    def assert_called_with(self, *args, **kwargs):
        assert self.call_args == (args, kwargs), 'Expected: %s\nCalled with: %s' % ((args, kwargs), self.call_args)
        

        
def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _patch(target, attribute, new):
        
    def patcher(func):
        original = getattr(target, attribute)
        if hasattr(func, 'restore_list'):
            func.restore_list.append((target, attribute, original))
            func.patch_list.append((target, attribute, new))
            return func
        
        func.restore_list = [(target, attribute, original)]
        func.patch_list = [(target, attribute, new)]
        
        def patched(*args, **keywargs):
            for target, attribute, new in func.patch_list:
                if new is DEFAULT:
                    new = Mock()
                    args += (new,)
                setattr(target, attribute, new)
            try:
                return func(*args, **keywargs)
            finally:
                for target, attribute, original in func.restore_list:
                    setattr(target, attribute, original)
                    
        patched.__name__ = func.__name__ 
        patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno", 
                                                func.func_code.co_firstlineno)
        return patched
    
    return patcher


def patch_object(target, attribute, new=DEFAULT):
    return _patch(target, attribute, new)


def patch(target, new=DEFAULT):
    try:
        target, attribute = target.rsplit('.', 1)    
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %s" % (target,))
    target = _importer(target)
    return _patch(target, attribute, new)


class SentinelObject(object):
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return '<SentinelObject "%s">' % self.name


class Sentinel(object):
    def __init__(self):
        self._sentinels = {}
        
    def __getattr__(self, name):
        return self._sentinels.setdefault(name, SentinelObject(name))
    
    
sentinel = Sentinel()

########NEW FILE########
__FILENAME__ = OpenStruct
# cheerfully stolen from http://snippets.dzone.com/posts/show/5116
class OpenStruct:
	def __init__(self, **dic):
		self.__dict__.update(dic)
	def __getattr__(self, i):
		if i in self.__dict__:
			return self.__dict__[i]
		else:
			raise AttributeError, i
	def __setattr__(self,i,v):
		if i in self.__dict__:
			self.__dict__[i] = v
		else:
			self.__dict__.update({i:v})
		return v
	def __getitem__(self, i):
		return self.__getattr__(i)
########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# general includes
import sys, glob, urllib2, os, commands

# local includes
import config
from db import DB
from item import Item
import proctl
import signal
from misc import *
from output import *
from lib.GoogleReader import GoogleReader, CONST
import app_globals
import template
from reader import Reader
import url_save
from thread_pool import ThreadPool

TASK_PROGRESS = 0
CANCELLED = False

def new_task(description=""):
	global TASK_PROGRESS
	status("TASK_PROGRESS", TASK_PROGRESS, description)
	TASK_PROGRESS += 1

def handle_signal(signum, stack):
	global CANCELLED
	print "Signal caught: %s" % (signum,)
	status("TASK_PROGRESS", TASK_PROGRESS, "Cancelled")
	CANCELLED = True
	cleanup()
	sys.exit(2)
	
def cleanup():
	if app_globals.DATABASE is not None:
		app_globals.DATABASE.close()
	app_globals.URLSAVE = None
	app_globals.READER = None
	
def init_signals():
	pass
	# signal.signal(signal.SIGINT, handle_signal)
	# signal.signal(signal.SIGTERM, handle_signal)

def save_db_state():
	debug("saving database state...")
	app_globals.DATABASE.close()
	app_globals.DATABASE = DB()

def execute():
	"""
	Logs in, syncs and downloads new items
	"""
	steps = 3
	download_steps = 0
	if not app_globals.OPTIONS['no_download']:
		download_steps = len(app_globals.OPTIONS['tag_list'])
		if download_steps < 1: download_steps = 1
		steps += download_steps
	
	status("TASK_TOTAL",steps)
	new_task("Authorizing")
	
	ensure_dir_exists(app_globals.OPTIONS['output_path'])
	ensure_dir_exists(app_globals.OPTIONS['output_path'] + '/' + app_globals.CONFIG['resources_path'])
	
	app_globals.URLSAVE = url_save.get_active_service()
	
	app_globals.READER = Reader()
	app_globals.READER.save_tag_list()
	if app_globals.OPTIONS['tag_list_only']:
		info("Got all tags.")
		return

	app_globals.OPTIONS['tag_list'] = app_globals.READER.validate_tag_list(app_globals.OPTIONS['tag_list'], False)

	new_task("Pushing status")

	line()
	app_globals.DATABASE = DB()
	
	# we now have something we need to clean up on interrupt:
	init_signals()
	
	app_globals.DATABASE.sync_to_google()
	
	if app_globals.OPTIONS['no_download']:
		info("not downloading any new items...")
	else:
		app_globals.DATABASE.prepare_for_download()
		download_new_items()
		new_task("Cleaning up old resources")
		app_globals.DATABASE.cleanup() # remove old _resources files

def download_feed(feed, feed_tag):
	new_subtask(len(feed) * 2)
	item_thread_pool = ThreadPool()
	for entry in feed.get_entries():
		increment_subtask()
	
		app_globals.STATS['items'] += 1

		if entry is None:
			app_globals.STATS['failed'] += 1
			error(" ** FAILED **")
			debug("(entry is None)")
			continue
		
		item = Item(entry, feed_tag)
		process_item(item, item_thread_pool)
		item_thread_pool.collect()
	item_thread_pool.collect_all()

def error_reporter_for_item(item):
	def error_report(exception, tb = None):
		error(" ** FAILED **: ", exc_info=True)
		app_globals.STATS['failed'] += 1
	return error_report

def process_item(item, item_thread_pool = None):
	db_item = app_globals.DATABASE.get(item.google_id, None)
	name = item.basename
	
	item_is_read = item.is_read or (db_item is not None and db_item.is_read)
	if item_is_read:
		# item has been read either online or offline
		debug("READ: " + name)
		app_globals.STATS['read'] += 1
		danger("About to delete item")
		item.delete()
		increment_subtask()
		return

	if db_item is not None:
		# we aready know about it - update any necessary info
		if db_item.had_errors or db_item.tag_name != item.tag_name:
			app_globals.STATS['reprocessed'] += 1
			debug("setting %s tag name to %s" % (db_item, item.tag_name))
			db_item.tag_name = item.tag_name
			if db_item.had_errors:
				debug("reprocessing erroneous item: %s" % (item.title,))
				db_item.redownload_images()
		db_item.update()
		increment_subtask()
	else:
		try:
			info("NEW: " + item.title)
			danger("About to output item")
			app_globals.STATS['new'] += 1
			if item_thread_pool is None:
				item.process()
				item.save()
				increment_subtask()
			else:
				def success_func():
					increment_subtask()
					item.save()
				item_thread_pool.spawn(
					item.process,
					name = item.title[:13],
					on_success = success_func,
					on_error = error_reporter_for_item(item))

		except StandardError,e:
			error_reporter_for_item(item)(e)
		
def download_new_items():
	"""
	Downloads new items from google reader across all feeds
	"""
	tag_list = app_globals.OPTIONS['tag_list']

	# special case: no tags specified so we download the global set
	if len(tag_list) == 0:
		tag_list = [None]
	
	status("SUBTASK_TOTAL", len(tag_list) * app_globals.OPTIONS['num_items'])

	for feed_tag in tag_list:
		line()
		save_db_state()
		_feed_tag = "All Items" if feed_tag is None else feed_tag
		new_task("Downloading tag \"%s\"" % (_feed_tag,))
		info("Fetching maximum %s items from feed %s" % (app_globals.OPTIONS['num_items'], _feed_tag))
		feed = app_globals.READER.get_tag_feed(feed_tag, oldest_first = not app_globals.OPTIONS['newest_first'])
		download_feed(feed, _feed_tag)
		
	line()
	
	info("%s NEW items" % app_globals.STATS['new'])
	info("%s items marked as read" % app_globals.STATS['read'])
	if app_globals.STATS['reprocessed'] > 0:
		info("%s items reprocessed because of previously failed image downloads" % (app_globals.STATS['reprocessed']))
	if app_globals.STATS['failed'] > 0:
		warning("%s items failed to parse" % app_globals.STATS['failed'])

def setup(opts=None):
	"""Parse options. If none given, opts is set to sys.argv"""
	if opts is None:
		opts = sys.argv[1:]
	config.bootstrap(opts)
	config.init_logging()
	config.load()
	config.parse_options(opts)
	ensure_dir_exists(app_globals.OPTIONS['output_path'])
	log_start()
	if app_globals.OPTIONS['report_pid']:
		proctl.report_pid()
		exit(0)
	config.check()
	proctl.ensure_singleton_process()
	init_signals()

def main():
	"""
	Main program entry point - loads config, parses otions and kicks off the sync process
	"""
	setup()
	execute()
	cleanup()
	print "Sync complete."
	return 0

if __name__ == '__main__':
	exitstatus = 1
	try:
		exitstatus = main()
	except StandardError, e:
		debug('unhandled error in main()', exc_info=True)
		if not CANCELLED:
			error("ERROR: %s" % (e,))
		exitstatus = 2
	except KeyboardInterrupt:
		info("cancelled - cleaning up")
		cleanup()
		print "Cancelled."
	sys.exit(exitstatus)


########NEW FILE########
__FILENAME__ = main_test
# the tested module
import main
from item import Item
from output import *

# test helpers
import test_helper
import item_test
from lib.mock import Mock
import unittest
import os
import signal
import commands
from misc import read_file, write_file

class MainTest(unittest.TestCase):
	def setUp(self):
		self.output_folder = test_helper.init_output_folder()
		self.db = app_globals.DATABASE = Mock()
	
	def tearDown(self):
		pass

	def test_item_should_be_updated_with_new_feed_name(self):
		item = Item(item_test.sample_item)
		
		db_item = Mock()
		item.tag_name = 'feedb'
		self.db.get.return_value = db_item
		db_item.is_read = False
		db_item.had_errors = False
		
		main.process_item(item)
		
		self.assertEqual(db_item.tag_name, 'feedb')
		self.assertEqual(self.db.method_calls, [('get', (item.google_id, None), {})])
		self.assertEqual(db_item.method_calls, [('update', (), {})])
	
	def test_item_with_errors_should_have_images_redownloaded(self):
		item = Item(item_test.sample_item)
		
		db_item = Mock()
		db_item.is_read = False
		db_item.had_errors = True
		self.db.get.return_value = db_item
		
		main.process_item(item)
		
		self.assertEqual(db_item.method_calls, [('redownload_images', (), {}), ('update', (), {})])
	
	def test_item_should_not_be_updated_if_it_didnt_exist_in_db(self):
		item = item_test.sample_item.copy()
		item['content'] = ''
		item = Item(item)
		
		self.db.get.return_value = None
		main.process_item(item)
		self.assertEqual(self.db.method_calls, [('get', (item.google_id, None), {}), ('add_item', (item,), {})])

	def test_setup_should_report_pid(self):
		main.proctl = Mock()
		app_globals.OPTIONS['report_pid'] = True
		self.assertRaises(SystemExit, lambda: main.setup([]))
		self.assertTrue(main.proctl.report_pid.called)

	def test_setup_should_ensure_singleton(self):
		main.proctl = Mock()
		app_globals.OPTIONS['report_pid'] = False
		main.setup(['--user=a','--password=b'])
		self.assertTrue(main.proctl.ensure_singleton_process.called)


########NEW FILE########
__FILENAME__ = misc
import app_globals
from output import *

import os, re, sys, shutil, pickle

def danger(desc):
	"""
	if cautious mode is enabled, pauses execution of the script until the user types "yes" (or presses return).
	Any other input will cause the program to terminate with error status 2
	"""
	if not app_globals.OPTIONS['cautious']: return
	response = raw_input("%s. Continue? " % desc)
	if not re.match('[yY]|(^$)', response):
		print "Aborted."
		sys.exit(2)
		raise Exception("We should never get here!")
	print "Continuing..."

def try_remove(elem, lst):
	"""
	Try to remove an element from a list. If it fails, nobody has to know...
	"""
	try:
		lst.remove(elem)
	except ValueError:
		pass
	
def try_lookup(obj, key):
	try:
		return obj[key]
	except KeyError:
		return None

def matches_any_regex(s, regexes, flags = 0):
	"""
		>>> matches_any_regex('abcd',['.*f','agg'])
		False
		>>> matches_any_regex('abCD',['bce?d','qwert'], flags=re.IGNORECASE)
		True
	"""
	regexes = [re.compile(regex, flags) if isinstance(regex, str) else regex for regex in regexes]
	return any([regex.search(s) for regex in regexes])


def try_shell(cmd):
	"""
	Execute a shell command. if it returns a non-zero (error) status, raise an exception

		>>> try_shell('[ 0 = 0 ]')
		>>> try_shell('[ 0 = 1 ]')
		Traceback (most recent call last):
		RuntimeError: shell command failed:
		[ 0 = 1 ]
	"""
	debug("running command: " + cmd)
	if os.system(cmd) != 0:
		raise RuntimeError("shell command failed:\n%s" % cmd)

def url_dirname(url):
	"""
	returns everything before and including the last slash in a URL
	"""
	return '/'.join(url.split('/')[:-1]) + '/'

def ensure_dir_exists(path):
	"""
	takes a path, and ensures all drectories exist
	"""
	dirs = [x for x in os.path.split(path) if len(x) > 0]
	active_dirs = []
	for d in dirs:
		active_dirs.append(d)
		location = os.path.join(*active_dirs)
		if not os.path.exists(location):
			os.mkdir(location)

def rm_rf(path):
	"""
		>>> os.system('mkdir /tmp/blah && touch /tmp/blah/foo')
		0
		>>> os.path.isdir('/tmp/blah')
		True
		>>> rm_rf('/tmp/blah')
		>>> os.path.isdir('/tmp/blah')
		False
		>>> rm_rf('/tmp/blah')
	"""
	danger("About to remove ENTIRE path below:\n%s" % path)
	if os.path.exists(path):
		shutil.rmtree(path, ignore_errors = True)

def slashify_dbl_quotes(s):
	r"""
		>>> print slashify_dbl_quotes('\\ "')
		\\ \"
	"""
	return s.replace('\\','\\\\').replace('"','\\"')

def slashify_single_quotes(s):
	r"""
	>>> print slashify_single_quotes("\\ '")
	\\ \'
	"""
	return s.replace('\\','\\\\').replace("'","\\'")

def do_with_file(*args):
	file_args = args[:-1]
	func = args[-1]
	retval = None
	f = file(*file_args)
	try:
		retval = func(f)
	finally:
		f.close()
	return retval

def write_file(filename, content):
	f = file(filename, 'w')
	f.write(utf8(content))
	f.close()

def write_file_lines(filename, content):
	f = file(filename, 'w')
	for line in content:
		f.write(utf8(line))
		if not line.endswith("\n"):
			f.write("\n")
	f.close()

def read_file(filename):
	f = file(filename,'r')
	ret = unicode(f.read(), 'utf-8')
	f.close()
	return ret
	
def read_file_lines(filename):
	f = file(filename,'r')
	ret = [unicode(line, 'utf-8') for line in f.readlines()]
	f.close()
	return ret

def touch_file(name):
	ensure_dir_exists(os.path.dirname(name))
	write_file(name, '\n')
	
def save_pickle(obj, filename):
	"""
	Save pickled version of `obj` to the file named `filename`
	
		>>> save_pickle({'key':'value'}, '/tmp/test_pickle')
		>>> load_pickle('/tmp/test_pickle')
		{'key': 'value'}
	"""
	f = file(filename,'w')
	pickle.dump(obj, f)
	f.close()

def load_pickle(filename):
	"""
	Load an object from a pickle file named `filename`

		>>> save_pickle({'key':'value'}, '/tmp/test_pickle')
		>>> load_pickle('/tmp/test_pickle')
		{'key': 'value'}
	"""
	f = file(filename,'r')
	obj = pickle.load(f)
	f.close()
	return obj


def first(l):
	"""
	get the first element in a list/tuple, or return the original element if it's not subscriptable
	>>> first([1,2])
	1
	>>> first("bob")
	'b'
	>>> first(23)
	23
	"""
	try:
		return l[0]
	except TypeError, e:
		return l

if __name__ == '__main__':
	import doctest
	doctest.testmod()

########NEW FILE########
__FILENAME__ = output
import app_globals
import time, threading
import sys, os, time, traceback
import logging
from logging import info, debug, warning, error, exception

def ascii(s): return s.encode('ascii','ignore') if isinstance(s, unicode) else str(s)
def utf8(s):  return s.encode('utf-8','ignore') if isinstance(s, unicode) else str(s)

def status(*s):
	"""output a machine-readable status message"""
	if app_globals.OPTIONS['show_status']:
		print "STAT:%s" % ":".join(map(utf8, s))
		sys.stdout.flush()

subtask_progress = 0
def new_subtask(length):
	global subtask_progress
	subtask_progress = 0
	status("SUBTASK_TOTAL", length)
	status("SUBTASK_PROGRESS", 0)
	
def increment_subtask():
	global subtask_progress
	subtask_progress += 1
	status("SUBTASK_PROGRESS", subtask_progress)

# level is actually an output function, i.e. one of the above
def line(level = info):
	level('-' * 50)

def log_start():
	debug("Log started at %s." % (time.ctime(),))
	debug("app version: %s" % (_get_version(),))

def _get_version():
	try:
		vfile = file(os.path.join(app_globals.OPTIONS['output_path'], 'VERSION'), 'r')
		version = vfile.readline()
		vfile.close()
		return version
	except IOError,e:
		warning("Failed to read app version: %s" % (e,))




########NEW FILE########
__FILENAME__ = pagefeed
import urllib
import urllib2

from output import *

import app_globals
from lib.app_engine_auth import AppEngineAuth

# BASE_URI = 'http://localhost:8082/'
BASE_URI = 'http://pagefeed.appspot.com/'
APP_NAME = "pagefeed-1.0"

class PageFeed(object):
	def __init__(self, email=None, password=None):
		self.email = email or app_globals.OPTIONS['user']
		self.password = password or app_globals.OPTIONS['password']
		self.auth_key = None
	
	def _setup(self):
		if self.auth_key is None:
			debug("authorising to app engine")
			auth = AppEngineAuth(self.email, self.password)
			self.auth_key = auth.login(APP_NAME, BASE_URI)
	
	def add_urls(self, urls):
		map(self.add, urls)

	def add(self, url):
		self._setup()
		debug("adding url to pagefeed: %s" % (url,))
		self._post('page/', params={'url':url})
	
	def delete(self, url):
		self._setup()
		debug("deleting url from pagefeed: %s" % (url,))
		try:
			self._post('page/del/', params={'url':url})
		except urllib2.HTTPError, e:
			if e.code == 404:
				info("couldn't delete %s from PageFeed - no such URL" % (url,))
			else:
				raise

	# ------------------------------

	def _post(self, relative_uri, params={}):
		req = urllib2.Request(BASE_URI + relative_uri, data=self._data(params))
		return self._load(req)
	
	def _load(self, request):
		try:
			response = urllib2.urlopen(request)
			return response.read()
		except urllib2.HTTPError, e:
			warning("PageFeed request failed (response code: %s)" % (e.code,))
			raise

	def _data(self, params):
		params = params.copy()
		params['auth'] = self.auth_key
		encoded = urllib.urlencode(params)
		return encoded

	def _get(self, relative_uri, params={}):
		req = urllib2.Request(BASE_URI + relative_uri + '?' + self._data(params))
		return self._load(req)
	

########NEW FILE########
__FILENAME__ = process
import thread_pool
import urllib2, re, os

from lib.BeautifulSoup import BeautifulSoup, Tag
from misc import *
from output import *
import app_globals

# don't bother downloading images smaller than this
MIN_IMAGE_BYTES = 512


image_extensions = ['jpg','jpeg','gif','png','bmp', 'tif','tiff']

def is_image(url):
	filetype = url.split('.')[-1].lower()
	if filetype not in image_extensions:
		return False
	return True

## processing modules:
def insert_alt_text(soup):
	"""
	insert bolded image title text after any image on the page
		>>> soup = BeautifulSoup('<p><img src="blah" title="some texts" /></p>')
		>>> insert_alt_text(soup)
		True
		>>> soup
		<p><img src="blah" title="some texts" /><p><b>(&nbsp;some texts&nbsp;)</b></p></p>
	"""
	images = soup.findAll('img',{'title':True})
	for img in images:
		title = img['title'].strip()
		if len(title) > 0:
			desc = BeautifulSoup('<p><b>(&nbsp;%s&nbsp;)</b></p>' % title)
			img.append(desc)
	return True

def strip_params_from_image_url(url):
	"""
	returns the url without query parameters, but only if the url location ends in a known image extension
	
		>>> strip_params_from_image_url('abc/de?x=y')
		'abc/de?x=y'
		>>> strip_params_from_image_url('abc/de.JPG?x=y')
		'abc/de.JPG'
		>>> strip_params_from_image_url('abc')
		'abc'
	"""
	if not '?' in url: return url
	location = url.split('?')[0]
	if is_image(location): return location
	return url

def insert_enclosure_images(soup, url_list):
	"""
	Insert a set of images (url_list) into the soup as html tags.
	A <br /> tag will be inserted before each added image.
	
	Images from the content will not be duplicated.
	If an image URL ends in a known image format (eg ".jpg"), query parameters will be stripped off when comparing URLs
	NOTE: no attempt is made to compare absolute / canonical URLs (it's just a string comparison)

	
		>>> from lib.mock import Mock
		>>> ensure_dir_exists = Mock()
		>>> import process
		>>> process.download_file = Mock()
		>>> process.download_file.return_value = "image.jpg"
		
		>>> soup = BeautifulSoup('<p>some text is here</p>')
		>>> insert_enclosure_images(soup, ['http://example.com/image.jpg', 'not-an-image.txt'])
		True
		>>> soup
		<p>some text is here</p><br /><img src="http://example.com/image.jpg" />

		>>> soup = BeautifulSoup('what about without a root element?')
		>>> insert_enclosure_images(soup, ['http://example.com/image.jpg', 'another-image.gif'])
		True
		>>> soup
		what about without a root element?<br /><img src="http://example.com/image.jpg" /><br /><img src="another-image.gif" />
		
		>>> soup = BeautifulSoup('<img src="a.gif" />')
		>>> insert_enclosure_images(soup, ['b.jpg', 'a.gif'])
		True
		>>> soup
		<img src="a.gif" /><br /><img src="b.jpg" />
		
		>>> soup = BeautifulSoup('<img src="a.gif?query=foo" />')
		>>> insert_enclosure_images(soup, ['a.gif?query=bar'])
		True
		>>> soup
		<img src="a.gif?query=foo" />

		# no query culling when url does not look like an image
		>>> soup = BeautifulSoup('<img src="a?query=foo" />')
		>>> insert_enclosure_images(soup, ['a?query=bar.jpg'])
		True
		>>> soup
		<img src="a?query=foo" /><br /><img src="a?query=bar.jpg" />

	"""
	existing_image_urls = []
	for existing_image in soup.findAll('img'):
		try:
			existing_image_urls.append(strip_params_from_image_url(existing_image['src']))
		except KeyError: pass
	
	for image_url in [url for url in url_list if is_image(url) and strip_params_from_image_url(url) not in existing_image_urls]:
		img = Tag(soup, 'img')
		img['src'] = image_url
		soup.append(Tag(soup, 'br'))
		soup.append(img)
	return True
	

def download_images(soup, dest_folder, href_prefix, base_href = None):
	"""
	Download all referenced images to the {dest} folder
	Replace href attributes with {href_prefix}/output_filename
	
		>>> from lib.mock import Mock
		>>> ensure_dir_exists = Mock()
		>>> import process
		>>> process.download_file = Mock()
		>>> process.download_file.return_value = "image.jpg"
		
		>>> soup = BeautifulSoup('<img src="http://google.com/image.jpg?a=b&c=d"/>')
		>>> process.download_images(soup, 'dest_folder', 'local_folder/')
		True
		>>> soup
		<img src="local_folder/image.jpg" />
	
		# (make sure the file was downloaded from the correct URL:)
		>>> process.download_file.call_args
		((u'http://google.com/image.jpg?a=b&c=d', 'image.jpg'), {'base_path': 'dest_folder'})
	"""
	images = soup.findAll('img',{'src':True})
	success = True
	
	if len(images) > 0:
		ensure_dir_exists(dest_folder)
	img_num = 0
	for img in images:
		debug("processing image %s of %s" % (img_num, len(images)))
		img_num += 1
		if img['src'].startswith(app_globals.CONFIG['resources_path']):
			continue
		href = absolute_url(img['src'], base_href)
		
		filename = get_filename(img['src'])
		try:
			filename = download_file(href, filename, base_path=dest_folder)
			if filename is not None:
				img['src'] = urllib2.quote(href_prefix + filename)
		except StandardError, e:
			info("Image %s failed to download: %s" % (img['src'], e))
			success = False
		
		# since this is a long running process; let the thread know we're still alive
		thread_pool.ping()
	
	return success



###############################
#   here be helper methods:   #
###############################

def absolute_url(url, base = None):
	"""
	grab the absolute URL of a link that comes from {base}
	
		>>> absolute_url('http://abcd')
		'http://abcd'
		>>> absolute_url('abcd','http://google.com/stuff/file')
		'http://google.com/stuff/abcd'
		>>> absolute_url('abcd','http://google.com/stuff/folder/')
		'http://google.com/stuff/folder/abcd'
		>>> absolute_url('/abcd','http://google.com/stuff/file')
		'http://google.com/abcd'
	"""
	if re.match('[a-zA-Z]+://', url):
		return url
	
	if base is None:
		raise ValueError("No base given, and \"%s\" is a relative URL!" % url)
	if re.match('/', url):
		protocol, path = base.split('://',1)
		server = path.split('/',1)[0]
		return protocol + '://' + server + url
	if not base[-1] == '/':
		# base is not a directory - so grab everything before the last slash:
		base = url_dirname(base)
	return base + url

def get_filename(url):
	""" TODO: doctests """
	url = url.split('?',1)[0] # chomp query strings
	url = url.split('/')[-1]
	return urllib2.quote(url)

def unique_filename(output_filename, base_path=None):
	"""
	get the next filename for a pattern that doesn't already exist

		>>> base='/tmp/filetest/'
		>>> rm_rf(base)
		>>> unique_filename(base+'filename.x.txt')
		'/tmp/filetest/filename.x.txt'
		>>> touch_file(_)
		>>> unique_filename(base+'filename.x.txt')
		'/tmp/filetest/filename.x-2.txt'
		>>> touch_file(_)
		>>> touch_file('/tmp/filetest/filename.x-3.txt')
		
	use a base_path to specify a full path for file-checking purposes,
	but which isn't included in the return value
	
		>>> unique_filename('filename.x.txt', base)
		'filename.x-4.txt'
	"""
	i = 2
	base, ext = os.path.splitext(output_filename)
	while os.path.exists(os.path.join(base_path, output_filename) if base_path else output_filename):
		output_filename = "%s-%s%s" % (base, i, ext)
		i += 1
	return output_filename

import hashlib
def limit_filename(name, length):
	"""
	limit a filename to be at most `length` characters
	(for length > 16)

		>>> fl = limit_filename('aaaabbbbccccddddeeeex', 20)
		>>> len(fl)
		20
		>>> fl
		'aaaa5004c72298531f66'
	"""

	if len(name) <= length:
		return name[:]
	
	hash_size = 16
	return name[:length-hash_size] + hashlib.md5(name).hexdigest()[:hash_size]

import socket
def download_file(url, output_filename, base_path='', allow_overwrite=False):
	"""
	Download an arbitrary URL. If output_filename is given, contents are written a file that looks a lot like output_filename.
	If output_filename does not contain an extension matching the file's reported mime-type, such an extension will be added.
	If allow_overwrite is set to true, this function will overwrite any existing file at output_filename.
	Otherwise, it will find a unique filename to create using the pattern <base>-n.<ext> for n in 2 ... inf
	
	Files are only downloaded if their mime-type is "image/x" where x is in the image_extensions list.
	
	Returns: - The filename that contents were written to.
	         - None if the file was not downloaded
	"""
	# timeout in seconds
	socket.setdefaulttimeout(20)

	debug("peeking at url: %s" % (url,))
	dl = urllib2.urlopen(url)
	headers = dl.headers

	try:
		mime_type = headers.getmaintype().lower()
		if mime_type == 'image':
			filetype = headers.subtype
		else:
			debug("not an image type: %s" % (mime_type,))
			filetype = None
	except StandardError, e:
		debug("download error: %s" % (e,))
		filetype = None
	
	try:
		if int(headers['Content-Length']) < MIN_IMAGE_BYTES:
			debug("not downloading image - it's only %s bytes long" % (headers['Content-Length'],))
			dl.close()
			return None
	except StandardError: pass
	
	if filetype is None:
		filetype = output_filename.split('.')[-1].lower()
	
	if filetype not in image_extensions:
		debug("not downloading image of type: %s" % (filetype,))
		dl.close()
		return None
	
	output_filename = limit_filename(output_filename, 64)
	
	if not output_filename.lower().endswith('.' + filetype):
		output_filename += '.' + filetype
	
	if not allow_overwrite:
		output_filename = unique_filename(output_filename, base_path=base_path)

	debug("downloading file: %s" % (url,))
	contents = dl.read()
	debug("downloaded file: %s" % (url,))
	dl.close()

	full_path = os.path.join(base_path, output_filename) if base_path else output_filename
	out = open(full_path,'w')
	out.write(contents)
	return output_filename

if __name__ == '__main__':
	import doctest
	doctest.testmod()

########NEW FILE########
__FILENAME__ = proctl
# process control
import commands
import signal
import os

import app_globals
from misc import *

def get_pid_filename():
	return "%s/sync.pid" % (app_globals.OPTIONS['output_path'],)

def write_pid_file(filename):
	write_file(filename, str(os.getpid()))

def report_pid():
	none = 'None'
	try:
		pid = get_running_pid()
		if pid is None:
			print none
		else:
			print pid
	except StandardError, e:
		exception("Error getting running pid")
		print none

def get_pids_matching(pattern):
	status, output = commands.getstatusoutput("ps ux | grep -v grep | grep '%s' | awk '{print $2}'" % pattern) # classy!
	running_pids = []
	if output.endswith("Operation not permitted"):
		if(os.uname()[-1] == 'i386'):
			status, output = (0, '') # lets just pretend it worked, and everything is fine
		else:
			warning("Error fetching running pids: %s" % (output,))
			warning(" - This is known to happen on the iphone simulator.")
			warning(" - if you see it on a real device, please file a bug report")
	if status != 0:
		raise RuntimeError("could not execute pid-checking command. got status of %s, output:\n%s" % (status, output))
	
	running_pids = output.split()
	try:
		running_pids = [int(x) for x in running_pids if len(x) > 0]
	except ValueError, e:
		raise RuntimeError("one or more pids could not be converted to an integer: %r" % (running_pids,))
	return running_pids

def get_running_pid():
	"""
	@throws: IOError, ValueError, RuntimeError
	"""
	filename =  get_pid_filename()
	if not os.path.isfile(filename): return None
	
	try:
		pid = int(read_file(filename).strip())
	except (IOError, ValueError), e:
		exception("Couldn't load PID file at %s: %s" % (filename,e))
		raise
	
	if pid == os.getpid():
		# it's me! it must have been stale, and happened to be reused. we don't want to kill it
		return None
	
	running_pids = get_pids_matching('python.*GRiS')
	
	if pid in running_pids:
		return pid
	return None

def ensure_singleton_process():
	"""
	ensure only one sync process is ever running.
	if --aggressive is given as a flag, this process will kill the existing one
	otherwise, it will exit when there is already a process running
	"""
	aggressive = app_globals.OPTIONS['aggressive']
	pid = None
	try:
		pid = get_running_pid()
		debug("no pid file found at %s" % (filename,))
	except StandardError, e:
		pass

	if not aggressive:
		# check for gris.app as well
		native_pids = get_pids_matching('Applications/GRiS\.app/GRiS')
		if len(native_pids) > 0:
			pid = native_pids[0]
	
	if pid is not None:
		if not aggressive:
			error("There is already a sync process running, pid=%s" % (pid,))
			sys.exit(2)
		else:
			try:
				debug("killing PID %s " %(pid,))
				os.kill(pid, signal.SIGKILL)
			except OSError, e:
				msg = "couldn't kill pid %s - %s" % (pid,e)
				error(msg)
				sys.exit(2)

	# if we haven't exited by now, we're the new running pid!
	filename =  get_pid_filename()
	write_pid_file(filename)

########NEW FILE########
__FILENAME__ = proctl_test
import unittest
import commands
import signal

from lib.mock import Mock
import app_globals
import output
from misc import *
import test_helper

import proctl

class GetPidTest(unittest.TestCase):
	def setUp(self):
		self.filename = "%s/sync.pid" % (app_globals.OPTIONS['output_path'],)
		self._backup_getpid = proctl.get_running_pid
	
	def tearDown(self):
		proctl.get_running_pid = self._backup_getpid

	def _mock_command(self, response):
		commands.getstatusoutput = Mock()
		commands.getstatusoutput.return_value = response
		
	def mock_pid_file(self, file_pid = '1234', command_response = (0,'1234')):
		write_file(self.filename, file_pid)
		self._mock_command(command_response)

	def mock_pid_process(self, aggressive=False, pid=1234, file_pid = None, command_response = (0,'')):
		app_globals.OPTIONS['aggressive'] = aggressive
		proctl.get_running_pid = Mock()
		proctl.get_running_pid.return_value = pid

		if file_pid is None:
			file_pid = str(pid)
		
		write_file(self.filename, file_pid)
		self._mock_command(command_response)
		os.kill = Mock()

	def fail(self):
		raise RuntimeError
		
	def test_get_pid_should_raise_IOError_when_file_doesnt_exist(self):
		self.mock_pid_file()
		try:
			os.remove(self.filename)
		except: pass
		self.assertRaises(IOError, proctl.get_running_pid)

	def test_get_pid_should_raise_ValueError_when_file_is_not_an_integer(self):
		self.mock_pid_file(file_pid = '')
		self.assertRaises(ValueError, proctl.get_running_pid)

	def test_get_pid_when_file_is_an_integer_with_whitespace(self):
		self.mock_pid_file(file_pid = ' 1234 \n', command_response=(0,'1234'))
		self.assertEqual(1234, proctl.get_running_pid())

	def test_get_pid_when_pid_is_valid_and_running(self):
		self.mock_pid_file(file_pid='1234\n', command_response=(0,'1234'))
		self.assertEqual(1234, proctl.get_running_pid())
		self.assertEqual(commands.getstatusoutput.call_args, (("ps ux | grep -v grep | grep 'python.*GRiS' | awk '{print $2}'",),{}))

	def test_get_pid_should_return_none_when_pid_is_not_gris(self):
		self.mock_pid_file(file_pid='1234', command_response=(0,'3456'))
		self.assertEqual(None, proctl.get_running_pid())

	def test_get_pid_should_raise_when_running_pids_cannot_be_parsed(self):
		self.mock_pid_file(file_pid='1234', command_response=(0,'1234\nxyz'))
		self.assertRaises(RuntimeError, proctl.get_running_pid)

	def test_get_pid_should_raise_when_get_ps_command_fails(self):
		self.mock_pid_file(file_pid='1234', command_response=(1,'3456'))
		self.assertRaises(RuntimeError, proctl.get_running_pid)

	def test_get_pid_should_return_none_when_pid_is_self(self):
		self.mock_pid_file(file_pid=str(os.getpid()))
		self.assertEqual(None, proctl.get_running_pid())

class ReportProcessTest(GetPidTest):
	def setUp(self):
		super(self.__class__, self).setUp()
		print dir(output)
		self._stdout = sys.stdout
		sys.stdout = Mock()
	
	def tearDown(self):
		sys.stdout = self._stdout
		super(self.__class__, self).tearDown()

	def test_should_report_pid_if_there_is_a_running_process(self):
		self.mock_pid_process(pid=1234)
		proctl.report_pid()
		self.assertEqual(sys.stdout.write.call_args_list, [(('1234',), {}), (('\n',), {})])
		
	def test_should_print__none__if_there_is_no_pid_running(self):
		self.mock_pid_process(pid=None)
		proctl.report_pid()
		self.assertEqual(sys.stdout.write.call_args_list, [(('None',), {}), (('\n',), {})])
		
	def test_should_print__none__if_there_is_an_error(self):
		proctl.get_running_pid = self.fail
		proctl.report_pid()
		self.assertEqual(sys.stdout.write.call_args_list, [(('None',), {}), (('\n',), {})])

class SingularProcessTest(GetPidTest):
	
	# aggressive ensure_singleton_process
	def test_aggressive_singular_process_should_continue_when_kill_works(self):
		self.mock_pid_process(aggressive = True, pid=1234, file_pid = '1234')
		
		proctl.ensure_singleton_process()
		self.assertEqual(os.kill.call_args_list, [((1234, signal.SIGKILL),{})])
		self.assertEqual(read_file(self.filename), str(os.getpid()))
	
	def test_aggressive_singular_process_should_exit_when_kill_fails(self):
		self.mock_pid_process(aggressive = True, pid=1234, command_response=(0,'567\n1234\n8910'))
		def raise_(error_cls, msg):
			raise OSError, msg
		os.kill = Mock(side_effect = lambda: raise_(OSError, '[Errno 3] No such process'))
		
		self.assertRaises(SystemExit, proctl.ensure_singleton_process)
		self.assertEqual(os.kill.call_args_list, [((1234, signal.SIGKILL),{})])
		self.assertEqual(read_file(self.filename), '1234') # contents should be unchanged
		
	def test_aggressive_singular_process_should_write_file_when_running_pids_raises(self):
		self.mock_pid_process(aggressive = True)
		proctl.get_running_pid = self.fail
		proctl.ensure_singleton_process()
		self.assertFalse(os.kill.called)
		self.assertEqual(read_file(self.filename), str(os.getpid()))
		
	def test_aggressive_singular_process_should_write_pid_file_when_running_pids_returns_none(self):
		self.mock_pid_process(aggressive = True, pid=None)
		proctl.ensure_singleton_process()
		self.assertFalse(os.kill.called)
		self.assertEqual(read_file(self.filename), str(os.getpid()))

	# submissive ensure_singleton_process
	def test_submissive_singular_process_when_pid_is_valid(self):
		self.mock_pid_process(aggressive = False, pid=1234)

		self.assertRaises(SystemExit, proctl.ensure_singleton_process)
		
		self.assertFalse(os.kill.called)
		self.assertEqual(read_file(self.filename), '1234') # file should be unchanged

	def test_submissive_should_not_write_pid_file_when_running_pid_raises(self):
		self.mock_pid_process(aggressive = False)
		self.mock_pid_file(file_pid='1234')
		proctl.get_running_pid = self.fail
		self.assertRaises(SystemExit, proctl.ensure_singleton_process)
		self.assertEqual(read_file(self.filename), '1234')


########NEW FILE########
__FILENAME__ = reader
from misc import *
from output import *
import app_globals
from lib.GoogleReader import GoogleReader, CONST
import os

class ReaderError(StandardError):
	pass

class Reader:
	def __init__(self, user=None, password=None):
		if app_globals.OPTIONS['test']:
			from lib.mock import Mock
			warning("using a mock google reader object")
			self.gr = Mock()
		else:
			self.gr = GoogleReader()
			self.login(user, password)

		self._tag_list = None

	def login(self, user=None, password=None):
		if user is None:
			user = app_globals.OPTIONS['user']
		if password is None:
			password = app_globals.OPTIONS['password']
		self.gr.identify(user, password)
		try:
			if not self.gr.login():
				raise RuntimeError("Login failed")
		except StandardError, e:
			error("error logging in: %s" % (e,))
			raise RuntimeError("Login failed (check your connection?)")
		
	def get_tag_list(self):
		if self._tag_list is None:
			tag_list = self.gr.get_tag_list()['tags']
			self._tag_list = [tag['id'].split('/')[-1] for tag in tag_list if '/label/' in tag['id']]
		return self._tag_list
	tag_list = property(get_tag_list)
		
	def validate_tag_list(self, user_tags = None, strict=True):
		"""
		Raise an error if any tag (in config) does not exist in your google account
		"""
		if user_tags is None:
			user_tags = app_globals.OPTIONS['tag_list']
		valid_tags = []
		for utag in user_tags:
			if utag in self.tag_list:
				valid_tags.append(utag)
			elif strict:
				print "Valid tags are: %s" %(self.tag_list,)
				raise ValueError("No such tag: %r" % (utag,))
		return valid_tags

	def save_tag_list(self):
		write_file_lines(os.path.join(app_globals.OPTIONS['output_path'], 'tag_list'), self.tag_list)

	def get_tag_feed(self, tag = None, count=None, oldest_first = True):
		if tag is not None:
			tag = CONST.ATOM_PREFIXE_LABEL + tag
		kwargs = {'exclude_target': CONST.ATOM_STATE_READ}
		if oldest_first:
			kwargs['order'] = CONST.ORDER_REVERSE

		if count is None:
			count = app_globals.OPTIONS['num_items']

		return self.gr.get_feed(None, tag, count=count, **kwargs)
		
	# pass-through methods
	def passthrough(f):
		def pass_func(self, *args, **kwargs):
			return getattr(self.gr, f.__name__)(*args, **kwargs)
		return pass_func
	
	def passthrough_and_check(f):
		def pass_func(self, *args, **kwargs):
			result = getattr(self.gr, f.__name__)(*args, **kwargs)
			if result != 'OK':
				raise ReaderError("Result (%s) is not 'OK'" % (result,))
		pass_func.__name__ = f.__name__
		return pass_func
	
	@passthrough_and_check
	def set_read(): pass

	@passthrough_and_check
	def set_unread(): pass
	
	@passthrough_and_check
	def add_star(): pass
	
	@passthrough_and_check
	def del_star(): pass
	
	@passthrough_and_check
	def add_public(): pass
	
	@passthrough_and_check
	def del_public(): pass
	
	@passthrough
	def get_feed(): pass

########NEW FILE########
__FILENAME__ = reader_test
# the tested module
from reader import *
from output import *
import os

# test helpers
import test_helper
from lib.mock import Mock
import pickle
from StringIO import StringIO
from lib.OpenStruct import OpenStruct
import unittest
import config

def mock_tag_list(reader, tag_list):
	reader.gr.get_tag_list = Mock()
	reader.gr.get_tag_list.return_value = {'tags':[{'id': tag_value} for tag_value in tag_list]}

class ReaderTest(unittest.TestCase):
	def setUp(self):
		self.output_folder = test_helper.init_output_folder()
		assert self.output_folder.startswith('/tmp')
		self.reader = Reader()
	
	def tearDown(self):
		assert self.output_folder.startswith('/tmp')
#		rm_rf(self.output_folder)
		
	def test_saving_unicode_in_tags(self):
		mock_tag_list(self.reader, [u'com.google/label/caf\xe9'])
		self.reader.save_tag_list()
		self.assertEqual(read_file_lines(os.path.join(self.output_folder, 'tag_list')), [u'caf\xe9\n'])
	
	def test_comparing_unicode_tags(self):
		config.parse_options(['--tag=caf\xc3\xa9']) # cafe in utf-8
		mock_tag_list(self.reader, [u'com.google/label/caf\xe9'])
		self.assertEqual(app_globals.OPTIONS['tag_list'], [u'caf\xe9'])
		self.reader.validate_tag_list()

	def test_saving_special_characters_in_tags(self):
		tag_name = 'com.google/label/and\\or\'"!@#$%^&*()_+'
		mock_tag_list(self.reader, [tag_name])
		self.reader.save_tag_list()
		print "tag list is: %s" % (read_file_lines(os.path.join(self.output_folder, 'tag_list')),)
		self.assertEqual(read_file_lines(os.path.join(self.output_folder, 'tag_list')), ['and\\or\'"!@#$%^&*()_+\n'])
		
	def test_should_ignore_tags_without__label_(self):
		"""should ignore tags without '/label/'"""
		tag_name = 'not a label'
		mock_tag_list(self.reader, [tag_name])
		self.assertEqual(self.reader.tag_list, [])
		
	def test_should_pass_through_get_feed(self):
		self.reader.get_feed(1, 2, 3, x=5)
		self.assertTrue( ('get_feed', (1,2,3), {'x':5}) in self.reader.gr.method_calls )
	
	def test_get_tag_feed_should_get_all_items(self):
		self.reader.get_tag_feed()
		self.assertTrue(
			('get_feed',
				(None, None),
				{'count': app_globals.OPTIONS['num_items'], 'order':CONST.ORDER_REVERSE, 'exclude_target': CONST.ATOM_STATE_READ})
			in self.reader.gr.method_calls )
	
	def test_get_tag_feed_should_get_single_tag(self):
		self.reader.get_tag_feed('blah')
		print self.reader.gr.method_calls
		self.assertTrue(
			('get_feed',
				(None, CONST.ATOM_PREFIXE_LABEL + 'blah'),
				{'count': app_globals.OPTIONS['num_items'], 'order':CONST.ORDER_REVERSE, 'exclude_target': CONST.ATOM_STATE_READ})
			in self.reader.gr.method_calls )

	def test_get_tag_feed_should_support_newest_first(self):
		self.reader.get_tag_feed(oldest_first = False)
		self.assertTrue(
			('get_feed',
				(None, None),
				{'count': app_globals.OPTIONS['num_items'], 'exclude_target': CONST.ATOM_STATE_READ})
			in self.reader.gr.method_calls )
########NEW FILE########
__FILENAME__ = template
from misc import *
from output import *
import app_globals
import re

import pdb

def update(obj, input_filename, output_filename = None, restrict_to=None):
	if output_filename is None:
		output_filename = input_filename
	_process(obj, input_filename, output_filename, restrict_to)

def update_template(template_filename, input_filename, output_filename=None):
	"""
	update the output of a previous template to a new template version
	"""
	if output_filename is None:
		output_filename = input_filename
	obj = _extract_templated_values(input_filename)
	_process(obj, template_filename, output_filename, None)
	
def create(obj, input_filename, output_filename = None, restrict_to=None):
	if output_filename is None:
		outut_filename = input_filename + ".html"
	_process(obj, input_filename, output_filename, restrict_to)

def get_str(obj):
	"""
	Get a string value from an arbitrary object.
	If it's callable, try to call it. If that fails, just convert it to a string.
	"""
	if obj is None:
		return ""
	try:
		res = str(obj())
	except TypeError:
 		res = str(obj)
	return res

def process_string(subject_str, obj, restrict_to = None):
	r"""
	Replaces {variable} substitutions that are within HTML comments.
	The replacement includes html-comment markers so that the value can be replaced / updated if desired.

	>>> process_string("<!--{content}-->", {'content':"la la la"})
	'<!--{content=}-->la la la<!--{=content}-->'

	>>> process_string('<!--{content=}-->previous\ncontent<!--{=content}-->', {'content':"new value"})
	'<!--{content=}-->new value<!--{=content}-->'

	# the restrict_to argument limits the set of keys that will be interpreted:
	>>> process_string("<!--{content}-->", {'content':"new value"}, ['other_key'])
	'<!--{content}-->'
	>>>
	"""
	# do expanded first, otherwise you'll expand it and match it again with expanded_re!
	for matcher_func in (_expanded_regex, _unexpanded_regex):
		matcher = matcher_func() # evaluate it
		matches = matcher.finditer(subject_str)
		for match in matches:
			object_property = match.groupdict()['tag']
			debug("object property: " + object_property)
			if (restrict_to is None or object_property in restrict_to):
				attr = get_attribute(obj, object_property)
				if attr is not None:
					# do the replacement!
					debug("substituting property: " + object_property)
					replacement_matcher = matcher_func(object_property)
					subject_str = replacement_matcher.sub('<!--{\g<tag>=}-->' + get_str(attr) + '<!--{=\g<tag>}-->', subject_str)
				else:
					debug("object does not respond to " + object_property)
				
	return subject_str

def extract_values(contents):
	"""
	grab a hash of values that were used to create the given
	output string (from a previous template render)
	
	>>> extract_values('fkdjlf<!--{something=}-->Value!<!--{=something}-->dsds')
	{'something': 'Value!'}
	"""
	obj = {}
	matches = _expanded_regex().finditer(contents)
	for match in matches:
		key = match.groupdict()['tag']
		content = match.groupdict()['content']
		obj[key] = content
	return obj


default_tagex = '[a-zA-Z0-9_]+'
def _unexpanded_regex(tagex = None):
	global default_tagex
	if tagex is None:
		tagex = default_tagex
	return re.compile('<!--\{(?P<tag>' + tagex + ')\}-->')

def _expanded_regex(tagex = None):
	global default_tagex
	if tagex is None:
		tagex = default_tagex
	return re.compile('<!--\{(?P<tag>' + tagex + ')=\}-->(?P<content>.*?)<!--\{=(?P=tag)\}-->', re.DOTALL) # the dot can match newlines


####################################################################################
# internal methods only below - use the above methods to interact with this module #
####################################################################################

def _process(obj, input_filename, output_filename, restrict_to):
	infile = file(input_filename, 'r')
	contents = infile.read()
	contents = process_string(contents, obj, restrict_to)
	infile.close()
	outfile = file(output_filename, 'w')
	outfile.write(contents)

def _extract_templated_values(input_filename):
	infile = file(input_filename, 'r')
	contents = infile.read()
	obj = extract_values(contents)
	infile.close()
	return obj

def get_attribute(obj, attr):
	"""
	Much like the built-in getattr, except:
	 - it returns None on failure
	 - it tries dictionary lookups if no attribute is found
	
	>>> class Something:
	... 	def __init__(self):
	... 		self.internal_var = 'moop'

	>>> get_attribute(Something(), 'internal_var')
	'moop'

	>>> get_attribute({'test_var':'test_val'}, 'test_var')
	'test_val'
	"""
	
	ret = None
	try:
		ret = getattr(obj, attr)
	except AttributeError:
		try:
			ret = obj[attr]
		except (TypeError, KeyError):
			pass
	return ret

########NEW FILE########
__FILENAME__ = test_helper
# test helpers
from lib.mock import Mock
import pickle
from StringIO import StringIO
from lib.OpenStruct import OpenStruct
import unittest
import config
from misc import *
from reader import Reader
import app_globals

def init_output_folder():
	output_folder = '/tmp/GRiS/test_entries'
	config.parse_options(['--test','--num-items=3','--logdir=/tmp/GRiS/logs', '--output-path=%s' % output_folder])

	assert app_globals.OPTIONS['output_path'] == output_folder
	ensure_dir_exists(output_folder)
	app_globals.READER = Reader()
	assert type(app_globals.READER.gr) == Mock

	return output_folder

def google_ids(item_list):
	return [x.google_id for x in sorted(item_list)]

def fake_item(**kwargs):
	args = {
		'google_id' : 'sample_id',
		'title' : 'title',
		'url' : 'http://example.com/post/1',
		'original_id': 'http://www.exampleblog.com/post/1',
		'is_read' : False,
		'is_dirty' : False,
		'is_starred' : False,
		'feed_name' : 'feedname',
		'tag_name' : 'tagname',
		'date' : '20080812140000',
		'content' : '<h1>content!</h1>',
		'had_errors' : False,
		'is_stale': False,
		'is_shared': False,
		'is_pagefeed':False,
		'instapaper_url': '',
		}
	args.update(kwargs)
	return OpenStruct(**args)


################ generic test helpers ################
import sys

def pending(function_or_reason):
	def wrap_func(func, reason = None):
		reason_str = "" if reason is None else " (%s)" % reason
		def actually_call_it(*args, **kwargs):
			fn_name = func.__name__
			try:
				func(*args, **kwargs)
				print >> sys.stderr, "%s%s PASSED unexpectedly " % (fn_name, reason_str),
			except:
				print >> sys.stderr, "[[[ PENDING ]]]%s ... " % (reason_str,),
		actually_call_it.__name__ = func.__name__
		return actually_call_it
	
	if callable(function_or_reason):
		# we're decorating a function
		return wrap_func(function_or_reason)
	else:
		# we've been given a description - return a decorator
		def decorator(func):
			return wrap_func(func, function_or_reason)
		return decorator

########NEW FILE########
__FILENAME__ = thread_pool
import thread, time, threading
from output import *

def ping():
	try:
		threading.currentThread().ping()
	except AttributeError, e:
		pass

# threaded decorator
# relies on the decorated method's instance having an initialised _lock variable
def locking(process):
	def fn(self, *args, **kwargs):
		self._lock.acquire()
		try:
			ret = process(self, *args, **kwargs)
		finally:
			self._lock.release()
		return ret
	fn.__name__ = process.__name__
	return fn

class ThreadAction(threading.Thread):
	def __init__(self, func, on_error = None, on_success = None, name=None, *args, **kwargs):
		super(self.__class__, self).__init__(group=None, target=None, name=name, args=(), kwargs={})
		self.args = args
		self.kwargs = kwargs
		self.func = func
		self.on_error = on_error
		self.on_success = on_success
		self.name = name
		self._killed = False
		self._lock = thread.allocate_lock()
		self.start_time = time.time()

	def kill(self):
		self._killed = True
	
	def ping(self):
		self.start_time = time.time()
	
	def run(self):
		if self._killed: return
		if self.name is not None:
			threading.currentThread().setName(self.name)
		
		try:
			self.func(*self.args, **self.kwargs)
		except StandardError, e:
			error("thread error! %s " % e)
			if self._killed: return
			if self.on_error is not None:
				self.on_error(e)
				return
			else:
				raise
			
		if self._killed: return
		if self.on_success is not None:
			self.on_success()
	

class ThreadPool:
	_max_count = 6
	_threads = []
	_global_count = 0
	_action_buffer = []
	
	def __init__(self):
		self._lock = thread.allocate_lock()

	def _get_count(self):
		return len(self._threads)
	_count = property(_get_count)
	
	def _sleep(self, seconds = 1):
		self._lock.release()
		time.sleep(seconds)
		self._lock.acquire()
	
	def _wait_for_any_thread_to_finish(self):
		initial_count = self._count
		global_count = self._global_count
		silence_threshold = 60
		sleeps = 0
		
		initial_threads = list(self._threads) # take a copy
		
		if self._count == 0:
			debug("no threads running!")
			return

		def threads_unchanged():
			if self._count != initial_count:
				return False
			return all(a is b for a,b in zip(self._threads, initial_threads))
		
		def partition_threads():
			now = time.time()
			old = []
			new = []
			for th in self._threads:
				if th.start_time + silence_threshold > now:
					new.append(th)
				else:
					old.append(th)
			return (old, new)
		
		while threads_unchanged():
			old_threads, new_threads = partition_threads()
			if len(old_threads) > 0:
				error("%s threads have been running over %s seconds" % (len(old_threads), silence_threshold))
				for thread_ in old_threads:
					info(" - killing thread: %s" % (thread_.name,))
					thread_.kill()
				error("%s threads killed" % (len(old_threads),))
				self._threads = new_threads
				break

			self._sleep(1)
			sleeps += 1

	
	@locking
	def spawn(self, function,
		name = None,
		on_success = None,
		on_error = None,
		*args, **kwargs):
		while self._count >= self._max_count:
			self._wait_for_any_thread_to_finish()

		debug("there are currently %s threads running" % self._count)
		self._global_count += 1
		thread_id = "%s.%s" % (self._global_count, ascii(name)) if name is not None else "thread %s" % (self._global_count,)
		action = ThreadAction(
			function,
			name = thread_id,
			*args, **kwargs)
		action.on_error = lambda e: self._thread_error(action, on_error, e)
		action.on_success = lambda: self._thread_finished(action, on_success)
		self._threads.append(action)
		debug("starting new thread")
		action.start()
	
	@locking
	def _thread_error(self, thread, callback, e):
		self._locked_thread_finished(thread)
		if callback is None:
			exception("thread raised an exception and ended: %s" % (e,))
		else:
			callback(e)
		
	@locking
	def _thread_finished(self, thread, next_action):
		self._action_buffer.append(next_action)
		self._locked_thread_finished(thread)
	
	def _locked_thread_finished(self, thread):
		self._threads.remove(thread)
		debug("thread finished - there remain %s threads" % (self._count,))
	
	@locking
	def collect(self):
		self._collect()
	
	@locking
	def collect_all(self):
		debug("waiting for %s threads to finish" % self._count)
		while self._count > 0:
			self._wait_for_any_thread_to_finish()
			
		self._collect()

	# non-locking - for internal use only
	def _collect(self):
		for next_action in self._action_buffer:
			if next_action is not None:
				debug("calling action: %s" % (next_action,))
				next_action()
		self._action_buffer = []

########NEW FILE########
__FILENAME__ = thread_pool_test
import time

# the tested module
from thread_pool import *
import thread_pool

# test helpers
import test_helper
import lib
from mocktest import *
from lib.mock import Mock
from StringIO import StringIO
from lib.OpenStruct import OpenStruct
import unittest

class ThreadPoolTest(TestCase):

	def setUp(self):
		self.pool = ThreadPool()

	def tearDown(self):
		pass
		
	def assert_uses_a_lock_for(self, func):
		lock = mock_on(self.pool)._lock
		def check_locked():
			self.assertTrue(lock.child('acquire').called)
		lock.child('release').action = check_locked
		func()
		self.assertTrue(lock.child('release').called)
		self.assertTrue(lock.child('acquire').called)
	
	def sleep(self, secs = 1):
		time.sleep(secs)
	
	def raise_(self, ex):
		raise ex
		
	def action(self, f = lambda: 1):
		self.action_happened = False
		def do_action():
			print "action started"
			try:
				f()
			finally:
				self.action_happened = True
		return do_action
		
	
	def wait_for_action(self):
		while not self.action_happened:
			print "waiting..."
			time.sleep(0.1)
		
	# -- actual tests --

	@ignore
	def test_should_use_lock_for_spawn(self):
		self.assert_uses_a_lock_for(lambda: self.pool.spawn(self.sleep))

	@ignore
	def test_should_use_lock_for_collect(self):
		self.assert_uses_a_lock_for(lambda: self.pool.collect())
		
	@ignore
	def test_should_use_lock_for_collect_all(self):
		self.assert_uses_a_lock_for(lambda: self.pool.collect_all())
		
	def test_sucessful_callback_on_next_collect(self):
		success = mock()
		self.pool.spawn(self.action(), on_success = success.raw)
		self.wait_for_action()
		self.assertFalse(success.called)
		self.pool.collect()
		self.assertTrue(success.called.once())

	def test_standard_error_callback(self):
		success = mock().named('success')
		fail = mock().named('fail')
		
		self.pool.spawn(self.action(lambda: self.raise_(ValueError)), on_success = success.raw, on_error = fail.raw)
		self.wait_for_action()
		self.pool.collect()
		
		self.assertTrue(fail.called.once())
		self.assertTrue(success.called.no_times())

	def test_should_log_standard_error_when_no_error_callback_given(self):
		success = mock().named('success')
		self.error_logged = False
		def errd(e):
			self.error_logged = True

		mock_on(thread_pool).exception.with_action(lambda desc, e: errd(e)).is_expected.once()
		
		self.pool.spawn(self.action(lambda: self.raise_(ValueError)), on_success = success.raw)
		self.wait_for_action()
		self.pool.collect()
		
		self.assertTrue(success.called.no_times())
	
	def test_should_not_catch_nonstandard_errors(self):
		success = mock().named('success')
		fail = mock().named('fail')
		
		class Dummy(Exception):
			pass

		self.pool.spawn(self.action(lambda: self.raise_(Dummy)), on_success = success.raw, on_error = fail.raw)
		self.wait_for_action()
		self.pool.collect()
		
		self.assertTrue(fail.called.no_times())
		self.assertTrue(success.called.no_times())
	
	@ignore
	def test_kill_of_old_threads_when_max_threads_reached(self):
		pass
	
	@ignore
	def test_ping_prolongs_kill(self):
		pass
	
	@ignore
	def test_collect_all_waits_for_all_threads(self):
		pass
	
	
	
	

########NEW FILE########
__FILENAME__ = url_save
INSTAPAPER = 'instapaper'
PAGEFEED = 'pagefeed'
OPTS_KEY = 'url_save_service'

import app_globals
from output import debug

def get_active_service():
	service_name = app_globals.OPTIONS[OPTS_KEY]
	if service_name == PAGEFEED:
		debug("URL SAVE: pagefeed mode")
		from pagefeed import PageFeed
		return PageFeed()
	elif service_name == INSTAPAPER:
		debug("URL SAVE: instapaper mode")
		from instapaper import Ipaper
		return Ipaper()
	else:
		raise ValueError("%s is %s (expected %s)" % (
			OPTS_KEY, service_name,
			' or '.join((INSTAPAPER, PAGEFEED))))


########NEW FILE########
