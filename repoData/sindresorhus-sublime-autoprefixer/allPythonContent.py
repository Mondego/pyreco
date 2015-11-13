__FILENAME__ = Autoprefixer
import sublime
import sublime_plugin
from os.path import dirname, realpath, join

try:
	# Python 2
	from node_bridge import node_bridge
except:
	from .node_bridge import node_bridge

# monkeypatch `Region` to be iterable
sublime.Region.totuple = lambda self: (self.a, self.b)
sublime.Region.__iter__ = lambda self: self.totuple().__iter__()

BIN_PATH = join(sublime.packages_path(), dirname(realpath(__file__)), 'autoprefixer.js')

class AutoprefixerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.browsers = ','.join(self.get_setting('browsers'))
		if not self.has_selection():
			region = sublime.Region(0, self.view.size())
			originalBuffer = self.view.substr(region)
			prefixed = self.prefix(originalBuffer)
			if prefixed:
				self.view.replace(edit, region, prefixed)
			return
		for region in self.view.sel():
			if region.empty():
				continue
			originalBuffer = self.view.substr(region)
			prefixed = self.prefix(originalBuffer)
			if prefixed:
				self.view.replace(edit, region, prefixed)

	def prefix(self, data):
		try:
			return node_bridge(data, BIN_PATH, [self.browsers])
		except Exception as e:
			sublime.error_message('Autoprefixer\n%s' % e)

	def has_selection(self):
		for sel in self.view.sel():
			start, end = sel
			if start != end:
				return True
		return False

	def get_setting(self, key):
		settings = self.view.settings().get('Autoprefixer')
		if settings is None:
			settings = sublime.load_settings('Autoprefixer.sublime-settings')
		return settings.get(key)

########NEW FILE########
__FILENAME__ = node_bridge
import os
import platform
from subprocess import Popen, PIPE

IS_OSX = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'

def node_bridge(data, bin, args=[]):
	env = None
	if IS_OSX:
		# GUI apps in OS X doesn't contain .bashrc/.zshrc set paths
		env = os.environ.copy()
		env['PATH'] += ':/usr/local/bin'
	try:
		p = Popen(['node', bin] + args,
			stdout=PIPE, stdin=PIPE, stderr=PIPE,
			env=env, shell=IS_WINDOWS)
	except OSError:
		raise Exception('Couldn\'t find Node.js. Make sure it\'s in your $PATH by running `node -v` in your command-line.')
	stdout, stderr = p.communicate(input=data.encode('utf-8'))
	stdout = stdout.decode('utf-8')
	stderr = stderr.decode('utf-8')
	if stderr:
		raise Exception('Error: %s' % stderr)
	else:
		return stdout

########NEW FILE########
