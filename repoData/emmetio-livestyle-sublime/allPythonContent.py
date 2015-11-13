__FILENAME__ = livestyle
import json
import re
import threading
import sys
import os.path
import platform
import imp
import logging
import json
import codecs

import sublime
import sublime_plugin

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
for p in [BASE_PATH, os.path.join(BASE_PATH, 'lsutils')]:
	if p not in sys.path:
		sys.path.append(p)

# need the windows select.pyd binary for ST2 only
if os.name == 'nt' and sublime.version()[0] < '3':
	__file = os.path.normpath(os.path.abspath(__file__))
	__path = os.path.dirname(__file)
	libs_path = os.path.join(__path, 'lsutils', 'libs', platform.architecture()[0])
	if libs_path not in sys.path:
		sys.path.insert(0, libs_path)


# Make sure all dependencies are reloaded on upgrade
if 'lsutils.reloader' in sys.modules:
	imp.reload(sys.modules['lsutils.reloader'])
import lsutils.reloader

import lsutils.editor as eutils
import lsutils.diff
import lsutils.websockets as ws
import lsutils.webkit_installer

sublime_ver = int(sublime.version()[0])

_suppressed = set()

# List of all opened views and their file names
_view_file_names = {}

# Create logger
logger = logging.getLogger('livestyle')
logger.propagate = False
if not logger.handlers:
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	ch.setFormatter(logging.Formatter('Emmet LiveStyle: %(message)s'))
	logger.addHandler(ch)

@eutils.main_thread
def identify_editor(socket):
	"Sends editor identification info to browser"
	ws.send({
		'action': 'id',
		'data': {
			'id': 'st%d' % sublime_ver,
			'title': 'Sublime Text %d' % sublime_ver,
			'icon': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABu0lEQVR42q2STWsTURhG3WvdCyq4CEVBAgYCM23JjEwy+cJC41gRdTIEGyELU7BNNMJQhUBBTUjSRdRI3GThRld+gbj2JwhuRFy5cZ3Ncd5LBwZCIIIXDlzmeZ9z4d458t9WoVB4XywWCcnn89i2TSaTIZvNEuRhJvtP0e7R6XT6VYJer8dkMmE0GrHf3uPxg1s8f+TR9ncZDocq63a7SiId6YogBqiPg8FASe43d3iz7/D7rcuP1zf4NnHxfV9yQc0CSFcEeihotVo0Gg22tzbh3SbP7lq4lzTuuHlqtZrkQlSgi8AIBZVKBc/zuH5lnc7tFX4OL/L9wOTJlsbGepFyuSwzUYERCqIXhGVZJJNJbqbP0b66DC8ucO/yedLptMzMF4S3X7JXeFWJ4Zln2LZPw9NT+BuxxQTquaw1Xl47yZ/WEr92j3PgnMBc08nlcvMF1Wo1DNW7G4aBpmnouo5pmtGyzM4K+v0+4/F4ITqdzqzAdV0cxyGVSsmpc5G/s1QqzQg+N5tNdUmJRIJ4PD4XkdTrdaQTClYDlvnHFXTOqu7h5mHAx4AvC/IhYE+6IliK2IwFWT3sHPsL6BnLQ4kfGmsAAAAASUVORK5CYII=',
			'files': eutils.css_files()
		}
	}, socket)

@eutils.main_thread
def update_files():
	ws.send({
		'action': 'updateFiles',
		'data': eutils.css_files()
	})

def send_patches(buf_id=None, p=None):
	if not buf_id or not p:
		return

	p = eutils.parse_json(p)
	view = eutils.view_for_buffer_id(buf_id)
	if p and view is not None:
		ws.send({
			'action': 'update',
			'data': {
				'editorFile': eutils.file_name(view),
				'patch': p
			}
		})

def read_file(file_path):
	try:
		with codecs.open(file_path, 'r', 'utf-8') as f:
			return f.read()
	except Exception as e:
		logger.error(e)
		return None

@eutils.main_thread
def send_unsaved_files(payload, sender):
	files = payload.get('files', [])
	out = []
	for f in files:
		view = eutils.view_for_file(f)
		if not view:
			continue

		content = eutils.content(view)
		if view and view.is_dirty():
			fname = view.file_name()
			pristine = None
			if not fname:
				# untitled file
				pristine = ''
			elif os.path.exists(fname):
				pristine = read_file(fname)

			if pristine is not None:
				out.append({
					'file': f,
					'pristine': pristine,
					'content': content
				})

	if out:
		ws.send({
			'action': 'unsavedFiles',
			'data': {
				'files': out
			}
		}, sender)
	else:
		logger.info('No unsaved changes')

@eutils.main_thread
def handle_patch_request(payload, sender):
	logger.debug('Handle CSS patch request')

	editor_file = payload.get('editorFile')
	if not editor_file:
		logger.debug('No editor file in payload, skip patching')
		return

	view = eutils.view_for_file(editor_file)
	if view is None:
		logger.warn('Unable to find view for %s file' % editor_file)
		if editor_file[0] == '<':
			# it's an untitled file, but view doesn't exists
			return

		view = sublime.active_window().open_file(editor_file)

	patch = payload.get('patch')
	if patch:
		apply_patch_on_view(view, patch)

def apply_patch_on_view(view, patch):
	"Waits until view is loaded and applies patch on it"
	if view.is_loading():
		return sublime.set_timeout(lambda: apply_patch_on_view(view, patch), 100)

	# make sure it's a CSS file
	if not eutils.is_css_view(view, True):
		logger.debug('File %s is not CSS, aborting' % eutils.file_name(view))
		return

	focus_view(view)
	lsutils.diff.patch(view.buffer_id(), patch)

def focus_view(view):
	# looks like view.window() is broken in ST2,
	# use another way to find parent window
	for w in sublime.windows():
		for v in w.views():
			if v.id() == view.id():
				return w.focus_view(v)

def apply_patched_source(buf_id, content):
	view = eutils.view_for_buffer_id(buf_id)
	if view is None or content is None:
		return

	view.run_command('livestyle_replace_content', {'payload': content})


def should_handle(view):
	"Checks whether incoming view modification should be handled"
	if view.id() in _suppressed:
		_suppressed.remove(view.id())
		return False

	# don't do anything if there are no connected clients
	# or change performed outside of CSS file
	return ws.clients() and eutils.is_css_view(view, True)

def suppress_update(view):
	"Marks given view to skip next incoming update"
	_suppressed.add(view.id())

class LivestyleListener(sublime_plugin.EventListener):
	def on_new(self, view):
		_view_file_names[view.id()] = eutils.file_name(view)

		if eutils.is_css_view(view):
			update_files()

	def on_load(self, view):
		_view_file_names[view.id()] = eutils.file_name(view)

		if eutils.is_css_view(view):
			update_files()

	def on_close(self, view):
		if view.id() in _view_file_names:
			del _view_file_names[view.id()]

		update_files()

	def on_modified(self, view):
		if should_handle(view):
			logger.debug('Run diff')
			lsutils.diff.diff(view.buffer_id())

	def on_activated(self, view):
		if eutils.is_css_view(view, True):
			logger.debug('Prepare diff')
			update_files()
			lsutils.diff.prepare_diff(view.buffer_id())

	def on_post_save(self, view):
		k = view.id()
		new_name = eutils.file_name(view)
		if k in _view_file_names and _view_file_names[k] != new_name:
			ws.send({
				'action': 'renameFile',
				'data': {
					'oldname': _view_file_names[k],
					'newname': new_name
				}
			})
			_view_file_names[k] = new_name


class LivestyleReplaceContentCommand(sublime_plugin.TextCommand):
	"Internal command to properly replace view content"
	def run(self, edit, payload=None, **kwargs):
		if not payload:
			return

		suppress_update(self.view)
		s = self.view.sel()[0]
		sels = [[s.a, s.a]]
		
		try:
			payload = eutils.parse_json(payload)
		except:
			payload = {'content': payload, 'selection': None}

		# if sublime_ver < 3:
		#	payload['content'] = payload.get('content', u'').decode('utf-8')

		self.view.replace(edit, sublime.Region(0, self.view.size()), payload.get('content', ''))

		if payload.get('selection'):
			sels = [payload.get('selection')]

		self.view.sel().clear()
		for s in sels:
			self.view.sel().add(sublime.Region(s[0], s[1]))

		self.view.show(self.view.sel())

class LivestyleInstallWebkitExt(sublime_plugin.ApplicationCommand):
	def run(self, *args, **kw):
		try:
			lsutils.webkit_installer.install()
			sublime.message_dialog('WebKit extension installed successfully. Please restart WebKit.')
		except lsutils.webkit_installer.LSIException as e:
			sublime.error_message('Unable to install WebKit extension:\n%s' % e.message)
		except Exception as e:
			sublime.error_message('Error during WebKit extension installation:\n%s' % e)

	def description(*args, **kwargs):
		return 'Install LiveStyle for WebKit extension'

class LivestyleApplyPatch(sublime_plugin.TextCommand):
	"Applies LiveStyle patch to active view"
	def run(self, edit, **kw):
		if not eutils.is_css_view(self.view, True):
			return sublime.error_message('You should run this action on CSS file')

		# build sources list
		sources = [view for view in eutils.all_views() if re.search(r'[\/\\]lspatch-[\w\-]+\.json$', view.file_name() or '')]

		# gather all available items
		display_items = []
		patches = []

		def add_item(patch, name):
			for p in patch:
				display_items.append([p['file'], 'Updated selectors: %s' % ', '.join(p['selectors']), name])
				patches.append(json.dumps(p['data']))

		for view in sources:
			add_item(lsutils.diff.parse_patch(eutils.content(view)), view.file_name())

		# check if buffer contains valid patch
		pb =  sublime.get_clipboard()
		if lsutils.diff.is_valid_patch(pb):
			add_item(lsutils.diff.parse_patch(pb), 'Clipboard')

		def on_done(ix):
			if ix == -1: return
			apply_patch_on_view(self.view, patches[ix])

		if len(display_items) == 1:
			on_done(0)
		elif display_items:
			self.view.window().show_quick_panel(display_items, on_done)
		else:
			sublime.error_message('No patches found. You have to open patch files in Sublime Text or copy patch file contents into clipboard and run this action again.')

def unload_handler():
	ws.stop()

def start_plugin():
	ws.start(int(eutils.get_setting('port')))
	logger.setLevel(logging.DEBUG if eutils.get_setting('debug', False) else logging.INFO)

	# collect all view's file paths
	for view in eutils.all_views():
		_view_file_names[view.id()] = eutils.file_name(view)


def plugin_loaded():
	sublime.set_timeout(start_plugin, 100)

# Init plugin
ws.on('update', handle_patch_request)
ws.on('requestUnsavedFiles', send_unsaved_files)
ws.on('ws_open', identify_editor)
lsutils.diff.on('diff_complete', send_patches)
lsutils.diff.on('patch_complete', apply_patched_source)

if sublime_ver < 3:
	plugin_loaded()
########NEW FILE########
__FILENAME__ = diff
import sublime
import sublime_plugin

import sys
import threading
import os.path
import codecs
import time
import json
import logging
import imp

import lsutils.editor as eutils
import lsutils.websockets as ws

from lsutils.event_dispatcher import EventDispatcher

LOCK_TIMEOUT = 15 # State lock timeout, in seconds

logger = logging.getLogger('livestyle')
_diff_state = {}
_patch_state = {}
_dispatcher = EventDispatcher()

def on(name, callback):
	_dispatcher.on(name, callback)

def off(name, callback=None):
	_dispatcher.off(name, callback)

def one(name, callback):
	_dispatcher.one(name, callback)

def get_syntax(view):
	return view.score_selector(0, 'source.less, source.scss') and 'scss' or 'css'

def lock_state(state):
	state['running'] = True
	state['start_time'] = time.time()

def unlock_state(state, log_message=None):
	state['running'] = False
	if log_message:
		logger.debug(log_message % (time.time() - state['start_time'], ))

def is_locked(state):
	if state['running']:
		return time.time() - state['start_time'] < LOCK_TIMEOUT

	return False

###############################
# Diff
###############################

def prepare_diff(buf_id):
	"Prepare buffer for diff'ing"
	view = eutils.view_for_buffer_id(buf_id)
	if view is None:
		return

	if buf_id not in _diff_state:
		_diff_state[buf_id] = {
			'running': False, 
			'required': False, 
			'content': '', 
			'start_time': 0
		}

	_diff_state[buf_id]['content'] = eutils.content(view)

def diff(buf_id):
	"""
	Performs diff'ing of two states of the same file
	in separate thread
	"""
	if buf_id not in _diff_state:
		logger.debug('Prepare buffer')
		prepare_diff(buf_id)

	state = _diff_state[buf_id]
	if is_locked(state):
		state['required'] = True
	else:
		_start_diff(buf_id)

def _start_diff(buf_id):
	view = eutils.view_for_buffer_id(buf_id)
	if view is None:
		return

	state = _diff_state[buf_id]
	prev_content = state['content']
	content = eutils.content(view)
	syntax = get_syntax(view)

	state['required'] = False

	client = ws.find_client({'supports': 'css'})

	if client:
		logger.debug('Use connected "%s" client for diff' % client.name())
		lock_state(state)
		ws.send({
			'action': 'diff',
			'data': {
				'file': buf_id,
				'syntax': syntax,
				'source1': prev_content,
				'source2': content
			}
		}, client)
	else:
		logger.error('No suitable client for diff')
		
def _on_diff_complete(buf_id, patches, content):
	_dispatcher.trigger('diff_complete', buf_id, patches)

	if buf_id in _diff_state:
		state = _diff_state[buf_id]
		unlock_state(state, 'Diff performed in %.4fs')
		if patches is not None:
			state['content'] = content

		if state['required']:
			diff(buf_id)

###############################
# Patch
###############################

def patch(buf_id, patches):
	"""
	Performs patching of given source in separate thread 
	"""
	logger.debug('Request patching')
	if buf_id not in _patch_state:
		_patch_state[buf_id] = {
			'running': False,
			'patches': [],
			'start_time': 0
		}

	state = _patch_state[buf_id]
	patches = eutils.parse_json(patches) or []

	if is_locked(state):
		logger.debug('Batch patches')
		state['patches'] += patches
	elif patches:
		logger.debug('Start patching')
		_start_patch(buf_id, patches)

def _start_patch(buf_id, patch):
	view = eutils.view_for_buffer_id(buf_id)
	if view is None:
		logger.debug('No view to patch')
		return

	content = eutils.content(view)
	syntax = get_syntax(view)
	state = _patch_state[buf_id]


	client = ws.find_client({'supports': 'css'})
	logger.debug('Client: %s' % client)

	if client:
		logger.debug('Use connected "%s" client for patching' % client.name())
		lock_state(state)
		ws.send({
			'action': 'patch',
			'data': {
				'file': buf_id,
				'syntax': syntax,
				'patches': patch,
				'source': content
			}
		}, client)
	else:
		logger.error('No suitable client for patching')

def _on_patch_complete(buf_id, content):
	_dispatcher.trigger('patch_complete', buf_id, content)

	if buf_id in _patch_state:
		state = _patch_state[buf_id]
		unlock_state(state, 'Patch performed in %.4fs')
		if state['patches']:
			patch(buf_id, state['patches'])
			state['patches'] = []


def is_valid_patch(content):
	"Check if given content is a valid patch"
	if eutils.isstr(content):
		try:
			content = json.loads(content)
		except:
			return False

	try:
		return content and content.get('id') == 'livestyle'
	except:
		return False

def parse_patch(data):
	"Parses given patch and returns object with meta-data about patch"
	if not is_valid_patch(data):
		return None

	if eutils.isstr(data): data = json.loads(data)
	out = []
	for k, v in data.get('files', {}).items():
		out.append({
			'file': k,
			'selectors': _stringify_selectors(v),
			'data': v
		})

	return out

def _stringify_selectors(patch):
	"Stringifies updated selectors. Mostly used for deceision making"
	out = []
	for p in patch:
		if p['action'] == 'remove':
			# No need to display removed selectors since, in most cases,
			# they are mostly garbage left during typing
			continue

		out.append('/'.join(s[0] for s in p['path']))

	return out

###############################
# Handle Websockets events
###############################

@eutils.main_thread
def _on_diff_editor_sources(data, sender):
	logger.debug('Received diff sources response: %s' % ws.format_message(data))
	if not data['success']:
		logger.error('[ws] %s' % data.get('result', ''))
		_on_diff_complete(data.get('file'), None, None)
	else:
		r = data.get('result', {})
		_on_diff_complete(data.get('file'), r.get('patches'), r.get('source'))

@eutils.main_thread
def _on_patch_editor_sources(data, sender):
	logger.debug('Received patched source: %s' % ws.format_message(data))
	if not data['success']:
		logger.error('[ws] %s' % data.get('result', ''))
		_on_patch_complete(data.get('file'), None)
	else:
		r = data.get('result', {})
		_on_patch_complete(data.get('file'), r)

ws.on('diff', _on_diff_editor_sources)
ws.on('patch', _on_patch_editor_sources)

########NEW FILE########
__FILENAME__ = editor
"""
Utility method for Sublime Text editor
"""

import sublime
import sublime_plugin

import re

re_css = re.compile(r'\.css$', re.IGNORECASE)
_settings = None

try:
	isinstance("", basestring)
	def isstr(s):
		return isinstance(s, basestring)
except NameError:
	def isstr(s):
		return isinstance(s, str)

def main_thread(fn):
	"Run function in main thread"
	return lambda *args, **kwargs: sublime.set_timeout(lambda: fn(*args, **kwargs), 1)

def get_setting(name, default=None):
	global _settings
	if not _settings:
		_settings = sublime.load_settings('LiveStyle.sublime-settings')

	return _settings.get(name, default)

def parse_json(data):
	return json.loads(data) if isstr(data) else data

def content(view):
	"Returns content of given view"
	return view.substr(sublime.Region(0, view.size()))

def file_name(view):
	"Returns file name representation for given view"
	return view.file_name() or temp_file_name(view)

def temp_file_name(view):
	"Returns temporary name for (unsaved) views"
	return '<untitled:%d>' % view.id()

def all_views():
	"Returns all view from all windows"
	views = []
	for w in sublime.windows():
		for v in w.views():
			views.append(v)

	return views

def view_for_buffer_id(buf_id):
	"Returns view for given buffer id"
	for view in all_views():
		if view.buffer_id() == buf_id:
			return view

	return None

def view_for_file(path):
	"Locates editor view with given file path"
	for view in all_views():
		if file_name(view) == path:
			return view

	return None

def active_view():
	"Returns currently active view"
	return sublime.active_window().active_view()

def css_views():
	"Returns list of opened CSS views"
	return [view for view in all_views() if is_css_view(view)]

def css_files():
	"Returns list of opened CSS files"
	return [file_name(view) for view in css_views()]

def is_css_view(view, strict=False):
	"Check if given view can be used for live CSS"
	sel = get_setting('css_files_selector', 'source.css - source.css.less')
	if not view.file_name() and not strict:
		# For new files, check if current scope is text.plain (just created)
		# or it's a strict CSS
		sel = '%s, text.plain' % sel

	return view.score_selector(0, sel) > 0

def unindent_text(text, pad):
	"""
	Removes padding at the beginning of each text's line
	@type text: str
	@type pad: str
	"""
	lines = text.splitlines()
	
	for i,line in enumerate(lines):
		if line.startswith(pad):
			lines[i] = line[len(pad):]
	
	return '\n'.join(lines)

def get_line_padding(line):
	"""
	Returns padding of current editor's line
	@return str
	"""
	m = re.match(r'^(\s+)', line)
	return m and m.group(0) or ''

########NEW FILE########
__FILENAME__ = event_dispatcher
# Simple event dispatching mini-framework

class EventDispatcher():
	def __init__(self):
		self._callbacks = {}

	def __del__(self):
		self._callbacks = None

	def on(self, name, callback, once=False):
		if name not in self._callbacks:
			self._callbacks[name] = []

		self._callbacks[name].append({
			'callback': callback,
			'once': once
		})

	def off(self, name, callback=None):
		if name in self._callbacks:
			if callback is None:
				self._callbacks[name].clear()
			else:
				self._callbacks[name] = [c for c in self._callbacks[name] if c['callback'] != callback]

	def one(self, name, callback):
		self.on(name, callback, True)

	def trigger(self, name, *args, **kwargs):
		if name in self._callbacks:
			for c in self._callbacks[name]:
				c['callback'](*args, **kwargs)

			self._callbacks[name] = [c for c in self._callbacks[name] if not c['once']]

########NEW FILE########
__FILENAME__ = reloader
import sys
import imp

# Dependecy reloader for Emmet LiveStyle plugin
# The original idea is borrowed from 
# https://github.com/wbond/sublime_package_control/blob/master/package_control/reloader.py 

reload_mods = []
for mod in sys.modules:
	if mod.startswith('lsutils') and sys.modules[mod] != None:
		reload_mods.append(mod)

mods_load_order = [
	'lsutils.event_dispatcher',
	'lsutils.editor',
	'lsutils.websockets',
	'lsutils.webkit_installer',
	'lsutils.diff'
]

for mod in mods_load_order:
	if mod in reload_mods:
		imp.reload(sys.modules[mod])
########NEW FILE########
__FILENAME__ = webkit_installer
"LiveStyle for WebKit extension installer"
import os
import re
import os.path
import plistlib
import platform
import zipfile
import sublime
import logging

try:
	# in Linux, it throws exception
	import io
except:
	pass

WEBKIT_PATH     = '/Applications/WebKit.app'
WEBKIT_RES_PATH = 'Contents/Frameworks/%s/WebInspectorUI.framework/Resources'
WEBKIT_URL      = 'http://nightly.webkit.org'
LIVESTYLE_PACK  = 'livestyle-webkit.zip'

logger = logging.getLogger('livestyle')

class LSIException(Exception):
	def __init__(self, message=''):
		self.message = message

def install():
	"Installs LiveStyle for WebKit extension"
	assertPlatform()
	assertWebkit()
	for v in ['10.7', '10.8', '10.9']:
		path = os.path.join(WEBKIT_PATH, WEBKIT_RES_PATH % v)
		if os.path.exists(path):
			logger.debug('Installing into %s' % path)
			unpack(path)
			patch(path)

def assertPlatform():
	system_name = platform.system()
	if platform.system() != 'Darwin':
		raise LSIException('WebKit extension works on OS X only')

def assertWebkit():
	if not os.path.exists(WEBKIT_PATH):
		raise LSIException('WebKit is not installed. Download it from %s' % WEBKIT_URL)

	# check WebKit version
	plist = plistlib.readPlist(os.path.join(WEBKIT_PATH, 'Contents/Info.plist'))
	if plist.get('CFBundleVersion', '0') < '153080':
		raise LSIException('Your WebKit version is outdated. Updated or download newer version from %s' % WEBKIT_URL)

def get_package_name():
	"Returns current package name"
	path = '%s/../' % os.path.dirname(__file__)
	name = os.path.basename(os.path.normpath(path))
	return name.replace('.sublime-package', '')

def unpack(target_path):
	"Unpacks LiveStyle extension into given path"
	pack = os.path.join(sublime.packages_path(), 'LiveStyle', LIVESTYLE_PACK)
	if sublime.version() >= '3':
		# in ST3 we should load package differently
		pack = sublime.load_binary_resource('Packages/%s/%s' % (get_package_name(), LIVESTYLE_PACK))
		pack = io.BytesIO(pack)

	target_path = os.path.join(target_path, 'livestyle')
	if os.path.exists(target_path):
		# remove old data
		for f in os.listdir(target_path):
			os.remove(os.path.join(target_path, f))
	else:
		os.mkdir(target_path)

	package_zip = zipfile.ZipFile(pack, 'r')
	package_zip.extractall(target_path)
	package_zip.close()


def patch(target_path):
	"Patches WebInspector at given path"
	main_html = os.path.join(target_path, 'Main.html')
	if not os.path.exists(main_html):
		raise LSIException('WebInspector is corrupted')

	content = None
	code = '<script src="livestyle/livestyle.js"></script>'
	with open(main_html) as f:
		content = f.read()
		if content.find(code) == -1:
			r = re.compile(r'(<script>.*?WebInspector\.loaded\(\).*?</script>)', flags=re.S)
			content = r.sub('%s\\n    \\1' % code, content)

	if content:
		with open(main_html, 'w') as f:
			f.write(content)

########NEW FILE########
__FILENAME__ = websockets
import json
import logging
import threading

# don't know why, but tornado's IOLoop cannot
# properly load platform modules during runtime, 
# so we pre-import them
try:
	import select

	if hasattr(select, "epoll"):
		import tornado.platform.epoll
	elif hasattr(select, "kqueue"):
		import tornado.platform.kqueue
	else:
		import tornado.platform.select
except ImportError:
	pass

# import tornado.process
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver

import lsutils.editor as eutils
from lsutils.event_dispatcher import EventDispatcher

# Tornado server instance
httpserver = None

logger = logging.getLogger('livestyle')

broadcast_events = ['update']

# Websockets event dispatcher
_dispatcher = EventDispatcher()

class LiveStyleIDHandler(tornado.web.RequestHandler):
	def get(self):
		self.write('LiveStyle websockets server is up and running')

class WSHandler(tornado.websocket.WebSocketHandler):
	clients = set()
	def open(self):
		logger.debug('client connected')
		WSHandler.clients.add(self)
		_dispatcher.trigger('ws_open', self)
	
	def on_message(self, message):
		logger.debug('message received:\n%s' % format_message(message))
		_dispatcher.trigger('ws_message', message, self)

		message = json.loads(message)
		_dispatcher.trigger(message['action'], message.get('data'), self)

		if message['action'] in broadcast_events:
			send(message, exclude=self)

		if message['action'] == 'handshake':
			self.livestyleClientInfo = message['data']
		elif message['action'] == 'error':
			logger.error('[client] %s' % message['data'].get('message'))

	def on_close(self):
		logger.debug('client disconnected')
		_dispatcher.trigger('ws_close', self)
		WSHandler.clients.discard(self)

	def name(self):
		return getattr(self, 'livestyleClientInfo', {}).get('id', 'unknown')

def on(name, callback):
	_dispatcher.on(name, callback)

def off(name, callback=None):
	_dispatcher.off(name, callback)

def one(name, callback):
	_dispatcher.one(name, callback)

def format_message(msg):
	msg = repr(msg)
	return msg[0:300]

def send(message, client=None, exclude=None):
	"Sends given message to websocket clients"
	if not eutils.isstr(message):
		message = json.dumps(message)
	clients = WSHandler.clients if not client else [client]
	if exclude:
		clients = [c for c in clients if c != exclude]

	if not clients:
		logger.debug('Cannot send message, client list empty')
	else:
		logger.debug('Sending ws message %s' % format_message(message))
		for c in clients:
			c.write_message(message)

def clients():
	return WSHandler.clients

def find_client(flt={}):
	for c in clients():
		info = getattr(c, 'livestyleClientInfo', None)
		if info:
			is_valid = True
			for k,v in flt.items():
				if k == 'supports':
					if v not in info.get('supports', []):
						is_valid = False
						break
				elif info.get(k) != v:
					is_valid = False
					break

			if is_valid:
				return c

		elif not flt:
			return c


application = tornado.web.Application([
	(r'/browser', WSHandler),
	(r'/', LiveStyleIDHandler)
])

def start(port):
	global httpserver
	logger.info('Starting LiveStyle server on port %s' % port)
	httpserver = tornado.httpserver.HTTPServer(application)
	httpserver.listen(port, address='127.0.0.1')
	threading.Thread(target=tornado.ioloop.IOLoop.instance().start).start()

def stop():
	global httpserver
	for c in WSHandler.clients.copy():
		c.close()
	WSHandler.clients.clear()

	if httpserver:
		logger.info('Stopping server')
		httpserver.stop()

	tornado.ioloop.IOLoop.instance().stop()

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""This module contains implementations of various third-party
authentication schemes.

All the classes in this file are class mixins designed to be used with
the `tornado.web.RequestHandler` class.  They are used in two ways:

* On a login handler, use methods such as ``authenticate_redirect()``,
  ``authorize_redirect()``, and ``get_authenticated_user()`` to
  establish the user's identity and store authentication tokens to your
  database and/or cookies.
* In non-login handlers, use methods such as ``facebook_request()``
  or ``twitter_request()`` to use the authentication tokens to make
  requests to the respective services.

They all take slightly different arguments due to the fact all these
services implement authentication and authorization slightly differently.
See the individual service classes below for complete documentation.

Example usage for Google OpenID::

    class GoogleLoginHandler(tornado.web.RequestHandler,
                             tornado.auth.GoogleMixin):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            if self.get_argument("openid.mode", None):
                user = yield self.get_authenticated_user()
                # Save the user with e.g. set_secure_cookie()
            else:
                yield self.authenticate_redirect()
"""

from __future__ import absolute_import, division, print_function, with_statement

import base64
import binascii
import functools
import hashlib
import hmac
import time
import uuid

from tornado.concurrent import Future, chain_future, return_future
from tornado import gen
from tornado import httpclient
from tornado import escape
from tornado.httputil import url_concat
from tornado.log import gen_log
from tornado.util import bytes_type, u, unicode_type, ArgReplacer

try:
    import urlparse  # py2
except ImportError:
    import urllib.parse as urlparse  # py3

try:
    import urllib.parse as urllib_parse  # py3
except ImportError:
    import urllib as urllib_parse  # py2


class AuthError(Exception):
    pass


def _auth_future_to_callback(callback, future):
    try:
        result = future.result()
    except AuthError as e:
        gen_log.warning(str(e))
        result = None
    callback(result)


def _auth_return_future(f):
    """Similar to tornado.concurrent.return_future, but uses the auth
    module's legacy callback interface.

    Note that when using this decorator the ``callback`` parameter
    inside the function will actually be a future.
    """
    replacer = ArgReplacer(f, 'callback')

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        future = Future()
        callback, args, kwargs = replacer.replace(future, args, kwargs)
        if callback is not None:
            future.add_done_callback(
                functools.partial(_auth_future_to_callback, callback))
        f(*args, **kwargs)
        return future
    return wrapper


class OpenIdMixin(object):
    """Abstract implementation of OpenID and Attribute Exchange.

    See `GoogleMixin` below for a customized example (which also
    includes OAuth support).

    Class attributes:

    * ``_OPENID_ENDPOINT``: the identity provider's URI.
    """
    @return_future
    def authenticate_redirect(self, callback_uri=None,
                              ax_attrs=["name", "email", "language", "username"],
                              callback=None):
        """Redirects to the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI with additional parameters including ``openid.mode``.

        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.

        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        callback_uri = callback_uri or self.request.uri
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        self.redirect(self._OPENID_ENDPOINT + "?" + urllib_parse.urlencode(args))
        callback()

    @_auth_return_future
    def get_authenticated_user(self, callback, http_client=None):
        """Fetches the authenticated user data upon redirect.

        This method should be called by the handler that receives the
        redirect from the `authenticate_redirect()` method (which is
        often the same as the one that calls it; in that case you would
        call `get_authenticated_user` if the ``openid.mode`` parameter
        is present and `authenticate_redirect` if it is not).

        The result of this method will generally be used to set a cookie.
        """
        # Verify the OpenID response via direct request to the OP
        args = dict((k, v[-1]) for k, v in self.request.arguments.items())
        args["openid.mode"] = u("check_authentication")
        url = self._OPENID_ENDPOINT
        if http_client is None:
            http_client = self.get_auth_http_client()
        http_client.fetch(url, self.async_callback(
            self._on_authentication_verified, callback),
            method="POST", body=urllib_parse.urlencode(args))

    def _openid_args(self, callback_uri, ax_attrs=[], oauth_scope=None):
        url = urlparse.urljoin(self.request.full_url(), callback_uri)
        args = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.identity":
            "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.return_to": url,
            "openid.realm": urlparse.urljoin(url, '/'),
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update({
                "openid.ns.ax": "http://openid.net/srv/ax/1.0",
                "openid.ax.mode": "fetch_request",
            })
            ax_attrs = set(ax_attrs)
            required = []
            if "name" in ax_attrs:
                ax_attrs -= set(["name", "firstname", "fullname", "lastname"])
                required += ["firstname", "fullname", "lastname"]
                args.update({
                    "openid.ax.type.firstname":
                    "http://axschema.org/namePerson/first",
                    "openid.ax.type.fullname":
                    "http://axschema.org/namePerson",
                    "openid.ax.type.lastname":
                    "http://axschema.org/namePerson/last",
                })
            known_attrs = {
                "email": "http://axschema.org/contact/email",
                "language": "http://axschema.org/pref/language",
                "username": "http://axschema.org/namePerson/friendly",
            }
            for name in ax_attrs:
                args["openid.ax.type." + name] = known_attrs[name]
                required.append(name)
            args["openid.ax.required"] = ",".join(required)
        if oauth_scope:
            args.update({
                "openid.ns.oauth":
                "http://specs.openid.net/extensions/oauth/1.0",
                "openid.oauth.consumer": self.request.host.split(":")[0],
                "openid.oauth.scope": oauth_scope,
            })
        return args

    def _on_authentication_verified(self, future, response):
        if response.error or b"is_valid:true" not in response.body:
            future.set_exception(AuthError(
                "Invalid OpenID response: %s" % (response.error or
                                                 response.body)))
            return

        # Make sure we got back at least an email from attribute exchange
        ax_ns = None
        for name in self.request.arguments:
            if name.startswith("openid.ns.") and \
                    self.get_argument(name) == u("http://openid.net/srv/ax/1.0"):
                ax_ns = name[10:]
                break

        def get_ax_arg(uri):
            if not ax_ns:
                return u("")
            prefix = "openid." + ax_ns + ".type."
            ax_name = None
            for name in self.request.arguments.keys():
                if self.get_argument(name) == uri and name.startswith(prefix):
                    part = name[len(prefix):]
                    ax_name = "openid." + ax_ns + ".value." + part
                    break
            if not ax_name:
                return u("")
            return self.get_argument(ax_name, u(""))

        email = get_ax_arg("http://axschema.org/contact/email")
        name = get_ax_arg("http://axschema.org/namePerson")
        first_name = get_ax_arg("http://axschema.org/namePerson/first")
        last_name = get_ax_arg("http://axschema.org/namePerson/last")
        username = get_ax_arg("http://axschema.org/namePerson/friendly")
        locale = get_ax_arg("http://axschema.org/pref/language").lower()
        user = dict()
        name_parts = []
        if first_name:
            user["first_name"] = first_name
            name_parts.append(first_name)
        if last_name:
            user["last_name"] = last_name
            name_parts.append(last_name)
        if name:
            user["name"] = name
        elif name_parts:
            user["name"] = u(" ").join(name_parts)
        elif email:
            user["name"] = email.split("@")[0]
        if email:
            user["email"] = email
        if locale:
            user["locale"] = locale
        if username:
            user["username"] = username
        claimed_id = self.get_argument("openid.claimed_id", None)
        if claimed_id:
            user["claimed_id"] = claimed_id
        future.set_result(user)

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class OAuthMixin(object):
    """Abstract implementation of OAuth 1.0 and 1.0a.

    See `TwitterMixin` and `FriendFeedMixin` below for example implementations,
    or `GoogleMixin` for an OAuth/OpenID hybrid.

    Class attributes:

    * ``_OAUTH_AUTHORIZE_URL``: The service's OAuth authorization url.
    * ``_OAUTH_ACCESS_TOKEN_URL``: The service's OAuth access token url.
    * ``_OAUTH_VERSION``: May be either "1.0" or "1.0a".
    * ``_OAUTH_NO_CALLBACKS``: Set this to True if the service requires
      advance registration of callbacks.

    Subclasses must also override the `_oauth_get_user_future` and
    `_oauth_consumer_token` methods.
    """
    @return_future
    def authorize_redirect(self, callback_uri=None, extra_params=None,
                           http_client=None, callback=None):
        """Redirects the user to obtain OAuth authorization for this service.

        The ``callback_uri`` may be omitted if you have previously
        registered a callback URI with the third-party service.  For
        some sevices (including Friendfeed), you must use a
        previously-registered callback URI and cannot specify a
        callback via this method.

        This method sets a cookie called ``_oauth_request_token`` which is
        subsequently used (and cleared) in `get_authenticated_user` for
        security purposes.

        Note that this method is asynchronous, although it calls
        `.RequestHandler.finish` for you so it may not be necessary
        to pass a callback or use the `.Future` it returns.  However,
        if this method is called from a function decorated with
        `.gen.coroutine`, you must call it with ``yield`` to keep the
        response from being closed prematurely.

        .. versionchanged:: 3.1
           Now returns a `.Future` and takes an optional callback, for
           compatibility with `.gen.coroutine`.
        """
        if callback_uri and getattr(self, "_OAUTH_NO_CALLBACKS", False):
            raise Exception("This service does not support oauth_callback")
        if http_client is None:
            http_client = self.get_auth_http_client()
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            http_client.fetch(
                self._oauth_request_token_url(callback_uri=callback_uri,
                                              extra_params=extra_params),
                self.async_callback(
                    self._on_request_token,
                    self._OAUTH_AUTHORIZE_URL,
                    callback_uri,
                    callback))
        else:
            http_client.fetch(
                self._oauth_request_token_url(),
                self.async_callback(
                    self._on_request_token, self._OAUTH_AUTHORIZE_URL,
                    callback_uri,
                    callback))

    @_auth_return_future
    def get_authenticated_user(self, callback, http_client=None):
        """Gets the OAuth authorized user and access token.

        This method should be called from the handler for your
        OAuth callback URL to complete the registration process. We run the
        callback with the authenticated user dictionary.  This dictionary
        will contain an ``access_key`` which can be used to make authorized
        requests to this service on behalf of the user.  The dictionary will
        also contain other fields such as ``name``, depending on the service
        used.
        """
        future = callback
        request_key = escape.utf8(self.get_argument("oauth_token"))
        oauth_verifier = self.get_argument("oauth_verifier", None)
        request_cookie = self.get_cookie("_oauth_request_token")
        if not request_cookie:
            future.set_exception(AuthError(
                "Missing OAuth request token cookie"))
            return
        self.clear_cookie("_oauth_request_token")
        cookie_key, cookie_secret = [base64.b64decode(escape.utf8(i)) for i in request_cookie.split("|")]
        if cookie_key != request_key:
            future.set_exception(AuthError(
                "Request token does not match cookie"))
            return
        token = dict(key=cookie_key, secret=cookie_secret)
        if oauth_verifier:
            token["verifier"] = oauth_verifier
        if http_client is None:
            http_client = self.get_auth_http_client()
        http_client.fetch(self._oauth_access_token_url(token),
                          self.async_callback(self._on_access_token, callback))

    def _oauth_request_token_url(self, callback_uri=None, extra_params=None):
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_REQUEST_TOKEN_URL
        args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            if callback_uri == "oob":
                args["oauth_callback"] = "oob"
            elif callback_uri:
                args["oauth_callback"] = urlparse.urljoin(
                    self.request.full_url(), callback_uri)
            if extra_params:
                args.update(extra_params)
            signature = _oauth10a_signature(consumer_token, "GET", url, args)
        else:
            signature = _oauth_signature(consumer_token, "GET", url, args)

        args["oauth_signature"] = signature
        return url + "?" + urllib_parse.urlencode(args)

    def _on_request_token(self, authorize_url, callback_uri, callback,
                          response):
        if response.error:
            raise Exception("Could not get request token: %s" % response.error)
        request_token = _oauth_parse_response(response.body)
        data = (base64.b64encode(escape.utf8(request_token["key"])) + b"|" +
                base64.b64encode(escape.utf8(request_token["secret"])))
        self.set_cookie("_oauth_request_token", data)
        args = dict(oauth_token=request_token["key"])
        if callback_uri == "oob":
            self.finish(authorize_url + "?" + urllib_parse.urlencode(args))
            callback()
            return
        elif callback_uri:
            args["oauth_callback"] = urlparse.urljoin(
                self.request.full_url(), callback_uri)
        self.redirect(authorize_url + "?" + urllib_parse.urlencode(args))
        callback()

    def _oauth_access_token_url(self, request_token):
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_ACCESS_TOKEN_URL
        args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_token=escape.to_basestring(request_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        if "verifier" in request_token:
            args["oauth_verifier"] = request_token["verifier"]

        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            signature = _oauth10a_signature(consumer_token, "GET", url, args,
                                            request_token)
        else:
            signature = _oauth_signature(consumer_token, "GET", url, args,
                                         request_token)

        args["oauth_signature"] = signature
        return url + "?" + urllib_parse.urlencode(args)

    def _on_access_token(self, future, response):
        if response.error:
            future.set_exception(AuthError("Could not fetch access token"))
            return

        access_token = _oauth_parse_response(response.body)
        self._oauth_get_user_future(access_token).add_done_callback(
            self.async_callback(self._on_oauth_get_user, access_token, future))

    def _oauth_consumer_token(self):
        """Subclasses must override this to return their OAuth consumer keys.

        The return value should be a `dict` with keys ``key`` and ``secret``.
        """
        raise NotImplementedError()

    @return_future
    def _oauth_get_user_future(self, access_token, callback):
        """Subclasses must override this to get basic information about the
        user.

        Should return a `.Future` whose result is a dictionary
        containing information about the user, which may have been
        retrieved by using ``access_token`` to make a request to the
        service.

        The access token will be added to the returned dictionary to make
        the result of `get_authenticated_user`.

        For backwards compatibility, the callback-based ``_oauth_get_user``
        method is also supported.
        """
        # By default, call the old-style _oauth_get_user, but new code
        # should override this method instead.
        self._oauth_get_user(access_token, callback)

    def _oauth_get_user(self, access_token, callback):
        raise NotImplementedError()

    def _on_oauth_get_user(self, access_token, future, user_future):
        if user_future.exception() is not None:
            future.set_exception(user_future.exception())
            return
        user = user_future.result()
        if not user:
            future.set_exception(AuthError("Error getting user"))
            return
        user["access_token"] = access_token
        future.set_result(user)

    def _oauth_request_parameters(self, url, access_token, parameters={},
                                  method="GET"):
        """Returns the OAuth parameters as a dict for the given request.

        parameters should include all POST arguments and query string arguments
        that will be sent with the request.
        """
        consumer_token = self._oauth_consumer_token()
        base_args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_token=escape.to_basestring(access_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        args = {}
        args.update(base_args)
        args.update(parameters)
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            signature = _oauth10a_signature(consumer_token, method, url, args,
                                            access_token)
        else:
            signature = _oauth_signature(consumer_token, method, url, args,
                                         access_token)
        base_args["oauth_signature"] = escape.to_basestring(signature)
        return base_args

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class OAuth2Mixin(object):
    """Abstract implementation of OAuth 2.0.

    See `FacebookGraphMixin` below for an example implementation.

    Class attributes:

    * ``_OAUTH_AUTHORIZE_URL``: The service's authorization url.
    * ``_OAUTH_ACCESS_TOKEN_URL``:  The service's access token url.
    """
    @return_future
    def authorize_redirect(self, redirect_uri=None, client_id=None,
                           client_secret=None, extra_params=None,
                           callback=None):
        """Redirects the user to obtain OAuth authorization for this service.

        Some providers require that you register a redirect URL with
        your application instead of passing one via this method. You
        should call this method to log the user in, and then call
        ``get_authenticated_user`` in the handler for your
        redirect URL to complete the authorization process.

        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        args = {
            "redirect_uri": redirect_uri,
            "client_id": client_id
        }
        if extra_params:
            args.update(extra_params)
        self.redirect(
            url_concat(self._OAUTH_AUTHORIZE_URL, args))
        callback()

    def _oauth_request_token_url(self, redirect_uri=None, client_id=None,
                                 client_secret=None, code=None,
                                 extra_params=None):
        url = self._OAUTH_ACCESS_TOKEN_URL
        args = dict(
            redirect_uri=redirect_uri,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
        )
        if extra_params:
            args.update(extra_params)
        return url_concat(url, args)


class TwitterMixin(OAuthMixin):
    """Twitter OAuth authentication.

    To authenticate with Twitter, register your application with
    Twitter at http://twitter.com/apps. Then copy your Consumer Key
    and Consumer Secret to the application
    `~tornado.web.Application.settings` ``twitter_consumer_key`` and
    ``twitter_consumer_secret``. Use this mixin on the handler for the
    URL you registered as your application's callback URL.

    When your application is set up, you can use this mixin like this
    to authenticate the user with Twitter and get access to their stream::

        class TwitterLoginHandler(tornado.web.RequestHandler,
                                  tornado.auth.TwitterMixin):
            @tornado.web.asynchronous
            @tornado.gen.coroutine
            def get(self):
                if self.get_argument("oauth_token", None):
                    user = yield self.get_authenticated_user()
                    # Save the user using e.g. set_secure_cookie()
                else:
                    yield self.authorize_redirect()

    The user object returned by `~OAuthMixin.get_authenticated_user`
    includes the attributes ``username``, ``name``, ``access_token``,
    and all of the custom Twitter user attributes described at
    https://dev.twitter.com/docs/api/1.1/get/users/show
    """
    _OAUTH_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
    _OAUTH_AUTHENTICATE_URL = "https://api.twitter.com/oauth/authenticate"
    _OAUTH_NO_CALLBACKS = False
    _TWITTER_BASE_URL = "https://api.twitter.com/1.1"

    @return_future
    def authenticate_redirect(self, callback_uri=None, callback=None):
        """Just like `~OAuthMixin.authorize_redirect`, but
        auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.

        .. versionchanged:: 3.1
           Now returns a `.Future` and takes an optional callback, for
           compatibility with `.gen.coroutine`.
        """
        http = self.get_auth_http_client()
        http.fetch(self._oauth_request_token_url(callback_uri=callback_uri),
                   self.async_callback(
                       self._on_request_token, self._OAUTH_AUTHENTICATE_URL,
                       None, callback))

    @_auth_return_future
    def twitter_request(self, path, callback=None, access_token=None,
                        post_args=None, **args):
        """Fetches the given API path, e.g., ``statuses/user_timeline/btaylor``

        The path should not include the format or API version number.
        (we automatically use JSON format and API version 1).

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        All the Twitter methods are documented at http://dev.twitter.com/

        Many methods require an OAuth access token which you can
        obtain through `~OAuthMixin.authorize_redirect` and
        `~OAuthMixin.get_authenticated_user`. The user returned through that
        process includes an 'access_token' attribute that can be used
        to make authenticated requests via this method. Example
        usage::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.TwitterMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                @tornado.gen.coroutine
                def get(self):
                    new_entry = yield self.twitter_request(
                        "/statuses/update",
                        post_args={"status": "Testing Tornado Web Server"},
                        access_token=self.current_user["access_token"])
                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        yield self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        """
        if path.startswith('http:') or path.startswith('https:'):
            # Raw urls are useful for e.g. search which doesn't follow the
            # usual pattern: http://search.twitter.com/search.json
            url = path
        else:
            url = self._TWITTER_BASE_URL + path + ".json"
        # Add the OAuth resource request signature if we have credentials
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args:
            url += "?" + urllib_parse.urlencode(args)
        http = self.get_auth_http_client()
        http_callback = self.async_callback(self._on_twitter_request, callback)
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=http_callback)
        else:
            http.fetch(url, callback=http_callback)

    def _on_twitter_request(self, future, response):
        if response.error:
            future.set_exception(AuthError(
                "Error response %s fetching %s" % (response.error,
                                                   response.request.url)))
            return
        future.set_result(escape.json_decode(response.body))

    def _oauth_consumer_token(self):
        self.require_setting("twitter_consumer_key", "Twitter OAuth")
        self.require_setting("twitter_consumer_secret", "Twitter OAuth")
        return dict(
            key=self.settings["twitter_consumer_key"],
            secret=self.settings["twitter_consumer_secret"])

    @gen.coroutine
    def _oauth_get_user_future(self, access_token):
        user = yield self.twitter_request(
            "/account/verify_credentials",
            access_token=access_token)
        if user:
            user["username"] = user["screen_name"]
        raise gen.Return(user)


class FriendFeedMixin(OAuthMixin):
    """FriendFeed OAuth authentication.

    To authenticate with FriendFeed, register your application with
    FriendFeed at http://friendfeed.com/api/applications. Then copy
    your Consumer Key and Consumer Secret to the application
    `~tornado.web.Application.settings` ``friendfeed_consumer_key``
    and ``friendfeed_consumer_secret``. Use this mixin on the handler
    for the URL you registered as your application's Callback URL.

    When your application is set up, you can use this mixin like this
    to authenticate the user with FriendFeed and get access to their feed::

        class FriendFeedLoginHandler(tornado.web.RequestHandler,
                                     tornado.auth.FriendFeedMixin):
            @tornado.web.asynchronous
            @tornado.gen.coroutine
            def get(self):
                if self.get_argument("oauth_token", None):
                    user = yield self.get_authenticated_user()
                    # Save the user using e.g. set_secure_cookie()
                else:
                    yield self.authorize_redirect()

    The user object returned by `~OAuthMixin.get_authenticated_user()` includes the
    attributes ``username``, ``name``, and ``description`` in addition to
    ``access_token``. You should save the access token with the user;
    it is required to make requests on behalf of the user later with
    `friendfeed_request()`.
    """
    _OAUTH_VERSION = "1.0"
    _OAUTH_REQUEST_TOKEN_URL = "https://friendfeed.com/account/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://friendfeed.com/account/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://friendfeed.com/account/oauth/authorize"
    _OAUTH_NO_CALLBACKS = True
    _OAUTH_VERSION = "1.0"

    @_auth_return_future
    def friendfeed_request(self, path, callback, access_token=None,
                           post_args=None, **args):
        """Fetches the given relative API path, e.g., "/bret/friends"

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        All the FriendFeed methods are documented at
        http://friendfeed.com/api/documentation.

        Many methods require an OAuth access token which you can
        obtain through `~OAuthMixin.authorize_redirect` and
        `~OAuthMixin.get_authenticated_user`. The user returned
        through that process includes an ``access_token`` attribute that
        can be used to make authenticated requests via this
        method.

        Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.FriendFeedMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                @tornado.gen.coroutine
                def get(self):
                    new_entry = yield self.friendfeed_request(
                        "/entry",
                        post_args={"body": "Testing Tornado Web Server"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        yield self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        """
        # Add the OAuth resource request signature if we have credentials
        url = "http://friendfeed-api.com/v2" + path
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args:
            url += "?" + urllib_parse.urlencode(args)
        callback = self.async_callback(self._on_friendfeed_request, callback)
        http = self.get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_friendfeed_request(self, future, response):
        if response.error:
            future.set_exception(AuthError(
                "Error response %s fetching %s" % (response.error,
                                                   response.request.url)))
            return
        future.set_result(escape.json_decode(response.body))

    def _oauth_consumer_token(self):
        self.require_setting("friendfeed_consumer_key", "FriendFeed OAuth")
        self.require_setting("friendfeed_consumer_secret", "FriendFeed OAuth")
        return dict(
            key=self.settings["friendfeed_consumer_key"],
            secret=self.settings["friendfeed_consumer_secret"])

    @gen.coroutine
    def _oauth_get_user_future(self, access_token, callback):
        user = yield self.friendfeed_request(
            "/feedinfo/" + access_token["username"],
            include="id,name,description", access_token=access_token)
        if user:
            user["username"] = user["id"]
        callback(user)

    def _parse_user_response(self, callback, user):
        if user:
            user["username"] = user["id"]
        callback(user)


class GoogleMixin(OpenIdMixin, OAuthMixin):
    """Google Open ID / OAuth authentication.

    No application registration is necessary to use Google for
    authentication or to access Google resources on behalf of a user.

    Google implements both OpenID and OAuth in a hybrid mode.  If you
    just need the user's identity, use
    `~OpenIdMixin.authenticate_redirect`.  If you need to make
    requests to Google on behalf of the user, use
    `authorize_redirect`.  On return, parse the response with
    `~OpenIdMixin.get_authenticated_user`. We send a dict containing
    the values for the user, including ``email``, ``name``, and
    ``locale``.

    Example usage::

        class GoogleLoginHandler(tornado.web.RequestHandler,
                                 tornado.auth.GoogleMixin):
           @tornado.web.asynchronous
           @tornado.gen.coroutine
           def get(self):
               if self.get_argument("openid.mode", None):
                   user = yield self.get_authenticated_user()
                   # Save the user with e.g. set_secure_cookie()
               else:
                   yield self.authenticate_redirect()
    """
    _OPENID_ENDPOINT = "https://www.google.com/accounts/o8/ud"
    _OAUTH_ACCESS_TOKEN_URL = "https://www.google.com/accounts/OAuthGetAccessToken"

    @return_future
    def authorize_redirect(self, oauth_scope, callback_uri=None,
                           ax_attrs=["name", "email", "language", "username"],
                           callback=None):
        """Authenticates and authorizes for the given Google resource.

        Some of the available resources which can be used in the ``oauth_scope``
        argument are:

        * Gmail Contacts - http://www.google.com/m8/feeds/
        * Calendar - http://www.google.com/calendar/feeds/
        * Finance - http://finance.google.com/finance/feeds/

        You can authorize multiple resources by separating the resource
        URLs with a space.

        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        callback_uri = callback_uri or self.request.uri
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs,
                                 oauth_scope=oauth_scope)
        self.redirect(self._OPENID_ENDPOINT + "?" + urllib_parse.urlencode(args))
        callback()

    @_auth_return_future
    def get_authenticated_user(self, callback):
        """Fetches the authenticated user data upon redirect."""
        # Look to see if we are doing combined OpenID/OAuth
        oauth_ns = ""
        for name, values in self.request.arguments.items():
            if name.startswith("openid.ns.") and \
                    values[-1] == b"http://specs.openid.net/extensions/oauth/1.0":
                oauth_ns = name[10:]
                break
        token = self.get_argument("openid." + oauth_ns + ".request_token", "")
        if token:
            http = self.get_auth_http_client()
            token = dict(key=token, secret="")
            http.fetch(self._oauth_access_token_url(token),
                       self.async_callback(self._on_access_token, callback))
        else:
            chain_future(OpenIdMixin.get_authenticated_user(self),
                         callback)

    def _oauth_consumer_token(self):
        self.require_setting("google_consumer_key", "Google OAuth")
        self.require_setting("google_consumer_secret", "Google OAuth")
        return dict(
            key=self.settings["google_consumer_key"],
            secret=self.settings["google_consumer_secret"])

    def _oauth_get_user_future(self, access_token):
        return OpenIdMixin.get_authenticated_user(self)


class FacebookMixin(object):
    """Facebook Connect authentication.

    *Deprecated:* New applications should use `FacebookGraphMixin`
    below instead of this class.  This class does not support the
    Future-based interface seen on other classes in this module.

    To authenticate with Facebook, register your application with
    Facebook at http://www.facebook.com/developers/apps.php. Then
    copy your API Key and Application Secret to the application settings
    ``facebook_api_key`` and ``facebook_secret``.

    When your application is set up, you can use this mixin like this
    to authenticate the user with Facebook::

        class FacebookHandler(tornado.web.RequestHandler,
                              tornado.auth.FacebookMixin):
            @tornado.web.asynchronous
            def get(self):
                if self.get_argument("session", None):
                    self.get_authenticated_user(self.async_callback(self._on_auth))
                    return
                yield self.authenticate_redirect()

            def _on_auth(self, user):
                if not user:
                    raise tornado.web.HTTPError(500, "Facebook auth failed")
                # Save the user using, e.g., set_secure_cookie()

    The user object returned by `get_authenticated_user` includes the
    attributes ``facebook_uid`` and ``name`` in addition to session attributes
    like ``session_key``. You should save the session key with the user; it is
    required to make requests on behalf of the user later with
    `facebook_request`.
    """
    @return_future
    def authenticate_redirect(self, callback_uri=None, cancel_uri=None,
                              extended_permissions=None, callback=None):
        """Authenticates/installs this app for the current user.

        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        self.require_setting("facebook_api_key", "Facebook Connect")
        callback_uri = callback_uri or self.request.uri
        args = {
            "api_key": self.settings["facebook_api_key"],
            "v": "1.0",
            "fbconnect": "true",
            "display": "page",
            "next": urlparse.urljoin(self.request.full_url(), callback_uri),
            "return_session": "true",
        }
        if cancel_uri:
            args["cancel_url"] = urlparse.urljoin(
                self.request.full_url(), cancel_uri)
        if extended_permissions:
            if isinstance(extended_permissions, (unicode_type, bytes_type)):
                extended_permissions = [extended_permissions]
            args["req_perms"] = ",".join(extended_permissions)
        self.redirect("http://www.facebook.com/login.php?" +
                      urllib_parse.urlencode(args))
        callback()

    def authorize_redirect(self, extended_permissions, callback_uri=None,
                           cancel_uri=None, callback=None):
        """Redirects to an authorization request for the given FB resource.

        The available resource names are listed at
        http://wiki.developers.facebook.com/index.php/Extended_permission.
        The most common resource types include:

        * publish_stream
        * read_stream
        * email
        * sms

        extended_permissions can be a single permission name or a list of
        names. To get the session secret and session key, call
        get_authenticated_user() just as you would with
        authenticate_redirect().

        .. versionchanged:: 3.1
           Returns a `.Future` and takes an optional callback.  These are
           not strictly necessary as this method is synchronous,
           but they are supplied for consistency with
           `OAuthMixin.authorize_redirect`.
        """
        return self.authenticate_redirect(callback_uri, cancel_uri,
                                          extended_permissions,
                                          callback=callback)

    def get_authenticated_user(self, callback):
        """Fetches the authenticated Facebook user.

        The authenticated user includes the special Facebook attributes
        'session_key' and 'facebook_uid' in addition to the standard
        user attributes like 'name'.
        """
        self.require_setting("facebook_api_key", "Facebook Connect")
        session = escape.json_decode(self.get_argument("session"))
        self.facebook_request(
            method="facebook.users.getInfo",
            callback=self.async_callback(
                self._on_get_user_info, callback, session),
            session_key=session["session_key"],
            uids=session["uid"],
            fields="uid,first_name,last_name,name,locale,pic_square,"
                   "profile_url,username")

    def facebook_request(self, method, callback, **args):
        """Makes a Facebook API REST request.

        We automatically include the Facebook API key and signature, but
        it is the callers responsibility to include 'session_key' and any
        other required arguments to the method.

        The available Facebook methods are documented here:
        http://wiki.developers.facebook.com/index.php/API

        Here is an example for the stream.get() method::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.FacebookMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                def get(self):
                    self.facebook_request(
                        method="stream.get",
                        callback=self.async_callback(self._on_stream),
                        session_key=self.current_user["session_key"])

                def _on_stream(self, stream):
                    if stream is None:
                       # Not authorized to read the stream yet?
                       self.redirect(self.authorize_redirect("read_stream"))
                       return
                    self.render("stream.html", stream=stream)

        """
        self.require_setting("facebook_api_key", "Facebook Connect")
        self.require_setting("facebook_secret", "Facebook Connect")
        if not method.startswith("facebook."):
            method = "facebook." + method
        args["api_key"] = self.settings["facebook_api_key"]
        args["v"] = "1.0"
        args["method"] = method
        args["call_id"] = str(long(time.time() * 1e6))
        args["format"] = "json"
        args["sig"] = self._signature(args)
        url = "http://api.facebook.com/restserver.php?" + \
            urllib_parse.urlencode(args)
        http = self.get_auth_http_client()
        http.fetch(url, callback=self.async_callback(
            self._parse_response, callback))

    def _on_get_user_info(self, callback, session, users):
        if users is None:
            callback(None)
            return
        callback({
            "name": users[0]["name"],
            "first_name": users[0]["first_name"],
            "last_name": users[0]["last_name"],
            "uid": users[0]["uid"],
            "locale": users[0]["locale"],
            "pic_square": users[0]["pic_square"],
            "profile_url": users[0]["profile_url"],
            "username": users[0].get("username"),
            "session_key": session["session_key"],
            "session_expires": session.get("expires"),
        })

    def _parse_response(self, callback, response):
        if response.error:
            gen_log.warning("HTTP error from Facebook: %s", response.error)
            callback(None)
            return
        try:
            json = escape.json_decode(response.body)
        except Exception:
            gen_log.warning("Invalid JSON from Facebook: %r", response.body)
            callback(None)
            return
        if isinstance(json, dict) and json.get("error_code"):
            gen_log.warning("Facebook error: %d: %r", json["error_code"],
                            json.get("error_msg"))
            callback(None)
            return
        callback(json)

    def _signature(self, args):
        parts = ["%s=%s" % (n, args[n]) for n in sorted(args.keys())]
        body = "".join(parts) + self.settings["facebook_secret"]
        if isinstance(body, unicode_type):
            body = body.encode("utf-8")
        return hashlib.md5(body).hexdigest()

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class FacebookGraphMixin(OAuth2Mixin):
    """Facebook authentication using the new Graph API and OAuth2."""
    _OAUTH_ACCESS_TOKEN_URL = "https://graph.facebook.com/oauth/access_token?"
    _OAUTH_AUTHORIZE_URL = "https://graph.facebook.com/oauth/authorize?"
    _OAUTH_NO_CALLBACKS = False
    _FACEBOOK_BASE_URL = "https://graph.facebook.com"

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                               code, callback, extra_fields=None):
        """Handles the login for the Facebook user, returning a user object.

        Example usage::

            class FacebookGraphLoginHandler(LoginHandler, tornado.auth.FacebookGraphMixin):
              @tornado.web.asynchronous
              @tornado.gen.coroutine
              def get(self):
                  if self.get_argument("code", False):
                      user = yield self.get_authenticated_user(
                          redirect_uri='/auth/facebookgraph/',
                          client_id=self.settings["facebook_api_key"],
                          client_secret=self.settings["facebook_secret"],
                          code=self.get_argument("code"))
                      # Save the user with e.g. set_secure_cookie
                  else:
                      yield self.authorize_redirect(
                          redirect_uri='/auth/facebookgraph/',
                          client_id=self.settings["facebook_api_key"],
                          extra_params={"scope": "read_stream,offline_access"})
        """
        http = self.get_auth_http_client()
        args = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        fields = set(['id', 'name', 'first_name', 'last_name',
                      'locale', 'picture', 'link'])
        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._oauth_request_token_url(**args),
                   self.async_callback(self._on_access_token, redirect_uri, client_id,
                                       client_secret, callback, fields))

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         future, fields, response):
        if response.error:
            future.set_exception(AuthError('Facebook auth error: %s' % str(response)))
            return

        args = escape.parse_qs_bytes(escape.native_str(response.body))
        session = {
            "access_token": args["access_token"][-1],
            "expires": args.get("expires")
        }

        self.facebook_request(
            path="/me",
            callback=self.async_callback(
                self._on_get_user_info, future, session, fields),
            access_token=session["access_token"],
            fields=",".join(fields)
        )

    def _on_get_user_info(self, future, session, fields, user):
        if user is None:
            future.set_result(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({"access_token": session["access_token"], "session_expires": session.get("expires")})
        future.set_result(fieldmap)

    @_auth_return_future
    def facebook_request(self, path, callback, access_token=None,
                         post_args=None, **args):
        """Fetches the given relative API path, e.g., "/btaylor/picture"

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        An introduction to the Facebook Graph API can be found at
        http://developers.facebook.com/docs/api

        Many methods require an OAuth access token which you can
        obtain through `~OAuth2Mixin.authorize_redirect` and
        `get_authenticated_user`. The user returned through that
        process includes an ``access_token`` attribute that can be
        used to make authenticated requests via this method.

        Example usage::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.FacebookGraphMixin):
                @tornado.web.authenticated
                @tornado.web.asynchronous
                @tornado.gen.coroutine
                def get(self):
                    new_entry = yield self.facebook_request(
                        "/me/feed",
                        post_args={"message": "I am posting from my Tornado application!"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        yield self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        The given path is relative to ``self._FACEBOOK_BASE_URL``,
        by default "https://graph.facebook.com".

        .. versionchanged:: 3.1
           Added the ability to override ``self._FACEBOOK_BASE_URL``.
        """
        url = self._FACEBOOK_BASE_URL + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(args)

        if all_args:
            url += "?" + urllib_parse.urlencode(all_args)
        callback = self.async_callback(self._on_facebook_request, callback)
        http = self.get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_facebook_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("Error response %s fetching %s" %
                                           (response.error, response.request.url)))
            return

        future.set_result(escape.json_decode(response.body))

    def get_auth_http_client(self):
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


def _oauth_signature(consumer_token, method, url, parameters={}, token=None):
    """Calculates the HMAC-SHA1 OAuth signature for the given request.

    See http://oauth.net/core/1.0/#signing_process
    """
    parts = urlparse.urlparse(url)
    scheme, netloc, path = parts[:3]
    normalized_url = scheme.lower() + "://" + netloc.lower() + path

    base_elems = []
    base_elems.append(method.upper())
    base_elems.append(normalized_url)
    base_elems.append("&".join("%s=%s" % (k, _oauth_escape(str(v)))
                               for k, v in sorted(parameters.items())))
    base_string = "&".join(_oauth_escape(e) for e in base_elems)

    key_elems = [escape.utf8(consumer_token["secret"])]
    key_elems.append(escape.utf8(token["secret"] if token else ""))
    key = b"&".join(key_elems)

    hash = hmac.new(key, escape.utf8(base_string), hashlib.sha1)
    return binascii.b2a_base64(hash.digest())[:-1]


def _oauth10a_signature(consumer_token, method, url, parameters={}, token=None):
    """Calculates the HMAC-SHA1 OAuth 1.0a signature for the given request.

    See http://oauth.net/core/1.0a/#signing_process
    """
    parts = urlparse.urlparse(url)
    scheme, netloc, path = parts[:3]
    normalized_url = scheme.lower() + "://" + netloc.lower() + path

    base_elems = []
    base_elems.append(method.upper())
    base_elems.append(normalized_url)
    base_elems.append("&".join("%s=%s" % (k, _oauth_escape(str(v)))
                               for k, v in sorted(parameters.items())))

    base_string = "&".join(_oauth_escape(e) for e in base_elems)
    key_elems = [escape.utf8(urllib_parse.quote(consumer_token["secret"], safe='~'))]
    key_elems.append(escape.utf8(urllib_parse.quote(token["secret"], safe='~') if token else ""))
    key = b"&".join(key_elems)

    hash = hmac.new(key, escape.utf8(base_string), hashlib.sha1)
    return binascii.b2a_base64(hash.digest())[:-1]


def _oauth_escape(val):
    if isinstance(val, unicode_type):
        val = val.encode("utf-8")
    return urllib_parse.quote(val, safe="~")


def _oauth_parse_response(body):
    # I can't find an officially-defined encoding for oauth responses and
    # have never seen anyone use non-ascii.  Leave the response in a byte
    # string for python 2, and use utf8 on python 3.
    body = escape.native_str(body)
    p = urlparse.parse_qs(body, keep_blank_values=False)
    token = dict(key=p["oauth_token"][0], secret=p["oauth_token_secret"][0])

    # Add the extra parameters the Provider included to the token
    special = ("oauth_token", "oauth_token_secret")
    token.update((k, p[k][0]) for k in p if k not in special)
    return token

########NEW FILE########
__FILENAME__ = autoreload
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""xAutomatically restart the server when a source file is modified.

Most applications should not access this module directly.  Instead, pass the
keyword argument ``debug=True`` to the `tornado.web.Application` constructor.
This will enable autoreload mode as well as checking for changes to templates
and static resources.  Note that restarting is a destructive operation
and any requests in progress will be aborted when the process restarts.

This module can also be used as a command-line wrapper around scripts
such as unit test runners.  See the `main` method for details.

The command-line wrapper and Application debug modes can be used together.
This combination is encouraged as the wrapper catches syntax errors and
other import-time failures, while debug mode catches changes once
the server has started.

This module depends on `.IOLoop`, so it will not work in WSGI applications
and Google App Engine.  It also will not work correctly when `.HTTPServer`'s
multi-process mode is used.

Reloading loses any Python interpreter command-line arguments (e.g. ``-u``)
because it re-executes Python using ``sys.executable`` and ``sys.argv``.
Additionally, modifying these variables will cause reloading to behave
incorrectly.
"""

from __future__ import absolute_import, division, print_function, with_statement

import os
import sys

# sys.path handling
# -----------------
#
# If a module is run with "python -m", the current directory (i.e. "")
# is automatically prepended to sys.path, but not if it is run as
# "path/to/file.py".  The processing for "-m" rewrites the former to
# the latter, so subsequent executions won't have the same path as the
# original.
#
# Conversely, when run as path/to/file.py, the directory containing
# file.py gets added to the path, which can cause confusion as imports
# may become relative in spite of the future import.
#
# We address the former problem by setting the $PYTHONPATH environment
# variable before re-execution so the new process will see the correct
# path.  We attempt to address the latter problem when tornado.autoreload
# is run as __main__, although we can't fix the general case because
# we cannot reliably reconstruct the original command line
# (http://bugs.python.org/issue14208).

if __name__ == "__main__":
    # This sys.path manipulation must come before our imports (as much
    # as possible - if we introduced a tornado.sys or tornado.os
    # module we'd be in trouble), or else our imports would become
    # relative again despite the future import.
    #
    # There is a separate __main__ block at the end of the file to call main().
    if sys.path[0] == os.path.dirname(__file__):
        del sys.path[0]

import functools
import logging
import os
import pkgutil
import sys
import traceback
import types
import subprocess
import weakref

from tornado import ioloop
from tornado.log import gen_log
from tornado import process
from tornado.util import exec_in

try:
    import signal
except ImportError:
    signal = None


_watched_files = set()
_reload_hooks = []
_reload_attempted = False
_io_loops = weakref.WeakKeyDictionary()


def start(io_loop=None, check_time=500):
    """Begins watching source files for changes using the given `.IOLoop`. """
    io_loop = io_loop or ioloop.IOLoop.current()
    if io_loop in _io_loops:
        return
    _io_loops[io_loop] = True
    if len(_io_loops) > 1:
        gen_log.warning("tornado.autoreload started more than once in the same process")
    add_reload_hook(functools.partial(io_loop.close, all_fds=True))
    modify_times = {}
    callback = functools.partial(_reload_on_update, modify_times)
    scheduler = ioloop.PeriodicCallback(callback, check_time, io_loop=io_loop)
    scheduler.start()


def wait():
    """Wait for a watched file to change, then restart the process.

    Intended to be used at the end of scripts like unit test runners,
    to run the tests again after any source file changes (but see also
    the command-line interface in `main`)
    """
    io_loop = ioloop.IOLoop()
    start(io_loop)
    io_loop.start()


def watch(filename):
    """Add a file to the watch list.

    All imported modules are watched by default.
    """
    _watched_files.add(filename)


def add_reload_hook(fn):
    """Add a function to be called before reloading the process.

    Note that for open file and socket handles it is generally
    preferable to set the ``FD_CLOEXEC`` flag (using `fcntl` or
    ``tornado.platform.auto.set_close_exec``) instead
    of using a reload hook to close them.
    """
    _reload_hooks.append(fn)


def _reload_on_update(modify_times):
    if _reload_attempted:
        # We already tried to reload and it didn't work, so don't try again.
        return
    if process.task_id() is not None:
        # We're in a child process created by fork_processes.  If child
        # processes restarted themselves, they'd all restart and then
        # all call fork_processes again.
        return
    for module in sys.modules.values():
        # Some modules play games with sys.modules (e.g. email/__init__.py
        # in the standard library), and occasionally this can cause strange
        # failures in getattr.  Just ignore anything that's not an ordinary
        # module.
        if not isinstance(module, types.ModuleType):
            continue
        path = getattr(module, "__file__", None)
        if not path:
            continue
        if path.endswith(".pyc") or path.endswith(".pyo"):
            path = path[:-1]
        _check_file(modify_times, path)
    for path in _watched_files:
        _check_file(modify_times, path)


def _check_file(modify_times, path):
    try:
        modified = os.stat(path).st_mtime
    except Exception:
        return
    if path not in modify_times:
        modify_times[path] = modified
        return
    if modify_times[path] != modified:
        gen_log.info("%s modified; restarting server", path)
        _reload()


def _reload():
    global _reload_attempted
    _reload_attempted = True
    for fn in _reload_hooks:
        fn()
    if hasattr(signal, "setitimer"):
        # Clear the alarm signal set by
        # ioloop.set_blocking_log_threshold so it doesn't fire
        # after the exec.
        signal.setitimer(signal.ITIMER_REAL, 0, 0)
    # sys.path fixes: see comments at top of file.  If sys.path[0] is an empty
    # string, we were (probably) invoked with -m and the effective path
    # is about to change on re-exec.  Add the current directory to $PYTHONPATH
    # to ensure that the new process sees the same path we did.
    path_prefix = '.' + os.pathsep
    if (sys.path[0] == '' and
            not os.environ.get("PYTHONPATH", "").startswith(path_prefix)):
        os.environ["PYTHONPATH"] = (path_prefix +
                                    os.environ.get("PYTHONPATH", ""))
    if sys.platform == 'win32':
        # os.execv is broken on Windows and can't properly parse command line
        # arguments and executable name if they contain whitespaces. subprocess
        # fixes that behavior.
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
    else:
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError:
            # Mac OS X versions prior to 10.6 do not support execv in
            # a process that contains multiple threads.  Instead of
            # re-executing in the current process, start a new one
            # and cause the current process to exit.  This isn't
            # ideal since the new process is detached from the parent
            # terminal and thus cannot easily be killed with ctrl-C,
            # but it's better than not being able to autoreload at
            # all.
            # Unfortunately the errno returned in this case does not
            # appear to be consistent, so we can't easily check for
            # this error specifically.
            os.spawnv(os.P_NOWAIT, sys.executable,
                      [sys.executable] + sys.argv)
            sys.exit(0)

_USAGE = """\
Usage:
  python -m tornado.autoreload -m module.to.run [args...]
  python -m tornado.autoreload path/to/script.py [args...]
"""


def main():
    """Command-line wrapper to re-run a script whenever its source changes.

    Scripts may be specified by filename or module name::

        python -m tornado.autoreload -m tornado.test.runtests
        python -m tornado.autoreload tornado/test/runtests.py

    Running a script with this wrapper is similar to calling
    `tornado.autoreload.wait` at the end of the script, but this wrapper
    can catch import-time problems like syntax errors that would otherwise
    prevent the script from reaching its call to `wait`.
    """
    original_argv = sys.argv
    sys.argv = sys.argv[:]
    if len(sys.argv) >= 3 and sys.argv[1] == "-m":
        mode = "module"
        module = sys.argv[2]
        del sys.argv[1:3]
    elif len(sys.argv) >= 2:
        mode = "script"
        script = sys.argv[1]
        sys.argv = sys.argv[1:]
    else:
        print(_USAGE, file=sys.stderr)
        sys.exit(1)

    try:
        if mode == "module":
            import runpy
            runpy.run_module(module, run_name="__main__", alter_sys=True)
        elif mode == "script":
            with open(script) as f:
                global __file__
                __file__ = script
                # Use globals as our "locals" dictionary so that
                # something that tries to import __main__ (e.g. the unittest
                # module) will see the right things.
                exec_in(f.read(), globals(), globals())
    except SystemExit as e:
        logging.basicConfig()
        gen_log.info("Script exited with status %s", e.code)
    except Exception as e:
        logging.basicConfig()
        gen_log.warning("Script exited with uncaught exception", exc_info=True)
        # If an exception occurred at import time, the file with the error
        # never made it into sys.modules and so we won't know to watch it.
        # Just to make sure we've covered everything, walk the stack trace
        # from the exception and watch every file.
        for (filename, lineno, name, line) in traceback.extract_tb(sys.exc_info()[2]):
            watch(filename)
        if isinstance(e, SyntaxError):
            # SyntaxErrors are special:  their innermost stack frame is fake
            # so extract_tb won't see it and we have to get the filename
            # from the exception object.
            watch(e.filename)
    else:
        logging.basicConfig()
        gen_log.info("Script exited normally")
    # restore sys.argv so subsequent executions will include autoreload
    sys.argv = original_argv

    if mode == 'module':
        # runpy did a fake import of the module as __main__, but now it's
        # no longer in sys.modules.  Figure out where it is and watch it.
        loader = pkgutil.get_loader(module)
        if loader is not None:
            watch(loader.get_filename())

    wait()


if __name__ == "__main__":
    # See also the other __main__ block at the top of the file, which modifies
    # sys.path before our imports
    main()

########NEW FILE########
__FILENAME__ = concurrent
#!/usr/bin/env python
#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Utilities for working with threads and ``Futures``.

``Futures`` are a pattern for concurrent programming introduced in
Python 3.2 in the `concurrent.futures` package (this package has also
been backported to older versions of Python and can be installed with
``pip install futures``).  Tornado will use `concurrent.futures.Future` if
it is available; otherwise it will use a compatible class defined in this
module.
"""
from __future__ import absolute_import, division, print_function, with_statement

import functools
import sys

from tornado.stack_context import ExceptionStackContext, wrap
from tornado.util import raise_exc_info, ArgReplacer

try:
    from concurrent import futures
except ImportError:
    futures = None


class ReturnValueIgnoredError(Exception):
    pass


class _DummyFuture(object):
    def __init__(self):
        self._done = False
        self._result = None
        self._exception = None
        self._callbacks = []

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return not self._done

    def done(self):
        return self._done

    def result(self, timeout=None):
        self._check_done()
        if self._exception:
            raise self._exception
        return self._result

    def exception(self, timeout=None):
        self._check_done()
        if self._exception:
            return self._exception
        else:
            return None

    def add_done_callback(self, fn):
        if self._done:
            fn(self)
        else:
            self._callbacks.append(fn)

    def set_result(self, result):
        self._result = result
        self._set_done()

    def set_exception(self, exception):
        self._exception = exception
        self._set_done()

    def _check_done(self):
        if not self._done:
            raise Exception("DummyFuture does not support blocking for results")

    def _set_done(self):
        self._done = True
        for cb in self._callbacks:
            # TODO: error handling
            cb(self)
        self._callbacks = None

if futures is None:
    Future = _DummyFuture
else:
    Future = futures.Future


class TracebackFuture(Future):
    """Subclass of `Future` which can store a traceback with
    exceptions.

    The traceback is automatically available in Python 3, but in the
    Python 2 futures backport this information is discarded.
    """
    def __init__(self):
        super(TracebackFuture, self).__init__()
        self.__exc_info = None

    def exc_info(self):
        return self.__exc_info

    def set_exc_info(self, exc_info):
        """Traceback-aware replacement for
        `~concurrent.futures.Future.set_exception`.
        """
        self.__exc_info = exc_info
        self.set_exception(exc_info[1])

    def result(self):
        if self.__exc_info is not None:
            raise_exc_info(self.__exc_info)
        else:
            return super(TracebackFuture, self).result()


class DummyExecutor(object):
    def submit(self, fn, *args, **kwargs):
        future = TracebackFuture()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception:
            future.set_exc_info(sys.exc_info())
        return future

    def shutdown(self, wait=True):
        pass

dummy_executor = DummyExecutor()


def run_on_executor(fn):
    """Decorator to run a synchronous method asynchronously on an executor.

    The decorated method may be called with a ``callback`` keyword
    argument and returns a future.
    """
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        callback = kwargs.pop("callback", None)
        future = self.executor.submit(fn, self, *args, **kwargs)
        if callback:
            self.io_loop.add_future(future,
                                    lambda future: callback(future.result()))
        return future
    return wrapper


_NO_RESULT = object()


def return_future(f):
    """Decorator to make a function that returns via callback return a
    `Future`.

    The wrapped function should take a ``callback`` keyword argument
    and invoke it with one argument when it has finished.  To signal failure,
    the function can simply raise an exception (which will be
    captured by the `.StackContext` and passed along to the ``Future``).

    From the caller's perspective, the callback argument is optional.
    If one is given, it will be invoked when the function is complete
    with `Future.result()` as an argument.  If the function fails, the
    callback will not be run and an exception will be raised into the
    surrounding `.StackContext`.

    If no callback is given, the caller should use the ``Future`` to
    wait for the function to complete (perhaps by yielding it in a
    `.gen.engine` function, or passing it to `.IOLoop.add_future`).

    Usage::

        @return_future
        def future_func(arg1, arg2, callback):
            # Do stuff (possibly asynchronous)
            callback(result)

        @gen.engine
        def caller(callback):
            yield future_func(arg1, arg2)
            callback()

    Note that ``@return_future`` and ``@gen.engine`` can be applied to the
    same function, provided ``@return_future`` appears first.  However,
    consider using ``@gen.coroutine`` instead of this combination.
    """
    replacer = ArgReplacer(f, 'callback')

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        future = TracebackFuture()
        callback, args, kwargs = replacer.replace(
            lambda value=_NO_RESULT: future.set_result(value),
            args, kwargs)

        def handle_error(typ, value, tb):
            future.set_exc_info((typ, value, tb))
            return True
        exc_info = None
        with ExceptionStackContext(handle_error):
            try:
                result = f(*args, **kwargs)
                if result is not None:
                    raise ReturnValueIgnoredError(
                        "@return_future should not be used with functions "
                        "that return values")
            except:
                exc_info = sys.exc_info()
                raise
        if exc_info is not None:
            # If the initial synchronous part of f() raised an exception,
            # go ahead and raise it to the caller directly without waiting
            # for them to inspect the Future.
            raise_exc_info(exc_info)

        # If the caller passed in a callback, schedule it to be called
        # when the future resolves.  It is important that this happens
        # just before we return the future, or else we risk confusing
        # stack contexts with multiple exceptions (one here with the
        # immediate exception, and again when the future resolves and
        # the callback triggers its exception by calling future.result()).
        if callback is not None:
            def run_callback(future):
                result = future.result()
                if result is _NO_RESULT:
                    callback()
                else:
                    callback(future.result())
            future.add_done_callback(wrap(run_callback))
        return future
    return wrapper


def chain_future(a, b):
    """Chain two futures together so that when one completes, so does the other.

    The result (success or failure) of ``a`` will be copied to ``b``.
    """
    def copy(future):
        assert future is a
        if (isinstance(a, TracebackFuture) and isinstance(b, TracebackFuture)
                and a.exc_info() is not None):
            b.set_exc_info(a.exc_info())
        elif a.exception() is not None:
            b.set_exception(a.exception())
        else:
            b.set_result(a.result())
    a.add_done_callback(copy)

########NEW FILE########
__FILENAME__ = curl_httpclient
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Non-blocking HTTP client implementation using pycurl."""

from __future__ import absolute_import, division, print_function, with_statement

import collections
import logging
import pycurl
import threading
import time

from tornado import httputil
from tornado import ioloop
from tornado.log import gen_log
from tornado import stack_context

from tornado.escape import utf8, native_str
from tornado.httpclient import HTTPResponse, HTTPError, AsyncHTTPClient, main
from tornado.util import bytes_type

try:
    from io import BytesIO  # py3
except ImportError:
    from cStringIO import StringIO as BytesIO  # py2


class CurlAsyncHTTPClient(AsyncHTTPClient):
    def initialize(self, io_loop, max_clients=10, defaults=None):
        super(CurlAsyncHTTPClient, self).initialize(io_loop, defaults=defaults)
        self._multi = pycurl.CurlMulti()
        self._multi.setopt(pycurl.M_TIMERFUNCTION, self._set_timeout)
        self._multi.setopt(pycurl.M_SOCKETFUNCTION, self._handle_socket)
        self._curls = [_curl_create() for i in range(max_clients)]
        self._free_list = self._curls[:]
        self._requests = collections.deque()
        self._fds = {}
        self._timeout = None

        try:
            self._socket_action = self._multi.socket_action
        except AttributeError:
            # socket_action is found in pycurl since 7.18.2 (it's been
            # in libcurl longer than that but wasn't accessible to
            # python).
            gen_log.warning("socket_action method missing from pycurl; "
                            "falling back to socket_all. Upgrading "
                            "libcurl and pycurl will improve performance")
            self._socket_action = \
                lambda fd, action: self._multi.socket_all()

        # libcurl has bugs that sometimes cause it to not report all
        # relevant file descriptors and timeouts to TIMERFUNCTION/
        # SOCKETFUNCTION.  Mitigate the effects of such bugs by
        # forcing a periodic scan of all active requests.
        self._force_timeout_callback = ioloop.PeriodicCallback(
            self._handle_force_timeout, 1000, io_loop=io_loop)
        self._force_timeout_callback.start()

        # Work around a bug in libcurl 7.29.0: Some fields in the curl
        # multi object are initialized lazily, and its destructor will
        # segfault if it is destroyed without having been used.  Add
        # and remove a dummy handle to make sure everything is
        # initialized.
        dummy_curl_handle = pycurl.Curl()
        self._multi.add_handle(dummy_curl_handle)
        self._multi.remove_handle(dummy_curl_handle)

    def close(self):
        self._force_timeout_callback.stop()
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
        for curl in self._curls:
            curl.close()
        self._multi.close()
        self._closed = True
        super(CurlAsyncHTTPClient, self).close()

    def fetch_impl(self, request, callback):
        self._requests.append((request, callback))
        self._process_queue()
        self._set_timeout(0)

    def _handle_socket(self, event, fd, multi, data):
        """Called by libcurl when it wants to change the file descriptors
        it cares about.
        """
        event_map = {
            pycurl.POLL_NONE: ioloop.IOLoop.NONE,
            pycurl.POLL_IN: ioloop.IOLoop.READ,
            pycurl.POLL_OUT: ioloop.IOLoop.WRITE,
            pycurl.POLL_INOUT: ioloop.IOLoop.READ | ioloop.IOLoop.WRITE
        }
        if event == pycurl.POLL_REMOVE:
            if fd in self._fds:
                self.io_loop.remove_handler(fd)
                del self._fds[fd]
        else:
            ioloop_event = event_map[event]
            # libcurl sometimes closes a socket and then opens a new
            # one using the same FD without giving us a POLL_NONE in
            # between.  This is a problem with the epoll IOLoop,
            # because the kernel can tell when a socket is closed and
            # removes it from the epoll automatically, causing future
            # update_handler calls to fail.  Since we can't tell when
            # this has happened, always use remove and re-add
            # instead of update.
            if fd in self._fds:
                self.io_loop.remove_handler(fd)
            self.io_loop.add_handler(fd, self._handle_events,
                                     ioloop_event)
            self._fds[fd] = ioloop_event

    def _set_timeout(self, msecs):
        """Called by libcurl to schedule a timeout."""
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
        self._timeout = self.io_loop.add_timeout(
            self.io_loop.time() + msecs / 1000.0, self._handle_timeout)

    def _handle_events(self, fd, events):
        """Called by IOLoop when there is activity on one of our
        file descriptors.
        """
        action = 0
        if events & ioloop.IOLoop.READ:
            action |= pycurl.CSELECT_IN
        if events & ioloop.IOLoop.WRITE:
            action |= pycurl.CSELECT_OUT
        while True:
            try:
                ret, num_handles = self._socket_action(fd, action)
            except pycurl.error as e:
                ret = e.args[0]
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break
        self._finish_pending_requests()

    def _handle_timeout(self):
        """Called by IOLoop when the requested timeout has passed."""
        with stack_context.NullContext():
            self._timeout = None
            while True:
                try:
                    ret, num_handles = self._socket_action(
                        pycurl.SOCKET_TIMEOUT, 0)
                except pycurl.error as e:
                    ret = e.args[0]
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break
            self._finish_pending_requests()

        # In theory, we shouldn't have to do this because curl will
        # call _set_timeout whenever the timeout changes.  However,
        # sometimes after _handle_timeout we will need to reschedule
        # immediately even though nothing has changed from curl's
        # perspective.  This is because when socket_action is
        # called with SOCKET_TIMEOUT, libcurl decides internally which
        # timeouts need to be processed by using a monotonic clock
        # (where available) while tornado uses python's time.time()
        # to decide when timeouts have occurred.  When those clocks
        # disagree on elapsed time (as they will whenever there is an
        # NTP adjustment), tornado might call _handle_timeout before
        # libcurl is ready.  After each timeout, resync the scheduled
        # timeout with libcurl's current state.
        new_timeout = self._multi.timeout()
        if new_timeout >= 0:
            self._set_timeout(new_timeout)

    def _handle_force_timeout(self):
        """Called by IOLoop periodically to ask libcurl to process any
        events it may have forgotten about.
        """
        with stack_context.NullContext():
            while True:
                try:
                    ret, num_handles = self._multi.socket_all()
                except pycurl.error as e:
                    ret = e.args[0]
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break
            self._finish_pending_requests()

    def _finish_pending_requests(self):
        """Process any requests that were completed by the last
        call to multi.socket_action.
        """
        while True:
            num_q, ok_list, err_list = self._multi.info_read()
            for curl in ok_list:
                self._finish(curl)
            for curl, errnum, errmsg in err_list:
                self._finish(curl, errnum, errmsg)
            if num_q == 0:
                break
        self._process_queue()

    def _process_queue(self):
        with stack_context.NullContext():
            while True:
                started = 0
                while self._free_list and self._requests:
                    started += 1
                    curl = self._free_list.pop()
                    (request, callback) = self._requests.popleft()
                    curl.info = {
                        "headers": httputil.HTTPHeaders(),
                        "buffer": BytesIO(),
                        "request": request,
                        "callback": callback,
                        "curl_start_time": time.time(),
                    }
                    # Disable IPv6 to mitigate the effects of this bug
                    # on curl versions <= 7.21.0
                    # http://sourceforge.net/tracker/?func=detail&aid=3017819&group_id=976&atid=100976
                    if pycurl.version_info()[2] <= 0x71500:  # 7.21.0
                        curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)
                    _curl_setup_request(curl, request, curl.info["buffer"],
                                        curl.info["headers"])
                    self._multi.add_handle(curl)

                if not started:
                    break

    def _finish(self, curl, curl_error=None, curl_message=None):
        info = curl.info
        curl.info = None
        self._multi.remove_handle(curl)
        self._free_list.append(curl)
        buffer = info["buffer"]
        if curl_error:
            error = CurlError(curl_error, curl_message)
            code = error.code
            effective_url = None
            buffer.close()
            buffer = None
        else:
            error = None
            code = curl.getinfo(pycurl.HTTP_CODE)
            effective_url = curl.getinfo(pycurl.EFFECTIVE_URL)
            buffer.seek(0)
        # the various curl timings are documented at
        # http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
        time_info = dict(
            queue=info["curl_start_time"] - info["request"].start_time,
            namelookup=curl.getinfo(pycurl.NAMELOOKUP_TIME),
            connect=curl.getinfo(pycurl.CONNECT_TIME),
            pretransfer=curl.getinfo(pycurl.PRETRANSFER_TIME),
            starttransfer=curl.getinfo(pycurl.STARTTRANSFER_TIME),
            total=curl.getinfo(pycurl.TOTAL_TIME),
            redirect=curl.getinfo(pycurl.REDIRECT_TIME),
        )
        try:
            info["callback"](HTTPResponse(
                request=info["request"], code=code, headers=info["headers"],
                buffer=buffer, effective_url=effective_url, error=error,
                request_time=time.time() - info["curl_start_time"],
                time_info=time_info))
        except Exception:
            self.handle_callback_exception(info["callback"])

    def handle_callback_exception(self, callback):
        self.io_loop.handle_callback_exception(callback)


class CurlError(HTTPError):
    def __init__(self, errno, message):
        HTTPError.__init__(self, 599, message)
        self.errno = errno


def _curl_create():
    curl = pycurl.Curl()
    if gen_log.isEnabledFor(logging.DEBUG):
        curl.setopt(pycurl.VERBOSE, 1)
        curl.setopt(pycurl.DEBUGFUNCTION, _curl_debug)
    return curl


def _curl_setup_request(curl, request, buffer, headers):
    curl.setopt(pycurl.URL, native_str(request.url))

    # libcurl's magic "Expect: 100-continue" behavior causes delays
    # with servers that don't support it (which include, among others,
    # Google's OpenID endpoint).  Additionally, this behavior has
    # a bug in conjunction with the curl_multi_socket_action API
    # (https://sourceforge.net/tracker/?func=detail&atid=100976&aid=3039744&group_id=976),
    # which increases the delays.  It's more trouble than it's worth,
    # so just turn off the feature (yes, setting Expect: to an empty
    # value is the official way to disable this)
    if "Expect" not in request.headers:
        request.headers["Expect"] = ""

    # libcurl adds Pragma: no-cache by default; disable that too
    if "Pragma" not in request.headers:
        request.headers["Pragma"] = ""

    # Request headers may be either a regular dict or HTTPHeaders object
    if isinstance(request.headers, httputil.HTTPHeaders):
        curl.setopt(pycurl.HTTPHEADER,
                    [native_str("%s: %s" % i) for i in request.headers.get_all()])
    else:
        curl.setopt(pycurl.HTTPHEADER,
                    [native_str("%s: %s" % i) for i in request.headers.items()])

    if request.header_callback:
        curl.setopt(pycurl.HEADERFUNCTION, request.header_callback)
    else:
        curl.setopt(pycurl.HEADERFUNCTION,
                    lambda line: _curl_header_callback(headers, line))
    if request.streaming_callback:
        write_function = request.streaming_callback
    else:
        write_function = buffer.write
    if bytes_type is str:  # py2
        curl.setopt(pycurl.WRITEFUNCTION, write_function)
    else:  # py3
        # Upstream pycurl doesn't support py3, but ubuntu 12.10 includes
        # a fork/port.  That version has a bug in which it passes unicode
        # strings instead of bytes to the WRITEFUNCTION.  This means that
        # if you use a WRITEFUNCTION (which tornado always does), you cannot
        # download arbitrary binary data.  This needs to be fixed in the
        # ported pycurl package, but in the meantime this lambda will
        # make it work for downloading (utf8) text.
        curl.setopt(pycurl.WRITEFUNCTION, lambda s: write_function(utf8(s)))
    curl.setopt(pycurl.FOLLOWLOCATION, request.follow_redirects)
    curl.setopt(pycurl.MAXREDIRS, request.max_redirects)
    curl.setopt(pycurl.CONNECTTIMEOUT_MS, int(1000 * request.connect_timeout))
    curl.setopt(pycurl.TIMEOUT_MS, int(1000 * request.request_timeout))
    if request.user_agent:
        curl.setopt(pycurl.USERAGENT, native_str(request.user_agent))
    else:
        curl.setopt(pycurl.USERAGENT, "Mozilla/5.0 (compatible; pycurl)")
    if request.network_interface:
        curl.setopt(pycurl.INTERFACE, request.network_interface)
    if request.use_gzip:
        curl.setopt(pycurl.ENCODING, "gzip,deflate")
    else:
        curl.setopt(pycurl.ENCODING, "none")
    if request.proxy_host and request.proxy_port:
        curl.setopt(pycurl.PROXY, request.proxy_host)
        curl.setopt(pycurl.PROXYPORT, request.proxy_port)
        if request.proxy_username:
            credentials = '%s:%s' % (request.proxy_username,
                                     request.proxy_password)
            curl.setopt(pycurl.PROXYUSERPWD, credentials)
    else:
        curl.setopt(pycurl.PROXY, '')
    if request.validate_cert:
        curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        curl.setopt(pycurl.SSL_VERIFYHOST, 2)
    else:
        curl.setopt(pycurl.SSL_VERIFYPEER, 0)
        curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    if request.ca_certs is not None:
        curl.setopt(pycurl.CAINFO, request.ca_certs)
    else:
        # There is no way to restore pycurl.CAINFO to its default value
        # (Using unsetopt makes it reject all certificates).
        # I don't see any way to read the default value from python so it
        # can be restored later.  We'll have to just leave CAINFO untouched
        # if no ca_certs file was specified, and require that if any
        # request uses a custom ca_certs file, they all must.
        pass

    if request.allow_ipv6 is False:
        # Curl behaves reasonably when DNS resolution gives an ipv6 address
        # that we can't reach, so allow ipv6 unless the user asks to disable.
        # (but see version check in _process_queue above)
        curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)

    # Set the request method through curl's irritating interface which makes
    # up names for almost every single method
    curl_options = {
        "GET": pycurl.HTTPGET,
        "POST": pycurl.POST,
        "PUT": pycurl.UPLOAD,
        "HEAD": pycurl.NOBODY,
    }
    custom_methods = set(["DELETE", "OPTIONS", "PATCH"])
    for o in curl_options.values():
        curl.setopt(o, False)
    if request.method in curl_options:
        curl.unsetopt(pycurl.CUSTOMREQUEST)
        curl.setopt(curl_options[request.method], True)
    elif request.allow_nonstandard_methods or request.method in custom_methods:
        curl.setopt(pycurl.CUSTOMREQUEST, request.method)
    else:
        raise KeyError('unknown method ' + request.method)

    # Handle curl's cryptic options for every individual HTTP method
    if request.method in ("POST", "PUT"):
        request_buffer = BytesIO(utf8(request.body))
        curl.setopt(pycurl.READFUNCTION, request_buffer.read)
        if request.method == "POST":
            def ioctl(cmd):
                if cmd == curl.IOCMD_RESTARTREAD:
                    request_buffer.seek(0)
            curl.setopt(pycurl.IOCTLFUNCTION, ioctl)
            curl.setopt(pycurl.POSTFIELDSIZE, len(request.body))
        else:
            curl.setopt(pycurl.INFILESIZE, len(request.body))

    if request.auth_username is not None:
        userpwd = "%s:%s" % (request.auth_username, request.auth_password or '')

        if request.auth_mode is None or request.auth_mode == "basic":
            curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
        elif request.auth_mode == "digest":
            curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
        else:
            raise ValueError("Unsupported auth_mode %s" % request.auth_mode)

        curl.setopt(pycurl.USERPWD, native_str(userpwd))
        gen_log.debug("%s %s (username: %r)", request.method, request.url,
                      request.auth_username)
    else:
        curl.unsetopt(pycurl.USERPWD)
        gen_log.debug("%s %s", request.method, request.url)

    if request.client_cert is not None:
        curl.setopt(pycurl.SSLCERT, request.client_cert)

    if request.client_key is not None:
        curl.setopt(pycurl.SSLKEY, request.client_key)

    if threading.activeCount() > 1:
        # libcurl/pycurl is not thread-safe by default.  When multiple threads
        # are used, signals should be disabled.  This has the side effect
        # of disabling DNS timeouts in some environments (when libcurl is
        # not linked against ares), so we don't do it when there is only one
        # thread.  Applications that use many short-lived threads may need
        # to set NOSIGNAL manually in a prepare_curl_callback since
        # there may not be any other threads running at the time we call
        # threading.activeCount.
        curl.setopt(pycurl.NOSIGNAL, 1)
    if request.prepare_curl_callback is not None:
        request.prepare_curl_callback(curl)


def _curl_header_callback(headers, header_line):
    # header_line as returned by curl includes the end-of-line characters.
    header_line = header_line.strip()
    if header_line.startswith("HTTP/"):
        headers.clear()
        return
    if not header_line:
        return
    headers.parse_line(header_line)


def _curl_debug(debug_type, debug_msg):
    debug_types = ('I', '<', '>', '<', '>')
    if debug_type == 0:
        gen_log.debug('%s', debug_msg.strip())
    elif debug_type in (1, 2):
        for line in debug_msg.splitlines():
            gen_log.debug('%s %s', debug_types[debug_type], line)
    elif debug_type == 4:
        gen_log.debug('%s %r', debug_types[debug_type], debug_msg)

if __name__ == "__main__":
    AsyncHTTPClient.configure(CurlAsyncHTTPClient)
    main()

########NEW FILE########
__FILENAME__ = escape
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Escaping/unescaping methods for HTML, JSON, URLs, and others.

Also includes a few other miscellaneous string manipulation functions that
have crept in over time.
"""

from __future__ import absolute_import, division, print_function, with_statement

import re
import sys

from tornado.util import bytes_type, unicode_type, basestring_type, u

try:
    from urllib.parse import parse_qs as _parse_qs  # py3
except ImportError:
    from urlparse import parse_qs as _parse_qs  # Python 2.6+

try:
    import htmlentitydefs  # py2
except ImportError:
    import html.entities as htmlentitydefs  # py3

try:
    import urllib.parse as urllib_parse  # py3
except ImportError:
    import urllib as urllib_parse  # py2

import json

try:
    unichr
except NameError:
    unichr = chr

_XHTML_ESCAPE_RE = re.compile('[&<>"]')
_XHTML_ESCAPE_DICT = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}


def xhtml_escape(value):
    """Escapes a string so it is valid within HTML or XML."""
    return _XHTML_ESCAPE_RE.sub(lambda match: _XHTML_ESCAPE_DICT[match.group(0)],
                                to_basestring(value))


def xhtml_unescape(value):
    """Un-escapes an XML-escaped string."""
    return re.sub(r"&(#?)(\w+?);", _convert_entity, _unicode(value))


# The fact that json_encode wraps json.dumps is an implementation detail.
# Please see https://github.com/facebook/tornado/pull/706
# before sending a pull request that adds **kwargs to this function.
def json_encode(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps(value).replace("</", "<\\/")


def json_decode(value):
    """Returns Python objects for the given JSON string."""
    return json.loads(to_basestring(value))


def squeeze(value):
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()


def url_escape(value, plus=True):
    """Returns a URL-encoded version of the given value.

    If ``plus`` is true (the default), spaces will be represented
    as "+" instead of "%20".  This is appropriate for query strings
    but not for the path component of a URL.  Note that this default
    is the reverse of Python's urllib module.

    .. versionadded:: 3.1
        The ``plus`` argument
    """
    quote = urllib_parse.quote_plus if plus else urllib_parse.quote
    return quote(utf8(value))


# python 3 changed things around enough that we need two separate
# implementations of url_unescape.  We also need our own implementation
# of parse_qs since python 3's version insists on decoding everything.
if sys.version_info[0] < 3:
    def url_unescape(value, encoding='utf-8', plus=True):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.

        If ``plus`` is true (the default), plus signs will be interpreted
        as spaces (literal plus signs must be represented as "%2B").  This
        is appropriate for query strings and form-encoded values but not
        for the path component of a URL.  Note that this default is the
        reverse of Python's urllib module.

        .. versionadded:: 3.1
           The ``plus`` argument
        """
        unquote = (urllib_parse.unquote_plus if plus else urllib_parse.unquote)
        if encoding is None:
            return unquote(utf8(value))
        else:
            return unicode_type(unquote(utf8(value)), encoding)

    parse_qs_bytes = _parse_qs
else:
    def url_unescape(value, encoding='utf-8', plus=True):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.

        If ``plus`` is true (the default), plus signs will be interpreted
        as spaces (literal plus signs must be represented as "%2B").  This
        is appropriate for query strings and form-encoded values but not
        for the path component of a URL.  Note that this default is the
        reverse of Python's urllib module.

        .. versionadded:: 3.1
           The ``plus`` argument
        """
        if encoding is None:
            if plus:
                # unquote_to_bytes doesn't have a _plus variant
                value = to_basestring(value).replace('+', ' ')
            return urllib_parse.unquote_to_bytes(value)
        else:
            unquote = (urllib_parse.unquote_plus if plus
                       else urllib_parse.unquote)
            return unquote(to_basestring(value), encoding=encoding)

    def parse_qs_bytes(qs, keep_blank_values=False, strict_parsing=False):
        """Parses a query string like urlparse.parse_qs, but returns the
        values as byte strings.

        Keys still become type str (interpreted as latin1 in python3!)
        because it's too painful to keep them as byte strings in
        python3 and in practice they're nearly always ascii anyway.
        """
        # This is gross, but python3 doesn't give us another way.
        # Latin1 is the universal donor of character encodings.
        result = _parse_qs(qs, keep_blank_values, strict_parsing,
                           encoding='latin1', errors='strict')
        encoded = {}
        for k, v in result.items():
            encoded[k] = [i.encode('latin1') for i in v]
        return encoded


_UTF8_TYPES = (bytes_type, type(None))


def utf8(value):
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, unicode_type), \
        "Expected bytes, unicode, or None; got %r" % type(value)
    return value.encode("utf-8")

_TO_UNICODE_TYPES = (unicode_type, type(None))


def to_unicode(value):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    assert isinstance(value, bytes_type), \
        "Expected bytes, unicode, or None; got %r" % type(value)
    return value.decode("utf-8")

# to_unicode was previously named _unicode not because it was private,
# but to avoid conflicts with the built-in unicode() function/type
_unicode = to_unicode

# When dealing with the standard library across python 2 and 3 it is
# sometimes useful to have a direct conversion to the native string type
if str is unicode_type:
    native_str = to_unicode
else:
    native_str = utf8

_BASESTRING_TYPES = (basestring_type, type(None))


def to_basestring(value):
    """Converts a string argument to a subclass of basestring.

    In python2, byte and unicode strings are mostly interchangeable,
    so functions that deal with a user-supplied argument in combination
    with ascii string constants can use either and should return the type
    the user supplied.  In python3, the two types are not interchangeable,
    so this method is needed to convert byte strings to unicode.
    """
    if isinstance(value, _BASESTRING_TYPES):
        return value
    assert isinstance(value, bytes_type), \
        "Expected bytes, unicode, or None; got %r" % type(value)
    return value.decode("utf-8")


def recursive_unicode(obj):
    """Walks a simple data structure, converting byte strings to unicode.

    Supports lists, tuples, and dictionaries.
    """
    if isinstance(obj, dict):
        return dict((recursive_unicode(k), recursive_unicode(v)) for (k, v) in obj.items())
    elif isinstance(obj, list):
        return list(recursive_unicode(i) for i in obj)
    elif isinstance(obj, tuple):
        return tuple(recursive_unicode(i) for i in obj)
    elif isinstance(obj, bytes_type):
        return to_unicode(obj)
    else:
        return obj

# I originally used the regex from
# http://daringfireball.net/2010/07/improved_regex_for_matching_urls
# but it gets all exponential on certain patterns (such as too many trailing
# dots), causing the regex matcher to never return.
# This regex should avoid those problems.
# Use to_unicode instead of tornado.util.u - we don't want backslashes getting
# processed as escapes.
_URL_RE = re.compile(to_unicode(r"""\b((?:([\w-]+):(/{1,3})|www[.])(?:(?:(?:[^\s&()]|&amp;|&quot;)*(?:[^!"#$%&'()*+,.:;<=>?@\[\]^`{|}~\s]))|(?:\((?:[^\s&()]|&amp;|&quot;)*\)))+)"""))


def linkify(text, shorten=False, extra_params="",
            require_protocol=False, permitted_protocols=["http", "https"]):
    """Converts plain text into HTML with links.

    For example: ``linkify("Hello http://tornadoweb.org!")`` would return
    ``Hello <a href="http://tornadoweb.org">http://tornadoweb.org</a>!``

    Parameters:

    * ``shorten``: Long urls will be shortened for display.

    * ``extra_params``: Extra text to include in the link tag, or a callable
        taking the link as an argument and returning the extra text
        e.g. ``linkify(text, extra_params='rel="nofollow" class="external"')``,
        or::

            def extra_params_cb(url):
                if url.startswith("http://example.com"):
                    return 'class="internal"'
                else:
                    return 'class="external" rel="nofollow"'
            linkify(text, extra_params=extra_params_cb)

    * ``require_protocol``: Only linkify urls which include a protocol. If
        this is False, urls such as www.facebook.com will also be linkified.

    * ``permitted_protocols``: List (or set) of protocols which should be
        linkified, e.g. ``linkify(text, permitted_protocols=["http", "ftp",
        "mailto"])``. It is very unsafe to include protocols such as
        ``javascript``.
    """
    if extra_params and not callable(extra_params):
        extra_params = " " + extra_params.strip()

    def make_link(m):
        url = m.group(1)
        proto = m.group(2)
        if require_protocol and not proto:
            return url  # not protocol, no linkify

        if proto and proto not in permitted_protocols:
            return url  # bad protocol, no linkify

        href = m.group(1)
        if not proto:
            href = "http://" + href   # no proto specified, use http

        if callable(extra_params):
            params = " " + extra_params(href).strip()
        else:
            params = extra_params

        # clip long urls. max_len is just an approximation
        max_len = 30
        if shorten and len(url) > max_len:
            before_clip = url
            if proto:
                proto_len = len(proto) + 1 + len(m.group(3) or "")  # +1 for :
            else:
                proto_len = 0

            parts = url[proto_len:].split("/")
            if len(parts) > 1:
                # Grab the whole host part plus the first bit of the path
                # The path is usually not that interesting once shortened
                # (no more slug, etc), so it really just provides a little
                # extra indication of shortening.
                url = url[:proto_len] + parts[0] + "/" + \
                    parts[1][:8].split('?')[0].split('.')[0]

            if len(url) > max_len * 1.5:  # still too long
                url = url[:max_len]

            if url != before_clip:
                amp = url.rfind('&')
                # avoid splitting html char entities
                if amp > max_len - 5:
                    url = url[:amp]
                url += "..."

                if len(url) >= len(before_clip):
                    url = before_clip
                else:
                    # full url is visible on mouse-over (for those who don't
                    # have a status bar, such as Safari by default)
                    params += ' title="%s"' % href

        return u('<a href="%s"%s>%s</a>') % (href, params, url)

    # First HTML-escape so that our strings are all safe.
    # The regex is modified to avoid character entites other than &amp; so
    # that we won't pick up &quot;, etc.
    text = _unicode(xhtml_escape(text))
    return _URL_RE.sub(make_link, text)


def _convert_entity(m):
    if m.group(1) == "#":
        try:
            return unichr(int(m.group(2)))
        except ValueError:
            return "&#%s;" % m.group(2)
    try:
        return _HTML_UNICODE_MAP[m.group(2)]
    except KeyError:
        return "&%s;" % m.group(2)


def _build_unicode_map():
    unicode_map = {}
    for name, value in htmlentitydefs.name2codepoint.items():
        unicode_map[name] = unichr(value)
    return unicode_map

_HTML_UNICODE_MAP = _build_unicode_map()

########NEW FILE########
__FILENAME__ = gen
"""``tornado.gen`` is a generator-based interface to make it easier to
work in an asynchronous environment.  Code using the ``gen`` module
is technically asynchronous, but it is written as a single generator
instead of a collection of separate functions.

For example, the following asynchronous handler::

    class AsyncHandler(RequestHandler):
        @asynchronous
        def get(self):
            http_client = AsyncHTTPClient()
            http_client.fetch("http://example.com",
                              callback=self.on_fetch)

        def on_fetch(self, response):
            do_something_with_response(response)
            self.render("template.html")

could be written with ``gen`` as::

    class GenAsyncHandler(RequestHandler):
        @gen.coroutine
        def get(self):
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch("http://example.com")
            do_something_with_response(response)
            self.render("template.html")

Most asynchronous functions in Tornado return a `.Future`;
yielding this object returns its `~.Future.result`.

For functions that do not return ``Futures``, `Task` works with any
function that takes a ``callback`` keyword argument (most Tornado functions
can be used in either style, although the ``Future`` style is preferred
since it is both shorter and provides better exception handling)::

    @gen.coroutine
    def get(self):
        yield gen.Task(AsyncHTTPClient().fetch, "http://example.com")

You can also yield a list of ``Futures`` and/or ``Tasks``, which will be
started at the same time and run in parallel; a list of results will
be returned when they are all finished::

    @gen.coroutine
    def get(self):
        http_client = AsyncHTTPClient()
        response1, response2 = yield [http_client.fetch(url1),
                                      http_client.fetch(url2)]

For more complicated interfaces, `Task` can be split into two parts:
`Callback` and `Wait`::

    class GenAsyncHandler2(RequestHandler):
        @asynchronous
        @gen.coroutine
        def get(self):
            http_client = AsyncHTTPClient()
            http_client.fetch("http://example.com",
                              callback=(yield gen.Callback("key"))
            response = yield gen.Wait("key")
            do_something_with_response(response)
            self.render("template.html")

The ``key`` argument to `Callback` and `Wait` allows for multiple
asynchronous operations to be started at different times and proceed
in parallel: yield several callbacks with different keys, then wait
for them once all the async operations have started.

The result of a `Wait` or `Task` yield expression depends on how the callback
was run.  If it was called with no arguments, the result is ``None``.  If
it was called with one argument, the result is that argument.  If it was
called with more than one argument or any keyword arguments, the result
is an `Arguments` object, which is a named tuple ``(args, kwargs)``.
"""
from __future__ import absolute_import, division, print_function, with_statement

import collections
import functools
import itertools
import sys
import types

from tornado.concurrent import Future, TracebackFuture
from tornado.ioloop import IOLoop
from tornado.stack_context import ExceptionStackContext, wrap


class KeyReuseError(Exception):
    pass


class UnknownKeyError(Exception):
    pass


class LeakedCallbackError(Exception):
    pass


class BadYieldError(Exception):
    pass


class ReturnValueIgnoredError(Exception):
    pass


def engine(func):
    """Callback-oriented decorator for asynchronous generators.

    This is an older interface; for new code that does not need to be
    compatible with versions of Tornado older than 3.0 the
    `coroutine` decorator is recommended instead.

    This decorator is similar to `coroutine`, except it does not
    return a `.Future` and the ``callback`` argument is not treated
    specially.

    In most cases, functions decorated with `engine` should take
    a ``callback`` argument and invoke it with their result when
    they are finished.  One notable exception is the
    `~tornado.web.RequestHandler` :ref:`HTTP verb methods <verbs>`,
    which use ``self.finish()`` in place of a callback argument.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        runner = None

        def handle_exception(typ, value, tb):
            # if the function throws an exception before its first "yield"
            # (or is not a generator at all), the Runner won't exist yet.
            # However, in that case we haven't reached anything asynchronous
            # yet, so we can just let the exception propagate.
            if runner is not None:
                return runner.handle_exception(typ, value, tb)
            return False
        with ExceptionStackContext(handle_exception) as deactivate:
            try:
                result = func(*args, **kwargs)
            except (Return, StopIteration) as e:
                result = getattr(e, 'value', None)
            else:
                if isinstance(result, types.GeneratorType):
                    def final_callback(value):
                        if value is not None:
                            raise ReturnValueIgnoredError(
                                "@gen.engine functions cannot return values: "
                                "%r" % (value,))
                        assert value is None
                        deactivate()
                    runner = Runner(result, final_callback)
                    runner.run()
                    return
            if result is not None:
                raise ReturnValueIgnoredError(
                    "@gen.engine functions cannot return values: %r" %
                    (result,))
            deactivate()
            # no yield, so we're done
    return wrapper


def coroutine(func):
    """Decorator for asynchronous generators.

    Any generator that yields objects from this module must be wrapped
    in either this decorator or `engine`.

    Coroutines may "return" by raising the special exception
    `Return(value) <Return>`.  In Python 3.3+, it is also possible for
    the function to simply use the ``return value`` statement (prior to
    Python 3.3 generators were not allowed to also return values).
    In all versions of Python a coroutine that simply wishes to exit
    early may use the ``return`` statement without a value.

    Functions with this decorator return a `.Future`.  Additionally,
    they may be called with a ``callback`` keyword argument, which
    will be invoked with the future's result when it resolves.  If the
    coroutine fails, the callback will not be run and an exception
    will be raised into the surrounding `.StackContext`.  The
    ``callback`` argument is not visible inside the decorated
    function; it is handled by the decorator itself.

    From the caller's perspective, ``@gen.coroutine`` is similar to
    the combination of ``@return_future`` and ``@gen.engine``.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        runner = None
        future = TracebackFuture()

        if 'callback' in kwargs:
            callback = kwargs.pop('callback')
            IOLoop.current().add_future(
                future, lambda future: callback(future.result()))

        def handle_exception(typ, value, tb):
            try:
                if runner is not None and runner.handle_exception(typ, value, tb):
                    return True
            except Exception:
                typ, value, tb = sys.exc_info()
            future.set_exc_info((typ, value, tb))
            return True
        with ExceptionStackContext(handle_exception) as deactivate:
            try:
                result = func(*args, **kwargs)
            except (Return, StopIteration) as e:
                result = getattr(e, 'value', None)
            except Exception:
                deactivate()
                future.set_exc_info(sys.exc_info())
                return future
            else:
                if isinstance(result, types.GeneratorType):
                    def final_callback(value):
                        deactivate()
                        future.set_result(value)
                    runner = Runner(result, final_callback)
                    runner.run()
                    return future
            deactivate()
            future.set_result(result)
        return future
    return wrapper


class Return(Exception):
    """Special exception to return a value from a `coroutine`.

    If this exception is raised, its value argument is used as the
    result of the coroutine::

        @gen.coroutine
        def fetch_json(url):
            response = yield AsyncHTTPClient().fetch(url)
            raise gen.Return(json_decode(response.body))

    In Python 3.3, this exception is no longer necessary: the ``return``
    statement can be used directly to return a value (previously
    ``yield`` and ``return`` with a value could not be combined in the
    same function).

    By analogy with the return statement, the value argument is optional,
    but it is never necessary to ``raise gen.Return()``.  The ``return``
    statement can be used with no arguments instead.
    """
    def __init__(self, value=None):
        super(Return, self).__init__()
        self.value = value


class YieldPoint(object):
    """Base class for objects that may be yielded from the generator.

    Applications do not normally need to use this class, but it may be
    subclassed to provide additional yielding behavior.
    """
    def start(self, runner):
        """Called by the runner after the generator has yielded.

        No other methods will be called on this object before ``start``.
        """
        raise NotImplementedError()

    def is_ready(self):
        """Called by the runner to determine whether to resume the generator.

        Returns a boolean; may be called more than once.
        """
        raise NotImplementedError()

    def get_result(self):
        """Returns the value to use as the result of the yield expression.

        This method will only be called once, and only after `is_ready`
        has returned true.
        """
        raise NotImplementedError()


class Callback(YieldPoint):
    """Returns a callable object that will allow a matching `Wait` to proceed.

    The key may be any value suitable for use as a dictionary key, and is
    used to match ``Callbacks`` to their corresponding ``Waits``.  The key
    must be unique among outstanding callbacks within a single run of the
    generator function, but may be reused across different runs of the same
    function (so constants generally work fine).

    The callback may be called with zero or one arguments; if an argument
    is given it will be returned by `Wait`.
    """
    def __init__(self, key):
        self.key = key

    def start(self, runner):
        self.runner = runner
        runner.register_callback(self.key)

    def is_ready(self):
        return True

    def get_result(self):
        return self.runner.result_callback(self.key)


class Wait(YieldPoint):
    """Returns the argument passed to the result of a previous `Callback`."""
    def __init__(self, key):
        self.key = key

    def start(self, runner):
        self.runner = runner

    def is_ready(self):
        return self.runner.is_ready(self.key)

    def get_result(self):
        return self.runner.pop_result(self.key)


class WaitAll(YieldPoint):
    """Returns the results of multiple previous `Callbacks <Callback>`.

    The argument is a sequence of `Callback` keys, and the result is
    a list of results in the same order.

    `WaitAll` is equivalent to yielding a list of `Wait` objects.
    """
    def __init__(self, keys):
        self.keys = keys

    def start(self, runner):
        self.runner = runner

    def is_ready(self):
        return all(self.runner.is_ready(key) for key in self.keys)

    def get_result(self):
        return [self.runner.pop_result(key) for key in self.keys]


class Task(YieldPoint):
    """Runs a single asynchronous operation.

    Takes a function (and optional additional arguments) and runs it with
    those arguments plus a ``callback`` keyword argument.  The argument passed
    to the callback is returned as the result of the yield expression.

    A `Task` is equivalent to a `Callback`/`Wait` pair (with a unique
    key generated automatically)::

        result = yield gen.Task(func, args)

        func(args, callback=(yield gen.Callback(key)))
        result = yield gen.Wait(key)
    """
    def __init__(self, func, *args, **kwargs):
        assert "callback" not in kwargs
        self.args = args
        self.kwargs = kwargs
        self.func = func

    def start(self, runner):
        self.runner = runner
        self.key = object()
        runner.register_callback(self.key)
        self.kwargs["callback"] = runner.result_callback(self.key)
        self.func(*self.args, **self.kwargs)

    def is_ready(self):
        return self.runner.is_ready(self.key)

    def get_result(self):
        return self.runner.pop_result(self.key)


class YieldFuture(YieldPoint):
    def __init__(self, future, io_loop=None):
        self.future = future
        self.io_loop = io_loop or IOLoop.current()

    def start(self, runner):
        self.runner = runner
        self.key = object()
        runner.register_callback(self.key)
        self.io_loop.add_future(self.future, runner.result_callback(self.key))

    def is_ready(self):
        return self.runner.is_ready(self.key)

    def get_result(self):
        return self.runner.pop_result(self.key).result()


class Multi(YieldPoint):
    """Runs multiple asynchronous operations in parallel.

    Takes a list of ``Tasks`` or other ``YieldPoints`` and returns a list of
    their responses.  It is not necessary to call `Multi` explicitly,
    since the engine will do so automatically when the generator yields
    a list of ``YieldPoints``.
    """
    def __init__(self, children):
        self.children = []
        for i in children:
            if isinstance(i, Future):
                i = YieldFuture(i)
            self.children.append(i)
        assert all(isinstance(i, YieldPoint) for i in self.children)
        self.unfinished_children = set(self.children)

    def start(self, runner):
        for i in self.children:
            i.start(runner)

    def is_ready(self):
        finished = list(itertools.takewhile(
            lambda i: i.is_ready(), self.unfinished_children))
        self.unfinished_children.difference_update(finished)
        return not self.unfinished_children

    def get_result(self):
        return [i.get_result() for i in self.children]


class _NullYieldPoint(YieldPoint):
    def start(self, runner):
        pass

    def is_ready(self):
        return True

    def get_result(self):
        return None


_null_yield_point = _NullYieldPoint()


class Runner(object):
    """Internal implementation of `tornado.gen.engine`.

    Maintains information about pending callbacks and their results.

    ``final_callback`` is run after the generator exits.
    """
    def __init__(self, gen, final_callback):
        self.gen = gen
        self.final_callback = final_callback
        self.yield_point = _null_yield_point
        self.pending_callbacks = set()
        self.results = {}
        self.running = False
        self.finished = False
        self.exc_info = None
        self.had_exception = False

    def register_callback(self, key):
        """Adds ``key`` to the list of callbacks."""
        if key in self.pending_callbacks:
            raise KeyReuseError("key %r is already pending" % (key,))
        self.pending_callbacks.add(key)

    def is_ready(self, key):
        """Returns true if a result is available for ``key``."""
        if key not in self.pending_callbacks:
            raise UnknownKeyError("key %r is not pending" % (key,))
        return key in self.results

    def set_result(self, key, result):
        """Sets the result for ``key`` and attempts to resume the generator."""
        self.results[key] = result
        self.run()

    def pop_result(self, key):
        """Returns the result for ``key`` and unregisters it."""
        self.pending_callbacks.remove(key)
        return self.results.pop(key)

    def run(self):
        """Starts or resumes the generator, running until it reaches a
        yield point that is not ready.
        """
        if self.running or self.finished:
            return
        try:
            self.running = True
            while True:
                if self.exc_info is None:
                    try:
                        if not self.yield_point.is_ready():
                            return
                        next = self.yield_point.get_result()
                        self.yield_point = None
                    except Exception:
                        self.exc_info = sys.exc_info()
                try:
                    if self.exc_info is not None:
                        self.had_exception = True
                        exc_info = self.exc_info
                        self.exc_info = None
                        yielded = self.gen.throw(*exc_info)
                    else:
                        yielded = self.gen.send(next)
                except (StopIteration, Return) as e:
                    self.finished = True
                    self.yield_point = _null_yield_point
                    if self.pending_callbacks and not self.had_exception:
                        # If we ran cleanly without waiting on all callbacks
                        # raise an error (really more of a warning).  If we
                        # had an exception then some callbacks may have been
                        # orphaned, so skip the check in that case.
                        raise LeakedCallbackError(
                            "finished without waiting for callbacks %r" %
                            self.pending_callbacks)
                    self.final_callback(getattr(e, 'value', None))
                    self.final_callback = None
                    return
                except Exception:
                    self.finished = True
                    self.yield_point = _null_yield_point
                    raise
                if isinstance(yielded, list):
                    yielded = Multi(yielded)
                elif isinstance(yielded, Future):
                    yielded = YieldFuture(yielded)
                if isinstance(yielded, YieldPoint):
                    self.yield_point = yielded
                    try:
                        self.yield_point.start(self)
                    except Exception:
                        self.exc_info = sys.exc_info()
                else:
                    self.exc_info = (BadYieldError(
                        "yielded unknown object %r" % (yielded,)),)
        finally:
            self.running = False

    def result_callback(self, key):
        def inner(*args, **kwargs):
            if kwargs or len(args) > 1:
                result = Arguments(args, kwargs)
            elif args:
                result = args[0]
            else:
                result = None
            self.set_result(key, result)
        return wrap(inner)

    def handle_exception(self, typ, value, tb):
        if not self.running and not self.finished:
            self.exc_info = (typ, value, tb)
            self.run()
            return True
        else:
            return False

Arguments = collections.namedtuple('Arguments', ['args', 'kwargs'])

########NEW FILE########
__FILENAME__ = httpclient
"""Blocking and non-blocking HTTP client interfaces.

This module defines a common interface shared by two implementations,
``simple_httpclient`` and ``curl_httpclient``.  Applications may either
instantiate their chosen implementation class directly or use the
`AsyncHTTPClient` class from this module, which selects an implementation
that can be overridden with the `AsyncHTTPClient.configure` method.

The default implementation is ``simple_httpclient``, and this is expected
to be suitable for most users' needs.  However, some applications may wish
to switch to ``curl_httpclient`` for reasons such as the following:

* ``curl_httpclient`` has some features not found in ``simple_httpclient``,
  including support for HTTP proxies and the ability to use a specified
  network interface.

* ``curl_httpclient`` is more likely to be compatible with sites that are
  not-quite-compliant with the HTTP spec, or sites that use little-exercised
  features of HTTP.

* ``curl_httpclient`` is faster.

* ``curl_httpclient`` was the default prior to Tornado 2.0.

Note that if you are using ``curl_httpclient``, it is highly recommended that
you use a recent version of ``libcurl`` and ``pycurl``.  Currently the minimum
supported version is 7.18.2, and the recommended version is 7.21.1 or newer.
"""

from __future__ import absolute_import, division, print_function, with_statement

import functools
import time
import weakref

from tornado.concurrent import Future
from tornado.escape import utf8
from tornado import httputil, stack_context
from tornado.ioloop import IOLoop
from tornado.util import Configurable


class HTTPClient(object):
    """A blocking HTTP client.

    This interface is provided for convenience and testing; most applications
    that are running an IOLoop will want to use `AsyncHTTPClient` instead.
    Typical usage looks like this::

        http_client = httpclient.HTTPClient()
        try:
            response = http_client.fetch("http://www.google.com/")
            print response.body
        except httpclient.HTTPError as e:
            print "Error:", e
        http_client.close()
    """
    def __init__(self, async_client_class=None, **kwargs):
        self._io_loop = IOLoop()
        if async_client_class is None:
            async_client_class = AsyncHTTPClient
        self._async_client = async_client_class(self._io_loop, **kwargs)
        self._closed = False

    def __del__(self):
        self.close()

    def close(self):
        """Closes the HTTPClient, freeing any resources used."""
        if not self._closed:
            self._async_client.close()
            self._io_loop.close()
            self._closed = True

    def fetch(self, request, **kwargs):
        """Executes a request, returning an `HTTPResponse`.

        The request may be either a string URL or an `HTTPRequest` object.
        If it is a string, we construct an `HTTPRequest` using any additional
        kwargs: ``HTTPRequest(request, **kwargs)``

        If an error occurs during the fetch, we raise an `HTTPError`.
        """
        response = self._io_loop.run_sync(functools.partial(
            self._async_client.fetch, request, **kwargs))
        response.rethrow()
        return response


class AsyncHTTPClient(Configurable):
    """An non-blocking HTTP client.

    Example usage::

        def handle_request(response):
            if response.error:
                print "Error:", response.error
            else:
                print response.body

        http_client = AsyncHTTPClient()
        http_client.fetch("http://www.google.com/", handle_request)

    The constructor for this class is magic in several respects: It
    actually creates an instance of an implementation-specific
    subclass, and instances are reused as a kind of pseudo-singleton
    (one per `.IOLoop`).  The keyword argument ``force_instance=True``
    can be used to suppress this singleton behavior.  Constructor
    arguments other than ``io_loop`` and ``force_instance`` are
    deprecated.  The implementation subclass as well as arguments to
    its constructor can be set with the static method `configure()`
    """
    @classmethod
    def configurable_base(cls):
        return AsyncHTTPClient

    @classmethod
    def configurable_default(cls):
        from tornado.simple_httpclient import SimpleAsyncHTTPClient
        return SimpleAsyncHTTPClient

    @classmethod
    def _async_clients(cls):
        attr_name = '_async_client_dict_' + cls.__name__
        if not hasattr(cls, attr_name):
            setattr(cls, attr_name, weakref.WeakKeyDictionary())
        return getattr(cls, attr_name)

    def __new__(cls, io_loop=None, force_instance=False, **kwargs):
        io_loop = io_loop or IOLoop.current()
        if io_loop in cls._async_clients() and not force_instance:
            return cls._async_clients()[io_loop]
        instance = super(AsyncHTTPClient, cls).__new__(cls, io_loop=io_loop,
                                                       **kwargs)
        if not force_instance:
            cls._async_clients()[io_loop] = instance
        return instance

    def initialize(self, io_loop, defaults=None):
        self.io_loop = io_loop
        self.defaults = dict(HTTPRequest._DEFAULTS)
        if defaults is not None:
            self.defaults.update(defaults)

    def close(self):
        """Destroys this HTTP client, freeing any file descriptors used.
        Not needed in normal use, but may be helpful in unittests that
        create and destroy http clients.  No other methods may be called
        on the `AsyncHTTPClient` after ``close()``.
        """
        if self._async_clients().get(self.io_loop) is self:
            del self._async_clients()[self.io_loop]

    def fetch(self, request, callback=None, **kwargs):
        """Executes a request, asynchronously returning an `HTTPResponse`.

        The request may be either a string URL or an `HTTPRequest` object.
        If it is a string, we construct an `HTTPRequest` using any additional
        kwargs: ``HTTPRequest(request, **kwargs)``

        This method returns a `.Future` whose result is an
        `HTTPResponse`.  The ``Future`` wil raise an `HTTPError` if
        the request returned a non-200 response code.

        If a ``callback`` is given, it will be invoked with the `HTTPResponse`.
        In the callback interface, `HTTPError` is not automatically raised.
        Instead, you must check the response's ``error`` attribute or
        call its `~HTTPResponse.rethrow` method.
        """
        if not isinstance(request, HTTPRequest):
            request = HTTPRequest(url=request, **kwargs)
        # We may modify this (to add Host, Accept-Encoding, etc),
        # so make sure we don't modify the caller's object.  This is also
        # where normal dicts get converted to HTTPHeaders objects.
        request.headers = httputil.HTTPHeaders(request.headers)
        request = _RequestProxy(request, self.defaults)
        future = Future()
        if callback is not None:
            callback = stack_context.wrap(callback)

            def handle_future(future):
                exc = future.exception()
                if isinstance(exc, HTTPError) and exc.response is not None:
                    response = exc.response
                elif exc is not None:
                    response = HTTPResponse(
                        request, 599, error=exc,
                        request_time=time.time() - request.start_time)
                else:
                    response = future.result()
                self.io_loop.add_callback(callback, response)
            future.add_done_callback(handle_future)

        def handle_response(response):
            if response.error:
                future.set_exception(response.error)
            else:
                future.set_result(response)
        self.fetch_impl(request, handle_response)
        return future

    def fetch_impl(self, request, callback):
        raise NotImplementedError()

    @classmethod
    def configure(cls, impl, **kwargs):
        """Configures the `AsyncHTTPClient` subclass to use.

        ``AsyncHTTPClient()`` actually creates an instance of a subclass.
        This method may be called with either a class object or the
        fully-qualified name of such a class (or ``None`` to use the default,
        ``SimpleAsyncHTTPClient``)

        If additional keyword arguments are given, they will be passed
        to the constructor of each subclass instance created.  The
        keyword argument ``max_clients`` determines the maximum number
        of simultaneous `~AsyncHTTPClient.fetch()` operations that can
        execute in parallel on each `.IOLoop`.  Additional arguments
        may be supported depending on the implementation class in use.

        Example::

           AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        """
        super(AsyncHTTPClient, cls).configure(impl, **kwargs)


class HTTPRequest(object):
    """HTTP client request object."""

    # Default values for HTTPRequest parameters.
    # Merged with the values on the request object by AsyncHTTPClient
    # implementations.
    _DEFAULTS = dict(
        connect_timeout=20.0,
        request_timeout=20.0,
        follow_redirects=True,
        max_redirects=5,
        use_gzip=True,
        proxy_password='',
        allow_nonstandard_methods=False,
        validate_cert=True)

    def __init__(self, url, method="GET", headers=None, body=None,
                 auth_username=None, auth_password=None, auth_mode=None,
                 connect_timeout=None, request_timeout=None,
                 if_modified_since=None, follow_redirects=None,
                 max_redirects=None, user_agent=None, use_gzip=None,
                 network_interface=None, streaming_callback=None,
                 header_callback=None, prepare_curl_callback=None,
                 proxy_host=None, proxy_port=None, proxy_username=None,
                 proxy_password=None, allow_nonstandard_methods=None,
                 validate_cert=None, ca_certs=None,
                 allow_ipv6=None,
                 client_key=None, client_cert=None):
        r"""All parameters except ``url`` are optional.

        :arg string url: URL to fetch
        :arg string method: HTTP method, e.g. "GET" or "POST"
        :arg headers: Additional HTTP headers to pass on the request
        :arg body: HTTP body to pass on the request
        :type headers: `~tornado.httputil.HTTPHeaders` or `dict`
        :arg string auth_username: Username for HTTP authentication
        :arg string auth_password: Password for HTTP authentication
        :arg string auth_mode: Authentication mode; default is "basic".
           Allowed values are implementation-defined; ``curl_httpclient``
           supports "basic" and "digest"; ``simple_httpclient`` only supports
           "basic"
        :arg float connect_timeout: Timeout for initial connection in seconds
        :arg float request_timeout: Timeout for entire request in seconds
        :arg if_modified_since: Timestamp for ``If-Modified-Since`` header
        :type if_modified_since: `datetime` or `float`
        :arg bool follow_redirects: Should redirects be followed automatically
           or return the 3xx response?
        :arg int max_redirects: Limit for ``follow_redirects``
        :arg string user_agent: String to send as ``User-Agent`` header
        :arg bool use_gzip: Request gzip encoding from the server
        :arg string network_interface: Network interface to use for request
        :arg callable streaming_callback: If set, ``streaming_callback`` will
           be run with each chunk of data as it is received, and
           ``HTTPResponse.body`` and ``HTTPResponse.buffer`` will be empty in
           the final response.
        :arg callable header_callback: If set, ``header_callback`` will
           be run with each header line as it is received (including the
           first line, e.g. ``HTTP/1.0 200 OK\r\n``, and a final line
           containing only ``\r\n``.  All lines include the trailing newline
           characters).  ``HTTPResponse.headers`` will be empty in the final
           response.  This is most useful in conjunction with
           ``streaming_callback``, because it's the only way to get access to
           header data while the request is in progress.
        :arg callable prepare_curl_callback: If set, will be called with
           a ``pycurl.Curl`` object to allow the application to make additional
           ``setopt`` calls.
        :arg string proxy_host: HTTP proxy hostname.  To use proxies,
           ``proxy_host`` and ``proxy_port`` must be set; ``proxy_username`` and
           ``proxy_pass`` are optional.  Proxies are currently only supported
           with ``curl_httpclient``.
        :arg int proxy_port: HTTP proxy port
        :arg string proxy_username: HTTP proxy username
        :arg string proxy_password: HTTP proxy password
        :arg bool allow_nonstandard_methods: Allow unknown values for ``method``
           argument?
        :arg bool validate_cert: For HTTPS requests, validate the server's
           certificate?
        :arg string ca_certs: filename of CA certificates in PEM format,
           or None to use defaults.  Note that in ``curl_httpclient``, if
           any request uses a custom ``ca_certs`` file, they all must (they
           don't have to all use the same ``ca_certs``, but it's not possible
           to mix requests with ``ca_certs`` and requests that use the defaults.
        :arg bool allow_ipv6: Use IPv6 when available?  Default is false in
           ``simple_httpclient`` and true in ``curl_httpclient``
        :arg string client_key: Filename for client SSL key, if any
        :arg string client_cert: Filename for client SSL certificate, if any

        .. versionadded:: 3.1
           The ``auth_mode`` argument.
        """
        if headers is None:
            headers = httputil.HTTPHeaders()
        if if_modified_since:
            headers["If-Modified-Since"] = httputil.format_timestamp(
                if_modified_since)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.url = url
        self.method = method
        self.headers = headers
        self.body = utf8(body)
        self.auth_username = auth_username
        self.auth_password = auth_password
        self.auth_mode = auth_mode
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.use_gzip = use_gzip
        self.network_interface = network_interface
        self.streaming_callback = stack_context.wrap(streaming_callback)
        self.header_callback = stack_context.wrap(header_callback)
        self.prepare_curl_callback = stack_context.wrap(prepare_curl_callback)
        self.allow_nonstandard_methods = allow_nonstandard_methods
        self.validate_cert = validate_cert
        self.ca_certs = ca_certs
        self.allow_ipv6 = allow_ipv6
        self.client_key = client_key
        self.client_cert = client_cert
        self.start_time = time.time()


class HTTPResponse(object):
    """HTTP Response object.

    Attributes:

    * request: HTTPRequest object

    * code: numeric HTTP status code, e.g. 200 or 404

    * reason: human-readable reason phrase describing the status code
      (with curl_httpclient, this is a default value rather than the
      server's actual response)

    * headers: `tornado.httputil.HTTPHeaders` object

    * buffer: ``cStringIO`` object for response body

    * body: response body as string (created on demand from ``self.buffer``)

    * error: Exception object, if any

    * request_time: seconds from request start to finish

    * time_info: dictionary of diagnostic timing information from the request.
      Available data are subject to change, but currently uses timings
      available from http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html,
      plus ``queue``, which is the delay (if any) introduced by waiting for
      a slot under `AsyncHTTPClient`'s ``max_clients`` setting.
    """
    def __init__(self, request, code, headers=None, buffer=None,
                 effective_url=None, error=None, request_time=None,
                 time_info=None, reason=None):
        if isinstance(request, _RequestProxy):
            self.request = request.request
        else:
            self.request = request
        self.code = code
        self.reason = reason or httputil.responses.get(code, "Unknown")
        if headers is not None:
            self.headers = headers
        else:
            self.headers = httputil.HTTPHeaders()
        self.buffer = buffer
        self._body = None
        if effective_url is None:
            self.effective_url = request.url
        else:
            self.effective_url = effective_url
        if error is None:
            if self.code < 200 or self.code >= 300:
                self.error = HTTPError(self.code, response=self)
            else:
                self.error = None
        else:
            self.error = error
        self.request_time = request_time
        self.time_info = time_info or {}

    def _get_body(self):
        if self.buffer is None:
            return None
        elif self._body is None:
            self._body = self.buffer.getvalue()

        return self._body

    body = property(_get_body)

    def rethrow(self):
        """If there was an error on the request, raise an `HTTPError`."""
        if self.error:
            raise self.error

    def __repr__(self):
        args = ",".join("%s=%r" % i for i in sorted(self.__dict__.items()))
        return "%s(%s)" % (self.__class__.__name__, args)


class HTTPError(Exception):
    """Exception thrown for an unsuccessful HTTP request.

    Attributes:

    * ``code`` - HTTP error integer error code, e.g. 404.  Error code 599 is
      used when no HTTP response was received, e.g. for a timeout.

    * ``response`` - `HTTPResponse` object, if any.

    Note that if ``follow_redirects`` is False, redirects become HTTPErrors,
    and you can look at ``error.response.headers['Location']`` to see the
    destination of the redirect.
    """
    def __init__(self, code, message=None, response=None):
        self.code = code
        message = message or httputil.responses.get(code, "Unknown")
        self.response = response
        Exception.__init__(self, "HTTP %d: %s" % (self.code, message))


class _RequestProxy(object):
    """Combines an object with a dictionary of defaults.

    Used internally by AsyncHTTPClient implementations.
    """
    def __init__(self, request, defaults):
        self.request = request
        self.defaults = defaults

    def __getattr__(self, name):
        request_attr = getattr(self.request, name)
        if request_attr is not None:
            return request_attr
        elif self.defaults is not None:
            return self.defaults.get(name, None)
        else:
            return None


def main():
    from tornado.options import define, options, parse_command_line
    define("print_headers", type=bool, default=False)
    define("print_body", type=bool, default=True)
    define("follow_redirects", type=bool, default=True)
    define("validate_cert", type=bool, default=True)
    args = parse_command_line()
    client = HTTPClient()
    for arg in args:
        try:
            response = client.fetch(arg,
                                    follow_redirects=options.follow_redirects,
                                    validate_cert=options.validate_cert,
                                    )
        except HTTPError as e:
            if e.response is not None:
                response = e.response
            else:
                raise
        if options.print_headers:
            print(response.headers)
        if options.print_body:
            print(response.body)
    client.close()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = httpserver
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `tornado.web.Application.listen`).

This module also defines the `HTTPRequest` class which is exposed via
`tornado.web.RequestHandler.request`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import socket
# import ssl
import time

from tornado.escape import native_str, parse_qs_bytes
from tornado import httputil
from tornado import iostream
from tornado.log import gen_log
from tornado import netutil
from tornado.tcpserver import TCPServer
from tornado import stack_context
from tornado.util import bytes_type

try:
    import Cookie  # py2
except ImportError:
    import http.cookies as Cookie  # py3


class HTTPServer(TCPServer):
    r"""A non-blocking, single-threaded HTTP server.

    A server is defined by a request callback that takes an HTTPRequest
    instance as an argument and writes a valid HTTP response with
    `HTTPRequest.write`. `HTTPRequest.finish` finishes the request (but does
    not necessarily close the connection in the case of HTTP/1.1 keep-alive
    requests). A simple example server that echoes back the URI you
    requested::

        import tornado.httpserver
        import tornado.ioloop

        def handle_request(request):
           message = "You requested %s\n" % request.uri
           request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (
                         len(message), message))
           request.finish()

        http_server = tornado.httpserver.HTTPServer(handle_request)
        http_server.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

    `HTTPServer` is a very basic connection handler.  It parses the request
    headers and body, but the request callback is responsible for producing
    the response exactly as it will appear on the wire.  This affords
    maximum flexibility for applications to implement whatever parts
    of HTTP responses are required.

    `HTTPServer` supports keep-alive connections by default
    (automatically for HTTP/1.1, or for HTTP/1.0 when the client
    requests ``Connection: keep-alive``).  This means that the request
    callback must generate a properly-framed response, using either
    the ``Content-Length`` header or ``Transfer-Encoding: chunked``.
    Applications that are unable to frame their responses properly
    should instead return a ``Connection: close`` header in each
    response and pass ``no_keep_alive=True`` to the `HTTPServer`
    constructor.

    If ``xheaders`` is ``True``, we support the
    ``X-Real-Ip``/``X-Forwarded-For`` and
    ``X-Scheme``/``X-Forwarded-Proto`` headers, which override the
    remote IP and URI scheme/protocol for all requests.  These headers
    are useful when running Tornado behind a reverse proxy or load
    balancer.  The ``protocol`` argument can also be set to ``https``
    if Tornado is run behind an SSL-decoding proxy that does not set one of
    the supported ``xheaders``.

    To make this server serve SSL traffic, send the ``ssl_options`` dictionary
    argument with the arguments required for the `ssl.wrap_socket` method,
    including ``certfile`` and ``keyfile``.  (In Python 3.2+ you can pass
    an `ssl.SSLContext` object instead of a dict)::

       HTTPServer(applicaton, ssl_options={
           "certfile": os.path.join(data_dir, "mydomain.crt"),
           "keyfile": os.path.join(data_dir, "mydomain.key"),
       })

    `HTTPServer` initialization follows one of three patterns (the
    initialization methods are defined on `tornado.tcpserver.TCPServer`):

    1. `~tornado.tcpserver.TCPServer.listen`: simple single-process::

            server = HTTPServer(app)
            server.listen(8888)
            IOLoop.instance().start()

       In many cases, `tornado.web.Application.listen` can be used to avoid
       the need to explicitly create the `HTTPServer`.

    2. `~tornado.tcpserver.TCPServer.bind`/`~tornado.tcpserver.TCPServer.start`:
       simple multi-process::

            server = HTTPServer(app)
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.instance().start()

       When using this interface, an `.IOLoop` must *not* be passed
       to the `HTTPServer` constructor.  `~.TCPServer.start` will always start
       the server on the default singleton `.IOLoop`.

    3. `~tornado.tcpserver.TCPServer.add_sockets`: advanced multi-process::

            sockets = tornado.netutil.bind_sockets(8888)
            tornado.process.fork_processes(0)
            server = HTTPServer(app)
            server.add_sockets(sockets)
            IOLoop.instance().start()

       The `~.TCPServer.add_sockets` interface is more complicated,
       but it can be used with `tornado.process.fork_processes` to
       give you more flexibility in when the fork happens.
       `~.TCPServer.add_sockets` can also be used in single-process
       servers if you want to create your listening sockets in some
       way other than `tornado.netutil.bind_sockets`.

    """
    def __init__(self, request_callback, no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None, protocol=None, **kwargs):
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        self.protocol = protocol
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options,
                           **kwargs)

    def handle_stream(self, stream, address):
        HTTPConnection(stream, address, self.request_callback,
                       self.no_keep_alive, self.xheaders, self.protocol)


class _BadRequestException(Exception):
    """Exception class for malformed HTTP requests."""
    pass


class HTTPConnection(object):
    """Handles a connection to an HTTP client, executing HTTP requests.

    We parse HTTP headers and bodies, and execute the request callback
    until the HTTP conection is closed.
    """
    def __init__(self, stream, address, request_callback, no_keep_alive=False,
                 xheaders=False, protocol=None):
        self.stream = stream
        self.address = address
        # Save the socket's address family now so we know how to
        # interpret self.address even after the stream is closed
        # and its socket attribute replaced with None.
        self.address_family = stream.socket.family
        self.request_callback = request_callback
        self.no_keep_alive = no_keep_alive
        self.xheaders = xheaders
        self.protocol = protocol
        self._clear_request_state()
        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = stack_context.wrap(self._on_headers)
        self.stream.set_close_callback(self._on_connection_close)
        self.stream.read_until(b"\r\n\r\n", self._header_callback)

    def _clear_request_state(self):
        """Clears the per-request state.

        This is run in between requests to allow the previous handler
        to be garbage collected (and prevent spurious close callbacks),
        and when the connection is closed (to break up cycles and
        facilitate garbage collection in cpython).
        """
        self._request = None
        self._request_finished = False
        self._write_callback = None
        self._close_callback = None

    def set_close_callback(self, callback):
        """Sets a callback that will be run when the connection is closed.

        Use this instead of accessing
        `HTTPConnection.stream.set_close_callback
        <.BaseIOStream.set_close_callback>` directly (which was the
        recommended approach prior to Tornado 3.0).
        """
        self._close_callback = stack_context.wrap(callback)

    def _on_connection_close(self):
        if self._close_callback is not None:
            callback = self._close_callback
            self._close_callback = None
            callback()
        # Delete any unfinished callbacks to break up reference cycles.
        self._header_callback = None
        self._clear_request_state()

    def close(self):
        self.stream.close()
        # Remove this reference to self, which would otherwise cause a
        # cycle and delay garbage collection of this connection.
        self._header_callback = None
        self._clear_request_state()

    def write(self, chunk, callback=None):
        """Writes a chunk of output to the stream."""
        if not self.stream.closed():
            self._write_callback = stack_context.wrap(callback)
            self.stream.write(chunk, self._on_write_complete)

    def finish(self):
        """Finishes the request."""
        self._request_finished = True
        # No more data is coming, so instruct TCP to send any remaining
        # data immediately instead of waiting for a full packet or ack.
        self.stream.set_nodelay(True)
        if not self.stream.writing():
            self._finish_request()

    def _on_write_complete(self):
        if self._write_callback is not None:
            callback = self._write_callback
            self._write_callback = None
            callback()
        # _on_write_complete is enqueued on the IOLoop whenever the
        # IOStream's write buffer becomes empty, but it's possible for
        # another callback that runs on the IOLoop before it to
        # simultaneously write more data and finish the request.  If
        # there is still data in the IOStream, a future
        # _on_write_complete will be responsible for calling
        # _finish_request.
        if self._request_finished and not self.stream.writing():
            self._finish_request()

    def _finish_request(self):
        if self.no_keep_alive or self._request is None:
            disconnect = True
        else:
            connection_header = self._request.headers.get("Connection")
            if connection_header is not None:
                connection_header = connection_header.lower()
            if self._request.supports_http_1_1():
                disconnect = connection_header == "close"
            elif ("Content-Length" in self._request.headers
                    or self._request.method in ("HEAD", "GET")):
                disconnect = connection_header != "keep-alive"
            else:
                disconnect = True
        self._clear_request_state()
        if disconnect:
            self.close()
            return
        try:
            # Use a try/except instead of checking stream.closed()
            # directly, because in some cases the stream doesn't discover
            # that it's closed until you try to read from it.
            self.stream.read_until(b"\r\n\r\n", self._header_callback)

            # Turn Nagle's algorithm back on, leaving the stream in its
            # default state for the next request.
            self.stream.set_nodelay(False)
        except iostream.StreamClosedError:
            self.close()

    def _on_headers(self, data):
        try:
            data = native_str(data.decode('latin1'))
            eol = data.find("\r\n")
            start_line = data[:eol]
            try:
                method, uri, version = start_line.split(" ")
            except ValueError:
                raise _BadRequestException("Malformed HTTP request line")
            if not version.startswith("HTTP/"):
                raise _BadRequestException("Malformed HTTP version in HTTP Request-Line")
            try:
                headers = httputil.HTTPHeaders.parse(data[eol:])
            except ValueError:
                # Probably from split() if there was no ':' in the line
                raise _BadRequestException("Malformed HTTP headers")

            # HTTPRequest wants an IP, not a full socket address
            if self.address_family in (socket.AF_INET, socket.AF_INET6):
                remote_ip = self.address[0]
            else:
                # Unix (or other) socket; fake the remote address
                remote_ip = '0.0.0.0'

            self._request = HTTPRequest(
                connection=self, method=method, uri=uri, version=version,
                headers=headers, remote_ip=remote_ip, protocol=self.protocol)

            content_length = headers.get("Content-Length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.stream.max_buffer_size:
                    raise _BadRequestException("Content-Length too long")
                if headers.get("Expect") == "100-continue":
                    self.stream.write(b"HTTP/1.1 100 (Continue)\r\n\r\n")
                self.stream.read_bytes(content_length, self._on_request_body)
                return

            self.request_callback(self._request)
        except _BadRequestException as e:
            gen_log.info("Malformed HTTP request from %s: %s",
                         self.address[0], e)
            self.close()
            return

    def _on_request_body(self, data):
        self._request.body = data
        if self._request.method in ("POST", "PATCH", "PUT"):
            httputil.parse_body_arguments(
                self._request.headers.get("Content-Type", ""), data,
                self._request.arguments, self._request.files)
        self.request_callback(self._request)


class HTTPRequest(object):
    """A single HTTP request.

    All attributes are type `str` unless otherwise noted.

    .. attribute:: method

       HTTP request method, e.g. "GET" or "POST"

    .. attribute:: uri

       The requested uri.

    .. attribute:: path

       The path portion of `uri`

    .. attribute:: query

       The query portion of `uri`

    .. attribute:: version

       HTTP version specified in request, e.g. "HTTP/1.1"

    .. attribute:: headers

       `.HTTPHeaders` dictionary-like object for request headers.  Acts like
       a case-insensitive dictionary with additional methods for repeated
       headers.

    .. attribute:: body

       Request body, if present, as a byte string.

    .. attribute:: remote_ip

       Client's IP address as a string.  If ``HTTPServer.xheaders`` is set,
       will pass along the real IP address provided by a load balancer
       in the ``X-Real-Ip`` or ``X-Forwarded-For`` header.

    .. versionchanged:: 3.1
       The list format of ``X-Forwarded-For`` is now supported.

    .. attribute:: protocol

       The protocol used, either "http" or "https".  If ``HTTPServer.xheaders``
       is set, will pass along the protocol used by a load balancer if
       reported via an ``X-Scheme`` header.

    .. attribute:: host

       The requested hostname, usually taken from the ``Host`` header.

    .. attribute:: arguments

       GET/POST arguments are available in the arguments property, which
       maps arguments names to lists of values (to support multiple values
       for individual names). Names are of type `str`, while arguments
       are byte strings.  Note that this is different from
       `.RequestHandler.get_argument`, which returns argument values as
       unicode strings.

    .. attribute:: files

       File uploads are available in the files property, which maps file
       names to lists of `.HTTPFile`.

    .. attribute:: connection

       An HTTP request is attached to a single HTTP connection, which can
       be accessed through the "connection" attribute. Since connections
       are typically kept open in HTTP/1.1, multiple requests can be handled
       sequentially on a single connection.
    """
    def __init__(self, method, uri, version="HTTP/1.0", headers=None,
                 body=None, remote_ip=None, protocol=None, host=None,
                 files=None, connection=None):
        self.method = method
        self.uri = uri
        self.version = version
        self.headers = headers or httputil.HTTPHeaders()
        self.body = body or ""

        # set remote IP and protocol
        self.remote_ip = remote_ip
        if protocol:
            self.protocol = protocol
        elif connection and isinstance(connection.stream,
                                       iostream.SSLIOStream):
            self.protocol = "https"
        else:
            self.protocol = "http"

        # xheaders can override the defaults
        if connection and connection.xheaders:
            # Squid uses X-Forwarded-For, others use X-Real-Ip
            ip = self.headers.get("X-Forwarded-For", self.remote_ip)
            ip = ip.split(',')[-1].strip()
            ip = self.headers.get(
                "X-Real-Ip", ip)
            if netutil.is_valid_ip(ip):
                self.remote_ip = ip
            # AWS uses X-Forwarded-Proto
            proto = self.headers.get(
                "X-Scheme", self.headers.get("X-Forwarded-Proto", self.protocol))
            if proto in ("http", "https"):
                self.protocol = proto

        self.host = host or self.headers.get("Host") or "127.0.0.1"
        self.files = files or {}
        self.connection = connection
        self._start_time = time.time()
        self._finish_time = None

        self.path, sep, self.query = uri.partition('?')
        self.arguments = parse_qs_bytes(self.query, keep_blank_values=True)

    def supports_http_1_1(self):
        """Returns True if this request supports HTTP/1.1 semantics"""
        return self.version == "HTTP/1.1"

    @property
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try:
                    self._cookies.load(
                        native_str(self.headers["Cookie"]))
                except Exception:
                    self._cookies = {}
        return self._cookies

    def write(self, chunk, callback=None):
        """Writes the given chunk to the response stream."""
        assert isinstance(chunk, bytes_type)
        self.connection.write(chunk, callback=callback)

    def finish(self):
        """Finishes this HTTP request on the open connection."""
        self.connection.finish()
        self._finish_time = time.time()

    def full_url(self):
        """Reconstructs the full URL for this request."""
        return self.protocol + "://" + self.host + self.uri

    def request_time(self):
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time

    def get_ssl_certificate(self, binary_form=False):
        """Returns the client's SSL certificate, if any.

        To use client certificates, the HTTPServer must have been constructed
        with cert_reqs set in ssl_options, e.g.::

            server = HTTPServer(app,
                ssl_options=dict(
                    certfile="foo.crt",
                    keyfile="foo.key",
                    cert_reqs=ssl.CERT_REQUIRED,
                    ca_certs="cacert.crt"))

        By default, the return value is a dictionary (or None, if no
        client certificate is present).  If ``binary_form`` is true, a
        DER-encoded form of the certificate is returned instead.  See
        SSLSocket.getpeercert() in the standard library for more
        details.
        http://docs.python.org/library/ssl.html#sslsocket-objects
        """
        try:
            return self.connection.stream.socket.getpeercert(
                binary_form=binary_form)
        except ssl.SSLError:
            return None

    def __repr__(self):
        attrs = ("protocol", "host", "method", "uri", "version", "remote_ip")
        args = ", ".join(["%s=%r" % (n, getattr(self, n)) for n in attrs])
        return "%s(%s, headers=%s)" % (
            self.__class__.__name__, args, dict(self.headers))

########NEW FILE########
__FILENAME__ = httputil
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""HTTP utility code shared by clients and servers."""

from __future__ import absolute_import, division, print_function, with_statement

import calendar
import collections
import datetime
import email.utils
import numbers
import time

from tornado.escape import native_str, parse_qs_bytes, utf8
from tornado.log import gen_log
from tornado.util import ObjectDict

try:
    from httplib import responses  # py2
except ImportError:
    from http.client import responses  # py3

# responses is unused in this file, but we re-export it to other files.
# Reference it so pyflakes doesn't complain.
responses

try:
    from urllib import urlencode  # py2
except ImportError:
    from urllib.parse import urlencode  # py3


class _NormalizedHeaderCache(dict):
    """Dynamic cached mapping of header names to Http-Header-Case.

    Implemented as a dict subclass so that cache hits are as fast as a
    normal dict lookup, without the overhead of a python function
    call.

    >>> normalized_headers = _NormalizedHeaderCache(10)
    >>> normalized_headers["coNtent-TYPE"]
    'Content-Type'
    """
    def __init__(self, size):
        super(_NormalizedHeaderCache, self).__init__()
        self.size = size
        self.queue = collections.deque()

    def __missing__(self, key):
        normalized = "-".join([w.capitalize() for w in key.split("-")])
        self[key] = normalized
        self.queue.append(key)
        if len(self.queue) > self.size:
            # Limit the size of the cache.  LRU would be better, but this
            # simpler approach should be fine.  In Python 2.7+ we could
            # use OrderedDict (or in 3.2+, @functools.lru_cache).
            old_key = self.queue.popleft()
            del self[old_key]
        return normalized

_normalized_headers = _NormalizedHeaderCache(1000)


class HTTPHeaders(dict):
    """A dictionary that maintains ``Http-Header-Case`` for all keys.

    Supports multiple values per key via a pair of new methods,
    `add()` and `get_list()`.  The regular dictionary interface
    returns a single value per key, with multiple values joined by a
    comma.

    >>> h = HTTPHeaders({"content-type": "text/html"})
    >>> list(h.keys())
    ['Content-Type']
    >>> h["Content-Type"]
    'text/html'

    >>> h.add("Set-Cookie", "A=B")
    >>> h.add("Set-Cookie", "C=D")
    >>> h["set-cookie"]
    'A=B,C=D'
    >>> h.get_list("set-cookie")
    ['A=B', 'C=D']

    >>> for (k,v) in sorted(h.get_all()):
    ...    print('%s: %s' % (k,v))
    ...
    Content-Type: text/html
    Set-Cookie: A=B
    Set-Cookie: C=D
    """
    def __init__(self, *args, **kwargs):
        # Don't pass args or kwargs to dict.__init__, as it will bypass
        # our __setitem__
        dict.__init__(self)
        self._as_list = {}
        self._last_key = None
        if (len(args) == 1 and len(kwargs) == 0 and
                isinstance(args[0], HTTPHeaders)):
            # Copy constructor
            for k, v in args[0].get_all():
                self.add(k, v)
        else:
            # Dict-style initialization
            self.update(*args, **kwargs)

    # new public methods

    def add(self, name, value):
        """Adds a new value for the given key."""
        norm_name = _normalized_headers[name]
        self._last_key = norm_name
        if norm_name in self:
            # bypass our override of __setitem__ since it modifies _as_list
            dict.__setitem__(self, norm_name,
                             native_str(self[norm_name]) + ',' +
                             native_str(value))
            self._as_list[norm_name].append(value)
        else:
            self[norm_name] = value

    def get_list(self, name):
        """Returns all values for the given header as a list."""
        norm_name = _normalized_headers[name]
        return self._as_list.get(norm_name, [])

    def get_all(self):
        """Returns an iterable of all (name, value) pairs.

        If a header has multiple values, multiple pairs will be
        returned with the same name.
        """
        for name, values in self._as_list.items():
            for value in values:
                yield (name, value)

    def parse_line(self, line):
        """Updates the dictionary with a single header line.

        >>> h = HTTPHeaders()
        >>> h.parse_line("Content-Type: text/html")
        >>> h.get('content-type')
        'text/html'
        """
        if line[0].isspace():
            # continuation of a multi-line header
            new_part = ' ' + line.lstrip()
            self._as_list[self._last_key][-1] += new_part
            dict.__setitem__(self, self._last_key,
                             self[self._last_key] + new_part)
        else:
            name, value = line.split(":", 1)
            self.add(name, value.strip())

    @classmethod
    def parse(cls, headers):
        """Returns a dictionary from HTTP header text.

        >>> h = HTTPHeaders.parse("Content-Type: text/html\\r\\nContent-Length: 42\\r\\n")
        >>> sorted(h.items())
        [('Content-Length', '42'), ('Content-Type', 'text/html')]
        """
        h = cls()
        for line in headers.splitlines():
            if line:
                h.parse_line(line)
        return h

    # dict implementation overrides

    def __setitem__(self, name, value):
        norm_name = _normalized_headers[name]
        dict.__setitem__(self, norm_name, value)
        self._as_list[norm_name] = [value]

    def __getitem__(self, name):
        return dict.__getitem__(self, _normalized_headers[name])

    def __delitem__(self, name):
        norm_name = _normalized_headers[name]
        dict.__delitem__(self, norm_name)
        del self._as_list[norm_name]

    def __contains__(self, name):
        norm_name = _normalized_headers[name]
        return dict.__contains__(self, norm_name)

    def get(self, name, default=None):
        return dict.get(self, _normalized_headers[name], default)

    def update(self, *args, **kwargs):
        # dict.update bypasses our __setitem__
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def copy(self):
        # default implementation returns dict(self), not the subclass
        return HTTPHeaders(self)


def url_concat(url, args):
    """Concatenate url and argument dictionary regardless of whether
    url has existing query parameters.

    >>> url_concat("http://example.com/foo?a=b", dict(c="d"))
    'http://example.com/foo?a=b&c=d'
    """
    if not args:
        return url
    if url[-1] not in ('?', '&'):
        url += '&' if ('?' in url) else '?'
    return url + urlencode(args)


class HTTPFile(ObjectDict):
    """Represents a file uploaded via a form.

    For backwards compatibility, its instance attributes are also
    accessible as dictionary keys.

    * ``filename``
    * ``body``
    * ``content_type``
    """
    pass


def _parse_request_range(range_header):
    """Parses a Range header.

    Returns either ``None`` or tuple ``(start, end)``.
    Note that while the HTTP headers use inclusive byte positions,
    this method returns indexes suitable for use in slices.

    >>> start, end = _parse_request_range("bytes=1-2")
    >>> start, end
    (1, 3)
    >>> [0, 1, 2, 3, 4][start:end]
    [1, 2]
    >>> _parse_request_range("bytes=6-")
    (6, None)
    >>> _parse_request_range("bytes=-6")
    (-6, None)
    >>> _parse_request_range("bytes=-0")
    (None, 0)
    >>> _parse_request_range("bytes=")
    (None, None)
    >>> _parse_request_range("foo=42")
    >>> _parse_request_range("bytes=1-2,6-10")

    Note: only supports one range (ex, ``bytes=1-2,6-10`` is not allowed).

    See [0] for the details of the range header.

    [0]: http://greenbytes.de/tech/webdav/draft-ietf-httpbis-p5-range-latest.html#byte.ranges
    """
    unit, _, value = range_header.partition("=")
    unit, value = unit.strip(), value.strip()
    if unit != "bytes":
        return None
    start_b, _, end_b = value.partition("-")
    try:
        start = _int_or_none(start_b)
        end = _int_or_none(end_b)
    except ValueError:
        return None
    if end is not None:
        if start is None:
            if end != 0:
                start = -end
                end = None
        else:
            end += 1
    return (start, end)


def _get_content_range(start, end, total):
    """Returns a suitable Content-Range header:

    >>> print(_get_content_range(None, 1, 4))
    bytes 0-0/4
    >>> print(_get_content_range(1, 3, 4))
    bytes 1-2/4
    >>> print(_get_content_range(None, None, 4))
    bytes 0-3/4
    """
    start = start or 0
    end = (end or total) - 1
    return "bytes %s-%s/%s" % (start, end, total)


def _int_or_none(val):
    val = val.strip()
    if val == "":
        return None
    return int(val)


def parse_body_arguments(content_type, body, arguments, files):
    """Parses a form request body.

    Supports ``application/x-www-form-urlencoded`` and
    ``multipart/form-data``.  The ``content_type`` parameter should be
    a string and ``body`` should be a byte string.  The ``arguments``
    and ``files`` parameters are dictionaries that will be updated
    with the parsed contents.
    """
    if content_type.startswith("application/x-www-form-urlencoded"):
        uri_arguments = parse_qs_bytes(native_str(body), keep_blank_values=True)
        for name, values in uri_arguments.items():
            if values:
                arguments.setdefault(name, []).extend(values)
    elif content_type.startswith("multipart/form-data"):
        fields = content_type.split(";")
        for field in fields:
            k, sep, v = field.strip().partition("=")
            if k == "boundary" and v:
                parse_multipart_form_data(utf8(v), body, arguments, files)
                break
        else:
            gen_log.warning("Invalid multipart/form-data")


def parse_multipart_form_data(boundary, data, arguments, files):
    """Parses a ``multipart/form-data`` body.

    The ``boundary`` and ``data`` parameters are both byte strings.
    The dictionaries given in the arguments and files parameters
    will be updated with the contents of the body.
    """
    # The standard allows for the boundary to be quoted in the header,
    # although it's rare (it happens at least for google app engine
    # xmpp).  I think we're also supposed to handle backslash-escapes
    # here but I'll save that until we see a client that uses them
    # in the wild.
    if boundary.startswith(b'"') and boundary.endswith(b'"'):
        boundary = boundary[1:-1]
    final_boundary_index = data.rfind(b"--" + boundary + b"--")
    if final_boundary_index == -1:
        gen_log.warning("Invalid multipart/form-data: no final boundary")
        return
    parts = data[:final_boundary_index].split(b"--" + boundary + b"\r\n")
    for part in parts:
        if not part:
            continue
        eoh = part.find(b"\r\n\r\n")
        if eoh == -1:
            gen_log.warning("multipart/form-data missing headers")
            continue
        headers = HTTPHeaders.parse(part[:eoh].decode("utf-8"))
        disp_header = headers.get("Content-Disposition", "")
        disposition, disp_params = _parse_header(disp_header)
        if disposition != "form-data" or not part.endswith(b"\r\n"):
            gen_log.warning("Invalid multipart/form-data")
            continue
        value = part[eoh + 4:-2]
        if not disp_params.get("name"):
            gen_log.warning("multipart/form-data value missing name")
            continue
        name = disp_params["name"]
        if disp_params.get("filename"):
            ctype = headers.get("Content-Type", "application/unknown")
            files.setdefault(name, []).append(HTTPFile(
                filename=disp_params["filename"], body=value,
                content_type=ctype))
        else:
            arguments.setdefault(name, []).append(value)


def format_timestamp(ts):
    """Formats a timestamp in the format used by HTTP.

    The argument may be a numeric timestamp as returned by `time.time`,
    a time tuple as returned by `time.gmtime`, or a `datetime.datetime`
    object.

    >>> format_timestamp(1359312200)
    'Sun, 27 Jan 2013 18:43:20 GMT'
    """
    if isinstance(ts, numbers.Real):
        pass
    elif isinstance(ts, (tuple, time.struct_time)):
        ts = calendar.timegm(ts)
    elif isinstance(ts, datetime.datetime):
        ts = calendar.timegm(ts.utctimetuple())
    else:
        raise TypeError("unknown timestamp type: %r" % ts)
    return email.utils.formatdate(ts, usegmt=True)

# _parseparam and _parse_header are copied and modified from python2.7's cgi.py
# The original 2.7 version of this code did not correctly support some
# combinations of semicolons and double quotes.


def _parseparam(s):
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def _parse_header(line):
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    """
    parts = _parseparam(';' + line)
    key = next(parts)
    pdict = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict


def doctests():
    import doctest
    return doctest.DocTestSuite()

########NEW FILE########
__FILENAME__ = ioloop
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""An I/O event loop for non-blocking sockets.

Typical applications will use a single `IOLoop` object, in the
`IOLoop.instance` singleton.  The `IOLoop.start` method should usually
be called at the end of the ``main()`` function.  Atypical applications may
use more than one `IOLoop`, such as one `IOLoop` per thread, or per `unittest`
case.

In addition to I/O events, the `IOLoop` can also schedule time-based events.
`IOLoop.add_timeout` is a non-blocking alternative to `time.sleep`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import datetime
import errno
import functools
import heapq
import logging
import numbers
import os
import select
import sys
import threading
import time
import traceback

from tornado.concurrent import Future, TracebackFuture
from tornado.log import app_log, gen_log
from tornado import stack_context
from tornado.util import Configurable

try:
    import signal
except ImportError:
    signal = None

try:
    import thread  # py2
except ImportError:
    import _thread as thread  # py3

from tornado.platform.auto import set_close_exec, Waker


class TimeoutError(Exception):
    pass


class IOLoop(Configurable):
    """A level-triggered I/O loop.

    We use ``epoll`` (Linux) or ``kqueue`` (BSD and Mac OS X) if they
    are available, or else we fall back on select(). If you are
    implementing a system that needs to handle thousands of
    simultaneous connections, you should use a system that supports
    either ``epoll`` or ``kqueue``.

    Example usage for a simple TCP server::

        import errno
        import functools
        import ioloop
        import socket

        def connection_ready(sock, fd, events):
            while True:
                try:
                    connection, address = sock.accept()
                except socket.error, e:
                    if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                        raise
                    return
                connection.setblocking(0)
                handle_connection(connection, address)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind(("", port))
        sock.listen(128)

        io_loop = ioloop.IOLoop.instance()
        callback = functools.partial(connection_ready, sock)
        io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
        io_loop.start()

    """
    # Constants from the epoll module
    _EPOLLIN = 0x001
    _EPOLLPRI = 0x002
    _EPOLLOUT = 0x004
    _EPOLLERR = 0x008
    _EPOLLHUP = 0x010
    _EPOLLRDHUP = 0x2000
    _EPOLLONESHOT = (1 << 30)
    _EPOLLET = (1 << 31)

    # Our events map exactly to the epoll events
    NONE = 0
    READ = _EPOLLIN
    WRITE = _EPOLLOUT
    ERROR = _EPOLLERR | _EPOLLHUP

    # Global lock for creating global IOLoop instance
    _instance_lock = threading.Lock()

    _current = threading.local()

    @staticmethod
    def instance():
        """Returns a global `IOLoop` instance.

        Most applications have a single, global `IOLoop` running on the
        main thread.  Use this method to get this instance from
        another thread.  To get the current thread's `IOLoop`, use `current()`.
        """
        if not hasattr(IOLoop, "_instance"):
            with IOLoop._instance_lock:
                if not hasattr(IOLoop, "_instance"):
                    # New instance after double check
                    IOLoop._instance = IOLoop()
        return IOLoop._instance

    @staticmethod
    def initialized():
        """Returns true if the singleton instance has been created."""
        return hasattr(IOLoop, "_instance")

    def install(self):
        """Installs this `IOLoop` object as the singleton instance.

        This is normally not necessary as `instance()` will create
        an `IOLoop` on demand, but you may want to call `install` to use
        a custom subclass of `IOLoop`.
        """
        assert not IOLoop.initialized()
        IOLoop._instance = self

    @staticmethod
    def current():
        """Returns the current thread's `IOLoop`.

        If an `IOLoop` is currently running or has been marked as current
        by `make_current`, returns that instance.  Otherwise returns
        `IOLoop.instance()`, i.e. the main thread's `IOLoop`.

        A common pattern for classes that depend on ``IOLoops`` is to use
        a default argument to enable programs with multiple ``IOLoops``
        but not require the argument for simpler applications::

            class MyClass(object):
                def __init__(self, io_loop=None):
                    self.io_loop = io_loop or IOLoop.current()

        In general you should use `IOLoop.current` as the default when
        constructing an asynchronous object, and use `IOLoop.instance`
        when you mean to communicate to the main thread from a different
        one.
        """
        current = getattr(IOLoop._current, "instance", None)
        if current is None:
            return IOLoop.instance()
        return current

    def make_current(self):
        """Makes this the `IOLoop` for the current thread.

        An `IOLoop` automatically becomes current for its thread
        when it is started, but it is sometimes useful to call
        `make_current` explictly before starting the `IOLoop`,
        so that code run at startup time can find the right
        instance.
        """
        IOLoop._current.instance = self

    @staticmethod
    def clear_current():
        IOLoop._current.instance = None

    @classmethod
    def configurable_base(cls):
        return IOLoop

    @classmethod
    def configurable_default(cls):
        if hasattr(select, "epoll"):
            from tornado.platform.epoll import EPollIOLoop
            return EPollIOLoop
        if hasattr(select, "kqueue"):
            # Python 2.6+ on BSD or Mac
            from tornado.platform.kqueue import KQueueIOLoop
            return KQueueIOLoop
        from tornado.platform.select import SelectIOLoop
        return SelectIOLoop

    def initialize(self):
        pass

    def close(self, all_fds=False):
        """Closes the `IOLoop`, freeing any resources used.

        If ``all_fds`` is true, all file descriptors registered on the
        IOLoop will be closed (not just the ones created by the
        `IOLoop` itself).

        Many applications will only use a single `IOLoop` that runs for the
        entire lifetime of the process.  In that case closing the `IOLoop`
        is not necessary since everything will be cleaned up when the
        process exits.  `IOLoop.close` is provided mainly for scenarios
        such as unit tests, which create and destroy a large number of
        ``IOLoops``.

        An `IOLoop` must be completely stopped before it can be closed.  This
        means that `IOLoop.stop()` must be called *and* `IOLoop.start()` must
        be allowed to return before attempting to call `IOLoop.close()`.
        Therefore the call to `close` will usually appear just after
        the call to `start` rather than near the call to `stop`.

        .. versionchanged:: 3.1
           If the `IOLoop` implementation supports non-integer objects
           for "file descriptors", those objects will have their
           ``close`` method when ``all_fds`` is true.
        """
        raise NotImplementedError()

    def add_handler(self, fd, handler, events):
        """Registers the given handler to receive the given events for fd.

        The ``events`` argument is a bitwise or of the constants
        ``IOLoop.READ``, ``IOLoop.WRITE``, and ``IOLoop.ERROR``.

        When an event occurs, ``handler(fd, events)`` will be run.
        """
        raise NotImplementedError()

    def update_handler(self, fd, events):
        """Changes the events we listen for fd."""
        raise NotImplementedError()

    def remove_handler(self, fd):
        """Stop listening for events on fd."""
        raise NotImplementedError()

    def set_blocking_signal_threshold(self, seconds, action):
        """Sends a signal if the `IOLoop` is blocked for more than
        ``s`` seconds.

        Pass ``seconds=None`` to disable.  Requires Python 2.6 on a unixy
        platform.

        The action parameter is a Python signal handler.  Read the
        documentation for the `signal` module for more information.
        If ``action`` is None, the process will be killed if it is
        blocked for too long.
        """
        raise NotImplementedError()

    def set_blocking_log_threshold(self, seconds):
        """Logs a stack trace if the `IOLoop` is blocked for more than
        ``s`` seconds.

        Equivalent to ``set_blocking_signal_threshold(seconds,
        self.log_stack)``
        """
        self.set_blocking_signal_threshold(seconds, self.log_stack)

    def log_stack(self, signal, frame):
        """Signal handler to log the stack trace of the current thread.

        For use with `set_blocking_signal_threshold`.
        """
        gen_log.warning('IOLoop blocked for %f seconds in\n%s',
                        self._blocking_signal_threshold,
                        ''.join(traceback.format_stack(frame)))

    def start(self):
        """Starts the I/O loop.

        The loop will run until one of the callbacks calls `stop()`, which
        will make the loop stop after the current event iteration completes.
        """
        raise NotImplementedError()

    def stop(self):
        """Stop the I/O loop.

        If the event loop is not currently running, the next call to `start()`
        will return immediately.

        To use asynchronous methods from otherwise-synchronous code (such as
        unit tests), you can start and stop the event loop like this::

          ioloop = IOLoop()
          async_method(ioloop=ioloop, callback=ioloop.stop)
          ioloop.start()

        ``ioloop.start()`` will return after ``async_method`` has run
        its callback, whether that callback was invoked before or
        after ``ioloop.start``.

        Note that even after `stop` has been called, the `IOLoop` is not
        completely stopped until `IOLoop.start` has also returned.
        Some work that was scheduled before the call to `stop` may still
        be run before the `IOLoop` shuts down.
        """
        raise NotImplementedError()

    def run_sync(self, func, timeout=None):
        """Starts the `IOLoop`, runs the given function, and stops the loop.

        If the function returns a `.Future`, the `IOLoop` will run
        until the future is resolved.  If it raises an exception, the
        `IOLoop` will stop and the exception will be re-raised to the
        caller.

        The keyword-only argument ``timeout`` may be used to set
        a maximum duration for the function.  If the timeout expires,
        a `TimeoutError` is raised.

        This method is useful in conjunction with `tornado.gen.coroutine`
        to allow asynchronous calls in a ``main()`` function::

            @gen.coroutine
            def main():
                # do stuff...

            if __name__ == '__main__':
                IOLoop.instance().run_sync(main)
        """
        future_cell = [None]

        def run():
            try:
                result = func()
            except Exception:
                future_cell[0] = TracebackFuture()
                future_cell[0].set_exc_info(sys.exc_info())
            else:
                if isinstance(result, Future):
                    future_cell[0] = result
                else:
                    future_cell[0] = Future()
                    future_cell[0].set_result(result)
            self.add_future(future_cell[0], lambda future: self.stop())
        self.add_callback(run)
        if timeout is not None:
            timeout_handle = self.add_timeout(self.time() + timeout, self.stop)
        self.start()
        if timeout is not None:
            self.remove_timeout(timeout_handle)
        if not future_cell[0].done():
            raise TimeoutError('Operation timed out after %s seconds' % timeout)
        return future_cell[0].result()

    def time(self):
        """Returns the current time according to the `IOLoop`'s clock.

        The return value is a floating-point number relative to an
        unspecified time in the past.

        By default, the `IOLoop`'s time function is `time.time`.  However,
        it may be configured to use e.g. `time.monotonic` instead.
        Calls to `add_timeout` that pass a number instead of a
        `datetime.timedelta` should use this function to compute the
        appropriate time, so they can work no matter what time function
        is chosen.
        """
        return time.time()

    def add_timeout(self, deadline, callback):
        """Runs the ``callback`` at the time ``deadline`` from the I/O loop.

        Returns an opaque handle that may be passed to
        `remove_timeout` to cancel.

        ``deadline`` may be a number denoting a time (on the same
        scale as `IOLoop.time`, normally `time.time`), or a
        `datetime.timedelta` object for a deadline relative to the
        current time.

        Note that it is not safe to call `add_timeout` from other threads.
        Instead, you must use `add_callback` to transfer control to the
        `IOLoop`'s thread, and then call `add_timeout` from there.
        """
        raise NotImplementedError()

    def remove_timeout(self, timeout):
        """Cancels a pending timeout.

        The argument is a handle as returned by `add_timeout`.  It is
        safe to call `remove_timeout` even if the callback has already
        been run.
        """
        raise NotImplementedError()

    def add_callback(self, callback, *args, **kwargs):
        """Calls the given callback on the next I/O loop iteration.

        It is safe to call this method from any thread at any time,
        except from a signal handler.  Note that this is the **only**
        method in `IOLoop` that makes this thread-safety guarantee; all
        other interaction with the `IOLoop` must be done from that
        `IOLoop`'s thread.  `add_callback()` may be used to transfer
        control from other threads to the `IOLoop`'s thread.

        To add a callback from a signal handler, see
        `add_callback_from_signal`.
        """
        raise NotImplementedError()

    def add_callback_from_signal(self, callback, *args, **kwargs):
        """Calls the given callback on the next I/O loop iteration.

        Safe for use from a Python signal handler; should not be used
        otherwise.

        Callbacks added with this method will be run without any
        `.stack_context`, to avoid picking up the context of the function
        that was interrupted by the signal.
        """
        raise NotImplementedError()

    def add_future(self, future, callback):
        """Schedules a callback on the ``IOLoop`` when the given
        `.Future` is finished.

        The callback is invoked with one argument, the
        `.Future`.
        """
        assert isinstance(future, Future)
        callback = stack_context.wrap(callback)
        future.add_done_callback(
            lambda future: self.add_callback(callback, future))

    def _run_callback(self, callback):
        """Runs a callback with error handling.

        For use in subclasses.
        """
        try:
            callback()
        except Exception:
            self.handle_callback_exception(callback)

    def handle_callback_exception(self, callback):
        """This method is called whenever a callback run by the `IOLoop`
        throws an exception.

        By default simply logs the exception as an error.  Subclasses
        may override this method to customize reporting of exceptions.

        The exception itself is not passed explicitly, but is available
        in `sys.exc_info`.
        """
        app_log.error("Exception in callback %r", callback, exc_info=True)


class PollIOLoop(IOLoop):
    """Base class for IOLoops built around a select-like function.

    For concrete implementations, see `tornado.platform.epoll.EPollIOLoop`
    (Linux), `tornado.platform.kqueue.KQueueIOLoop` (BSD and Mac), or
    `tornado.platform.select.SelectIOLoop` (all platforms).
    """
    def initialize(self, impl, time_func=None):
        super(PollIOLoop, self).initialize()
        self._impl = impl
        if hasattr(self._impl, 'fileno'):
            set_close_exec(self._impl.fileno())
        self.time_func = time_func or time.time
        self._handlers = {}
        self._events = {}
        self._callbacks = []
        self._callback_lock = threading.Lock()
        self._timeouts = []
        self._cancellations = 0
        self._running = False
        self._stopped = False
        self._closing = False
        self._thread_ident = None
        self._blocking_signal_threshold = None

        # Create a pipe that we send bogus data to when we want to wake
        # the I/O loop when it is idle
        self._waker = Waker()
        self.add_handler(self._waker.fileno(),
                         lambda fd, events: self._waker.consume(),
                         self.READ)

    def close(self, all_fds=False):
        with self._callback_lock:
            self._closing = True
        self.remove_handler(self._waker.fileno())
        if all_fds:
            for fd in self._handlers.keys():
                try:
                    close_method = getattr(fd, 'close', None)
                    if close_method is not None:
                        close_method()
                    else:
                        os.close(fd)
                except Exception:
                    gen_log.debug("error closing fd %s", fd, exc_info=True)
        self._waker.close()
        self._impl.close()

    def add_handler(self, fd, handler, events):
        self._handlers[fd] = stack_context.wrap(handler)
        self._impl.register(fd, events | self.ERROR)

    def update_handler(self, fd, events):
        self._impl.modify(fd, events | self.ERROR)

    def remove_handler(self, fd):
        self._handlers.pop(fd, None)
        self._events.pop(fd, None)
        try:
            self._impl.unregister(fd)
        except Exception:
            gen_log.debug("Error deleting fd from IOLoop", exc_info=True)

    def set_blocking_signal_threshold(self, seconds, action):
        if not hasattr(signal, "setitimer"):
            gen_log.error("set_blocking_signal_threshold requires a signal module "
                          "with the setitimer method")
            return
        self._blocking_signal_threshold = seconds
        if seconds is not None:
            signal.signal(signal.SIGALRM,
                          action if action is not None else signal.SIG_DFL)

    def start(self):
        if not logging.getLogger().handlers:
            # The IOLoop catches and logs exceptions, so it's
            # important that log output be visible.  However, python's
            # default behavior for non-root loggers (prior to python
            # 3.2) is to print an unhelpful "no handlers could be
            # found" message rather than the actual log entry, so we
            # must explicitly configure logging if we've made it this
            # far without anything.
            logging.basicConfig()
        if self._stopped:
            self._stopped = False
            return
        old_current = getattr(IOLoop._current, "instance", None)
        IOLoop._current.instance = self
        self._thread_ident = thread.get_ident()
        self._running = True

        # signal.set_wakeup_fd closes a race condition in event loops:
        # a signal may arrive at the beginning of select/poll/etc
        # before it goes into its interruptible sleep, so the signal
        # will be consumed without waking the select.  The solution is
        # for the (C, synchronous) signal handler to write to a pipe,
        # which will then be seen by select.
        #
        # In python's signal handling semantics, this only matters on the
        # main thread (fortunately, set_wakeup_fd only works on the main
        # thread and will raise a ValueError otherwise).
        #
        # If someone has already set a wakeup fd, we don't want to
        # disturb it.  This is an issue for twisted, which does its
        # SIGCHILD processing in response to its own wakeup fd being
        # written to.  As long as the wakeup fd is registered on the IOLoop,
        # the loop will still wake up and everything should work.
        old_wakeup_fd = None
        if hasattr(signal, 'set_wakeup_fd') and os.name == 'posix':
            # requires python 2.6+, unix.  set_wakeup_fd exists but crashes
            # the python process on windows.
            try:
                old_wakeup_fd = signal.set_wakeup_fd(self._waker.write_fileno())
                if old_wakeup_fd != -1:
                    # Already set, restore previous value.  This is a little racy,
                    # but there's no clean get_wakeup_fd and in real use the
                    # IOLoop is just started once at the beginning.
                    signal.set_wakeup_fd(old_wakeup_fd)
                    old_wakeup_fd = None
            except ValueError:  # non-main thread
                pass

        while True:
            poll_timeout = 3600.0

            # Prevent IO event starvation by delaying new callbacks
            # to the next iteration of the event loop.
            with self._callback_lock:
                callbacks = self._callbacks
                self._callbacks = []
            for callback in callbacks:
                self._run_callback(callback)

            if self._timeouts:
                now = self.time()
                while self._timeouts:
                    if self._timeouts[0].callback is None:
                        # the timeout was cancelled
                        heapq.heappop(self._timeouts)
                        self._cancellations -= 1
                    elif self._timeouts[0].deadline <= now:
                        timeout = heapq.heappop(self._timeouts)
                        self._run_callback(timeout.callback)
                    else:
                        seconds = self._timeouts[0].deadline - now
                        poll_timeout = min(seconds, poll_timeout)
                        break
                if (self._cancellations > 512
                        and self._cancellations > (len(self._timeouts) >> 1)):
                    # Clean up the timeout queue when it gets large and it's
                    # more than half cancellations.
                    self._cancellations = 0
                    self._timeouts = [x for x in self._timeouts
                                      if x.callback is not None]
                    heapq.heapify(self._timeouts)

            if self._callbacks:
                # If any callbacks or timeouts called add_callback,
                # we don't want to wait in poll() before we run them.
                poll_timeout = 0.0

            if not self._running:
                break

            if self._blocking_signal_threshold is not None:
                # clear alarm so it doesn't fire while poll is waiting for
                # events.
                signal.setitimer(signal.ITIMER_REAL, 0, 0)

            try:
                event_pairs = self._impl.poll(poll_timeout)
            except Exception as e:
                # Depending on python version and IOLoop implementation,
                # different exception types may be thrown and there are
                # two ways EINTR might be signaled:
                # * e.errno == errno.EINTR
                # * e.args is like (errno.EINTR, 'Interrupted system call')
                if (getattr(e, 'errno', None) == errno.EINTR or
                    (isinstance(getattr(e, 'args', None), tuple) and
                     len(e.args) == 2 and e.args[0] == errno.EINTR)):
                    continue
                else:
                    raise

            if self._blocking_signal_threshold is not None:
                signal.setitimer(signal.ITIMER_REAL,
                                 self._blocking_signal_threshold, 0)

            # Pop one fd at a time from the set of pending fds and run
            # its handler. Since that handler may perform actions on
            # other file descriptors, there may be reentrant calls to
            # this IOLoop that update self._events
            self._events.update(event_pairs)
            while self._events:
                fd, events = self._events.popitem()
                try:
                    self._handlers[fd](fd, events)
                except (OSError, IOError) as e:
                    if e.args[0] == errno.EPIPE:
                        # Happens when the client closes the connection
                        pass
                    else:
                        app_log.error("Exception in I/O handler for fd %s",
                                      fd, exc_info=True)
                except Exception:
                    app_log.error("Exception in I/O handler for fd %s",
                                  fd, exc_info=True)
        # reset the stopped flag so another start/stop pair can be issued
        self._stopped = False
        if self._blocking_signal_threshold is not None:
            signal.setitimer(signal.ITIMER_REAL, 0, 0)
        IOLoop._current.instance = old_current
        if old_wakeup_fd is not None:
            signal.set_wakeup_fd(old_wakeup_fd)

    def stop(self):
        self._running = False
        self._stopped = True
        self._waker.wake()

    def time(self):
        return self.time_func()

    def add_timeout(self, deadline, callback):
        timeout = _Timeout(deadline, stack_context.wrap(callback), self)
        heapq.heappush(self._timeouts, timeout)
        return timeout

    def remove_timeout(self, timeout):
        # Removing from a heap is complicated, so just leave the defunct
        # timeout object in the queue (see discussion in
        # http://docs.python.org/library/heapq.html).
        # If this turns out to be a problem, we could add a garbage
        # collection pass whenever there are too many dead timeouts.
        timeout.callback = None
        self._cancellations += 1

    def add_callback(self, callback, *args, **kwargs):
        with self._callback_lock:
            if self._closing:
                raise RuntimeError("IOLoop is closing")
            list_empty = not self._callbacks
            self._callbacks.append(functools.partial(
                stack_context.wrap(callback), *args, **kwargs))
        if list_empty and thread.get_ident() != self._thread_ident:
            # If we're in the IOLoop's thread, we know it's not currently
            # polling.  If we're not, and we added the first callback to an
            # empty list, we may need to wake it up (it may wake up on its
            # own, but an occasional extra wake is harmless).  Waking
            # up a polling IOLoop is relatively expensive, so we try to
            # avoid it when we can.
            self._waker.wake()

    def add_callback_from_signal(self, callback, *args, **kwargs):
        with stack_context.NullContext():
            if thread.get_ident() != self._thread_ident:
                # if the signal is handled on another thread, we can add
                # it normally (modulo the NullContext)
                self.add_callback(callback, *args, **kwargs)
            else:
                # If we're on the IOLoop's thread, we cannot use
                # the regular add_callback because it may deadlock on
                # _callback_lock.  Blindly insert into self._callbacks.
                # This is safe because the GIL makes list.append atomic.
                # One subtlety is that if the signal interrupted the
                # _callback_lock block in IOLoop.start, we may modify
                # either the old or new version of self._callbacks,
                # but either way will work.
                self._callbacks.append(functools.partial(
                    stack_context.wrap(callback), *args, **kwargs))


class _Timeout(object):
    """An IOLoop timeout, a UNIX timestamp and a callback"""

    # Reduce memory overhead when there are lots of pending callbacks
    __slots__ = ['deadline', 'callback']

    def __init__(self, deadline, callback, io_loop):
        if isinstance(deadline, numbers.Real):
            self.deadline = deadline
        elif isinstance(deadline, datetime.timedelta):
            self.deadline = io_loop.time() + _Timeout.timedelta_to_seconds(deadline)
        else:
            raise TypeError("Unsupported deadline %r" % deadline)
        self.callback = callback

    @staticmethod
    def timedelta_to_seconds(td):
        """Equivalent to td.total_seconds() (introduced in python 2.7)."""
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)

    # Comparison methods to sort by deadline, with object id as a tiebreaker
    # to guarantee a consistent ordering.  The heapq module uses __le__
    # in python2.5, and __lt__ in 2.6+ (sort() and most other comparisons
    # use __lt__).
    def __lt__(self, other):
        return ((self.deadline, id(self)) <
                (other.deadline, id(other)))

    def __le__(self, other):
        return ((self.deadline, id(self)) <=
                (other.deadline, id(other)))


class PeriodicCallback(object):
    """Schedules the given callback to be called periodically.

    The callback is called every ``callback_time`` milliseconds.

    `start` must be called after the `PeriodicCallback` is created.
    """
    def __init__(self, callback, callback_time, io_loop=None):
        self.callback = callback
        if callback_time <= 0:
            raise ValueError("Periodic callback must have a positive callback_time")
        self.callback_time = callback_time
        self.io_loop = io_loop or IOLoop.current()
        self._running = False
        self._timeout = None

    def start(self):
        """Starts the timer."""
        self._running = True
        self._next_timeout = self.io_loop.time()
        self._schedule_next()

    def stop(self):
        """Stops the timer."""
        self._running = False
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def _run(self):
        if not self._running:
            return
        try:
            self.callback()
        except Exception:
            app_log.error("Error in periodic callback", exc_info=True)
        self._schedule_next()

    def _schedule_next(self):
        if self._running:
            current_time = self.io_loop.time()
            while self._next_timeout <= current_time:
                self._next_timeout += self.callback_time / 1000.0
            self._timeout = self.io_loop.add_timeout(self._next_timeout, self._run)

########NEW FILE########
__FILENAME__ = iostream
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Utility classes to write to and read from non-blocking files and sockets.

Contents:

* `BaseIOStream`: Generic interface for reading and writing.
* `IOStream`: Implementation of BaseIOStream using non-blocking sockets.
* `SSLIOStream`: SSL-aware version of IOStream.
* `PipeIOStream`: Pipe-based IOStream implementation.
"""

from __future__ import absolute_import, division, print_function, with_statement

import collections
import errno
import numbers
import os
import socket
# import ssl
import sys
import re

from tornado import ioloop
from tornado.log import gen_log, app_log
from tornado.netutil import ssl_wrap_socket, ssl_match_hostname, SSLCertificateError
from tornado import stack_context
from tornado.util import bytes_type

try:
    from tornado.platform.posix import _set_nonblocking
except ImportError:
    _set_nonblocking = None


class StreamClosedError(IOError):
    """Exception raised by `IOStream` methods when the stream is closed.

    Note that the close callback is scheduled to run *after* other
    callbacks on the stream (to allow for buffered data to be processed),
    so you may see this error before you see the close callback.
    """
    pass


class BaseIOStream(object):
    """A utility class to write to and read from a non-blocking file or socket.

    We support a non-blocking ``write()`` and a family of ``read_*()`` methods.
    All of the methods take callbacks (since writing and reading are
    non-blocking and asynchronous).

    When a stream is closed due to an error, the IOStream's ``error``
    attribute contains the exception object.

    Subclasses must implement `fileno`, `close_fd`, `write_to_fd`,
    `read_from_fd`, and optionally `get_fd_error`.
    """
    def __init__(self, io_loop=None, max_buffer_size=None,
                 read_chunk_size=4096):
        self.io_loop = io_loop or ioloop.IOLoop.current()
        self.max_buffer_size = max_buffer_size or 104857600
        self.read_chunk_size = read_chunk_size
        self.error = None
        self._read_buffer = collections.deque()
        self._write_buffer = collections.deque()
        self._read_buffer_size = 0
        self._write_buffer_frozen = False
        self._read_delimiter = None
        self._read_regex = None
        self._read_bytes = None
        self._read_until_close = False
        self._read_callback = None
        self._streaming_callback = None
        self._write_callback = None
        self._close_callback = None
        self._connect_callback = None
        self._connecting = False
        self._state = None
        self._pending_callbacks = 0
        self._closed = False

    def fileno(self):
        """Returns the file descriptor for this stream."""
        raise NotImplementedError()

    def close_fd(self):
        """Closes the file underlying this stream.

        ``close_fd`` is called by `BaseIOStream` and should not be called
        elsewhere; other users should call `close` instead.
        """
        raise NotImplementedError()

    def write_to_fd(self, data):
        """Attempts to write ``data`` to the underlying file.

        Returns the number of bytes written.
        """
        raise NotImplementedError()

    def read_from_fd(self):
        """Attempts to read from the underlying file.

        Returns ``None`` if there was nothing to read (the socket
        returned `~errno.EWOULDBLOCK` or equivalent), otherwise
        returns the data.  When possible, should return no more than
        ``self.read_chunk_size`` bytes at a time.
        """
        raise NotImplementedError()

    def get_fd_error(self):
        """Returns information about any error on the underlying file.

        This method is called after the `.IOLoop` has signaled an error on the
        file descriptor, and should return an Exception (such as `socket.error`
        with additional information, or None if no such information is
        available.
        """
        return None

    def read_until_regex(self, regex, callback):
        """Run ``callback`` when we read the given regex pattern.

        The callback will get the data read (including the data that
        matched the regex and anything that came before it) as an argument.
        """
        self._set_read_callback(callback)
        self._read_regex = re.compile(regex)
        self._try_inline_read()

    def read_until(self, delimiter, callback):
        """Run ``callback`` when we read the given delimiter.

        The callback will get the data read (including the delimiter)
        as an argument.
        """
        self._set_read_callback(callback)
        self._read_delimiter = delimiter
        self._try_inline_read()

    def read_bytes(self, num_bytes, callback, streaming_callback=None):
        """Run callback when we read the given number of bytes.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.  Otherwise, the ``callback`` gets
        the data as an argument.
        """
        self._set_read_callback(callback)
        assert isinstance(num_bytes, numbers.Integral)
        self._read_bytes = num_bytes
        self._streaming_callback = stack_context.wrap(streaming_callback)
        self._try_inline_read()

    def read_until_close(self, callback, streaming_callback=None):
        """Reads all data from the socket until it is closed.

        If a ``streaming_callback`` is given, it will be called with chunks
        of data as they become available, and the argument to the final
        ``callback`` will be empty.  Otherwise, the ``callback`` gets the
        data as an argument.

        Subject to ``max_buffer_size`` limit from `IOStream` constructor if
        a ``streaming_callback`` is not used.
        """
        self._set_read_callback(callback)
        self._streaming_callback = stack_context.wrap(streaming_callback)
        if self.closed():
            if self._streaming_callback is not None:
                self._run_callback(self._streaming_callback,
                                   self._consume(self._read_buffer_size))
            self._run_callback(self._read_callback,
                               self._consume(self._read_buffer_size))
            self._streaming_callback = None
            self._read_callback = None
            return
        self._read_until_close = True
        self._streaming_callback = stack_context.wrap(streaming_callback)
        self._try_inline_read()

    def write(self, data, callback=None):
        """Write the given data to this stream.

        If ``callback`` is given, we call it when all of the buffered write
        data has been successfully written to the stream. If there was
        previously buffered write data and an old write callback, that
        callback is simply overwritten with this new callback.
        """
        assert isinstance(data, bytes_type)
        self._check_closed()
        # We use bool(_write_buffer) as a proxy for write_buffer_size>0,
        # so never put empty strings in the buffer.
        if data:
            # Break up large contiguous strings before inserting them in the
            # write buffer, so we don't have to recopy the entire thing
            # as we slice off pieces to send to the socket.
            WRITE_BUFFER_CHUNK_SIZE = 128 * 1024
            if len(data) > WRITE_BUFFER_CHUNK_SIZE:
                for i in range(0, len(data), WRITE_BUFFER_CHUNK_SIZE):
                    self._write_buffer.append(data[i:i + WRITE_BUFFER_CHUNK_SIZE])
            else:
                self._write_buffer.append(data)
        self._write_callback = stack_context.wrap(callback)
        if not self._connecting:
            self._handle_write()
            if self._write_buffer:
                self._add_io_state(self.io_loop.WRITE)
            self._maybe_add_error_listener()

    def set_close_callback(self, callback):
        """Call the given callback when the stream is closed."""
        self._close_callback = stack_context.wrap(callback)

    def close(self, exc_info=False):
        """Close this stream.

        If ``exc_info`` is true, set the ``error`` attribute to the current
        exception from `sys.exc_info` (or if ``exc_info`` is a tuple,
        use that instead of `sys.exc_info`).
        """
        if not self.closed():
            if exc_info:
                if not isinstance(exc_info, tuple):
                    exc_info = sys.exc_info()
                if any(exc_info):
                    self.error = exc_info[1]
            if self._read_until_close:
                if (self._streaming_callback is not None and
                        self._read_buffer_size):
                    self._run_callback(self._streaming_callback,
                                       self._consume(self._read_buffer_size))
                callback = self._read_callback
                self._read_callback = None
                self._read_until_close = False
                self._run_callback(callback,
                                   self._consume(self._read_buffer_size))
            if self._state is not None:
                self.io_loop.remove_handler(self.fileno())
                self._state = None
            self.close_fd()
            self._closed = True
        self._maybe_run_close_callback()

    def _maybe_run_close_callback(self):
        if (self.closed() and self._close_callback and
                self._pending_callbacks == 0):
            # if there are pending callbacks, don't run the close callback
            # until they're done (see _maybe_add_error_handler)
            cb = self._close_callback
            self._close_callback = None
            self._run_callback(cb)
            # Delete any unfinished callbacks to break up reference cycles.
            self._read_callback = self._write_callback = None

    def reading(self):
        """Returns true if we are currently reading from the stream."""
        return self._read_callback is not None

    def writing(self):
        """Returns true if we are currently writing to the stream."""
        return bool(self._write_buffer)

    def closed(self):
        """Returns true if the stream has been closed."""
        return self._closed

    def set_nodelay(self, value):
        """Sets the no-delay flag for this stream.

        By default, data written to TCP streams may be held for a time
        to make the most efficient use of bandwidth (according to
        Nagle's algorithm).  The no-delay flag requests that data be
        written as soon as possible, even if doing so would consume
        additional bandwidth.

        This flag is currently defined only for TCP-based ``IOStreams``.

        .. versionadded:: 3.1
        """
        pass

    def _handle_events(self, fd, events):
        if self.closed():
            gen_log.warning("Got events for closed stream %d", fd)
            return
        try:
            if events & self.io_loop.READ:
                self._handle_read()
            if self.closed():
                return
            if events & self.io_loop.WRITE:
                if self._connecting:
                    self._handle_connect()
                self._handle_write()
            if self.closed():
                return
            if events & self.io_loop.ERROR:
                self.error = self.get_fd_error()
                # We may have queued up a user callback in _handle_read or
                # _handle_write, so don't close the IOStream until those
                # callbacks have had a chance to run.
                self.io_loop.add_callback(self.close)
                return
            state = self.io_loop.ERROR
            if self.reading():
                state |= self.io_loop.READ
            if self.writing():
                state |= self.io_loop.WRITE
            if state == self.io_loop.ERROR:
                state |= self.io_loop.READ
            if state != self._state:
                assert self._state is not None, \
                    "shouldn't happen: _handle_events without self._state"
                self._state = state
                self.io_loop.update_handler(self.fileno(), self._state)
        except Exception:
            gen_log.error("Uncaught exception, closing connection.",
                          exc_info=True)
            self.close(exc_info=True)
            raise

    def _run_callback(self, callback, *args):
        def wrapper():
            self._pending_callbacks -= 1
            try:
                callback(*args)
            except Exception:
                app_log.error("Uncaught exception, closing connection.",
                              exc_info=True)
                # Close the socket on an uncaught exception from a user callback
                # (It would eventually get closed when the socket object is
                # gc'd, but we don't want to rely on gc happening before we
                # run out of file descriptors)
                self.close(exc_info=True)
                # Re-raise the exception so that IOLoop.handle_callback_exception
                # can see it and log the error
                raise
            self._maybe_add_error_listener()
        # We schedule callbacks to be run on the next IOLoop iteration
        # rather than running them directly for several reasons:
        # * Prevents unbounded stack growth when a callback calls an
        #   IOLoop operation that immediately runs another callback
        # * Provides a predictable execution context for e.g.
        #   non-reentrant mutexes
        # * Ensures that the try/except in wrapper() is run outside
        #   of the application's StackContexts
        with stack_context.NullContext():
            # stack_context was already captured in callback, we don't need to
            # capture it again for IOStream's wrapper.  This is especially
            # important if the callback was pre-wrapped before entry to
            # IOStream (as in HTTPConnection._header_callback), as we could
            # capture and leak the wrong context here.
            self._pending_callbacks += 1
            self.io_loop.add_callback(wrapper)

    def _handle_read(self):
        try:
            try:
                # Pretend to have a pending callback so that an EOF in
                # _read_to_buffer doesn't trigger an immediate close
                # callback.  At the end of this method we'll either
                # estabilsh a real pending callback via
                # _read_from_buffer or run the close callback.
                #
                # We need two try statements here so that
                # pending_callbacks is decremented before the `except`
                # clause below (which calls `close` and does need to
                # trigger the callback)
                self._pending_callbacks += 1
                while not self.closed():
                    # Read from the socket until we get EWOULDBLOCK or equivalent.
                    # SSL sockets do some internal buffering, and if the data is
                    # sitting in the SSL object's buffer select() and friends
                    # can't see it; the only way to find out if it's there is to
                    # try to read it.
                    if self._read_to_buffer() == 0:
                        break
            finally:
                self._pending_callbacks -= 1
        except Exception:
            gen_log.warning("error on read", exc_info=True)
            self.close(exc_info=True)
            return
        if self._read_from_buffer():
            return
        else:
            self._maybe_run_close_callback()

    def _set_read_callback(self, callback):
        assert not self._read_callback, "Already reading"
        self._read_callback = stack_context.wrap(callback)

    def _try_inline_read(self):
        """Attempt to complete the current read operation from buffered data.

        If the read can be completed without blocking, schedules the
        read callback on the next IOLoop iteration; otherwise starts
        listening for reads on the socket.
        """
        # See if we've already got the data from a previous read
        if self._read_from_buffer():
            return
        self._check_closed()
        try:
            try:
                # See comments in _handle_read about incrementing _pending_callbacks
                self._pending_callbacks += 1
                while not self.closed():
                    if self._read_to_buffer() == 0:
                        break
            finally:
                self._pending_callbacks -= 1
        except Exception:
            # If there was an in _read_to_buffer, we called close() already,
            # but couldn't run the close callback because of _pending_callbacks.
            # Before we escape from this function, run the close callback if
            # applicable.
            self._maybe_run_close_callback()
            raise
        if self._read_from_buffer():
            return
        self._maybe_add_error_listener()

    def _read_to_buffer(self):
        """Reads from the socket and appends the result to the read buffer.

        Returns the number of bytes read.  Returns 0 if there is nothing
        to read (i.e. the read returns EWOULDBLOCK or equivalent).  On
        error closes the socket and raises an exception.
        """
        try:
            chunk = self.read_from_fd()
        except (socket.error, IOError, OSError) as e:
            # ssl.SSLError is a subclass of socket.error
            if e.args[0] == errno.ECONNRESET:
                # Treat ECONNRESET as a connection close rather than
                # an error to minimize log spam  (the exception will
                # be available on self.error for apps that care).
                self.close(exc_info=True)
                return
            self.close(exc_info=True)
            raise
        if chunk is None:
            return 0
        self._read_buffer.append(chunk)
        self._read_buffer_size += len(chunk)
        if self._read_buffer_size >= self.max_buffer_size:
            gen_log.error("Reached maximum read buffer size")
            self.close()
            raise IOError("Reached maximum read buffer size")
        return len(chunk)

    def _read_from_buffer(self):
        """Attempts to complete the currently-pending read from the buffer.

        Returns True if the read was completed.
        """
        if self._streaming_callback is not None and self._read_buffer_size:
            bytes_to_consume = self._read_buffer_size
            if self._read_bytes is not None:
                bytes_to_consume = min(self._read_bytes, bytes_to_consume)
                self._read_bytes -= bytes_to_consume
            self._run_callback(self._streaming_callback,
                               self._consume(bytes_to_consume))
        if self._read_bytes is not None and self._read_buffer_size >= self._read_bytes:
            num_bytes = self._read_bytes
            callback = self._read_callback
            self._read_callback = None
            self._streaming_callback = None
            self._read_bytes = None
            self._run_callback(callback, self._consume(num_bytes))
            return True
        elif self._read_delimiter is not None:
            # Multi-byte delimiters (e.g. '\r\n') may straddle two
            # chunks in the read buffer, so we can't easily find them
            # without collapsing the buffer.  However, since protocols
            # using delimited reads (as opposed to reads of a known
            # length) tend to be "line" oriented, the delimiter is likely
            # to be in the first few chunks.  Merge the buffer gradually
            # since large merges are relatively expensive and get undone in
            # consume().
            if self._read_buffer:
                while True:
                    loc = self._read_buffer[0].find(self._read_delimiter)
                    if loc != -1:
                        callback = self._read_callback
                        delimiter_len = len(self._read_delimiter)
                        self._read_callback = None
                        self._streaming_callback = None
                        self._read_delimiter = None
                        self._run_callback(callback,
                                           self._consume(loc + delimiter_len))
                        return True
                    if len(self._read_buffer) == 1:
                        break
                    _double_prefix(self._read_buffer)
        elif self._read_regex is not None:
            if self._read_buffer:
                while True:
                    m = self._read_regex.search(self._read_buffer[0])
                    if m is not None:
                        callback = self._read_callback
                        self._read_callback = None
                        self._streaming_callback = None
                        self._read_regex = None
                        self._run_callback(callback, self._consume(m.end()))
                        return True
                    if len(self._read_buffer) == 1:
                        break
                    _double_prefix(self._read_buffer)
        return False

    def _handle_write(self):
        while self._write_buffer:
            try:
                if not self._write_buffer_frozen:
                    # On windows, socket.send blows up if given a
                    # write buffer that's too large, instead of just
                    # returning the number of bytes it was able to
                    # process.  Therefore we must not call socket.send
                    # with more than 128KB at a time.
                    _merge_prefix(self._write_buffer, 128 * 1024)
                num_bytes = self.write_to_fd(self._write_buffer[0])
                if num_bytes == 0:
                    # With OpenSSL, if we couldn't write the entire buffer,
                    # the very same string object must be used on the
                    # next call to send.  Therefore we suppress
                    # merging the write buffer after an incomplete send.
                    # A cleaner solution would be to set
                    # SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER, but this is
                    # not yet accessible from python
                    # (http://bugs.python.org/issue8240)
                    self._write_buffer_frozen = True
                    break
                self._write_buffer_frozen = False
                _merge_prefix(self._write_buffer, num_bytes)
                self._write_buffer.popleft()
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    self._write_buffer_frozen = True
                    break
                else:
                    if e.args[0] not in (errno.EPIPE, errno.ECONNRESET):
                        # Broken pipe errors are usually caused by connection
                        # reset, and its better to not log EPIPE errors to
                        # minimize log spam
                        gen_log.warning("Write error on %d: %s",
                                        self.fileno(), e)
                    self.close(exc_info=True)
                    return
        if not self._write_buffer and self._write_callback:
            callback = self._write_callback
            self._write_callback = None
            self._run_callback(callback)

    def _consume(self, loc):
        if loc == 0:
            return b""
        _merge_prefix(self._read_buffer, loc)
        self._read_buffer_size -= loc
        return self._read_buffer.popleft()

    def _check_closed(self):
        if self.closed():
            raise StreamClosedError("Stream is closed")

    def _maybe_add_error_listener(self):
        if self._state is None and self._pending_callbacks == 0:
            if self.closed():
                self._maybe_run_close_callback()
            else:
                self._add_io_state(ioloop.IOLoop.READ)

    def _add_io_state(self, state):
        """Adds `state` (IOLoop.{READ,WRITE} flags) to our event handler.

        Implementation notes: Reads and writes have a fast path and a
        slow path.  The fast path reads synchronously from socket
        buffers, while the slow path uses `_add_io_state` to schedule
        an IOLoop callback.  Note that in both cases, the callback is
        run asynchronously with `_run_callback`.

        To detect closed connections, we must have called
        `_add_io_state` at some point, but we want to delay this as
        much as possible so we don't have to set an `IOLoop.ERROR`
        listener that will be overwritten by the next slow-path
        operation.  As long as there are callbacks scheduled for
        fast-path ops, those callbacks may do more reads.
        If a sequence of fast-path ops do not end in a slow-path op,
        (e.g. for an @asynchronous long-poll request), we must add
        the error handler.  This is done in `_run_callback` and `write`
        (since the write callback is optional so we can have a
        fast-path write with no `_run_callback`)
        """
        if self.closed():
            # connection has been closed, so there can be no future events
            return
        if self._state is None:
            self._state = ioloop.IOLoop.ERROR | state
            with stack_context.NullContext():
                self.io_loop.add_handler(
                    self.fileno(), self._handle_events, self._state)
        elif not self._state & state:
            self._state = self._state | state
            self.io_loop.update_handler(self.fileno(), self._state)


class IOStream(BaseIOStream):
    r"""Socket-based `IOStream` implementation.

    This class supports the read and write methods from `BaseIOStream`
    plus a `connect` method.

    The ``socket`` parameter may either be connected or unconnected.
    For server operations the socket is the result of calling
    `socket.accept <socket.socket.accept>`.  For client operations the
    socket is created with `socket.socket`, and may either be
    connected before passing it to the `IOStream` or connected with
    `IOStream.connect`.

    A very simple (and broken) HTTP client using this class::

        import tornado.ioloop
        import tornado.iostream
        import socket

        def send_request():
            stream.write(b"GET / HTTP/1.0\r\nHost: friendfeed.com\r\n\r\n")
            stream.read_until(b"\r\n\r\n", on_headers)

        def on_headers(data):
            headers = {}
            for line in data.split(b"\r\n"):
               parts = line.split(b":")
               if len(parts) == 2:
                   headers[parts[0].strip()] = parts[1].strip()
            stream.read_bytes(int(headers[b"Content-Length"]), on_body)

        def on_body(data):
            print data
            stream.close()
            tornado.ioloop.IOLoop.instance().stop()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = tornado.iostream.IOStream(s)
        stream.connect(("friendfeed.com", 80), send_request)
        tornado.ioloop.IOLoop.instance().start()
    """
    def __init__(self, socket, *args, **kwargs):
        self.socket = socket
        self.socket.setblocking(False)
        super(IOStream, self).__init__(*args, **kwargs)

    def fileno(self):
        return self.socket.fileno()

    def close_fd(self):
        self.socket.close()
        self.socket = None

    def get_fd_error(self):
        errno = self.socket.getsockopt(socket.SOL_SOCKET,
                                       socket.SO_ERROR)
        return socket.error(errno, os.strerror(errno))

    def read_from_fd(self):
        try:
            chunk = self.socket.recv(self.read_chunk_size)
        except socket.error as e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk

    def write_to_fd(self, data):
        return self.socket.send(data)

    def connect(self, address, callback=None, server_hostname=None):
        """Connects the socket to a remote address without blocking.

        May only be called if the socket passed to the constructor was
        not previously connected.  The address parameter is in the
        same format as for `socket.connect <socket.socket.connect>`,
        i.e. a ``(host, port)`` tuple.  If ``callback`` is specified,
        it will be called when the connection is completed.

        If specified, the ``server_hostname`` parameter will be used
        in SSL connections for certificate validation (if requested in
        the ``ssl_options``) and SNI (if supported; requires
        Python 3.2+).

        Note that it is safe to call `IOStream.write
        <BaseIOStream.write>` while the connection is pending, in
        which case the data will be written as soon as the connection
        is ready.  Calling `IOStream` read methods before the socket is
        connected works on some platforms but is non-portable.
        """
        self._connecting = True
        try:
            self.socket.connect(address)
        except socket.error as e:
            # In non-blocking mode we expect connect() to raise an
            # exception with EINPROGRESS or EWOULDBLOCK.
            #
            # On freebsd, other errors such as ECONNREFUSED may be
            # returned immediately when attempting to connect to
            # localhost, so handle them the same way as an error
            # reported later in _handle_connect.
            if e.args[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                gen_log.warning("Connect error on fd %d: %s",
                                self.socket.fileno(), e)
                self.close(exc_info=True)
                return
        self._connect_callback = stack_context.wrap(callback)
        self._add_io_state(self.io_loop.WRITE)

    def _handle_connect(self):
        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err != 0:
            self.error = socket.error(err, os.strerror(err))
            # IOLoop implementations may vary: some of them return
            # an error state before the socket becomes writable, so
            # in that case a connection failure would be handled by the
            # error path in _handle_events instead of here.
            gen_log.warning("Connect error on fd %d: %s",
                            self.socket.fileno(), errno.errorcode[err])
            self.close()
            return
        if self._connect_callback is not None:
            callback = self._connect_callback
            self._connect_callback = None
            self._run_callback(callback)
        self._connecting = False

    def set_nodelay(self, value):
        if (self.socket is not None and
                self.socket.family in (socket.AF_INET, socket.AF_INET6)):
            try:
                self.socket.setsockopt(socket.IPPROTO_TCP,
                                       socket.TCP_NODELAY, 1 if value else 0)
            except socket.error as e:
                # Sometimes setsockopt will fail if the socket is closed
                # at the wrong time.  This can happen with HTTPServer
                # resetting the value to false between requests.
                if e.errno != errno.EINVAL:
                    raise


class SSLIOStream(IOStream):
    """A utility class to write to and read from a non-blocking SSL socket.

    If the socket passed to the constructor is already connected,
    it should be wrapped with::

        ssl.wrap_socket(sock, do_handshake_on_connect=False, **kwargs)

    before constructing the `SSLIOStream`.  Unconnected sockets will be
    wrapped when `IOStream.connect` is finished.
    """
    def __init__(self, *args, **kwargs):
        """The ``ssl_options`` keyword argument may either be a dictionary
        of keywords arguments for `ssl.wrap_socket`, or an `ssl.SSLContext`
        object.
        """
        self._ssl_options = kwargs.pop('ssl_options', {})
        super(SSLIOStream, self).__init__(*args, **kwargs)
        self._ssl_accepting = True
        self._handshake_reading = False
        self._handshake_writing = False
        self._ssl_connect_callback = None
        self._server_hostname = None

    def reading(self):
        return self._handshake_reading or super(SSLIOStream, self).reading()

    def writing(self):
        return self._handshake_writing or super(SSLIOStream, self).writing()

    def _do_ssl_handshake(self):
        # Based on code from test_ssl.py in the python stdlib
        try:
            self._handshake_reading = False
            self._handshake_writing = False
            self.socket.do_handshake()
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._handshake_reading = True
                return
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._handshake_writing = True
                return
            elif err.args[0] in (ssl.SSL_ERROR_EOF,
                                 ssl.SSL_ERROR_ZERO_RETURN):
                return self.close(exc_info=True)
            elif err.args[0] == ssl.SSL_ERROR_SSL:
                try:
                    peer = self.socket.getpeername()
                except Exception:
                    peer = '(not connected)'
                gen_log.warning("SSL Error on %d %s: %s",
                                self.socket.fileno(), peer, err)
                return self.close(exc_info=True)
            raise
        except socket.error as err:
            if err.args[0] in (errno.ECONNABORTED, errno.ECONNRESET):
                return self.close(exc_info=True)
        except AttributeError:
            # On Linux, if the connection was reset before the call to
            # wrap_socket, do_handshake will fail with an
            # AttributeError.
            return self.close(exc_info=True)
        else:
            self._ssl_accepting = False
            if not self._verify_cert(self.socket.getpeercert()):
                self.close()
                return
            if self._ssl_connect_callback is not None:
                callback = self._ssl_connect_callback
                self._ssl_connect_callback = None
                self._run_callback(callback)

    def _verify_cert(self, peercert):
        """Returns True if peercert is valid according to the configured
        validation mode and hostname.

        The ssl handshake already tested the certificate for a valid
        CA signature; the only thing that remains is to check
        the hostname.
        """
        if isinstance(self._ssl_options, dict):
            verify_mode = self._ssl_options.get('cert_reqs', ssl.CERT_NONE)
        elif isinstance(self._ssl_options, ssl.SSLContext):
            verify_mode = self._ssl_options.verify_mode
        assert verify_mode in (ssl.CERT_NONE, ssl.CERT_REQUIRED, ssl.CERT_OPTIONAL)
        if verify_mode == ssl.CERT_NONE or self._server_hostname is None:
            return True
        cert = self.socket.getpeercert()
        if cert is None and verify_mode == ssl.CERT_REQUIRED:
            gen_log.warning("No SSL certificate given")
            return False
        try:
            ssl_match_hostname(peercert, self._server_hostname)
        except SSLCertificateError:
            gen_log.warning("Invalid SSL certificate", exc_info=True)
            return False
        else:
            return True

    def _handle_read(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super(SSLIOStream, self)._handle_read()

    def _handle_write(self):
        if self._ssl_accepting:
            self._do_ssl_handshake()
            return
        super(SSLIOStream, self)._handle_write()

    def connect(self, address, callback=None, server_hostname=None):
        # Save the user's callback and run it after the ssl handshake
        # has completed.
        self._ssl_connect_callback = stack_context.wrap(callback)
        self._server_hostname = server_hostname
        super(SSLIOStream, self).connect(address, callback=None)

    def _handle_connect(self):
        # When the connection is complete, wrap the socket for SSL
        # traffic.  Note that we do this by overriding _handle_connect
        # instead of by passing a callback to super().connect because
        # user callbacks are enqueued asynchronously on the IOLoop,
        # but since _handle_events calls _handle_connect immediately
        # followed by _handle_write we need this to be synchronous.
        self.socket = ssl_wrap_socket(self.socket, self._ssl_options,
                                      server_hostname=self._server_hostname,
                                      do_handshake_on_connect=False)
        super(SSLIOStream, self)._handle_connect()

    def read_from_fd(self):
        if self._ssl_accepting:
            # If the handshake hasn't finished yet, there can't be anything
            # to read (attempting to read may or may not raise an exception
            # depending on the SSL version)
            return None
        try:
            # SSLSocket objects have both a read() and recv() method,
            # while regular sockets only have recv().
            # The recv() method blocks (at least in python 2.6) if it is
            # called when there is nothing to read, so we have to use
            # read() instead.
            chunk = self.socket.read(self.read_chunk_size)
        except ssl.SSLError as e:
            # SSLError is a subclass of socket.error, so this except
            # block must come first.
            if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                return None
            else:
                raise
        except socket.error as e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk


class PipeIOStream(BaseIOStream):
    """Pipe-based `IOStream` implementation.

    The constructor takes an integer file descriptor (such as one returned
    by `os.pipe`) rather than an open file object.  Pipes are generally
    one-way, so a `PipeIOStream` can be used for reading or writing but not
    both.
    """
    def __init__(self, fd, *args, **kwargs):
        self.fd = fd
        _set_nonblocking(fd)
        super(PipeIOStream, self).__init__(*args, **kwargs)

    def fileno(self):
        return self.fd

    def close_fd(self):
        os.close(self.fd)

    def write_to_fd(self, data):
        return os.write(self.fd, data)

    def read_from_fd(self):
        try:
            chunk = os.read(self.fd, self.read_chunk_size)
        except (IOError, OSError) as e:
            if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                return None
            elif e.args[0] == errno.EBADF:
                # If the writing half of a pipe is closed, select will
                # report it as readable but reads will fail with EBADF.
                self.close(exc_info=True)
                return None
            else:
                raise
        if not chunk:
            self.close()
            return None
        return chunk


def _double_prefix(deque):
    """Grow by doubling, but don't split the second chunk just because the
    first one is small.
    """
    new_len = max(len(deque[0]) * 2,
                  (len(deque[0]) + len(deque[1])))
    _merge_prefix(deque, new_len)


def _merge_prefix(deque, size):
    """Replace the first entries in a deque of strings with a single
    string of up to size bytes.

    >>> d = collections.deque(['abc', 'de', 'fghi', 'j'])
    >>> _merge_prefix(d, 5); print(d)
    deque(['abcde', 'fghi', 'j'])

    Strings will be split as necessary to reach the desired size.
    >>> _merge_prefix(d, 7); print(d)
    deque(['abcdefg', 'hi', 'j'])

    >>> _merge_prefix(d, 3); print(d)
    deque(['abc', 'defg', 'hi', 'j'])

    >>> _merge_prefix(d, 100); print(d)
    deque(['abcdefghij'])
    """
    if len(deque) == 1 and len(deque[0]) <= size:
        return
    prefix = []
    remaining = size
    while deque and remaining > 0:
        chunk = deque.popleft()
        if len(chunk) > remaining:
            deque.appendleft(chunk[remaining:])
            chunk = chunk[:remaining]
        prefix.append(chunk)
        remaining -= len(chunk)
    # This data structure normally just contains byte strings, but
    # the unittest gets messy if it doesn't use the default str() type,
    # so do the merge based on the type of data that's actually present.
    if prefix:
        deque.appendleft(type(prefix[0])().join(prefix))
    if not deque:
        deque.appendleft(b"")


def doctests():
    import doctest
    return doctest.DocTestSuite()

########NEW FILE########
__FILENAME__ = locale
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Translation methods for generating localized strings.

To load a locale and generate a translated string::

    user_locale = tornado.locale.get("es_LA")
    print user_locale.translate("Sign out")

`tornado.locale.get()` returns the closest matching locale, not necessarily the
specific locale you requested. You can support pluralization with
additional arguments to `~Locale.translate()`, e.g.::

    people = [...]
    message = user_locale.translate(
        "%(list)s is online", "%(list)s are online", len(people))
    print message % {"list": user_locale.list(people)}

The first string is chosen if ``len(people) == 1``, otherwise the second
string is chosen.

Applications should call one of `load_translations` (which uses a simple
CSV format) or `load_gettext_translations` (which uses the ``.mo`` format
supported by `gettext` and related tools).  If neither method is called,
the `Locale.translate` method will simply return the original string.
"""

from __future__ import absolute_import, division, print_function, with_statement

import csv
import datetime
import numbers
import os
import re

from tornado import escape
from tornado.log import gen_log
from tornado.util import u

_default_locale = "en_US"
_translations = {}
_supported_locales = frozenset([_default_locale])
_use_gettext = False


def get(*locale_codes):
    """Returns the closest match for the given locale codes.

    We iterate over all given locale codes in order. If we have a tight
    or a loose match for the code (e.g., "en" for "en_US"), we return
    the locale. Otherwise we move to the next code in the list.

    By default we return ``en_US`` if no translations are found for any of
    the specified locales. You can change the default locale with
    `set_default_locale()`.
    """
    return Locale.get_closest(*locale_codes)


def set_default_locale(code):
    """Sets the default locale.

    The default locale is assumed to be the language used for all strings
    in the system. The translations loaded from disk are mappings from
    the default locale to the destination locale. Consequently, you don't
    need to create a translation file for the default locale.
    """
    global _default_locale
    global _supported_locales
    _default_locale = code
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])


def load_translations(directory):
    """Loads translations from CSV files in a directory.

    Translations are strings with optional Python-style named placeholders
    (e.g., ``My name is %(name)s``) and their associated translations.

    The directory should have translation files of the form ``LOCALE.csv``,
    e.g. ``es_GT.csv``. The CSV files should have two or three columns: string,
    translation, and an optional plural indicator. Plural indicators should
    be one of "plural" or "singular". A given string can have both singular
    and plural forms. For example ``%(name)s liked this`` may have a
    different verb conjugation depending on whether %(name)s is one
    name or a list of names. There should be two rows in the CSV file for
    that string, one with plural indicator "singular", and one "plural".
    For strings with no verbs that would change on translation, simply
    use "unknown" or the empty string (or don't include the column at all).

    The file is read using the `csv` module in the default "excel" dialect.
    In this format there should not be spaces after the commas.

    Example translation ``es_LA.csv``::

        "I love you","Te amo"
        "%(name)s liked this","A %(name)s les gustó esto","plural"
        "%(name)s liked this","A %(name)s le gustó esto","singular"

    """
    global _translations
    global _supported_locales
    _translations = {}
    for path in os.listdir(directory):
        if not path.endswith(".csv"):
            continue
        locale, extension = path.split(".")
        if not re.match("[a-z]+(_[A-Z]+)?$", locale):
            gen_log.error("Unrecognized locale %r (path: %s)", locale,
                          os.path.join(directory, path))
            continue
        full_path = os.path.join(directory, path)
        try:
            # python 3: csv.reader requires a file open in text mode.
            # Force utf8 to avoid dependence on $LANG environment variable.
            f = open(full_path, "r", encoding="utf-8")
        except TypeError:
            # python 2: files return byte strings, which are decoded below.
            f = open(full_path, "r")
        _translations[locale] = {}
        for i, row in enumerate(csv.reader(f)):
            if not row or len(row) < 2:
                continue
            row = [escape.to_unicode(c).strip() for c in row]
            english, translation = row[:2]
            if len(row) > 2:
                plural = row[2] or "unknown"
            else:
                plural = "unknown"
            if plural not in ("plural", "singular", "unknown"):
                gen_log.error("Unrecognized plural indicator %r in %s line %d",
                              plural, path, i + 1)
                continue
            _translations[locale].setdefault(plural, {})[english] = translation
        f.close()
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])
    gen_log.debug("Supported locales: %s", sorted(_supported_locales))


def load_gettext_translations(directory, domain):
    """Loads translations from `gettext`'s locale tree

    Locale tree is similar to system's ``/usr/share/locale``, like::

        {directory}/{lang}/LC_MESSAGES/{domain}.mo

    Three steps are required to have you app translated:

    1. Generate POT translation file::

        xgettext --language=Python --keyword=_:1,2 -d mydomain file1.py file2.html etc

    2. Merge against existing POT file::

        msgmerge old.po mydomain.po > new.po

    3. Compile::

        msgfmt mydomain.po -o {directory}/pt_BR/LC_MESSAGES/mydomain.mo
    """
    import gettext
    global _translations
    global _supported_locales
    global _use_gettext
    _translations = {}
    for lang in os.listdir(directory):
        if lang.startswith('.'):
            continue  # skip .svn, etc
        if os.path.isfile(os.path.join(directory, lang)):
            continue
        try:
            os.stat(os.path.join(directory, lang, "LC_MESSAGES", domain + ".mo"))
            _translations[lang] = gettext.translation(domain, directory,
                                                      languages=[lang])
        except Exception as e:
            gen_log.error("Cannot load translation for '%s': %s", lang, str(e))
            continue
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])
    _use_gettext = True
    gen_log.debug("Supported locales: %s", sorted(_supported_locales))


def get_supported_locales():
    """Returns a list of all the supported locale codes."""
    return _supported_locales


class Locale(object):
    """Object representing a locale.

    After calling one of `load_translations` or `load_gettext_translations`,
    call `get` or `get_closest` to get a Locale object.
    """
    @classmethod
    def get_closest(cls, *locale_codes):
        """Returns the closest match for the given locale code."""
        for code in locale_codes:
            if not code:
                continue
            code = code.replace("-", "_")
            parts = code.split("_")
            if len(parts) > 2:
                continue
            elif len(parts) == 2:
                code = parts[0].lower() + "_" + parts[1].upper()
            if code in _supported_locales:
                return cls.get(code)
            if parts[0].lower() in _supported_locales:
                return cls.get(parts[0].lower())
        return cls.get(_default_locale)

    @classmethod
    def get(cls, code):
        """Returns the Locale for the given locale code.

        If it is not supported, we raise an exception.
        """
        if not hasattr(cls, "_cache"):
            cls._cache = {}
        if code not in cls._cache:
            assert code in _supported_locales
            translations = _translations.get(code, None)
            if translations is None:
                locale = CSVLocale(code, {})
            elif _use_gettext:
                locale = GettextLocale(code, translations)
            else:
                locale = CSVLocale(code, translations)
            cls._cache[code] = locale
        return cls._cache[code]

    def __init__(self, code, translations):
        self.code = code
        self.name = LOCALE_NAMES.get(code, {}).get("name", u("Unknown"))
        self.rtl = False
        for prefix in ["fa", "ar", "he"]:
            if self.code.startswith(prefix):
                self.rtl = True
                break
        self.translations = translations

        # Initialize strings for date formatting
        _ = self.translate
        self._months = [
            _("January"), _("February"), _("March"), _("April"),
            _("May"), _("June"), _("July"), _("August"),
            _("September"), _("October"), _("November"), _("December")]
        self._weekdays = [
            _("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"),
            _("Friday"), _("Saturday"), _("Sunday")]

    def translate(self, message, plural_message=None, count=None):
        """Returns the translation for the given message for this locale.

        If ``plural_message`` is given, you must also provide
        ``count``. We return ``plural_message`` when ``count != 1``,
        and we return the singular form for the given message when
        ``count == 1``.
        """
        raise NotImplementedError()

    def format_date(self, date, gmt_offset=0, relative=True, shorter=False,
                    full_format=False):
        """Formats the given date (which should be GMT).

        By default, we return a relative time (e.g., "2 minutes ago"). You
        can return an absolute date string with ``relative=False``.

        You can force a full format date ("July 10, 1980") with
        ``full_format=True``.

        This method is primarily intended for dates in the past.
        For dates in the future, we fall back to full format.
        """
        if self.code.startswith("ru"):
            relative = False
        if isinstance(date, numbers.Real):
            date = datetime.datetime.utcfromtimestamp(date)
        now = datetime.datetime.utcnow()
        if date > now:
            if relative and (date - now).seconds < 60:
                # Due to click skew, things are some things slightly
                # in the future. Round timestamps in the immediate
                # future down to now in relative mode.
                date = now
            else:
                # Otherwise, future dates always use the full format.
                full_format = True
        local_date = date - datetime.timedelta(minutes=gmt_offset)
        local_now = now - datetime.timedelta(minutes=gmt_offset)
        local_yesterday = local_now - datetime.timedelta(hours=24)
        difference = now - date
        seconds = difference.seconds
        days = difference.days

        _ = self.translate
        format = None
        if not full_format:
            if relative and days == 0:
                if seconds < 50:
                    return _("1 second ago", "%(seconds)d seconds ago",
                             seconds) % {"seconds": seconds}

                if seconds < 50 * 60:
                    minutes = round(seconds / 60.0)
                    return _("1 minute ago", "%(minutes)d minutes ago",
                             minutes) % {"minutes": minutes}

                hours = round(seconds / (60.0 * 60))
                return _("1 hour ago", "%(hours)d hours ago",
                         hours) % {"hours": hours}

            if days == 0:
                format = _("%(time)s")
            elif days == 1 and local_date.day == local_yesterday.day and \
                    relative:
                format = _("yesterday") if shorter else \
                    _("yesterday at %(time)s")
            elif days < 5:
                format = _("%(weekday)s") if shorter else \
                    _("%(weekday)s at %(time)s")
            elif days < 334:  # 11mo, since confusing for same month last year
                format = _("%(month_name)s %(day)s") if shorter else \
                    _("%(month_name)s %(day)s at %(time)s")

        if format is None:
            format = _("%(month_name)s %(day)s, %(year)s") if shorter else \
                _("%(month_name)s %(day)s, %(year)s at %(time)s")

        tfhour_clock = self.code not in ("en", "en_US", "zh_CN")
        if tfhour_clock:
            str_time = "%d:%02d" % (local_date.hour, local_date.minute)
        elif self.code == "zh_CN":
            str_time = "%s%d:%02d" % (
                (u('\u4e0a\u5348'), u('\u4e0b\u5348'))[local_date.hour >= 12],
                local_date.hour % 12 or 12, local_date.minute)
        else:
            str_time = "%d:%02d %s" % (
                local_date.hour % 12 or 12, local_date.minute,
                ("am", "pm")[local_date.hour >= 12])

        return format % {
            "month_name": self._months[local_date.month - 1],
            "weekday": self._weekdays[local_date.weekday()],
            "day": str(local_date.day),
            "year": str(local_date.year),
            "time": str_time
        }

    def format_day(self, date, gmt_offset=0, dow=True):
        """Formats the given date as a day of week.

        Example: "Monday, January 22". You can remove the day of week with
        ``dow=False``.
        """
        local_date = date - datetime.timedelta(minutes=gmt_offset)
        _ = self.translate
        if dow:
            return _("%(weekday)s, %(month_name)s %(day)s") % {
                "month_name": self._months[local_date.month - 1],
                "weekday": self._weekdays[local_date.weekday()],
                "day": str(local_date.day),
            }
        else:
            return _("%(month_name)s %(day)s") % {
                "month_name": self._months[local_date.month - 1],
                "day": str(local_date.day),
            }

    def list(self, parts):
        """Returns a comma-separated list for the given list of parts.

        The format is, e.g., "A, B and C", "A and B" or just "A" for lists
        of size 1.
        """
        _ = self.translate
        if len(parts) == 0:
            return ""
        if len(parts) == 1:
            return parts[0]
        comma = u(' \u0648 ') if self.code.startswith("fa") else u(", ")
        return _("%(commas)s and %(last)s") % {
            "commas": comma.join(parts[:-1]),
            "last": parts[len(parts) - 1],
        }

    def friendly_number(self, value):
        """Returns a comma-separated number for the given integer."""
        if self.code not in ("en", "en_US"):
            return str(value)
        value = str(value)
        parts = []
        while value:
            parts.append(value[-3:])
            value = value[:-3]
        return ",".join(reversed(parts))


class CSVLocale(Locale):
    """Locale implementation using tornado's CSV translation format."""
    def translate(self, message, plural_message=None, count=None):
        if plural_message is not None:
            assert count is not None
            if count != 1:
                message = plural_message
                message_dict = self.translations.get("plural", {})
            else:
                message_dict = self.translations.get("singular", {})
        else:
            message_dict = self.translations.get("unknown", {})
        return message_dict.get(message, message)


class GettextLocale(Locale):
    """Locale implementation using the `gettext` module."""
    def __init__(self, code, translations):
        try:
            # python 2
            self.ngettext = translations.ungettext
            self.gettext = translations.ugettext
        except AttributeError:
            # python 3
            self.ngettext = translations.ngettext
            self.gettext = translations.gettext
        # self.gettext must exist before __init__ is called, since it
        # calls into self.translate
        super(GettextLocale, self).__init__(code, translations)

    def translate(self, message, plural_message=None, count=None):
        if plural_message is not None:
            assert count is not None
            return self.ngettext(message, plural_message, count)
        else:
            return self.gettext(message)

LOCALE_NAMES = {
    "af_ZA": {"name_en": u("Afrikaans"), "name": u("Afrikaans")},
    "am_ET": {"name_en": u("Amharic"), "name": u('\u12a0\u121b\u122d\u129b')},
    "ar_AR": {"name_en": u("Arabic"), "name": u("\u0627\u0644\u0639\u0631\u0628\u064a\u0629")},
    "bg_BG": {"name_en": u("Bulgarian"), "name": u("\u0411\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438")},
    "bn_IN": {"name_en": u("Bengali"), "name": u("\u09ac\u09be\u0982\u09b2\u09be")},
    "bs_BA": {"name_en": u("Bosnian"), "name": u("Bosanski")},
    "ca_ES": {"name_en": u("Catalan"), "name": u("Catal\xe0")},
    "cs_CZ": {"name_en": u("Czech"), "name": u("\u010ce\u0161tina")},
    "cy_GB": {"name_en": u("Welsh"), "name": u("Cymraeg")},
    "da_DK": {"name_en": u("Danish"), "name": u("Dansk")},
    "de_DE": {"name_en": u("German"), "name": u("Deutsch")},
    "el_GR": {"name_en": u("Greek"), "name": u("\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac")},
    "en_GB": {"name_en": u("English (UK)"), "name": u("English (UK)")},
    "en_US": {"name_en": u("English (US)"), "name": u("English (US)")},
    "es_ES": {"name_en": u("Spanish (Spain)"), "name": u("Espa\xf1ol (Espa\xf1a)")},
    "es_LA": {"name_en": u("Spanish"), "name": u("Espa\xf1ol")},
    "et_EE": {"name_en": u("Estonian"), "name": u("Eesti")},
    "eu_ES": {"name_en": u("Basque"), "name": u("Euskara")},
    "fa_IR": {"name_en": u("Persian"), "name": u("\u0641\u0627\u0631\u0633\u06cc")},
    "fi_FI": {"name_en": u("Finnish"), "name": u("Suomi")},
    "fr_CA": {"name_en": u("French (Canada)"), "name": u("Fran\xe7ais (Canada)")},
    "fr_FR": {"name_en": u("French"), "name": u("Fran\xe7ais")},
    "ga_IE": {"name_en": u("Irish"), "name": u("Gaeilge")},
    "gl_ES": {"name_en": u("Galician"), "name": u("Galego")},
    "he_IL": {"name_en": u("Hebrew"), "name": u("\u05e2\u05d1\u05e8\u05d9\u05ea")},
    "hi_IN": {"name_en": u("Hindi"), "name": u("\u0939\u093f\u0928\u094d\u0926\u0940")},
    "hr_HR": {"name_en": u("Croatian"), "name": u("Hrvatski")},
    "hu_HU": {"name_en": u("Hungarian"), "name": u("Magyar")},
    "id_ID": {"name_en": u("Indonesian"), "name": u("Bahasa Indonesia")},
    "is_IS": {"name_en": u("Icelandic"), "name": u("\xcdslenska")},
    "it_IT": {"name_en": u("Italian"), "name": u("Italiano")},
    "ja_JP": {"name_en": u("Japanese"), "name": u("\u65e5\u672c\u8a9e")},
    "ko_KR": {"name_en": u("Korean"), "name": u("\ud55c\uad6d\uc5b4")},
    "lt_LT": {"name_en": u("Lithuanian"), "name": u("Lietuvi\u0173")},
    "lv_LV": {"name_en": u("Latvian"), "name": u("Latvie\u0161u")},
    "mk_MK": {"name_en": u("Macedonian"), "name": u("\u041c\u0430\u043a\u0435\u0434\u043e\u043d\u0441\u043a\u0438")},
    "ml_IN": {"name_en": u("Malayalam"), "name": u("\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02")},
    "ms_MY": {"name_en": u("Malay"), "name": u("Bahasa Melayu")},
    "nb_NO": {"name_en": u("Norwegian (bokmal)"), "name": u("Norsk (bokm\xe5l)")},
    "nl_NL": {"name_en": u("Dutch"), "name": u("Nederlands")},
    "nn_NO": {"name_en": u("Norwegian (nynorsk)"), "name": u("Norsk (nynorsk)")},
    "pa_IN": {"name_en": u("Punjabi"), "name": u("\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40")},
    "pl_PL": {"name_en": u("Polish"), "name": u("Polski")},
    "pt_BR": {"name_en": u("Portuguese (Brazil)"), "name": u("Portugu\xeas (Brasil)")},
    "pt_PT": {"name_en": u("Portuguese (Portugal)"), "name": u("Portugu\xeas (Portugal)")},
    "ro_RO": {"name_en": u("Romanian"), "name": u("Rom\xe2n\u0103")},
    "ru_RU": {"name_en": u("Russian"), "name": u("\u0420\u0443\u0441\u0441\u043a\u0438\u0439")},
    "sk_SK": {"name_en": u("Slovak"), "name": u("Sloven\u010dina")},
    "sl_SI": {"name_en": u("Slovenian"), "name": u("Sloven\u0161\u010dina")},
    "sq_AL": {"name_en": u("Albanian"), "name": u("Shqip")},
    "sr_RS": {"name_en": u("Serbian"), "name": u("\u0421\u0440\u043f\u0441\u043a\u0438")},
    "sv_SE": {"name_en": u("Swedish"), "name": u("Svenska")},
    "sw_KE": {"name_en": u("Swahili"), "name": u("Kiswahili")},
    "ta_IN": {"name_en": u("Tamil"), "name": u("\u0ba4\u0bae\u0bbf\u0bb4\u0bcd")},
    "te_IN": {"name_en": u("Telugu"), "name": u("\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41")},
    "th_TH": {"name_en": u("Thai"), "name": u("\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22")},
    "tl_PH": {"name_en": u("Filipino"), "name": u("Filipino")},
    "tr_TR": {"name_en": u("Turkish"), "name": u("T\xfcrk\xe7e")},
    "uk_UA": {"name_en": u("Ukraini "), "name": u("\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430")},
    "vi_VN": {"name_en": u("Vietnamese"), "name": u("Ti\u1ebfng Vi\u1ec7t")},
    "zh_CN": {"name_en": u("Chinese (Simplified)"), "name": u("\u4e2d\u6587(\u7b80\u4f53)")},
    "zh_TW": {"name_en": u("Chinese (Traditional)"), "name": u("\u4e2d\u6587(\u7e41\u9ad4)")},
}

########NEW FILE########
__FILENAME__ = log
#!/usr/bin/env python
#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Logging support for Tornado.

Tornado uses three logger streams:

* ``tornado.access``: Per-request logging for Tornado's HTTP servers (and
  potentially other servers in the future)
* ``tornado.application``: Logging of errors from application code (i.e.
  uncaught exceptions from callbacks)
* ``tornado.general``: General-purpose logging, including any errors
  or warnings from Tornado itself.

These streams may be configured independently using the standard library's
`logging` module.  For example, you may wish to send ``tornado.access`` logs
to a separate file for analysis.
"""
from __future__ import absolute_import, division, print_function, with_statement

import logging
import logging.handlers
import sys
import time

from tornado.escape import _unicode
from tornado.util import unicode_type, basestring_type

try:
    import curses
except ImportError:
    curses = None

# Logger objects for internal tornado use
access_log = logging.getLogger("tornado.access")
app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")


def _stderr_supports_color():
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except Exception:
            pass
    return color


class LogFormatter(logging.Formatter):
    """Log formatter used in Tornado.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.

    This formatter is enabled automatically by
    `tornado.options.parse_command_line` (unless ``--logging=none`` is
    used).
    """
    def __init__(self, color=True, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self._color = color and _stderr_supports_color()
        if self._color:
            # The curses module has some str/bytes confusion in
            # python3.  Until version 3.2.3, most methods return
            # bytes, but only accept strings.  In addition, we want to
            # output these strings with the logging module, which
            # works with unicode strings.  The explicit calls to
            # unicode() below are harmless in python2 but will do the
            # right conversion in python 3.
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = unicode_type(fg_color, "ascii")
            self._colors = {
                logging.DEBUG: unicode_type(curses.tparm(fg_color, 4),  # Blue
                                            "ascii"),
                logging.INFO: unicode_type(curses.tparm(fg_color, 2),  # Green
                                           "ascii"),
                logging.WARNING: unicode_type(curses.tparm(fg_color, 3),  # Yellow
                                              "ascii"),
                logging.ERROR: unicode_type(curses.tparm(fg_color, 1),  # Red
                                            "ascii"),
            }
            self._normal = unicode_type(curses.tigetstr("sgr0"), "ascii")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        assert isinstance(record.message, basestring_type)  # guaranteed by logging
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
            record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)

        # Encoding notes:  The logging module prefers to work with character
        # strings, but only enforces that log messages are instances of
        # basestring.  In python 2, non-ascii bytestrings will make
        # their way through the logging framework until they blow up with
        # an unhelpful decoding error (with this formatter it happens
        # when we attach the prefix, but there are other opportunities for
        # exceptions further along in the framework).
        #
        # If a byte string makes it this far, convert it to unicode to
        # ensure it will make it out to the logs.  Use repr() as a fallback
        # to ensure that all byte strings can be converted successfully,
        # but don't do it by default so we don't add extra quotes to ascii
        # bytestrings.  This is a bit of a hacky place to do this, but
        # it's worth it since the encoding errors that would otherwise
        # result are so useless (and tornado is fond of using utf8-encoded
        # byte strings whereever possible).
        def safe_unicode(s):
            try:
                return _unicode(s)
            except UnicodeDecodeError:
                return repr(s)

        formatted = prefix + " " + safe_unicode(record.message)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(safe_unicode(ln) for ln in record.exc_text.split('\n'))
            formatted = '\n'.join(lines)
        return formatted.replace("\n", "\n    ")


def enable_pretty_logging(options=None, logger=None):
    """Turns on formatted logging output as configured.

    This is called automaticaly by `tornado.options.parse_command_line`
    and `tornado.options.parse_config_file`.
    """
    if options is None:
        from tornado.options import options
    if options.logging == 'none':
        return
    if logger is None:
        logger = logging.getLogger()
    logger.setLevel(getattr(logging, options.logging.upper()))
    if options.log_file_prefix:
        channel = logging.handlers.RotatingFileHandler(
            filename=options.log_file_prefix,
            maxBytes=options.log_file_max_size,
            backupCount=options.log_file_num_backups)
        channel.setFormatter(LogFormatter(color=False))
        logger.addHandler(channel)

    if (options.log_to_stderr or
            (options.log_to_stderr is None and not logger.handlers)):
        # Set up color if we are in a tty and curses is installed
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        logger.addHandler(channel)


def define_logging_options(options=None):
    if options is None:
        # late import to prevent cycle
        from tornado.options import options
    options.define("logging", default="info",
                   help=("Set the Python log level. If 'none', tornado won't touch the "
                         "logging configuration."),
                   metavar="debug|info|warning|error|none")
    options.define("log_to_stderr", type=bool, default=None,
                   help=("Send log output to stderr (colorized if possible). "
                         "By default use stderr if --log_file_prefix is not set and "
                         "no other logging is configured."))
    options.define("log_file_prefix", type=str, default=None, metavar="PATH",
                   help=("Path prefix for log files. "
                         "Note that if you are running multiple tornado processes, "
                         "log_file_prefix must be different for each of them (e.g. "
                         "include the port number)"))
    options.define("log_file_max_size", type=int, default=100 * 1000 * 1000,
                   help="max size of log files before rollover")
    options.define("log_file_num_backups", type=int, default=10,
                   help="number of log files to keep")

    options.add_parse_callback(enable_pretty_logging)

########NEW FILE########
__FILENAME__ = netutil
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Miscellaneous network utility code."""

from __future__ import absolute_import, division, print_function, with_statement

import errno
import os
import re
import socket
# import ssl
import stat
ssl = {}

from tornado.concurrent import dummy_executor, run_on_executor
from tornado.ioloop import IOLoop
from tornado.platform.auto import set_close_exec
from tornado.util import Configurable


def bind_sockets(port, address=None, family=socket.AF_UNSPEC, backlog=128, flags=None):
    """Creates listening sockets bound to the given port and address.

    Returns a list of socket objects (multiple sockets are returned if
    the given address maps to multiple IP addresses, which is most common
    for mixed IPv4 and IPv6 use).

    Address may be either an IP address or hostname.  If it's a hostname,
    the server will listen on all IP addresses associated with the
    name.  Address may be an empty string or None to listen on all
    available interfaces.  Family may be set to either `socket.AF_INET`
    or `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise
    both will be used if available.

    The ``backlog`` argument has the same meaning as for
    `socket.listen() <socket.socket.listen>`.

    ``flags`` is a bitmask of AI_* flags to `~socket.getaddrinfo`, like
    ``socket.AI_PASSIVE | socket.AI_NUMERICHOST``.
    """
    sockets = []
    if address == "":
        address = None
    if not socket.has_ipv6 and family == socket.AF_UNSPEC:
        # Python can be compiled with --disable-ipv6, which causes
        # operations on AF_INET6 sockets to fail, but does not
        # automatically exclude those results from getaddrinfo
        # results.
        # http://bugs.python.org/issue16208
        family = socket.AF_INET
    if flags is None:
        flags = socket.AI_PASSIVE
    for res in set(socket.getaddrinfo(address, port, family, socket.SOCK_STREAM,
                                      0, flags)):
        af, socktype, proto, canonname, sockaddr = res
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error as e:
            if e.args[0] == errno.EAFNOSUPPORT:
                continue
            raise
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if af == socket.AF_INET6:
            # On linux, ipv6 sockets accept ipv4 too by default,
            # but this makes it impossible to bind to both
            # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
            # separate sockets *must* be used to listen for both ipv4
            # and ipv6.  For consistency, always disable ipv4 on our
            # ipv6 sockets and use a separate ipv4 socket when needed.
            #
            # Python 2.x on windows doesn't have IPPROTO_IPV6.
            if hasattr(socket, "IPPROTO_IPV6"):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setblocking(0)
        sock.bind(sockaddr)
        sock.listen(backlog)
        sockets.append(sock)
    return sockets

if hasattr(socket, 'AF_UNIX'):
    def bind_unix_socket(file, mode=0o600, backlog=128):
        """Creates a listening unix socket.

        If a socket with the given name already exists, it will be deleted.
        If any other file with that name exists, an exception will be
        raised.

        Returns a socket object (not a list of socket objects like
        `bind_sockets`)
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        set_close_exec(sock.fileno())
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        try:
            st = os.stat(file)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
        else:
            if stat.S_ISSOCK(st.st_mode):
                os.remove(file)
            else:
                raise ValueError("File %s exists and is not a socket", file)
        sock.bind(file)
        os.chmod(file, mode)
        sock.listen(backlog)
        return sock


def add_accept_handler(sock, callback, io_loop=None):
    """Adds an `.IOLoop` event handler to accept new connections on ``sock``.

    When a connection is accepted, ``callback(connection, address)`` will
    be run (``connection`` is a socket object, and ``address`` is the
    address of the other end of the connection).  Note that this signature
    is different from the ``callback(fd, events)`` signature used for
    `.IOLoop` handlers.
    """
    if io_loop is None:
        io_loop = IOLoop.current()

    def accept_handler(fd, events):
        while True:
            try:
                connection, address = sock.accept()
            except socket.error as e:
                # EWOULDBLOCK and EAGAIN indicate we have accepted every
                # connection that is available.
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                # ECONNABORTED indicates that there was a connection
                # but it was closed while still in the accept queue.
                # (observed on FreeBSD).
                if e.args[0] == errno.ECONNABORTED:
                    continue
                raise
            callback(connection, address)
    io_loop.add_handler(sock.fileno(), accept_handler, IOLoop.READ)


def is_valid_ip(ip):
    """Returns true if the given string is a well-formed IP address.

    Supports IPv4 and IPv6.
    """
    try:
        res = socket.getaddrinfo(ip, 0, socket.AF_UNSPEC,
                                 socket.SOCK_STREAM,
                                 0, socket.AI_NUMERICHOST)
        return bool(res)
    except socket.gaierror as e:
        if e.args[0] == socket.EAI_NONAME:
            return False
        raise
    return True


class Resolver(Configurable):
    """Configurable asynchronous DNS resolver interface.

    By default, a blocking implementation is used (which simply calls
    `socket.getaddrinfo`).  An alternative implementation can be
    chosen with the `Resolver.configure <.Configurable.configure>`
    class method::

        Resolver.configure('tornado.netutil.ThreadedResolver')

    The implementations of this interface included with Tornado are

    * `tornado.netutil.BlockingResolver`
    * `tornado.netutil.ThreadedResolver`
    * `tornado.netutil.OverrideResolver`
    * `tornado.platform.twisted.TwistedResolver`
    * `tornado.platform.caresresolver.CaresResolver`
    """
    @classmethod
    def configurable_base(cls):
        return Resolver

    @classmethod
    def configurable_default(cls):
        return BlockingResolver

    def resolve(self, host, port, family=socket.AF_UNSPEC, callback=None):
        """Resolves an address.

        The ``host`` argument is a string which may be a hostname or a
        literal IP address.

        Returns a `.Future` whose result is a list of (family,
        address) pairs, where address is a tuple suitable to pass to
        `socket.connect <socket.socket.connect>` (i.e. a ``(host,
        port)`` pair for IPv4; additional fields may be present for
        IPv6). If a ``callback`` is passed, it will be run with the
        result as an argument when it is complete.
        """
        raise NotImplementedError()

    def close(self):
        """Closes the `Resolver`, freeing any resources used.

        .. versionadded:: 3.1

        """
        pass


class ExecutorResolver(Resolver):
    """Resolver implementation using a `concurrent.futures.Executor`.

    Use this instead of `ThreadedResolver` when you require additional
    control over the executor being used.

    The executor will be shut down when the resolver is closed unless
    ``close_resolver=False``; use this if you want to reuse the same
    executor elsewhere.
    """
    def initialize(self, io_loop=None, executor=None, close_executor=True):
        self.io_loop = io_loop or IOLoop.current()
        if executor is not None:
            self.executor = executor
            self.close_executor = close_executor
        else:
            self.executor = dummy_executor
            self.close_executor = False

    def close(self):
        if self.close_executor:
            self.executor.shutdown()
        self.executor = None

    @run_on_executor
    def resolve(self, host, port, family=socket.AF_UNSPEC):
        # On Solaris, getaddrinfo fails if the given port is not found
        # in /etc/services and no socket type is given, so we must pass
        # one here.  The socket type used here doesn't seem to actually
        # matter (we discard the one we get back in the results),
        # so the addresses we return should still be usable with SOCK_DGRAM.
        addrinfo = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
        results = []
        for family, socktype, proto, canonname, address in addrinfo:
            results.append((family, address))
        return results


class BlockingResolver(ExecutorResolver):
    """Default `Resolver` implementation, using `socket.getaddrinfo`.

    The `.IOLoop` will be blocked during the resolution, although the
    callback will not be run until the next `.IOLoop` iteration.
    """
    def initialize(self, io_loop=None):
        super(BlockingResolver, self).initialize(io_loop=io_loop)


class ThreadedResolver(ExecutorResolver):
    """Multithreaded non-blocking `Resolver` implementation.

    Requires the `concurrent.futures` package to be installed
    (available in the standard library since Python 3.2,
    installable with ``pip install futures`` in older versions).

    The thread pool size can be configured with::

        Resolver.configure('tornado.netutil.ThreadedResolver',
                           num_threads=10)

    .. versionchanged:: 3.1
       All ``ThreadedResolvers`` share a single thread pool, whose
       size is set by the first one to be created.
    """
    _threadpool = None
    _threadpool_pid = None

    def initialize(self, io_loop=None, num_threads=10):
        threadpool = ThreadedResolver._create_threadpool(num_threads)
        super(ThreadedResolver, self).initialize(
            io_loop=io_loop, executor=threadpool, close_executor=False)

    @classmethod
    def _create_threadpool(cls, num_threads):
        pid = os.getpid()
        if cls._threadpool_pid != pid:
            # Threads cannot survive after a fork, so if our pid isn't what it
            # was when we created the pool then delete it.
            cls._threadpool = None
        if cls._threadpool is None:
            from concurrent.futures import ThreadPoolExecutor
            cls._threadpool = ThreadPoolExecutor(num_threads)
            cls._threadpool_pid = pid
        return cls._threadpool


class OverrideResolver(Resolver):
    """Wraps a resolver with a mapping of overrides.

    This can be used to make local DNS changes (e.g. for testing)
    without modifying system-wide settings.

    The mapping can contain either host strings or host-port pairs.
    """
    def initialize(self, resolver, mapping):
        self.resolver = resolver
        self.mapping = mapping

    def close(self):
        self.resolver.close()

    def resolve(self, host, port, *args, **kwargs):
        if (host, port) in self.mapping:
            host, port = self.mapping[(host, port)]
        elif host in self.mapping:
            host = self.mapping[host]
        return self.resolver.resolve(host, port, *args, **kwargs)


# These are the keyword arguments to ssl.wrap_socket that must be translated
# to their SSLContext equivalents (the other arguments are still passed
# to SSLContext.wrap_socket).
_SSL_CONTEXT_KEYWORDS = frozenset(['ssl_version', 'certfile', 'keyfile',
                                   'cert_reqs', 'ca_certs', 'ciphers'])


def ssl_options_to_context(ssl_options):
    """Try to convert an ``ssl_options`` dictionary to an
    `~ssl.SSLContext` object.

    The ``ssl_options`` dictionary contains keywords to be passed to
    `ssl.wrap_socket`.  In Python 3.2+, `ssl.SSLContext` objects can
    be used instead.  This function converts the dict form to its
    `~ssl.SSLContext` equivalent, and may be used when a component which
    accepts both forms needs to upgrade to the `~ssl.SSLContext` version
    to use features like SNI or NPN.
    """
    if isinstance(ssl_options, dict):
        assert all(k in _SSL_CONTEXT_KEYWORDS for k in ssl_options), ssl_options
    if (not hasattr(ssl, 'SSLContext') or
            isinstance(ssl_options, ssl.SSLContext)):
        return ssl_options
    context = ssl.SSLContext(
        ssl_options.get('ssl_version', ssl.PROTOCOL_SSLv23))
    if 'certfile' in ssl_options:
        context.load_cert_chain(ssl_options['certfile'], ssl_options.get('keyfile', None))
    if 'cert_reqs' in ssl_options:
        context.verify_mode = ssl_options['cert_reqs']
    if 'ca_certs' in ssl_options:
        context.load_verify_locations(ssl_options['ca_certs'])
    if 'ciphers' in ssl_options:
        context.set_ciphers(ssl_options['ciphers'])
    return context


def ssl_wrap_socket(socket, ssl_options, server_hostname=None, **kwargs):
    """Returns an ``ssl.SSLSocket`` wrapping the given socket.

    ``ssl_options`` may be either a dictionary (as accepted by
    `ssl_options_to_context`) or an `ssl.SSLContext` object.
    Additional keyword arguments are passed to ``wrap_socket``
    (either the `~ssl.SSLContext` method or the `ssl` module function
    as appropriate).
    """
    context = ssl_options_to_context(ssl_options)
    if hasattr(ssl, 'SSLContext') and isinstance(context, ssl.SSLContext):
        if server_hostname is not None and getattr(ssl, 'HAS_SNI'):
            # Python doesn't have server-side SNI support so we can't
            # really unittest this, but it can be manually tested with
            # python3.2 -m tornado.httpclient https://sni.velox.ch
            return context.wrap_socket(socket, server_hostname=server_hostname,
                                       **kwargs)
        else:
            return context.wrap_socket(socket, **kwargs)
    else:
        return ssl.wrap_socket(socket, **dict(context, **kwargs))

if ssl and hasattr(ssl, 'match_hostname') and hasattr(ssl, 'CertificateError'):  # python 3.2+
    ssl_match_hostname = ssl.match_hostname
    SSLCertificateError = ssl.CertificateError
else:
    # match_hostname was added to the standard library ssl module in python 3.2.
    # The following code was backported for older releases and copied from
    # https://bitbucket.org/brandon/backports.ssl_match_hostname
    class SSLCertificateError(ValueError):
        pass

    def _dnsname_to_pat(dn, max_wildcards=1):
        pats = []
        for frag in dn.split(r'.'):
            if frag.count('*') > max_wildcards:
                # Issue #17980: avoid denials of service by refusing more
                # than one wildcard per fragment.  A survery of established
                # policy among SSL implementations showed it to be a
                # reasonable choice.
                raise SSLCertificateError(
                    "too many wildcards in certificate DNS name: " + repr(dn))
            if frag == '*':
                # When '*' is a fragment by itself, it matches a non-empty dotless
                # fragment.
                pats.append('[^.]+')
            else:
                # Otherwise, '*' matches any dotless fragment.
                frag = re.escape(frag)
                pats.append(frag.replace(r'\*', '[^.]*'))
        return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)

    def ssl_match_hostname(cert, hostname):
        """Verify that *cert* (in decoded format as returned by
        SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
        are mostly followed, but IP addresses are not accepted for *hostname*.

        CertificateError is raised on failure. On success, the function
        returns nothing.
        """
        if not cert:
            raise ValueError("empty or no certificate")
        dnsnames = []
        san = cert.get('subjectAltName', ())
        for key, value in san:
            if key == 'DNS':
                if _dnsname_to_pat(value).match(hostname):
                    return
                dnsnames.append(value)
        if not dnsnames:
            # The subject is only checked when there is no dNSName entry
            # in subjectAltName
            for sub in cert.get('subject', ()):
                for key, value in sub:
                    # XXX according to RFC 2818, the most specific Common Name
                    # must be used.
                    if key == 'commonName':
                        if _dnsname_to_pat(value).match(hostname):
                            return
                        dnsnames.append(value)
        if len(dnsnames) > 1:
            raise SSLCertificateError("hostname %r "
                                      "doesn't match either of %s"
                                      % (hostname, ', '.join(map(repr, dnsnames))))
        elif len(dnsnames) == 1:
            raise SSLCertificateError("hostname %r "
                                      "doesn't match %r"
                                      % (hostname, dnsnames[0]))
        else:
            raise SSLCertificateError("no appropriate commonName or "
                                      "subjectAltName fields were found")

########NEW FILE########
__FILENAME__ = options
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A command line parsing module that lets modules define their own options.

Each module defines its own options which are added to the global
option namespace, e.g.::

    from tornado.options import define, options

    define("mysql_host", default="127.0.0.1:3306", help="Main user DB")
    define("memcache_hosts", default="127.0.0.1:11011", multiple=True,
           help="Main user memcache servers")

    def connect():
        db = database.Connection(options.mysql_host)
        ...

The ``main()`` method of your application does not need to be aware of all of
the options used throughout your program; they are all automatically loaded
when the modules are loaded.  However, all modules that define options
must have been imported before the command line is parsed.

Your ``main()`` method can parse the command line or parse a config file with
either::

    tornado.options.parse_command_line()
    # or
    tornado.options.parse_config_file("/etc/server.conf")

Command line formats are what you would expect (``--myoption=myvalue``).
Config files are just Python files. Global names become options, e.g.::

    myoption = "myvalue"
    myotheroption = "myothervalue"

We support `datetimes <datetime.datetime>`, `timedeltas
<datetime.timedelta>`, ints, and floats (just pass a ``type`` kwarg to
`define`). We also accept multi-value options. See the documentation for
`define()` below.

`tornado.options.options` is a singleton instance of `OptionParser`, and
the top-level functions in this module (`define`, `parse_command_line`, etc)
simply call methods on it.  You may create additional `OptionParser`
instances to define isolated sets of options, such as for subcommands.
"""

from __future__ import absolute_import, division, print_function, with_statement

import datetime
import numbers
import re
import sys
import os
import textwrap

from tornado.escape import _unicode
from tornado.log import define_logging_options
from tornado import stack_context
from tornado.util import basestring_type, exec_in


class Error(Exception):
    """Exception raised by errors in the options module."""
    pass


class OptionParser(object):
    """A collection of options, a dictionary with object-like access.

    Normally accessed via static functions in the `tornado.options` module,
    which reference a global instance.
    """
    def __init__(self):
        # we have to use self.__dict__ because we override setattr.
        self.__dict__['_options'] = {}
        self.__dict__['_parse_callbacks'] = []
        self.define("help", type=bool, help="show this help information",
                    callback=self._help_callback)

    def __getattr__(self, name):
        if isinstance(self._options.get(name), _Option):
            return self._options[name].value()
        raise AttributeError("Unrecognized option %r" % name)

    def __setattr__(self, name, value):
        if isinstance(self._options.get(name), _Option):
            return self._options[name].set(value)
        raise AttributeError("Unrecognized option %r" % name)

    def __iter__(self):
        return iter(self._options)

    def __getitem__(self, item):
        return self._options[item].value()

    def items(self):
        """A sequence of (name, value) pairs.

        .. versionadded:: 3.1
        """
        return [(name, opt.value()) for name, opt in self._options.items()]

    def groups(self):
        """The set of option-groups created by ``define``.

        .. versionadded:: 3.1
        """
        return set(opt.group_name for opt in self._options.values())

    def group_dict(self, group):
        """The names and values of options in a group.

        Useful for copying options into Application settings::

            from tornado.options import define, parse_command_line, options

            define('template_path', group='application')
            define('static_path', group='application')

            parse_command_line()

            application = Application(
                handlers, **options.group_dict('application'))

        .. versionadded:: 3.1
        """
        return dict(
            (name, opt.value()) for name, opt in self._options.items()
            if not group or group == opt.group_name)

    def as_dict(self):
        """The names and values of all options.

        .. versionadded:: 3.1
        """
        return dict(
            (name, opt.value()) for name, opt in self._options.items())

    def define(self, name, default=None, type=None, help=None, metavar=None,
               multiple=False, group=None, callback=None):
        """Defines a new command line option.

        If ``type`` is given (one of str, float, int, datetime, or timedelta)
        or can be inferred from the ``default``, we parse the command line
        arguments based on the given type. If ``multiple`` is True, we accept
        comma-separated values, and the option value is always a list.

        For multi-value integers, we also accept the syntax ``x:y``, which
        turns into ``range(x, y)`` - very useful for long integer ranges.

        ``help`` and ``metavar`` are used to construct the
        automatically generated command line help string. The help
        message is formatted like::

           --name=METAVAR      help string

        ``group`` is used to group the defined options in logical
        groups. By default, command line options are grouped by the
        file in which they are defined.

        Command line option names must be unique globally. They can be parsed
        from the command line with `parse_command_line` or parsed from a
        config file with `parse_config_file`.

        If a ``callback`` is given, it will be run with the new value whenever
        the option is changed.  This can be used to combine command-line
        and file-based options::

            define("config", type=str, help="path to config file",
                   callback=lambda path: parse_config_file(path, final=False))

        With this definition, options in the file specified by ``--config`` will
        override options set earlier on the command line, but can be overridden
        by later flags.
        """
        if name in self._options:
            raise Error("Option %r already defined in %s" %
                        (name, self._options[name].file_name))
        frame = sys._getframe(0)
        options_file = frame.f_code.co_filename
        file_name = frame.f_back.f_code.co_filename
        if file_name == options_file:
            file_name = ""
        if type is None:
            if not multiple and default is not None:
                type = default.__class__
            else:
                type = str
        if group:
            group_name = group
        else:
            group_name = file_name
        self._options[name] = _Option(name, file_name=file_name,
                                      default=default, type=type, help=help,
                                      metavar=metavar, multiple=multiple,
                                      group_name=group_name,
                                      callback=callback)

    def parse_command_line(self, args=None, final=True):
        """Parses all options given on the command line (defaults to
        `sys.argv`).

        Note that ``args[0]`` is ignored since it is the program name
        in `sys.argv`.

        We return a list of all arguments that are not parsed as options.

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.
        """
        if args is None:
            args = sys.argv
        remaining = []
        for i in range(1, len(args)):
            # All things after the last option are command line arguments
            if not args[i].startswith("-"):
                remaining = args[i:]
                break
            if args[i] == "--":
                remaining = args[i + 1:]
                break
            arg = args[i].lstrip("-")
            name, equals, value = arg.partition("=")
            name = name.replace('-', '_')
            if not name in self._options:
                self.print_help()
                raise Error('Unrecognized command line option: %r' % name)
            option = self._options[name]
            if not equals:
                if option.type == bool:
                    value = "true"
                else:
                    raise Error('Option %r requires a value' % name)
            option.parse(value)

        if final:
            self.run_parse_callbacks()

        return remaining

    def parse_config_file(self, path, final=True):
        """Parses and loads the Python config file at the given path.

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.
        """
        config = {}
        with open(path) as f:
            exec_in(f.read(), config, config)
        for name in config:
            if name in self._options:
                self._options[name].set(config[name])

        if final:
            self.run_parse_callbacks()

    def print_help(self, file=None):
        """Prints all the command line options to stderr (or another file)."""
        if file is None:
            file = sys.stderr
        print("Usage: %s [OPTIONS]" % sys.argv[0], file=file)
        print("\nOptions:\n", file=file)
        by_group = {}
        for option in self._options.values():
            by_group.setdefault(option.group_name, []).append(option)

        for filename, o in sorted(by_group.items()):
            if filename:
                print("\n%s options:\n" % os.path.normpath(filename), file=file)
            o.sort(key=lambda option: option.name)
            for option in o:
                prefix = option.name
                if option.metavar:
                    prefix += "=" + option.metavar
                description = option.help or ""
                if option.default is not None and option.default != '':
                    description += " (default %s)" % option.default
                lines = textwrap.wrap(description, 79 - 35)
                if len(prefix) > 30 or len(lines) == 0:
                    lines.insert(0, '')
                print("  --%-30s %s" % (prefix, lines[0]), file=file)
                for line in lines[1:]:
                    print("%-34s %s" % (' ', line), file=file)
        print(file=file)

    def _help_callback(self, value):
        if value:
            self.print_help()
            sys.exit(0)

    def add_parse_callback(self, callback):
        """Adds a parse callback, to be invoked when option parsing is done."""
        self._parse_callbacks.append(stack_context.wrap(callback))

    def run_parse_callbacks(self):
        for callback in self._parse_callbacks:
            callback()

    def mockable(self):
        """Returns a wrapper around self that is compatible with
        `mock.patch <unittest.mock.patch>`.

        The `mock.patch <unittest.mock.patch>` function (included in
        the standard library `unittest.mock` package since Python 3.3,
        or in the third-party ``mock`` package for older versions of
        Python) is incompatible with objects like ``options`` that
        override ``__getattr__`` and ``__setattr__``.  This function
        returns an object that can be used with `mock.patch.object
        <unittest.mock.patch.object>` to modify option values::

            with mock.patch.object(options.mockable(), 'name', value):
                assert options.name == value
        """
        return _Mockable(self)


class _Mockable(object):
    """`mock.patch` compatible wrapper for `OptionParser`.

    As of ``mock`` version 1.0.1, when an object uses ``__getattr__``
    hooks instead of ``__dict__``, ``patch.__exit__`` tries to delete
    the attribute it set instead of setting a new one (assuming that
    the object does not catpure ``__setattr__``, so the patch
    created a new attribute in ``__dict__``).

    _Mockable's getattr and setattr pass through to the underlying
    OptionParser, and delattr undoes the effect of a previous setattr.
    """
    def __init__(self, options):
        # Modify __dict__ directly to bypass __setattr__
        self.__dict__['_options'] = options
        self.__dict__['_originals'] = {}

    def __getattr__(self, name):
        return getattr(self._options, name)

    def __setattr__(self, name, value):
        assert name not in self._originals, "don't reuse mockable objects"
        self._originals[name] = getattr(self._options, name)
        setattr(self._options, name, value)

    def __delattr__(self, name):
        setattr(self._options, name, self._originals.pop(name))


class _Option(object):
    def __init__(self, name, default=None, type=basestring_type, help=None,
                 metavar=None, multiple=False, file_name=None, group_name=None,
                 callback=None):
        if default is None and multiple:
            default = []
        self.name = name
        self.type = type
        self.help = help
        self.metavar = metavar
        self.multiple = multiple
        self.file_name = file_name
        self.group_name = group_name
        self.callback = callback
        self.default = default
        self._value = None

    def value(self):
        return self.default if self._value is None else self._value

    def parse(self, value):
        _parse = {
            datetime.datetime: self._parse_datetime,
            datetime.timedelta: self._parse_timedelta,
            bool: self._parse_bool,
            basestring_type: self._parse_string,
        }.get(self.type, self.type)
        if self.multiple:
            self._value = []
            for part in value.split(","):
                if issubclass(self.type, numbers.Integral):
                    # allow ranges of the form X:Y (inclusive at both ends)
                    lo, _, hi = part.partition(":")
                    lo = _parse(lo)
                    hi = _parse(hi) if hi else lo
                    self._value.extend(range(lo, hi + 1))
                else:
                    self._value.append(_parse(part))
        else:
            self._value = _parse(value)
        if self.callback is not None:
            self.callback(self._value)
        return self.value()

    def set(self, value):
        if self.multiple:
            if not isinstance(value, list):
                raise Error("Option %r is required to be a list of %s" %
                            (self.name, self.type.__name__))
            for item in value:
                if item is not None and not isinstance(item, self.type):
                    raise Error("Option %r is required to be a list of %s" %
                                (self.name, self.type.__name__))
        else:
            if value is not None and not isinstance(value, self.type):
                raise Error("Option %r is required to be a %s (%s given)" %
                            (self.name, self.type.__name__, type(value)))
        self._value = value
        if self.callback is not None:
            self.callback(self._value)

    # Supported date/time formats in our options
    _DATETIME_FORMATS = [
        "%a %b %d %H:%M:%S %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d",
        "%H:%M:%S",
        "%H:%M",
    ]

    def _parse_datetime(self, value):
        for format in self._DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                pass
        raise Error('Unrecognized date/time format: %r' % value)

    _TIMEDELTA_ABBREVS = [
        ('hours', ['h']),
        ('minutes', ['m', 'min']),
        ('seconds', ['s', 'sec']),
        ('milliseconds', ['ms']),
        ('microseconds', ['us']),
        ('days', ['d']),
        ('weeks', ['w']),
    ]

    _TIMEDELTA_ABBREV_DICT = dict(
        (abbrev, full) for full, abbrevs in _TIMEDELTA_ABBREVS
        for abbrev in abbrevs)

    _FLOAT_PATTERN = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

    _TIMEDELTA_PATTERN = re.compile(
        r'\s*(%s)\s*(\w*)\s*' % _FLOAT_PATTERN, re.IGNORECASE)

    def _parse_timedelta(self, value):
        try:
            sum = datetime.timedelta()
            start = 0
            while start < len(value):
                m = self._TIMEDELTA_PATTERN.match(value, start)
                if not m:
                    raise Exception()
                num = float(m.group(1))
                units = m.group(2) or 'seconds'
                units = self._TIMEDELTA_ABBREV_DICT.get(units, units)
                sum += datetime.timedelta(**{units: num})
                start = m.end()
            return sum
        except Exception:
            raise

    def _parse_bool(self, value):
        return value.lower() not in ("false", "0", "f")

    def _parse_string(self, value):
        return _unicode(value)


options = OptionParser()
"""Global options object.

All defined options are available as attributes on this object.
"""


def define(name, default=None, type=None, help=None, metavar=None,
           multiple=False, group=None, callback=None):
    """Defines an option in the global namespace.

    See `OptionParser.define`.
    """
    return options.define(name, default=default, type=type, help=help,
                          metavar=metavar, multiple=multiple, group=group,
                          callback=callback)


def parse_command_line(args=None, final=True):
    """Parses global options from the command line.

    See `OptionParser.parse_command_line`.
    """
    return options.parse_command_line(args, final=final)


def parse_config_file(path, final=True):
    """Parses global options from a config file.

    See `OptionParser.parse_config_file`.
    """
    return options.parse_config_file(path, final=final)


def print_help(file=None):
    """Prints all the command line options to stderr (or another file).

    See `OptionParser.print_help`.
    """
    return options.print_help(file)


def add_parse_callback(callback):
    """Adds a parse callback, to be invoked when option parsing is done.

    See `OptionParser.add_parse_callback`
    """
    options.add_parse_callback(callback)


# Default options
define_logging_options(options)

########NEW FILE########
__FILENAME__ = auto
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Implementation of platform-specific functionality.

For each function or class described in `tornado.platform.interface`,
the appropriate platform-specific implementation exists in this module.
Most code that needs access to this functionality should do e.g.::

    from tornado.platform.auto import set_close_exec
"""

from __future__ import absolute_import, division, print_function, with_statement

import os

if os.name == 'nt':
    from tornado.platform.common import Waker
    from tornado.platform.windows import set_close_exec
else:
    from tornado.platform.posix import set_close_exec, Waker

try:
    # monotime monkey-patches the time module to have a monotonic function
    # in versions of python before 3.3.
    import monotime
except ImportError:
    pass
try:
    from time import monotonic as monotonic_time
except ImportError:
    monotonic_time = None

########NEW FILE########
__FILENAME__ = caresresolver
import pycares
import socket

from tornado import gen
from tornado.ioloop import IOLoop
from tornado.netutil import Resolver, is_valid_ip


class CaresResolver(Resolver):
    """Name resolver based on the c-ares library.

    This is a non-blocking and non-threaded resolver.  It may not produce
    the same results as the system resolver, but can be used for non-blocking
    resolution when threads cannot be used.

    c-ares fails to resolve some names when ``family`` is ``AF_UNSPEC``,
    so it is only recommended for use in ``AF_INET`` (i.e. IPv4).  This is
    the default for ``tornado.simple_httpclient``, but other libraries
    may default to ``AF_UNSPEC``.
    """
    def initialize(self, io_loop=None):
        self.io_loop = io_loop or IOLoop.current()
        self.channel = pycares.Channel(sock_state_cb=self._sock_state_cb)
        self.fds = {}

    def _sock_state_cb(self, fd, readable, writable):
        state = ((IOLoop.READ if readable else 0) |
                 (IOLoop.WRITE if writable else 0))
        if not state:
            self.io_loop.remove_handler(fd)
            del self.fds[fd]
        elif fd in self.fds:
            self.io_loop.update_handler(fd, state)
            self.fds[fd] = state
        else:
            self.io_loop.add_handler(fd, self._handle_events, state)
            self.fds[fd] = state

    def _handle_events(self, fd, events):
        read_fd = pycares.ARES_SOCKET_BAD
        write_fd = pycares.ARES_SOCKET_BAD
        if events & IOLoop.READ:
            read_fd = fd
        if events & IOLoop.WRITE:
            write_fd = fd
        self.channel.process_fd(read_fd, write_fd)

    @gen.coroutine
    def resolve(self, host, port, family=0):
        if is_valid_ip(host):
            addresses = [host]
        else:
            # gethostbyname doesn't take callback as a kwarg
            self.channel.gethostbyname(host, family, (yield gen.Callback(1)))
            callback_args = yield gen.Wait(1)
            assert isinstance(callback_args, gen.Arguments)
            assert not callback_args.kwargs
            result, error = callback_args.args
            if error:
                raise Exception('C-Ares returned error %s: %s while resolving %s' %
                                (error, pycares.errno.strerror(error), host))
            addresses = result.addresses
        addrinfo = []
        for address in addresses:
            if '.' in address:
                address_family = socket.AF_INET
            elif ':' in address:
                address_family = socket.AF_INET6
            else:
                address_family = socket.AF_UNSPEC
            if family != socket.AF_UNSPEC and family != address_family:
                raise Exception('Requested socket family %d but got %d' %
                                (family, address_family))
            addrinfo.append((address_family, (address, port)))
        raise gen.Return(addrinfo)

########NEW FILE########
__FILENAME__ = common
"""Lowest-common-denominator implementations of platform functionality."""
from __future__ import absolute_import, division, print_function, with_statement

import errno
import socket

from tornado.platform import interface


class Waker(interface.Waker):
    """Create an OS independent asynchronous pipe.

    For use on platforms that don't have os.pipe() (or where pipes cannot
    be passed to select()), but do have sockets.  This includes Windows
    and Jython.
    """
    def __init__(self):
        # Based on Zope async.py: http://svn.zope.org/zc.ngi/trunk/src/zc/ngi/async.py

        self.writer = socket.socket()
        # Disable buffering -- pulling the trigger sends 1 byte,
        # and we want that sent immediately, to wake up ASAP.
        self.writer.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        count = 0
        while 1:
            count += 1
            # Bind to a local port; for efficiency, let the OS pick
            # a free port for us.
            # Unfortunately, stress tests showed that we may not
            # be able to connect to that port ("Address already in
            # use") despite that the OS picked it.  This appears
            # to be a race bug in the Windows socket implementation.
            # So we loop until a connect() succeeds (almost always
            # on the first try).  See the long thread at
            # http://mail.zope.org/pipermail/zope/2005-July/160433.html
            # for hideous details.
            a = socket.socket()
            a.bind(("127.0.0.1", 0))
            a.listen(1)
            connect_address = a.getsockname()  # assigned (host, port) pair
            try:
                self.writer.connect(connect_address)
                break    # success
            except socket.error as detail:
                if (not hasattr(errno, 'WSAEADDRINUSE') or
                        detail[0] != errno.WSAEADDRINUSE):
                    # "Address already in use" is the only error
                    # I've seen on two WinXP Pro SP2 boxes, under
                    # Pythons 2.3.5 and 2.4.1.
                    raise
                # (10048, 'Address already in use')
                # assert count <= 2 # never triggered in Tim's tests
                if count >= 10:  # I've never seen it go above 2
                    a.close()
                    self.writer.close()
                    raise socket.error("Cannot bind trigger!")
                # Close `a` and try again.  Note:  I originally put a short
                # sleep() here, but it didn't appear to help or hurt.
                a.close()

        self.reader, addr = a.accept()
        self.reader.setblocking(0)
        self.writer.setblocking(0)
        a.close()
        self.reader_fd = self.reader.fileno()

    def fileno(self):
        return self.reader.fileno()

    def write_fileno(self):
        return self.writer.fileno()

    def wake(self):
        try:
            self.writer.send(b"x")
        except (IOError, socket.error):
            pass

    def consume(self):
        try:
            while True:
                result = self.reader.recv(1024)
                if not result:
                    break
        except (IOError, socket.error):
            pass

    def close(self):
        self.reader.close()
        self.writer.close()

########NEW FILE########
__FILENAME__ = epoll
#!/usr/bin/env python
#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""EPoll-based IOLoop implementation for Linux systems."""
from __future__ import absolute_import, division, print_function, with_statement

import select

from tornado.ioloop import PollIOLoop


class EPollIOLoop(PollIOLoop):
    def initialize(self, **kwargs):
        super(EPollIOLoop, self).initialize(impl=select.epoll(), **kwargs)

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Interfaces for platform-specific functionality.

This module exists primarily for documentation purposes and as base classes
for other tornado.platform modules.  Most code should import the appropriate
implementation from `tornado.platform.auto`.
"""

from __future__ import absolute_import, division, print_function, with_statement


def set_close_exec(fd):
    """Sets the close-on-exec bit (``FD_CLOEXEC``)for a file descriptor."""
    raise NotImplementedError()


class Waker(object):
    """A socket-like object that can wake another thread from ``select()``.

    The `~tornado.ioloop.IOLoop` will add the Waker's `fileno()` to
    its ``select`` (or ``epoll`` or ``kqueue``) calls.  When another
    thread wants to wake up the loop, it calls `wake`.  Once it has woken
    up, it will call `consume` to do any necessary per-wake cleanup.  When
    the ``IOLoop`` is closed, it closes its waker too.
    """
    def fileno(self):
        """Returns the read file descriptor for this waker.

        Must be suitable for use with ``select()`` or equivalent on the
        local platform.
        """
        raise NotImplementedError()

    def write_fileno(self):
        """Returns the write file descriptor for this waker."""
        raise NotImplementedError()

    def wake(self):
        """Triggers activity on the waker's file descriptor."""
        raise NotImplementedError()

    def consume(self):
        """Called after the listen has woken up to do any necessary cleanup."""
        raise NotImplementedError()

    def close(self):
        """Closes the waker's file descriptor(s)."""
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = kqueue
#!/usr/bin/env python
#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""KQueue-based IOLoop implementation for BSD/Mac systems."""
from __future__ import absolute_import, division, print_function, with_statement

import select

from tornado.ioloop import IOLoop, PollIOLoop

assert hasattr(select, 'kqueue'), 'kqueue not supported'


class _KQueue(object):
    """A kqueue-based event loop for BSD/Mac systems."""
    def __init__(self):
        self._kqueue = select.kqueue()
        self._active = {}

    def fileno(self):
        return self._kqueue.fileno()

    def close(self):
        self._kqueue.close()

    def register(self, fd, events):
        if fd in self._active:
            raise IOError("fd %d already registered" % fd)
        self._control(fd, events, select.KQ_EV_ADD)
        self._active[fd] = events

    def modify(self, fd, events):
        self.unregister(fd)
        self.register(fd, events)

    def unregister(self, fd):
        events = self._active.pop(fd)
        self._control(fd, events, select.KQ_EV_DELETE)

    def _control(self, fd, events, flags):
        kevents = []
        if events & IOLoop.WRITE:
            kevents.append(select.kevent(
                fd, filter=select.KQ_FILTER_WRITE, flags=flags))
        if events & IOLoop.READ or not kevents:
            # Always read when there is not a write
            kevents.append(select.kevent(
                fd, filter=select.KQ_FILTER_READ, flags=flags))
        # Even though control() takes a list, it seems to return EINVAL
        # on Mac OS X (10.6) when there is more than one event in the list.
        for kevent in kevents:
            self._kqueue.control([kevent], 0)

    def poll(self, timeout):
        kevents = self._kqueue.control(None, 1000, timeout)
        events = {}
        for kevent in kevents:
            fd = kevent.ident
            if kevent.filter == select.KQ_FILTER_READ:
                events[fd] = events.get(fd, 0) | IOLoop.READ
            if kevent.filter == select.KQ_FILTER_WRITE:
                if kevent.flags & select.KQ_EV_EOF:
                    # If an asynchronous connection is refused, kqueue
                    # returns a write event with the EOF flag set.
                    # Turn this into an error for consistency with the
                    # other IOLoop implementations.
                    # Note that for read events, EOF may be returned before
                    # all data has been consumed from the socket buffer,
                    # so we only check for EOF on write events.
                    events[fd] = IOLoop.ERROR
                else:
                    events[fd] = events.get(fd, 0) | IOLoop.WRITE
            if kevent.flags & select.KQ_EV_ERROR:
                events[fd] = events.get(fd, 0) | IOLoop.ERROR
        return events.items()


class KQueueIOLoop(PollIOLoop):
    def initialize(self, **kwargs):
        super(KQueueIOLoop, self).initialize(impl=_KQueue(), **kwargs)

########NEW FILE########
__FILENAME__ = posix
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Posix implementations of platform-specific functionality."""

from __future__ import absolute_import, division, print_function, with_statement

import fcntl
import os

from tornado.platform import interface


def set_close_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)


def _set_nonblocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


class Waker(interface.Waker):
    def __init__(self):
        r, w = os.pipe()
        _set_nonblocking(r)
        _set_nonblocking(w)
        set_close_exec(r)
        set_close_exec(w)
        self.reader = os.fdopen(r, "rb", 0)
        self.writer = os.fdopen(w, "wb", 0)

    def fileno(self):
        return self.reader.fileno()

    def write_fileno(self):
        return self.writer.fileno()

    def wake(self):
        try:
            self.writer.write(b"x")
        except IOError:
            pass

    def consume(self):
        try:
            while True:
                result = self.reader.read()
                if not result:
                    break
        except IOError:
            pass

    def close(self):
        self.reader.close()
        self.writer.close()

########NEW FILE########
__FILENAME__ = select
#!/usr/bin/env python
#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Select-based IOLoop implementation.

Used as a fallback for systems that don't support epoll or kqueue.
"""
from __future__ import absolute_import, division, print_function, with_statement

import select

from tornado.ioloop import IOLoop, PollIOLoop


class _Select(object):
    """A simple, select()-based IOLoop implementation for non-Linux systems"""
    def __init__(self):
        self.read_fds = set()
        self.write_fds = set()
        self.error_fds = set()
        self.fd_sets = (self.read_fds, self.write_fds, self.error_fds)

    def close(self):
        pass

    def register(self, fd, events):
        if fd in self.read_fds or fd in self.write_fds or fd in self.error_fds:
            raise IOError("fd %d already registered" % fd)
        if events & IOLoop.READ:
            self.read_fds.add(fd)
        if events & IOLoop.WRITE:
            self.write_fds.add(fd)
        if events & IOLoop.ERROR:
            self.error_fds.add(fd)
            # Closed connections are reported as errors by epoll and kqueue,
            # but as zero-byte reads by select, so when errors are requested
            # we need to listen for both read and error.
            self.read_fds.add(fd)

    def modify(self, fd, events):
        self.unregister(fd)
        self.register(fd, events)

    def unregister(self, fd):
        self.read_fds.discard(fd)
        self.write_fds.discard(fd)
        self.error_fds.discard(fd)

    def poll(self, timeout):
        readable, writeable, errors = select.select(
            self.read_fds, self.write_fds, self.error_fds, timeout)
        events = {}
        for fd in readable:
            events[fd] = events.get(fd, 0) | IOLoop.READ
        for fd in writeable:
            events[fd] = events.get(fd, 0) | IOLoop.WRITE
        for fd in errors:
            events[fd] = events.get(fd, 0) | IOLoop.ERROR
        return events.items()


class SelectIOLoop(PollIOLoop):
    def initialize(self, **kwargs):
        super(SelectIOLoop, self).initialize(impl=_Select(), **kwargs)

########NEW FILE########
__FILENAME__ = twisted
# Author: Ovidiu Predescu
# Date: July 2011
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Note:  This module's docs are not currently extracted automatically,
# so changes must be made manually to twisted.rst
# TODO: refactor doc build process to use an appropriate virtualenv
"""Bridges between the Twisted reactor and Tornado IOLoop.

This module lets you run applications and libraries written for
Twisted in a Tornado application.  It can be used in two modes,
depending on which library's underlying event loop you want to use.

This module has been tested with Twisted versions 11.0.0 and newer.

Twisted on Tornado
------------------

`TornadoReactor` implements the Twisted reactor interface on top of
the Tornado IOLoop.  To use it, simply call `install` at the beginning
of the application::

    import tornado.platform.twisted
    tornado.platform.twisted.install()
    from twisted.internet import reactor

When the app is ready to start, call `IOLoop.instance().start()`
instead of `reactor.run()`.

It is also possible to create a non-global reactor by calling
`tornado.platform.twisted.TornadoReactor(io_loop)`.  However, if
the `IOLoop` and reactor are to be short-lived (such as those used in
unit tests), additional cleanup may be required.  Specifically, it is
recommended to call::

    reactor.fireSystemEvent('shutdown')
    reactor.disconnectAll()

before closing the `IOLoop`.

Tornado on Twisted
------------------

`TwistedIOLoop` implements the Tornado IOLoop interface on top of the Twisted
reactor.  Recommended usage::

    from tornado.platform.twisted import TwistedIOLoop
    from twisted.internet import reactor
    TwistedIOLoop().install()
    # Set up your tornado application as usual using `IOLoop.instance`
    reactor.run()

`TwistedIOLoop` always uses the global Twisted reactor.
"""

from __future__ import absolute_import, division, print_function, with_statement

import datetime
import functools
import socket

import twisted.internet.abstract
from twisted.internet.posixbase import PosixReactorBase
from twisted.internet.interfaces import \
    IReactorFDSet, IDelayedCall, IReactorTime, IReadDescriptor, IWriteDescriptor
from twisted.python import failure, log
from twisted.internet import error
import twisted.names.cache
import twisted.names.client
import twisted.names.hosts
import twisted.names.resolve

from zope.interface import implementer

from tornado.escape import utf8
from tornado import gen
import tornado.ioloop
from tornado.log import app_log
from tornado.netutil import Resolver
from tornado.stack_context import NullContext, wrap
from tornado.ioloop import IOLoop


@implementer(IDelayedCall)
class TornadoDelayedCall(object):
    """DelayedCall object for Tornado."""
    def __init__(self, reactor, seconds, f, *args, **kw):
        self._reactor = reactor
        self._func = functools.partial(f, *args, **kw)
        self._time = self._reactor.seconds() + seconds
        self._timeout = self._reactor._io_loop.add_timeout(self._time,
                                                           self._called)
        self._active = True

    def _called(self):
        self._active = False
        self._reactor._removeDelayedCall(self)
        try:
            self._func()
        except:
            app_log.error("_called caught exception", exc_info=True)

    def getTime(self):
        return self._time

    def cancel(self):
        self._active = False
        self._reactor._io_loop.remove_timeout(self._timeout)
        self._reactor._removeDelayedCall(self)

    def delay(self, seconds):
        self._reactor._io_loop.remove_timeout(self._timeout)
        self._time += seconds
        self._timeout = self._reactor._io_loop.add_timeout(self._time,
                                                           self._called)

    def reset(self, seconds):
        self._reactor._io_loop.remove_timeout(self._timeout)
        self._time = self._reactor.seconds() + seconds
        self._timeout = self._reactor._io_loop.add_timeout(self._time,
                                                           self._called)

    def active(self):
        return self._active


@implementer(IReactorTime, IReactorFDSet)
class TornadoReactor(PosixReactorBase):
    """Twisted reactor built on the Tornado IOLoop.

    Since it is intented to be used in applications where the top-level
    event loop is ``io_loop.start()`` rather than ``reactor.run()``,
    it is implemented a little differently than other Twisted reactors.
    We override `mainLoop` instead of `doIteration` and must implement
    timed call functionality on top of `IOLoop.add_timeout` rather than
    using the implementation in `PosixReactorBase`.
    """
    def __init__(self, io_loop=None):
        if not io_loop:
            io_loop = tornado.ioloop.IOLoop.current()
        self._io_loop = io_loop
        self._readers = {}  # map of reader objects to fd
        self._writers = {}  # map of writer objects to fd
        self._fds = {}  # a map of fd to a (reader, writer) tuple
        self._delayedCalls = {}
        PosixReactorBase.__init__(self)
        self.addSystemEventTrigger('during', 'shutdown', self.crash)

        # IOLoop.start() bypasses some of the reactor initialization.
        # Fire off the necessary events if they weren't already triggered
        # by reactor.run().
        def start_if_necessary():
            if not self._started:
                self.fireSystemEvent('startup')
        self._io_loop.add_callback(start_if_necessary)

    # IReactorTime
    def seconds(self):
        return self._io_loop.time()

    def callLater(self, seconds, f, *args, **kw):
        dc = TornadoDelayedCall(self, seconds, f, *args, **kw)
        self._delayedCalls[dc] = True
        return dc

    def getDelayedCalls(self):
        return [x for x in self._delayedCalls if x._active]

    def _removeDelayedCall(self, dc):
        if dc in self._delayedCalls:
            del self._delayedCalls[dc]

    # IReactorThreads
    def callFromThread(self, f, *args, **kw):
        """See `twisted.internet.interfaces.IReactorThreads.callFromThread`"""
        assert callable(f), "%s is not callable" % f
        with NullContext():
            # This NullContext is mainly for an edge case when running
            # TwistedIOLoop on top of a TornadoReactor.
            # TwistedIOLoop.add_callback uses reactor.callFromThread and
            # should not pick up additional StackContexts along the way.
            self._io_loop.add_callback(f, *args, **kw)

    # We don't need the waker code from the super class, Tornado uses
    # its own waker.
    def installWaker(self):
        pass

    def wakeUp(self):
        pass

    # IReactorFDSet
    def _invoke_callback(self, fd, events):
        if fd not in self._fds:
            return
        (reader, writer) = self._fds[fd]
        if reader:
            err = None
            if reader.fileno() == -1:
                err = error.ConnectionLost()
            elif events & IOLoop.READ:
                err = log.callWithLogger(reader, reader.doRead)
            if err is None and events & IOLoop.ERROR:
                err = error.ConnectionLost()
            if err is not None:
                self.removeReader(reader)
                reader.readConnectionLost(failure.Failure(err))
        if writer:
            err = None
            if writer.fileno() == -1:
                err = error.ConnectionLost()
            elif events & IOLoop.WRITE:
                err = log.callWithLogger(writer, writer.doWrite)
            if err is None and events & IOLoop.ERROR:
                err = error.ConnectionLost()
            if err is not None:
                self.removeWriter(writer)
                writer.writeConnectionLost(failure.Failure(err))

    def addReader(self, reader):
        """Add a FileDescriptor for notification of data available to read."""
        if reader in self._readers:
            # Don't add the reader if it's already there
            return
        fd = reader.fileno()
        self._readers[reader] = fd
        if fd in self._fds:
            (_, writer) = self._fds[fd]
            self._fds[fd] = (reader, writer)
            if writer:
                # We already registered this fd for write events,
                # update it for read events as well.
                self._io_loop.update_handler(fd, IOLoop.READ | IOLoop.WRITE)
        else:
            with NullContext():
                self._fds[fd] = (reader, None)
                self._io_loop.add_handler(fd, self._invoke_callback,
                                          IOLoop.READ)

    def addWriter(self, writer):
        """Add a FileDescriptor for notification of data available to write."""
        if writer in self._writers:
            return
        fd = writer.fileno()
        self._writers[writer] = fd
        if fd in self._fds:
            (reader, _) = self._fds[fd]
            self._fds[fd] = (reader, writer)
            if reader:
                # We already registered this fd for read events,
                # update it for write events as well.
                self._io_loop.update_handler(fd, IOLoop.READ | IOLoop.WRITE)
        else:
            with NullContext():
                self._fds[fd] = (None, writer)
                self._io_loop.add_handler(fd, self._invoke_callback,
                                          IOLoop.WRITE)

    def removeReader(self, reader):
        """Remove a Selectable for notification of data available to read."""
        if reader in self._readers:
            fd = self._readers.pop(reader)
            (_, writer) = self._fds[fd]
            if writer:
                # We have a writer so we need to update the IOLoop for
                # write events only.
                self._fds[fd] = (None, writer)
                self._io_loop.update_handler(fd, IOLoop.WRITE)
            else:
                # Since we have no writer registered, we remove the
                # entry from _fds and unregister the handler from the
                # IOLoop
                del self._fds[fd]
                self._io_loop.remove_handler(fd)

    def removeWriter(self, writer):
        """Remove a Selectable for notification of data available to write."""
        if writer in self._writers:
            fd = self._writers.pop(writer)
            (reader, _) = self._fds[fd]
            if reader:
                # We have a reader so we need to update the IOLoop for
                # read events only.
                self._fds[fd] = (reader, None)
                self._io_loop.update_handler(fd, IOLoop.READ)
            else:
                # Since we have no reader registered, we remove the
                # entry from the _fds and unregister the handler from
                # the IOLoop.
                del self._fds[fd]
                self._io_loop.remove_handler(fd)

    def removeAll(self):
        return self._removeAll(self._readers, self._writers)

    def getReaders(self):
        return self._readers.keys()

    def getWriters(self):
        return self._writers.keys()

    # The following functions are mainly used in twisted-style test cases;
    # it is expected that most users of the TornadoReactor will call
    # IOLoop.start() instead of Reactor.run().
    def stop(self):
        PosixReactorBase.stop(self)
        fire_shutdown = functools.partial(self.fireSystemEvent, "shutdown")
        self._io_loop.add_callback(fire_shutdown)

    def crash(self):
        PosixReactorBase.crash(self)
        self._io_loop.stop()

    def doIteration(self, delay):
        raise NotImplementedError("doIteration")

    def mainLoop(self):
        self._io_loop.start()


class _TestReactor(TornadoReactor):
    """Subclass of TornadoReactor for use in unittests.

    This can't go in the test.py file because of import-order dependencies
    with the Twisted reactor test builder.
    """
    def __init__(self):
        # always use a new ioloop
        super(_TestReactor, self).__init__(IOLoop())

    def listenTCP(self, port, factory, backlog=50, interface=''):
        # default to localhost to avoid firewall prompts on the mac
        if not interface:
            interface = '127.0.0.1'
        return super(_TestReactor, self).listenTCP(
            port, factory, backlog=backlog, interface=interface)

    def listenUDP(self, port, protocol, interface='', maxPacketSize=8192):
        if not interface:
            interface = '127.0.0.1'
        return super(_TestReactor, self).listenUDP(
            port, protocol, interface=interface, maxPacketSize=maxPacketSize)


def install(io_loop=None):
    """Install this package as the default Twisted reactor."""
    if not io_loop:
        io_loop = tornado.ioloop.IOLoop.current()
    reactor = TornadoReactor(io_loop)
    from twisted.internet.main import installReactor
    installReactor(reactor)
    return reactor


@implementer(IReadDescriptor, IWriteDescriptor)
class _FD(object):
    def __init__(self, fd, handler):
        self.fd = fd
        self.handler = handler
        self.reading = False
        self.writing = False
        self.lost = False

    def fileno(self):
        return self.fd

    def doRead(self):
        if not self.lost:
            self.handler(self.fd, tornado.ioloop.IOLoop.READ)

    def doWrite(self):
        if not self.lost:
            self.handler(self.fd, tornado.ioloop.IOLoop.WRITE)

    def connectionLost(self, reason):
        if not self.lost:
            self.handler(self.fd, tornado.ioloop.IOLoop.ERROR)
            self.lost = True

    def logPrefix(self):
        return ''


class TwistedIOLoop(tornado.ioloop.IOLoop):
    """IOLoop implementation that runs on Twisted.

    Uses the global Twisted reactor by default.  To create multiple
    `TwistedIOLoops` in the same process, you must pass a unique reactor
    when constructing each one.

    Not compatible with `tornado.process.Subprocess.set_exit_callback`
    because the ``SIGCHLD`` handlers used by Tornado and Twisted conflict
    with each other.
    """
    def initialize(self, reactor=None):
        if reactor is None:
            import twisted.internet.reactor
            reactor = twisted.internet.reactor
        self.reactor = reactor
        self.fds = {}
        self.reactor.callWhenRunning(self.make_current)

    def close(self, all_fds=False):
        self.reactor.removeAll()
        for c in self.reactor.getDelayedCalls():
            c.cancel()

    def add_handler(self, fd, handler, events):
        if fd in self.fds:
            raise ValueError('fd %d added twice' % fd)
        self.fds[fd] = _FD(fd, wrap(handler))
        if events & tornado.ioloop.IOLoop.READ:
            self.fds[fd].reading = True
            self.reactor.addReader(self.fds[fd])
        if events & tornado.ioloop.IOLoop.WRITE:
            self.fds[fd].writing = True
            self.reactor.addWriter(self.fds[fd])

    def update_handler(self, fd, events):
        if events & tornado.ioloop.IOLoop.READ:
            if not self.fds[fd].reading:
                self.fds[fd].reading = True
                self.reactor.addReader(self.fds[fd])
        else:
            if self.fds[fd].reading:
                self.fds[fd].reading = False
                self.reactor.removeReader(self.fds[fd])
        if events & tornado.ioloop.IOLoop.WRITE:
            if not self.fds[fd].writing:
                self.fds[fd].writing = True
                self.reactor.addWriter(self.fds[fd])
        else:
            if self.fds[fd].writing:
                self.fds[fd].writing = False
                self.reactor.removeWriter(self.fds[fd])

    def remove_handler(self, fd):
        if fd not in self.fds:
            return
        self.fds[fd].lost = True
        if self.fds[fd].reading:
            self.reactor.removeReader(self.fds[fd])
        if self.fds[fd].writing:
            self.reactor.removeWriter(self.fds[fd])
        del self.fds[fd]

    def start(self):
        self.reactor.run()

    def stop(self):
        self.reactor.crash()

    def _run_callback(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception:
            self.handle_callback_exception(callback)

    def add_timeout(self, deadline, callback):
        if isinstance(deadline, (int, long, float)):
            delay = max(deadline - self.time(), 0)
        elif isinstance(deadline, datetime.timedelta):
            delay = tornado.ioloop._Timeout.timedelta_to_seconds(deadline)
        else:
            raise TypeError("Unsupported deadline %r")
        return self.reactor.callLater(delay, self._run_callback, wrap(callback))

    def remove_timeout(self, timeout):
        if timeout.active():
            timeout.cancel()

    def add_callback(self, callback, *args, **kwargs):
        self.reactor.callFromThread(self._run_callback,
                                    wrap(callback), *args, **kwargs)

    def add_callback_from_signal(self, callback, *args, **kwargs):
        self.add_callback(callback, *args, **kwargs)


class TwistedResolver(Resolver):
    """Twisted-based asynchronous resolver.

    This is a non-blocking and non-threaded resolver.  It is
    recommended only when threads cannot be used, since it has
    limitations compared to the standard ``getaddrinfo``-based
    `~tornado.netutil.Resolver` and
    `~tornado.netutil.ThreadedResolver`.  Specifically, it returns at
    most one result, and arguments other than ``host`` and ``family``
    are ignored.  It may fail to resolve when ``family`` is not
    ``socket.AF_UNSPEC``.

    Requires Twisted 12.1 or newer.
    """
    def initialize(self, io_loop=None):
        self.io_loop = io_loop or IOLoop.current()
        # partial copy of twisted.names.client.createResolver, which doesn't
        # allow for a reactor to be passed in.
        self.reactor = tornado.platform.twisted.TornadoReactor(io_loop)

        host_resolver = twisted.names.hosts.Resolver('/etc/hosts')
        cache_resolver = twisted.names.cache.CacheResolver(reactor=self.reactor)
        real_resolver = twisted.names.client.Resolver('/etc/resolv.conf',
                                                      reactor=self.reactor)
        self.resolver = twisted.names.resolve.ResolverChain(
            [host_resolver, cache_resolver, real_resolver])

    @gen.coroutine
    def resolve(self, host, port, family=0):
        # getHostByName doesn't accept IP addresses, so if the input
        # looks like an IP address just return it immediately.
        if twisted.internet.abstract.isIPAddress(host):
            resolved = host
            resolved_family = socket.AF_INET
        elif twisted.internet.abstract.isIPv6Address(host):
            resolved = host
            resolved_family = socket.AF_INET6
        else:
            deferred = self.resolver.getHostByName(utf8(host))
            resolved = yield gen.Task(deferred.addCallback)
            if twisted.internet.abstract.isIPAddress(resolved):
                resolved_family = socket.AF_INET
            elif twisted.internet.abstract.isIPv6Address(resolved):
                resolved_family = socket.AF_INET6
            else:
                resolved_family = socket.AF_UNSPEC
        if family != socket.AF_UNSPEC and family != resolved_family:
            raise Exception('Requested socket family %d but got %d' %
                            (family, resolved_family))
        result = [
            (resolved_family, (resolved, port)),
        ]
        raise gen.Return(result)

########NEW FILE########
__FILENAME__ = windows
# NOTE: win32 support is currently experimental, and not recommended
# for production use.


from __future__ import absolute_import, division, print_function, with_statement
import ctypes
import ctypes.wintypes

# See: http://msdn.microsoft.com/en-us/library/ms724935(VS.85).aspx
SetHandleInformation = ctypes.windll.kernel32.SetHandleInformation
SetHandleInformation.argtypes = (ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)
SetHandleInformation.restype = ctypes.wintypes.BOOL

HANDLE_FLAG_INHERIT = 0x00000001


def set_close_exec(fd):
    success = SetHandleInformation(fd, HANDLE_FLAG_INHERIT, 0)
    if not success:
        raise ctypes.GetLastError()

########NEW FILE########
__FILENAME__ = process
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Utilities for working with multiple processes, including both forking
the server into multiple processes and managing subprocesses.
"""

from __future__ import absolute_import, division, print_function, with_statement

import errno
import os
import signal
import subprocess
import sys
import time

from binascii import hexlify

from tornado import ioloop
from tornado.iostream import PipeIOStream
from tornado.log import gen_log
from tornado.platform.auto import set_close_exec
from tornado import stack_context

try:
    long  # py2
except NameError:
    long = int  # py3


def cpu_count():
    """Returns the number of processors on this machine."""
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except [NotImplementedError, ImportError]:
        pass
    try:
        return os.sysconf("SC_NPROCESSORS_CONF")
    except ValueError:
        pass
    gen_log.error("Could not detect number of processors; assuming 1")
    return 1


def _reseed_random():
    if 'random' not in sys.modules:
        return
    import random
    # If os.urandom is available, this method does the same thing as
    # random.seed (at least as of python 2.6).  If os.urandom is not
    # available, we mix in the pid in addition to a timestamp.
    try:
        seed = long(hexlify(os.urandom(16)), 16)
    except NotImplementedError:
        seed = int(time.time() * 1000) ^ os.getpid()
    random.seed(seed)


def _pipe_cloexec():
    r, w = os.pipe()
    set_close_exec(r)
    set_close_exec(w)
    return r, w


_task_id = None


def fork_processes(num_processes, max_restarts=100):
    """Starts multiple worker processes.

    If ``num_processes`` is None or <= 0, we detect the number of cores
    available on this machine and fork that number of child
    processes. If ``num_processes`` is given and > 0, we fork that
    specific number of sub-processes.

    Since we use processes and not threads, there is no shared memory
    between any server code.

    Note that multiple processes are not compatible with the autoreload
    module (or the debug=True option to `tornado.web.Application`).
    When using multiple processes, no IOLoops can be created or
    referenced until after the call to ``fork_processes``.

    In each child process, ``fork_processes`` returns its *task id*, a
    number between 0 and ``num_processes``.  Processes that exit
    abnormally (due to a signal or non-zero exit status) are restarted
    with the same id (up to ``max_restarts`` times).  In the parent
    process, ``fork_processes`` returns None if all child processes
    have exited normally, but will otherwise only exit by throwing an
    exception.
    """
    global _task_id
    assert _task_id is None
    if num_processes is None or num_processes <= 0:
        num_processes = cpu_count()
    if ioloop.IOLoop.initialized():
        raise RuntimeError("Cannot run in multiple processes: IOLoop instance "
                           "has already been initialized. You cannot call "
                           "IOLoop.instance() before calling start_processes()")
    gen_log.info("Starting %d processes", num_processes)
    children = {}

    def start_child(i):
        pid = os.fork()
        if pid == 0:
            # child process
            _reseed_random()
            global _task_id
            _task_id = i
            return i
        else:
            children[pid] = i
            return None
    for i in range(num_processes):
        id = start_child(i)
        if id is not None:
            return id
    num_restarts = 0
    while children:
        try:
            pid, status = os.wait()
        except OSError as e:
            if e.errno == errno.EINTR:
                continue
            raise
        if pid not in children:
            continue
        id = children.pop(pid)
        if os.WIFSIGNALED(status):
            gen_log.warning("child %d (pid %d) killed by signal %d, restarting",
                            id, pid, os.WTERMSIG(status))
        elif os.WEXITSTATUS(status) != 0:
            gen_log.warning("child %d (pid %d) exited with status %d, restarting",
                            id, pid, os.WEXITSTATUS(status))
        else:
            gen_log.info("child %d (pid %d) exited normally", id, pid)
            continue
        num_restarts += 1
        if num_restarts > max_restarts:
            raise RuntimeError("Too many child restarts, giving up")
        new_id = start_child(id)
        if new_id is not None:
            return new_id
    # All child processes exited cleanly, so exit the master process
    # instead of just returning to right after the call to
    # fork_processes (which will probably just start up another IOLoop
    # unless the caller checks the return value).
    sys.exit(0)


def task_id():
    """Returns the current task id, if any.

    Returns None if this process was not created by `fork_processes`.
    """
    global _task_id
    return _task_id


class Subprocess(object):
    """Wraps ``subprocess.Popen`` with IOStream support.

    The constructor is the same as ``subprocess.Popen`` with the following
    additions:

    * ``stdin``, ``stdout``, and ``stderr`` may have the value
      ``tornado.process.Subprocess.STREAM``, which will make the corresponding
      attribute of the resulting Subprocess a `.PipeIOStream`.
    * A new keyword argument ``io_loop`` may be used to pass in an IOLoop.
    """
    STREAM = object()

    _initialized = False
    _waiting = {}

    def __init__(self, *args, **kwargs):
        self.io_loop = kwargs.pop('io_loop', None) or ioloop.IOLoop.current()
        to_close = []
        if kwargs.get('stdin') is Subprocess.STREAM:
            in_r, in_w = _pipe_cloexec()
            kwargs['stdin'] = in_r
            to_close.append(in_r)
            self.stdin = PipeIOStream(in_w, io_loop=self.io_loop)
        if kwargs.get('stdout') is Subprocess.STREAM:
            out_r, out_w = _pipe_cloexec()
            kwargs['stdout'] = out_w
            to_close.append(out_w)
            self.stdout = PipeIOStream(out_r, io_loop=self.io_loop)
        if kwargs.get('stderr') is Subprocess.STREAM:
            err_r, err_w = _pipe_cloexec()
            kwargs['stderr'] = err_w
            to_close.append(err_w)
            self.stderr = PipeIOStream(err_r, io_loop=self.io_loop)
        self.proc = subprocess.Popen(*args, **kwargs)
        for fd in to_close:
            os.close(fd)
        for attr in ['stdin', 'stdout', 'stderr', 'pid']:
            if not hasattr(self, attr):  # don't clobber streams set above
                setattr(self, attr, getattr(self.proc, attr))
        self._exit_callback = None
        self.returncode = None

    def set_exit_callback(self, callback):
        """Runs ``callback`` when this process exits.

        The callback takes one argument, the return code of the process.

        This method uses a ``SIGCHILD`` handler, which is a global setting
        and may conflict if you have other libraries trying to handle the
        same signal.  If you are using more than one ``IOLoop`` it may
        be necessary to call `Subprocess.initialize` first to designate
        one ``IOLoop`` to run the signal handlers.

        In many cases a close callback on the stdout or stderr streams
        can be used as an alternative to an exit callback if the
        signal handler is causing a problem.
        """
        self._exit_callback = stack_context.wrap(callback)
        Subprocess.initialize(self.io_loop)
        Subprocess._waiting[self.pid] = self
        Subprocess._try_cleanup_process(self.pid)

    @classmethod
    def initialize(cls, io_loop=None):
        """Initializes the ``SIGCHILD`` handler.

        The signal handler is run on an `.IOLoop` to avoid locking issues.
        Note that the `.IOLoop` used for signal handling need not be the
        same one used by individual Subprocess objects (as long as the
        ``IOLoops`` are each running in separate threads).
        """
        if cls._initialized:
            return
        if io_loop is None:
            io_loop = ioloop.IOLoop.current()
        cls._old_sigchld = signal.signal(
            signal.SIGCHLD,
            lambda sig, frame: io_loop.add_callback_from_signal(cls._cleanup))
        cls._initialized = True

    @classmethod
    def uninitialize(cls):
        """Removes the ``SIGCHILD`` handler."""
        if not cls._initialized:
            return
        signal.signal(signal.SIGCHLD, cls._old_sigchld)
        cls._initialized = False

    @classmethod
    def _cleanup(cls):
        for pid in list(cls._waiting.keys()):  # make a copy
            cls._try_cleanup_process(pid)

    @classmethod
    def _try_cleanup_process(cls, pid):
        try:
            ret_pid, status = os.waitpid(pid, os.WNOHANG)
        except OSError as e:
            if e.args[0] == errno.ECHILD:
                return
        if ret_pid == 0:
            return
        assert ret_pid == pid
        subproc = cls._waiting.pop(pid)
        subproc.io_loop.add_callback_from_signal(
            subproc._set_returncode, status)

    def _set_returncode(self, status):
        if os.WIFSIGNALED(status):
            self.returncode = -os.WTERMSIG(status)
        else:
            assert os.WIFEXITED(status)
            self.returncode = os.WEXITSTATUS(status)
        if self._exit_callback:
            callback = self._exit_callback
            self._exit_callback = None
            callback(self.returncode)

########NEW FILE########
__FILENAME__ = simple_httpclient
#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, with_statement

from tornado.escape import utf8, _unicode, native_str
from tornado.httpclient import HTTPResponse, HTTPError, AsyncHTTPClient, main, _RequestProxy
from tornado.httputil import HTTPHeaders
from tornado.iostream import IOStream, SSLIOStream
from tornado.netutil import Resolver, OverrideResolver
from tornado.log import gen_log
from tornado import stack_context
from tornado.util import GzipDecompressor

import base64
import collections
import copy
import functools
import os.path
import re
import socket
# import ssl
import sys

try:
    from io import BytesIO  # python 3
except ImportError:
    from cStringIO import StringIO as BytesIO  # python 2

try:
    import urlparse  # py2
except ImportError:
    import urllib.parse as urlparse  # py3

_DEFAULT_CA_CERTS = os.path.dirname(__file__) + '/ca-certificates.crt'


class SimpleAsyncHTTPClient(AsyncHTTPClient):
    """Non-blocking HTTP client with no external dependencies.

    This class implements an HTTP 1.1 client on top of Tornado's IOStreams.
    It does not currently implement all applicable parts of the HTTP
    specification, but it does enough to work with major web service APIs.

    Some features found in the curl-based AsyncHTTPClient are not yet
    supported.  In particular, proxies are not supported, connections
    are not reused, and callers cannot select the network interface to be
    used.
    """
    def initialize(self, io_loop, max_clients=10,
                   hostname_mapping=None, max_buffer_size=104857600,
                   resolver=None, defaults=None):
        """Creates a AsyncHTTPClient.

        Only a single AsyncHTTPClient instance exists per IOLoop
        in order to provide limitations on the number of pending connections.
        force_instance=True may be used to suppress this behavior.

        max_clients is the number of concurrent requests that can be
        in progress.  Note that this arguments are only used when the
        client is first created, and will be ignored when an existing
        client is reused.

        hostname_mapping is a dictionary mapping hostnames to IP addresses.
        It can be used to make local DNS changes when modifying system-wide
        settings like /etc/hosts is not possible or desirable (e.g. in
        unittests).

        max_buffer_size is the number of bytes that can be read by IOStream. It
        defaults to 100mb.
        """
        super(SimpleAsyncHTTPClient, self).initialize(io_loop,
                                                      defaults=defaults)
        self.max_clients = max_clients
        self.queue = collections.deque()
        self.active = {}
        self.max_buffer_size = max_buffer_size
        if resolver:
            self.resolver = resolver
            self.own_resolver = False
        else:
            self.resolver = Resolver(io_loop=io_loop)
            self.own_resolver = True
        if hostname_mapping is not None:
            self.resolver = OverrideResolver(resolver=self.resolver,
                                             mapping=hostname_mapping)

    def close(self):
        super(SimpleAsyncHTTPClient, self).close()
        if self.own_resolver:
            self.resolver.close()

    def fetch_impl(self, request, callback):
        self.queue.append((request, callback))
        self._process_queue()
        if self.queue:
            gen_log.debug("max_clients limit reached, request queued. "
                          "%d active, %d queued requests." % (
                              len(self.active), len(self.queue)))

    def _process_queue(self):
        with stack_context.NullContext():
            while self.queue and len(self.active) < self.max_clients:
                request, callback = self.queue.popleft()
                key = object()
                self.active[key] = (request, callback)
                release_callback = functools.partial(self._release_fetch, key)
                self._handle_request(request, release_callback, callback)

    def _handle_request(self, request, release_callback, final_callback):
        _HTTPConnection(self.io_loop, self, request, release_callback,
                        final_callback, self.max_buffer_size, self.resolver)

    def _release_fetch(self, key):
        del self.active[key]
        self._process_queue()


class _HTTPConnection(object):
    _SUPPORTED_METHODS = set(["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])

    def __init__(self, io_loop, client, request, release_callback,
                 final_callback, max_buffer_size, resolver):
        self.start_time = io_loop.time()
        self.io_loop = io_loop
        self.client = client
        self.request = request
        self.release_callback = release_callback
        self.final_callback = final_callback
        self.max_buffer_size = max_buffer_size
        self.resolver = resolver
        self.code = None
        self.headers = None
        self.chunks = None
        self._decompressor = None
        # Timeout handle returned by IOLoop.add_timeout
        self._timeout = None
        with stack_context.ExceptionStackContext(self._handle_exception):
            self.parsed = urlparse.urlsplit(_unicode(self.request.url))
            if self.parsed.scheme not in ("http", "https"):
                raise ValueError("Unsupported url scheme: %s" %
                                 self.request.url)
            # urlsplit results have hostname and port results, but they
            # didn't support ipv6 literals until python 2.7.
            netloc = self.parsed.netloc
            if "@" in netloc:
                userpass, _, netloc = netloc.rpartition("@")
            match = re.match(r'^(.+):(\d+)$', netloc)
            if match:
                host = match.group(1)
                port = int(match.group(2))
            else:
                host = netloc
                port = 443 if self.parsed.scheme == "https" else 80
            if re.match(r'^\[.*\]$', host):
                # raw ipv6 addresses in urls are enclosed in brackets
                host = host[1:-1]
            self.parsed_hostname = host  # save final host for _on_connect

            if request.allow_ipv6:
                af = socket.AF_UNSPEC
            else:
                # We only try the first IP we get from getaddrinfo,
                # so restrict to ipv4 by default.
                af = socket.AF_INET

            self.resolver.resolve(host, port, af, callback=self._on_resolve)

    def _on_resolve(self, addrinfo):
        self.stream = self._create_stream(addrinfo)
        timeout = min(self.request.connect_timeout, self.request.request_timeout)
        if timeout:
            self._timeout = self.io_loop.add_timeout(
                self.start_time + timeout,
                stack_context.wrap(self._on_timeout))
        self.stream.set_close_callback(self._on_close)
        # ipv6 addresses are broken (in self.parsed.hostname) until
        # 2.7, here is correctly parsed value calculated in __init__
        sockaddr = addrinfo[0][1]
        self.stream.connect(sockaddr, self._on_connect,
                            server_hostname=self.parsed_hostname)

    def _create_stream(self, addrinfo):
        af = addrinfo[0][0]
        if self.parsed.scheme == "https":
            ssl_options = {}
            if self.request.validate_cert:
                ssl_options["cert_reqs"] = ssl.CERT_REQUIRED
            if self.request.ca_certs is not None:
                ssl_options["ca_certs"] = self.request.ca_certs
            else:
                ssl_options["ca_certs"] = _DEFAULT_CA_CERTS
            if self.request.client_key is not None:
                ssl_options["keyfile"] = self.request.client_key
            if self.request.client_cert is not None:
                ssl_options["certfile"] = self.request.client_cert

            # SSL interoperability is tricky.  We want to disable
            # SSLv2 for security reasons; it wasn't disabled by default
            # until openssl 1.0.  The best way to do this is to use
            # the SSL_OP_NO_SSLv2, but that wasn't exposed to python
            # until 3.2.  Python 2.7 adds the ciphers argument, which
            # can also be used to disable SSLv2.  As a last resort
            # on python 2.6, we set ssl_version to SSLv3.  This is
            # more narrow than we'd like since it also breaks
            # compatibility with servers configured for TLSv1 only,
            # but nearly all servers support SSLv3:
            # http://blog.ivanristic.com/2011/09/ssl-survey-protocol-support.html
            if sys.version_info >= (2, 7):
                ssl_options["ciphers"] = "DEFAULT:!SSLv2"
            else:
                # This is really only necessary for pre-1.0 versions
                # of openssl, but python 2.6 doesn't expose version
                # information.
                ssl_options["ssl_version"] = ssl.PROTOCOL_SSLv3

            return SSLIOStream(socket.socket(af),
                               io_loop=self.io_loop,
                               ssl_options=ssl_options,
                               max_buffer_size=self.max_buffer_size)
        else:
            return IOStream(socket.socket(af),
                            io_loop=self.io_loop,
                            max_buffer_size=self.max_buffer_size)

    def _on_timeout(self):
        self._timeout = None
        if self.final_callback is not None:
            raise HTTPError(599, "Timeout")

    def _remove_timeout(self):
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def _on_connect(self):
        self._remove_timeout()
        if self.request.request_timeout:
            self._timeout = self.io_loop.add_timeout(
                self.start_time + self.request.request_timeout,
                stack_context.wrap(self._on_timeout))
        if (self.request.method not in self._SUPPORTED_METHODS and
                not self.request.allow_nonstandard_methods):
            raise KeyError("unknown method %s" % self.request.method)
        for key in ('network_interface',
                    'proxy_host', 'proxy_port',
                    'proxy_username', 'proxy_password'):
            if getattr(self.request, key, None):
                raise NotImplementedError('%s not supported' % key)
        if "Connection" not in self.request.headers:
            self.request.headers["Connection"] = "close"
        if "Host" not in self.request.headers:
            if '@' in self.parsed.netloc:
                self.request.headers["Host"] = self.parsed.netloc.rpartition('@')[-1]
            else:
                self.request.headers["Host"] = self.parsed.netloc
        username, password = None, None
        if self.parsed.username is not None:
            username, password = self.parsed.username, self.parsed.password
        elif self.request.auth_username is not None:
            username = self.request.auth_username
            password = self.request.auth_password or ''
        if username is not None:
            if self.request.auth_mode not in (None, "basic"):
                raise ValueError("unsupported auth_mode %s",
                                 self.request.auth_mode)
            auth = utf8(username) + b":" + utf8(password)
            self.request.headers["Authorization"] = (b"Basic " +
                                                     base64.b64encode(auth))
        if self.request.user_agent:
            self.request.headers["User-Agent"] = self.request.user_agent
        if not self.request.allow_nonstandard_methods:
            if self.request.method in ("POST", "PATCH", "PUT"):
                assert self.request.body is not None
            else:
                assert self.request.body is None
        if self.request.body is not None:
            self.request.headers["Content-Length"] = str(len(
                self.request.body))
        if (self.request.method == "POST" and
                "Content-Type" not in self.request.headers):
            self.request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.request.use_gzip:
            self.request.headers["Accept-Encoding"] = "gzip"
        req_path = ((self.parsed.path or '/') +
                   (('?' + self.parsed.query) if self.parsed.query else ''))
        request_lines = [utf8("%s %s HTTP/1.1" % (self.request.method,
                                                  req_path))]
        for k, v in self.request.headers.get_all():
            line = utf8(k) + b": " + utf8(v)
            if b'\n' in line:
                raise ValueError('Newline in header: ' + repr(line))
            request_lines.append(line)
        request_str = b"\r\n".join(request_lines) + b"\r\n\r\n"
        if self.request.body is not None:
            request_str += self.request.body
        self.stream.set_nodelay(True)
        self.stream.write(request_str)
        self.stream.read_until_regex(b"\r?\n\r?\n", self._on_headers)

    def _release(self):
        if self.release_callback is not None:
            release_callback = self.release_callback
            self.release_callback = None
            release_callback()

    def _run_callback(self, response):
        self._release()
        if self.final_callback is not None:
            final_callback = self.final_callback
            self.final_callback = None
            self.io_loop.add_callback(final_callback, response)

    def _handle_exception(self, typ, value, tb):
        if self.final_callback:
            self._remove_timeout()
            self._run_callback(HTTPResponse(self.request, 599, error=value,
                                            request_time=self.io_loop.time() - self.start_time,
                                            ))

            if hasattr(self, "stream"):
                self.stream.close()
            return True
        else:
            # If our callback has already been called, we are probably
            # catching an exception that is not caused by us but rather
            # some child of our callback. Rather than drop it on the floor,
            # pass it along.
            return False

    def _on_close(self):
        if self.final_callback is not None:
            message = "Connection closed"
            if self.stream.error:
                message = str(self.stream.error)
            raise HTTPError(599, message)

    def _handle_1xx(self, code):
        self.stream.read_until_regex(b"\r?\n\r?\n", self._on_headers)

    def _on_headers(self, data):
        data = native_str(data.decode("latin1"))
        first_line, _, header_data = data.partition("\n")
        match = re.match("HTTP/1.[01] ([0-9]+) ([^\r]*)", first_line)
        assert match
        code = int(match.group(1))
        self.headers = HTTPHeaders.parse(header_data)
        if 100 <= code < 200:
            self._handle_1xx(code)
            return
        else:
            self.code = code
            self.reason = match.group(2)

        if "Content-Length" in self.headers:
            if "," in self.headers["Content-Length"]:
                # Proxies sometimes cause Content-Length headers to get
                # duplicated.  If all the values are identical then we can
                # use them but if they differ it's an error.
                pieces = re.split(r',\s*', self.headers["Content-Length"])
                if any(i != pieces[0] for i in pieces):
                    raise ValueError("Multiple unequal Content-Lengths: %r" %
                                     self.headers["Content-Length"])
                self.headers["Content-Length"] = pieces[0]
            content_length = int(self.headers["Content-Length"])
        else:
            content_length = None

        if self.request.header_callback is not None:
            # re-attach the newline we split on earlier
            self.request.header_callback(first_line + _)
            for k, v in self.headers.get_all():
                self.request.header_callback("%s: %s\r\n" % (k, v))
            self.request.header_callback('\r\n')

        if self.request.method == "HEAD" or self.code == 304:
            # HEAD requests and 304 responses never have content, even
            # though they may have content-length headers
            self._on_body(b"")
            return
        if 100 <= self.code < 200 or self.code == 204:
            # These response codes never have bodies
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.3
            if ("Transfer-Encoding" in self.headers or
                    content_length not in (None, 0)):
                raise ValueError("Response with code %d should not have body" %
                                 self.code)
            self._on_body(b"")
            return

        if (self.request.use_gzip and
                self.headers.get("Content-Encoding") == "gzip"):
            self._decompressor = GzipDecompressor()
        if self.headers.get("Transfer-Encoding") == "chunked":
            self.chunks = []
            self.stream.read_until(b"\r\n", self._on_chunk_length)
        elif content_length is not None:
            self.stream.read_bytes(content_length, self._on_body)
        else:
            self.stream.read_until_close(self._on_body)

    def _on_body(self, data):
        self._remove_timeout()
        original_request = getattr(self.request, "original_request",
                                   self.request)
        if (self.request.follow_redirects and
            self.request.max_redirects > 0 and
                self.code in (301, 302, 303, 307)):
            assert isinstance(self.request, _RequestProxy)
            new_request = copy.copy(self.request.request)
            new_request.url = urlparse.urljoin(self.request.url,
                                               self.headers["Location"])
            new_request.max_redirects = self.request.max_redirects - 1
            del new_request.headers["Host"]
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.4
            # Client SHOULD make a GET request after a 303.
            # According to the spec, 302 should be followed by the same
            # method as the original request, but in practice browsers
            # treat 302 the same as 303, and many servers use 302 for
            # compatibility with pre-HTTP/1.1 user agents which don't
            # understand the 303 status.
            if self.code in (302, 303):
                new_request.method = "GET"
                new_request.body = None
                for h in ["Content-Length", "Content-Type",
                          "Content-Encoding", "Transfer-Encoding"]:
                    try:
                        del self.request.headers[h]
                    except KeyError:
                        pass
            new_request.original_request = original_request
            final_callback = self.final_callback
            self.final_callback = None
            self._release()
            self.client.fetch(new_request, final_callback)
            self._on_end_request()
            return
        if self._decompressor:
            data = (self._decompressor.decompress(data) +
                    self._decompressor.flush())
        if self.request.streaming_callback:
            if self.chunks is None:
                # if chunks is not None, we already called streaming_callback
                # in _on_chunk_data
                self.request.streaming_callback(data)
            buffer = BytesIO()
        else:
            buffer = BytesIO(data)  # TODO: don't require one big string?
        response = HTTPResponse(original_request,
                                self.code, reason=self.reason,
                                headers=self.headers,
                                request_time=self.io_loop.time() - self.start_time,
                                buffer=buffer,
                                effective_url=self.request.url)
        self._run_callback(response)
        self._on_end_request()

    def _on_end_request(self):
        self.stream.close()

    def _on_chunk_length(self, data):
        # TODO: "chunk extensions" http://tools.ietf.org/html/rfc2616#section-3.6.1
        length = int(data.strip(), 16)
        if length == 0:
            if self._decompressor is not None:
                tail = self._decompressor.flush()
                if tail:
                    # I believe the tail will always be empty (i.e.
                    # decompress will return all it can).  The purpose
                    # of the flush call is to detect errors such
                    # as truncated input.  But in case it ever returns
                    # anything, treat it as an extra chunk
                    if self.request.streaming_callback is not None:
                        self.request.streaming_callback(tail)
                    else:
                        self.chunks.append(tail)
                # all the data has been decompressed, so we don't need to
                # decompress again in _on_body
                self._decompressor = None
            self._on_body(b''.join(self.chunks))
        else:
            self.stream.read_bytes(length + 2,  # chunk ends with \r\n
                                   self._on_chunk_data)

    def _on_chunk_data(self, data):
        assert data[-2:] == b"\r\n"
        chunk = data[:-2]
        if self._decompressor:
            chunk = self._decompressor.decompress(chunk)
        if self.request.streaming_callback is not None:
            self.request.streaming_callback(chunk)
        else:
            self.chunks.append(chunk)
        self.stream.read_until(b"\r\n", self._on_chunk_length)


if __name__ == "__main__":
    AsyncHTTPClient.configure(SimpleAsyncHTTPClient)
    main()

########NEW FILE########
__FILENAME__ = stack_context
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""`StackContext` allows applications to maintain threadlocal-like state
that follows execution as it moves to other execution contexts.

The motivating examples are to eliminate the need for explicit
``async_callback`` wrappers (as in `tornado.web.RequestHandler`), and to
allow some additional context to be kept for logging.

This is slightly magic, but it's an extension of the idea that an
exception handler is a kind of stack-local state and when that stack
is suspended and resumed in a new context that state needs to be
preserved.  `StackContext` shifts the burden of restoring that state
from each call site (e.g.  wrapping each `.AsyncHTTPClient` callback
in ``async_callback``) to the mechanisms that transfer control from
one context to another (e.g. `.AsyncHTTPClient` itself, `.IOLoop`,
thread pools, etc).

Example usage::

    @contextlib.contextmanager
    def die_on_error():
        try:
            yield
        except Exception:
            logging.error("exception in asynchronous operation",exc_info=True)
            sys.exit(1)

    with StackContext(die_on_error):
        # Any exception thrown here *or in callback and its desendents*
        # will cause the process to exit instead of spinning endlessly
        # in the ioloop.
        http_client.fetch(url, callback)
    ioloop.start()

Most applications shouln't have to work with `StackContext` directly.
Here are a few rules of thumb for when it's necessary:

* If you're writing an asynchronous library that doesn't rely on a
  stack_context-aware library like `tornado.ioloop` or `tornado.iostream`
  (for example, if you're writing a thread pool), use
  `.stack_context.wrap()` before any asynchronous operations to capture the
  stack context from where the operation was started.

* If you're writing an asynchronous library that has some shared
  resources (such as a connection pool), create those shared resources
  within a ``with stack_context.NullContext():`` block.  This will prevent
  ``StackContexts`` from leaking from one request to another.

* If you want to write something like an exception handler that will
  persist across asynchronous calls, create a new `StackContext` (or
  `ExceptionStackContext`), and make your asynchronous calls in a ``with``
  block that references your `StackContext`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import sys
import threading

from tornado.util import raise_exc_info


class StackContextInconsistentError(Exception):
    pass


class _State(threading.local):
    def __init__(self):
        self.contexts = (tuple(), None)
_state = _State()


class StackContext(object):
    """Establishes the given context as a StackContext that will be transferred.

    Note that the parameter is a callable that returns a context
    manager, not the context itself.  That is, where for a
    non-transferable context manager you would say::

      with my_context():

    StackContext takes the function itself rather than its result::

      with StackContext(my_context):

    The result of ``with StackContext() as cb:`` is a deactivation
    callback.  Run this callback when the StackContext is no longer
    needed to ensure that it is not propagated any further (note that
    deactivating a context does not affect any instances of that
    context that are currently pending).  This is an advanced feature
    and not necessary in most applications.
    """
    def __init__(self, context_factory):
        self.context_factory = context_factory
        self.contexts = []
        self.active = True

    def _deactivate(self):
        self.active = False

    # StackContext protocol
    def enter(self):
        context = self.context_factory()
        self.contexts.append(context)
        context.__enter__()

    def exit(self, type, value, traceback):
        context = self.contexts.pop()
        context.__exit__(type, value, traceback)

    # Note that some of this code is duplicated in ExceptionStackContext
    # below.  ExceptionStackContext is more common and doesn't need
    # the full generality of this class.
    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0] + (self,), self)
        _state.contexts = self.new_contexts

        try:
            self.enter()
        except:
            _state.contexts = self.old_contexts
            raise

        return self._deactivate

    def __exit__(self, type, value, traceback):
        try:
            self.exit(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            # Generator coroutines and with-statements with non-local
            # effects interact badly.  Check here for signs of
            # the stack getting out of sync.
            # Note that this check comes after restoring _state.context
            # so that if it fails things are left in a (relatively)
            # consistent state.
            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')

            # Break up a reference to itself to allow for faster GC on CPython.
            self.new_contexts = None


class ExceptionStackContext(object):
    """Specialization of StackContext for exception handling.

    The supplied ``exception_handler`` function will be called in the
    event of an uncaught exception in this context.  The semantics are
    similar to a try/finally clause, and intended use cases are to log
    an error, close a socket, or similar cleanup actions.  The
    ``exc_info`` triple ``(type, value, traceback)`` will be passed to the
    exception_handler function.

    If the exception handler returns true, the exception will be
    consumed and will not be propagated to other exception handlers.
    """
    def __init__(self, exception_handler):
        self.exception_handler = exception_handler
        self.active = True

    def _deactivate(self):
        self.active = False

    def exit(self, type, value, traceback):
        if type is not None:
            return self.exception_handler(type, value, traceback)

    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0], self)
        _state.contexts = self.new_contexts

        return self._deactivate

    def __exit__(self, type, value, traceback):
        try:
            if type is not None:
                return self.exception_handler(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')

            # Break up a reference to itself to allow for faster GC on CPython.
            self.new_contexts = None


class NullContext(object):
    """Resets the `StackContext`.

    Useful when creating a shared resource on demand (e.g. an
    `.AsyncHTTPClient`) where the stack that caused the creating is
    not relevant to future operations.
    """
    def __enter__(self):
        self.old_contexts = _state.contexts
        _state.contexts = (tuple(), None)

    def __exit__(self, type, value, traceback):
        _state.contexts = self.old_contexts


def _remove_deactivated(contexts):
    """Remove deactivated handlers from the chain"""
    # Clean ctx handlers
    stack_contexts = tuple([h for h in contexts[0] if h.active])

    # Find new head
    head = contexts[1]
    while head is not None and not head.active:
        head = head.old_contexts[1]

    # Process chain
    ctx = head
    while ctx is not None:
        parent = ctx.old_contexts[1]

        while parent is not None:
            if parent.active:
                break
            ctx.old_contexts = parent.old_contexts
            parent = parent.old_contexts[1]

        ctx = parent

    return (stack_contexts, head)


def wrap(fn):
    """Returns a callable object that will restore the current `StackContext`
    when executed.

    Use this whenever saving a callback to be executed later in a
    different execution context (either in a different thread or
    asynchronously in the same thread).
    """
    # Check if function is already wrapped
    if fn is None or hasattr(fn, '_wrapped'):
        return fn

    # Capture current stack head
    # TODO: Any other better way to store contexts and update them in wrapped function?
    cap_contexts = [_state.contexts]

    def wrapped(*args, **kwargs):
        ret = None
        try:
            # Capture old state
            current_state = _state.contexts

            # Remove deactivated items
            cap_contexts[0] = contexts = _remove_deactivated(cap_contexts[0])

            # Force new state
            _state.contexts = contexts

            # Current exception
            exc = (None, None, None)
            top = None

            # Apply stack contexts
            last_ctx = 0
            stack = contexts[0]

            # Apply state
            for n in stack:
                try:
                    n.enter()
                    last_ctx += 1
                except:
                    # Exception happened. Record exception info and store top-most handler
                    exc = sys.exc_info()
                    top = n.old_contexts[1]

            # Execute callback if no exception happened while restoring state
            if top is None:
                try:
                    ret = fn(*args, **kwargs)
                except:
                    exc = sys.exc_info()
                    top = contexts[1]

            # If there was exception, try to handle it by going through the exception chain
            if top is not None:
                exc = _handle_exception(top, exc)
            else:
                # Otherwise take shorter path and run stack contexts in reverse order
                while last_ctx > 0:
                    last_ctx -= 1
                    c = stack[last_ctx]

                    try:
                        c.exit(*exc)
                    except:
                        exc = sys.exc_info()
                        top = c.old_contexts[1]
                        break
                else:
                    top = None

                # If if exception happened while unrolling, take longer exception handler path
                if top is not None:
                    exc = _handle_exception(top, exc)

            # If exception was not handled, raise it
            if exc != (None, None, None):
                raise_exc_info(exc)
        finally:
            _state.contexts = current_state
        return ret

    wrapped._wrapped = True
    return wrapped


def _handle_exception(tail, exc):
    while tail is not None:
        try:
            if tail.exit(*exc):
                exc = (None, None, None)
        except:
            exc = sys.exc_info()

        tail = tail.old_contexts[1]

    return exc


def run_with_stack_context(context, func):
    """Run a coroutine ``func`` in the given `StackContext`.

    It is not safe to have a ``yield`` statement within a ``with StackContext``
    block, so it is difficult to use stack context with `.gen.coroutine`.
    This helper function runs the function in the correct context while
    keeping the ``yield`` and ``with`` statements syntactically separate.

    Example::

        @gen.coroutine
        def incorrect():
            with StackContext(ctx):
                # ERROR: this will raise StackContextInconsistentError
                yield other_coroutine()

        @gen.coroutine
        def correct():
            yield run_with_stack_context(StackContext(ctx), other_coroutine)

    .. versionadded:: 3.1
    """
    with context:
        return func()

########NEW FILE########
__FILENAME__ = tcpserver
#!/usr/bin/env python
#
# Copyright 2011 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A non-blocking, single-threaded TCP server."""
from __future__ import absolute_import, division, print_function, with_statement

import errno
import os
import socket
# import ssl

from tornado.log import app_log
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream, SSLIOStream
from tornado.netutil import bind_sockets, add_accept_handler, ssl_wrap_socket
from tornado import process


class TCPServer(object):
    r"""A non-blocking, single-threaded TCP server.

    To use `TCPServer`, define a subclass which overrides the `handle_stream`
    method.

    To make this server serve SSL traffic, send the ssl_options dictionary
    argument with the arguments required for the `ssl.wrap_socket` method,
    including "certfile" and "keyfile"::

       TCPServer(ssl_options={
           "certfile": os.path.join(data_dir, "mydomain.crt"),
           "keyfile": os.path.join(data_dir, "mydomain.key"),
       })

    `TCPServer` initialization follows one of three patterns:

    1. `listen`: simple single-process::

            server = TCPServer()
            server.listen(8888)
            IOLoop.instance().start()

    2. `bind`/`start`: simple multi-process::

            server = TCPServer()
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.instance().start()

       When using this interface, an `.IOLoop` must *not* be passed
       to the `TCPServer` constructor.  `start` will always start
       the server on the default singleton `.IOLoop`.

    3. `add_sockets`: advanced multi-process::

            sockets = bind_sockets(8888)
            tornado.process.fork_processes(0)
            server = TCPServer()
            server.add_sockets(sockets)
            IOLoop.instance().start()

       The `add_sockets` interface is more complicated, but it can be
       used with `tornado.process.fork_processes` to give you more
       flexibility in when the fork happens.  `add_sockets` can
       also be used in single-process servers if you want to create
       your listening sockets in some way other than
       `~tornado.netutil.bind_sockets`.

    .. versionadded:: 3.1
       The ``max_buffer_size`` argument.
    """
    def __init__(self, io_loop=None, ssl_options=None, max_buffer_size=None):
        self.io_loop = io_loop
        self.ssl_options = ssl_options
        self._sockets = {}  # fd -> socket object
        self._pending_sockets = []
        self._started = False
        self.max_buffer_size = max_buffer_size

        # Verify the SSL options. Otherwise we don't get errors until clients
        # connect. This doesn't verify that the keys are legitimate, but
        # the SSL module doesn't do that until there is a connected socket
        # which seems like too much work
        if self.ssl_options is not None and isinstance(self.ssl_options, dict):
            # Only certfile is required: it can contain both keys
            if 'certfile' not in self.ssl_options:
                raise KeyError('missing key "certfile" in ssl_options')

            if not os.path.exists(self.ssl_options['certfile']):
                raise ValueError('certfile "%s" does not exist' %
                                 self.ssl_options['certfile'])
            if ('keyfile' in self.ssl_options and
                    not os.path.exists(self.ssl_options['keyfile'])):
                raise ValueError('keyfile "%s" does not exist' %
                                 self.ssl_options['keyfile'])

    def listen(self, port, address=""):
        """Starts accepting connections on the given port.

        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately; it is not necessary to call
        `TCPServer.start` afterwards.  It is, however, necessary to start
        the `.IOLoop`.
        """
        sockets = bind_sockets(port, address=address)
        self.add_sockets(sockets)

    def add_sockets(self, sockets):
        """Makes this server start accepting connections on the given sockets.

        The ``sockets`` parameter is a list of socket objects such as
        those returned by `~tornado.netutil.bind_sockets`.
        `add_sockets` is typically used in combination with that
        method and `tornado.process.fork_processes` to provide greater
        control over the initialization of a multi-process server.
        """
        if self.io_loop is None:
            self.io_loop = IOLoop.current()

        for sock in sockets:
            self._sockets[sock.fileno()] = sock
            add_accept_handler(sock, self._handle_connection,
                               io_loop=self.io_loop)

    def add_socket(self, socket):
        """Singular version of `add_sockets`.  Takes a single socket object."""
        self.add_sockets([socket])

    def bind(self, port, address=None, family=socket.AF_UNSPEC, backlog=128):
        """Binds this server to the given port on the given address.

        To start the server, call `start`. If you want to run this server
        in a single process, you can call `listen` as a shortcut to the
        sequence of `bind` and `start` calls.

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the
        name.  Address may be an empty string or None to listen on all
        available interfaces.  Family may be set to either `socket.AF_INET`
        or `socket.AF_INET6` to restrict to IPv4 or IPv6 addresses, otherwise
        both will be used if available.

        The ``backlog`` argument has the same meaning as for
        `socket.listen <socket.socket.listen>`.

        This method may be called multiple times prior to `start` to listen
        on multiple ports or interfaces.
        """
        sockets = bind_sockets(port, address=address, family=family,
                               backlog=backlog)
        if self._started:
            self.add_sockets(sockets)
        else:
            self._pending_sockets.extend(sockets)

    def start(self, num_processes=1):
        """Starts this server in the `.IOLoop`.

        By default, we run the server in this process and do not fork any
        additional child process.

        If num_processes is ``None`` or <= 0, we detect the number of cores
        available on this machine and fork that number of child
        processes. If num_processes is given and > 1, we fork that
        specific number of sub-processes.

        Since we use processes and not threads, there is no shared memory
        between any server code.

        Note that multiple processes are not compatible with the autoreload
        module (or the ``debug=True`` option to `tornado.web.Application`).
        When using multiple processes, no IOLoops can be created or
        referenced until after the call to ``TCPServer.start(n)``.
        """
        assert not self._started
        self._started = True
        if num_processes != 1:
            process.fork_processes(num_processes)
        sockets = self._pending_sockets
        self._pending_sockets = []
        self.add_sockets(sockets)

    def stop(self):
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        for fd, sock in self._sockets.items():
            self.io_loop.remove_handler(fd)
            sock.close()

    def handle_stream(self, stream, address):
        """Override to handle a new `.IOStream` from an incoming connection."""
        raise NotImplementedError()

    def _handle_connection(self, connection, address):
        if self.ssl_options is not None:
            assert ssl, "Python 2.6+ and OpenSSL required for SSL"
            try:
                connection = ssl_wrap_socket(connection,
                                             self.ssl_options,
                                             server_side=True,
                                             do_handshake_on_connect=False)
            except ssl.SSLError as err:
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    return connection.close()
                else:
                    raise
            except socket.error as err:
                # If the connection is closed immediately after it is created
                # (as in a port scan), we can get one of several errors.
                # wrap_socket makes an internal call to getpeername,
                # which may return either EINVAL (Mac OS X) or ENOTCONN
                # (Linux).  If it returns ENOTCONN, this error is
                # silently swallowed by the ssl module, so we need to
                # catch another error later on (AttributeError in
                # SSLIOStream._do_ssl_handshake).
                # To test this behavior, try nmap with the -sT flag.
                # https://github.com/facebook/tornado/pull/750
                if err.args[0] in (errno.ECONNABORTED, errno.EINVAL):
                    return connection.close()
                else:
                    raise
        try:
            if self.ssl_options is not None:
                stream = SSLIOStream(connection, io_loop=self.io_loop, max_buffer_size=self.max_buffer_size)
            else:
                stream = IOStream(connection, io_loop=self.io_loop, max_buffer_size=self.max_buffer_size)
            self.handle_stream(stream, address)
        except Exception:
            app_log.error("Error in connection callback", exc_info=True)

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A simple template system that compiles templates to Python code.

Basic usage looks like::

    t = template.Template("<html>{{ myvalue }}</html>")
    print t.generate(myvalue="XXX")

Loader is a class that loads templates from a root directory and caches
the compiled templates::

    loader = template.Loader("/home/btaylor")
    print loader.load("test.html").generate(myvalue="XXX")

We compile all templates to raw Python. Error-reporting is currently... uh,
interesting. Syntax for the templates::

    ### base.html
    <html>
      <head>
        <title>{% block title %}Default title{% end %}</title>
      </head>
      <body>
        <ul>
          {% for student in students %}
            {% block student %}
              <li>{{ escape(student.name) }}</li>
            {% end %}
          {% end %}
        </ul>
      </body>
    </html>

    ### bold.html
    {% extends "base.html" %}

    {% block title %}A bolder title{% end %}

    {% block student %}
      <li><span style="bold">{{ escape(student.name) }}</span></li>
    {% end %}

Unlike most other template systems, we do not put any restrictions on the
expressions you can include in your statements. if and for blocks get
translated exactly into Python, you can do complex expressions like::

   {% for student in [p for p in people if p.student and p.age > 23] %}
     <li>{{ escape(student.name) }}</li>
   {% end %}

Translating directly to Python means you can apply functions to expressions
easily, like the escape() function in the examples above. You can pass
functions in to your template just like any other variable::

   ### Python code
   def add(x, y):
      return x + y
   template.execute(add=add)

   ### The template
   {{ add(1, 2) }}

We provide the functions escape(), url_escape(), json_encode(), and squeeze()
to all templates by default.

Typical applications do not create `Template` or `Loader` instances by
hand, but instead use the `~.RequestHandler.render` and
`~.RequestHandler.render_string` methods of
`tornado.web.RequestHandler`, which load templates automatically based
on the ``template_path`` `.Application` setting.

Variable names beginning with ``_tt_`` are reserved by the template
system and should not be used by application code.

Syntax Reference
----------------

Template expressions are surrounded by double curly braces: ``{{ ... }}``.
The contents may be any python expression, which will be escaped according
to the current autoescape setting and inserted into the output.  Other
template directives use ``{% %}``.  These tags may be escaped as ``{{!``
and ``{%!`` if you need to include a literal ``{{`` or ``{%`` in the output.

To comment out a section so that it is omitted from the output, surround it
with ``{# ... #}``.

``{% apply *function* %}...{% end %}``
    Applies a function to the output of all template code between ``apply``
    and ``end``::

        {% apply linkify %}{{name}} said: {{message}}{% end %}

    Note that as an implementation detail apply blocks are implemented
    as nested functions and thus may interact strangely with variables
    set via ``{% set %}``, or the use of ``{% break %}`` or ``{% continue %}``
    within loops.

``{% autoescape *function* %}``
    Sets the autoescape mode for the current file.  This does not affect
    other files, even those referenced by ``{% include %}``.  Note that
    autoescaping can also be configured globally, at the `.Application`
    or `Loader`.::

        {% autoescape xhtml_escape %}
        {% autoescape None %}

``{% block *name* %}...{% end %}``
    Indicates a named, replaceable block for use with ``{% extends %}``.
    Blocks in the parent template will be replaced with the contents of
    the same-named block in a child template.::

        <!-- base.html -->
        <title>{% block title %}Default title{% end %}</title>

        <!-- mypage.html -->
        {% extends "base.html" %}
        {% block title %}My page title{% end %}

``{% comment ... %}``
    A comment which will be removed from the template output.  Note that
    there is no ``{% end %}`` tag; the comment goes from the word ``comment``
    to the closing ``%}`` tag.

``{% extends *filename* %}``
    Inherit from another template.  Templates that use ``extends`` should
    contain one or more ``block`` tags to replace content from the parent
    template.  Anything in the child template not contained in a ``block``
    tag will be ignored.  For an example, see the ``{% block %}`` tag.

``{% for *var* in *expr* %}...{% end %}``
    Same as the python ``for`` statement.  ``{% break %}`` and
    ``{% continue %}`` may be used inside the loop.

``{% from *x* import *y* %}``
    Same as the python ``import`` statement.

``{% if *condition* %}...{% elif *condition* %}...{% else %}...{% end %}``
    Conditional statement - outputs the first section whose condition is
    true.  (The ``elif`` and ``else`` sections are optional)

``{% import *module* %}``
    Same as the python ``import`` statement.

``{% include *filename* %}``
    Includes another template file.  The included file can see all the local
    variables as if it were copied directly to the point of the ``include``
    directive (the ``{% autoescape %}`` directive is an exception).
    Alternately, ``{% module Template(filename, **kwargs) %}`` may be used
    to include another template with an isolated namespace.

``{% module *expr* %}``
    Renders a `~tornado.web.UIModule`.  The output of the ``UIModule`` is
    not escaped::

        {% module Template("foo.html", arg=42) %}

``{% raw *expr* %}``
    Outputs the result of the given expression without autoescaping.

``{% set *x* = *y* %}``
    Sets a local variable.

``{% try %}...{% except %}...{% finally %}...{% else %}...{% end %}``
    Same as the python ``try`` statement.

``{% while *condition* %}... {% end %}``
    Same as the python ``while`` statement.  ``{% break %}`` and
    ``{% continue %}`` may be used inside the loop.
"""

from __future__ import absolute_import, division, print_function, with_statement

import datetime
import linecache
import os.path
import posixpath
import re
import threading

from tornado import escape
from tornado.log import app_log
from tornado.util import bytes_type, ObjectDict, exec_in, unicode_type

try:
    from cStringIO import StringIO  # py2
except ImportError:
    from io import StringIO  # py3

_DEFAULT_AUTOESCAPE = "xhtml_escape"
_UNSET = object()


class Template(object):
    """A compiled template.

    We compile into Python from the given template_string. You can generate
    the template from variables with generate().
    """
    # note that the constructor's signature is not extracted with
    # autodoc because _UNSET looks like garbage.  When changing
    # this signature update website/sphinx/template.rst too.
    def __init__(self, template_string, name="<string>", loader=None,
                 compress_whitespace=None, autoescape=_UNSET):
        self.name = name
        if compress_whitespace is None:
            compress_whitespace = name.endswith(".html") or \
                name.endswith(".js")
        if autoescape is not _UNSET:
            self.autoescape = autoescape
        elif loader:
            self.autoescape = loader.autoescape
        else:
            self.autoescape = _DEFAULT_AUTOESCAPE
        self.namespace = loader.namespace if loader else {}
        reader = _TemplateReader(name, escape.native_str(template_string))
        self.file = _File(self, _parse(reader, self))
        self.code = self._generate_python(loader, compress_whitespace)
        self.loader = loader
        try:
            # Under python2.5, the fake filename used here must match
            # the module name used in __name__ below.
            # The dont_inherit flag prevents template.py's future imports
            # from being applied to the generated code.
            self.compiled = compile(
                escape.to_unicode(self.code),
                "%s.generated.py" % self.name.replace('.', '_'),
                "exec", dont_inherit=True)
        except Exception:
            formatted_code = _format_code(self.code).rstrip()
            app_log.error("%s code:\n%s", self.name, formatted_code)
            raise

    def generate(self, **kwargs):
        """Generate this template with the given arguments."""
        namespace = {
            "escape": escape.xhtml_escape,
            "xhtml_escape": escape.xhtml_escape,
            "url_escape": escape.url_escape,
            "json_encode": escape.json_encode,
            "squeeze": escape.squeeze,
            "linkify": escape.linkify,
            "datetime": datetime,
            "_tt_utf8": escape.utf8,  # for internal use
            "_tt_string_types": (unicode_type, bytes_type),
            # __name__ and __loader__ allow the traceback mechanism to find
            # the generated source code.
            "__name__": self.name.replace('.', '_'),
            "__loader__": ObjectDict(get_source=lambda name: self.code),
        }
        namespace.update(self.namespace)
        namespace.update(kwargs)
        exec_in(self.compiled, namespace)
        execute = namespace["_tt_execute"]
        # Clear the traceback module's cache of source data now that
        # we've generated a new template (mainly for this module's
        # unittests, where different tests reuse the same name).
        linecache.clearcache()
        return execute()

    def _generate_python(self, loader, compress_whitespace):
        buffer = StringIO()
        try:
            # named_blocks maps from names to _NamedBlock objects
            named_blocks = {}
            ancestors = self._get_ancestors(loader)
            ancestors.reverse()
            for ancestor in ancestors:
                ancestor.find_named_blocks(loader, named_blocks)
            writer = _CodeWriter(buffer, named_blocks, loader, ancestors[0].template,
                                 compress_whitespace)
            ancestors[0].generate(writer)
            return buffer.getvalue()
        finally:
            buffer.close()

    def _get_ancestors(self, loader):
        ancestors = [self.file]
        for chunk in self.file.body.chunks:
            if isinstance(chunk, _ExtendsBlock):
                if not loader:
                    raise ParseError("{% extends %} block found, but no "
                                     "template loader")
                template = loader.load(chunk.name, self.name)
                ancestors.extend(template._get_ancestors(loader))
        return ancestors


class BaseLoader(object):
    """Base class for template loaders.

    You must use a template loader to use template constructs like
    ``{% extends %}`` and ``{% include %}``. The loader caches all
    templates after they are loaded the first time.
    """
    def __init__(self, autoescape=_DEFAULT_AUTOESCAPE, namespace=None):
        """``autoescape`` must be either None or a string naming a function
        in the template namespace, such as "xhtml_escape".
        """
        self.autoescape = autoescape
        self.namespace = namespace or {}
        self.templates = {}
        # self.lock protects self.templates.  It's a reentrant lock
        # because templates may load other templates via `include` or
        # `extends`.  Note that thanks to the GIL this code would be safe
        # even without the lock, but could lead to wasted work as multiple
        # threads tried to compile the same template simultaneously.
        self.lock = threading.RLock()

    def reset(self):
        """Resets the cache of compiled templates."""
        with self.lock:
            self.templates = {}

    def resolve_path(self, name, parent_path=None):
        """Converts a possibly-relative path to absolute (used internally)."""
        raise NotImplementedError()

    def load(self, name, parent_path=None):
        """Loads a template."""
        name = self.resolve_path(name, parent_path=parent_path)
        with self.lock:
            if name not in self.templates:
                self.templates[name] = self._create_template(name)
            return self.templates[name]

    def _create_template(self, name):
        raise NotImplementedError()


class Loader(BaseLoader):
    """A template loader that loads from a single root directory.
    """
    def __init__(self, root_directory, **kwargs):
        super(Loader, self).__init__(**kwargs)
        self.root = os.path.abspath(root_directory)

    def resolve_path(self, name, parent_path=None):
        if parent_path and not parent_path.startswith("<") and \
            not parent_path.startswith("/") and \
                not name.startswith("/"):
            current_path = os.path.join(self.root, parent_path)
            file_dir = os.path.dirname(os.path.abspath(current_path))
            relative_path = os.path.abspath(os.path.join(file_dir, name))
            if relative_path.startswith(self.root):
                name = relative_path[len(self.root) + 1:]
        return name

    def _create_template(self, name):
        path = os.path.join(self.root, name)
        f = open(path, "rb")
        template = Template(f.read(), name=name, loader=self)
        f.close()
        return template


class DictLoader(BaseLoader):
    """A template loader that loads from a dictionary."""
    def __init__(self, dict, **kwargs):
        super(DictLoader, self).__init__(**kwargs)
        self.dict = dict

    def resolve_path(self, name, parent_path=None):
        if parent_path and not parent_path.startswith("<") and \
            not parent_path.startswith("/") and \
                not name.startswith("/"):
            file_dir = posixpath.dirname(parent_path)
            name = posixpath.normpath(posixpath.join(file_dir, name))
        return name

    def _create_template(self, name):
        return Template(self.dict[name], name=name, loader=self)


class _Node(object):
    def each_child(self):
        return ()

    def generate(self, writer):
        raise NotImplementedError()

    def find_named_blocks(self, loader, named_blocks):
        for child in self.each_child():
            child.find_named_blocks(loader, named_blocks)


class _File(_Node):
    def __init__(self, template, body):
        self.template = template
        self.body = body
        self.line = 0

    def generate(self, writer):
        writer.write_line("def _tt_execute():", self.line)
        with writer.indent():
            writer.write_line("_tt_buffer = []", self.line)
            writer.write_line("_tt_append = _tt_buffer.append", self.line)
            self.body.generate(writer)
            writer.write_line("return _tt_utf8('').join(_tt_buffer)", self.line)

    def each_child(self):
        return (self.body,)


class _ChunkList(_Node):
    def __init__(self, chunks):
        self.chunks = chunks

    def generate(self, writer):
        for chunk in self.chunks:
            chunk.generate(writer)

    def each_child(self):
        return self.chunks


class _NamedBlock(_Node):
    def __init__(self, name, body, template, line):
        self.name = name
        self.body = body
        self.template = template
        self.line = line

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        block = writer.named_blocks[self.name]
        with writer.include(block.template, self.line):
            block.body.generate(writer)

    def find_named_blocks(self, loader, named_blocks):
        named_blocks[self.name] = self
        _Node.find_named_blocks(self, loader, named_blocks)


class _ExtendsBlock(_Node):
    def __init__(self, name):
        self.name = name


class _IncludeBlock(_Node):
    def __init__(self, name, reader, line):
        self.name = name
        self.template_name = reader.name
        self.line = line

    def find_named_blocks(self, loader, named_blocks):
        included = loader.load(self.name, self.template_name)
        included.file.find_named_blocks(loader, named_blocks)

    def generate(self, writer):
        included = writer.loader.load(self.name, self.template_name)
        with writer.include(included, self.line):
            included.file.body.generate(writer)


class _ApplyBlock(_Node):
    def __init__(self, method, line, body=None):
        self.method = method
        self.line = line
        self.body = body

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        method_name = "_tt_apply%d" % writer.apply_counter
        writer.apply_counter += 1
        writer.write_line("def %s():" % method_name, self.line)
        with writer.indent():
            writer.write_line("_tt_buffer = []", self.line)
            writer.write_line("_tt_append = _tt_buffer.append", self.line)
            self.body.generate(writer)
            writer.write_line("return _tt_utf8('').join(_tt_buffer)", self.line)
        writer.write_line("_tt_append(_tt_utf8(%s(%s())))" % (
            self.method, method_name), self.line)


class _ControlBlock(_Node):
    def __init__(self, statement, line, body=None):
        self.statement = statement
        self.line = line
        self.body = body

    def each_child(self):
        return (self.body,)

    def generate(self, writer):
        writer.write_line("%s:" % self.statement, self.line)
        with writer.indent():
            self.body.generate(writer)
            # Just in case the body was empty
            writer.write_line("pass", self.line)


class _IntermediateControlBlock(_Node):
    def __init__(self, statement, line):
        self.statement = statement
        self.line = line

    def generate(self, writer):
        # In case the previous block was empty
        writer.write_line("pass", self.line)
        writer.write_line("%s:" % self.statement, self.line, writer.indent_size() - 1)


class _Statement(_Node):
    def __init__(self, statement, line):
        self.statement = statement
        self.line = line

    def generate(self, writer):
        writer.write_line(self.statement, self.line)


class _Expression(_Node):
    def __init__(self, expression, line, raw=False):
        self.expression = expression
        self.line = line
        self.raw = raw

    def generate(self, writer):
        writer.write_line("_tt_tmp = %s" % self.expression, self.line)
        writer.write_line("if isinstance(_tt_tmp, _tt_string_types):"
                          " _tt_tmp = _tt_utf8(_tt_tmp)", self.line)
        writer.write_line("else: _tt_tmp = _tt_utf8(str(_tt_tmp))", self.line)
        if not self.raw and writer.current_template.autoescape is not None:
            # In python3 functions like xhtml_escape return unicode,
            # so we have to convert to utf8 again.
            writer.write_line("_tt_tmp = _tt_utf8(%s(_tt_tmp))" %
                              writer.current_template.autoescape, self.line)
        writer.write_line("_tt_append(_tt_tmp)", self.line)


class _Module(_Expression):
    def __init__(self, expression, line):
        super(_Module, self).__init__("_tt_modules." + expression, line,
                                      raw=True)


class _Text(_Node):
    def __init__(self, value, line):
        self.value = value
        self.line = line

    def generate(self, writer):
        value = self.value

        # Compress lots of white space to a single character. If the whitespace
        # breaks a line, have it continue to break a line, but just with a
        # single \n character
        if writer.compress_whitespace and "<pre>" not in value:
            value = re.sub(r"([\t ]+)", " ", value)
            value = re.sub(r"(\s*\n\s*)", "\n", value)

        if value:
            writer.write_line('_tt_append(%r)' % escape.utf8(value), self.line)


class ParseError(Exception):
    """Raised for template syntax errors."""
    pass


class _CodeWriter(object):
    def __init__(self, file, named_blocks, loader, current_template,
                 compress_whitespace):
        self.file = file
        self.named_blocks = named_blocks
        self.loader = loader
        self.current_template = current_template
        self.compress_whitespace = compress_whitespace
        self.apply_counter = 0
        self.include_stack = []
        self._indent = 0

    def indent_size(self):
        return self._indent

    def indent(self):
        class Indenter(object):
            def __enter__(_):
                self._indent += 1
                return self

            def __exit__(_, *args):
                assert self._indent > 0
                self._indent -= 1

        return Indenter()

    def include(self, template, line):
        self.include_stack.append((self.current_template, line))
        self.current_template = template

        class IncludeTemplate(object):
            def __enter__(_):
                return self

            def __exit__(_, *args):
                self.current_template = self.include_stack.pop()[0]

        return IncludeTemplate()

    def write_line(self, line, line_number, indent=None):
        if indent is None:
            indent = self._indent
        line_comment = '  # %s:%d' % (self.current_template.name, line_number)
        if self.include_stack:
            ancestors = ["%s:%d" % (tmpl.name, lineno)
                         for (tmpl, lineno) in self.include_stack]
            line_comment += ' (via %s)' % ', '.join(reversed(ancestors))
        print("    " * indent + line + line_comment, file=self.file)


class _TemplateReader(object):
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.line = 1
        self.pos = 0

    def find(self, needle, start=0, end=None):
        assert start >= 0, start
        pos = self.pos
        start += pos
        if end is None:
            index = self.text.find(needle, start)
        else:
            end += pos
            assert end >= start
            index = self.text.find(needle, start, end)
        if index != -1:
            index -= pos
        return index

    def consume(self, count=None):
        if count is None:
            count = len(self.text) - self.pos
        newpos = self.pos + count
        self.line += self.text.count("\n", self.pos, newpos)
        s = self.text[self.pos:newpos]
        self.pos = newpos
        return s

    def remaining(self):
        return len(self.text) - self.pos

    def __len__(self):
        return self.remaining()

    def __getitem__(self, key):
        if type(key) is slice:
            size = len(self)
            start, stop, step = key.indices(size)
            if start is None:
                start = self.pos
            else:
                start += self.pos
            if stop is not None:
                stop += self.pos
            return self.text[slice(start, stop, step)]
        elif key < 0:
            return self.text[key]
        else:
            return self.text[self.pos + key]

    def __str__(self):
        return self.text[self.pos:]


def _format_code(code):
    lines = code.splitlines()
    format = "%%%dd  %%s\n" % len(repr(len(lines) + 1))
    return "".join([format % (i + 1, line) for (i, line) in enumerate(lines)])


def _parse(reader, template, in_block=None, in_loop=None):
    body = _ChunkList([])
    while True:
        # Find next template directive
        curly = 0
        while True:
            curly = reader.find("{", curly)
            if curly == -1 or curly + 1 == reader.remaining():
                # EOF
                if in_block:
                    raise ParseError("Missing {%% end %%} block for %s" %
                                     in_block)
                body.chunks.append(_Text(reader.consume(), reader.line))
                return body
            # If the first curly brace is not the start of a special token,
            # start searching from the character after it
            if reader[curly + 1] not in ("{", "%", "#"):
                curly += 1
                continue
            # When there are more than 2 curlies in a row, use the
            # innermost ones.  This is useful when generating languages
            # like latex where curlies are also meaningful
            if (curly + 2 < reader.remaining() and
                    reader[curly + 1] == '{' and reader[curly + 2] == '{'):
                curly += 1
                continue
            break

        # Append any text before the special token
        if curly > 0:
            cons = reader.consume(curly)
            body.chunks.append(_Text(cons, reader.line))

        start_brace = reader.consume(2)
        line = reader.line

        # Template directives may be escaped as "{{!" or "{%!".
        # In this case output the braces and consume the "!".
        # This is especially useful in conjunction with jquery templates,
        # which also use double braces.
        if reader.remaining() and reader[0] == "!":
            reader.consume(1)
            body.chunks.append(_Text(start_brace, line))
            continue

        # Comment
        if start_brace == "{#":
            end = reader.find("#}")
            if end == -1:
                raise ParseError("Missing end expression #} on line %d" % line)
            contents = reader.consume(end).strip()
            reader.consume(2)
            continue

        # Expression
        if start_brace == "{{":
            end = reader.find("}}")
            if end == -1:
                raise ParseError("Missing end expression }} on line %d" % line)
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise ParseError("Empty expression on line %d" % line)
            body.chunks.append(_Expression(contents, line))
            continue

        # Block
        assert start_brace == "{%", start_brace
        end = reader.find("%}")
        if end == -1:
            raise ParseError("Missing end block %%} on line %d" % line)
        contents = reader.consume(end).strip()
        reader.consume(2)
        if not contents:
            raise ParseError("Empty block tag ({%% %%}) on line %d" % line)

        operator, space, suffix = contents.partition(" ")
        suffix = suffix.strip()

        # Intermediate ("else", "elif", etc) blocks
        intermediate_blocks = {
            "else": set(["if", "for", "while", "try"]),
            "elif": set(["if"]),
            "except": set(["try"]),
            "finally": set(["try"]),
        }
        allowed_parents = intermediate_blocks.get(operator)
        if allowed_parents is not None:
            if not in_block:
                raise ParseError("%s outside %s block" %
                                (operator, allowed_parents))
            if in_block not in allowed_parents:
                raise ParseError("%s block cannot be attached to %s block" % (operator, in_block))
            body.chunks.append(_IntermediateControlBlock(contents, line))
            continue

        # End tag
        elif operator == "end":
            if not in_block:
                raise ParseError("Extra {%% end %%} block on line %d" % line)
            return body

        elif operator in ("extends", "include", "set", "import", "from",
                          "comment", "autoescape", "raw", "module"):
            if operator == "comment":
                continue
            if operator == "extends":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    raise ParseError("extends missing file path on line %d" % line)
                block = _ExtendsBlock(suffix)
            elif operator in ("import", "from"):
                if not suffix:
                    raise ParseError("import missing statement on line %d" % line)
                block = _Statement(contents, line)
            elif operator == "include":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    raise ParseError("include missing file path on line %d" % line)
                block = _IncludeBlock(suffix, reader, line)
            elif operator == "set":
                if not suffix:
                    raise ParseError("set missing statement on line %d" % line)
                block = _Statement(suffix, line)
            elif operator == "autoescape":
                fn = suffix.strip()
                if fn == "None":
                    fn = None
                template.autoescape = fn
                continue
            elif operator == "raw":
                block = _Expression(suffix, line, raw=True)
            elif operator == "module":
                block = _Module(suffix, line)
            body.chunks.append(block)
            continue

        elif operator in ("apply", "block", "try", "if", "for", "while"):
            # parse inner body recursively
            if operator in ("for", "while"):
                block_body = _parse(reader, template, operator, operator)
            elif operator == "apply":
                # apply creates a nested function so syntactically it's not
                # in the loop.
                block_body = _parse(reader, template, operator, None)
            else:
                block_body = _parse(reader, template, operator, in_loop)

            if operator == "apply":
                if not suffix:
                    raise ParseError("apply missing method name on line %d" % line)
                block = _ApplyBlock(suffix, line, block_body)
            elif operator == "block":
                if not suffix:
                    raise ParseError("block missing name on line %d" % line)
                block = _NamedBlock(suffix, block_body, template, line)
            else:
                block = _ControlBlock(contents, line, block_body)
            body.chunks.append(block)
            continue

        elif operator in ("break", "continue"):
            if not in_loop:
                raise ParseError("%s outside %s block" % (operator, set(["for", "while"])))
            body.chunks.append(_Statement(contents, line))
            continue

        else:
            raise ParseError("unknown operator: %r" % operator)

########NEW FILE########
__FILENAME__ = testing
#!/usr/bin/env python
"""Support classes for automated testing.

* `AsyncTestCase` and `AsyncHTTPTestCase`:  Subclasses of unittest.TestCase
  with additional support for testing asynchronous (`.IOLoop` based) code.

* `ExpectLog` and `LogTrapTestCase`: Make test logs less spammy.

* `main()`: A simple test runner (wrapper around unittest.main()) with support
  for the tornado.autoreload module to rerun the tests when code changes.
"""

from __future__ import absolute_import, division, print_function, with_statement

try:
    from tornado import gen
    from tornado.httpclient import AsyncHTTPClient
    from tornado.httpserver import HTTPServer
    from tornado.simple_httpclient import SimpleAsyncHTTPClient
    from tornado.ioloop import IOLoop
    from tornado import netutil
except ImportError:
    # These modules are not importable on app engine.  Parts of this module
    # won't work, but e.g. LogTrapTestCase and main() will.
    AsyncHTTPClient = None
    gen = None
    HTTPServer = None
    IOLoop = None
    netutil = None
    SimpleAsyncHTTPClient = None
from tornado.log import gen_log
from tornado.stack_context import ExceptionStackContext
from tornado.util import raise_exc_info, basestring_type
import functools
import logging
import os
import re
import signal
import socket
import sys

try:
    from cStringIO import StringIO  # py2
except ImportError:
    from io import StringIO  # py3

# Tornado's own test suite requires the updated unittest module
# (either py27+ or unittest2) so tornado.test.util enforces
# this requirement, but for other users of tornado.testing we want
# to allow the older version if unitest2 is not available.
try:
    import unittest2 as unittest
except ImportError:
    import unittest

_next_port = 10000


def get_unused_port():
    """Returns a (hopefully) unused port number.

    This function does not guarantee that the port it returns is available,
    only that a series of get_unused_port calls in a single process return
    distinct ports.

    **Deprecated**.  Use bind_unused_port instead, which is guaranteed
    to find an unused port.
    """
    global _next_port
    port = _next_port
    _next_port = _next_port + 1
    return port


def bind_unused_port():
    """Binds a server socket to an available port on localhost.

    Returns a tuple (socket, port).
    """
    [sock] = netutil.bind_sockets(None, 'localhost', family=socket.AF_INET)
    port = sock.getsockname()[1]
    return sock, port


def get_async_test_timeout():
    """Get the global timeout setting for async tests.

    Returns a float, the timeout in seconds.

    .. versionadded:: 3.1
    """
    try:
        return float(os.environ.get('ASYNC_TEST_TIMEOUT'))
    except (ValueError, TypeError):
        return 5


class AsyncTestCase(unittest.TestCase):
    """`~unittest.TestCase` subclass for testing `.IOLoop`-based
    asynchronous code.

    The unittest framework is synchronous, so the test must be
    complete by the time the test method returns.  This means that
    asynchronous code cannot be used in quite the same way as usual.
    To write test functions that use the same ``yield``-based patterns
    used with the `tornado.gen` module, decorate your test methods
    with `tornado.testing.gen_test` instead of
    `tornado.gen.coroutine`.  This class also provides the `stop()`
    and `wait()` methods for a more manual style of testing.  The test
    method itself must call ``self.wait()``, and asynchronous
    callbacks should call ``self.stop()`` to signal completion.

    By default, a new `.IOLoop` is constructed for each test and is available
    as ``self.io_loop``.  This `.IOLoop` should be used in the construction of
    HTTP clients/servers, etc.  If the code being tested requires a
    global `.IOLoop`, subclasses should override `get_new_ioloop` to return it.

    The `.IOLoop`'s ``start`` and ``stop`` methods should not be
    called directly.  Instead, use `self.stop <stop>` and `self.wait
    <wait>`.  Arguments passed to ``self.stop`` are returned from
    ``self.wait``.  It is possible to have multiple ``wait``/``stop``
    cycles in the same test.

    Example::

        # This test uses coroutine style.
        class MyTestCase(AsyncTestCase):
            @tornado.testing.gen_test
            def test_http_fetch(self):
                client = AsyncHTTPClient(self.io_loop)
                response = yield client.fetch("http://www.tornadoweb.org")
                # Test contents of response
                self.assertIn("FriendFeed", response.body)

        # This test uses argument passing between self.stop and self.wait.
        class MyTestCase2(AsyncTestCase):
            def test_http_fetch(self):
                client = AsyncHTTPClient(self.io_loop)
                client.fetch("http://www.tornadoweb.org/", self.stop)
                response = self.wait()
                # Test contents of response
                self.assertIn("FriendFeed", response.body)

        # This test uses an explicit callback-based style.
        class MyTestCase3(AsyncTestCase):
            def test_http_fetch(self):
                client = AsyncHTTPClient(self.io_loop)
                client.fetch("http://www.tornadoweb.org/", self.handle_fetch)
                self.wait()

            def handle_fetch(self, response):
                # Test contents of response (failures and exceptions here
                # will cause self.wait() to throw an exception and end the
                # test).
                # Exceptions thrown here are magically propagated to
                # self.wait() in test_http_fetch() via stack_context.
                self.assertIn("FriendFeed", response.body)
                self.stop()
    """
    def __init__(self, *args, **kwargs):
        super(AsyncTestCase, self).__init__(*args, **kwargs)
        self.__stopped = False
        self.__running = False
        self.__failure = None
        self.__stop_args = None
        self.__timeout = None

    def setUp(self):
        super(AsyncTestCase, self).setUp()
        self.io_loop = self.get_new_ioloop()
        self.io_loop.make_current()

    def tearDown(self):
        self.io_loop.clear_current()
        if (not IOLoop.initialized() or
                self.io_loop is not IOLoop.instance()):
            # Try to clean up any file descriptors left open in the ioloop.
            # This avoids leaks, especially when tests are run repeatedly
            # in the same process with autoreload (because curl does not
            # set FD_CLOEXEC on its file descriptors)
            self.io_loop.close(all_fds=True)
        super(AsyncTestCase, self).tearDown()
        # In case an exception escaped or the StackContext caught an exception
        # when there wasn't a wait() to re-raise it, do so here.
        # This is our last chance to raise an exception in a way that the
        # unittest machinery understands.
        self.__rethrow()

    def get_new_ioloop(self):
        """Creates a new `.IOLoop` for this test.  May be overridden in
        subclasses for tests that require a specific `.IOLoop` (usually
        the singleton `.IOLoop.instance()`).
        """
        return IOLoop()

    def _handle_exception(self, typ, value, tb):
        self.__failure = (typ, value, tb)
        self.stop()
        return True

    def __rethrow(self):
        if self.__failure is not None:
            failure = self.__failure
            self.__failure = None
            raise_exc_info(failure)

    def run(self, result=None):
        with ExceptionStackContext(self._handle_exception):
            super(AsyncTestCase, self).run(result)
        # As a last resort, if an exception escaped super.run() and wasn't
        # re-raised in tearDown, raise it here.  This will cause the
        # unittest run to fail messily, but that's better than silently
        # ignoring an error.
        self.__rethrow()

    def stop(self, _arg=None, **kwargs):
        """Stops the `.IOLoop`, causing one pending (or future) call to `wait()`
        to return.

        Keyword arguments or a single positional argument passed to `stop()` are
        saved and will be returned by `wait()`.
        """
        assert _arg is None or not kwargs
        self.__stop_args = kwargs or _arg
        if self.__running:
            self.io_loop.stop()
            self.__running = False
        self.__stopped = True

    def wait(self, condition=None, timeout=None):
        """Runs the `.IOLoop` until stop is called or timeout has passed.

        In the event of a timeout, an exception will be thrown. The
        default timeout is 5 seconds; it may be overridden with a
        ``timeout`` keyword argument or globally with the
        ``ASYNC_TEST_TIMEOUT`` environment variable.

        If ``condition`` is not None, the `.IOLoop` will be restarted
        after `stop()` until ``condition()`` returns true.

        .. versionchanged:: 3.1
           Added the ``ASYNC_TEST_TIMEOUT`` environment variable.
        """
        if timeout is None:
            timeout = get_async_test_timeout()

        if not self.__stopped:
            if timeout:
                def timeout_func():
                    try:
                        raise self.failureException(
                            'Async operation timed out after %s seconds' %
                            timeout)
                    except Exception:
                        self.__failure = sys.exc_info()
                    self.stop()
                self.__timeout = self.io_loop.add_timeout(self.io_loop.time() + timeout, timeout_func)
            while True:
                self.__running = True
                self.io_loop.start()
                if (self.__failure is not None or
                        condition is None or condition()):
                    break
            if self.__timeout is not None:
                self.io_loop.remove_timeout(self.__timeout)
                self.__timeout = None
        assert self.__stopped
        self.__stopped = False
        self.__rethrow()
        result = self.__stop_args
        self.__stop_args = None
        return result


class AsyncHTTPTestCase(AsyncTestCase):
    """A test case that starts up an HTTP server.

    Subclasses must override `get_app()`, which returns the
    `tornado.web.Application` (or other `.HTTPServer` callback) to be tested.
    Tests will typically use the provided ``self.http_client`` to fetch
    URLs from this server.

    Example::

        class MyHTTPTest(AsyncHTTPTestCase):
            def get_app(self):
                return Application([('/', MyHandler)...])

            def test_homepage(self):
                # The following two lines are equivalent to
                #   response = self.fetch('/')
                # but are shown in full here to demonstrate explicit use
                # of self.stop and self.wait.
                self.http_client.fetch(self.get_url('/'), self.stop)
                response = self.wait()
                # test contents of response
    """
    def setUp(self):
        super(AsyncHTTPTestCase, self).setUp()
        sock, port = bind_unused_port()
        self.__port = port

        self.http_client = self.get_http_client()
        self._app = self.get_app()
        self.http_server = self.get_http_server()
        self.http_server.add_sockets([sock])

    def get_http_client(self):
        return AsyncHTTPClient(io_loop=self.io_loop)

    def get_http_server(self):
        return HTTPServer(self._app, io_loop=self.io_loop,
                          **self.get_httpserver_options())

    def get_app(self):
        """Should be overridden by subclasses to return a
        `tornado.web.Application` or other `.HTTPServer` callback.
        """
        raise NotImplementedError()

    def fetch(self, path, **kwargs):
        """Convenience method to synchronously fetch a url.

        The given path will be appended to the local server's host and
        port.  Any additional kwargs will be passed directly to
        `.AsyncHTTPClient.fetch` (and so could be used to pass
        ``method="POST"``, ``body="..."``, etc).
        """
        self.http_client.fetch(self.get_url(path), self.stop, **kwargs)
        return self.wait()

    def get_httpserver_options(self):
        """May be overridden by subclasses to return additional
        keyword arguments for the server.
        """
        return {}

    def get_http_port(self):
        """Returns the port used by the server.

        A new port is chosen for each test.
        """
        return self.__port

    def get_protocol(self):
        return 'http'

    def get_url(self, path):
        """Returns an absolute url for the given path on the test server."""
        return '%s://localhost:%s%s' % (self.get_protocol(),
                                        self.get_http_port(), path)

    def tearDown(self):
        self.http_server.stop()
        if (not IOLoop.initialized() or
                self.http_client.io_loop is not IOLoop.instance()):
            self.http_client.close()
        super(AsyncHTTPTestCase, self).tearDown()


class AsyncHTTPSTestCase(AsyncHTTPTestCase):
    """A test case that starts an HTTPS server.

    Interface is generally the same as `AsyncHTTPTestCase`.
    """
    def get_http_client(self):
        # Some versions of libcurl have deadlock bugs with ssl,
        # so always run these tests with SimpleAsyncHTTPClient.
        return SimpleAsyncHTTPClient(io_loop=self.io_loop, force_instance=True,
                                     defaults=dict(validate_cert=False))

    def get_httpserver_options(self):
        return dict(ssl_options=self.get_ssl_options())

    def get_ssl_options(self):
        """May be overridden by subclasses to select SSL options.

        By default includes a self-signed testing certificate.
        """
        # Testing keys were generated with:
        # openssl req -new -keyout tornado/test/test.key -out tornado/test/test.crt -nodes -days 3650 -x509
        module_dir = os.path.dirname(__file__)
        return dict(
            certfile=os.path.join(module_dir, 'test', 'test.crt'),
            keyfile=os.path.join(module_dir, 'test', 'test.key'))

    def get_protocol(self):
        return 'https'


def gen_test(func=None, timeout=None):
    """Testing equivalent of ``@gen.coroutine``, to be applied to test methods.

    ``@gen.coroutine`` cannot be used on tests because the `.IOLoop` is not
    already running.  ``@gen_test`` should be applied to test methods
    on subclasses of `AsyncTestCase`.

    Example::

        class MyTest(AsyncHTTPTestCase):
            @gen_test
            def test_something(self):
                response = yield gen.Task(self.fetch('/'))

    By default, ``@gen_test`` times out after 5 seconds. The timeout may be
    overridden globally with the ``ASYNC_TEST_TIMEOUT`` environment variable,
    or for each test with the ``timeout`` keyword argument::

        class MyTest(AsyncHTTPTestCase):
            @gen_test(timeout=10)
            def test_something_slow(self):
                response = yield gen.Task(self.fetch('/'))

    .. versionadded:: 3.1
       The ``timeout`` argument and ``ASYNC_TEST_TIMEOUT`` environment
       variable.
    """
    if timeout is None:
        timeout = get_async_test_timeout()

    def wrap(f):
        f = gen.coroutine(f)

        @functools.wraps(f)
        def wrapper(self):
            return self.io_loop.run_sync(
                functools.partial(f, self), timeout=timeout)
        return wrapper

    if func is not None:
        # Used like:
        #     @gen_test
        #     def f(self):
        #         pass
        return wrap(func)
    else:
        # Used like @gen_test(timeout=10)
        return wrap


# Without this attribute, nosetests will try to run gen_test as a test
# anywhere it is imported.
gen_test.__test__ = False


class LogTrapTestCase(unittest.TestCase):
    """A test case that captures and discards all logging output
    if the test passes.

    Some libraries can produce a lot of logging output even when
    the test succeeds, so this class can be useful to minimize the noise.
    Simply use it as a base class for your test case.  It is safe to combine
    with AsyncTestCase via multiple inheritance
    (``class MyTestCase(AsyncHTTPTestCase, LogTrapTestCase):``)

    This class assumes that only one log handler is configured and
    that it is a `~logging.StreamHandler`.  This is true for both
    `logging.basicConfig` and the "pretty logging" configured by
    `tornado.options`.  It is not compatible with other log buffering
    mechanisms, such as those provided by some test runners.
    """
    def run(self, result=None):
        logger = logging.getLogger()
        if not logger.handlers:
            logging.basicConfig()
        handler = logger.handlers[0]
        if (len(logger.handlers) > 1 or
                not isinstance(handler, logging.StreamHandler)):
            # Logging has been configured in a way we don't recognize,
            # so just leave it alone.
            super(LogTrapTestCase, self).run(result)
            return
        old_stream = handler.stream
        try:
            handler.stream = StringIO()
            gen_log.info("RUNNING TEST: " + str(self))
            old_error_count = len(result.failures) + len(result.errors)
            super(LogTrapTestCase, self).run(result)
            new_error_count = len(result.failures) + len(result.errors)
            if new_error_count != old_error_count:
                old_stream.write(handler.stream.getvalue())
        finally:
            handler.stream = old_stream


class ExpectLog(logging.Filter):
    """Context manager to capture and suppress expected log output.

    Useful to make tests of error conditions less noisy, while still
    leaving unexpected log entries visible.  *Not thread safe.*

    Usage::

        with ExpectLog('tornado.application', "Uncaught exception"):
            error_response = self.fetch("/some_page")
    """
    def __init__(self, logger, regex, required=True):
        """Constructs an ExpectLog context manager.

        :param logger: Logger object (or name of logger) to watch.  Pass
            an empty string to watch the root logger.
        :param regex: Regular expression to match.  Any log entries on
            the specified logger that match this regex will be suppressed.
        :param required: If true, an exeption will be raised if the end of
            the ``with`` statement is reached without matching any log entries.
        """
        if isinstance(logger, basestring_type):
            logger = logging.getLogger(logger)
        self.logger = logger
        self.regex = re.compile(regex)
        self.required = required
        self.matched = False

    def filter(self, record):
        message = record.getMessage()
        if self.regex.match(message):
            self.matched = True
            return False
        return True

    def __enter__(self):
        self.logger.addFilter(self)

    def __exit__(self, typ, value, tb):
        self.logger.removeFilter(self)
        if not typ and self.required and not self.matched:
            raise Exception("did not get expected log message")


def main(**kwargs):
    """A simple test runner.

    This test runner is essentially equivalent to `unittest.main` from
    the standard library, but adds support for tornado-style option
    parsing and log formatting.

    The easiest way to run a test is via the command line::

        python -m tornado.testing tornado.test.stack_context_test

    See the standard library unittest module for ways in which tests can
    be specified.

    Projects with many tests may wish to define a test script like
    ``tornado/test/runtests.py``.  This script should define a method
    ``all()`` which returns a test suite and then call
    `tornado.testing.main()`.  Note that even when a test script is
    used, the ``all()`` test suite may be overridden by naming a
    single test on the command line::

        # Runs all tests
        python -m tornado.test.runtests
        # Runs one test
        python -m tornado.test.runtests tornado.test.stack_context_test

    Additional keyword arguments passed through to ``unittest.main()``.
    For example, use ``tornado.testing.main(verbosity=2)``
    to show many test details as they are run.
    See http://docs.python.org/library/unittest.html#unittest.main
    for full argument list.
    """
    from tornado.options import define, options, parse_command_line

    define('exception_on_interrupt', type=bool, default=True,
           help=("If true (default), ctrl-c raises a KeyboardInterrupt "
                 "exception.  This prints a stack trace but cannot interrupt "
                 "certain operations.  If false, the process is more reliably "
                 "killed, but does not print a stack trace."))

    # support the same options as unittest's command-line interface
    define('verbose', type=bool)
    define('quiet', type=bool)
    define('failfast', type=bool)
    define('catch', type=bool)
    define('buffer', type=bool)

    argv = [sys.argv[0]] + parse_command_line(sys.argv)

    if not options.exception_on_interrupt:
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    if options.verbose is not None:
        kwargs['verbosity'] = 2
    if options.quiet is not None:
        kwargs['verbosity'] = 0
    if options.failfast is not None:
        kwargs['failfast'] = True
    if options.catch is not None:
        kwargs['catchbreak'] = True
    if options.buffer is not None:
        kwargs['buffer'] = True

    if __name__ == '__main__' and len(argv) == 1:
        print("No tests specified", file=sys.stderr)
        sys.exit(1)
    try:
        # In order to be able to run tests by their fully-qualified name
        # on the command line without importing all tests here,
        # module must be set to None.  Python 3.2's unittest.main ignores
        # defaultTest if no module is given (it tries to do its own
        # test discovery, which is incompatible with auto2to3), so don't
        # set module if we're not asking for a specific test.
        if len(argv) > 1:
            unittest.main(module=None, argv=argv, **kwargs)
        else:
            unittest.main(defaultTest="all", argv=argv, **kwargs)
    except SystemExit as e:
        if e.code == 0:
            gen_log.info('PASS')
        else:
            gen_log.error('FAIL')
        raise

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = util
"""Miscellaneous utility functions and classes.

This module is used internally by Tornado.  It is not necessarily expected
that the functions and classes defined here will be useful to other
applications, but they are documented here in case they are.

The one public-facing part of this module is the `Configurable` class
and its `~Configurable.configure` method, which becomes a part of the
interface of its subclasses, including `.AsyncHTTPClient`, `.IOLoop`,
and `.Resolver`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import inspect
import sys
import zlib


class ObjectDict(dict):
    """Makes a dictionary behave like an object, with attribute-style access.
    """
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class GzipDecompressor(object):
    """Streaming gzip decompressor.

    The interface is like that of `zlib.decompressobj` (without the
    optional arguments, but it understands gzip headers and checksums.
    """
    def __init__(self):
        # Magic parameter makes zlib module understand gzip header
        # http://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
        # This works on cpython and pypy, but not jython.
        self.decompressobj = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def decompress(self, value):
        """Decompress a chunk, returning newly-available data.

        Some data may be buffered for later processing; `flush` must
        be called when there is no more input data to ensure that
        all data was processed.
        """
        return self.decompressobj.decompress(value)

    def flush(self):
        """Return any remaining buffered data not yet returned by decompress.

        Also checks for errors such as truncated input.
        No other methods may be called on this object after `flush`.
        """
        return self.decompressobj.flush()


def import_object(name):
    """Imports an object by name.

    import_object('x') is equivalent to 'import x'.
    import_object('x.y.z') is equivalent to 'from x.y import z'.

    >>> import tornado.escape
    >>> import_object('tornado.escape') is tornado.escape
    True
    >>> import_object('tornado.escape.utf8') is tornado.escape.utf8
    True
    >>> import_object('tornado') is tornado
    True
    >>> import_object('tornado.missing_module')
    Traceback (most recent call last):
        ...
    ImportError: No module named missing_module
    """
    if name.count('.') == 0:
        return __import__(name, None, None)

    parts = name.split('.')
    obj = __import__('.'.join(parts[:-1]), None, None, [parts[-1]], 0)
    try:
        return getattr(obj, parts[-1])
    except AttributeError:
        raise ImportError("No module named %s" % parts[-1])


# Fake unicode literal support:  Python 3.2 doesn't have the u'' marker for
# literal strings, and alternative solutions like "from __future__ import
# unicode_literals" have other problems (see PEP 414).  u() can be applied
# to ascii strings that include \u escapes (but they must not contain
# literal non-ascii characters).
if type('') is not type(b''):
    def u(s):
        return s
    bytes_type = bytes
    unicode_type = str
    basestring_type = str
else:
    def u(s):
        return s.decode('unicode_escape')
    bytes_type = str
    unicode_type = unicode
    basestring_type = basestring


if sys.version_info > (3,):
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[1].with_traceback(exc_info[2])

def exec_in(code, glob, loc=None):
    if isinstance(code, str):
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec(code, glob, loc)
""")
else:
    exec("""
def raise_exc_info(exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]

def exec_in(code, glob, loc=None):
    if isinstance(code, basestring):
        # exec(string) inherits the caller's future imports; compile
        # the string first to prevent that.
        code = compile(code, '<string>', 'exec', dont_inherit=True)
    exec code in glob, loc
""")


class Configurable(object):
    """Base class for configurable interfaces.

    A configurable interface is an (abstract) class whose constructor
    acts as a factory function for one of its implementation subclasses.
    The implementation subclass as well as optional keyword arguments to
    its initializer can be set globally at runtime with `configure`.

    By using the constructor as the factory method, the interface
    looks like a normal class, `isinstance` works as usual, etc.  This
    pattern is most useful when the choice of implementation is likely
    to be a global decision (e.g. when `~select.epoll` is available,
    always use it instead of `~select.select`), or when a
    previously-monolithic class has been split into specialized
    subclasses.

    Configurable subclasses must define the class methods
    `configurable_base` and `configurable_default`, and use the instance
    method `initialize` instead of ``__init__``.
    """
    __impl_class = None
    __impl_kwargs = None

    def __new__(cls, **kwargs):
        base = cls.configurable_base()
        args = {}
        if cls is base:
            impl = cls.configured_class()
            if base.__impl_kwargs:
                args.update(base.__impl_kwargs)
        else:
            impl = cls
        args.update(kwargs)
        instance = super(Configurable, cls).__new__(impl)
        # initialize vs __init__ chosen for compatiblity with AsyncHTTPClient
        # singleton magic.  If we get rid of that we can switch to __init__
        # here too.
        instance.initialize(**args)
        return instance

    @classmethod
    def configurable_base(cls):
        """Returns the base class of a configurable hierarchy.

        This will normally return the class in which it is defined.
        (which is *not* necessarily the same as the cls classmethod parameter).
        """
        raise NotImplementedError()

    @classmethod
    def configurable_default(cls):
        """Returns the implementation class to be used if none is configured."""
        raise NotImplementedError()

    def initialize(self):
        """Initialize a `Configurable` subclass instance.

        Configurable classes should use `initialize` instead of ``__init__``.
        """

    @classmethod
    def configure(cls, impl, **kwargs):
        """Sets the class to use when the base class is instantiated.

        Keyword arguments will be saved and added to the arguments passed
        to the constructor.  This can be used to set global defaults for
        some parameters.
        """
        base = cls.configurable_base()
        if isinstance(impl, (unicode_type, bytes_type)):
            impl = import_object(impl)
        if impl is not None and not issubclass(impl, cls):
            raise ValueError("Invalid subclass of %s" % cls)
        base.__impl_class = impl
        base.__impl_kwargs = kwargs

    @classmethod
    def configured_class(cls):
        """Returns the currently configured class."""
        base = cls.configurable_base()
        if cls.__impl_class is None:
            base.__impl_class = cls.configurable_default()
        return base.__impl_class

    @classmethod
    def _save_configuration(cls):
        base = cls.configurable_base()
        return (base.__impl_class, base.__impl_kwargs)

    @classmethod
    def _restore_configuration(cls, saved):
        base = cls.configurable_base()
        base.__impl_class = saved[0]
        base.__impl_kwargs = saved[1]


class ArgReplacer(object):
    """Replaces one value in an ``args, kwargs`` pair.

    Inspects the function signature to find an argument by name
    whether it is passed by position or keyword.  For use in decorators
    and similar wrappers.
    """
    def __init__(self, func, name):
        self.name = name
        try:
            self.arg_pos = inspect.getargspec(func).args.index(self.name)
        except ValueError:
            # Not a positional parameter
            self.arg_pos = None

    def replace(self, new_value, args, kwargs):
        """Replace the named argument in ``args, kwargs`` with ``new_value``.

        Returns ``(old_value, args, kwargs)``.  The returned ``args`` and
        ``kwargs`` objects may not be the same as the input objects, or
        the input objects may be mutated.

        If the named argument was not found, ``new_value`` will be added
        to ``kwargs`` and None will be returned as ``old_value``.
        """
        if self.arg_pos is not None and len(args) > self.arg_pos:
            # The arg to replace is passed positionally
            old_value = args[self.arg_pos]
            args = list(args)  # *args is normally a tuple
            args[self.arg_pos] = new_value
        else:
            # The arg to replace is either omitted or passed by keyword.
            old_value = kwargs.get(self.name)
            kwargs[self.name] = new_value
        return old_value, args, kwargs


def doctests():
    import doctest
    return doctest.DocTestSuite()

########NEW FILE########
__FILENAME__ = web
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""``tornado.web`` provides a simple web framework with asynchronous
features that allow it to scale to large numbers of open connections,
making it ideal for `long polling
<http://en.wikipedia.org/wiki/Push_technology#Long_polling>`_.

Here is a simple "Hello, world" example app::

    import tornado.ioloop
    import tornado.web

    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            self.write("Hello, world")

    if __name__ == "__main__":
        application = tornado.web.Application([
            (r"/", MainHandler),
        ])
        application.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

See the :doc:`Tornado overview <overview>` for more details and a good getting
started guide.

Thread-safety notes
-------------------

In general, methods on `RequestHandler` and elsewhere in Tornado are
not thread-safe.  In particular, methods such as
`~RequestHandler.write()`, `~RequestHandler.finish()`, and
`~RequestHandler.flush()` must only be called from the main thread.  If
you use multiple threads it is important to use `.IOLoop.add_callback`
to transfer control back to the main thread before finishing the
request.
"""

from __future__ import absolute_import, division, print_function, with_statement


import base64
import binascii
import datetime
import email.utils
import functools
import gzip
import hashlib
import hmac
import mimetypes
import numbers
import os.path
import re
import stat
import sys
import threading
import time
import tornado
import traceback
import types
import uuid

from tornado.concurrent import Future
from tornado import escape
from tornado import httputil
from tornado import locale
from tornado.log import access_log, app_log, gen_log
from tornado import stack_context
from tornado import template
from tornado.escape import utf8, _unicode
from tornado.util import bytes_type, import_object, ObjectDict, raise_exc_info, unicode_type

try:
    from io import BytesIO  # python 3
except ImportError:
    from cStringIO import StringIO as BytesIO  # python 2

try:
    import Cookie  # py2
except ImportError:
    import http.cookies as Cookie  # py3

try:
    import urlparse  # py2
except ImportError:
    import urllib.parse as urlparse  # py3

try:
    from urllib import urlencode  # py2
except ImportError:
    from urllib.parse import urlencode  # py3


class RequestHandler(object):
    """Subclass this class and define `get()` or `post()` to make a handler.

    If you want to support more methods than the standard GET/HEAD/POST, you
    should override the class variable ``SUPPORTED_METHODS`` in your
    `RequestHandler` subclass.
    """
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PATCH", "PUT",
                         "OPTIONS")

    _template_loaders = {}  # {path: template.BaseLoader}
    _template_loader_lock = threading.Lock()
    _remove_control_chars_regex = re.compile(r"[\x00-\x08\x0e-\x1f]")

    def __init__(self, application, request, **kwargs):
        super(RequestHandler, self).__init__()

        self.application = application
        self.request = request
        self._headers_written = False
        self._finished = False
        self._auto_finish = True
        self._transforms = None  # will be set in _execute
        self.path_args = None
        self.path_kwargs = None
        self.ui = ObjectDict((n, self._ui_method(m)) for n, m in
                             application.ui_methods.items())
        # UIModules are available as both `modules` and `_tt_modules` in the
        # template namespace.  Historically only `modules` was available
        # but could be clobbered by user additions to the namespace.
        # The template {% module %} directive looks in `_tt_modules` to avoid
        # possible conflicts.
        self.ui["_tt_modules"] = _UIModuleNamespace(self,
                                                    application.ui_modules)
        self.ui["modules"] = self.ui["_tt_modules"]
        self.clear()
        # Check since connection is not available in WSGI
        if getattr(self.request, "connection", None):
            self.request.connection.set_close_callback(
                self.on_connection_close)
        self.initialize(**kwargs)

    def initialize(self):
        """Hook for subclass initialization.

        A dictionary passed as the third argument of a url spec will be
        supplied as keyword arguments to initialize().

        Example::

            class ProfileHandler(RequestHandler):
                def initialize(self, database):
                    self.database = database

                def get(self, username):
                    ...

            app = Application([
                (r'/user/(.*)', ProfileHandler, dict(database=database)),
                ])
        """
        pass

    @property
    def settings(self):
        """An alias for `self.application.settings <Application.settings>`."""
        return self.application.settings

    def head(self, *args, **kwargs):
        raise HTTPError(405)

    def get(self, *args, **kwargs):
        raise HTTPError(405)

    def post(self, *args, **kwargs):
        raise HTTPError(405)

    def delete(self, *args, **kwargs):
        raise HTTPError(405)

    def patch(self, *args, **kwargs):
        raise HTTPError(405)

    def put(self, *args, **kwargs):
        raise HTTPError(405)

    def options(self, *args, **kwargs):
        raise HTTPError(405)

    def prepare(self):
        """Called at the beginning of a request before  `get`/`post`/etc.

        Override this method to perform common initialization regardless
        of the request method.

        Asynchronous support: Decorate this method with `.gen.coroutine`
        or `.return_future` to make it asynchronous (the
        `asynchronous` decorator cannot be used on `prepare`).
        If this method returns a `.Future` execution will not proceed
        until the `.Future` is done.

        .. versionadded:: 3.1
           Asynchronous support.
        """
        pass

    def on_finish(self):
        """Called after the end of a request.

        Override this method to perform cleanup, logging, etc.
        This method is a counterpart to `prepare`.  ``on_finish`` may
        not produce any output, as it is called after the response
        has been sent to the client.
        """
        pass

    def on_connection_close(self):
        """Called in async handlers if the client closed the connection.

        Override this to clean up resources associated with
        long-lived connections.  Note that this method is called only if
        the connection was closed during asynchronous processing; if you
        need to do cleanup after every request override `on_finish`
        instead.

        Proxies may keep a connection open for a time (perhaps
        indefinitely) after the client has gone away, so this method
        may not be called promptly after the end user closes their
        connection.
        """
        pass

    def clear(self):
        """Resets all headers and content for this response."""
        self._headers = httputil.HTTPHeaders({
            "Server": "TornadoServer/%s" % tornado.version,
            "Content-Type": "text/html; charset=UTF-8",
            "Date": httputil.format_timestamp(time.time()),
        })
        self.set_default_headers()
        if (not self.request.supports_http_1_1() and
            getattr(self.request, 'connection', None) and
                not self.request.connection.no_keep_alive):
            conn_header = self.request.headers.get("Connection")
            if conn_header and (conn_header.lower() == "keep-alive"):
                self.set_header("Connection", "Keep-Alive")
        self._write_buffer = []
        self._status_code = 200
        self._reason = httputil.responses[200]

    def set_default_headers(self):
        """Override this to set HTTP headers at the beginning of the request.

        For example, this is the place to set a custom ``Server`` header.
        Note that setting such headers in the normal flow of request
        processing may not do what you want, since headers may be reset
        during error handling.
        """
        pass

    def set_status(self, status_code, reason=None):
        """Sets the status code for our response.

        :arg int status_code: Response status code. If ``reason`` is ``None``,
            it must be present in `httplib.responses <http.client.responses>`.
        :arg string reason: Human-readable reason phrase describing the status
            code. If ``None``, it will be filled in from
            `httplib.responses <http.client.responses>`.
        """
        self._status_code = status_code
        if reason is not None:
            self._reason = escape.native_str(reason)
        else:
            try:
                self._reason = httputil.responses[status_code]
            except KeyError:
                raise ValueError("unknown status code %d", status_code)

    def get_status(self):
        """Returns the status code for our response."""
        return self._status_code

    def set_header(self, name, value):
        """Sets the given response header name and value.

        If a datetime is given, we automatically format it according to the
        HTTP specification. If the value is not a string, we convert it to
        a string. All header values are then encoded as UTF-8.
        """
        self._headers[name] = self._convert_header_value(value)

    def add_header(self, name, value):
        """Adds the given response header and value.

        Unlike `set_header`, `add_header` may be called multiple times
        to return multiple values for the same header.
        """
        self._headers.add(name, self._convert_header_value(value))

    def clear_header(self, name):
        """Clears an outgoing header, undoing a previous `set_header` call.

        Note that this method does not apply to multi-valued headers
        set by `add_header`.
        """
        if name in self._headers:
            del self._headers[name]

    _INVALID_HEADER_CHAR_RE = re.compile(br"[\x00-\x1f]")

    def _convert_header_value(self, value):
        if isinstance(value, bytes_type):
            pass
        elif isinstance(value, unicode_type):
            value = value.encode('utf-8')
        elif isinstance(value, numbers.Integral):
            # return immediately since we know the converted value will be safe
            return str(value)
        elif isinstance(value, datetime.datetime):
            return httputil.format_timestamp(value)
        else:
            raise TypeError("Unsupported header value %r" % value)
        # If \n is allowed into the header, it is possible to inject
        # additional headers or split the request. Also cap length to
        # prevent obviously erroneous values.
        if (len(value) > 4000 or
                RequestHandler._INVALID_HEADER_CHAR_RE.search(value)):
            raise ValueError("Unsafe header value %r", value)
        return value

    _ARG_DEFAULT = []

    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of the argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we raise a `MissingArgumentError` if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """
        args = self.get_arguments(name, strip=strip)
        if not args:
            if default is self._ARG_DEFAULT:
                raise MissingArgumentError(name)
            return default
        return args[-1]

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """

        values = []
        for v in self.request.arguments.get(name, []):
            v = self.decode_argument(v, name=name)
            if isinstance(v, unicode_type):
                # Get rid of any weird control chars (unless decoding gave
                # us bytes, in which case leave it alone)
                v = RequestHandler._remove_control_chars_regex.sub(" ", v)
            if strip:
                v = v.strip()
            values.append(v)
        return values

    def decode_argument(self, value, name=None):
        """Decodes an argument from the request.

        The argument has been percent-decoded and is now a byte string.
        By default, this method decodes the argument as utf-8 and returns
        a unicode string, but this may be overridden in subclasses.

        This method is used as a filter for both `get_argument()` and for
        values extracted from the url and passed to `get()`/`post()`/etc.

        The name of the argument is provided if known, but may be None
        (e.g. for unnamed groups in the url regex).
        """
        return _unicode(value)

    @property
    def cookies(self):
        """An alias for `self.request.cookies <.httpserver.HTTPRequest.cookies>`."""
        return self.request.cookies

    def get_cookie(self, name, default=None):
        """Gets the value of the cookie with the given name, else default."""
        if self.request.cookies is not None and name in self.request.cookies:
            return self.request.cookies[name].value
        return default

    def set_cookie(self, name, value, domain=None, expires=None, path="/",
                   expires_days=None, **kwargs):
        """Sets the given cookie name/value with the given options.

        Additional keyword arguments are set on the Cookie.Morsel
        directly.
        See http://docs.python.org/library/cookie.html#morsel-objects
        for available attributes.
        """
        # The cookie library only accepts type str, in both python 2 and 3
        name = escape.native_str(name)
        value = escape.native_str(value)
        if re.search(r"[\x00-\x20]", name + value):
            # Don't let us accidentally inject bad stuff
            raise ValueError("Invalid cookie %r: %r" % (name, value))
        if not hasattr(self, "_new_cookie"):
            self._new_cookie = Cookie.SimpleCookie()
        if name in self._new_cookie:
            del self._new_cookie[name]
        self._new_cookie[name] = value
        morsel = self._new_cookie[name]
        if domain:
            morsel["domain"] = domain
        if expires_days is not None and not expires:
            expires = datetime.datetime.utcnow() + datetime.timedelta(
                days=expires_days)
        if expires:
            morsel["expires"] = httputil.format_timestamp(expires)
        if path:
            morsel["path"] = path
        for k, v in kwargs.items():
            if k == 'max_age':
                k = 'max-age'
            morsel[k] = v

    def clear_cookie(self, name, path="/", domain=None):
        """Deletes the cookie with the given name."""
        expires = datetime.datetime.utcnow() - datetime.timedelta(days=365)
        self.set_cookie(name, value="", path=path, expires=expires,
                        domain=domain)

    def clear_all_cookies(self):
        """Deletes all the cookies the user sent with this request."""
        for name in self.request.cookies:
            self.clear_cookie(name)

    def set_secure_cookie(self, name, value, expires_days=30, **kwargs):
        """Signs and timestamps a cookie so it cannot be forged.

        You must specify the ``cookie_secret`` setting in your Application
        to use this method. It should be a long, random sequence of bytes
        to be used as the HMAC secret for the signature.

        To read a cookie set with this method, use `get_secure_cookie()`.

        Note that the ``expires_days`` parameter sets the lifetime of the
        cookie in the browser, but is independent of the ``max_age_days``
        parameter to `get_secure_cookie`.

        Secure cookies may contain arbitrary byte values, not just unicode
        strings (unlike regular cookies)
        """
        self.set_cookie(name, self.create_signed_value(name, value),
                        expires_days=expires_days, **kwargs)

    def create_signed_value(self, name, value):
        """Signs and timestamps a string so it cannot be forged.

        Normally used via set_secure_cookie, but provided as a separate
        method for non-cookie uses.  To decode a value not stored
        as a cookie use the optional value argument to get_secure_cookie.
        """
        self.require_setting("cookie_secret", "secure cookies")
        return create_signed_value(self.application.settings["cookie_secret"],
                                   name, value)

    def get_secure_cookie(self, name, value=None, max_age_days=31):
        """Returns the given signed cookie if it validates, or None.

        The decoded cookie value is returned as a byte string (unlike
        `get_cookie`).
        """
        self.require_setting("cookie_secret", "secure cookies")
        if value is None:
            value = self.get_cookie(name)
        return decode_signed_value(self.application.settings["cookie_secret"],
                                   name, value, max_age_days=max_age_days)

    def redirect(self, url, permanent=False, status=None):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if self._headers_written:
            raise Exception("Cannot redirect after headers have been written")
        if status is None:
            status = 301 if permanent else 302
        else:
            assert isinstance(status, int) and 300 <= status <= 399
        self.set_status(status)
        self.set_header("Location", urlparse.urljoin(utf8(self.request.uri),
                                                     utf8(url)))
        self.finish()

    def write(self, chunk):
        """Writes the given chunk to the output buffer.

        To write the output to the network, use the flush() method below.

        If the given chunk is a dictionary, we write it as JSON and set
        the Content-Type of the response to be ``application/json``.
        (if you want to send JSON as a different ``Content-Type``, call
        set_header *after* calling write()).

        Note that lists are not converted to JSON because of a potential
        cross-site security vulnerability.  All JSON output should be
        wrapped in a dictionary.  More details at
        http://haacked.com/archive/2008/11/20/anatomy-of-a-subtle-json-vulnerability.aspx
        """
        if self._finished:
            raise RuntimeError("Cannot write() after finish().  May be caused "
                               "by using async operations without the "
                               "@asynchronous decorator.")
        if isinstance(chunk, dict):
            chunk = escape.json_encode(chunk)
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        chunk = utf8(chunk)
        self._write_buffer.append(chunk)

    def render(self, template_name, **kwargs):
        """Renders the template with the given arguments as the response."""
        html = self.render_string(template_name, **kwargs)

        # Insert the additional JS and CSS added by the modules on the page
        js_embed = []
        js_files = []
        css_embed = []
        css_files = []
        html_heads = []
        html_bodies = []
        for module in getattr(self, "_active_modules", {}).values():
            embed_part = module.embedded_javascript()
            if embed_part:
                js_embed.append(utf8(embed_part))
            file_part = module.javascript_files()
            if file_part:
                if isinstance(file_part, (unicode_type, bytes_type)):
                    js_files.append(file_part)
                else:
                    js_files.extend(file_part)
            embed_part = module.embedded_css()
            if embed_part:
                css_embed.append(utf8(embed_part))
            file_part = module.css_files()
            if file_part:
                if isinstance(file_part, (unicode_type, bytes_type)):
                    css_files.append(file_part)
                else:
                    css_files.extend(file_part)
            head_part = module.html_head()
            if head_part:
                html_heads.append(utf8(head_part))
            body_part = module.html_body()
            if body_part:
                html_bodies.append(utf8(body_part))

        def is_absolute(path):
            return any(path.startswith(x) for x in ["/", "http:", "https:"])
        if js_files:
            # Maintain order of JavaScript files given by modules
            paths = []
            unique_paths = set()
            for path in js_files:
                if not is_absolute(path):
                    path = self.static_url(path)
                if path not in unique_paths:
                    paths.append(path)
                    unique_paths.add(path)
            js = ''.join('<script src="' + escape.xhtml_escape(p) +
                         '" type="text/javascript"></script>'
                         for p in paths)
            sloc = html.rindex(b'</body>')
            html = html[:sloc] + utf8(js) + b'\n' + html[sloc:]
        if js_embed:
            js = b'<script type="text/javascript">\n//<![CDATA[\n' + \
                b'\n'.join(js_embed) + b'\n//]]>\n</script>'
            sloc = html.rindex(b'</body>')
            html = html[:sloc] + js + b'\n' + html[sloc:]
        if css_files:
            paths = []
            unique_paths = set()
            for path in css_files:
                if not is_absolute(path):
                    path = self.static_url(path)
                if path not in unique_paths:
                    paths.append(path)
                    unique_paths.add(path)
            css = ''.join('<link href="' + escape.xhtml_escape(p) + '" '
                          'type="text/css" rel="stylesheet"/>'
                          for p in paths)
            hloc = html.index(b'</head>')
            html = html[:hloc] + utf8(css) + b'\n' + html[hloc:]
        if css_embed:
            css = b'<style type="text/css">\n' + b'\n'.join(css_embed) + \
                b'\n</style>'
            hloc = html.index(b'</head>')
            html = html[:hloc] + css + b'\n' + html[hloc:]
        if html_heads:
            hloc = html.index(b'</head>')
            html = html[:hloc] + b''.join(html_heads) + b'\n' + html[hloc:]
        if html_bodies:
            hloc = html.index(b'</body>')
            html = html[:hloc] + b''.join(html_bodies) + b'\n' + html[hloc:]
        self.finish(html)

    def render_string(self, template_name, **kwargs):
        """Generate the given template with the given arguments.

        We return the generated byte string (in utf8). To generate and
        write a template as a response, use render() above.
        """
        # If no template_path is specified, use the path of the calling file
        template_path = self.get_template_path()
        if not template_path:
            frame = sys._getframe(0)
            web_file = frame.f_code.co_filename
            while frame.f_code.co_filename == web_file:
                frame = frame.f_back
            template_path = os.path.dirname(frame.f_code.co_filename)
        with RequestHandler._template_loader_lock:
            if template_path not in RequestHandler._template_loaders:
                loader = self.create_template_loader(template_path)
                RequestHandler._template_loaders[template_path] = loader
            else:
                loader = RequestHandler._template_loaders[template_path]
        t = loader.load(template_name)
        namespace = self.get_template_namespace()
        namespace.update(kwargs)
        return t.generate(**namespace)

    def get_template_namespace(self):
        """Returns a dictionary to be used as the default template namespace.

        May be overridden by subclasses to add or modify values.

        The results of this method will be combined with additional
        defaults in the `tornado.template` module and keyword arguments
        to `render` or `render_string`.
        """
        namespace = dict(
            handler=self,
            request=self.request,
            current_user=self.current_user,
            locale=self.locale,
            _=self.locale.translate,
            static_url=self.static_url,
            xsrf_form_html=self.xsrf_form_html,
            reverse_url=self.reverse_url
        )
        namespace.update(self.ui)
        return namespace

    def create_template_loader(self, template_path):
        """Returns a new template loader for the given path.

        May be overridden by subclasses.  By default returns a
        directory-based loader on the given path, using the
        ``autoescape`` application setting.  If a ``template_loader``
        application setting is supplied, uses that instead.
        """
        settings = self.application.settings
        if "template_loader" in settings:
            return settings["template_loader"]
        kwargs = {}
        if "autoescape" in settings:
            # autoescape=None means "no escaping", so we have to be sure
            # to only pass this kwarg if the user asked for it.
            kwargs["autoescape"] = settings["autoescape"]
        return template.Loader(template_path, **kwargs)

    def flush(self, include_footers=False, callback=None):
        """Flushes the current output buffer to the network.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """
        if self.application._wsgi:
            # WSGI applications cannot usefully support flush, so just make
            # it a no-op (and run the callback immediately).
            if callback is not None:
                callback()
            return

        chunk = b"".join(self._write_buffer)
        self._write_buffer = []
        if not self._headers_written:
            self._headers_written = True
            for transform in self._transforms:
                self._status_code, self._headers, chunk = \
                    transform.transform_first_chunk(
                        self._status_code, self._headers, chunk, include_footers)
            headers = self._generate_headers()
        else:
            for transform in self._transforms:
                chunk = transform.transform_chunk(chunk, include_footers)
            headers = b""

        # Ignore the chunk and only write the headers for HEAD requests
        if self.request.method == "HEAD":
            if headers:
                self.request.write(headers, callback=callback)
            return

        self.request.write(headers + chunk, callback=callback)

    def finish(self, chunk=None):
        """Finishes this response, ending the HTTP request."""
        if self._finished:
            raise RuntimeError("finish() called twice.  May be caused "
                               "by using async operations without the "
                               "@asynchronous decorator.")

        if chunk is not None:
            self.write(chunk)

        # Automatically support ETags and add the Content-Length header if
        # we have not flushed any content yet.
        if not self._headers_written:
            if (self._status_code == 200 and
                self.request.method in ("GET", "HEAD") and
                    "Etag" not in self._headers):
                self.set_etag_header()
                if self.check_etag_header():
                    self._write_buffer = []
                    self.set_status(304)
            if self._status_code == 304:
                assert not self._write_buffer, "Cannot send body with 304"
                self._clear_headers_for_304()
            elif "Content-Length" not in self._headers:
                content_length = sum(len(part) for part in self._write_buffer)
                self.set_header("Content-Length", content_length)

        if hasattr(self.request, "connection"):
            # Now that the request is finished, clear the callback we
            # set on the IOStream (which would otherwise prevent the
            # garbage collection of the RequestHandler when there
            # are keepalive connections)
            self.request.connection.stream.set_close_callback(None)

        if not self.application._wsgi:
            self.flush(include_footers=True)
            self.request.finish()
            self._log()
        self._finished = True
        self.on_finish()
        # Break up a reference cycle between this handler and the
        # _ui_module closures to allow for faster GC on CPython.
        self.ui = None

    def send_error(self, status_code=500, **kwargs):
        """Sends the given HTTP error code to the browser.

        If `flush()` has already been called, it is not possible to send
        an error, so this method will simply terminate the response.
        If output has been written but not yet flushed, it will be discarded
        and replaced with the error page.

        Override `write_error()` to customize the error page that is returned.
        Additional keyword arguments are passed through to `write_error`.
        """
        if self._headers_written:
            gen_log.error("Cannot send error response after headers written")
            if not self._finished:
                self.finish()
            return
        self.clear()

        reason = None
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            if isinstance(exception, HTTPError) and exception.reason:
                reason = exception.reason
        self.set_status(status_code, reason=reason)
        try:
            self.write_error(status_code, **kwargs)
        except Exception:
            app_log.error("Uncaught exception in write_error", exc_info=True)
        if not self._finished:
            self.finish()

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception (including
        HTTPError), an ``exc_info`` triple will be available as
        ``kwargs["exc_info"]``.  Note that this exception may not be
        the "current" exception for purposes of methods like
        ``sys.exc_info()`` or ``traceback.format_exc``.

        For historical reasons, if a method ``get_error_html`` exists,
        it will be used instead of the default ``write_error`` implementation.
        ``get_error_html`` returned a string instead of producing output
        normally, and had different semantics for exception handling.
        Users of ``get_error_html`` are encouraged to convert their code
        to override ``write_error`` instead.
        """
        if hasattr(self, 'get_error_html'):
            if 'exc_info' in kwargs:
                exc_info = kwargs.pop('exc_info')
                kwargs['exception'] = exc_info[1]
                try:
                    # Put the traceback into sys.exc_info()
                    raise_exc_info(exc_info)
                except Exception:
                    self.finish(self.get_error_html(status_code, **kwargs))
            else:
                self.finish(self.get_error_html(status_code, **kwargs))
            return
        if self.settings.get("debug") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                            "code": status_code,
                            "message": self._reason,
                        })

    @property
    def locale(self):
        """The local for the current session.

        Determined by either `get_user_locale`, which you can override to
        set the locale based on, e.g., a user preference stored in a
        database, or `get_browser_locale`, which uses the ``Accept-Language``
        header.
        """
        if not hasattr(self, "_locale"):
            self._locale = self.get_user_locale()
            if not self._locale:
                self._locale = self.get_browser_locale()
                assert self._locale
        return self._locale

    def get_user_locale(self):
        """Override to determine the locale from the authenticated user.

        If None is returned, we fall back to `get_browser_locale()`.

        This method should return a `tornado.locale.Locale` object,
        most likely obtained via a call like ``tornado.locale.get("en")``
        """
        return None

    def get_browser_locale(self, default="en_US"):
        """Determines the user's locale from ``Accept-Language`` header.

        See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.4
        """
        if "Accept-Language" in self.request.headers:
            languages = self.request.headers["Accept-Language"].split(",")
            locales = []
            for language in languages:
                parts = language.strip().split(";")
                if len(parts) > 1 and parts[1].startswith("q="):
                    try:
                        score = float(parts[1][2:])
                    except (ValueError, TypeError):
                        score = 0.0
                else:
                    score = 1.0
                locales.append((parts[0], score))
            if locales:
                locales.sort(key=lambda pair: pair[1], reverse=True)
                codes = [l[0] for l in locales]
                return locale.get(*codes)
        return locale.get(default)

    @property
    def current_user(self):
        """The authenticated user for this request.

        This is a cached version of `get_current_user`, which you can
        override to set the user based on, e.g., a cookie. If that
        method is not overridden, this method always returns None.

        We lazy-load the current user the first time this method is called
        and cache the result after that.
        """
        if not hasattr(self, "_current_user"):
            self._current_user = self.get_current_user()
        return self._current_user

    @current_user.setter
    def current_user(self, value):
        self._current_user = value

    def get_current_user(self):
        """Override to determine the current user from, e.g., a cookie."""
        return None

    def get_login_url(self):
        """Override to customize the login URL based on the request.

        By default, we use the ``login_url`` application setting.
        """
        self.require_setting("login_url", "@tornado.web.authenticated")
        return self.application.settings["login_url"]

    def get_template_path(self):
        """Override to customize template path for each handler.

        By default, we use the ``template_path`` application setting.
        Return None to load templates relative to the calling file.
        """
        return self.application.settings.get("template_path")

    @property
    def xsrf_token(self):
        """The XSRF-prevention token for the current user/session.

        To prevent cross-site request forgery, we set an '_xsrf' cookie
        and include the same '_xsrf' value as an argument with all POST
        requests. If the two do not match, we reject the form submission
        as a potential forgery.

        See http://en.wikipedia.org/wiki/Cross-site_request_forgery
        """
        if not hasattr(self, "_xsrf_token"):
            token = self.get_cookie("_xsrf")
            if not token:
                token = binascii.b2a_hex(uuid.uuid4().bytes)
                expires_days = 30 if self.current_user else None
                self.set_cookie("_xsrf", token, expires_days=expires_days)
            self._xsrf_token = token
        return self._xsrf_token

    def check_xsrf_cookie(self):
        """Verifies that the ``_xsrf`` cookie matches the ``_xsrf`` argument.

        To prevent cross-site request forgery, we set an ``_xsrf``
        cookie and include the same value as a non-cookie
        field with all ``POST`` requests. If the two do not match, we
        reject the form submission as a potential forgery.

        The ``_xsrf`` value may be set as either a form field named ``_xsrf``
        or in a custom HTTP header named ``X-XSRFToken`` or ``X-CSRFToken``
        (the latter is accepted for compatibility with Django).

        See http://en.wikipedia.org/wiki/Cross-site_request_forgery

        Prior to release 1.1.1, this check was ignored if the HTTP header
        ``X-Requested-With: XMLHTTPRequest`` was present.  This exception
        has been shown to be insecure and has been removed.  For more
        information please see
        http://www.djangoproject.com/weblog/2011/feb/08/security/
        http://weblog.rubyonrails.org/2011/2/8/csrf-protection-bypass-in-ruby-on-rails
        """
        token = (self.get_argument("_xsrf", None) or
                 self.request.headers.get("X-Xsrftoken") or
                 self.request.headers.get("X-Csrftoken"))
        if not token:
            raise HTTPError(403, "'_xsrf' argument missing from POST")
        if self.xsrf_token != token:
            raise HTTPError(403, "XSRF cookie does not match POST argument")

    def xsrf_form_html(self):
        """An HTML ``<input/>`` element to be included with all POST forms.

        It defines the ``_xsrf`` input value, which we check on all POST
        requests to prevent cross-site request forgery. If you have set
        the ``xsrf_cookies`` application setting, you must include this
        HTML within all of your HTML forms.

        In a template, this method should be called with ``{% module
        xsrf_form_html() %}``

        See `check_xsrf_cookie()` above for more information.
        """
        return '<input type="hidden" name="_xsrf" value="' + \
            escape.xhtml_escape(self.xsrf_token) + '"/>'

    def static_url(self, path, include_host=None, **kwargs):
        """Returns a static URL for the given relative static file path.

        This method requires you set the ``static_path`` setting in your
        application (which specifies the root directory of your static
        files).

        This method returns a versioned url (by default appending
        ``?v=<signature>``), which allows the static files to be
        cached indefinitely.  This can be disabled by passing
        ``include_version=False`` (in the default implementation;
        other static file implementations are not required to support
        this, but they may support other options).

        By default this method returns URLs relative to the current
        host, but if ``include_host`` is true the URL returned will be
        absolute.  If this handler has an ``include_host`` attribute,
        that value will be used as the default for all `static_url`
        calls that do not pass ``include_host`` as a keyword argument.

        """
        self.require_setting("static_path", "static_url")
        get_url = self.settings.get("static_handler_class",
                                    StaticFileHandler).make_static_url

        if include_host is None:
            include_host = getattr(self, "include_host", False)

        if include_host:
            base = self.request.protocol + "://" + self.request.host
        else:
            base = ""

        return base + get_url(self.settings, path, **kwargs)

    def async_callback(self, callback, *args, **kwargs):
        """Obsolete - catches exceptions from the wrapped function.

        This function is unnecessary since Tornado 1.1.
        """
        if callback is None:
            return None
        if args or kwargs:
            callback = functools.partial(callback, *args, **kwargs)

        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception as e:
                if self._headers_written:
                    app_log.error("Exception after headers written",
                                  exc_info=True)
                else:
                    self._handle_request_exception(e)
        return wrapper

    def require_setting(self, name, feature="this feature"):
        """Raises an exception if the given app setting is not defined."""
        if not self.application.settings.get(name):
            raise Exception("You must define the '%s' setting in your "
                            "application to use %s" % (name, feature))

    def reverse_url(self, name, *args):
        """Alias for `Application.reverse_url`."""
        return self.application.reverse_url(name, *args)

    def compute_etag(self):
        """Computes the etag header to be used for this request.

        By default uses a hash of the content written so far.

        May be overridden to provide custom etag implementations,
        or may return None to disable tornado's default etag support.
        """
        hasher = hashlib.sha1()
        for part in self._write_buffer:
            hasher.update(part)
        return '"%s"' % hasher.hexdigest()

    def set_etag_header(self):
        """Sets the response's Etag header using ``self.compute_etag()``.

        Note: no header will be set if ``compute_etag()`` returns ``None``.

        This method is called automatically when the request is finished.
        """
        etag = self.compute_etag()
        if etag is not None:
            self.set_header("Etag", etag)

    def check_etag_header(self):
        """Checks the ``Etag`` header against requests's ``If-None-Match``.

        Returns ``True`` if the request's Etag matches and a 304 should be
        returned. For example::

            self.set_etag_header()
            if self.check_etag_header():
                self.set_status(304)
                return

        This method is called automatically when the request is finished,
        but may be called earlier for applications that override
        `compute_etag` and want to do an early check for ``If-None-Match``
        before completing the request.  The ``Etag`` header should be set
        (perhaps with `set_etag_header`) before calling this method.
        """
        etag = self._headers.get("Etag")
        inm = utf8(self.request.headers.get("If-None-Match", ""))
        return bool(etag and inm and inm.find(etag) >= 0)

    def _stack_context_handle_exception(self, type, value, traceback):
        try:
            # For historical reasons _handle_request_exception only takes
            # the exception value instead of the full triple,
            # so re-raise the exception to ensure that it's in
            # sys.exc_info()
            raise_exc_info((type, value, traceback))
        except Exception:
            self._handle_request_exception(value)
        return True

    def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        self._transforms = transforms
        try:
            if self.request.method not in self.SUPPORTED_METHODS:
                raise HTTPError(405)
            self.path_args = [self.decode_argument(arg) for arg in args]
            self.path_kwargs = dict((k, self.decode_argument(v, name=k))
                                    for (k, v) in kwargs.items())
            # If XSRF cookies are turned on, reject form submissions without
            # the proper cookie
            if self.request.method not in ("GET", "HEAD", "OPTIONS") and \
                    self.application.settings.get("xsrf_cookies"):
                self.check_xsrf_cookie()
            self._when_complete(self.prepare(), self._execute_method)
        except Exception as e:
            self._handle_request_exception(e)

    def _when_complete(self, result, callback):
        try:
            if result is None:
                callback()
            elif isinstance(result, Future):
                if result.done():
                    if result.result() is not None:
                        raise ValueError('Expected None, got %r' % result)
                    callback()
                else:
                    # Delayed import of IOLoop because it's not available
                    # on app engine
                    from tornado.ioloop import IOLoop
                    IOLoop.current().add_future(
                        result, functools.partial(self._when_complete,
                                                  callback=callback))
            else:
                raise ValueError("Expected Future or None, got %r" % result)
        except Exception as e:
            self._handle_request_exception(e)

    def _execute_method(self):
        if not self._finished:
            method = getattr(self, self.request.method.lower())
            self._when_complete(method(*self.path_args, **self.path_kwargs),
                                self._execute_finish)

    def _execute_finish(self):
        if self._auto_finish and not self._finished:
            self.finish()

    def _generate_headers(self):
        reason = self._reason
        lines = [utf8(self.request.version + " " +
                      str(self._status_code) +
                      " " + reason)]
        lines.extend([utf8(n) + b": " + utf8(v) for n, v in self._headers.get_all()])

        if hasattr(self, "_new_cookie"):
            for cookie in self._new_cookie.values():
                lines.append(utf8("Set-Cookie: " + cookie.OutputString(None)))
        return b"\r\n".join(lines) + b"\r\n\r\n"

    def _log(self):
        """Logs the current request.

        Sort of deprecated since this functionality was moved to the
        Application, but left in place for the benefit of existing apps
        that have overridden this method.
        """
        self.application.log_request(self)

    def _request_summary(self):
        return self.request.method + " " + self.request.uri + \
            " (" + self.request.remote_ip + ")"

    def _handle_request_exception(self, e):
        self.log_exception(*sys.exc_info())
        if self._finished:
            # Extra errors after the request has been finished should
            # be logged, but there is no reason to continue to try and
            # send a response.
            return
        if isinstance(e, HTTPError):
            if e.status_code not in httputil.responses and not e.reason:
                gen_log.error("Bad HTTP status code: %d", e.status_code)
                self.send_error(500, exc_info=sys.exc_info())
            else:
                self.send_error(e.status_code, exc_info=sys.exc_info())
        else:
            self.send_error(500, exc_info=sys.exc_info())

    def log_exception(self, typ, value, tb):
        """Override to customize logging of uncaught exceptions.

        By default logs instances of `HTTPError` as warnings without
        stack traces (on the ``tornado.general`` logger), and all
        other exceptions as errors with stack traces (on the
        ``tornado.application`` logger).

        .. versionadded:: 3.1
        """
        if isinstance(value, HTTPError):
            if value.log_message:
                format = "%d %s: " + value.log_message
                args = ([value.status_code, self._request_summary()] +
                        list(value.args))
                gen_log.warning(format, *args)
        else:
            app_log.error("Uncaught exception %s\n%r", self._request_summary(),
                          self.request, exc_info=(typ, value, tb))

    def _ui_module(self, name, module):
        def render(*args, **kwargs):
            if not hasattr(self, "_active_modules"):
                self._active_modules = {}
            if name not in self._active_modules:
                self._active_modules[name] = module(self)
            rendered = self._active_modules[name].render(*args, **kwargs)
            return rendered
        return render

    def _ui_method(self, method):
        return lambda *args, **kwargs: method(self, *args, **kwargs)

    def _clear_headers_for_304(self):
        # 304 responses should not contain entity headers (defined in
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec7.html#sec7.1)
        # not explicitly allowed by
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.3.5
        headers = ["Allow", "Content-Encoding", "Content-Language",
                   "Content-Length", "Content-MD5", "Content-Range",
                   "Content-Type", "Last-Modified"]
        for h in headers:
            self.clear_header(h)


def asynchronous(method):
    """Wrap request handler methods with this if they are asynchronous.

    This decorator is unnecessary if the method is also decorated with
    ``@gen.coroutine`` (it is legal but unnecessary to use the two
    decorators together, in which case ``@asynchronous`` must be
    first).

    This decorator should only be applied to the :ref:`HTTP verb
    methods <verbs>`; its behavior is undefined for any other method.
    This decorator does not *make* a method asynchronous; it tells
    the framework that the method *is* asynchronous.  For this decorator
    to be useful the method must (at least sometimes) do something
    asynchronous.

    If this decorator is given, the response is not finished when the
    method returns. It is up to the request handler to call
    `self.finish() <RequestHandler.finish>` to finish the HTTP
    request. Without this decorator, the request is automatically
    finished when the ``get()`` or ``post()`` method returns. Example::

       class MyRequestHandler(web.RequestHandler):
           @web.asynchronous
           def get(self):
              http = httpclient.AsyncHTTPClient()
              http.fetch("http://friendfeed.com/", self._on_download)

           def _on_download(self, response):
              self.write("Downloaded!")
              self.finish()

    .. versionadded:: 3.1
       The ability to use ``@gen.coroutine`` without ``@asynchronous``.
    """
    # Delay the IOLoop import because it's not available on app engine.
    from tornado.ioloop import IOLoop
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.application._wsgi:
            raise Exception("@asynchronous is not supported for WSGI apps")
        self._auto_finish = False
        with stack_context.ExceptionStackContext(
                self._stack_context_handle_exception):
            result = method(self, *args, **kwargs)
            if isinstance(result, Future):
                # If @asynchronous is used with @gen.coroutine, (but
                # not @gen.engine), we can automatically finish the
                # request when the future resolves.  Additionally,
                # the Future will swallow any exceptions so we need
                # to throw them back out to the stack context to finish
                # the request.
                def future_complete(f):
                    f.result()
                    if not self._finished:
                        self.finish()
                IOLoop.current().add_future(result, future_complete)
            return result
    return wrapper


def removeslash(method):
    """Use this decorator to remove trailing slashes from the request path.

    For example, a request to ``/foo/`` would redirect to ``/foo`` with this
    decorator. Your request handler mapping should use a regular expression
    like ``r'/foo/*'`` in conjunction with using the decorator.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.request.path.endswith("/"):
            if self.request.method in ("GET", "HEAD"):
                uri = self.request.path.rstrip("/")
                if uri:  # don't try to redirect '/' to ''
                    if self.request.query:
                        uri += "?" + self.request.query
                    self.redirect(uri, permanent=True)
                    return
            else:
                raise HTTPError(404)
        return method(self, *args, **kwargs)
    return wrapper


def addslash(method):
    """Use this decorator to add a missing trailing slash to the request path.

    For example, a request to ``/foo`` would redirect to ``/foo/`` with this
    decorator. Your request handler mapping should use a regular expression
    like ``r'/foo/?'`` in conjunction with using the decorator.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.request.path.endswith("/"):
            if self.request.method in ("GET", "HEAD"):
                uri = self.request.path + "/"
                if self.request.query:
                    uri += "?" + self.request.query
                self.redirect(uri, permanent=True)
                return
            raise HTTPError(404)
        return method(self, *args, **kwargs)
    return wrapper


class Application(object):
    """A collection of request handlers that make up a web application.

    Instances of this class are callable and can be passed directly to
    HTTPServer to serve the application::

        application = web.Application([
            (r"/", MainPageHandler),
        ])
        http_server = httpserver.HTTPServer(application)
        http_server.listen(8080)
        ioloop.IOLoop.instance().start()

    The constructor for this class takes in a list of `URLSpec` objects
    or (regexp, request_class) tuples. When we receive requests, we
    iterate over the list in order and instantiate an instance of the
    first request class whose regexp matches the request path.

    Each tuple can contain an optional third element, which should be
    a dictionary if it is present. That dictionary is passed as
    keyword arguments to the contructor of the handler. This pattern
    is used for the `StaticFileHandler` in this example (note that a
    `StaticFileHandler` can be installed automatically with the
    static_path setting described below)::

        application = web.Application([
            (r"/static/(.*)", web.StaticFileHandler, {"path": "/var/www"}),
        ])

    We support virtual hosts with the `add_handlers` method, which takes in
    a host regular expression as the first argument::

        application.add_handlers(r"www\.myhost\.com", [
            (r"/article/([0-9]+)", ArticleHandler),
        ])

    You can serve static files by sending the ``static_path`` setting
    as a keyword argument. We will serve those files from the
    ``/static/`` URI (this is configurable with the
    ``static_url_prefix`` setting), and we will serve ``/favicon.ico``
    and ``/robots.txt`` from the same directory.  A custom subclass of
    `StaticFileHandler` can be specified with the
    ``static_handler_class`` setting.
    """
    def __init__(self, handlers=None, default_host="", transforms=None,
                 wsgi=False, **settings):
        if transforms is None:
            self.transforms = []
            if settings.get("gzip"):
                self.transforms.append(GZipContentEncoding)
            self.transforms.append(ChunkedTransferEncoding)
        else:
            self.transforms = transforms
        self.handlers = []
        self.named_handlers = {}
        self.default_host = default_host
        self.settings = settings
        self.ui_modules = {'linkify': _linkify,
                           'xsrf_form_html': _xsrf_form_html,
                           'Template': TemplateModule,
                           }
        self.ui_methods = {}
        self._wsgi = wsgi
        self._load_ui_modules(settings.get("ui_modules", {}))
        self._load_ui_methods(settings.get("ui_methods", {}))
        if self.settings.get("static_path"):
            path = self.settings["static_path"]
            handlers = list(handlers or [])
            static_url_prefix = settings.get("static_url_prefix",
                                             "/static/")
            static_handler_class = settings.get("static_handler_class",
                                                StaticFileHandler)
            static_handler_args = settings.get("static_handler_args", {})
            static_handler_args['path'] = path
            for pattern in [re.escape(static_url_prefix) + r"(.*)",
                            r"/(favicon\.ico)", r"/(robots\.txt)"]:
                handlers.insert(0, (pattern, static_handler_class,
                                    static_handler_args))
        if handlers:
            self.add_handlers(".*$", handlers)

        # Automatically reload modified modules
        if self.settings.get("debug") and not wsgi:
            from tornado import autoreload
            autoreload.start()

    def listen(self, port, address="", **kwargs):
        """Starts an HTTP server for this application on the given port.

        This is a convenience alias for creating an `.HTTPServer`
        object and calling its listen method.  Keyword arguments not
        supported by `HTTPServer.listen <.TCPServer.listen>` are passed to the
        `.HTTPServer` constructor.  For advanced uses
        (e.g. multi-process mode), do not use this method; create an
        `.HTTPServer` and call its
        `.TCPServer.bind`/`.TCPServer.start` methods directly.

        Note that after calling this method you still need to call
        ``IOLoop.instance().start()`` to start the server.
        """
        # import is here rather than top level because HTTPServer
        # is not importable on appengine
        from tornado.httpserver import HTTPServer
        server = HTTPServer(self, **kwargs)
        server.listen(port, address)

    def add_handlers(self, host_pattern, host_handlers):
        """Appends the given handlers to our handler list.

        Host patterns are processed sequentially in the order they were
        added. All matching patterns will be considered.
        """
        if not host_pattern.endswith("$"):
            host_pattern += "$"
        handlers = []
        # The handlers with the wildcard host_pattern are a special
        # case - they're added in the constructor but should have lower
        # precedence than the more-precise handlers added later.
        # If a wildcard handler group exists, it should always be last
        # in the list, so insert new groups just before it.
        if self.handlers and self.handlers[-1][0].pattern == '.*$':
            self.handlers.insert(-1, (re.compile(host_pattern), handlers))
        else:
            self.handlers.append((re.compile(host_pattern), handlers))

        for spec in host_handlers:
            if isinstance(spec, (tuple, list)):
                assert len(spec) in (2, 3)
                pattern = spec[0]
                handler = spec[1]

                if isinstance(handler, str):
                    # import the Module and instantiate the class
                    # Must be a fully qualified name (module.ClassName)
                    handler = import_object(handler)

                if len(spec) == 3:
                    kwargs = spec[2]
                else:
                    kwargs = {}
                spec = URLSpec(pattern, handler, kwargs)
            handlers.append(spec)
            if spec.name:
                if spec.name in self.named_handlers:
                    app_log.warning(
                        "Multiple handlers named %s; replacing previous value",
                        spec.name)
                self.named_handlers[spec.name] = spec

    def add_transform(self, transform_class):
        self.transforms.append(transform_class)

    def _get_host_handlers(self, request):
        host = request.host.lower().split(':')[0]
        matches = []
        for pattern, handlers in self.handlers:
            if pattern.match(host):
                matches.extend(handlers)
        # Look for default host if not behind load balancer (for debugging)
        if not matches and "X-Real-Ip" not in request.headers:
            for pattern, handlers in self.handlers:
                if pattern.match(self.default_host):
                    matches.extend(handlers)
        return matches or None

    def _load_ui_methods(self, methods):
        if isinstance(methods, types.ModuleType):
            self._load_ui_methods(dict((n, getattr(methods, n))
                                       for n in dir(methods)))
        elif isinstance(methods, list):
            for m in methods:
                self._load_ui_methods(m)
        else:
            for name, fn in methods.items():
                if not name.startswith("_") and hasattr(fn, "__call__") \
                        and name[0].lower() == name[0]:
                    self.ui_methods[name] = fn

    def _load_ui_modules(self, modules):
        if isinstance(modules, types.ModuleType):
            self._load_ui_modules(dict((n, getattr(modules, n))
                                       for n in dir(modules)))
        elif isinstance(modules, list):
            for m in modules:
                self._load_ui_modules(m)
        else:
            assert isinstance(modules, dict)
            for name, cls in modules.items():
                try:
                    if issubclass(cls, UIModule):
                        self.ui_modules[name] = cls
                except TypeError:
                    pass

    def __call__(self, request):
        """Called by HTTPServer to execute the request."""
        transforms = [t(request) for t in self.transforms]
        handler = None
        args = []
        kwargs = {}
        handlers = self._get_host_handlers(request)
        if not handlers:
            handler = RedirectHandler(
                self, request, url="http://" + self.default_host + "/")
        else:
            for spec in handlers:
                match = spec.regex.match(request.path)
                if match:
                    handler = spec.handler_class(self, request, **spec.kwargs)
                    if spec.regex.groups:
                        # None-safe wrapper around url_unescape to handle
                        # unmatched optional groups correctly
                        def unquote(s):
                            if s is None:
                                return s
                            return escape.url_unescape(s, encoding=None,
                                                       plus=False)
                        # Pass matched groups to the handler.  Since
                        # match.groups() includes both named and unnamed groups,
                        # we want to use either groups or groupdict but not both.
                        # Note that args are passed as bytes so the handler can
                        # decide what encoding to use.

                        if spec.regex.groupindex:
                            kwargs = dict(
                                (str(k), unquote(v))
                                for (k, v) in match.groupdict().items())
                        else:
                            args = [unquote(s) for s in match.groups()]
                    break
            if not handler:
                handler = ErrorHandler(self, request, status_code=404)

        # In debug mode, re-compile templates and reload static files on every
        # request so you don't need to restart to see changes
        if self.settings.get("debug"):
            with RequestHandler._template_loader_lock:
                for loader in RequestHandler._template_loaders.values():
                    loader.reset()
            StaticFileHandler.reset()

        handler._execute(transforms, *args, **kwargs)
        return handler

    def reverse_url(self, name, *args):
        """Returns a URL path for handler named ``name``

        The handler must be added to the application as a named `URLSpec`.

        Args will be substituted for capturing groups in the `URLSpec` regex.
        They will be converted to strings if necessary, encoded as utf8,
        and url-escaped.
        """
        if name in self.named_handlers:
            return self.named_handlers[name].reverse(*args)
        raise KeyError("%s not found in named urls" % name)

    def log_request(self, handler):
        """Writes a completed HTTP request to the logs.

        By default writes to the python root logger.  To change
        this behavior either subclass Application and override this method,
        or pass a function in the application settings dictionary as
        ``log_function``.
        """
        if "log_function" in self.settings:
            self.settings["log_function"](handler)
            return
        if handler.get_status() < 400:
            log_method = access_log.info
        elif handler.get_status() < 500:
            log_method = access_log.warning
        else:
            log_method = access_log.error
        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(),
                   handler._request_summary(), request_time)


class HTTPError(Exception):
    """An exception that will turn into an HTTP error response.

    Raising an `HTTPError` is a convenient alternative to calling
    `RequestHandler.send_error` since it automatically ends the
    current function.

    :arg int status_code: HTTP status code.  Must be listed in
        `httplib.responses <http.client.responses>` unless the ``reason``
        keyword argument is given.
    :arg string log_message: Message to be written to the log for this error
        (will not be shown to the user unless the `Application` is in debug
        mode).  May contain ``%s``-style placeholders, which will be filled
        in with remaining positional parameters.
    :arg string reason: Keyword-only argument.  The HTTP "reason" phrase
        to pass in the status line along with ``status_code``.  Normally
        determined automatically from ``status_code``, but can be used
        to use a non-standard numeric code.
    """
    def __init__(self, status_code, log_message=None, *args, **kwargs):
        self.status_code = status_code
        self.log_message = log_message
        self.args = args
        self.reason = kwargs.get('reason', None)

    def __str__(self):
        message = "HTTP %d: %s" % (
            self.status_code,
            self.reason or httputil.responses.get(self.status_code, 'Unknown'))
        if self.log_message:
            return message + " (" + (self.log_message % self.args) + ")"
        else:
            return message


class MissingArgumentError(HTTPError):
    """Exception raised by `RequestHandler.get_argument`.

    This is a subclass of `HTTPError`, so if it is uncaught a 400 response
    code will be used instead of 500 (and a stack trace will not be logged).

    .. versionadded:: 3.1
    """
    def __init__(self, arg_name):
        super(MissingArgumentError, self).__init__(
            400, 'Missing argument %s' % arg_name)
        self.arg_name = arg_name


class ErrorHandler(RequestHandler):
    """Generates an error response with ``status_code`` for all requests."""
    def initialize(self, status_code):
        self.set_status(status_code)

    def prepare(self):
        raise HTTPError(self._status_code)

    def check_xsrf_cookie(self):
        # POSTs to an ErrorHandler don't actually have side effects,
        # so we don't need to check the xsrf token.  This allows POSTs
        # to the wrong url to return a 404 instead of 403.
        pass


class RedirectHandler(RequestHandler):
    """Redirects the client to the given URL for all GET requests.

    You should provide the keyword argument ``url`` to the handler, e.g.::

        application = web.Application([
            (r"/oldpath", web.RedirectHandler, {"url": "/newpath"}),
        ])
    """
    def initialize(self, url, permanent=True):
        self._url = url
        self._permanent = permanent

    def get(self):
        self.redirect(self._url, permanent=self._permanent)


class StaticFileHandler(RequestHandler):
    """A simple handler that can serve static content from a directory.

    A `StaticFileHandler` is configured automatically if you pass the
    ``static_path`` keyword argument to `Application`.  This handler
    can be customized with the ``static_url_prefix``, ``static_handler_class``,
    and ``static_handler_args`` settings.

    To map an additional path to this handler for a static data directory
    you would add a line to your application like::

        application = web.Application([
            (r"/content/(.*)", web.StaticFileHandler, {"path": "/var/www"}),
        ])

    The handler constructor requires a ``path`` argument, which specifies the
    local root directory of the content to be served.

    Note that a capture group in the regex is required to parse the value for
    the ``path`` argument to the get() method (different than the constructor
    argument above); see `URLSpec` for details.

    To maximize the effectiveness of browser caching, this class supports
    versioned urls (by default using the argument ``?v=``).  If a version
    is given, we instruct the browser to cache this file indefinitely.
    `make_static_url` (also available as `RequestHandler.static_url`) can
    be used to construct a versioned url.

    This handler is intended primarily for use in development and light-duty
    file serving; for heavy traffic it will be more efficient to use
    a dedicated static file server (such as nginx or Apache).  We support
    the HTTP ``Accept-Ranges`` mechanism to return partial content (because
    some browsers require this functionality to be present to seek in
    HTML5 audio or video), but this handler should not be used with
    files that are too large to fit comfortably in memory.

    **Subclassing notes**

    This class is designed to be extensible by subclassing, but because
    of the way static urls are generated with class methods rather than
    instance methods, the inheritance patterns are somewhat unusual.
    Be sure to use the ``@classmethod`` decorator when overriding a
    class method.  Instance methods may use the attributes ``self.path``
    ``self.absolute_path``, and ``self.modified``.

    To change the way static urls are generated (e.g. to match the behavior
    of another server or CDN), override `make_static_url`, `parse_url_path`,
    `get_cache_time`, and/or `get_version`.

    To replace all interaction with the filesystem (e.g. to serve
    static content from a database), override `get_content`,
    `get_content_size`, `get_modified_time`, `get_absolute_path`, and
    `validate_absolute_path`.

    .. versionchanged:: 3.1
       Many of the methods for subclasses were added in Tornado 3.1.
    """
    CACHE_MAX_AGE = 86400 * 365 * 10  # 10 years

    _static_hashes = {}
    _lock = threading.Lock()  # protects _static_hashes

    def initialize(self, path, default_filename=None):
        self.root = path
        self.default_filename = default_filename

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._static_hashes = {}

    def head(self, path):
        self.get(path, include_body=False)

    def get(self, path, include_body=True):
        # Set up our path instance variables.
        self.path = self.parse_url_path(path)
        del path  # make sure we don't refer to path instead of self.path again
        absolute_path = self.get_absolute_path(self.root, self.path)
        self.absolute_path = self.validate_absolute_path(
            self.root, absolute_path)
        if self.absolute_path is None:
            return

        self.modified = self.get_modified_time()
        self.set_headers()

        if self.should_return_304():
            self.set_status(304)
            return

        request_range = None
        range_header = self.request.headers.get("Range")
        if range_header:
            # As per RFC 2616 14.16, if an invalid Range header is specified,
            # the request will be treated as if the header didn't exist.
            request_range = httputil._parse_request_range(range_header)

        if request_range:
            start, end = request_range
            size = self.get_content_size()
            if (start is not None and start >= size) or end == 0:
                # As per RFC 2616 14.35.1, a range is not satisfiable only: if
                # the first requested byte is equal to or greater than the
                # content, or when a suffix with length 0 is specified
                self.set_status(416)  # Range Not Satisfiable
                self.set_header("Content-Type", "text/plain")
                self.set_header("Content-Range", "bytes */%s" %(size, ))
                return
            if start is not None and start < 0:
                start += size
            # Note: only return HTTP 206 if less than the entire range has been
            # requested. Not only is this semantically correct, but Chrome
            # refuses to play audio if it gets an HTTP 206 in response to
            # ``Range: bytes=0-``.
            if size != (end or size) - (start or 0):
                self.set_status(206)  # Partial Content
                self.set_header("Content-Range",
                                httputil._get_content_range(start, end, size))
        else:
            start = end = None
        content = self.get_content(self.absolute_path, start, end)
        if isinstance(content, bytes_type):
            content = [content]
        content_length = 0
        for chunk in content:
            if include_body:
                self.write(chunk)
            else:
                content_length += len(chunk)
        if not include_body:
            assert self.request.method == "HEAD"
            self.set_header("Content-Length", content_length)

    def compute_etag(self):
        """Sets the ``Etag`` header based on static url version.

        This allows efficient ``If-None-Match`` checks against cached
        versions, and sends the correct ``Etag`` for a partial response
        (i.e. the same ``Etag`` as the full file).

        .. versionadded:: 3.1
        """
        version_hash = self._get_cached_version(self.absolute_path)
        if not version_hash:
            return None
        return '"%s"' % (version_hash, )

    def set_headers(self):
        """Sets the content and caching headers on the response.

        .. versionadded:: 3.1
        """
        self.set_header("Accept-Ranges", "bytes")
        self.set_etag_header()

        if self.modified is not None:
            self.set_header("Last-Modified", self.modified)

        content_type = self.get_content_type()
        if content_type:
            self.set_header("Content-Type", content_type)

        cache_time = self.get_cache_time(self.path, self.modified, content_type)
        if cache_time > 0:
            self.set_header("Expires", datetime.datetime.utcnow() +
                            datetime.timedelta(seconds=cache_time))
            self.set_header("Cache-Control", "max-age=" + str(cache_time))

        self.set_extra_headers(self.path)

    def should_return_304(self):
        """Returns True if the headers indicate that we should return 304.

        .. versionadded:: 3.1
        """
        if self.check_etag_header():
            return True

        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if date_tuple is not None:
                if_since = datetime.datetime(*date_tuple[:6])
                if if_since >= self.modified:
                    return True

        return False

    @classmethod
    def get_absolute_path(cls, root, path):
        """Returns the absolute location of ``path`` relative to ``root``.

        ``root`` is the path configured for this `StaticFileHandler`
        (in most cases the ``static_path`` `Application` setting).

        This class method may be overridden in subclasses.  By default
        it returns a filesystem path, but other strings may be used
        as long as they are unique and understood by the subclass's
        overridden `get_content`.

        .. versionadded:: 3.1
        """
        abspath = os.path.abspath(os.path.join(root, path))
        return abspath

    def validate_absolute_path(self, root, absolute_path):
        """Validate and return the absolute path.

        ``root`` is the configured path for the `StaticFileHandler`,
        and ``path`` is the result of `get_absolute_path`

        This is an instance method called during request processing,
        so it may raise `HTTPError` or use methods like
        `RequestHandler.redirect` (return None after redirecting to
        halt further processing).  This is where 404 errors for missing files
        are generated.

        This method may modify the path before returning it, but note that
        any such modifications will not be understood by `make_static_url`.

        In instance methods, this method's result is available as
        ``self.absolute_path``.

        .. versionadded:: 3.1
        """
        root = os.path.abspath(root)
        # os.path.abspath strips a trailing /
        # it needs to be temporarily added back for requests to root/
        if not (absolute_path + os.path.sep).startswith(root):
            raise HTTPError(403, "%s is not in root static directory",
                            self.path)
        if (os.path.isdir(absolute_path) and
                self.default_filename is not None):
            # need to look at the request.path here for when path is empty
            # but there is some prefix to the path that was already
            # trimmed by the routing
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            absolute_path = os.path.join(absolute_path, self.default_filename)
        if not os.path.exists(absolute_path):
            raise HTTPError(404)
        if not os.path.isfile(absolute_path):
            raise HTTPError(403, "%s is not a file", self.path)
        return absolute_path

    @classmethod
    def get_content(cls, abspath, start=None, end=None):
        """Retrieve the content of the requested resource which is located
        at the given absolute path.

        This class method may be overridden by subclasses.  Note that its
        signature is different from other overridable class methods
        (no ``settings`` argument); this is deliberate to ensure that
        ``abspath`` is able to stand on its own as a cache key.

        This method should either return a byte string or an iterator
        of byte strings.  The latter is preferred for large files
        as it helps reduce memory fragmentation.

        .. versionadded:: 3.1
        """
        with open(abspath, "rb") as file:
            if start is not None:
                file.seek(start)
            if end is not None:
                remaining = end - (start or 0)
            else:
                remaining = None
            while True:
                chunk_size = 64 * 1024
                if remaining is not None and remaining < chunk_size:
                    chunk_size = remaining
                chunk = file.read(chunk_size)
                if chunk:
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
                else:
                    if remaining is not None:
                        assert remaining == 0
                    return

    @classmethod
    def get_content_version(cls, abspath):
        """Returns a version string for the resource at the given path.

        This class method may be overridden by subclasses.  The
        default implementation is a hash of the file's contents.

        .. versionadded:: 3.1
        """
        data = cls.get_content(abspath)
        hasher = hashlib.md5()
        if isinstance(data, bytes_type):
            hasher.update(data)
        else:
            for chunk in data:
                hasher.update(chunk)
        return hasher.hexdigest()

    def _stat(self):
        if not hasattr(self, '_stat_result'):
            self._stat_result = os.stat(self.absolute_path)
        return self._stat_result

    def get_content_size(self):
        """Retrieve the total size of the resource at the given path.

        This method may be overridden by subclasses. It will only
        be called if a partial result is requested from `get_content`

        .. versionadded:: 3.1
        """
        stat_result = self._stat()
        return stat_result[stat.ST_SIZE]

    def get_modified_time(self):
        """Returns the time that ``self.absolute_path`` was last modified.

        May be overridden in subclasses.  Should return a `~datetime.datetime`
        object or None.

        .. versionadded:: 3.1
        """
        stat_result = self._stat()
        modified = datetime.datetime.utcfromtimestamp(stat_result[stat.ST_MTIME])
        return modified

    def get_content_type(self):
        """Returns the ``Content-Type`` header to be used for this request.

        .. versionadded:: 3.1
        """
        mime_type, encoding = mimetypes.guess_type(self.absolute_path)
        return mime_type

    def set_extra_headers(self, path):
        """For subclass to add extra headers to the response"""
        pass

    def get_cache_time(self, path, modified, mime_type):
        """Override to customize cache control behavior.

        Return a positive number of seconds to make the result
        cacheable for that amount of time or 0 to mark resource as
        cacheable for an unspecified amount of time (subject to
        browser heuristics).

        By default returns cache expiry of 10 years for resources requested
        with ``v`` argument.
        """
        return self.CACHE_MAX_AGE if "v" in self.request.arguments else 0

    @classmethod
    def make_static_url(cls, settings, path, include_version=True):
        """Constructs a versioned url for the given path.

        This method may be overridden in subclasses (but note that it
        is a class method rather than an instance method).  Subclasses
        are only required to implement the signature
        ``make_static_url(cls, settings, path)``; other keyword
        arguments may be passed through `~RequestHandler.static_url`
        but are not standard.

        ``settings`` is the `Application.settings` dictionary.  ``path``
        is the static path being requested.  The url returned should be
        relative to the current host.

        ``include_version`` determines whether the generated URL should
        include the query string containing the version hash of the
        file corresponding to the given ``path``.

        """
        url = settings.get('static_url_prefix', '/static/') + path
        if not include_version:
            return url

        version_hash = cls.get_version(settings, path)
        if not version_hash:
            return url

        return '%s?v=%s' % (url, version_hash)

    def parse_url_path(self, url_path):
        """Converts a static URL path into a filesystem path.

        ``url_path`` is the path component of the URL with
        ``static_url_prefix`` removed.  The return value should be
        filesystem path relative to ``static_path``.

        This is the inverse of `make_static_url`.
        """
        if os.path.sep != "/":
            url_path = url_path.replace("/", os.path.sep)
        return url_path

    @classmethod
    def get_version(cls, settings, path):
        """Generate the version string to be used in static URLs.

        ``settings`` is the `Application.settings` dictionary and ``path``
        is the relative location of the requested asset on the filesystem.
        The returned value should be a string, or ``None`` if no version
        could be determined.

        .. versionchanged:: 3.1
           This method was previously recommended for subclasses to override;
           `get_content_version` is now preferred as it allows the base
           class to handle caching of the result.
        """
        abs_path = cls.get_absolute_path(settings['static_path'], path)
        return cls._get_cached_version(abs_path)

    @classmethod
    def _get_cached_version(cls, abs_path):
        with cls._lock:
            hashes = cls._static_hashes
            if abs_path not in hashes:
                try:
                    hashes[abs_path] = cls.get_content_version(abs_path)
                except Exception:
                    gen_log.error("Could not open static file %r", abs_path)
                    hashes[abs_path] = None
            hsh = hashes.get(abs_path)
            if hsh:
                return hsh
        return None


class FallbackHandler(RequestHandler):
    """A `RequestHandler` that wraps another HTTP server callback.

    The fallback is a callable object that accepts an
    `~.httpserver.HTTPRequest`, such as an `Application` or
    `tornado.wsgi.WSGIContainer`.  This is most useful to use both
    Tornado ``RequestHandlers`` and WSGI in the same server.  Typical
    usage::

        wsgi_app = tornado.wsgi.WSGIContainer(
            django.core.handlers.wsgi.WSGIHandler())
        application = tornado.web.Application([
            (r"/foo", FooHandler),
            (r".*", FallbackHandler, dict(fallback=wsgi_app),
        ])
    """
    def initialize(self, fallback):
        self.fallback = fallback

    def prepare(self):
        self.fallback(self.request)
        self._finished = True


class OutputTransform(object):
    """A transform modifies the result of an HTTP request (e.g., GZip encoding)

    A new transform instance is created for every request. See the
    ChunkedTransferEncoding example below if you want to implement a
    new Transform.
    """
    def __init__(self, request):
        pass

    def transform_first_chunk(self, status_code, headers, chunk, finishing):
        return status_code, headers, chunk

    def transform_chunk(self, chunk, finishing):
        return chunk


class GZipContentEncoding(OutputTransform):
    """Applies the gzip content encoding to the response.

    See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.11
    """
    CONTENT_TYPES = set([
        "text/plain", "text/html", "text/css", "text/xml", "application/javascript",
        "application/x-javascript", "application/xml", "application/atom+xml",
        "text/javascript", "application/json", "application/xhtml+xml"])
    MIN_LENGTH = 5

    def __init__(self, request):
        self._gzipping = request.supports_http_1_1() and \
            "gzip" in request.headers.get("Accept-Encoding", "")

    def transform_first_chunk(self, status_code, headers, chunk, finishing):
        if 'Vary' in headers:
            headers['Vary'] += b', Accept-Encoding'
        else:
            headers['Vary'] = b'Accept-Encoding'
        if self._gzipping:
            ctype = _unicode(headers.get("Content-Type", "")).split(";")[0]
            self._gzipping = (ctype in self.CONTENT_TYPES) and \
                (not finishing or len(chunk) >= self.MIN_LENGTH) and \
                (finishing or "Content-Length" not in headers) and \
                ("Content-Encoding" not in headers)
        if self._gzipping:
            headers["Content-Encoding"] = "gzip"
            self._gzip_value = BytesIO()
            self._gzip_file = gzip.GzipFile(mode="w", fileobj=self._gzip_value)
            chunk = self.transform_chunk(chunk, finishing)
            if "Content-Length" in headers:
                headers["Content-Length"] = str(len(chunk))
        return status_code, headers, chunk

    def transform_chunk(self, chunk, finishing):
        if self._gzipping:
            self._gzip_file.write(chunk)
            if finishing:
                self._gzip_file.close()
            else:
                self._gzip_file.flush()
            chunk = self._gzip_value.getvalue()
            self._gzip_value.truncate(0)
            self._gzip_value.seek(0)
        return chunk


class ChunkedTransferEncoding(OutputTransform):
    """Applies the chunked transfer encoding to the response.

    See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.6.1
    """
    def __init__(self, request):
        self._chunking = request.supports_http_1_1()

    def transform_first_chunk(self, status_code, headers, chunk, finishing):
        # 304 responses have no body (not even a zero-length body), and so
        # should not have either Content-Length or Transfer-Encoding headers.
        if self._chunking and status_code != 304:
            # No need to chunk the output if a Content-Length is specified
            if "Content-Length" in headers or "Transfer-Encoding" in headers:
                self._chunking = False
            else:
                headers["Transfer-Encoding"] = "chunked"
                chunk = self.transform_chunk(chunk, finishing)
        return status_code, headers, chunk

    def transform_chunk(self, block, finishing):
        if self._chunking:
            # Don't write out empty chunks because that means END-OF-STREAM
            # with chunked encoding
            if block:
                block = utf8("%x" % len(block)) + b"\r\n" + block + b"\r\n"
            if finishing:
                block += b"0\r\n\r\n"
        return block


def authenticated(method):
    """Decorate methods with this to require that the user be logged in.

    If the user is not logged in, they will be redirected to the configured
    `login url <RequestHandler.get_login_url>`.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method in ("GET", "HEAD"):
                url = self.get_login_url()
                if "?" not in url:
                    if urlparse.urlsplit(url).scheme:
                        # if login url is absolute, make next absolute too
                        next_url = self.request.full_url()
                    else:
                        next_url = self.request.uri
                    url += "?" + urlencode(dict(next=next_url))
                self.redirect(url)
                return
            raise HTTPError(403)
        return method(self, *args, **kwargs)
    return wrapper


class UIModule(object):
    """A re-usable, modular UI unit on a page.

    UI modules often execute additional queries, and they can include
    additional CSS and JavaScript that will be included in the output
    page, which is automatically inserted on page render.
    """
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request
        self.ui = handler.ui
        self.current_user = handler.current_user
        self.locale = handler.locale

    def render(self, *args, **kwargs):
        """Overridden in subclasses to return this module's output."""
        raise NotImplementedError()

    def embedded_javascript(self):
        """Returns a JavaScript string that will be embedded in the page."""
        return None

    def javascript_files(self):
        """Returns a list of JavaScript files required by this module."""
        return None

    def embedded_css(self):
        """Returns a CSS string that will be embedded in the page."""
        return None

    def css_files(self):
        """Returns a list of CSS files required by this module."""
        return None

    def html_head(self):
        """Returns a CSS string that will be put in the <head/> element"""
        return None

    def html_body(self):
        """Returns an HTML string that will be put in the <body/> element"""
        return None

    def render_string(self, path, **kwargs):
        """Renders a template and returns it as a string."""
        return self.handler.render_string(path, **kwargs)


class _linkify(UIModule):
    def render(self, text, **kwargs):
        return escape.linkify(text, **kwargs)


class _xsrf_form_html(UIModule):
    def render(self):
        return self.handler.xsrf_form_html()


class TemplateModule(UIModule):
    """UIModule that simply renders the given template.

    {% module Template("foo.html") %} is similar to {% include "foo.html" %},
    but the module version gets its own namespace (with kwargs passed to
    Template()) instead of inheriting the outer template's namespace.

    Templates rendered through this module also get access to UIModule's
    automatic javascript/css features.  Simply call set_resources
    inside the template and give it keyword arguments corresponding to
    the methods on UIModule: {{ set_resources(js_files=static_url("my.js")) }}
    Note that these resources are output once per template file, not once
    per instantiation of the template, so they must not depend on
    any arguments to the template.
    """
    def __init__(self, handler):
        super(TemplateModule, self).__init__(handler)
        # keep resources in both a list and a dict to preserve order
        self._resource_list = []
        self._resource_dict = {}

    def render(self, path, **kwargs):
        def set_resources(**kwargs):
            if path not in self._resource_dict:
                self._resource_list.append(kwargs)
                self._resource_dict[path] = kwargs
            else:
                if self._resource_dict[path] != kwargs:
                    raise ValueError("set_resources called with different "
                                     "resources for the same template")
            return ""
        return self.render_string(path, set_resources=set_resources,
                                  **kwargs)

    def _get_resources(self, key):
        return (r[key] for r in self._resource_list if key in r)

    def embedded_javascript(self):
        return "\n".join(self._get_resources("embedded_javascript"))

    def javascript_files(self):
        result = []
        for f in self._get_resources("javascript_files"):
            if isinstance(f, (unicode_type, bytes_type)):
                result.append(f)
            else:
                result.extend(f)
        return result

    def embedded_css(self):
        return "\n".join(self._get_resources("embedded_css"))

    def css_files(self):
        result = []
        for f in self._get_resources("css_files"):
            if isinstance(f, (unicode_type, bytes_type)):
                result.append(f)
            else:
                result.extend(f)
        return result

    def html_head(self):
        return "".join(self._get_resources("html_head"))

    def html_body(self):
        return "".join(self._get_resources("html_body"))


class _UIModuleNamespace(object):
    """Lazy namespace which creates UIModule proxies bound to a handler."""
    def __init__(self, handler, ui_modules):
        self.handler = handler
        self.ui_modules = ui_modules

    def __getitem__(self, key):
        return self.handler._ui_module(key, self.ui_modules[key])

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(str(e))


class URLSpec(object):
    """Specifies mappings between URLs and handlers."""
    def __init__(self, pattern, handler_class, kwargs=None, name=None):
        """Parameters:

        * ``pattern``: Regular expression to be matched.  Any groups
          in the regex will be passed in to the handler's get/post/etc
          methods as arguments.

        * ``handler_class``: `RequestHandler` subclass to be invoked.

        * ``kwargs`` (optional): A dictionary of additional arguments
          to be passed to the handler's constructor.

        * ``name`` (optional): A name for this handler.  Used by
          `Application.reverse_url`.
        """
        if not pattern.endswith('$'):
            pattern += '$'
        self.regex = re.compile(pattern)
        assert len(self.regex.groupindex) in (0, self.regex.groups), \
            ("groups in url regexes must either be all named or all "
             "positional: %r" % self.regex.pattern)
        self.handler_class = handler_class
        self.kwargs = kwargs or {}
        self.name = name
        self._path, self._group_count = self._find_groups()

    def __repr__(self):
        return '%s(%r, %s, kwargs=%r, name=%r)' % \
            (self.__class__.__name__, self.regex.pattern,
             self.handler_class, self.kwargs, self.name)

    def _find_groups(self):
        """Returns a tuple (reverse string, group count) for a url.

        For example: Given the url pattern /([0-9]{4})/([a-z-]+)/, this method
        would return ('/%s/%s/', 2).
        """
        pattern = self.regex.pattern
        if pattern.startswith('^'):
            pattern = pattern[1:]
        if pattern.endswith('$'):
            pattern = pattern[:-1]

        if self.regex.groups != pattern.count('('):
            # The pattern is too complicated for our simplistic matching,
            # so we can't support reversing it.
            return (None, None)

        pieces = []
        for fragment in pattern.split('('):
            if ')' in fragment:
                paren_loc = fragment.index(')')
                if paren_loc >= 0:
                    pieces.append('%s' + fragment[paren_loc + 1:])
            else:
                pieces.append(fragment)

        return (''.join(pieces), self.regex.groups)

    def reverse(self, *args):
        assert self._path is not None, \
            "Cannot reverse url regex " + self.regex.pattern
        assert len(args) == self._group_count, "required number of arguments "\
            "not found"
        if not len(args):
            return self._path
        converted_args = []
        for a in args:
            if not isinstance(a, (unicode_type, bytes_type)):
                a = str(a)
            converted_args.append(escape.url_escape(utf8(a), plus=False))
        return self._path % tuple(converted_args)

url = URLSpec


if hasattr(hmac, 'compare_digest'):  # python 3.3
    _time_independent_equals = hmac.compare_digest
else:
    def _time_independent_equals(a, b):
        if len(a) != len(b):
            return False
        result = 0
        if isinstance(a[0], int):  # python3 byte strings
            for x, y in zip(a, b):
                result |= x ^ y
        else:  # python2
            for x, y in zip(a, b):
                result |= ord(x) ^ ord(y)
        return result == 0


def create_signed_value(secret, name, value):
    timestamp = utf8(str(int(time.time())))
    value = base64.b64encode(utf8(value))
    signature = _create_signature(secret, name, value, timestamp)
    value = b"|".join([value, timestamp, signature])
    return value


def decode_signed_value(secret, name, value, max_age_days=31):
    if not value:
        return None
    parts = utf8(value).split(b"|")
    if len(parts) != 3:
        return None
    signature = _create_signature(secret, name, parts[0], parts[1])
    if not _time_independent_equals(parts[2], signature):
        gen_log.warning("Invalid cookie signature %r", value)
        return None
    timestamp = int(parts[1])
    if timestamp < time.time() - max_age_days * 86400:
        gen_log.warning("Expired cookie %r", value)
        return None
    if timestamp > time.time() + 31 * 86400:
        # _cookie_signature does not hash a delimiter between the
        # parts of the cookie, so an attacker could transfer trailing
        # digits from the payload to the timestamp without altering the
        # signature.  For backwards compatibility, sanity-check timestamp
        # here instead of modifying _cookie_signature.
        gen_log.warning("Cookie timestamp in future; possible tampering %r", value)
        return None
    if parts[1].startswith(b"0"):
        gen_log.warning("Tampered cookie %r", value)
        return None
    try:
        return base64.b64decode(parts[0])
    except Exception:
        return None


def _create_signature(secret, *parts):
    hash = hmac.new(utf8(secret), digestmod=hashlib.sha1)
    for part in parts:
        hash.update(utf8(part))
    return utf8(hash.hexdigest())

########NEW FILE########
__FILENAME__ = websocket
"""Implementation of the WebSocket protocol.

`WebSockets <http://dev.w3.org/html5/websockets/>`_ allow for bidirectional
communication between the browser and server.

.. warning::

   The WebSocket protocol was recently finalized as `RFC 6455
   <http://tools.ietf.org/html/rfc6455>`_ and is not yet supported in
   all browsers.  Refer to http://caniuse.com/websockets for details
   on compatibility.  In addition, during development the protocol
   went through several incompatible versions, and some browsers only
   support older versions.  By default this module only supports the
   latest version of the protocol, but optional support for an older
   version (known as "draft 76" or "hixie-76") can be enabled by
   overriding `WebSocketHandler.allow_draft76` (see that method's
   documentation for caveats).
"""

from __future__ import absolute_import, division, print_function, with_statement
# Author: Jacob Kristhammar, 2010

import array
import base64
import collections
import functools
import hashlib
import os
import struct
import time
import tornado.escape
import tornado.web

from tornado.concurrent import Future
from tornado.escape import utf8, native_str
from tornado import httpclient
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado.log import gen_log, app_log
from tornado.netutil import Resolver
from tornado import simple_httpclient
from tornado.util import bytes_type, unicode_type

try:
    xrange  # py2
except NameError:
    xrange = range  # py3


class WebSocketError(Exception):
    pass


class WebSocketHandler(tornado.web.RequestHandler):
    """Subclass this class to create a basic WebSocket handler.

    Override `on_message` to handle incoming messages, and use
    `write_message` to send messages to the client. You can also
    override `open` and `on_close` to handle opened and closed
    connections.

    See http://dev.w3.org/html5/websockets/ for details on the
    JavaScript interface.  The protocol is specified at
    http://tools.ietf.org/html/rfc6455.

    Here is an example WebSocket handler that echos back all received messages
    back to the client::

      class EchoWebSocket(websocket.WebSocketHandler):
          def open(self):
              print "WebSocket opened"

          def on_message(self, message):
              self.write_message(u"You said: " + message)

          def on_close(self):
              print "WebSocket closed"

    WebSockets are not standard HTTP connections. The "handshake" is
    HTTP, but after the handshake, the protocol is
    message-based. Consequently, most of the Tornado HTTP facilities
    are not available in handlers of this type. The only communication
    methods available to you are `write_message()`, `ping()`, and
    `close()`. Likewise, your request handler class should implement
    `open()` method rather than ``get()`` or ``post()``.

    If you map the handler above to ``/websocket`` in your application, you can
    invoke it in JavaScript with::

      var ws = new WebSocket("ws://localhost:8888/websocket");
      ws.onopen = function() {
         ws.send("Hello, world");
      };
      ws.onmessage = function (evt) {
         alert(evt.data);
      };

    This script pops up an alert box that says "You said: Hello, world".
    """
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request,
                                            **kwargs)
        self.stream = request.connection.stream
        self.ws_connection = None

    def _execute(self, transforms, *args, **kwargs):
        self.open_args = args
        self.open_kwargs = kwargs

        # Websocket only supports GET method
        if self.request.method != 'GET':
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            ))
            self.stream.close()
            return

        # Upgrade header should be present and should be equal to WebSocket
        if self.request.headers.get("Upgrade", "").lower() != 'websocket':
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 400 Bad Request\r\n\r\n"
                "Can \"Upgrade\" only to \"WebSocket\"."
            ))
            self.stream.close()
            return

        # Connection header should be upgrade. Some proxy servers/load balancers
        # might mess with it.
        headers = self.request.headers
        connection = map(lambda s: s.strip().lower(), headers.get("Connection", "").split(","))
        if 'upgrade' not in connection:
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 400 Bad Request\r\n\r\n"
                "\"Connection\" must be \"Upgrade\"."
            ))
            self.stream.close()
            return

        # The difference between version 8 and 13 is that in 8 the
        # client sends a "Sec-Websocket-Origin" header and in 13 it's
        # simply "Origin".
        if self.request.headers.get("Sec-WebSocket-Version") in ("7", "8", "13"):
            self.ws_connection = WebSocketProtocol13(self)
            self.ws_connection.accept_connection()
        elif (self.allow_draft76() and
              "Sec-WebSocket-Version" not in self.request.headers):
            self.ws_connection = WebSocketProtocol76(self)
            self.ws_connection.accept_connection()
        else:
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 426 Upgrade Required\r\n"
                "Sec-WebSocket-Version: 8\r\n\r\n"))
            self.stream.close()

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket.

        The message may be either a string or a dict (which will be
        encoded as json).  If the ``binary`` argument is false, the
        message will be sent as utf8; in binary mode any byte string
        is allowed.
        """
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        self.ws_connection.write_message(message, binary=binary)

    def select_subprotocol(self, subprotocols):
        """Invoked when a new WebSocket requests specific subprotocols.

        ``subprotocols`` is a list of strings identifying the
        subprotocols proposed by the client.  This method may be
        overridden to return one of those strings to select it, or
        ``None`` to not select a subprotocol.  Failure to select a
        subprotocol does not automatically abort the connection,
        although clients may close the connection if none of their
        proposed subprotocols was selected.
        """
        return None

    def open(self):
        """Invoked when a new WebSocket is opened.

        The arguments to `open` are extracted from the `tornado.web.URLSpec`
        regular expression, just like the arguments to
        `tornado.web.RequestHandler.get`.
        """
        pass

    def on_message(self, message):
        """Handle incoming messages on the WebSocket

        This method must be overridden.
        """
        raise NotImplementedError

    def ping(self, data):
        """Send ping frame to the remote end."""
        self.ws_connection.write_ping(data)

    def on_pong(self, data):
        """Invoked when the response to a ping frame is received."""
        pass

    def on_close(self):
        """Invoked when the WebSocket is closed."""
        pass

    def close(self):
        """Closes this Web Socket.

        Once the close handshake is successful the socket will be closed.
        """
        self.ws_connection.close()
        self.ws_connection = None

    def allow_draft76(self):
        """Override to enable support for the older "draft76" protocol.

        The draft76 version of the websocket protocol is disabled by
        default due to security concerns, but it can be enabled by
        overriding this method to return True.

        Connections using the draft76 protocol do not support the
        ``binary=True`` flag to `write_message`.

        Support for the draft76 protocol is deprecated and will be
        removed in a future version of Tornado.
        """
        return False

    def set_nodelay(self, value):
        """Set the no-delay flag for this stream.

        By default, small messages may be delayed and/or combined to minimize
        the number of packets sent.  This can sometimes cause 200-500ms delays
        due to the interaction between Nagle's algorithm and TCP delayed
        ACKs.  To reduce this delay (at the expense of possibly increasing
        bandwidth usage), call ``self.set_nodelay(True)`` once the websocket
        connection is established.

        See `.BaseIOStream.set_nodelay` for additional details.

        .. versionadded:: 3.1
        """
        self.stream.set_nodelay(value)

    def get_websocket_scheme(self):
        """Return the url scheme used for this request, either "ws" or "wss".

        This is normally decided by HTTPServer, but applications
        may wish to override this if they are using an SSL proxy
        that does not provide the X-Scheme header as understood
        by HTTPServer.

        Note that this is only used by the draft76 protocol.
        """
        return "wss" if self.request.protocol == "https" else "ws"

    def async_callback(self, callback, *args, **kwargs):
        """Obsolete - catches exceptions from the wrapped function.

        This function is normally unncecessary thanks to
        `tornado.stack_context`.
        """
        return self.ws_connection.async_callback(callback, *args, **kwargs)

    def _not_supported(self, *args, **kwargs):
        raise Exception("Method not supported for Web Sockets")

    def on_connection_close(self):
        if self.ws_connection:
            self.ws_connection.on_connection_close()
            self.ws_connection = None
            self.on_close()


for method in ["write", "redirect", "set_header", "send_error", "set_cookie",
               "set_status", "flush", "finish"]:
    setattr(WebSocketHandler, method, WebSocketHandler._not_supported)


class WebSocketProtocol(object):
    """Base class for WebSocket protocol versions.
    """
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request
        self.stream = handler.stream
        self.client_terminated = False
        self.server_terminated = False

    def async_callback(self, callback, *args, **kwargs):
        """Wrap callbacks with this if they are used on asynchronous requests.

        Catches exceptions properly and closes this WebSocket if an exception
        is uncaught.
        """
        if args or kwargs:
            callback = functools.partial(callback, *args, **kwargs)

        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception:
                app_log.error("Uncaught exception in %s",
                              self.request.path, exc_info=True)
                self._abort()
        return wrapper

    def on_connection_close(self):
        self._abort()

    def _abort(self):
        """Instantly aborts the WebSocket connection by closing the socket"""
        self.client_terminated = True
        self.server_terminated = True
        self.stream.close()  # forcibly tear down the connection
        self.close()  # let the subclass cleanup


class WebSocketProtocol76(WebSocketProtocol):
    """Implementation of the WebSockets protocol, version hixie-76.

    This class provides basic functionality to process WebSockets requests as
    specified in
    http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76
    """
    def __init__(self, handler):
        WebSocketProtocol.__init__(self, handler)
        self.challenge = None
        self._waiting = None

    def accept_connection(self):
        try:
            self._handle_websocket_headers()
        except ValueError:
            gen_log.debug("Malformed WebSocket request received")
            self._abort()
            return

        scheme = self.handler.get_websocket_scheme()

        # draft76 only allows a single subprotocol
        subprotocol_header = ''
        subprotocol = self.request.headers.get("Sec-WebSocket-Protocol", None)
        if subprotocol:
            selected = self.handler.select_subprotocol([subprotocol])
            if selected:
                assert selected == subprotocol
                subprotocol_header = "Sec-WebSocket-Protocol: %s\r\n" % selected

        # Write the initial headers before attempting to read the challenge.
        # This is necessary when using proxies (such as HAProxy), which
        # need to see the Upgrade headers before passing through the
        # non-HTTP traffic that follows.
        self.stream.write(tornado.escape.utf8(
            "HTTP/1.1 101 WebSocket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "Server: TornadoServer/%(version)s\r\n"
            "Sec-WebSocket-Origin: %(origin)s\r\n"
            "Sec-WebSocket-Location: %(scheme)s://%(host)s%(uri)s\r\n"
            "%(subprotocol)s"
            "\r\n" % (dict(
            version=tornado.version,
            origin=self.request.headers["Origin"],
            scheme=scheme,
            host=self.request.host,
            uri=self.request.uri,
            subprotocol=subprotocol_header))))
        self.stream.read_bytes(8, self._handle_challenge)

    def challenge_response(self, challenge):
        """Generates the challenge response that's needed in the handshake

        The challenge parameter should be the raw bytes as sent from the
        client.
        """
        key_1 = self.request.headers.get("Sec-Websocket-Key1")
        key_2 = self.request.headers.get("Sec-Websocket-Key2")
        try:
            part_1 = self._calculate_part(key_1)
            part_2 = self._calculate_part(key_2)
        except ValueError:
            raise ValueError("Invalid Keys/Challenge")
        return self._generate_challenge_response(part_1, part_2, challenge)

    def _handle_challenge(self, challenge):
        try:
            challenge_response = self.challenge_response(challenge)
        except ValueError:
            gen_log.debug("Malformed key data in WebSocket request")
            self._abort()
            return
        self._write_response(challenge_response)

    def _write_response(self, challenge):
        self.stream.write(challenge)
        self.async_callback(self.handler.open)(*self.handler.open_args, **self.handler.open_kwargs)
        self._receive_message()

    def _handle_websocket_headers(self):
        """Verifies all invariant- and required headers

        If a header is missing or have an incorrect value ValueError will be
        raised
        """
        fields = ("Origin", "Host", "Sec-Websocket-Key1",
                  "Sec-Websocket-Key2")
        if not all(map(lambda f: self.request.headers.get(f), fields)):
            raise ValueError("Missing/Invalid WebSocket headers")

    def _calculate_part(self, key):
        """Processes the key headers and calculates their key value.

        Raises ValueError when feed invalid key."""
        # pyflakes complains about variable reuse if both of these lines use 'c'
        number = int(''.join(c for c in key if c.isdigit()))
        spaces = len([c2 for c2 in key if c2.isspace()])
        try:
            key_number = number // spaces
        except (ValueError, ZeroDivisionError):
            raise ValueError
        return struct.pack(">I", key_number)

    def _generate_challenge_response(self, part_1, part_2, part_3):
        m = hashlib.md5()
        m.update(part_1)
        m.update(part_2)
        m.update(part_3)
        return m.digest()

    def _receive_message(self):
        self.stream.read_bytes(1, self._on_frame_type)

    def _on_frame_type(self, byte):
        frame_type = ord(byte)
        if frame_type == 0x00:
            self.stream.read_until(b"\xff", self._on_end_delimiter)
        elif frame_type == 0xff:
            self.stream.read_bytes(1, self._on_length_indicator)
        else:
            self._abort()

    def _on_end_delimiter(self, frame):
        if not self.client_terminated:
            self.async_callback(self.handler.on_message)(
                frame[:-1].decode("utf-8", "replace"))
        if not self.client_terminated:
            self._receive_message()

    def _on_length_indicator(self, byte):
        if ord(byte) != 0x00:
            self._abort()
            return
        self.client_terminated = True
        self.close()

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket."""
        if binary:
            raise ValueError(
                "Binary messages not supported by this version of websockets")
        if isinstance(message, unicode_type):
            message = message.encode("utf-8")
        assert isinstance(message, bytes_type)
        self.stream.write(b"\x00" + message + b"\xff")

    def write_ping(self, data):
        """Send ping frame."""
        raise ValueError("Ping messages not supported by this version of websockets")

    def close(self):
        """Closes the WebSocket connection."""
        if not self.server_terminated:
            if not self.stream.closed():
                self.stream.write("\xff\x00")
            self.server_terminated = True
        if self.client_terminated:
            if self._waiting is not None:
                self.stream.io_loop.remove_timeout(self._waiting)
            self._waiting = None
            self.stream.close()
        elif self._waiting is None:
            self._waiting = self.stream.io_loop.add_timeout(
                time.time() + 5, self._abort)


class WebSocketProtocol13(WebSocketProtocol):
    """Implementation of the WebSocket protocol from RFC 6455.

    This class supports versions 7 and 8 of the protocol in addition to the
    final version 13.
    """
    def __init__(self, handler, mask_outgoing=False):
        WebSocketProtocol.__init__(self, handler)
        self.mask_outgoing = mask_outgoing
        self._final_frame = False
        self._frame_opcode = None
        self._masked_frame = None
        self._frame_mask = None
        self._frame_length = None
        self._fragmented_message_buffer = None
        self._fragmented_message_opcode = None
        self._waiting = None

    def accept_connection(self):
        try:
            self._handle_websocket_headers()
            self._accept_connection()
        except ValueError:
            gen_log.debug("Malformed WebSocket request received", exc_info=True)
            self._abort()
            return

    def _handle_websocket_headers(self):
        """Verifies all invariant- and required headers

        If a header is missing or have an incorrect value ValueError will be
        raised
        """
        fields = ("Host", "Sec-Websocket-Key", "Sec-Websocket-Version")
        if not all(map(lambda f: self.request.headers.get(f), fields)):
            raise ValueError("Missing/Invalid WebSocket headers")

    @staticmethod
    def compute_accept_value(key):
        """Computes the value for the Sec-WebSocket-Accept header,
        given the value for Sec-WebSocket-Key.
        """
        sha1 = hashlib.sha1()
        sha1.update(utf8(key))
        sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
        return native_str(base64.b64encode(sha1.digest()))

    def _challenge_response(self):
        return WebSocketProtocol13.compute_accept_value(
            self.request.headers.get("Sec-Websocket-Key"))

    def _accept_connection(self):
        subprotocol_header = ''
        subprotocols = self.request.headers.get("Sec-WebSocket-Protocol", '')
        subprotocols = [s.strip() for s in subprotocols.split(',')]
        if subprotocols:
            selected = self.handler.select_subprotocol(subprotocols)
            if selected:
                assert selected in subprotocols
                subprotocol_header = "Sec-WebSocket-Protocol: %s\r\n" % selected

        self.stream.write(tornado.escape.utf8(
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            "%s"
            "\r\n" % (self._challenge_response(), subprotocol_header)))

        self.async_callback(self.handler.open)(*self.handler.open_args, **self.handler.open_kwargs)
        self._receive_frame()

    def _write_frame(self, fin, opcode, data):
        if fin:
            finbit = 0x80
        else:
            finbit = 0
        frame = struct.pack("B", finbit | opcode)
        l = len(data)
        if self.mask_outgoing:
            mask_bit = 0x80
        else:
            mask_bit = 0
        if l < 126:
            frame += struct.pack("B", l | mask_bit)
        elif l <= 0xFFFF:
            frame += struct.pack("!BH", 126 | mask_bit, l)
        else:
            frame += struct.pack("!BQ", 127 | mask_bit, l)
        if self.mask_outgoing:
            mask = os.urandom(4)
            data = mask + self._apply_mask(mask, data)
        frame += data
        self.stream.write(frame)

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket."""
        if binary:
            opcode = 0x2
        else:
            opcode = 0x1
        message = tornado.escape.utf8(message)
        assert isinstance(message, bytes_type)
        try:
            self._write_frame(True, opcode, message)
        except StreamClosedError:
            self._abort()

    def write_ping(self, data):
        """Send ping frame."""
        assert isinstance(data, bytes_type)
        self._write_frame(True, 0x9, data)

    def _receive_frame(self):
        try:
            self.stream.read_bytes(2, self._on_frame_start)
        except StreamClosedError:
            self._abort()

    def _on_frame_start(self, data):
        header, payloadlen = struct.unpack("BB", data)
        self._final_frame = header & 0x80
        reserved_bits = header & 0x70
        self._frame_opcode = header & 0xf
        self._frame_opcode_is_control = self._frame_opcode & 0x8
        if reserved_bits:
            # client is using as-yet-undefined extensions; abort
            self._abort()
            return
        self._masked_frame = bool(payloadlen & 0x80)
        payloadlen = payloadlen & 0x7f
        if self._frame_opcode_is_control and payloadlen >= 126:
            # control frames must have payload < 126
            self._abort()
            return
        try:
            if payloadlen < 126:
                self._frame_length = payloadlen
                if self._masked_frame:
                    self.stream.read_bytes(4, self._on_masking_key)
                else:
                    self.stream.read_bytes(self._frame_length, self._on_frame_data)
            elif payloadlen == 126:
                self.stream.read_bytes(2, self._on_frame_length_16)
            elif payloadlen == 127:
                self.stream.read_bytes(8, self._on_frame_length_64)
        except StreamClosedError:
            self._abort()

    def _on_frame_length_16(self, data):
        self._frame_length = struct.unpack("!H", data)[0]
        try:
            if self._masked_frame:
                self.stream.read_bytes(4, self._on_masking_key)
            else:
                self.stream.read_bytes(self._frame_length, self._on_frame_data)
        except StreamClosedError:
            self._abort()

    def _on_frame_length_64(self, data):
        self._frame_length = struct.unpack("!Q", data)[0]
        try:
            if self._masked_frame:
                self.stream.read_bytes(4, self._on_masking_key)
            else:
                self.stream.read_bytes(self._frame_length, self._on_frame_data)
        except StreamClosedError:
            self._abort()

    def _on_masking_key(self, data):
        self._frame_mask = data
        try:
            self.stream.read_bytes(self._frame_length, self._on_masked_frame_data)
        except StreamClosedError:
            self._abort()

    def _apply_mask(self, mask, data):
        mask = array.array("B", mask)
        unmasked = array.array("B", data)
        for i in xrange(len(data)):
            unmasked[i] = unmasked[i] ^ mask[i % 4]
        if hasattr(unmasked, 'tobytes'):
            # tostring was deprecated in py32.  It hasn't been removed,
            # but since we turn on deprecation warnings in our tests
            # we need to use the right one.
            return unmasked.tobytes()
        else:
            return unmasked.tostring()

    def _on_masked_frame_data(self, data):
        self._on_frame_data(self._apply_mask(self._frame_mask, data))

    def _on_frame_data(self, data):
        if self._frame_opcode_is_control:
            # control frames may be interleaved with a series of fragmented
            # data frames, so control frames must not interact with
            # self._fragmented_*
            if not self._final_frame:
                # control frames must not be fragmented
                self._abort()
                return
            opcode = self._frame_opcode
        elif self._frame_opcode == 0:  # continuation frame
            if self._fragmented_message_buffer is None:
                # nothing to continue
                self._abort()
                return
            self._fragmented_message_buffer += data
            if self._final_frame:
                opcode = self._fragmented_message_opcode
                data = self._fragmented_message_buffer
                self._fragmented_message_buffer = None
        else:  # start of new data message
            if self._fragmented_message_buffer is not None:
                # can't start new message until the old one is finished
                self._abort()
                return
            if self._final_frame:
                opcode = self._frame_opcode
            else:
                self._fragmented_message_opcode = self._frame_opcode
                self._fragmented_message_buffer = data

        if self._final_frame:
            self._handle_message(opcode, data)

        if not self.client_terminated:
            self._receive_frame()

    def _handle_message(self, opcode, data):
        if self.client_terminated:
            return

        if opcode == 0x1:
            # UTF-8 data
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                self._abort()
                return
            self.async_callback(self.handler.on_message)(decoded)
        elif opcode == 0x2:
            # Binary data
            self.async_callback(self.handler.on_message)(data)
        elif opcode == 0x8:
            # Close
            self.client_terminated = True
            self.close()
        elif opcode == 0x9:
            # Ping
            self._write_frame(True, 0xA, data)
        elif opcode == 0xA:
            # Pong
            self.async_callback(self.handler.on_pong)(data)
        else:
            self._abort()

    def close(self):
        """Closes the WebSocket connection."""
        if not self.server_terminated:
            if not self.stream.closed():
                self._write_frame(True, 0x8, b"")
            self.server_terminated = True
        if self.client_terminated:
            if self._waiting is not None:
                self.stream.io_loop.remove_timeout(self._waiting)
                self._waiting = None
            self.stream.close()
        elif self._waiting is None:
            # Give the client a few seconds to complete a clean shutdown,
            # otherwise just close the connection.
            self._waiting = self.stream.io_loop.add_timeout(
                self.stream.io_loop.time() + 5, self._abort)


class WebSocketClientConnection(simple_httpclient._HTTPConnection):
    """WebSocket client connection."""
    def __init__(self, io_loop, request):
        self.connect_future = Future()
        self.read_future = None
        self.read_queue = collections.deque()
        self.key = base64.b64encode(os.urandom(16))

        scheme, sep, rest = request.url.partition(':')
        scheme = {'ws': 'http', 'wss': 'https'}[scheme]
        request.url = scheme + sep + rest
        request.headers.update({
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': self.key,
            'Sec-WebSocket-Version': '13',
        })

        self.resolver = Resolver(io_loop=io_loop)
        super(WebSocketClientConnection, self).__init__(
            io_loop, None, request, lambda: None, self._on_http_response,
            104857600, self.resolver)

    def _on_close(self):
        self.on_message(None)
        self.resolver.close()

    def _on_http_response(self, response):
        if not self.connect_future.done():
            if response.error:
                self.connect_future.set_exception(response.error)
            else:
                self.connect_future.set_exception(WebSocketError(
                    "Non-websocket response"))

    def _handle_1xx(self, code):
        assert code == 101
        assert self.headers['Upgrade'].lower() == 'websocket'
        assert self.headers['Connection'].lower() == 'upgrade'
        accept = WebSocketProtocol13.compute_accept_value(self.key)
        assert self.headers['Sec-Websocket-Accept'] == accept

        self.protocol = WebSocketProtocol13(self, mask_outgoing=True)
        self.protocol._receive_frame()

        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

        self.connect_future.set_result(self)

    def write_message(self, message, binary=False):
        """Sends a message to the WebSocket server."""
        self.protocol.write_message(message, binary)

    def read_message(self, callback=None):
        """Reads a message from the WebSocket server.

        Returns a future whose result is the message, or None
        if the connection is closed.  If a callback argument
        is given it will be called with the future when it is
        ready.
        """
        assert self.read_future is None
        future = Future()
        if self.read_queue:
            future.set_result(self.read_queue.popleft())
        else:
            self.read_future = future
        if callback is not None:
            self.io_loop.add_future(future, callback)
        return future

    def on_message(self, message):
        if self.read_future is not None:
            self.read_future.set_result(message)
            self.read_future = None
        else:
            self.read_queue.append(message)

    def on_pong(self, data):
        pass


def websocket_connect(url, io_loop=None, callback=None, connect_timeout=None):
    """Client-side websocket support.

    Takes a url and returns a Future whose result is a
    `WebSocketClientConnection`.
    """
    if io_loop is None:
        io_loop = IOLoop.current()
    request = httpclient.HTTPRequest(url, connect_timeout=connect_timeout)
    request = httpclient._RequestProxy(
        request, httpclient.HTTPRequest._DEFAULTS)
    conn = WebSocketClientConnection(io_loop, request)
    if callback is not None:
        io_loop.add_future(conn.connect_future, callback)
    return conn.connect_future

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""WSGI support for the Tornado web framework.

WSGI is the Python standard for web servers, and allows for interoperability
between Tornado and other Python web frameworks and servers.  This module
provides WSGI support in two ways:

* `WSGIApplication` is a version of `tornado.web.Application` that can run
  inside a WSGI server.  This is useful for running a Tornado app on another
  HTTP server, such as Google App Engine.  See the `WSGIApplication` class
  documentation for limitations that apply.
* `WSGIContainer` lets you run other WSGI applications and frameworks on the
  Tornado HTTP server.  For example, with this class you can mix Django
  and Tornado handlers in a single server.
"""

from __future__ import absolute_import, division, print_function, with_statement

import sys
import time
import tornado

from tornado import escape
from tornado import httputil
from tornado.log import access_log
from tornado import web
from tornado.escape import native_str, parse_qs_bytes
from tornado.util import bytes_type, unicode_type

try:
    from io import BytesIO  # python 3
except ImportError:
    from cStringIO import StringIO as BytesIO  # python 2

try:
    import Cookie  # py2
except ImportError:
    import http.cookies as Cookie  # py3

try:
    import urllib.parse as urllib_parse  # py3
except ImportError:
    import urllib as urllib_parse

# PEP 3333 specifies that WSGI on python 3 generally deals with byte strings
# that are smuggled inside objects of type unicode (via the latin1 encoding).
# These functions are like those in the tornado.escape module, but defined
# here to minimize the temptation to use them in non-wsgi contexts.
if str is unicode_type:
    def to_wsgi_str(s):
        assert isinstance(s, bytes_type)
        return s.decode('latin1')

    def from_wsgi_str(s):
        assert isinstance(s, str)
        return s.encode('latin1')
else:
    def to_wsgi_str(s):
        assert isinstance(s, bytes_type)
        return s

    def from_wsgi_str(s):
        assert isinstance(s, str)
        return s


class WSGIApplication(web.Application):
    """A WSGI equivalent of `tornado.web.Application`.

    `WSGIApplication` is very similar to `tornado.web.Application`,
    except no asynchronous methods are supported (since WSGI does not
    support non-blocking requests properly). If you call
    ``self.flush()`` or other asynchronous methods in your request
    handlers running in a `WSGIApplication`, we throw an exception.

    Example usage::

        import tornado.web
        import tornado.wsgi
        import wsgiref.simple_server

        class MainHandler(tornado.web.RequestHandler):
            def get(self):
                self.write("Hello, world")

        if __name__ == "__main__":
            application = tornado.wsgi.WSGIApplication([
                (r"/", MainHandler),
            ])
            server = wsgiref.simple_server.make_server('', 8888, application)
            server.serve_forever()

    See the `appengine demo
    <https://github.com/facebook/tornado/tree/master/demos/appengine>`_
    for an example of using this module to run a Tornado app on Google
    App Engine.

    WSGI applications use the same `.RequestHandler` class, but not
    ``@asynchronous`` methods or ``flush()``.  This means that it is
    not possible to use `.AsyncHTTPClient`, or the `tornado.auth` or
    `tornado.websocket` modules.
    """
    def __init__(self, handlers=None, default_host="", **settings):
        web.Application.__init__(self, handlers, default_host, transforms=[],
                                 wsgi=True, **settings)

    def __call__(self, environ, start_response):
        handler = web.Application.__call__(self, HTTPRequest(environ))
        assert handler._finished
        reason = handler._reason
        status = str(handler._status_code) + " " + reason
        headers = list(handler._headers.get_all())
        if hasattr(handler, "_new_cookie"):
            for cookie in handler._new_cookie.values():
                headers.append(("Set-Cookie", cookie.OutputString(None)))
        start_response(status,
                       [(native_str(k), native_str(v)) for (k, v) in headers])
        return handler._write_buffer


class HTTPRequest(object):
    """Mimics `tornado.httpserver.HTTPRequest` for WSGI applications."""
    def __init__(self, environ):
        """Parses the given WSGI environment to construct the request."""
        self.method = environ["REQUEST_METHOD"]
        self.path = urllib_parse.quote(from_wsgi_str(environ.get("SCRIPT_NAME", "")))
        self.path += urllib_parse.quote(from_wsgi_str(environ.get("PATH_INFO", "")))
        self.uri = self.path
        self.arguments = {}
        self.query = environ.get("QUERY_STRING", "")
        if self.query:
            self.uri += "?" + self.query
            self.arguments = parse_qs_bytes(native_str(self.query),
                                            keep_blank_values=True)
        self.version = "HTTP/1.1"
        self.headers = httputil.HTTPHeaders()
        if environ.get("CONTENT_TYPE"):
            self.headers["Content-Type"] = environ["CONTENT_TYPE"]
        if environ.get("CONTENT_LENGTH"):
            self.headers["Content-Length"] = environ["CONTENT_LENGTH"]
        for key in environ:
            if key.startswith("HTTP_"):
                self.headers[key[5:].replace("_", "-")] = environ[key]
        if self.headers.get("Content-Length"):
            self.body = environ["wsgi.input"].read(
                int(self.headers["Content-Length"]))
        else:
            self.body = ""
        self.protocol = environ["wsgi.url_scheme"]
        self.remote_ip = environ.get("REMOTE_ADDR", "")
        if environ.get("HTTP_HOST"):
            self.host = environ["HTTP_HOST"]
        else:
            self.host = environ["SERVER_NAME"]

        # Parse request body
        self.files = {}
        httputil.parse_body_arguments(self.headers.get("Content-Type", ""),
                                      self.body, self.arguments, self.files)

        self._start_time = time.time()
        self._finish_time = None

    def supports_http_1_1(self):
        """Returns True if this request supports HTTP/1.1 semantics"""
        return self.version == "HTTP/1.1"

    @property
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.SimpleCookie()
            if "Cookie" in self.headers:
                try:
                    self._cookies.load(
                        native_str(self.headers["Cookie"]))
                except Exception:
                    self._cookies = None
        return self._cookies

    def full_url(self):
        """Reconstructs the full URL for this request."""
        return self.protocol + "://" + self.host + self.uri

    def request_time(self):
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time


class WSGIContainer(object):
    r"""Makes a WSGI-compatible function runnable on Tornado's HTTP server.

    Wrap a WSGI function in a `WSGIContainer` and pass it to `.HTTPServer` to
    run it. For example::

        def simple_app(environ, start_response):
            status = "200 OK"
            response_headers = [("Content-type", "text/plain")]
            start_response(status, response_headers)
            return ["Hello world!\n"]

        container = tornado.wsgi.WSGIContainer(simple_app)
        http_server = tornado.httpserver.HTTPServer(container)
        http_server.listen(8888)
        tornado.ioloop.IOLoop.instance().start()

    This class is intended to let other frameworks (Django, web.py, etc)
    run on the Tornado HTTP server and I/O loop.

    The `tornado.web.FallbackHandler` class is often useful for mixing
    Tornado and WSGI apps in the same server.  See
    https://github.com/bdarnell/django-tornado-demo for a complete example.
    """
    def __init__(self, wsgi_application):
        self.wsgi_application = wsgi_application

    def __call__(self, request):
        data = {}
        response = []

        def start_response(status, response_headers, exc_info=None):
            data["status"] = status
            data["headers"] = response_headers
            return response.append
        app_response = self.wsgi_application(
            WSGIContainer.environ(request), start_response)
        response.extend(app_response)
        body = b"".join(response)
        if hasattr(app_response, "close"):
            app_response.close()
        if not data:
            raise Exception("WSGI app did not call start_response")

        status_code = int(data["status"].split()[0])
        headers = data["headers"]
        header_set = set(k.lower() for (k, v) in headers)
        body = escape.utf8(body)
        if status_code != 304:
            if "content-length" not in header_set:
                headers.append(("Content-Length", str(len(body))))
            if "content-type" not in header_set:
                headers.append(("Content-Type", "text/html; charset=UTF-8"))
        if "server" not in header_set:
            headers.append(("Server", "TornadoServer/%s" % tornado.version))

        parts = [escape.utf8("HTTP/1.1 " + data["status"] + "\r\n")]
        for key, value in headers:
            parts.append(escape.utf8(key) + b": " + escape.utf8(value) + b"\r\n")
        parts.append(b"\r\n")
        parts.append(body)
        request.write(b"".join(parts))
        request.finish()
        self._log(status_code, request)

    @staticmethod
    def environ(request):
        """Converts a `tornado.httpserver.HTTPRequest` to a WSGI environment.
        """
        hostport = request.host.split(":")
        if len(hostport) == 2:
            host = hostport[0]
            port = int(hostport[1])
        else:
            host = request.host
            port = 443 if request.protocol == "https" else 80
        environ = {
            "REQUEST_METHOD": request.method,
            "SCRIPT_NAME": "",
            "PATH_INFO": to_wsgi_str(escape.url_unescape(
            request.path, encoding=None, plus=False)),
            "QUERY_STRING": request.query,
            "REMOTE_ADDR": request.remote_ip,
            "SERVER_NAME": host,
            "SERVER_PORT": str(port),
            "SERVER_PROTOCOL": request.version,
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": request.protocol,
            "wsgi.input": BytesIO(escape.utf8(request.body)),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
        }
        if "Content-Type" in request.headers:
            environ["CONTENT_TYPE"] = request.headers.pop("Content-Type")
        if "Content-Length" in request.headers:
            environ["CONTENT_LENGTH"] = request.headers.pop("Content-Length")
        for key, value in request.headers.items():
            environ["HTTP_" + key.replace("-", "_").upper()] = value
        return environ

    def _log(self, status_code, request):
        if status_code < 400:
            log_method = access_log.info
        elif status_code < 500:
            log_method = access_log.warning
        else:
            log_method = access_log.error
        request_time = 1000.0 * request.request_time()
        summary = request.method + " " + request.uri + " (" + \
            request.remote_ip + ")"
        log_method("%d %s %.2fms", status_code, summary, request_time)

########NEW FILE########
