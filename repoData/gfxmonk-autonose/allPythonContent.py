__FILENAME__ = runner
#!/usr/bin/env python

import nose
import sys
import time
import logging
import logging.config
import traceback
from optparse import OptionParser
import paragram as pg

import scanner
import watcher
from shared.test_result import ResultEvent

log = logging.getLogger('runner')
debug = log.debug
info = log.info
logging.getLogger('paragram').setLevel(logging.WARN)

class NullHandler(logging.Handler):
	def emit(self, record):
		pass

class MultiOutputQueue(object):
	def __init__(self, *output_queues):
		self.output_queues = output_queues
	
	def put(self, o):
		[queue.put(o) for queue in self.output_queues]

class Main(object):
	def __init__(self):
		parser = OptionParser()
		# run control
		parser.add_option('--clear', action='store_true', default=False, help='reset all dependency information')
		parser.add_option('--once', action='store_true', default=False, help='run all outdated tests and then exit (uses --console)')
		parser.add_option('--all', action='store_true', default=False, help='always run all tests - no filtering')
		parser.add_option('--dump-state', action='store_true', default=False, help='just dump the saved dependency state')
		
		# logging
		parser.add_option('--debug', action="store_true", default=False, help='show debug output')
		parser.add_option('--info', action="store_true", default=False, help='show more info about what files have changed')
		parser.add_option('--log-only', action="store", default=None, help='restrict logging to the given module(s)')
		
		# UI
		parser.add_option('--console', action="store_true", default=False, help='use the console interface (no GUI)')

		# nose options
		parser.add_option('--config', default=None, help='nosetests config file')
		parser.add_option('-x', '--nose-arg', default=[], dest='nose_args', action="append", help='additional nose arg (use multiple times to add many arguments)') #TODO: --direct -> run only files that have changed, and their direct imports
		opts, args = parser.parse_args()
		if args:
			parser.print_help()
			sys.exit(2)
		self.opts = opts
	
	def run(self):
		self.init_logging()
		self.init_nose_args()
		if self.opts.clear:
			scanner.reset()
		state_manager = scanner.load()
		if self.opts.dump_state:
			print repr(state_manager.state)
			return
		self.init_ui()
		try:
			self.run_forever(state_manager)
		except Exception, e:
			pg.main.terminate(e)
			raise
	
	def monitor_state_changes(self, proc, state_manager):
		iterator = state_manager.state_changes()

		@proc.receive('next', pg.Process)
		def next(msg, caller):
			iterator.next()
			caller.send('state_changed')

	def run_when_state_changes(self, proc, state_manager, state_monitor_proc):
		@proc.receive('state_changed')
		def state_changed(msg):
			self.run_with_state(state_manager, proc)
			state_monitor_proc.send('next', proc)

		@proc.receive('focus_on', str)
		def focus_on(msg, test_id):
			self.test_id = test_id or None
			self.run_with_state(state_manager, proc)

		@proc.receive('start')
		def start(msg):
			state_monitor_proc.send('next', proc)

	def run_forever(self, state_manager):
		self.state_listener = pg.main.spawn_link(
			target=self.state_saver,
			name='state-saver',
			args=(state_manager.state,),
			kind=pg.ThreadProcess)

		self.run_with_state(state_manager, pg.main)
		if self.opts.once:
			pg.main.terminate()
			return

		# now set up processes to run forever
		monitor_state_changes = pg.main.spawn_link(
			target=self.monitor_state_changes,
			name='monitor-state-changes',
			args=(state_manager,),
			kind=pg.ThreadProcess)

		run_triggerer = pg.main.spawn_link(
			target=self.run_when_state_changes,
			name='run-on-state-change',
			args=(state_manager, monitor_state_changes),
			kind=pg.ThreadProcess)

		self.ui.send('use_runner', run_triggerer)
		run_triggerer.send('start')

	def init_logging(self):
		format = '[%(levelname)s] %(name)s: %(message)s'
		lvl = logging.WARNING
		if self.opts.debug:
			lvl = logging.DEBUG
		elif self.opts.info:
			lvl = logging.INFO
		logging.basicConfig(level=lvl, format=format)

		if self.opts.log_only:
			for name in self.opts.log_only.split(","):
				level = logging.DEBUG
				if ":" in name:
					name, level = name.split(":")
					level = getattr(logging, level)
				logging.getLogger(name).setLevel(level)
				logging.info("set extended logging on logger %s" % (name,))
		# since watcher runs in the nose process, it needs to be careful when logging...
		watcher.actual_log_level = logging.getLogger('watcher').level

	def init_nose_args(self):
		self.nose_args = ['nosetests','--exe']
		if self.opts.config is not None:
			self.nose_args.append('--config=%s' % (self.opts.config))
		self.nose_args.extend(self.opts.nose_args)
		self.test_id = None

	def init_ui(self):
		self.ui = None
		def basic():
			from ui.basic import Basic
			self.ui = pg.main.spawn_link(target=Basic, kind=pg.ThreadProcess, name="basic UI")

		if self.opts.console or self.opts.once:
			return basic()

		from ui.platform import default_app
		try:
			App = default_app()
			from ui.shared import Main as UIMain
			self.ui = pg.main.spawn_link(target=UIMain, args=(App,), name="UI", kind=pg.OSProcess)
		except StandardError:
			traceback.print_exc()
			print "UI load failed - falling back to basic console"
			print '-'*40
			time.sleep(3)
			return basic()
	
	def state_saver(self, proc, state):
		proc.receive[watcher.Completion] = lambda completion: scanner.save(state)
		proc.receive[ResultEvent] = lambda event: event.affect_state(state)

	def run_with_state(self, state_manager, proc):
		info("running with %s affected and %s bad files... (%s files total)" % (len(state_manager.affected), len(state_manager.bad), len(state_manager.state)))
		debug("state is: %r" % (state_manager.state,))
		args = self.nose_args[:]
		if self.test_id:
			args.append(self.test_id)
			# when only running a single test, we can't reliably update the state records
			listeners = [self.ui]
		else:
			listeners = [self.ui, self.state_listener]

		debug("args are: %r" % (args,))
		watcher_plugin = watcher.Watcher(state_manager, *listeners)
		if self.opts.all:
			watcher_plugin.run_all()

		def run_tests(proc):
			nose.run(argv=args, addplugins=[watcher_plugin])
			proc.terminate()

		runner = proc.spawn(target=run_tests, name="nose test runner", kind=pg.OSProcess)
		runner.wait()
		if runner.error:
			proc.terminate(runner.error)
		#pg.graph()

def main():
	#pg.enable_graphs()
	try:
		Main().run()
		sys.exit(0)
	except KeyboardInterrupt:
		sys.exit(1)

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = scanner
import os
import sys
import logging
import pickle

log = logging.getLogger(__name__)
debug = log.debug

from shared import const
from shared.state import FileSystemState, FileSystemStateManager

def pickle_path():
	return os.path.join(const.cwd, const.picklefile_name)

def open_file(path, *a):
	return open(path, *a)


def load():
	path = pickle_path()
	ret = None
	loaded = False
	tried_deleting = False
	picklefile = None
	try:
		while not loaded:
			picklefile = open_file(path)
			logging.info("loading saved state from %s" % (path,))
			try:
				ret = pickle.load(picklefile)
				ret.check()
				loaded = True
				debug("loaded: %s" % (picklefile.name,))
			except StandardError, e:
				errmsg = "Failed loading \"%s\". (Error was %s: \"%s\")" % (const.picklefile_name, type(e).__name__, e.message)
				log.error(errmsg, exc_info=1)
				print >> sys.stderr, errmsg
				picklefile.close()
				if tried_deleting:
					sys.exit(1)
				print >> sys.stderr, "Deleting picklefile and trying again..."
				tried_deleting = True
				reset()
	except IOError:
		debug("IOError:", exc_info=sys.exc_info())
		ret = FileSystemState()
	manager = FileSystemStateManager(ret)
	manager.update()
	return manager

def save(state):
	assert isinstance(state, FileSystemState)
	picklefile = open_file(pickle_path(), 'w')
	pickle.dump(state, picklefile)
	picklefile.close()
	debug("saved dependencies file: %s" % (picklefile.name))
	debug("saved dependencies are: %r" % (state))

def reset():
	path = pickle_path()
	if os.path.exists(path):
		log.info("removing %s" % (path,))
		os.remove(path)
	else:
		log.info("No such file to remove: %s" % (path,))

########NEW FILE########
__FILENAME__ = const
import os

picklefile_name = '.autonose-depends.pickle'
cwd = os.path.realpath(os.getcwd())

########NEW FILE########
__FILENAME__ = file_state
import os
import file_util
import logging
import snakefood.find
from test_result import TestResultSet
log = logging.getLogger(__name__)

class FileState(object):
	def __init__(self, path):
		self._test_results = None
		self.path = path
		self.update()
	
	def __str__(self):
		return "%s@%s" % (self.path, self.modtime)

	def __repr__(self):
		return "<%s: %s, test_results:%r (depends on %s files)>" % (self.__class__.__name__, self, self.test_results, len(self.dependencies))

	def _get_modtime(self):
		return os.stat(file_util.absolute(self.path)).st_mtime
	
	def stale(self):
		return self._get_modtime() != self.modtime
	
	def update(self):
		self.modtime = self._get_modtime()
		self.dependencies = self._get_dependencies()
		
	def _get_test_results(self):
		if self._test_results is None:
			self._test_results = TestResultSet()
		return self._test_results

	def _set_test_results(self, test_results):
		log.debug("added test_results %r to file state %s" % (test_results, self.path))
		self._test_results = test_results
	test_results = property(_get_test_results, _set_test_results)
	
	def ok(self):
		return False if self._test_results is None else self._test_results.ok()
	
	def _get_dependencies(self):
		paths = self._get_direct_dependency_paths(self.path)
		rel_paths = filter(lambda x: x is not None, map(lambda p: file_util.relative(p, None), paths))
		log.debug("rel_paths: %s" % (rel_paths))
		return rel_paths

	@staticmethod
	def _get_direct_dependency_paths(file_):
		log.debug("fetching dependencies for %s" % (file_,))
		files, errors = snakefood.find.find_dependencies(file_, verbose=False, process_pragmas=False)
		if len(errors) > 0:
			map(log.debug, errors)
		log.debug("found dependant files: %s" % (files,))
		return files


########NEW FILE########
__FILENAME__ = file_util
import os
from const import cwd

class FileOutsideCurrentRoot(RuntimeError):
	pass

_default = object()
def relative(path, default=_default):
	realpath = os.path.realpath(path)
	if realpath.startswith(cwd):
		return realpath[len(cwd)+1:]
	if default is not _default:
		return default
	raise FileOutsideCurrentRoot(realpath)

def source(path):
	return path[:-1] if ext(path) == 'pyc' else path

def absolute(path):
	if os.path.isabs(path):
		return path
	return os.path.join(cwd, path)

def ext(path):
	return path.rsplit('.',1)[-1].lower()

def is_pyfile(path):
	return '.' in path and ext(path) == 'py'



########NEW FILE########
__FILENAME__ = state
import os
import sys
import logging
import threading
import Queue as queue

from file_state import FileState
import file_util
from const import cwd as base

log = logging.getLogger(__name__)
debug = log.debug
info = logging.getLogger(__name__ + '.summary').info

# TODO: shut up about unfound imports
#logging.getLogger(snakefood.find.logname).setLevel(logging.ERROR)

def union(*sets):
	return reduce(lambda set_, new: set_.union(new), sets)

VERSION = 1

class FileSystemState(object):
	def __init__(self, version=VERSION, known_paths=None):
		self.version = version
		self.known_paths = known_paths or {}
		self._zombies = {}
		self.lock = threading.RLock()

	def check(self):
		assert self.version == VERSION
	
	def __iter__(self):
		return iter(list(self.known_paths.keys()))

	def __len__(self):
		return len(self.known_paths)
	
	def items(self):
		return self.known_paths.items()

	def values(self):
		return self.known_paths.values()

	def __setitem__(self, item, value):
		with self.lock:
			log.debug("ALTERING path: %s" % (item,))
			assert isinstance(item, str)
			assert isinstance(value, FileState)
			self.known_paths[item] = value

	def get_or_create(self, path):
		with self.lock:
			try:
				return self[path]
			except KeyError:
				self[path] = FileState(path)
				return self[path]

	def __getitem__(self, item):
		with self.lock:
			return self.known_paths[item]

	def __delitem__(self, item):
		with self.lock:
			log.debug("DELETING known path: %s" % (item,))
			self._zombies[item] = self.known_paths[item]
			del self.known_paths[item]
	
	def resurrect(self, item):
		with self.lock:
			try:
				self.known_paths[item] = self._zombies[item]
				del self._zombies[item]
			except KeyError:
				return False
			return True

	
	def __repr__(self): return "\n" + "\n".join(map(repr, self.values()))
	def copy(self):
		cls, args = self.__reduce__()
		return cls(*args)

	def __reduce__(self):
		return (FileSystemState, (self.version, self.known_paths.copy()))


from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog import events
class QueueHandler(FileSystemEventHandler):
	def __init__(self):
		self.queue = queue.Queue()
	def dispatch(self, event):
		self.queue.put(event)


class FileSystemStateManager(object):
	def __init__(self, state = None):
		if state is None:
			state = FileSystemState()
		self.state = state
		self.anything_changed = threading.Event()
		self.lock = threading.Lock()
		self._event_handler = QueueHandler()
		self.reset()
	
	def reset(self):
		"""
		reset all diff-like attributes (changed, added, removed, etc)
		"""
		self.changed = set()
		self.added = set()
		self.removed = set()
		self.affected = set()

		self._seen = set()
		self.reset_scan()
		self.anything_changed.clear()

	def update(self):
		with self.lock:
			self.reset()
			self._walk(base)
			self._propagate_changes()

	def reset_scan(self):
		self._seen = set()
	
	def _init_filesystem_watch(self):
		observer = Observer()
		observer.schedule(self._event_handler, path='.', recursive=True)
		observer.start()

	def state_changes(self):
		self._process_events_thread = threading.Thread(target=self.process_events_forever, name="FileSystemState inotify event handler")
		self._process_events_thread.daemon = True
		self._process_events_thread.start()
		self._init_filesystem_watch()

		while True:
			self.anything_changed.wait()
			with self.lock:
				yield self
				self.reset()
	
	def process_events_forever(self):
		try:
			while(True):
				new_events = []
				new_events.append(self._event_handler.queue.get())
				# suck up the rest of the events while we're at it
				try:
					while True:
						new_events.append(self._event_handler.queue.get(False, timeout=0.1))
				except queue.Empty: pass
				self._process_changes(new_events)
		except:
			#TODO: should be able to kill the main thread here
			import traceback
			traceback.print_exc(file=sys.stderr)
			raise

	def _process_changes(self, changes):
		with self.lock:
			self.reset_scan()
			map(self._process_change, changes)
			self._propagate_changes()
			if self._all_differences():
				self.anything_changed.set()

	def _get_existing_and_nonexisting_paths(self, change):
		existing = []
		nonexisting = []
		if change.event_type == events.EVENT_TYPE_MOVED:
			existing.append(change.dest_path)
			nonexisting.append(change.src_path)
		elif change.event_type in (events.EVENT_TYPE_CREATED, events.EVENT_TYPE_MODIFIED):
			existing.append(change.src_path)
		elif change.event_type == events.EVENT_TYPE_DELETED:
			nonexisting.append(change.src_path)
		else:
			raise AssertionError("unknown event type: %s" % (change.event_type,))
		return existing, nonexisting

	def _process_change(self, change):
		existing, nonexisting = self._get_existing_and_nonexisting_paths(change)

		existing = filter(None, map(lambda path: file_util.relative(path, None), existing))
		nonexisting = filter(None, map(lambda path: file_util.relative(path, None), nonexisting))

		if len(existing + nonexisting) == 0:
			info("skipped: %s" % (change.src_path))
			return

		self.reset_scan()
		if not change.is_directory:
			existing = filter(file_util.is_pyfile, existing)
			nonexisting = filter(file_util.is_pyfile, nonexisting)
			map(self._inspect, existing)
			map(self._remove, nonexisting)

	@property
	def bad(self):
		return set([item.path for item in self.state.values() if not item.ok()])
	
	def __repr__(self):
		def _repr(attr):
			return "%s: %r" % (attr, getattr(self, attr))
		internals = ', '.join(map(_repr, ('changed','added','removed','state')))
		return '<%s: (%s)>' % (self.__class__.__name__,internals)
	
	def _all_differences(self):
		"""return all files that have been added, changed or deleted"""
		return union(self.changed, self.added, self.removed)
	
	def _propagate_changes(self):
		self.affected = self._all_differences()
		state_changed = True
		while state_changed:
			state_changed = False
			for path, state in self.state.items():
				if path in self.affected: # already changed; ignore
					continue
				if len(self.affected.intersection(state.dependencies)) > 0: # any item has changed
					info("affected: %s (depends on: %s)" % (
						path,
						", ".join(self.affected.intersection(state.dependencies))))
					self.affected.add(path)
					state_changed = True
		if len(self.affected) > 0:
			info("all affected files:    \n%s" % ("\n".join(["  %s" % (item,) for item in sorted(self.affected)]),))

	def _remove(self, path):
		info("removed: %s" % path)
		try:
			del self.state[path]
		except KeyError:
			pass
		self.removed.add(path)
	
	def _walk(self, dir):
		for root, dirs, files in os.walk(dir):
			for dir_ in dirs:
				if dir_.startswith('.'):
					dirs.remove(dir_)
			for file_ in files:
				try:
					rel_path = file_util.relative(os.path.join(root, file_))
				except file_util.FileOutsideCurrentRoot:
					info("skipped non-cwd file: %s" % (file_,))
					continue
				self._inspect(rel_path)

	def _inspect(self, rel_path):
		if not file_util.is_pyfile(rel_path):
			log.debug("ignoring non-python file: %s" % (rel_path,))
			return

		if rel_path in self._seen:
			debug("visited file twice: %s" % (rel_path))
			return
		self._seen.add(rel_path)

		with self.state.lock:
			if rel_path in self.state or self.state.resurrect(rel_path):
				self._check_for_change(rel_path)
			else:
				self._add(rel_path)
	
	def _add(self, rel_path):
		info("added: %s" % (rel_path))
		self.added.add(rel_path)
		self.state.get_or_create(rel_path)
	
	def _check_for_change(self, rel_path):
		file_state = self.state[rel_path]
		if file_state.stale():
			info("changed: %s" % (rel_path,))
			file_state.update()
			self.changed.add(rel_path)
		else:
			debug("unchanged: %s" % (rel_path,))



########NEW FILE########
__FILENAME__ = test_result
success = 'success'
fail = 'fail'
error = 'error'
skip = 'skipped'

_all_states = set([success, fail, error, skip])
_acceptable_states = set([success, skip])

import logging
import traceback
import itertools
log = logging.getLogger(__name__)

class ResultEvent(object): pass

class TestResultSet(object):
	"""
	a set of TestResult objects that only keeps results from the most recent set
	(i.e the only results kept are those with the newest timestamp)
	"""
	def __init__(self):
		self.results = []
		
	def add(self, result):
		self.results.append(result)
		self._clean()

	def _clean(self):
		if len(self.results) <= 1:
			return
		newest = max([result.time for result in self.results])
		self.results = filter(lambda result: result.time >= newest, self.results)
	
	def ok(self):
		return all([result.ok() for result in self.results])
	
	def __repr__(self):
		repr(self.results)
		results = self.results
		if results:
			results = "\n   " + "\n   ".join(map(repr, results))
		return "<TestResults [%s]: %s>" % ("ok" if self.ok() else "NOT OK", results)

	def __str__(self):  return str(self.results)
	
	def __eq__(self, other):
		return type(self) == type(other) and self.results == other.results
	def __ne__(self, other):
		return not self == other
	def __hash__(self):
		hash(self.results)

class TestResult(ResultEvent):
	def __init__(self, state, id, name, address, path, err, run_start, outputs):
		if state not in _all_states:
			raise ValueError("state \"%s\" is invalid. Must be one of: %s" %
				(state, ', '.join(sorted(_all_states))))
		self.id = id
		self.state = state
		self.name = name
		self.time = run_start
		self.path = path
		self.outputs = outputs
		self.address = address
		if err:
			self.outputs.insert(0, ('traceback', self.extract_error(err)))
		self.attrs = ['id','state','name','time','path','address']
	
	def __filter_unittest_from_traceback(self, tb):
		trace = []

		while tb:
			frame = tb.tb_frame
			tb = tb.tb_next
			if '__unittest' in frame.f_globals:
				# this is the magical flag that prevents unittest internal
				# code from junking up the stacktrace
				continue
			trace.extend(traceback.extract_stack(frame, 1))
		return trace

	def extract_error(self, err):
		cls, instance, tb = err
		cls = getattr(cls, '__name__', str(cls))
		trace = traceback.extract_tb(tb)
		trace = self.__filter_unittest_from_traceback(tb)

		message = str(instance)
		marker = "begin captured"
		if marker in message:
			lines = message.splitlines()
			lines = itertools.takewhile(lambda line: marker not in line, lines)
			message = "\n".join(lines)
		return (cls, message, trace)

	def ok(self):
		return self.state in _acceptable_states
	
	def __str__(self):
		return "%s: %s@%s" % (self.state, self.name, self.time)
	
	def __repr__(self):
		return "<TestResult: %s>" % (str(self),)
	
	def __eq__(self, other):
		if not type(self) == type(other): return False
		get_self = lambda a: getattr(self, a)
		get_other = lambda a: getattr(other, a)
		return map(get_self, self.attrs) == map(get_other, self.attrs)

	def __ne__(self, other):
		return not self == other
	def __hash__(self):
		hash(self.state, self.name, self.time, self.err)
	
	def affect_state(self, state):
		state.get_or_create(self.path).test_results.add(self)
	
	@property
	def runnable_address(self):
		# no idea if this will work for all addresses,
		# it seems like a roundabout way to get back to
		# a particular test...
		return ":".join(map(str, self.address[1:]))

	def affect_page(self, page):
		page.test_complete(self)

########NEW FILE########
__FILENAME__ = basic
import time
import subprocess
import sys
import termstyle
from autonose.watcher import TestRun
import paragram as pg

class Basic(object):
	"""
	The main event handler for the basic (console) runner.
	"""
	def __init__(self, proc):
		proc.receive[pg.Any] = self.process
		proc.receive[str, pg.Any] = lambda *a: None

	def process(self, event):
		if isinstance(event, TestRun):
			print "\n" * 10
			subprocess.call('clear')
			msg = "# Running tests at %s  " % (time.strftime("%H:%M:%S"),)
	
			print >> sys.stderr, termstyle.inverted(termstyle.bold(msg))
			print >> sys.stderr, ""


########NEW FILE########
__FILENAME__ = file_openers
import subprocess

class TextMateOpener(object):
	def __init__(self):
		self.tm_path = self._get_tm_path()
	
	def open(self, path, line):
		if not self.tm_path:
			return False
		subprocess.Popen([self.tm_path, path, '-wl', str(line)])
		return True
	
	def _get_tm_path(self):
		which_proc = subprocess.Popen(['which', 'mate'], stdout=subprocess.PIPE)
		(stdout, stderr) = which_proc.communicate()
		if which_proc.returncode != 0:
			return None
		return stdout.rstrip()

class DefaultOpener(object):
	def open(self, path, line):
		from Cocoa import NSWorkspace
		NSWorkspace.sharedWorkspace().openFile_(path)
		return True

all_openers = [TextMateOpener, DefaultOpener]

########NEW FILE########
__FILENAME__ = scroll_keeper
import time
from Cocoa import *

# this class is far more involved than it ought to be.
# all it does is make sure the WebView scroll position is maintained
# across page updates

# we need a 1 second wait before we'll believe a scroll position of (0,0)
# to be the truth, because there are many times when the scroll pos has
# been set to nonzero but the following update will still see (0,0)

class ScrollKeeper(object):
	def __init__(self, html_view):
		self.html_view = html_view
		self.last_update = time.time()
		self.pos = NSMakePoint(0,0)
		self.needs_scroll = False
	
	def _scroll_view(self):
		return self.html_view.frameView().documentView().enclosingScrollView()
	def _scroll_source(self):
		return self._scroll_view().contentView() 
	def _scroll_target(self):
		return self._scroll_view().documentView()
	
	def save(self):
		if self.needs_scroll:
			return # we've already saved a position
		pos = self._scroll_source().bounds().origin
		if not self._spurious(pos):
			self.pos = pos
			self.needs_scroll = True
	
	def _spurious(self, pos):
		default_scroll = (pos.y == pos.x == 0)
		old = self.last_update < time.time() - 1
		return default_scroll and not old

	def restore(self):
		self.last_update = time.time()
		self._scroll_target().scrollPoint_(self.pos)
		self.needs_scroll = False


########NEW FILE########
__FILENAME__ = gtkapp
#!/usr/bin/env python

import sys
import os
import cgi
import thread
import subprocess

import gtk
import webkit
import gobject
import logging
log = logging.getLogger(__name__)

from shared import urlparse


class App(object):
	script = __file__
	URI_BASE = "file://" + (os.path.dirname(__file__))
	def __init__(self, mainloop):
		self.quitting = False
		self.mainloop = mainloop
		gtk.gdk.threads_init()
		thread.start_new_thread(gtk.main, ())
		self.do(self.init_gtk)
	
	def exit(self): # called by main thread
		if self.quitting:
			return # we already know!
		self.do(self.quit)
		self.do(lambda _=None: gtk.main_quit())
	
	def do(self, func, arg=None):
		gobject.idle_add(func, arg)
	
	def update(self, page=None):
		def _update(page=None):
			if page is None:
				page = self.mainLoop.page
			self.browser.load_html_string(str(page), self.URI_BASE)
		self.do(_update, page)
	
	def _navigation_requested_cb(self, view, frame, networkRequest):
		url = networkRequest.get_uri()
		if url.startswith(self.URI_BASE + "#"):
			test_id = url.split('#',1)[1]
			self.mainloop.run_just(test_id)
			return 1
		opener = os.environ.get('EDITOR', 'gnome-open')
		#log.info("navigation requested: %s" % (url,))
		if not urlparse.editable_file(url):
			return 0
		path, line = urlparse.path_and_line_from(url)
		subprocess.Popen([opener, path])
		# return 1 to stop any other handlers running
		return 1

	def quit(self, _=None):
		self.quitting = True
		self.mainloop.terminate()

	def init_gtk(self, _):
		self.window = gtk.Window()
		self.window.set_title("Autonose")
		
		scrollView = gtk.ScrolledWindow()
		self.browser = webkit.WebView()
		self.browser.connect('navigation_requested', self._navigation_requested_cb)
		scrollView.add(self.browser)

		self.window.set_default_size(800, 600)
		self.window.connect('destroy', self.quit)

		self.window.add(scrollView)
		self.update("<h1>loading...</h1>")
		self.window.show_all()


########NEW FILE########
__FILENAME__ = platform
import sys

def default_app():
	platform = sys.platform
	App = None
	if platform.startswith('linux'):
		from gtkapp import App
	else:
		raise RuntimeError("Unknown platform name: %r" % (platform,))
	return App

########NEW FILE########
__FILENAME__ = main
import logging
from autonose.shared.test_result import ResultEvent
from autonose.watcher import TestRun
import paragram as pg

from page import Page

log = logging.getLogger(__name__)

class Main(object):
	"""
	The main-loop of all graphical App classes
	(currently, gtkapp and cocoa-app)
	"""
	def __init__(self, proc, app_cls):
		self.delegate = app_cls(self)
		self.proc = proc
		self.page = Page()
		self.run_trigger = None

		@proc.receive('use_runner', pg.Process)
		def use_runner(msg, runner):
			self.runner = runner

		proc.receive[ResultEvent] = self.process
		proc.receive[TestRun] = self.process

	def run_just(self, test_id):
		self.runner.send('focus_on', test_id)

	def run_normally(self):
		self.runner.send('focus_on', None)

	def process(self, event):
		log.debug("processing event: %r" % (event,))
		event.affect_page(self.page)
		self.delegate.update(self.page)
	
	def terminate(self):
		self.proc.terminate()
	

########NEW FILE########
__FILENAME__ = page
import cgi
from datetime import datetime
import os

from autonose.shared.test_result import success, skip, error, fail

def h(o):
	return cgi.escape(str(o))

def shorten_file(file_path):
	abs_ = os.path.abspath(os.path.realpath(file_path))
	here = os.path.abspath(os.path.realpath(os.path.curdir))
	if abs_.startswith(here):
		return abs_[len(here)+1:]
	return abs_

class Summary(object):
	def __init__(self):
		self.reset()
	
	def reset(self):
		self.ran = self.failures = self.errors = self.skipped = 0
	
	def finish(self): pass

	def __str__(self):
		html = '<a href="#">#</a> ran <span class="tests">%s tests</span>' % (self.ran,)
		supplementary = [
			('failures', self.failures),
			('errors', self.errors),
			('skipped', self.skipped)
		]
		relevant_supps = list(filter(lambda x: x[-1] > 0, supplementary))
		def render_supp(supp):
			name, num = supp
			return '<span class="{name}">{num} {name}</span>'.format(name=name, num=num)
		if relevant_supps:
			html += ' (' + (', '.join(map(render_supp, relevant_supps))) + ')'
		return html

class Status(object):
	def __init__(self):
		self.time = None
	
	def reset(self):
		self.time = datetime.now()
		self.finish_time = None
	
	def finish(self):
		self.finish_time = datetime.now()

	def __str__(self):
		time_format = "%H:%M:%S"
		if self.time is None:
			return "loading..."
		if self.finish_time:
			diff = self.finish_time - self.time
			return 'run finished: %s (%ss)' % (self.finish_time.strftime(time_format), diff.seconds)
		return 'run started: %s' % (self.time.strftime("%H:%M:%S"),)

class Tests(object):
	success_msg = '<h1 id="success">All tests ran successfully</h1>'
	def __init__(self):
		self.tests = {}
		self.finished = False
	
	def __setitem__(self, key, item):
		self.tests[key] = item
	
	def __delitem__(self, key):
		try:
			del self.tests[key]
		except KeyError:
			pass
	
	def reset(self):
		self.finished = False
		self._clear_old_tests()
		self._mark_tests_as_old()
	
	def finish(self):
		self.finished = True
		self._clear_old_tests()
		
	def _clear_old_tests(self):
		for test in self.tests.values():
			if test.old:
				del self.tests[test.id]
	
	def _mark_tests_as_old(self):
		for test in self.tests.values():
			test.old = True

	def current_tests(self):
		return [test for test in self.tests.values() if not test.old]
	
	def __str__(self):
		if self.finished and len(self.current_tests()) == 0:
			return self.success_msg
		if len(self.tests) == 0:
			# not finished, but no tests failed yet...
			return '<div class="old">%s</div>' % (self.success_msg,)
			
		sorted_tests = sorted(self.tests.values(), key=lambda t: t.id)
		return '\n'.join([str(test) for test in sorted_tests])
		
class Test(object):
	def __init__(self, test, html):
		self.id = test.id
		self.address = test.runnable_address
		self.name = self.get_name(self.id)
		self.status = test.state
		self.html = html

		self.old = False
		self.time = datetime.now()
	
	def get_name(self, id_):
		name = id_
		name = name.replace('_', ' ')
		try:
			parts = name.split('.')
			parts = name.split('.')[1:]
			
			parts[-1] = '<span>%s</span>' % (parts[-1],)
				
			name = '&nbsp;&nbsp;&raquo; '.join(parts)
		except IndexError: pass
		return name
	
	def __str__(self):
		return """
			<div class="test {status} {staleness}%s">
				<a style="float:left;margin:7px;opacity:0.4;color:black;" href="#{address}">&#x25cf;</a>
				<h2 class="flush">{name}</h2>
				{content}
			</div>""".format(
				status=self.status,
				address=h(self.address),
				staleness='old' if self.old else 'current',
				name=self.name,
				content=self.html)

class Notice(object):
	levels = ['debug','info','error']
	def __init__(self):
		self.reset()
		
	def finish(self):
		if self.lvl == 0:
			self.val = ''

	def reset(self):
		self.val = ''
		self.lvl = 0
		
	def set(self, val, lvl=0):
		if lvl >= self.lvl:
			self.val = val
			self.lvl = lvl
	
	def __str__(self):
		return """<span class="notice %s">%s</span>""" % (self.levels[self.lvl], self.val)

class Page(object):
	def __init__(self):
		self.status = Status()
		self.summary = Summary()
		self.tests = Tests()
		self.notice = Notice()
		self.content = HtmlPage(head=self.status, foot=self.summary, body=self.tests, notice=self.notice)
	
	def _format(self, _type, value):
		try:
			processor = getattr(self, '_format_' + str(_type))
		except AttributeError, e:
			print "Error processing results: %s" % (e.message,)
			return None
		result = processor(value)
		return result

	def start_new_run(self):
		self._broadcast('reset')

	def finish(self):
		self._broadcast('finish')

	def _broadcast(self, methodname):
		for listener in (self.status, self.summary, self.notice, self.tests):
			getattr(listener, methodname)()

	def test_complete(self, test):
		self.summary.ran += 1
		self.notice.set("last test: %s" % (test.id,))
		
		if test.state == fail:
			self.summary.failures += 1
		elif test.state == error:
			self.summary.errors += 1
		elif test.state == skip:
			self.summary.skipped += 1
		elif test.state == success:
			del self.tests[test.id]
			return
		else:
			raise ValueError("unknown status type: %s" % (test.state,))
		
		output = []
		for output_source, content in test.outputs:
			formatted = self._format(output_source, content)
			output.append(formatted)
		
		output.append('</div>')
		output = "\n".join(output)
		
		test = Test(test, output)
		self.tests[test.id] = test
	
	def _format_traceback(self, value):
		output = []
		output.append("""<ul class="traceback flush">""")
		
		cls, message, trace = value
		output.append(self._format_cause(cls, message))

		for frame in trace:
			output.append(self._format_frame(*frame))

		output.append("</ul>")
		return '\n'.join(output)
	
	def _format__stream(self, name, output):
		if not output:
			return ""
		return """
			<div class="capture %s">
				<h3>Captured %s:</h3>
				<pre>%s</pre>
			</div>""" % (name, name, h(output))
	
	def _format_logging(self, content):
		return self._format__stream('logging', "\n".join(content))

	def _format_stderr(self, content):
		return self._format__stream('stderr', content)
	
	def _format_stdout(self, content):
		return self._format__stream('stdout', content)
	
	def _format_frame(self, filename, line_number, function_name, text):
		return """
			<li class="frame">
				<div class="line">from <code class="function">%s</code>, <a class="file" href="file://%s?line=%s">%s</a>, line <span class="lineno">%s</span>:</div>
				<div class="code"><pre>%s</pre></div>
			</li>
		""" % tuple(map(h, (function_name, filename, line_number, shorten_file(filename), line_number, text)))
	
	def _format_cause(self, cls, message):
		return """
			<li class="cause">
				<span class="type">%s</span>: <pre class="message">%s</pre>
			</li>
		""" % tuple(map(h, (cls, message)))
	
	def __str__(self):
		return str(self.content)


class HtmlPage(object):
	def __init__(self, head, body, foot, notice=''):
		self.head = head
		self.body = body
		self.foot = foot
		self.notice = notice
	
	def __str__(self):
		css_path = os.path.join(os.path.dirname(__file__), 'style.css')
		return """
			<html>
				<head>
					<link rel="stylesheet" type="text/css" href="file://%s" />
				</head>
				<body>
					<div id="head" class="flush">%s</div>
					<div id="notice" class="flush">%s</div>
					<div id="tests">%s</div>
					<div id="summary" class="flush">%s</div>
				</body>
			</html>
		""" % (css_path, self.head, self.notice, self.body, self.foot)

########NEW FILE########
__FILENAME__ = process
import os
import signal

class RunnerProcess(object):
	def __init__(self, pid, queue):
		self.queue = queue
		self.pid = pid
	
	def wait(self):
		pid, retcode = os.waitpid(self.pid, 0)
		return retcode
	
	def terminate(self):
		return os.kill(self.pid, signal.SIGINT)


########NEW FILE########
__FILENAME__ = urlparse
import urllib
import cgi

file_protocol = 'file://'
def editable_file(url):
	return url.startswith(file_protocol) and urllib.splitquery(url)[0].endswith('.py')
	
def path_and_line_from(url):
	if not url.startswith(file_protocol):
		raise ValueError("URI (%s) is not a '%s' URI" % (url, file_protocol))
	url = url[len(file_protocol):]
	path, query = urllib.splitquery(url)
	path = urllib.url2pathname(path)
	line = 0
	try:
		if query:
			query_dict = cgi.parse_qs(query)
			line = query_dict['line'][0]
	except (IndexError, KeyError): pass
	return (path, line)


########NEW FILE########
__FILENAME__ = watcher
import nose
import logging
import os
import time

from shared import file_util
from shared.file_util import FileOutsideCurrentRoot


# because the logcapture plugin
# sets logging to full throttle, we want to
# explicitly keep track of the log level
# requested by runner.py
actual_log_level = logging.INFO
def _log(lvl):
	log = logging.getLogger(__name__)
	def _(msg):
		if actual_log_level >= lvl:
			log.log(lvl, msg)
	return _

debug = _log(logging.DEBUG)
info = _log(logging.INFO)
warning = _log(logging.WARN)

from shared.test_result import TestResult, success, skip, error, fail, ResultEvent

class TestRun(ResultEvent):
	is_test=False
	def __init__(self, time):
		self.time = time
	
	def affect_state(self, state):
		pass

	def affect_page(self, page):
		page.start_new_run()

class Completion(ResultEvent):
	is_test=False

	def affect_page(self, page):
		page.finish()

def get_path(x): return x.path

class Watcher(nose.plugins.Plugin):
	name = 'autonose'
	score = 8000 # watcher is a mostly passive plugin so we shouldn't
	             # interfere with anyone else, however if others steal
	             # the handleError and handleFaure calls (as the
	             # xml plugin does), autonose fails to remember which
	             # tests failed - which is a Very Bad Thing (TM)
	enabled = True
	env_opt = 'AUTO_NOSE'
	
	def __init__(self, state_manager, *results_listeners):
		self.state_manager = state_manager
		self.results_listeners = results_listeners
		self._setup()
		super(self.__class__, self).__init__()
	
	def _send(self, *msg):
		[listener.send(*msg) for listener in self.results_listeners]
	
	def _setup(self):
		self.start_time = time.time()
		self.files_to_run = set(self.state_manager.affected).union(set(self.state_manager.bad))
		if len(self.state_manager.affected):
			warning("changed files: %s" % (self.state_manager.affected,))
		if len(self.state_manager.bad):
			info("bad files: %s" % (self.state_manager.bad,))
		if len(self.files_to_run):
			warning("files to run: %s" % (self.files_to_run,))
		self._send(TestRun(self.start_time))

	def options(self, parser, env=os.environ):
		pass

	def configure(self, options, conf=None):
		self.enabled = True

	def run_all(self):
		self.wantFile = lambda filename: None

	def wantFile(self, filename):
		try:
			rel_file = file_util.relative(filename)
		except FileOutsideCurrentRoot:
			warning("ignoring file outside current root: %s" % (filename,))
			return False
		
		debug("want file %s? %s" % (rel_file, "NO" if (rel_file not in self.files_to_run) else "if you like..."))
		debug("files to run are: %r" % (self.files_to_run,))
		if rel_file not in self.files_to_run:
			return False
		return None # do nose's default behaviour
	
	def beforeTest(self, test):
		self._current_test = test
	
	def _test_file(self, test):
		addr = test.address()
		err = RuntimeError("test.address does not contain a valid file: %s" % (addr,))
		if not addr: raise err

		file_path = addr[0]
		if not os.path.exists(file_path): raise err
		return file_util.relative(file_util.source(file_path))

	def _update_test(self, test, state, err=None):
		log_lvl = debug
		if state != 'success':
			log_lvl = info
		log_lvl("test finished: %s with state: %s" % (test, state))
		self._send(TestResult(
			state=state,
			id=test.id(),
			name=str(test),
			address=nose.util.test_address(test),
			err=err,
			run_start=self.start_time,
			path=self._test_file(test),
			outputs=self._capture_outputs(test)
		))
		self._current_test = None
		
	def addSuccess(self, test):
		self._update_test(test, success)
	
	def handleFailure(self, test, err):
		err = test.plugins.formatFailure(test, err) or err
		self._update_test(test, fail, err)
	
	def handleError(self, test, err):
		err = test.plugins.formatError(test, err) or err
		self._update_test(test, error, err)
	
	def _addSkip(self, test):
		self._update_test(test, skip)
	
	def afterTest(self, test):
		if self._current_test is not None:
			if self._current_test is not test:
				raise RuntimeError(
					"result for %s was never recorded, but this test is %s" %
					(self._current_test, test))
			self._addSkip(self._current_test)
		debug('-'*80)

	def _capture_outputs(self, test):
		outputs = []
		try:
			outputs.append(('stdout', test.capturedOutput))
		except AttributeError: pass

		try:
			outputs.append(('logging', test.capturedLogging))
		except AttributeError: pass
		return outputs
	
	def finalize(self, result=None):
		self._send(Completion())
	


########NEW FILE########
__FILENAME__ = issue_21_custom_exception

class SomeError(Exception):
	pass

def foo():
	raise SomeError()

def test_foo():
	foo()

########NEW FILE########
__FILENAME__ = runner_test
import test_helper

from mocktest import *

#TODO: fill in all these tests!

class RunnerTest(TestCase):
	def test_should_run_nose_with_autonose_enabled(self):
		pass
	
	def test_should_run_nose_with_autonose_disabled_if__all_specified(self):
		pass
	
	def test_should_run_nose_with_debug(self):
		pass
	
	def test_should_run_nose_with_debug_enabled(self):
		pass
	
	def test_should_run_in_a_loop_if_once_not_specified(self):
		pass
	
	def test_should_sleep__sleep_time__between_scans(self):
		pass
	
	def test_should_not_include_state_receiver_when_running_in_focussed_mode(self):
		pass


########NEW FILE########
__FILENAME__ = scanner_test
import test_helper

import logging
from mocktest import *
from autonose import scanner
import os, types
import sys

pickle_path = os.path.abspath('.autonose-depends.pickle')
class ScannerTest(TestCase):
	def test_should_load_saved_dependency_information(self):
		picklefile = mock('pickle file')
		expect(scanner).open_file(pickle_path).and_return(picklefile)
		pickle = mock('unpickled info')
		expect(scanner.pickle).load(picklefile).and_return(pickle)

		manager = mock('manager')
		expect(scanner.FileSystemStateManager)['__new__'](any_(type), pickle).and_return(manager)
		
		loaded = scanner.load()
		self.assertEqual(loaded, manager)
		
	def test_should_print_a_useful_error_on_load_failure_when_pickle_exists(self):
		picklefile = mock('pickle file')
		f = open(pickle_path, 'w')
		f.write('garbage')
		f.close()
		modify(sys).stderr = mock('stderr')
		expect(sys.stderr).write(string_matching("Failed loading \"\.autonose-depends\.pickle\"\."))
		expect(sys.stderr).write("Deleting picklefile and trying again...")
		expect(sys.stderr).write('\n')
		expect(os).remove(pickle_path)
		logger = logging.getLogger("autonose.scanner")
		try:
			logger.setLevel(logging.CRITICAL)
			self.assertRaises(SystemExit, scanner.load, args=(1,))
		finally:
			logger.setLevel(logging.ERROR)
			try:
				os.remove(pickle_path)
			except OSError: pass
	
	def test_should_return_an_empty_dict_when_no_pickle_exists(self):
		expect(scanner).open_file.and_raise(IOError())
		state = mock('state')
		manager = mock('manager')
		expect(scanner.FileSystemState)['__new__'].and_return(state)
		expect(scanner.FileSystemStateManager)['__new__'].and_return(manager)
		expect(scanner.pickle).load.never()
		expect(manager).update
		modify(sys).stderr = mock('stderr')
		expect(sys.stderr).write.never()
		
		self.assertEqual(scanner.load(), manager)
	
	def test_should_delete_dependency_information_on_reset(self):
		expect(scanner.os.path).exists(pickle_path).and_return(True)
		expect(scanner.os).remove(pickle_path)
		scanner.reset()
	
	def test_should_only_delete_saved_dependencies_if_they_exist(self):
		expect(scanner.os.path).exists(pickle_path).and_return(False)
		expect(scanner.os).remove.never()
		scanner.reset()


########NEW FILE########
__FILENAME__ = file_state_test
import os
import time
from unittest import TestCase, skip

from autonose.shared import FileState
from autonose.shared.test_result  import TestResultSet
from autonose.shared.test_result  import TestResult

class FileStateTest(TestCase):
	def setUp(self):
		self.filename = 'test.file'
		self._file = open(self.filename, 'w')
		self._file.write('contents!')
		self._file.close()

	def tearDown(self):
		os.remove(self._file.name)
	
	def test_should_get_current_modtime(self):
		mtime = os.stat(self.filename).st_mtime
		stamp = FileState(self.filename)
		
		self.assertEqual(stamp.path, self.filename)
		self.assertEqual(stamp.modtime, mtime)
	
	def _touch(self):
		newtime = time.time() + 10
		os.utime(self.filename, (newtime, newtime))
	
	def test_should_check_staleness(self):
		stamp = FileState(self.filename)
		self._touch()
		self.assertTrue(stamp.stale())

	def test_should_update_mtime(self):
		stamp = FileState(self.filename)
		self._touch()
		self.assertTrue(stamp.stale())
		stamp.update()
		self.assertFalse(stamp.stale())

	def test_should_default_to_new_test_result_set_info(self):
		self.assertEqual(FileState(self.filename).test_results, TestResultSet())
	
	@skip('TODO')
	def test_should_pickle(self):
		pass
	
	@skip('TODO')
	def test_should_remember_deleted_files_and_resurrect_them_if_they_reappear(self):
		pass


########NEW FILE########
__FILENAME__ = state_test
from .. import test_helper

from mocktest import *

#TODO: fill in all these tests!

class StateTest(TestCase):
	def test_anything_changed_should_be_affected_by_changed__added_and_removed_files(self):
		pass
	
	def test_update_should_ignore_dot_files(self):
		pass
	
	def test_update_should_inspect_all_files_using_relative_paths(self):
		pass
	
	def test_inspect_should_skip_already_seen_files(self):
		pass
	
	def test_inspect_should_track_removed_files(self):
		pass
	
	def test_inspect_should_track_added_files(self):
		pass
	
	def test_inspect_should_track_changed_files(self):
		pass

	def test_inspect_should_ignore_unchanged_files(self):
		pass
	
	def test_affected_should_be_the_transitive_dependencies_of_added_removed_and_updated_files(self):
		pass
		
	def test_bad_should_be_all_affected_and_non__ok_files(self):
		pass
	
	def test_file_state_should_be_indexable_by_relative_file_path(self):
		#TODO: this is probably a poor idea...
		pass
	
	def test_should_return_modified_files_without_propagating_changes(self):
		pass


########NEW FILE########
__FILENAME__ = test_result_test
from mocktest import *

from autonose.shared.test_result import TestResult, TestResultSet
def make_result(state, id=None, name=None, address=None, path=None, err=None, run_start=None, outputs=[]):
	return TestResult(state, id, name, address, path, err, run_start, outputs)


class TestResultTest(TestCase):
	def test_should_store_state(self):
		state = 'success'
		self.assertEqual(make_result(state).state, state)
		
	def test_should_store_name_from_test(self):
		self.assertEqual(make_result('success', name='test_str').name, 'test_str')
		
	def test_should_store_time(self):
		time = mock('time')
		self.assertEqual(make_result('success', run_start=time).time, time)

	def test_should_extract_trace_from_err(self):
		err = ('cls', 'instance', mock('traceback').with_child(tb_frame = []))
		self.assertEqual(make_result('success', err=err).outputs[0], ('traceback', ('cls', 'instance', [])))

	def test_should_validate_state(self):
		self.assertRaises(ValueError, lambda: make_result('notastate', None, None, None))

	def test_should_be_ok_if_state_is_in_acceptable_states(self):
		self.assertTrue(make_result('success', None, None, None).ok())
		self.assertTrue(make_result('skipped', None, None, None).ok())
	
	def test_should_not_be_ok_if_state_is_not_in_acceptable_states(self):
		self.assertFalse(make_result('fail', None, None, None).ok())
		self.assertFalse(make_result('error', None, None, None).ok())
	
class TestResultSetTest(TestCase):
	def result_mock(self, name=None, time=0, ok=False):
		_mock = mock(name).with_children(time=time).with_methods(ok=ok)
		return _mock
		
	def test_should_not_be_ok_if_any_result_is_not(self):
		ok1 = self.result_mock(ok = True, name='ok1')
		ok2 = self.result_mock(ok = True, name='ok2')
		not_ok = self.result_mock(ok = False)
		trs = TestResultSet()
		trs.add(ok1.raw)
		trs.add(ok2.raw)
		trs.add(not_ok.raw)
		self.assertFalse(trs.ok())
		
	def test_should_be_ok_if_all_results_are_success_or_skip(self):
		ok1 = make_result('success')
		ok2 = make_result('skipped')
		trs = TestResultSet()

		trs.add(ok1)
		trs.add(ok2)
		self.assertTrue(trs.ok())
	
	def test_should_be_ok_with_no_test_cases(self):
		trs = TestResultSet()
		self.assertTrue(trs.ok())
		
	def test_should_clear_all_non_newest_results_on_add(self):
		old = self.result_mock(time=1, name='old')
		new = self.result_mock(time=2, name='new')
		new2 = self.result_mock(time=2, name='new2')
		trs = TestResultSet()
		
		trs.add(old)
		self.assertEqual(trs.results, [old])
		trs.add(new)
		self.assertEqual(trs.results, [new])
		trs.add(new2)
		self.assertEqual(trs.results, [new, new2])
		

########NEW FILE########
__FILENAME__ = test_helper
import logging
import sys
import os

logging.getLogger('test').setLevel(logging.DEBUG)
autonose_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if not autonose_root in sys.path:
	sys.path.insert(0, autonose_root)


########NEW FILE########
__FILENAME__ = page_test
from mocktest import *
from autonose.ui.shared.page import Page, Summary

class SummaryTest(TestCase):
	def setUp(self):
		self.summary = Summary()

	def test_success_formatting(self):
		self.summary.ran += 5
		self.assertMatches(string_containing(
			'ran <span class="tests">5 tests</span>'
		), str(self.summary))
		assert 'failures' not in str(self.summary)
		assert 'errors' not in str(self.summary)

	def test_fail_formatting(self):
		self.summary.ran += 5
		self.assertMatches(string_containing(
			'ran <span class="tests">5 tests</span>'
		), str(self.summary))
		assert 'failures' not in str(self.summary)
		assert 'errors' not in str(self.summary)
	
	def test_error_formatting(self):
		self.summary.ran += 5
		self.summary.skips += 1
		self.assertMatches(string_containing(
			'ran <span class="tests">5 tests</span> '
			'(<span class="skip">1 skipped</span>)'
		), str(self.summary))
		assert 'failures' not in str(self.summary)

	def test_error_formatting(self):
		self.summary.ran += 5
		self.summary.errors += 1
		self.assertMatches(string_containing(
			'ran <span class="tests">5 tests</span> '
			'(<span class="errors">1 errors</span>)'
		), str(self.summary))
		assert 'failures' not in str(self.summary)

	def test_combination_formatting(self):
		self.summary.ran += 5
		self.summary.failures += 1
		self.summary.errors += 2
		self.summary.skipped += 3
		self.assertMatches(string_containing(
			'ran <span class="tests">5 tests</span> '
			'(<span class="failures">1 failures</span>, '
			'<span class="errors">2 errors</span>, '
			'<span class="skipped">3 skipped</span>)'
		), str(self.summary))

########NEW FILE########
__FILENAME__ = watcher_test
from . import test_helper

from mocktest import *
from autonose.watcher import Watcher
from autonose import scanner
from autonose.shared.test_result import TestResult
from autonose.shared import test_result
from autonose import watcher as watcher_module
from unittest import skip

from autonose.shared import file_util
import time
import os

import logging
def without_logging(func, level=logging.WARNING):
	log = logging.disable(level)
	try:
		func()
	finally:
		log = logging.disable(logging.NOTSET)

#@skip('TODO: requires updating, state_manager is used instead of scanning directly')
class WatcherTest(TestCase):
	def watcher(self, state_manager=None):
		def default_manager():
			manager = mock('state manager').with_children(bad=[], affected=[])
			return manager
		self.state_manager = state_manager or default_manager()
		return Watcher(self.state_manager)

	def test_should_only_run_affected_and_bad_files(self):
		# have to use an object with a path for debugging purposes - not ideal..
		class Num(object):
			def __init__(self, n):
				self.n = n
				self.path = "PATH"
			def __repr__(self): return repr(self.n)
			def __str__(self):  return str(self.n)
			def __eq__(self, other): return self.n == other.n
		good = set(map(Num, [1,2,3]))
		bad = set(map(Num, [4,5,6]))
		changed = set(map(Num, [7,8,9]))
		affected = set(map(Num, [10,11,12]))
		state = mock('state').with_children(good=good, bad=bad, changed=changed, affected=affected)
		watcher = self.watcher(state)
		
		self.assertEqual(watcher.files_to_run, bad.union(affected))

	def test_should_update_test_on_success(self):
		watcher = self.watcher()
		good = mock('good')
		
		expect(watcher)._update_test(good, test_result.success).once()
		watcher.beforeTest(good)
		watcher.addSuccess(good)

	def test_should_update_test_on_failure(self):
		watcher = self.watcher()

		bad = mock('bad').with_children(plugins=mock('bad plugins').with_methods(formatFailure=None))
		bad_err = mock('bad_err')

		expect(watcher)._update_test(bad, test_result.fail, bad_err).once()

		watcher.beforeTest(bad)
		watcher.handleFailure(bad, bad_err)

	def test_should_update_test_on_error(self):
		watcher = self.watcher()

		ugly = mock('ugly').with_children(plugins=mock('ugly plugins').with_methods(formatError=None))
		ugly_err = mock('ugly_err')
		expect(watcher)._update_test(ugly, test_result.error, ugly_err).once()

		watcher.beforeTest(ugly)
		watcher.handleError(ugly, ugly_err)

	def test_should_update_test_on_skip(self):
		watcher = self.watcher()

		skippy = mock('skippy')
		expect(watcher)._update_test(skippy, test_result.skip).once()
		watcher.beforeTest(skippy)
		watcher.afterTest(skippy)
	
	def test_should_not_run_tests_from_outside_current_root(self):
		path = mock('path')

		expect(file_util).relative(path).and_raise(file_util.FileOutsideCurrentRoot()).once()
		
		watcher = self.watcher()

		without_logging(lambda: self.assertEqual(watcher.wantFile(path), False), level=logging.ERROR)

	def test_should_save_state_on_finalize(self):
		watcher = self.watcher()

		expect(watcher)._send.once()
		watcher.finalize()





########NEW FILE########
