__FILENAME__ = conf
# vim:fileencoding=utf-8:noet

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(os.getcwd()))))
sys.path.insert(0, os.path.abspath(os.getcwd()))

extensions = ['powerline_autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']
source_suffix = '.rst'
master_doc = 'index'
project = u'Powerline'
copyright = u'Kim Silkebækken'
version = 'beta'
release = 'beta'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']

########NEW FILE########
__FILENAME__ = powerline_autodoc
# vim:fileencoding=utf-8:noet
from sphinx.ext import autodoc
from inspect import formatargspec
from powerline.lint.inspect import getconfigargspec
from powerline.lib.threaded import ThreadedSegment

try:
	from __builtin__ import unicode
except ImportError:
	unicode = lambda s, enc: s  # NOQA


def formatvalue(val):
	if type(val) is str:
		return '="' + unicode(val, 'utf-8').replace('"', '\\"').replace('\\', '\\\\') + '"'
	else:
		return '=' + repr(val)


class ThreadedDocumenter(autodoc.FunctionDocumenter):
	'''Specialized documenter subclass for ThreadedSegment subclasses.'''
	@classmethod
	def can_document_member(cls, member, membername, isattr, parent):
		return (isinstance(member, ThreadedSegment) or
			super(ThreadedDocumenter, cls).can_document_member(member, membername, isattr, parent))

	def format_args(self):
		argspec = getconfigargspec(self.object)
		return formatargspec(*argspec, formatvalue=formatvalue).replace('\\', '\\\\')


def setup(app):
	autodoc.setup(app)
	app.add_autodocumenter(ThreadedDocumenter)

########NEW FILE########
__FILENAME__ = powerline-awesome
#!/usr/bin/env python
# vim:fileencoding=utf-8:noet

from powerline import Powerline
import sys
from time import sleep
from powerline.lib.monotonic import monotonic
from subprocess import Popen, PIPE

powerline = Powerline('wm', renderer_module='pango_markup')
powerline.update_renderer()

try:
	interval = float(sys.argv[1])
except IndexError:
	interval = 2


def read_to_log(pl, client):
	for line in client.stdout:
		if line:
			pl.info(line, prefix='awesome-client')
	for line in client.stderr:
		if line:
			pl.error(line, prefix='awesome-client')
	if client.wait():
		pl.error('Client exited with {0}', client.returncode, prefix='awesome')


while True:
	start_time = monotonic()
	s = powerline.render(side='right')
	request = "powerline_widget:set_markup('" + s.replace('\\', '\\\\').replace("'", "\\'") + "')\n"
	client = Popen(['awesome-client'], shell=False, stdout=PIPE, stderr=PIPE, stdin=PIPE)
	client.stdin.write(request.encode('utf-8'))
	client.stdin.close()
	read_to_log(powerline.pl, client)
	sleep(max(interval - (monotonic() - start_time), 0.1))

########NEW FILE########
__FILENAME__ = powerline-i3
#!/usr/bin/env python
# vim:fileencoding=utf-8:noet
from __future__ import print_function

from powerline import Powerline
from powerline.lib.monotonic import monotonic

import sys
import time
import i3
from threading import Lock


if __name__ == '__main__':
	name = 'wm'
	if len(sys.argv) > 1:
		name = sys.argv[1]

	powerline = Powerline(name, renderer_module='i3bar')
	powerline.update_renderer()

	interval = 0.5

	print ('{"version": 1, "custom_workspace": true}')
	print ('[')
	print ('\t[[],[]]')

	lock = Lock()

	def render(event=None, data=None, sub=None):
		global lock
		with lock:
			s = '[\n' + powerline.render(side='right')[:-2] + '\n]\n'
			s += ',[\n' + powerline.render(side='left')[:-2] + '\n]'
			print (',[\n' + s + '\n]')
			sys.stdout.flush()

	sub = i3.Subscription(render, 'workspace')

	while True:
		start_time = monotonic()
		render()
		time.sleep(max(interval - (monotonic() - start_time), 0.1))

########NEW FILE########
__FILENAME__ = post_0_11
# vim:fileencoding=utf-8:noet
from powerline.ipython import IpythonPowerline

from IPython.core.prompts import PromptManager
from IPython.core.hooks import TryNext


class IpythonInfo(object):
	def __init__(self, shell):
		self._shell = shell

	@property
	def prompt_count(self):
		return self._shell.execution_count


class PowerlinePromptManager(PromptManager):
	powerline = None

	def __init__(self, powerline, shell):
		self.powerline = powerline
		self.powerline_segment_info = IpythonInfo(shell)
		self.shell = shell

	def render(self, name, color=True, *args, **kwargs):
		width = None if name == 'in' else self.width
		res, res_nocolor = self.powerline.render(output_raw=True, width=width, matcher_info=name, segment_info=self.powerline_segment_info)
		self.txtwidth = len(res_nocolor)
		self.width = self.txtwidth
		return res if color else res_nocolor


class ConfigurableIpythonPowerline(IpythonPowerline):
	def __init__(self, ip):
		config = ip.config.Powerline
		self.config_overrides = config.get('config_overrides')
		self.theme_overrides = config.get('theme_overrides', {})
		self.path = config.get('path')
		super(ConfigurableIpythonPowerline, self).__init__()


old_prompt_manager = None


def load_ipython_extension(ip):
	global old_prompt_manager

	old_prompt_manager = ip.prompt_manager
	powerline = ConfigurableIpythonPowerline(ip)

	ip.prompt_manager = PowerlinePromptManager(powerline=powerline, shell=ip.prompt_manager.shell)

	def shutdown_hook():
		powerline.shutdown()
		raise TryNext()

	ip.hooks.shutdown_hook.add(shutdown_hook)


def unload_ipython_extension(ip):
	ip.prompt_manager = old_prompt_manager

########NEW FILE########
__FILENAME__ = pre_0_11
# vim:fileencoding=utf-8:noet
from powerline.ipython import IpythonPowerline
from IPython.Prompts import BasePrompt
from IPython.ipapi import get as get_ipython
from IPython.ipapi import TryNext

import re


def string(s):
	if type(s) is not str:
		return s.encode('utf-8')
	else:
		return s


# HACK: ipython tries to only leave us with plain ASCII
class RewriteResult(object):
	def __init__(self, prompt):
		self.prompt = string(prompt)

	def __str__(self):
		return self.prompt

	def __add__(self, s):
		if type(s) is not str:
			try:
				s = s.encode('utf-8')
			except AttributeError:
				raise NotImplementedError
		return RewriteResult(self.prompt + s)


class IpythonInfo(object):
	def __init__(self, cache):
		self._cache = cache

	@property
	def prompt_count(self):
		return self._cache.prompt_count


class PowerlinePrompt(BasePrompt):
	def __init__(self, powerline, powerline_last_in, old_prompt):
		self.powerline = powerline
		self.powerline_last_in = powerline_last_in
		self.powerline_segment_info = IpythonInfo(old_prompt.cache)
		self.cache = old_prompt.cache
		if hasattr(old_prompt, 'sep'):
			self.sep = old_prompt.sep
		self.pad_left = False

	def __str__(self):
		self.set_p_str()
		return string(self.p_str)

	def set_p_str(self, width=None):
		self.p_str, self.p_str_nocolor = (
			self.powerline.render(output_raw=True,
								segment_info=self.powerline_segment_info,
								matcher_info=self.powerline_prompt_type,
								width=width)
		)

	@staticmethod
	def set_colors():
		pass


class PowerlinePrompt1(PowerlinePrompt):
	powerline_prompt_type = 'in'
	rspace = re.compile(r'(\s*)$')

	def __str__(self):
		self.cache.prompt_count += 1
		self.set_p_str()
		self.cache.last_prompt = self.p_str_nocolor.split('\n')[-1]
		return string(self.p_str)

	def set_p_str(self):
		super(PowerlinePrompt1, self).set_p_str()
		self.nrspaces = len(self.rspace.search(self.p_str_nocolor).group())
		self.prompt_text_len = len(self.p_str_nocolor) - self.nrspaces
		self.powerline_last_in['nrspaces'] = self.nrspaces
		self.powerline_last_in['prompt_text_len'] = self.prompt_text_len

	def auto_rewrite(self):
		return RewriteResult(self.powerline.render(matcher_info='rewrite', width=self.prompt_text_len, segment_info=self.powerline_segment_info)
						+ (' ' * self.nrspaces))


class PowerlinePromptOut(PowerlinePrompt):
	powerline_prompt_type = 'out'

	def set_p_str(self):
		super(PowerlinePromptOut, self).set_p_str(width=self.powerline_last_in['prompt_text_len'])
		spaces = ' ' * self.powerline_last_in['nrspaces']
		self.p_str += spaces
		self.p_str_nocolor += spaces


class PowerlinePrompt2(PowerlinePromptOut):
	powerline_prompt_type = 'in2'


class ConfigurableIpythonPowerline(IpythonPowerline):
	def __init__(self, config_overrides=None, theme_overrides={}, path=None):
		self.config_overrides = config_overrides
		self.theme_overrides = theme_overrides
		self.path = path
		super(ConfigurableIpythonPowerline, self).__init__()


def setup(**kwargs):
	ip = get_ipython()

	powerline = ConfigurableIpythonPowerline(**kwargs)

	def late_startup_hook():
		last_in = {'nrspaces': 0, 'prompt_text_len': None}
		for attr, prompt_class in (
			('prompt1', PowerlinePrompt1),
			('prompt2', PowerlinePrompt2),
			('prompt_out', PowerlinePromptOut)
		):
			old_prompt = getattr(ip.IP.outputcache, attr)
			setattr(ip.IP.outputcache, attr, prompt_class(powerline, last_in, old_prompt))
		raise TryNext()

	def shutdown_hook():
		powerline.shutdown()
		raise TryNext()

	ip.IP.hooks.late_startup_hook.add(late_startup_hook)
	ip.IP.hooks.shutdown_hook.add(shutdown_hook)

########NEW FILE########
__FILENAME__ = widget
# vim:fileencoding=utf-8:noet

from libqtile import bar
from libqtile.widget import base

from powerline import Powerline as PowerlineCore


class Powerline(base._TextBox):
	def __init__(self, timeout=2, text=" ", width=bar.CALCULATED, **config):
		base._TextBox.__init__(self, text, width, **config)
		self.timeout_add(timeout, self.update)
		self.powerline = PowerlineCore(ext='wm', renderer_module='pango_markup')

	def update(self):
		if not self.configured:
			return True
		self.text = self.powerline.render(side='right')
		self.bar.draw()
		return True

	def cmd_update(self, text):
		self.update(text)

	def cmd_get(self):
		return self.text

	def _configure(self, qtile, bar):
		base._TextBox._configure(self, qtile, bar)
		self.layout = self.drawer.textlayout(
			self.text,
			self.foreground,
			self.font,
			self.fontsize,
			self.fontshadow,
			markup=True)

########NEW FILE########
__FILENAME__ = colorscheme
# vim:fileencoding=utf-8:noet

from copy import copy


DEFAULT_MODE_KEY = None
ATTR_BOLD = 1
ATTR_ITALIC = 2
ATTR_UNDERLINE = 4


def get_attr_flag(attributes):
	'''Convert an attribute array to a renderer flag.'''
	attr_flag = 0
	if 'bold' in attributes:
		attr_flag |= ATTR_BOLD
	if 'italic' in attributes:
		attr_flag |= ATTR_ITALIC
	if 'underline' in attributes:
		attr_flag |= ATTR_UNDERLINE
	return attr_flag


def pick_gradient_value(grad_list, gradient_level):
	'''Given a list of colors and gradient percent, return a color that should be used.

	Note: gradient level is not checked for being inside [0, 100] interval.
	'''
	return grad_list[int(round(gradient_level * (len(grad_list) - 1) / 100))]


def hl_iter(value):
	if type(value) is list:
		for v in value:
			yield v
	else:
		yield value


class Colorscheme(object):
	def __init__(self, colorscheme_config, colors_config):
		'''Initialize a colorscheme.'''
		self.colors = {}
		self.gradients = {}

		self.groups = colorscheme_config['groups']
		self.translations = colorscheme_config.get('mode_translations', {})

		# Create a dict of color tuples with both a cterm and hex value
		for color_name, color in colors_config['colors'].items():
			try:
				self.colors[color_name] = (color[0], int(color[1], 16))
			except TypeError:
				self.colors[color_name] = (color, cterm_to_hex[color])

		# Create a dict of gradient names with two lists: for cterm and hex 
		# values. Two lists in place of one list of pairs were chosen because 
		# true colors allow more precise gradients.
		for gradient_name, gradient in colors_config['gradients'].items():
			if len(gradient) == 2:
				self.gradients[gradient_name] = (
					(gradient[0], [int(color, 16) for color in gradient[1]]))
			else:
				self.gradients[gradient_name] = (
					(gradient[0], [cterm_to_hex[color] for color in gradient[0]]))

	def get_gradient(self, gradient, gradient_level):
		if gradient in self.gradients:
			return tuple((pick_gradient_value(grad_list, gradient_level) for grad_list in self.gradients[gradient]))
		else:
			return self.colors[gradient]

	def get_highlighting(self, groups, mode, gradient_level=None):
		trans = self.translations.get(mode, {})
		for group in hl_iter(groups):
			if 'groups' in trans and group in trans['groups']:
				try:
					group_props = trans['groups'][group]
				except KeyError:
					continue
				break

			else:
				try:
					group_props = copy(self.groups[group])
				except KeyError:
					continue

				try:
					ctrans = trans['colors']
					for key in ('fg', 'bg'):
						try:
							group_props[key] = ctrans[group_props[key]]
						except KeyError:
							pass
				except KeyError:
					pass

				break
		else:
			raise KeyError('Highlighting groups not found in colorscheme: ' + ', '.join(hl_iter(groups)))

		if gradient_level is None:
			pick_color = self.colors.__getitem__
		else:
			pick_color = lambda gradient: self.get_gradient(gradient, gradient_level)

		return {
			'fg': pick_color(group_props['fg']),
			'bg': pick_color(group_props['bg']),
			'attr': get_attr_flag(group_props.get('attr', [])),
		}


#       0         1         2         3         4         5         6         7         8         9
cterm_to_hex = (
	0x000000, 0xc00000, 0x008000, 0x804000, 0x0000c0, 0xc000c0, 0x008080, 0xc0c0c0, 0x808080, 0xff6060,  # 0
	0x00ff00, 0xffff00, 0x8080ff, 0xff40ff, 0x00ffff, 0xffffff, 0x000000, 0x00005f, 0x000087, 0x0000af,  # 1
	0x0000d7, 0x0000ff, 0x005f00, 0x005f5f, 0x005f87, 0x005faf, 0x005fd7, 0x005fff, 0x008700, 0x00875f,  # 2
	0x008787, 0x0087af, 0x0087d7, 0x0087ff, 0x00af00, 0x00af5f, 0x00af87, 0x00afaf, 0x00afd7, 0x00afff,  # 3
	0x00d700, 0x00d75f, 0x00d787, 0x00d7af, 0x00d7d7, 0x00d7ff, 0x00ff00, 0x00ff5f, 0x00ff87, 0x00ffaf,  # 4
	0x00ffd7, 0x00ffff, 0x5f0000, 0x5f005f, 0x5f0087, 0x5f00af, 0x5f00d7, 0x5f00ff, 0x5f5f00, 0x5f5f5f,  # 5
	0x5f5f87, 0x5f5faf, 0x5f5fd7, 0x5f5fff, 0x5f8700, 0x5f875f, 0x5f8787, 0x5f87af, 0x5f87d7, 0x5f87ff,  # 6
	0x5faf00, 0x5faf5f, 0x5faf87, 0x5fafaf, 0x5fafd7, 0x5fafff, 0x5fd700, 0x5fd75f, 0x5fd787, 0x5fd7af,  # 7
	0x5fd7d7, 0x5fd7ff, 0x5fff00, 0x5fff5f, 0x5fff87, 0x5fffaf, 0x5fffd7, 0x5fffff, 0x870000, 0x87005f,  # 8
	0x870087, 0x8700af, 0x8700d7, 0x8700ff, 0x875f00, 0x875f5f, 0x875f87, 0x875faf, 0x875fd7, 0x875fff,  # 9
	0x878700, 0x87875f, 0x878787, 0x8787af, 0x8787d7, 0x8787ff, 0x87af00, 0x87af5f, 0x87af87, 0x87afaf,  # 10
	0x87afd7, 0x87afff, 0x87d700, 0x87d75f, 0x87d787, 0x87d7af, 0x87d7d7, 0x87d7ff, 0x87ff00, 0x87ff5f,  # 11
	0x87ff87, 0x87ffaf, 0x87ffd7, 0x87ffff, 0xaf0000, 0xaf005f, 0xaf0087, 0xaf00af, 0xaf00d7, 0xaf00ff,  # 12
	0xaf5f00, 0xaf5f5f, 0xaf5f87, 0xaf5faf, 0xaf5fd7, 0xaf5fff, 0xaf8700, 0xaf875f, 0xaf8787, 0xaf87af,  # 13
	0xaf87d7, 0xaf87ff, 0xafaf00, 0xafaf5f, 0xafaf87, 0xafafaf, 0xafafd7, 0xafafff, 0xafd700, 0xafd75f,  # 14
	0xafd787, 0xafd7af, 0xafd7d7, 0xafd7ff, 0xafff00, 0xafff5f, 0xafff87, 0xafffaf, 0xafffd7, 0xafffff,  # 15
	0xd70000, 0xd7005f, 0xd70087, 0xd700af, 0xd700d7, 0xd700ff, 0xd75f00, 0xd75f5f, 0xd75f87, 0xd75faf,  # 16
	0xd75fd7, 0xd75fff, 0xd78700, 0xd7875f, 0xd78787, 0xd787af, 0xd787d7, 0xd787ff, 0xd7af00, 0xd7af5f,  # 17
	0xd7af87, 0xd7afaf, 0xd7afd7, 0xd7afff, 0xd7d700, 0xd7d75f, 0xd7d787, 0xd7d7af, 0xd7d7d7, 0xd7d7ff,  # 18
	0xd7ff00, 0xd7ff5f, 0xd7ff87, 0xd7ffaf, 0xd7ffd7, 0xd7ffff, 0xff0000, 0xff005f, 0xff0087, 0xff00af,  # 19
	0xff00d7, 0xff00ff, 0xff5f00, 0xff5f5f, 0xff5f87, 0xff5faf, 0xff5fd7, 0xff5fff, 0xff8700, 0xff875f,  # 20
	0xff8787, 0xff87af, 0xff87d7, 0xff87ff, 0xffaf00, 0xffaf5f, 0xffaf87, 0xffafaf, 0xffafd7, 0xffafff,  # 21
	0xffd700, 0xffd75f, 0xffd787, 0xffd7af, 0xffd7d7, 0xffd7ff, 0xffff00, 0xffff5f, 0xffff87, 0xffffaf,  # 22
	0xffffd7, 0xffffff, 0x080808, 0x121212, 0x1c1c1c, 0x262626, 0x303030, 0x3a3a3a, 0x444444, 0x4e4e4e,  # 23
	0x585858, 0x626262, 0x6c6c6c, 0x767676, 0x808080, 0x8a8a8a, 0x949494, 0x9e9e9e, 0xa8a8a8, 0xb2b2b2,  # 24
	0xbcbcbc, 0xc6c6c6, 0xd0d0d0, 0xdadada, 0xe4e4e4, 0xeeeeee                                           # 25
)

########NEW FILE########
__FILENAME__ = ipython
# vim:fileencoding=utf-8:noet

from powerline import Powerline
from powerline.lib import mergedicts


class IpythonPowerline(Powerline):
	def __init__(self):
		super(IpythonPowerline, self).__init__('ipython', use_daemon_threads=True)

	def get_config_paths(self):
		if self.path:
			return [self.path]
		else:
			return super(IpythonPowerline, self).get_config_paths()

	def get_local_themes(self, local_themes):
		return dict(((type, {'config': self.load_theme_config(name)}) for type, name in local_themes.items()))

	def load_main_config(self):
		r = super(IpythonPowerline, self).load_main_config()
		if self.config_overrides:
			mergedicts(r, self.config_overrides)
		return r

	def load_theme_config(self, name):
		r = super(IpythonPowerline, self).load_theme_config(name)
		if name in self.theme_overrides:
			mergedicts(r, self.theme_overrides[name])
		return r

########NEW FILE########
__FILENAME__ = config
# vim:fileencoding=utf-8:noet

from powerline.lib.threaded import MultiRunnedThread
from powerline.lib.file_watcher import create_file_watcher
from copy import deepcopy

from threading import Event, Lock
from collections import defaultdict

import json
import codecs


def open_file(path):
	return codecs.open(path, encoding='utf-8')


def load_json_config(config_file_path, load=json.load, open_file=open_file):
	with open_file(config_file_path) as config_file_fp:
		return load(config_file_fp)


class DummyWatcher(object):
	def __call__(self, *args, **kwargs):
		return False

	def watch(self, *args, **kwargs):
		pass


class ConfigLoader(MultiRunnedThread):
	def __init__(self, shutdown_event=None, watcher=None, load=load_json_config, run_once=False):
		super(ConfigLoader, self).__init__()
		self.shutdown_event = shutdown_event or Event()
		if run_once:
			self.watcher = DummyWatcher()
		else:
			self.watcher = watcher or create_file_watcher()
		self._load = load

		self.pl = None
		self.interval = None

		self.lock = Lock()

		self.watched = defaultdict(set)
		self.missing = defaultdict(set)
		self.loaded = {}

	def set_pl(self, pl):
		self.pl = pl

	def set_interval(self, interval):
		self.interval = interval

	def register(self, function, path):
		'''Register function that will be run when file changes.

		:param function function:
			Function that will be called when file at the given path changes.
		:param str path:
			Path that will be watched for.
		'''
		with self.lock:
			self.watched[path].add(function)
			self.watcher.watch(path)

	def register_missing(self, condition_function, function, key):
		'''Register any function that will be called with given key each 
		interval seconds (interval is defined at __init__). Its result is then 
		passed to ``function``, but only if the result is true.

		:param function condition_function:
			Function which will be called each ``interval`` seconds. All 
			exceptions from it will be ignored.
		:param function function:
			Function which will be called if condition_function returns 
			something that is true. Accepts result of condition_function as an 
			argument.
		:param str key:
			Any value, it will be passed to condition_function on each call.

		Note: registered functions will be automatically removed if 
		condition_function results in something true.
		'''
		with self.lock:
			self.missing[key].add((condition_function, function))

	def unregister_functions(self, removed_functions):
		'''Unregister files handled by these functions.

		:param set removed_functions:
			Set of functions previously passed to ``.register()`` method.
		'''
		with self.lock:
			for path, functions in list(self.watched.items()):
				functions -= removed_functions
				if not functions:
					self.watched.pop(path)
					self.loaded.pop(path, None)

	def unregister_missing(self, removed_functions):
		'''Unregister files handled by these functions.

		:param set removed_functions:
			Set of pairs (2-tuples) representing ``(condition_function, 
			function)`` function pairs previously passed as an arguments to 
			``.register_missing()`` method.
		'''
		with self.lock:
			for key, functions in list(self.missing.items()):
				functions -= removed_functions
				if not functions:
					self.missing.pop(key)

	def load(self, path):
		try:
			# No locks: GIL does what we need
			return deepcopy(self.loaded[path])
		except KeyError:
			r = self._load(path)
			self.loaded[path] = deepcopy(r)
			return r

	def update(self):
		toload = []
		with self.lock:
			for path, functions in self.watched.items():
				for function in functions:
					try:
						modified = self.watcher(path)
					except OSError as e:
						modified = True
						self.exception('Error while running watcher for path {0}: {1}', path, str(e))
					else:
						if modified:
							toload.append(path)
					if modified:
						function(path)
		with self.lock:
			for key, functions in list(self.missing.items()):
				for condition_function, function in list(functions):
					try:
						path = condition_function(key)
					except Exception as e:
						self.exception('Error while running condition function for key {0}: {1}', key, str(e))
					else:
						if path:
							toload.append(path)
							function(path)
							functions.remove((condition_function, function))
				if not functions:
					self.missing.pop(key)
		for path in toload:
			try:
				self.loaded[path] = deepcopy(self._load(path))
			except Exception as e:
				try:
					self.loaded.pop(path)
				except KeyError:
					pass
				self.exception('Error while loading {0}: {1}', path, str(e))

	def run(self):
		while self.interval is not None and not self.shutdown_event.is_set():
			self.update()
			self.shutdown_event.wait(self.interval)

	def exception(self, msg, *args, **kwargs):
		if self.pl:
			self.pl.exception(msg, prefix='config_loader', *args, **kwargs)
		else:
			raise

########NEW FILE########
__FILENAME__ = file_watcher
# vim:fileencoding=utf-8:noet
from __future__ import unicode_literals, absolute_import

__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import os
import sys
import errno
from time import sleep
from threading import RLock

from powerline.lib.monotonic import monotonic
from powerline.lib.inotify import INotify, INotifyError


def realpath(path):
	return os.path.abspath(os.path.realpath(path))


class INotifyWatch(INotify):
	is_stat_based = False

	def __init__(self, expire_time=10):
		super(INotifyWatch, self).__init__()
		self.watches = {}
		self.modified = {}
		self.last_query = {}
		self.lock = RLock()
		self.expire_time = expire_time * 60

	def expire_watches(self):
		now = monotonic()
		for path, last_query in tuple(self.last_query.items()):
			if last_query - now > self.expire_time:
				self.unwatch(path)

	def process_event(self, wd, mask, cookie, name):
		if wd == -1 and (mask & self.Q_OVERFLOW):
			# We missed some INOTIFY events, so we dont
			# know the state of any tracked files.
			for path in tuple(self.modified):
				if os.path.exists(path):
					self.modified[path] = True
				else:
					self.watches.pop(path, None)
					self.modified.pop(path, None)
					self.last_query.pop(path, None)
			return

		for path, num in tuple(self.watches.items()):
			if num == wd:
				if mask & self.IGNORED:
					self.watches.pop(path, None)
					self.modified.pop(path, None)
					self.last_query.pop(path, None)
				else:
					if mask & self.ATTRIB:
						# The watched file could have had its inode changed, in
						# which case we will not get any more events for this
						# file, so re-register the watch. For example by some
						# other file being renamed as this file.
						try:
							self.unwatch(path)
						except OSError:
							pass
						try:
							self.watch(path)
						except OSError as e:
							if getattr(e, 'errno', None) != errno.ENOENT:
								raise
						else:
							self.modified[path] = True
					else:
						self.modified[path] = True

	def unwatch(self, path):
		''' Remove the watch for path. Raises an OSError if removing the watch
		fails for some reason. '''
		path = realpath(path)
		with self.lock:
			self.modified.pop(path, None)
			self.last_query.pop(path, None)
			wd = self.watches.pop(path, None)
			if wd is not None:
				if self._rm_watch(self._inotify_fd, wd) != 0:
					self.handle_error()

	def watch(self, path):
		''' Register a watch for the file/directory named path. Raises an OSError if path
		does not exist. '''
		import ctypes
		path = realpath(path)
		with self.lock:
			if path not in self.watches:
				bpath = path if isinstance(path, bytes) else path.encode(self.fenc)
				flags = self.MOVE_SELF | self.DELETE_SELF
				buf = ctypes.c_char_p(bpath)
				# Try watching path as a directory
				wd = self._add_watch(self._inotify_fd, buf, flags | self.ONLYDIR)
				if wd == -1:
					eno = ctypes.get_errno()
					if eno != errno.ENOTDIR:
						self.handle_error()
					# Try watching path as a file
					flags |= (self.MODIFY | self.ATTRIB)
					wd = self._add_watch(self._inotify_fd, buf, flags)
					if wd == -1:
						self.handle_error()
				self.watches[path] = wd
				self.modified[path] = False

	def is_watched(self, path):
		with self.lock:
			return realpath(path) in self.watches

	def __call__(self, path):
		''' Return True if path has been modified since the last call. Can
		raise OSError if the path does not exist. '''
		path = realpath(path)
		with self.lock:
			self.last_query[path] = monotonic()
			self.expire_watches()
			if path not in self.watches:
				# Try to re-add the watch, it will fail if the file does not
				# exist/you dont have permission
				self.watch(path)
				return True
			self.read(get_name=False)
			if path not in self.modified:
				# An ignored event was received which means the path has been
				# automatically unwatched
				return True
			ans = self.modified[path]
			if ans:
				self.modified[path] = False
			return ans

	def close(self):
		with self.lock:
			for path in tuple(self.watches):
				try:
					self.unwatch(path)
				except OSError:
					pass
			super(INotifyWatch, self).close()


class StatWatch(object):
	is_stat_based = True

	def __init__(self):
		self.watches = {}
		self.lock = RLock()

	def watch(self, path):
		path = realpath(path)
		with self.lock:
			self.watches[path] = os.path.getmtime(path)

	def unwatch(self, path):
		path = realpath(path)
		with self.lock:
			self.watches.pop(path, None)

	def is_watched(self, path):
		with self.lock:
			return realpath(path) in self.watches

	def __call__(self, path):
		path = realpath(path)
		with self.lock:
			if path not in self.watches:
				self.watches[path] = os.path.getmtime(path)
				return True
			mtime = os.path.getmtime(path)
			if mtime != self.watches[path]:
				self.watches[path] = mtime
				return True
			return False

	def close(self):
		with self.lock:
			self.watches.clear()


def create_file_watcher(use_stat=False, expire_time=10):
	'''
	Create an object that can watch for changes to specified files. To use:

	watcher = create_file_watcher()
	watcher(path1) # Will return True if path1 has changed since the last time this was called. Always returns True the first time.
	watcher.unwatch(path1)

	Uses inotify if available, otherwise tracks mtimes. expire_time is the
	number of minutes after the last query for a given path for the inotify
	watch for that path to be automatically removed. This conserves kernel
	resources.
	'''
	if use_stat:
		return StatWatch()
	try:
		return INotifyWatch(expire_time=expire_time)
	except INotifyError:
		pass
	return StatWatch()

if __name__ == '__main__':
	watcher = create_file_watcher()
	print ('Using watcher: %s' % watcher.__class__.__name__)
	print ('Watching %s, press Ctrl-C to quit' % sys.argv[-1])
	watcher.watch(sys.argv[-1])
	try:
		while True:
			if watcher(sys.argv[-1]):
				print ('%s has changed' % sys.argv[-1])
			sleep(1)
	except KeyboardInterrupt:
		pass
	watcher.close()

########NEW FILE########
__FILENAME__ = humanize_bytes
# vim:fileencoding=utf-8:noet

from math import log
unit_list = tuple(zip(['', 'k', 'M', 'G', 'T', 'P'], [0, 0, 1, 2, 2, 2]))


def humanize_bytes(num, suffix='B', si_prefix=False):
	'''Return a human friendly byte representation.

	Modified version from http://stackoverflow.com/questions/1094841
	'''
	if num == 0:
		return '0 ' + suffix
	div = 1000 if si_prefix else 1024
	exponent = min(int(log(num, div)) if num else 0, len(unit_list) - 1)
	quotient = float(num) / div ** exponent
	unit, decimals = unit_list[exponent]
	if unit and not si_prefix:
		unit = unit.upper() + 'i'
	return ('{{quotient:.{decimals}f}} {{unit}}{{suffix}}'
		.format(decimals=decimals)
		.format(quotient=quotient, unit=unit, suffix=suffix))

########NEW FILE########
__FILENAME__ = inotify
# vim:fileencoding=utf-8:noet
from __future__ import unicode_literals, absolute_import

__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import sys
import os
import errno


class INotifyError(Exception):
	pass


_inotify = None


def load_inotify():
	''' Initialize the inotify library '''
	global _inotify
	if _inotify is None:
		if hasattr(sys, 'getwindowsversion'):
			# On windows abort before loading the C library. Windows has
			# multiple, incompatible C runtimes, and we have no way of knowing
			# if the one chosen by ctypes is compatible with the currently
			# loaded one.
			raise INotifyError('INotify not available on windows')
		if sys.platform == 'darwin':
			raise INotifyError('INotify not available on OS X')
		import ctypes
		if not hasattr(ctypes, 'c_ssize_t'):
			raise INotifyError('You need python >= 2.7 to use inotify')
		from ctypes.util import find_library
		name = find_library('c')
		if not name:
			raise INotifyError('Cannot find C library')
		libc = ctypes.CDLL(name, use_errno=True)
		for function in ("inotify_add_watch", "inotify_init1", "inotify_rm_watch"):
			if not hasattr(libc, function):
				raise INotifyError('libc is too old')
		# inotify_init1()
		prototype = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, use_errno=True)
		init1 = prototype(('inotify_init1', libc), ((1, "flags", 0),))

		# inotify_add_watch()
		prototype = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32, use_errno=True)
		add_watch = prototype(('inotify_add_watch', libc), (
			(1, "fd"), (1, "pathname"), (1, "mask")), use_errno=True)

		# inotify_rm_watch()
		prototype = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, use_errno=True)
		rm_watch = prototype(('inotify_rm_watch', libc), (
			(1, "fd"), (1, "wd")), use_errno=True)

		# read()
		prototype = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, use_errno=True)
		read = prototype(('read', libc), (
			(1, "fd"), (1, "buf"), (1, "count")), use_errno=True)
		_inotify = (init1, add_watch, rm_watch, read)
	return _inotify


class INotify(object):

	# See <sys/inotify.h> for the flags defined below

	# Supported events suitable for MASK parameter of INOTIFY_ADD_WATCH.
	ACCESS = 0x00000001         # File was accessed.
	MODIFY = 0x00000002         # File was modified.
	ATTRIB = 0x00000004         # Metadata changed.
	CLOSE_WRITE = 0x00000008    # Writtable file was closed.
	CLOSE_NOWRITE = 0x00000010  # Unwrittable file closed.
	OPEN = 0x00000020           # File was opened.
	MOVED_FROM = 0x00000040     # File was moved from X.
	MOVED_TO = 0x00000080       # File was moved to Y.
	CREATE = 0x00000100         # Subfile was created.
	DELETE = 0x00000200         # Subfile was deleted.
	DELETE_SELF = 0x00000400    # Self was deleted.
	MOVE_SELF = 0x00000800      # Self was moved.

	# Events sent by the kernel.
	UNMOUNT = 0x00002000     # Backing fs was unmounted.
	Q_OVERFLOW = 0x00004000  # Event queued overflowed.
	IGNORED = 0x00008000     # File was ignored.

	# Helper events.
	CLOSE = (CLOSE_WRITE | CLOSE_NOWRITE)  # Close.
	MOVE = (MOVED_FROM | MOVED_TO)         # Moves.

	# Special flags.
	ONLYDIR = 0x01000000      # Only watch the path if it is a directory.
	DONT_FOLLOW = 0x02000000  # Do not follow a sym link.
	EXCL_UNLINK = 0x04000000  # Exclude events on unlinked objects.
	MASK_ADD = 0x20000000     # Add to the mask of an already existing watch.
	ISDIR = 0x40000000        # Event occurred against dir.
	ONESHOT = 0x80000000      # Only send event once.

	# All events which a program can wait on.
	ALL_EVENTS = (ACCESS | MODIFY | ATTRIB | CLOSE_WRITE | CLOSE_NOWRITE |
					OPEN | MOVED_FROM | MOVED_TO | CREATE | DELETE |
					DELETE_SELF | MOVE_SELF)

	# See <bits/inotify.h>
	CLOEXEC = 0x80000
	NONBLOCK = 0x800

	def __init__(self, cloexec=True, nonblock=True):
		import ctypes
		import struct
		self._init1, self._add_watch, self._rm_watch, self._read = load_inotify()
		flags = 0
		if cloexec:
			flags |= self.CLOEXEC
		if nonblock:
			flags |= self.NONBLOCK
		self._inotify_fd = self._init1(flags)
		if self._inotify_fd == -1:
			raise INotifyError(os.strerror(ctypes.get_errno()))

		self._buf = ctypes.create_string_buffer(5000)
		self.fenc = sys.getfilesystemencoding() or 'utf-8'
		self.hdr = struct.Struct(b'iIII')
		if self.fenc == 'ascii':
			self.fenc = 'utf-8'
		# We keep a reference to os to prevent it from being deleted
		# during interpreter shutdown, which would lead to errors in the
		# __del__ method
		self.os = os

	def handle_error(self):
		import ctypes
		eno = ctypes.get_errno()
		extra = ''
		if eno == errno.ENOSPC:
			extra = 'You may need to increase the inotify limits on your system, via /proc/sys/inotify/max_user_*'
		raise OSError(eno, self.os.strerror(eno) + str(extra))

	def __del__(self):
		# This method can be called during interpreter shutdown, which means we
		# must do the absolute minimum here. Note that there could be running
		# daemon threads that are trying to call other methods on this object.
		try:
			self.os.close(self._inotify_fd)
		except (AttributeError, TypeError):
			pass

	def close(self):
		if hasattr(self, '_inotify_fd'):
			self.os.close(self._inotify_fd)
			del self.os
			del self._add_watch
			del self._rm_watch
			del self._inotify_fd

	def read(self, get_name=True):
		import ctypes
		buf = []
		while True:
			num = self._read(self._inotify_fd, self._buf, len(self._buf))
			if num == 0:
				break
			if num < 0:
				en = ctypes.get_errno()
				if en == errno.EAGAIN:
					break  # No more data
				if en == errno.EINTR:
					continue  # Interrupted, try again
				raise OSError(en, self.os.strerror(en))
			buf.append(self._buf.raw[:num])
		raw = b''.join(buf)
		pos = 0
		lraw = len(raw)
		while lraw - pos >= self.hdr.size:
			wd, mask, cookie, name_len = self.hdr.unpack_from(raw, pos)
			pos += self.hdr.size
			name = None
			if get_name:
				name = raw[pos:pos + name_len].rstrip(b'\0').decode(self.fenc)
			pos += name_len
			self.process_event(wd, mask, cookie, name)

	def process_event(self, *args):
		raise NotImplementedError()

########NEW FILE########
__FILENAME__ = memoize
# vim:fileencoding=utf-8:noet

from functools import wraps
from powerline.lib.monotonic import monotonic


def default_cache_key(**kwargs):
	return frozenset(kwargs.items())


class memoize(object):
	'''Memoization decorator with timeout.'''
	def __init__(self, timeout, cache_key=default_cache_key, cache_reg_func=None):
		self.timeout = timeout
		self.cache_key = cache_key
		self.cache = {}
		self.cache_reg_func = cache_reg_func

	def __call__(self, func):
		@wraps(func)
		def decorated_function(**kwargs):
			if self.cache_reg_func:
				self.cache_reg_func(self.cache)
				self.cache_reg_func = None

			key = self.cache_key(**kwargs)
			try:
				cached = self.cache.get(key, None)
			except TypeError:
				return func(**kwargs)
			# Handle case when time() appears to be less then cached['time'] due 
			# to clock updates. Not applicable for monotonic clock, but this 
			# case is currently rare.
			if cached is None or not (cached['time'] < monotonic() < cached['time'] + self.timeout):
				cached = self.cache[key] = {
					'result': func(**kwargs),
					'time': monotonic(),
					}
			return cached['result']
		return decorated_function

########NEW FILE########
__FILENAME__ = monotonic
# vim:fileencoding=utf-8:noet

from __future__ import division, absolute_import

try:
	try:
		# >=python-3.3, Unix
		from time import clock_gettime
		try:
			# >={kernel}-sources-2.6.28
			from time import CLOCK_MONOTONIC_RAW as CLOCK_ID
		except ImportError:
			from time import CLOCK_MONOTONIC as CLOCK_ID  # NOQA

		monotonic = lambda: clock_gettime(CLOCK_ID)

	except ImportError:
		# >=python-3.3
		from time import monotonic  # NOQA

except ImportError:
	import ctypes
	import sys

	try:
		if sys.platform == 'win32':
			# Windows only
			GetTickCount64 = ctypes.windll.kernel32.GetTickCount64
			GetTickCount64.restype = ctypes.c_ulonglong

			def monotonic():  # NOQA
				return GetTickCount64() / 1000

		elif sys.platform == 'darwin':
			# Mac OS X
			from ctypes.util import find_library

			libc_name = find_library('c')
			if not libc_name:
				raise OSError

			libc = ctypes.CDLL(libc_name, use_errno=True)

			mach_absolute_time = libc.mach_absolute_time
			mach_absolute_time.argtypes = ()
			mach_absolute_time.restype = ctypes.c_uint64

			class mach_timebase_info_data_t(ctypes.Structure):
				_fields_ = (
					('numer', ctypes.c_uint32),
					('denom', ctypes.c_uint32),
				)
			mach_timebase_info_data_p = ctypes.POINTER(mach_timebase_info_data_t)

			_mach_timebase_info = libc.mach_timebase_info
			_mach_timebase_info.argtypes = (mach_timebase_info_data_p,)
			_mach_timebase_info.restype = ctypes.c_int

			def mach_timebase_info():
				timebase = mach_timebase_info_data_t()
				_mach_timebase_info(ctypes.byref(timebase))
				return (timebase.numer, timebase.denom)

			timebase = mach_timebase_info()
			factor = timebase[0] / timebase[1] * 1e-9

			def monotonic():  # NOQA
				return mach_absolute_time() * factor
		else:
			# linux only (no librt on OS X)
			import os

			# See <bits/time.h>
			CLOCK_MONOTONIC = 1
			CLOCK_MONOTONIC_RAW = 4

			class timespec(ctypes.Structure):
				_fields_ = (
					('tv_sec', ctypes.c_long),
					('tv_nsec', ctypes.c_long)
				)
			tspec = timespec()

			librt = ctypes.CDLL('librt.so.1', use_errno=True)
			clock_gettime = librt.clock_gettime
			clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

			if clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.pointer(tspec)) == 0:
				# >={kernel}-sources-2.6.28
				clock_id = CLOCK_MONOTONIC_RAW
			elif clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(tspec)) == 0:
				clock_id = CLOCK_MONOTONIC
			else:
				raise OSError

			def monotonic():  # NOQA
				if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(tspec)) != 0:
					errno_ = ctypes.get_errno()
					raise OSError(errno_, os.strerror(errno_))
				return tspec.tv_sec + tspec.tv_nsec / 1e9

	except:
		from time import time as monotonic  # NOQA

########NEW FILE########
__FILENAME__ = shell
# vim:fileencoding=utf-8:noet

from subprocess import Popen, PIPE


def run_cmd(pl, cmd, stdin=None):
	try:
		p = Popen(cmd, stdout=PIPE, stdin=PIPE)
	except OSError as e:
		pl.exception('Could not execute command ({0}): {1}', e, cmd)
		return None
	else:
		stdout, err = p.communicate(stdin)
	return stdout.strip()


def asrun(pl, ascript):
	'''Run the given AppleScript and return the standard output and error.'''
	return run_cmd(pl, ['osascript', '-'], ascript)

########NEW FILE########
__FILENAME__ = threaded
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import

from powerline.lib.monotonic import monotonic

from threading import Thread, Lock, Event


class MultiRunnedThread(object):
	daemon = True

	def __init__(self):
		self.thread = None

	def is_alive(self):
		return self.thread and self.thread.is_alive()

	def start(self):
		self.shutdown_event.clear()
		self.thread = Thread(target=self.run)
		self.thread.daemon = self.daemon
		self.thread.start()

	def join(self, *args, **kwargs):
		if self.thread:
			return self.thread.join(*args, **kwargs)
		return None


class ThreadedSegment(MultiRunnedThread):
	min_sleep_time = 0.1
	update_first = True
	interval = 1
	daemon = False

	def __init__(self):
		super(ThreadedSegment, self).__init__()
		self.run_once = True
		self.crashed = False
		self.crashed_value = None
		self.update_value = None
		self.updated = False

	def __call__(self, pl, update_first=True, **kwargs):
		if self.run_once:
			self.pl = pl
			self.set_state(**kwargs)
			update_value = self.get_update_value(True)
		elif not self.is_alive():
			# Without this we will not have to wait long until receiving bug “I 
			# opened vim, but branch information is only shown after I move 
			# cursor”.
			#
			# If running once .update() is called in __call__.
			self.start()
			update_value = self.get_update_value(self.do_update_first)
		else:
			update_value = self.get_update_value(not self.updated)

		if self.crashed:
			return self.crashed_value

		return self.render(update_value, update_first=update_first, pl=pl, **kwargs)

	def set_update_value(self):
		try:
			self.update_value = self.update(self.update_value)
		except Exception as e:
			self.exception('Exception while updating: {0}', str(e))
			self.crashed = True
		except KeyboardInterrupt:
			self.warn('Caught keyboard interrupt while updating')
			self.crashed = True
		else:
			self.crashed = False
			self.updated = True

	def get_update_value(self, update=False):
		if update:
			self.set_update_value()
		return self.update_value

	def run(self):
		if self.do_update_first:
			start_time = monotonic()
			while True:
				self.shutdown_event.wait(max(self.interval - (monotonic() - start_time), self.min_sleep_time))
				if self.shutdown_event.is_set():
					break
				start_time = monotonic()
				self.set_update_value()
		else:
			while not self.shutdown_event.is_set():
				start_time = monotonic()
				self.set_update_value()
				self.shutdown_event.wait(max(self.interval - (monotonic() - start_time), self.min_sleep_time))

	def shutdown(self):
		self.shutdown_event.set()
		if self.daemon and self.is_alive():
			# Give the worker thread a chance to shutdown, but don't block for 
			# too long
			self.join(0.01)

	def set_interval(self, interval=None):
		# Allowing “interval” keyword in configuration.
		# Note: Here **kwargs is needed to support foreign data, in subclasses 
		# it can be seen in a number of places in order to support 
		# .set_interval().
		interval = interval or getattr(self, 'interval')
		self.interval = interval

	def set_state(self, interval=None, update_first=True, shutdown_event=None, **kwargs):
		self.set_interval(interval)
		self.shutdown_event = shutdown_event or Event()
		self.do_update_first = update_first and self.update_first
		self.updated = self.updated or (not self.do_update_first)

	def startup(self, pl, **kwargs):
		self.run_once = False
		self.pl = pl
		self.daemon = pl.use_daemon_threads

		self.set_state(**kwargs)

		if not self.is_alive():
			self.start()

	def critical(self, *args, **kwargs):
		self.pl.critical(prefix=self.__class__.__name__, *args, **kwargs)

	def exception(self, *args, **kwargs):
		self.pl.exception(prefix=self.__class__.__name__, *args, **kwargs)

	def info(self, *args, **kwargs):
		self.pl.info(prefix=self.__class__.__name__, *args, **kwargs)

	def error(self, *args, **kwargs):
		self.pl.error(prefix=self.__class__.__name__, *args, **kwargs)

	def warn(self, *args, **kwargs):
		self.pl.warn(prefix=self.__class__.__name__, *args, **kwargs)

	def debug(self, *args, **kwargs):
		self.pl.debug(prefix=self.__class__.__name__, *args, **kwargs)


class KwThreadedSegment(ThreadedSegment):
	update_first = True

	def __init__(self):
		super(KwThreadedSegment, self).__init__()
		self.updated = True
		self.update_value = ({}, set())
		self.write_lock = Lock()
		self.new_queries = []

	@staticmethod
	def key(**kwargs):
		return frozenset(kwargs.items())

	def render(self, update_value, update_first, key=None, after_update=False, **kwargs):
		queries, crashed = update_value
		if key is None:
			key = self.key(**kwargs)
		if key in crashed:
			return self.crashed_value

		try:
			update_state = queries[key][1]
		except KeyError:
			with self.write_lock:
				self.new_queries.append(key)
			if self.do_update_first or self.run_once:
				if after_update:
					self.error('internal error: value was not computed even though update_first was set')
					update_state = None
				else:
					return self.render(
						update_value=self.get_update_value(True),
						update_first=False,
						key=key,
						after_update=True,
						**kwargs
					)
			else:
				update_state = None

		return self.render_one(update_state, **kwargs)

	def update_one(self, crashed, updates, key):
		try:
			updates[key] = (monotonic(), self.compute_state(key))
		except Exception as e:
			self.exception('Exception while computing state for {0!r}: {1}', key, str(e))
			crashed.add(key)
		except KeyboardInterrupt:
			self.warn('Interrupt while computing state for {0!r}', key)
			crashed.add(key)

	def update(self, old_update_value):
		updates = {}
		crashed = set()
		update_value = (updates, crashed)
		queries = old_update_value[0]

		new_queries = self.new_queries
		with self.write_lock:
			self.new_queries = []

		for key, (last_query_time, state) in queries.items():
			if last_query_time < monotonic() < last_query_time + self.interval:
				updates[key] = (last_query_time, state)
			else:
				self.update_one(crashed, updates, key)

		for key in new_queries:
			self.update_one(crashed, updates, key)

		return update_value

	def set_state(self, interval=None, update_first=True, shutdown_event=None, **kwargs):
		self.set_interval(interval)
		self.do_update_first = update_first and self.update_first
		self.shutdown_event = shutdown_event or Event()

	@staticmethod
	def render_one(update_state, **kwargs):
		return update_state


def with_docstring(instance, doc):
	instance.__doc__ = doc
	return instance

########NEW FILE########
__FILENAME__ = tree_watcher
# vim:fileencoding=utf-8:noet
from __future__ import (unicode_literals, absolute_import, print_function)

__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import sys
import os
import errno
from time import sleep
from powerline.lib.monotonic import monotonic

from powerline.lib.inotify import INotify, INotifyError


class NoSuchDir(ValueError):
	pass


class BaseDirChanged(ValueError):
	pass


class DirTooLarge(ValueError):
	def __init__(self, bdir):
		ValueError.__init__(self, 'The directory {0} is too large to monitor. Try increasing the value in /proc/sys/fs/inotify/max_user_watches'.format(bdir))


def realpath(path):
	return os.path.abspath(os.path.realpath(path))


class INotifyTreeWatcher(INotify):
	is_dummy = False

	def __init__(self, basedir, ignore_event=None):
		super(INotifyTreeWatcher, self).__init__()
		self.basedir = realpath(basedir)
		self.watch_tree()
		self.modified = True
		self.ignore_event = (lambda path, name: False) if ignore_event is None else ignore_event

	def watch_tree(self):
		self.watched_dirs = {}
		self.watched_rmap = {}
		try:
			self.add_watches(self.basedir)
		except OSError as e:
			if e.errno == errno.ENOSPC:
				raise DirTooLarge(self.basedir)

	def add_watches(self, base, top_level=True):
		''' Add watches for this directory and all its descendant directories,
		recursively. '''
		base = realpath(base)
		# There may exist a link which leads to an endless
		# add_watches loop or to maximum recursion depth exceeded
		if not top_level and base in self.watched_dirs:
			return
		try:
			is_dir = self.add_watch(base)
		except OSError as e:
			if e.errno == errno.ENOENT:
				# The entry could have been deleted between listdir() and
				# add_watch().
				if top_level:
					raise NoSuchDir('The dir {0} does not exist'.format(base))
				return
			if e.errno == errno.EACCES:
				# We silently ignore entries for which we dont have permission,
				# unless they are the top level dir
				if top_level:
					raise NoSuchDir('You do not have permission to monitor {0}'.format(base))
				return
			raise
		else:
			if is_dir:
				try:
					files = os.listdir(base)
				except OSError as e:
					if e.errno in (errno.ENOTDIR, errno.ENOENT):
						# The dir was deleted/replaced between the add_watch()
						# and listdir()
						if top_level:
							raise NoSuchDir('The dir {0} does not exist'.format(base))
						return
					raise
				for x in files:
					self.add_watches(os.path.join(base, x), top_level=False)
			elif top_level:
				# The top level dir is a file, not good.
				raise NoSuchDir('The dir {0} does not exist'.format(base))

	def add_watch(self, path):
		import ctypes
		bpath = path if isinstance(path, bytes) else path.encode(self.fenc)
		wd = self._add_watch(self._inotify_fd, ctypes.c_char_p(bpath),
				# Ignore symlinks and watch only directories
				self.DONT_FOLLOW | self.ONLYDIR |

				self.MODIFY | self.CREATE | self.DELETE |
				self.MOVE_SELF | self.MOVED_FROM | self.MOVED_TO |
				self.ATTRIB | self.DELETE_SELF)
		if wd == -1:
			eno = ctypes.get_errno()
			if eno == errno.ENOTDIR:
				return False
			raise OSError(eno, 'Failed to add watch for: {0}: {1}'.format(path, self.os.strerror(eno)))
		self.watched_dirs[path] = wd
		self.watched_rmap[wd] = path
		return True

	def process_event(self, wd, mask, cookie, name):
		if wd == -1 and (mask & self.Q_OVERFLOW):
			# We missed some INOTIFY events, so we dont
			# know the state of any tracked dirs.
			self.watch_tree()
			self.modified = True
			return
		path = self.watched_rmap.get(wd, None)
		if path is not None:
			self.modified = not self.ignore_event(path, name)
			if mask & self.CREATE:
				# A new sub-directory might have been created, monitor it.
				try:
					self.add_watch(os.path.join(path, name))
				except OSError as e:
					if e.errno == errno.ENOENT:
						# Deleted before add_watch()
						pass
					elif e.errno == errno.ENOSPC:
						raise DirTooLarge(self.basedir)
					else:
						raise
			if (mask & self.DELETE_SELF or mask & self.MOVE_SELF) and path == self.basedir:
				raise BaseDirChanged('The directory %s was moved/deleted' % path)

	def __call__(self):
		self.read()
		ret = self.modified
		self.modified = False
		return ret


class DummyTreeWatcher(object):
	is_dummy = True

	def __init__(self, basedir):
		self.basedir = realpath(basedir)

	def __call__(self):
		return False


class TreeWatcher(object):
	def __init__(self, expire_time=10):
		self.watches = {}
		self.last_query_times = {}
		self.expire_time = expire_time * 60

	def watch(self, path, logger=None, ignore_event=None):
		path = realpath(path)
		try:
			w = INotifyTreeWatcher(path, ignore_event=ignore_event)
		except (INotifyError, DirTooLarge) as e:
			if logger is not None and not isinstance(e, INotifyError):
				logger.warn('Failed to watch path: {0} with error: {1}'.format(path, e))
			w = DummyTreeWatcher(path)
		self.watches[path] = w
		return w

	def is_actually_watched(self, path):
		w = self.watches.get(path, None)
		return not getattr(w, 'is_dummy', True)

	def expire_old_queries(self):
		pop = []
		now = monotonic()
		for path, lt in self.last_query_times.items():
			if now - lt > self.expire_time:
				pop.append(path)
		for path in pop:
			del self.last_query_times[path]

	def __call__(self, path, logger=None, ignore_event=None):
		path = realpath(path)
		self.expire_old_queries()
		self.last_query_times[path] = monotonic()
		w = self.watches.get(path, None)
		if w is None:
			try:
				self.watch(path, logger=logger, ignore_event=ignore_event)
			except NoSuchDir:
				pass
			return True
		try:
			return w()
		except BaseDirChanged:
			self.watches.pop(path, None)
			return True
		except DirTooLarge as e:
			if logger is not None:
				logger.warn(str(e))
			self.watches[path] = DummyTreeWatcher(path)
			return False


if __name__ == '__main__':
	w = INotifyTreeWatcher(sys.argv[-1])
	w()
	print ('Monitoring', sys.argv[-1], 'press Ctrl-C to stop')
	try:
		while True:
			if w():
				print (sys.argv[-1], 'changed')
			sleep(1)
	except KeyboardInterrupt:
		raise SystemExit(0)

########NEW FILE########
__FILENAME__ = unicode
# vim:fileencoding=utf-8:noet


from locale import getpreferredencoding


try:
	from __builtin__ import unicode
except ImportError:
	unicode = str  # NOQA


def u(s):
	'''Return unicode instance assuming UTF-8 encoded string.
	'''
	if type(s) is unicode:
		return s
	else:
		return unicode(s, 'utf-8')


def safe_unicode(s):
	'''Return unicode instance without raising an exception.

	Order of assumptions:
	* ASCII string or unicode object
	* UTF-8 string
	* Object with __str__() or __repr__() method that returns UTF-8 string or 
	  unicode object (depending on python version)
	* String in locale.getpreferredencoding() encoding
	* If everything failed use safe_unicode on last exception with which 
	  everything failed
	'''
	try:
		try:
			return unicode(s)
		except UnicodeDecodeError:
			try:
				return unicode(s, 'utf-8')
			except TypeError:
				return unicode(str(s), 'utf-8')
			except UnicodeDecodeError:
				return unicode(s, getpreferredencoding())
	except Exception as e:
		return safe_unicode(e)


class FailedUnicode(unicode):
	'''Builtin ``unicode`` (``str`` in python 3) subclass indicating fatal 
	error.

	If your code for some reason wants to determine whether `.render()` method 
	failed it should check returned string for being a FailedUnicode instance. 
	Alternatively you could subclass Powerline and override `.render()` method 
	to do what you like in place of catching the exception and returning 
	FailedUnicode.
	'''
	pass

########NEW FILE########
__FILENAME__ = url
# vim:fileencoding=utf-8:noet

try:
	from urllib.error import HTTPError
	from urllib.request import urlopen
	from urllib.parse import urlencode as urllib_urlencode  # NOQA
except ImportError:
	from urllib2 import urlopen, HTTPError  # NOQA
	from urllib import urlencode as urllib_urlencode  # NOQA


def urllib_read(url):
	try:
		return urlopen(url, timeout=10).read().decode('utf-8')
	except HTTPError:
		return

########NEW FILE########
__FILENAME__ = bzr
# vim:fileencoding=utf-8:noet
from __future__ import absolute_import, unicode_literals, division, print_function

import sys
import os
import re
from io import StringIO

from bzrlib import (workingtree, status, library_state, trace, ui)

from powerline.lib.vcs import get_branch_name, get_file_status


class CoerceIO(StringIO):
	def write(self, arg):
		if isinstance(arg, bytes):
			arg = arg.decode('utf-8', 'replace')
		return super(CoerceIO, self).write(arg)


nick_pat = re.compile(br'nickname\s*=\s*(.+)')


def branch_name_from_config_file(directory, config_file):
	ans = None
	try:
		with open(config_file, 'rb') as f:
			for line in f:
				m = nick_pat.match(line)
				if m is not None:
					ans = m.group(1).strip().decode('utf-8', 'replace')
					break
	except Exception:
		pass
	return ans or os.path.basename(directory)


state = None


class Repository(object):
	def __init__(self, directory):
		if isinstance(directory, bytes):
			directory = directory.decode(sys.getfilesystemencoding() or sys.getdefaultencoding() or 'utf-8')
		self.directory = os.path.abspath(directory)

	def status(self, path=None):
		'''Return status of repository or file.

		Without file argument: returns status of the repository:

		:"D?": dirty (tracked modified files: added, removed, deleted, modified),
		:"?U": untracked-dirty (added, but not tracked files)
		:None: clean (status is empty)

		With file argument: returns status of this file: The status codes are
		those returned by bzr status -S
		'''
		if path is not None:
			return get_file_status(self.directory, os.path.join(self.directory, '.bzr', 'checkout', 'dirstate'),
								path, '.bzrignore', self.do_status)
		return self.do_status(self.directory, path)

	def do_status(self, directory, path):
		try:
			return self._status(self.directory, path)
		except Exception:
			pass

	def _status(self, directory, path):
		global state
		if state is None:
			state = library_state.BzrLibraryState(ui=ui.SilentUIFactory, trace=trace.DefaultConfig())
		buf = CoerceIO()
		w = workingtree.WorkingTree.open(directory)
		status.show_tree_status(w, specific_files=[path] if path else None, to_file=buf, short=True)
		raw = buf.getvalue()
		if not raw.strip():
			return
		if path:
			ans = raw[:2]
			if ans == 'I ':  # Ignored
				ans = None
			return ans
		dirtied = untracked = ' '
		for line in raw.splitlines():
			if len(line) > 1 and line[1] in 'ACDMRIN':
				dirtied = 'D'
			elif line and line[0] == '?':
				untracked = 'U'
		ans = dirtied + untracked
		return ans if ans.strip() else None

	def branch(self):
		config_file = os.path.join(self.directory, '.bzr', 'branch', 'branch.conf')
		return get_branch_name(self.directory, config_file, branch_name_from_config_file)

########NEW FILE########
__FILENAME__ = git
# vim:fileencoding=utf-8:noet

from __future__ import (unicode_literals, absolute_import, print_function)

import os
import sys
import re

from powerline.lib.vcs import get_branch_name as _get_branch_name, get_file_status


_ref_pat = re.compile(br'ref:\s*refs/heads/(.+)')


def branch_name_from_config_file(directory, config_file):
	try:
		with open(config_file, 'rb') as f:
			raw = f.read()
	except EnvironmentError:
		return os.path.basename(directory)
	m = _ref_pat.match(raw)
	if m is not None:
		return m.group(1).decode('utf-8', 'replace')
	return raw[:7]


def git_directory(directory):
	path = os.path.join(directory, '.git')
	if os.path.isfile(path):
		with open(path, 'rb') as f:
			raw = f.read()
			if not raw.startswith(b'gitdir: '):
				raise IOError('invalid gitfile format')
			raw = raw[8:].decode(sys.getfilesystemencoding() or 'utf-8')
			if not raw:
				raise IOError('no path in gitfile')
			return os.path.abspath(os.path.join(directory, raw))
	else:
		return path


def get_branch_name(base_dir):
	head = os.path.join(git_directory(base_dir), 'HEAD')
	return _get_branch_name(base_dir, head, branch_name_from_config_file)


def do_status(directory, path, func):
	if path:
		gitd = git_directory(directory)
		# We need HEAD as without it using fugitive to commit causes the
		# current file's status (and only the current file) to not be updated
		# for some reason I cannot be bothered to figure out.
		return get_file_status(
			directory, os.path.join(gitd, 'index'),
			path, '.gitignore', func, extra_ignore_files=tuple(os.path.join(gitd, x) for x in ('logs/HEAD', 'info/exclude')))
	return func(directory, path)


def ignore_event(path, name):
	# Ignore changes to the index.lock file, since they happen frequently and
	# dont indicate an actual change in the working tree status
	return False
	return path.endswith('.git') and name == 'index.lock'


try:
	import pygit2 as git

	class Repository(object):
		__slots__ = ('directory', 'ignore_event')

		def __init__(self, directory):
			self.directory = os.path.abspath(directory)
			self.ignore_event = ignore_event

		def do_status(self, directory, path):
			if path:
				try:
					status = git.Repository(directory).status_file(path)
				except (KeyError, ValueError):
					return None

				if status == git.GIT_STATUS_CURRENT:
					return None
				else:
					if status & git.GIT_STATUS_WT_NEW:
						return '??'
					if status & git.GIT_STATUS_IGNORED:
						return '!!'

					if status & git.GIT_STATUS_INDEX_NEW:
						index_status = 'A'
					elif status & git.GIT_STATUS_INDEX_DELETED:
						index_status = 'D'
					elif status & git.GIT_STATUS_INDEX_MODIFIED:
						index_status = 'M'
					else:
						index_status = ' '

					if status & git.GIT_STATUS_WT_DELETED:
						wt_status = 'D'
					elif status & git.GIT_STATUS_WT_MODIFIED:
						wt_status = 'M'
					else:
						wt_status = ' '

					return index_status + wt_status
			else:
				wt_column = ' '
				index_column = ' '
				untracked_column = ' '
				for status in git.Repository(directory).status().values():
					if status & git.GIT_STATUS_WT_NEW:
						untracked_column = 'U'
						continue

					if status & (git.GIT_STATUS_WT_DELETED
							| git.GIT_STATUS_WT_MODIFIED):
						wt_column = 'D'

					if status & (git.GIT_STATUS_INDEX_NEW
							| git.GIT_STATUS_INDEX_MODIFIED
							| git.GIT_STATUS_INDEX_DELETED):
						index_column = 'I'
				r = wt_column + index_column + untracked_column
				return r if r != '   ' else None

		def status(self, path=None):
			'''Return status of repository or file.

			Without file argument: returns status of the repository:

			:First column: working directory status (D: dirty / space)
			:Second column: index status (I: index dirty / space)
			:Third column: presence of untracked files (U: untracked files / space)
			:None: repository clean

			With file argument: returns status of this file. Output is
			equivalent to the first two columns of "git status --porcelain"
			(except for merge statuses as they are not supported by libgit2).
			'''
			return do_status(self.directory, path, self.do_status)

		def branch(self):
			return get_branch_name(self.directory)
except ImportError:
	from subprocess import Popen, PIPE

	def readlines(cmd, cwd):
		p = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE, cwd=cwd)
		p.stderr.close()
		with p.stdout:
			for line in p.stdout:
				yield line[:-1].decode('utf-8')

	class Repository(object):
		__slots__ = ('directory', 'ignore_event')

		def __init__(self, directory):
			self.directory = os.path.abspath(directory)
			self.ignore_event = ignore_event

		def _gitcmd(self, directory, *args):
			return readlines(('git',) + args, directory)

		def do_status(self, directory, path):
			if path:
				try:
					return next(self._gitcmd(directory, 'status', '--porcelain', '--ignored', '--', path))[:2]
				except StopIteration:
					return None
			else:
				wt_column = ' '
				index_column = ' '
				untracked_column = ' '
				for line in self._gitcmd(directory, 'status', '--porcelain'):
					if line[0] == '?':
						untracked_column = 'U'
						continue
					elif line[0] == '!':
						continue

					if line[0] != ' ':
						index_column = 'I'

					if line[1] != ' ':
						wt_column = 'D'

				r = wt_column + index_column + untracked_column
				return r if r != '   ' else None

		def status(self, path=None):
			return do_status(self.directory, path, self.do_status)

		def branch(self):
			return get_branch_name(self.directory)

########NEW FILE########
__FILENAME__ = mercurial
# vim:fileencoding=utf-8:noet
from __future__ import absolute_import

import os

from mercurial import hg, ui, match

from powerline.lib.vcs import get_branch_name, get_file_status


def branch_name_from_config_file(directory, config_file):
	try:
		with open(config_file, 'rb') as f:
			raw = f.read()
		return raw.decode('utf-8', 'replace').strip()
	except Exception:
		return 'default'


class Repository(object):
	__slots__ = ('directory', 'ui')

	statuses = 'MARDUI'
	repo_statuses = (1, 1, 1, 1, 2)
	repo_statuses_str = (None, 'D ', ' U', 'DU')

	def __init__(self, directory):
		self.directory = os.path.abspath(directory)
		self.ui = ui.ui()

	def _repo(self, directory):
		# Cannot create this object once and use always: when repository updates
		# functions emit invalid results
		return hg.repository(self.ui, directory)

	def status(self, path=None):
		'''Return status of repository or file.

		Without file argument: returns status of the repository:

		:"D?": dirty (tracked modified files: added, removed, deleted, modified),
		:"?U": untracked-dirty (added, but not tracked files)
		:None: clean (status is empty)

		With file argument: returns status of this file: "M"odified, "A"dded,
		"R"emoved, "D"eleted (removed from filesystem, but still tracked),
		"U"nknown, "I"gnored, (None)Clean.
		'''
		if path:
			return get_file_status(self.directory, os.path.join(self.directory, '.hg', 'dirstate'),
					path, '.hgignore', self.do_status)
		return self.do_status(self.directory, path)

	def do_status(self, directory, path):
		repo = self._repo(directory)
		if path:
			m = match.match(None, None, [path], exact=True)
			statuses = repo.status(match=m, unknown=True, ignored=True)
			for status, paths in zip(self.statuses, statuses):
				if paths:
					return status
			return None
		else:
			resulting_status = 0
			for status, paths in zip(self.repo_statuses, repo.status(unknown=True)):
				if paths:
					resulting_status |= status
			return self.repo_statuses_str[resulting_status]

	def branch(self):
		config_file = os.path.join(self.directory, '.hg', 'branch')
		return get_branch_name(self.directory, config_file, branch_name_from_config_file)

########NEW FILE########
__FILENAME__ = inspect
# vim:fileencoding=utf-8:noet
from __future__ import absolute_import
from inspect import ArgSpec, getargspec
from powerline.lib.threaded import ThreadedSegment, KwThreadedSegment
from itertools import count


def getconfigargspec(obj):
	if isinstance(obj, ThreadedSegment):
		args = ['interval']
		defaults = [getattr(obj, 'interval', 1)]
		if obj.update_first:
			args.append('update_first')
			defaults.append(True)
		methods = ['render', 'set_state']
		if isinstance(obj, KwThreadedSegment):
			methods += ['key', 'render_one']

		for method in methods:
			if hasattr(obj, method):
				# Note: on <python-2.6 it may return simple tuple, not 
				# ArgSpec instance.
				argspec = getargspec(getattr(obj, method))
				for i, arg in zip(count(1), reversed(argspec.args)):
					if (arg == 'self' or
							(arg == 'segment_info' and
								getattr(obj, 'powerline_requires_segment_info', None)) or
							(arg == 'pl') or
							(method.startswith('render') and (1 if argspec.args[0] == 'self' else 0) + i == len(argspec.args)) or
							arg in args):
						continue
					if argspec.defaults and len(argspec.defaults) >= i:
						default = argspec.defaults[-i]
						defaults.append(default)
						args.append(arg)
					else:
						args.insert(0, arg)
		argspec = ArgSpec(args=args, varargs=None, keywords=None, defaults=tuple(defaults))
	else:
		if hasattr(obj, 'powerline_origin'):
			obj = obj.powerline_origin
		else:
			obj = obj

		argspec = getargspec(obj)
		args = []
		defaults = []
		for i, arg in zip(count(1), reversed(argspec.args)):
			if ((arg == 'segment_info' and getattr(obj, 'powerline_requires_segment_info', None)) or
				arg == 'pl'):
				continue
			if argspec.defaults and len(argspec.defaults) >= i:
				default = argspec.defaults[-i]
				defaults.append(default)
				args.append(arg)
			else:
				args.insert(0, arg)
		argspec = ArgSpec(args=args, varargs=argspec.varargs, keywords=argspec.keywords, defaults=tuple(defaults))

	return argspec

########NEW FILE########
__FILENAME__ = composer
__all__ = ['Composer', 'ComposerError']

from .error import MarkedError
from .events import *  # NOQA
from .nodes import *  # NOQA


class ComposerError(MarkedError):
	pass


class Composer:
	def __init__(self):
		pass

	def check_node(self):
		# Drop the STREAM-START event.
		if self.check_event(StreamStartEvent):
			self.get_event()

		# If there are more documents available?
		return not self.check_event(StreamEndEvent)

	def get_node(self):
		# Get the root node of the next document.
		if not self.check_event(StreamEndEvent):
			return self.compose_document()

	def get_single_node(self):
		# Drop the STREAM-START event.
		self.get_event()

		# Compose a document if the stream is not empty.
		document = None
		if not self.check_event(StreamEndEvent):
			document = self.compose_document()

		# Ensure that the stream contains no more documents.
		if not self.check_event(StreamEndEvent):
			event = self.get_event()
			raise ComposerError("expected a single document in the stream",
					document.start_mark, "but found another document",
					event.start_mark)

		# Drop the STREAM-END event.
		self.get_event()

		return document

	def compose_document(self):
		# Drop the DOCUMENT-START event.
		self.get_event()

		# Compose the root node.
		node = self.compose_node(None, None)

		# Drop the DOCUMENT-END event.
		self.get_event()

		return node

	def compose_node(self, parent, index):
		self.descend_resolver(parent, index)
		if self.check_event(ScalarEvent):
			node = self.compose_scalar_node()
		elif self.check_event(SequenceStartEvent):
			node = self.compose_sequence_node()
		elif self.check_event(MappingStartEvent):
			node = self.compose_mapping_node()
		self.ascend_resolver()
		return node

	def compose_scalar_node(self):
		event = self.get_event()
		tag = event.tag
		if tag is None or tag == '!':
			tag = self.resolve(ScalarNode, event.value, event.implicit, event.start_mark)
		node = ScalarNode(tag, event.value,
				event.start_mark, event.end_mark, style=event.style)
		return node

	def compose_sequence_node(self):
		start_event = self.get_event()
		tag = start_event.tag
		if tag is None or tag == '!':
			tag = self.resolve(SequenceNode, None, start_event.implicit)
		node = SequenceNode(tag, [],
				start_event.start_mark, None,
				flow_style=start_event.flow_style)
		index = 0
		while not self.check_event(SequenceEndEvent):
			node.value.append(self.compose_node(node, index))
			index += 1
		end_event = self.get_event()
		node.end_mark = end_event.end_mark
		return node

	def compose_mapping_node(self):
		start_event = self.get_event()
		tag = start_event.tag
		if tag is None or tag == '!':
			tag = self.resolve(MappingNode, None, start_event.implicit)
		node = MappingNode(tag, [],
				start_event.start_mark, None,
				flow_style=start_event.flow_style)
		while not self.check_event(MappingEndEvent):
			#key_event = self.peek_event()
			item_key = self.compose_node(node, None)
			#if item_key in node.value:
			#	 raise ComposerError("while composing a mapping", start_event.start_mark,
			#			 "found duplicate key", key_event.start_mark)
			item_value = self.compose_node(node, item_key)
			#node.value[item_key] = item_value
			node.value.append((item_key, item_value))
		end_event = self.get_event()
		node.end_mark = end_event.end_mark
		return node

########NEW FILE########
__FILENAME__ = constructor
__all__ = ['BaseConstructor', 'Constructor', 'ConstructorError']

from .error import MarkedError
from .nodes import *  # NOQA
from .markedvalue import gen_marked_value

import collections
import types

from functools import wraps


try:
	from __builtin__ import unicode
except ImportError:
	unicode = str  # NOQA


def marked(func):
	@wraps(func)
	def f(self, node, *args, **kwargs):
		return gen_marked_value(func(self, node, *args, **kwargs), node.start_mark)
	return f


class ConstructorError(MarkedError):
	pass


class BaseConstructor:
	yaml_constructors = {}

	def __init__(self):
		self.constructed_objects = {}
		self.state_generators = []
		self.deep_construct = False

	def check_data(self):
		# If there are more documents available?
		return self.check_node()

	def get_data(self):
		# Construct and return the next document.
		if self.check_node():
			return self.construct_document(self.get_node())

	def get_single_data(self):
		# Ensure that the stream contains a single document and construct it.
		node = self.get_single_node()
		if node is not None:
			return self.construct_document(node)
		return None

	def construct_document(self, node):
		data = self.construct_object(node)
		while self.state_generators:
			state_generators = self.state_generators
			self.state_generators = []
			for generator in state_generators:
				for dummy in generator:
					pass
		self.constructed_objects = {}
		self.deep_construct = False
		return data

	def construct_object(self, node, deep=False):
		if node in self.constructed_objects:
			return self.constructed_objects[node]
		if deep:
			old_deep = self.deep_construct
			self.deep_construct = True
		constructor = None
		tag_suffix = None
		if node.tag in self.yaml_constructors:
			constructor = self.yaml_constructors[node.tag]
		else:
			raise ConstructorError(None, None, 'no constructor for tag %s' % node.tag)
		if tag_suffix is None:
			data = constructor(self, node)
		else:
			data = constructor(self, tag_suffix, node)
		if isinstance(data, types.GeneratorType):
			generator = data
			data = next(generator)
			if self.deep_construct:
				for dummy in generator:
					pass
			else:
				self.state_generators.append(generator)
		self.constructed_objects[node] = data
		if deep:
			self.deep_construct = old_deep
		return data

	@marked
	def construct_scalar(self, node):
		if not isinstance(node, ScalarNode):
			raise ConstructorError(None, None,
					"expected a scalar node, but found %s" % node.id,
					node.start_mark)
		return node.value

	def construct_sequence(self, node, deep=False):
		if not isinstance(node, SequenceNode):
			raise ConstructorError(None, None,
					"expected a sequence node, but found %s" % node.id,
					node.start_mark)
		return [self.construct_object(child, deep=deep)
				for child in node.value]

	@marked
	def construct_mapping(self, node, deep=False):
		if not isinstance(node, MappingNode):
			raise ConstructorError(None, None,
					"expected a mapping node, but found %s" % node.id,
					node.start_mark)
		mapping = {}
		for key_node, value_node in node.value:
			key = self.construct_object(key_node, deep=deep)
			if not isinstance(key, collections.Hashable):
				self.echoerr('While constructing a mapping', node.start_mark,
						'found unhashable key', key_node.start_mark)
				continue
			elif type(key.value) != unicode:
				self.echoerr('Error while constructing a mapping', node.start_mark,
						'found key that is not a string', key_node.start_mark)
				continue
			elif key in mapping:
				self.echoerr('Error while constructing a mapping', node.start_mark,
						'found duplicate key', key_node.start_mark)
				continue
			value = self.construct_object(value_node, deep=deep)
			mapping[key] = value
		return mapping

	@classmethod
	def add_constructor(cls, tag, constructor):
		if not 'yaml_constructors' in cls.__dict__:
			cls.yaml_constructors = cls.yaml_constructors.copy()
		cls.yaml_constructors[tag] = constructor


class Constructor(BaseConstructor):
	def construct_scalar(self, node):
		if isinstance(node, MappingNode):
			for key_node, value_node in node.value:
				if key_node.tag == 'tag:yaml.org,2002:value':
					return self.construct_scalar(value_node)
		return BaseConstructor.construct_scalar(self, node)

	def flatten_mapping(self, node):
		merge = []
		index = 0
		while index < len(node.value):
			key_node, value_node = node.value[index]
			if key_node.tag == 'tag:yaml.org,2002:merge':
				del node.value[index]
				if isinstance(value_node, MappingNode):
					self.flatten_mapping(value_node)
					merge.extend(value_node.value)
				elif isinstance(value_node, SequenceNode):
					submerge = []
					for subnode in value_node.value:
						if not isinstance(subnode, MappingNode):
							raise ConstructorError("while constructing a mapping",
									node.start_mark,
									"expected a mapping for merging, but found %s"
									% subnode.id, subnode.start_mark)
						self.flatten_mapping(subnode)
						submerge.append(subnode.value)
					submerge.reverse()
					for value in submerge:
						merge.extend(value)
				else:
					raise ConstructorError("while constructing a mapping", node.start_mark,
							"expected a mapping or list of mappings for merging, but found %s"
							% value_node.id, value_node.start_mark)
			elif key_node.tag == 'tag:yaml.org,2002:value':
				key_node.tag = 'tag:yaml.org,2002:str'
				index += 1
			else:
				index += 1
		if merge:
			node.value = merge + node.value

	def construct_mapping(self, node, deep=False):
		if isinstance(node, MappingNode):
			self.flatten_mapping(node)
		return BaseConstructor.construct_mapping(self, node, deep=deep)

	@marked
	def construct_yaml_null(self, node):
		self.construct_scalar(node)
		return None

	@marked
	def construct_yaml_bool(self, node):
		value = self.construct_scalar(node).value
		return bool(value)

	@marked
	def construct_yaml_int(self, node):
		value = self.construct_scalar(node).value
		sign = +1
		if value[0] == '-':
			sign = -1
		if value[0] in '+-':
			value = value[1:]
		if value == '0':
			return 0
		else:
			return sign * int(value)

	@marked
	def construct_yaml_float(self, node):
		value = self.construct_scalar(node).value
		sign = +1
		if value[0] == '-':
			sign = -1
		if value[0] in '+-':
			value = value[1:]
		else:
			return sign * float(value)

	def construct_yaml_str(self, node):
		return self.construct_scalar(node)

	def construct_yaml_seq(self, node):
		data = gen_marked_value([], node.start_mark)
		yield data
		data.extend(self.construct_sequence(node))

	def construct_yaml_map(self, node):
		data = gen_marked_value({}, node.start_mark)
		yield data
		value = self.construct_mapping(node)
		data.update(value)

	def construct_undefined(self, node):
		raise ConstructorError(None, None,
				"could not determine a constructor for the tag %r" % node.tag,
				node.start_mark)


Constructor.add_constructor(
		'tag:yaml.org,2002:null',
		Constructor.construct_yaml_null)

Constructor.add_constructor(
		'tag:yaml.org,2002:bool',
		Constructor.construct_yaml_bool)

Constructor.add_constructor(
		'tag:yaml.org,2002:int',
		Constructor.construct_yaml_int)

Constructor.add_constructor(
		'tag:yaml.org,2002:float',
		Constructor.construct_yaml_float)

Constructor.add_constructor(
		'tag:yaml.org,2002:str',
		Constructor.construct_yaml_str)

Constructor.add_constructor(
		'tag:yaml.org,2002:seq',
		Constructor.construct_yaml_seq)

Constructor.add_constructor(
		'tag:yaml.org,2002:map',
		Constructor.construct_yaml_map)

Constructor.add_constructor(None,
		Constructor.construct_undefined)

########NEW FILE########
__FILENAME__ = error
__all__ = ['Mark', 'MarkedError', 'echoerr', 'NON_PRINTABLE']


import sys
import re

try:
	from __builtin__ import unichr
except ImportError:
	unichr = chr  # NOQA


NON_PRINTABLE = re.compile('[^\t\n\x20-\x7E' + unichr(0x85) + (unichr(0xA0) + '-' + unichr(0xD7FF)) + (unichr(0xE000) + '-' + unichr(0xFFFD)) + ']')


def repl(s):
	return '<x%04x>' % ord(s.group())


def strtrans(s):
	return NON_PRINTABLE.sub(repl, s.replace('\t', '>---'))


class Mark:
	def __init__(self, name, line, column, buffer, pointer):
		self.name = name
		self.line = line
		self.column = column
		self.buffer = buffer
		self.pointer = pointer

	def copy(self):
		return Mark(self.name, self.line, self.column, self.buffer, self.pointer)

	def get_snippet(self, indent=4, max_length=75):
		if self.buffer is None:
			return None
		head = ''
		start = self.pointer
		while start > 0 and self.buffer[start - 1] not in '\0\n':
			start -= 1
			if self.pointer - start > max_length / 2 - 1:
				head = ' ... '
				start += 5
				break
		tail = ''
		end = self.pointer
		while end < len(self.buffer) and self.buffer[end] not in '\0\n':
			end += 1
			if end - self.pointer > max_length / 2 - 1:
				tail = ' ... '
				end -= 5
				break
		snippet = [self.buffer[start:self.pointer], self.buffer[self.pointer], self.buffer[self.pointer + 1:end]]
		snippet = [strtrans(s) for s in snippet]
		return (' ' * indent + head + ''.join(snippet) + tail + '\n'
				+ ' ' * (indent + len(head) + len(snippet[0])) + '^')

	def __str__(self):
		snippet = self.get_snippet()
		where = ("  in \"%s\", line %d, column %d"
				% (self.name, self.line + 1, self.column + 1))
		if snippet is not None:
			where += ":\n" + snippet
		if type(where) is str:
			return where
		else:
			return where.encode('utf-8')


def echoerr(*args, **kwargs):
	sys.stderr.write('\n')
	sys.stderr.write(format_error(*args, **kwargs) + '\n')


def format_error(context=None, context_mark=None, problem=None, problem_mark=None, note=None):
	lines = []
	if context is not None:
		lines.append(context)
	if context_mark is not None  \
		and (problem is None or problem_mark is None
				or context_mark.name != problem_mark.name
				or context_mark.line != problem_mark.line
				or context_mark.column != problem_mark.column):
		lines.append(str(context_mark))
	if problem is not None:
		lines.append(problem)
	if problem_mark is not None:
		lines.append(str(problem_mark))
	if note is not None:
		lines.append(note)
	return '\n'.join(lines)


class MarkedError(Exception):
	def __init__(self, context=None, context_mark=None,
			problem=None, problem_mark=None, note=None):
		Exception.__init__(self, format_error(context, context_mark, problem,
										problem_mark, note))

########NEW FILE########
__FILENAME__ = events
# Abstract classes.


class Event(object):
	def __init__(self, start_mark=None, end_mark=None):
		self.start_mark = start_mark
		self.end_mark = end_mark

	def __repr__(self):
		attributes = [key for key in ['implicit', 'value']
				if hasattr(self, key)]
		arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
				for key in attributes])
		return '%s(%s)' % (self.__class__.__name__, arguments)


class NodeEvent(Event):
	def __init__(self, start_mark=None, end_mark=None):
		self.start_mark = start_mark
		self.end_mark = end_mark


class CollectionStartEvent(NodeEvent):
	def __init__(self, implicit, start_mark=None, end_mark=None,
			flow_style=None):
		self.tag = None
		self.implicit = implicit
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.flow_style = flow_style


class CollectionEndEvent(Event):
	pass


# Implementations.


class StreamStartEvent(Event):
	def __init__(self, start_mark=None, end_mark=None, encoding=None):
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.encoding = encoding


class StreamEndEvent(Event):
	pass


class DocumentStartEvent(Event):
	def __init__(self, start_mark=None, end_mark=None,
			explicit=None, version=None, tags=None):
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.explicit = explicit
		self.version = version
		self.tags = tags


class DocumentEndEvent(Event):
	def __init__(self, start_mark=None, end_mark=None,
			explicit=None):
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.explicit = explicit


class AliasEvent(NodeEvent):
	pass


class ScalarEvent(NodeEvent):
	def __init__(self, implicit, value,
			start_mark=None, end_mark=None, style=None):
		self.tag = None
		self.implicit = implicit
		self.value = value
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.style = style


class SequenceStartEvent(CollectionStartEvent):
	pass


class SequenceEndEvent(CollectionEndEvent):
	pass


class MappingStartEvent(CollectionStartEvent):
	pass


class MappingEndEvent(CollectionEndEvent):
	pass

########NEW FILE########
__FILENAME__ = loader
__all__ = ['Loader']

from .reader import Reader
from .scanner import Scanner
from .parser import Parser
from .composer import Composer
from .constructor import Constructor
from .resolver import Resolver
from .error import echoerr


class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):
	def __init__(self, stream):
		Reader.__init__(self, stream)
		Scanner.__init__(self)
		Parser.__init__(self)
		Composer.__init__(self)
		Constructor.__init__(self)
		Resolver.__init__(self)
		self.haserrors = False

	def echoerr(self, *args, **kwargs):
		echoerr(*args, **kwargs)
		self.haserrors = True

########NEW FILE########
__FILENAME__ = markedvalue
__all__ = ['gen_marked_value', 'MarkedValue']


try:
	from __builtin__ import unicode
except ImportError:
	unicode = str


def gen_new(cls):
	def __new__(arg_cls, value, mark):
		r = super(arg_cls, arg_cls).__new__(arg_cls, value)
		r.mark = mark
		r.value = value
		return r
	return __new__


class MarkedUnicode(unicode):
	__new__ = gen_new(unicode)

	def _proc_partition(self, part_result):
		pointdiff = 1
		r = []
		for s in part_result:
			mark = self.mark.copy()
			# XXX Does not work properly with escaped strings, but this requires 
			# saving much more information in mark.
			mark.column += pointdiff
			mark.pointer += pointdiff
			r.append(MarkedUnicode(s, mark))
			pointdiff += len(s)
		return tuple(r)

	def rpartition(self, sep):
		return self._proc_partition(super(MarkedUnicode, self).rpartition(sep))

	def partition(self, sep):
		return self._proc_partition(super(MarkedUnicode, self).partition(sep))


class MarkedInt(int):
	__new__ = gen_new(int)


class MarkedFloat(float):
	__new__ = gen_new(float)


class MarkedValue:
	def __init__(self, value, mark):
		self.mark = mark
		self.value = value


specialclasses = {
	unicode: MarkedUnicode,
	int: MarkedInt,
	float: MarkedFloat,
}

classcache = {}


def gen_marked_value(value, mark, use_special_classes=True):
	if use_special_classes and value.__class__ in specialclasses:
		Marked = specialclasses[value.__class__]
	elif value.__class__ in classcache:
		Marked = classcache[value.__class__]
	else:
		class Marked(MarkedValue):
			for func in value.__class__.__dict__:
				if func not in set(('__init__', '__new__', '__getattribute__')):
					if func in set(('__eq__',)):
						# HACK to make marked dictionaries always work
						exec (('def {0}(self, *args):\n'
								'	return self.value.{0}(*[arg.value if isinstance(arg, MarkedValue) else arg for arg in args])').format(func))
					else:
						exec (('def {0}(self, *args, **kwargs):\n'
								'	return self.value.{0}(*args, **kwargs)\n').format(func))
		classcache[value.__class__] = Marked

	return Marked(value, mark)

########NEW FILE########
__FILENAME__ = nodes
class Node(object):
	def __init__(self, tag, value, start_mark, end_mark):
		self.tag = tag
		self.value = value
		self.start_mark = start_mark
		self.end_mark = end_mark

	def __repr__(self):
		value = self.value
		#if isinstance(value, list):
		#	 if len(value) == 0:
		#		 value = '<empty>'
		#	 elif len(value) == 1:
		#		 value = '<1 item>'
		#	 else:
		#		 value = '<%d items>' % len(value)
		#else:
		#	 if len(value) > 75:
		#		 value = repr(value[:70]+u' ... ')
		#	 else:
		#		 value = repr(value)
		value = repr(value)
		return '%s(tag=%r, value=%s)' % (self.__class__.__name__, self.tag, value)


class ScalarNode(Node):
	id = 'scalar'

	def __init__(self, tag, value,
			start_mark=None, end_mark=None, style=None):
		self.tag = tag
		self.value = value
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.style = style


class CollectionNode(Node):
	def __init__(self, tag, value,
			start_mark=None, end_mark=None, flow_style=None):
		self.tag = tag
		self.value = value
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.flow_style = flow_style


class SequenceNode(CollectionNode):
	id = 'sequence'


class MappingNode(CollectionNode):
	id = 'mapping'

########NEW FILE########
__FILENAME__ = parser
__all__ = ['Parser', 'ParserError']

from .error import MarkedError
from .tokens import *  # NOQA
from .events import *  # NOQA


class ParserError(MarkedError):
	pass


class Parser:
	def __init__(self):
		self.current_event = None
		self.yaml_version = None
		self.states = []
		self.marks = []
		self.state = self.parse_stream_start

	def dispose(self):
		# Reset the state attributes (to clear self-references)
		self.states = []
		self.state = None

	def check_event(self, *choices):
		# Check the type of the next event.
		if self.current_event is None:
			if self.state:
				self.current_event = self.state()
		if self.current_event is not None:
			if not choices:
				return True
			for choice in choices:
				if isinstance(self.current_event, choice):
					return True
		return False

	def peek_event(self):
		# Get the next event.
		if self.current_event is None:
			if self.state:
				self.current_event = self.state()
		return self.current_event

	def get_event(self):
		# Get the next event and proceed further.
		if self.current_event is None:
			if self.state:
				self.current_event = self.state()
		value = self.current_event
		self.current_event = None
		return value

	# stream	::= STREAM-START implicit_document? explicit_document* STREAM-END
	# implicit_document ::= block_node DOCUMENT-END*
	# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

	def parse_stream_start(self):
		# Parse the stream start.
		token = self.get_token()
		event = StreamStartEvent(token.start_mark, token.end_mark,
				encoding=token.encoding)

		# Prepare the next state.
		self.state = self.parse_implicit_document_start

		return event

	def parse_implicit_document_start(self):
		# Parse an implicit document.
		if not self.check_token(StreamEndToken):
			token = self.peek_token()
			start_mark = end_mark = token.start_mark
			event = DocumentStartEvent(start_mark, end_mark, explicit=False)

			# Prepare the next state.
			self.states.append(self.parse_document_end)
			self.state = self.parse_node

			return event

		else:
			return self.parse_document_start()

	def parse_document_start(self):
		# Parse an explicit document.
		if not self.check_token(StreamEndToken):
			token = self.peek_token()
			self.echoerr(None, None,
					"expected '<stream end>', but found %r" % token.id,
					token.start_mark)
			return StreamEndEvent(token.start_mark, token.end_mark)
		else:
			# Parse the end of the stream.
			token = self.get_token()
			event = StreamEndEvent(token.start_mark, token.end_mark)
			assert not self.states
			assert not self.marks
			self.state = None
		return event

	def parse_document_end(self):
		# Parse the document end.
		token = self.peek_token()
		start_mark = end_mark = token.start_mark
		explicit = False
		event = DocumentEndEvent(start_mark, end_mark, explicit=explicit)

		# Prepare the next state.
		self.state = self.parse_document_start

		return event

	def parse_document_content(self):
		return self.parse_node()

	def parse_node(self, indentless_sequence=False):
		start_mark = end_mark = None
		if start_mark is None:
			start_mark = end_mark = self.peek_token().start_mark
		event = None
		implicit = True
		if self.check_token(ScalarToken):
			token = self.get_token()
			end_mark = token.end_mark
			if token.plain:
				implicit = (True, False)
			else:
				implicit = (False, True)
			event = ScalarEvent(implicit, token.value,
					start_mark, end_mark, style=token.style)
			self.state = self.states.pop()
		elif self.check_token(FlowSequenceStartToken):
			end_mark = self.peek_token().end_mark
			event = SequenceStartEvent(implicit,
					start_mark, end_mark, flow_style=True)
			self.state = self.parse_flow_sequence_first_entry
		elif self.check_token(FlowMappingStartToken):
			end_mark = self.peek_token().end_mark
			event = MappingStartEvent(implicit,
					start_mark, end_mark, flow_style=True)
			self.state = self.parse_flow_mapping_first_key
		else:
			token = self.peek_token()
			raise ParserError("while parsing a flow node", start_mark,
					"expected the node content, but found %r" % token.id,
					token.start_mark)
		return event

	def parse_flow_sequence_first_entry(self):
		token = self.get_token()
		self.marks.append(token.start_mark)
		return self.parse_flow_sequence_entry(first=True)

	def parse_flow_sequence_entry(self, first=False):
		if not self.check_token(FlowSequenceEndToken):
			if not first:
				if self.check_token(FlowEntryToken):
					self.get_token()
					if self.check_token(FlowSequenceEndToken):
						token = self.peek_token()
						self.echoerr("While parsing a flow sequence", self.marks[-1],
							"expected sequence value, but got %r" % token.id, token.start_mark)
				else:
					token = self.peek_token()
					raise ParserError("while parsing a flow sequence", self.marks[-1],
							"expected ',' or ']', but got %r" % token.id, token.start_mark)

			if not self.check_token(FlowSequenceEndToken):
				self.states.append(self.parse_flow_sequence_entry)
				return self.parse_node()
		token = self.get_token()
		event = SequenceEndEvent(token.start_mark, token.end_mark)
		self.state = self.states.pop()
		self.marks.pop()
		return event

	def parse_flow_sequence_entry_mapping_end(self):
		self.state = self.parse_flow_sequence_entry
		token = self.peek_token()
		return MappingEndEvent(token.start_mark, token.start_mark)

	def parse_flow_mapping_first_key(self):
		token = self.get_token()
		self.marks.append(token.start_mark)
		return self.parse_flow_mapping_key(first=True)

	def parse_flow_mapping_key(self, first=False):
		if not self.check_token(FlowMappingEndToken):
			if not first:
				if self.check_token(FlowEntryToken):
					self.get_token()
					if self.check_token(FlowMappingEndToken):
						token = self.peek_token()
						self.echoerr("While parsing a flow mapping", self.marks[-1],
							"expected mapping key, but got %r" % token.id, token.start_mark)
				else:
					token = self.peek_token()
					raise ParserError("while parsing a flow mapping", self.marks[-1],
							"expected ',' or '}', but got %r" % token.id, token.start_mark)
			if self.check_token(KeyToken):
				token = self.get_token()
				if not self.check_token(ValueToken,
						FlowEntryToken, FlowMappingEndToken):
					self.states.append(self.parse_flow_mapping_value)
					return self.parse_node()
				else:
					token = self.peek_token()
					raise ParserError("while parsing a flow mapping", self.marks[-1],
							"expected value, but got %r" % token.id, token.start_mark)
			elif not self.check_token(FlowMappingEndToken):
				token = self.peek_token()
				expect_key = self.check_token(ValueToken, FlowEntryToken)
				if not expect_key:
					self.get_token()
					expect_key = self.check_token(ValueToken)

				if expect_key:
					raise ParserError("while parsing a flow mapping", self.marks[-1],
							"expected string key, but got %r" % token.id, token.start_mark)
				else:
					token = self.peek_token()
					raise ParserError("while parsing a flow mapping", self.marks[-1],
							"expected ':', but got %r" % token.id, token.start_mark)
		token = self.get_token()
		event = MappingEndEvent(token.start_mark, token.end_mark)
		self.state = self.states.pop()
		self.marks.pop()
		return event

	def parse_flow_mapping_value(self):
		if self.check_token(ValueToken):
			token = self.get_token()
			if not self.check_token(FlowEntryToken, FlowMappingEndToken):
				self.states.append(self.parse_flow_mapping_key)
				return self.parse_node()

		token = self.peek_token()
		raise ParserError("while parsing a flow mapping", self.marks[-1],
				"expected mapping value, but got %r" % token.id, token.start_mark)

########NEW FILE########
__FILENAME__ = reader
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.

__all__ = ['Reader', 'ReaderError']

from .error import MarkedError, Mark, NON_PRINTABLE

import codecs

try:
	from __builtin__ import unicode
except ImportError:
	unicode = str  # NOQA


class ReaderError(MarkedError):
	pass


class Reader(object):
	# Reader:
	# - determines the data encoding and converts it to a unicode string,
	# - checks if characters are in allowed range,
	# - adds '\0' to the end.

	# Reader accepts
	#  - a file-like object with its `read` method returning `str`,

	# Yeah, it's ugly and slow.
	def __init__(self, stream):
		self.name = None
		self.stream = None
		self.stream_pointer = 0
		self.eof = True
		self.buffer = ''
		self.pointer = 0
		self.full_buffer = unicode('')
		self.full_pointer = 0
		self.raw_buffer = None
		self.raw_decode = codecs.utf_8_decode
		self.encoding = 'utf-8'
		self.index = 0
		self.line = 0
		self.column = 0

		self.stream = stream
		self.name = getattr(stream, 'name', "<file>")
		self.eof = False
		self.raw_buffer = None

		while not self.eof and (self.raw_buffer is None or len(self.raw_buffer) < 2):
			self.update_raw()
		self.update(1)

	def peek(self, index=0):
		try:
			return self.buffer[self.pointer + index]
		except IndexError:
			self.update(index + 1)
			return self.buffer[self.pointer + index]

	def prefix(self, length=1):
		if self.pointer + length >= len(self.buffer):
			self.update(length)
		return self.buffer[self.pointer:self.pointer + length]

	def update_pointer(self, length):
		while length:
			ch = self.buffer[self.pointer]
			self.pointer += 1
			self.full_pointer += 1
			self.index += 1
			if ch == '\n':
				self.line += 1
				self.column = 0
			else:
				self.column += 1
			length -= 1

	def forward(self, length=1):
		if self.pointer + length + 1 >= len(self.buffer):
			self.update(length + 1)
		self.update_pointer(length)

	def get_mark(self):
		return Mark(self.name, self.line, self.column, self.full_buffer, self.full_pointer)

	def check_printable(self, data):
		match = NON_PRINTABLE.search(data)
		if match:
			self.update_pointer(match.start())
			raise ReaderError('while reading from stream', None,
					'found special characters which are not allowed',
					Mark(self.name, self.line, self.column, self.full_buffer, self.full_pointer))

	def update(self, length):
		if self.raw_buffer is None:
			return
		self.buffer = self.buffer[self.pointer:]
		self.pointer = 0
		while len(self.buffer) < length:
			if not self.eof:
				self.update_raw()
			try:
				data, converted = self.raw_decode(self.raw_buffer,
						'strict', self.eof)
			except UnicodeDecodeError as exc:
				character = self.raw_buffer[exc.start]
				position = self.stream_pointer - len(self.raw_buffer) + exc.start
				data, converted = self.raw_decode(self.raw_buffer[:exc.start], 'strict', self.eof)
				self.buffer += data
				self.full_buffer += data + '<' + str(ord(character)) + '>'
				self.raw_buffer = self.raw_buffer[converted:]
				self.update_pointer(exc.start - 1)
				raise ReaderError('while reading from stream', None,
						'found character #x%04x that cannot be decoded by UTF-8 codec' % ord(character),
						Mark(self.name, self.line, self.column, self.full_buffer, position))
			self.buffer += data
			self.full_buffer += data
			self.raw_buffer = self.raw_buffer[converted:]
			self.check_printable(data)
			if self.eof:
				self.buffer += '\0'
				self.raw_buffer = None
				break

	def update_raw(self, size=4096):
		data = self.stream.read(size)
		if self.raw_buffer is None:
			self.raw_buffer = data
		else:
			self.raw_buffer += data
		self.stream_pointer += len(data)
		if not data:
			self.eof = True

########NEW FILE########
__FILENAME__ = resolver
__all__ = ['BaseResolver', 'Resolver']

from .error import MarkedError
from .nodes import *  # NOQA

import re


class ResolverError(MarkedError):
	pass


class BaseResolver:
	DEFAULT_SCALAR_TAG = 'tag:yaml.org,2002:str'
	DEFAULT_SEQUENCE_TAG = 'tag:yaml.org,2002:seq'
	DEFAULT_MAPPING_TAG = 'tag:yaml.org,2002:map'

	yaml_implicit_resolvers = {}
	yaml_path_resolvers = {}

	def __init__(self):
		self.resolver_exact_paths = []
		self.resolver_prefix_paths = []

	@classmethod
	def add_implicit_resolver(cls, tag, regexp, first):
		if not 'yaml_implicit_resolvers' in cls.__dict__:
			cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
		if first is None:
			first = [None]
		for ch in first:
			cls.yaml_implicit_resolvers.setdefault(ch, []).append((tag, regexp))

	def descend_resolver(self, current_node, current_index):
		if not self.yaml_path_resolvers:
			return
		exact_paths = {}
		prefix_paths = []
		if current_node:
			depth = len(self.resolver_prefix_paths)
			for path, kind in self.resolver_prefix_paths[-1]:
				if self.check_resolver_prefix(depth, path, kind,
						current_node, current_index):
					if len(path) > depth:
						prefix_paths.append((path, kind))
					else:
						exact_paths[kind] = self.yaml_path_resolvers[path, kind]
		else:
			for path, kind in self.yaml_path_resolvers:
				if not path:
					exact_paths[kind] = self.yaml_path_resolvers[path, kind]
				else:
					prefix_paths.append((path, kind))
		self.resolver_exact_paths.append(exact_paths)
		self.resolver_prefix_paths.append(prefix_paths)

	def ascend_resolver(self):
		if not self.yaml_path_resolvers:
			return
		self.resolver_exact_paths.pop()
		self.resolver_prefix_paths.pop()

	def check_resolver_prefix(self, depth, path, kind,
			current_node, current_index):
		node_check, index_check = path[depth - 1]
		if isinstance(node_check, str):
			if current_node.tag != node_check:
				return
		elif node_check is not None:
			if not isinstance(current_node, node_check):
				return
		if index_check is True and current_index is not None:
			return
		if ((index_check is False or index_check is None)
			and current_index is None):
			return
		if isinstance(index_check, str):
			if not (isinstance(current_index, ScalarNode)
					and index_check == current_index.value):
				return
		elif isinstance(index_check, int) and not isinstance(index_check, bool):
			if index_check != current_index:
				return
		return True

	def resolve(self, kind, value, implicit, mark=None):
		if kind is ScalarNode and implicit[0]:
			if value == '':
				resolvers = self.yaml_implicit_resolvers.get('', [])
			else:
				resolvers = self.yaml_implicit_resolvers.get(value[0], [])
			resolvers += self.yaml_implicit_resolvers.get(None, [])
			for tag, regexp in resolvers:
				if regexp.match(value):
					return tag
			else:
				self.echoerr('While resolving plain scalar', None,
						'expected floating-point value, integer, null or boolean, but got %r' % value,
						mark)
				return self.DEFAULT_SCALAR_TAG
		if kind is ScalarNode:
			return self.DEFAULT_SCALAR_TAG
		elif kind is SequenceNode:
			return self.DEFAULT_SEQUENCE_TAG
		elif kind is MappingNode:
			return self.DEFAULT_MAPPING_TAG


class Resolver(BaseResolver):
	pass


Resolver.add_implicit_resolver(
		'tag:yaml.org,2002:bool',
		re.compile(r'''^(?:true|false)$''', re.X),
		list('yYnNtTfFoO'))

Resolver.add_implicit_resolver(
		'tag:yaml.org,2002:float',
		re.compile(r'^-?(?:0|[1-9]\d*)(?=[.eE])(?:\.\d+)?(?:[eE][-+]?\d+)?$', re.X),
		list('-0123456789'))

Resolver.add_implicit_resolver(
		'tag:yaml.org,2002:int',
		re.compile(r'^(?:0|-?[1-9]\d*)$', re.X),
		list('-0123456789'))

Resolver.add_implicit_resolver(
		'tag:yaml.org,2002:null',
		re.compile(r'^null$', re.X),
		['n'])

########NEW FILE########
__FILENAME__ = scanner
# Scanner produces tokens of the following types:
# STREAM-START
# STREAM-END
# DOCUMENT-START
# DOCUMENT-END
# FLOW-SEQUENCE-START
# FLOW-MAPPING-START
# FLOW-SEQUENCE-END
# FLOW-MAPPING-END
# FLOW-ENTRY
# KEY
# VALUE
# SCALAR(value, plain, style)
#
# Read comments in the Scanner code for more details.

__all__ = ['Scanner', 'ScannerError']

from .error import MarkedError
from .tokens import *  # NOQA


class ScannerError(MarkedError):
	pass


try:
	from __builtin__ import unicode
except ImportError:
	unicode = str  # NOQA


class SimpleKey:
	# See below simple keys treatment.
	def __init__(self, token_number, index, line, column, mark):
		self.token_number = token_number
		self.index = index
		self.line = line
		self.column = column
		self.mark = mark


class Scanner:
	def __init__(self):
		"""Initialize the scanner."""
		# It is assumed that Scanner and Reader will have a common descendant.
		# Reader do the dirty work of checking for BOM and converting the
		# input data to Unicode. It also adds NUL to the end.
		#
		# Reader supports the following methods
		#	self.peek(i=0)		 # peek the next i-th character
		#	self.prefix(l=1)	 # peek the next l characters
		#	self.forward(l=1)	 # read the next l characters and move the pointer.

		# Had we reached the end of the stream?
		self.done = False

		# The number of unclosed '{' and '['. `flow_level == 0` means block
		# context.
		self.flow_level = 0

		# List of processed tokens that are not yet emitted.
		self.tokens = []

		# Add the STREAM-START token.
		self.fetch_stream_start()

		# Number of tokens that were emitted through the `get_token` method.
		self.tokens_taken = 0

		# Variables related to simple keys treatment.

		# A simple key is a key that is not denoted by the '?' indicator.
		# We emit the KEY token before all keys, so when we find a potential
		# simple key, we try to locate the corresponding ':' indicator.
		# Simple keys should be limited to a single line.

		# Can a simple key start at the current position? A simple key may
		# start:
		# - after '{', '[', ',' (in the flow context),
		self.allow_simple_key = False

		# Keep track of possible simple keys. This is a dictionary. The key
		# is `flow_level`; there can be no more that one possible simple key
		# for each level. The value is a SimpleKey record:
		#	(token_number, index, line, column, mark)
		# A simple key may start with SCALAR(flow), '[', or '{' tokens.
		self.possible_simple_keys = {}

	# Public methods.

	def check_token(self, *choices):
		# Check if the next token is one of the given types.
		while self.need_more_tokens():
			self.fetch_more_tokens()
		if self.tokens:
			if not choices:
				return True
			for choice in choices:
				if isinstance(self.tokens[0], choice):
					return True
		return False

	def peek_token(self):
		# Return the next token, but do not delete if from the queue.
		while self.need_more_tokens():
			self.fetch_more_tokens()
		if self.tokens:
			return self.tokens[0]

	def get_token(self):
		# Return the next token.
		while self.need_more_tokens():
			self.fetch_more_tokens()
		if self.tokens:
			self.tokens_taken += 1
			return self.tokens.pop(0)

	# Private methods.

	def need_more_tokens(self):
		if self.done:
			return False
		if not self.tokens:
			return True
		# The current token may be a potential simple key, so we
		# need to look further.
		self.stale_possible_simple_keys()
		if self.next_possible_simple_key() == self.tokens_taken:
			return True

	def fetch_more_tokens(self):

		# Eat whitespaces and comments until we reach the next token.
		self.scan_to_next_token()

		# Remove obsolete possible simple keys.
		self.stale_possible_simple_keys()

		# Peek the next character.
		ch = self.peek()

		# Is it the end of stream?
		if ch == '\0':
			return self.fetch_stream_end()

		# Note: the order of the following checks is NOT significant.

		# Is it the flow sequence start indicator?
		if ch == '[':
			return self.fetch_flow_sequence_start()

		# Is it the flow mapping start indicator?
		if ch == '{':
			return self.fetch_flow_mapping_start()

		# Is it the flow sequence end indicator?
		if ch == ']':
			return self.fetch_flow_sequence_end()

		# Is it the flow mapping end indicator?
		if ch == '}':
			return self.fetch_flow_mapping_end()

		# Is it the flow entry indicator?
		if ch == ',':
			return self.fetch_flow_entry()

		# Is it the value indicator?
		if ch == ':' and self.flow_level:
			return self.fetch_value()

		# Is it a double quoted scalar?
		if ch == '\"':
			return self.fetch_double()

		# It must be a plain scalar then.
		if self.check_plain():
			return self.fetch_plain()

		# No? It's an error. Let's produce a nice error message.
		raise ScannerError("while scanning for the next token", None,
				"found character %r that cannot start any token" % ch,
				self.get_mark())

	# Simple keys treatment.

	def next_possible_simple_key(self):
		# Return the number of the nearest possible simple key. Actually we
		# don't need to loop through the whole dictionary. We may replace it
		# with the following code:
		#	if not self.possible_simple_keys:
		#		return None
		#	return self.possible_simple_keys[
		#			min(self.possible_simple_keys.keys())].token_number
		min_token_number = None
		for level in self.possible_simple_keys:
			key = self.possible_simple_keys[level]
			if min_token_number is None or key.token_number < min_token_number:
				min_token_number = key.token_number
		return min_token_number

	def stale_possible_simple_keys(self):
		# Remove entries that are no longer possible simple keys. According to
		# the YAML specification, simple keys
		# - should be limited to a single line,
		# Disabling this procedure will allow simple keys of any length and
		# height (may cause problems if indentation is broken though).
		for level in list(self.possible_simple_keys):
			key = self.possible_simple_keys[level]
			if key.line != self.line:
				del self.possible_simple_keys[level]

	def save_possible_simple_key(self):
		# The next token may start a simple key. We check if it's possible
		# and save its position. This function is called for
		#	SCALAR(flow), '[', and '{'.

		# The next token might be a simple key. Let's save it's number and
		# position.
		if self.allow_simple_key:
			self.remove_possible_simple_key()
			token_number = self.tokens_taken + len(self.tokens)
			key = SimpleKey(token_number,
					self.index, self.line, self.column, self.get_mark())
			self.possible_simple_keys[self.flow_level] = key

	def remove_possible_simple_key(self):
		# Remove the saved possible key position at the current flow level.
		if self.flow_level in self.possible_simple_keys:
			del self.possible_simple_keys[self.flow_level]

	# Fetchers.

	def fetch_stream_start(self):
		# We always add STREAM-START as the first token and STREAM-END as the
		# last token.

		# Read the token.
		mark = self.get_mark()

		# Add STREAM-START.
		self.tokens.append(StreamStartToken(mark, mark,
			encoding=self.encoding))

	def fetch_stream_end(self):
		# Reset simple keys.
		self.remove_possible_simple_key()
		self.allow_simple_key = False
		self.possible_simple_keys = {}

		# Read the token.
		mark = self.get_mark()

		# Add STREAM-END.
		self.tokens.append(StreamEndToken(mark, mark))

		# The steam is finished.
		self.done = True

	def fetch_flow_sequence_start(self):
		self.fetch_flow_collection_start(FlowSequenceStartToken)

	def fetch_flow_mapping_start(self):
		self.fetch_flow_collection_start(FlowMappingStartToken)

	def fetch_flow_collection_start(self, TokenClass):

		# '[' and '{' may start a simple key.
		self.save_possible_simple_key()

		# Increase the flow level.
		self.flow_level += 1

		# Simple keys are allowed after '[' and '{'.
		self.allow_simple_key = True

		# Add FLOW-SEQUENCE-START or FLOW-MAPPING-START.
		start_mark = self.get_mark()
		self.forward()
		end_mark = self.get_mark()
		self.tokens.append(TokenClass(start_mark, end_mark))

	def fetch_flow_sequence_end(self):
		self.fetch_flow_collection_end(FlowSequenceEndToken)

	def fetch_flow_mapping_end(self):
		self.fetch_flow_collection_end(FlowMappingEndToken)

	def fetch_flow_collection_end(self, TokenClass):

		# Reset possible simple key on the current level.
		self.remove_possible_simple_key()

		# Decrease the flow level.
		self.flow_level -= 1

		# No simple keys after ']' or '}'.
		self.allow_simple_key = False

		# Add FLOW-SEQUENCE-END or FLOW-MAPPING-END.
		start_mark = self.get_mark()
		self.forward()
		end_mark = self.get_mark()
		self.tokens.append(TokenClass(start_mark, end_mark))

	def fetch_value(self):
		# Do we determine a simple key?
		if self.flow_level in self.possible_simple_keys:

			# Add KEY.
			key = self.possible_simple_keys[self.flow_level]
			del self.possible_simple_keys[self.flow_level]
			self.tokens.insert(key.token_number - self.tokens_taken,
					KeyToken(key.mark, key.mark))

			# There cannot be two simple keys one after another.
			self.allow_simple_key = False

		# Add VALUE.
		start_mark = self.get_mark()
		self.forward()
		end_mark = self.get_mark()
		self.tokens.append(ValueToken(start_mark, end_mark))

	def fetch_flow_entry(self):

		# Simple keys are allowed after ','.
		self.allow_simple_key = True

		# Reset possible simple key on the current level.
		self.remove_possible_simple_key()

		# Add FLOW-ENTRY.
		start_mark = self.get_mark()
		self.forward()
		end_mark = self.get_mark()
		self.tokens.append(FlowEntryToken(start_mark, end_mark))

	def fetch_double(self):
		# A flow scalar could be a simple key.
		self.save_possible_simple_key()

		# No simple keys after flow scalars.
		self.allow_simple_key = False

		# Scan and add SCALAR.
		self.tokens.append(self.scan_flow_scalar())

	def fetch_plain(self):

		self.save_possible_simple_key()

		# No simple keys after plain scalars.
		self.allow_simple_key = False

		# Scan and add SCALAR. May change `allow_simple_key`.
		self.tokens.append(self.scan_plain())

	# Checkers.

	def check_plain(self):
		return self.peek() in '0123456789-ntf'

	# Scanners.

	def scan_to_next_token(self):
		while self.peek() in ' \t\n':
			self.forward()

	def scan_flow_scalar(self):
		# See the specification for details.
		# Note that we loose indentation rules for quoted scalars. Quoted
		# scalars don't need to adhere indentation because " and ' clearly
		# mark the beginning and the end of them. Therefore we are less
		# restrictive then the specification requires. We only need to check
		# that document separators are not included in scalars.
		chunks = []
		start_mark = self.get_mark()
		quote = self.peek()
		self.forward()
		chunks.extend(self.scan_flow_scalar_non_spaces(start_mark))
		while self.peek() != quote:
			chunks.extend(self.scan_flow_scalar_spaces(start_mark))
			chunks.extend(self.scan_flow_scalar_non_spaces(start_mark))
		self.forward()
		end_mark = self.get_mark()
		return ScalarToken(unicode().join(chunks), False, start_mark, end_mark, '"')

	ESCAPE_REPLACEMENTS = {
		'b': '\x08',
		't': '\x09',
		'n': '\x0A',
		'f': '\x0C',
		'r': '\x0D',
		'\"': '\"',
		'\\': '\\',
	}

	ESCAPE_CODES = {
		'u': 4,
	}

	def scan_flow_scalar_non_spaces(self, start_mark):
		# See the specification for details.
		chunks = []
		while True:
			length = 0
			while self.peek(length) not in '\"\\\0 \t\n':
				length += 1
			if length:
				chunks.append(self.prefix(length))
				self.forward(length)
			ch = self.peek()
			if ch == '\\':
				self.forward()
				ch = self.peek()
				if ch in self.ESCAPE_REPLACEMENTS:
					chunks.append(self.ESCAPE_REPLACEMENTS[ch])
					self.forward()
				elif ch in self.ESCAPE_CODES:
					length = self.ESCAPE_CODES[ch]
					self.forward()
					for k in range(length):
						if self.peek(k) not in '0123456789ABCDEFabcdef':
							raise ScannerError("while scanning a double-quoted scalar", start_mark,
									"expected escape sequence of %d hexdecimal numbers, but found %r" %
										(length, self.peek(k)), self.get_mark())
					code = int(self.prefix(length), 16)
					chunks.append(chr(code))
					self.forward(length)
				else:
					raise ScannerError("while scanning a double-quoted scalar", start_mark,
							"found unknown escape character %r" % ch, self.get_mark())
			else:
				return chunks

	def scan_flow_scalar_spaces(self, start_mark):
		# See the specification for details.
		chunks = []
		length = 0
		while self.peek(length) in ' \t':
			length += 1
		whitespaces = self.prefix(length)
		self.forward(length)
		ch = self.peek()
		if ch == '\0':
			raise ScannerError("while scanning a quoted scalar", start_mark,
					"found unexpected end of stream", self.get_mark())
		elif ch == '\n':
			raise ScannerError("while scanning a quoted scalar", start_mark,
					"found unexpected line end", self.get_mark())
		else:
			chunks.append(whitespaces)
		return chunks

	def scan_plain(self):
		chunks = []
		start_mark = self.get_mark()
		spaces = []
		while True:
			length = 0
			while True:
				if self.peek(length) not in 'eE.0123456789nul-tr+fas':
					break
				length += 1
			if length == 0:
				break
			self.allow_simple_key = False
			chunks.extend(spaces)
			chunks.append(self.prefix(length))
			self.forward(length)
		end_mark = self.get_mark()
		return ScalarToken(''.join(chunks), True, start_mark, end_mark)

########NEW FILE########
__FILENAME__ = tokens
class Token(object):
	def __init__(self, start_mark, end_mark):
		self.start_mark = start_mark
		self.end_mark = end_mark

	def __repr__(self):
		attributes = [key for key in self.__dict__
				if not key.endswith('_mark')]
		attributes.sort()
		arguments = ', '.join(['%s=%r' % (key, getattr(self, key))
				for key in attributes])
		return '%s(%s)' % (self.__class__.__name__, arguments)


class StreamStartToken(Token):
	id = '<stream start>'

	def __init__(self, start_mark=None, end_mark=None,
			encoding=None):
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.encoding = encoding


class StreamEndToken(Token):
	id = '<stream end>'


class FlowSequenceStartToken(Token):
	id = '['


class FlowMappingStartToken(Token):
	id = '{'


class FlowSequenceEndToken(Token):
	id = ']'


class FlowMappingEndToken(Token):
	id = '}'


class KeyToken(Token):
	id = '?'


class ValueToken(Token):
	id = ':'


class FlowEntryToken(Token):
	id = ','


class ScalarToken(Token):
	id = '<scalar>'

	def __init__(self, value, plain, start_mark, end_mark, style=None):
		self.value = value
		self.plain = plain
		self.start_mark = start_mark
		self.end_mark = end_mark
		self.style = style

########NEW FILE########
__FILENAME__ = matcher
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import
import sys


def gen_matcher_getter(ext, import_paths):
	def get(match_name):
		match_module, separator, match_function = match_name.rpartition('.')
		if not separator:
			match_module = 'powerline.matchers.{0}'.format(ext)
			match_function = match_name
		oldpath = sys.path
		sys.path = import_paths + sys.path
		try:
			return getattr(__import__(match_module, fromlist=[match_function]), match_function)
		finally:
			sys.path = oldpath
	return get

########NEW FILE########
__FILENAME__ = ctrlp
# vim:fileencoding=utf-8:noet

import os
try:
	import vim

	vim.command('''function! Powerline_plugin_ctrlp_main(...)
		let b:powerline_ctrlp_type = 'main'
		let b:powerline_ctrlp_args = a:000
	endfunction''')

	vim.command('''function! Powerline_plugin_ctrlp_prog(...)
		let b:powerline_ctrlp_type = 'prog'
		let b:powerline_ctrlp_args = a:000
	endfunction''')

	vim.command('''let g:ctrlp_status_func = { 'main': 'Powerline_plugin_ctrlp_main', 'prog': 'Powerline_plugin_ctrlp_prog' }''')
except ImportError:
	vim = object()  # NOQA


def ctrlp(matcher_info):
	name = matcher_info['buffer'].name
	return name and os.path.basename(name) == 'ControlP'

########NEW FILE########
__FILENAME__ = gundo
# vim:fileencoding=utf-8:noet

import os


def gundo(matcher_info):
	name = matcher_info['buffer'].name
	return name and os.path.basename(name) == '__Gundo__'


def gundo_preview(matcher_info):
	name = matcher_info['buffer'].name
	return name and os.path.basename(name) == '__Gundo_Preview__'

########NEW FILE########
__FILENAME__ = nerdtree
# vim:fileencoding=utf-8:noet

import os
import re


def nerdtree(matcher_info):
	name = matcher_info['buffer'].name
	return name and re.match(r'NERD_tree_\d+', os.path.basename(name))

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import

import os
from powerline.bindings.vim import vim_getbufoption


def help(matcher_info):
	return str(vim_getbufoption(matcher_info, 'buftype')) == 'help'


def cmdwin(matcher_info):
	name = matcher_info['buffer'].name
	return name and os.path.basename(name) == '[Command Line]'


def quickfix(matcher_info):
	return str(vim_getbufoption(matcher_info, 'buftype')) == 'quickfix'

########NEW FILE########
__FILENAME__ = renderer
# vim:fileencoding=utf-8:noet

from powerline.theme import Theme
from unicodedata import east_asian_width, combining
import os

try:
	NBSP = unicode(' ', 'utf-8')
except NameError:
	NBSP = ' '

try:
	from __builtin__ import unichr as chr
except ImportError:
	pass


def construct_returned_value(rendered_highlighted, segments, output_raw):
	if output_raw:
		return rendered_highlighted, ''.join((segment['_rendered_raw'] for segment in segments))
	else:
		return rendered_highlighted


class Renderer(object):
	'''Object that is responsible for generating the highlighted string.

	:param dict theme_config:
		Main theme configuration.
	:param local_themes:
		Local themes. Is to be used by subclasses from ``.get_theme()`` method, 
		base class only records this parameter to a ``.local_themes`` attribute.
	:param dict theme_kwargs:
		Keyword arguments for ``Theme`` class constructor.
	:param Colorscheme colorscheme:
		Colorscheme object that holds colors configuration.
	:param PowerlineLogger pl:
		Object used for logging.
	:param int ambiwidth:
		Width of the characters with east asian width unicode attribute equal to 
		``A`` (Ambigious).
	:param dict options:
		Various options. Are normally not used by base renderer, but all options 
		are recorded as attributes.
	'''

	segment_info = {
		'environ': os.environ,
		'getcwd': getattr(os, 'getcwdu', os.getcwd),
		'home': os.environ.get('HOME'),
	}
	'''Basic segment info. Is merged with local segment information by 
	``.get_segment_info()`` method. Keys:

	``environ``
		Object containing environment variables. Must define at least the 
		following methods: ``.__getitem__(var)`` that raises ``KeyError`` in 
		case requested environment variable is not present, ``.get(var, 
		default=None)`` that works like ``dict.get`` and be able to be passed to 
		``Popen``.

	``getcwd``
		Function that returns current working directory. Will be called without 
		any arguments, should return ``unicode`` or (in python-2) regular 
		string.

	``home``
		String containing path to home directory. Should be ``unicode`` or (in 
		python-2) regular string or ``None``.
	'''

	character_translations = {ord(' '): NBSP}
	'''Character translations for use in escape() function.

	See documentation of ``unicode.translate`` for details.
	'''

	np_character_translations = dict(((i, '^' + chr(i + 0x40)) for i in range(0x20)))
	'''Non-printable character translations

	These are used to transform characters in range 0x00—0x1F into ``^@``, 
	``^A`` and so on. Unilke with ``.escape()`` method (and 
	``character_translations``) result is passed to ``.strwidth()`` method.

	Note: transforms tab into ``^I``.
	'''

	def __init__(self,
				theme_config,
				local_themes,
				theme_kwargs,
				colorscheme,
				pl,
				ambiwidth=1,
				**options):
		self.__dict__.update(options)
		self.theme_config = theme_config
		theme_kwargs['pl'] = pl
		self.pl = pl
		self.theme = Theme(theme_config=theme_config, **theme_kwargs)
		self.local_themes = local_themes
		self.theme_kwargs = theme_kwargs
		self.colorscheme = colorscheme
		self.width_data = {
			'N': 1,          # Neutral
			'Na': 1,         # Narrow
			'A': ambiwidth,  # Ambigious
			'H': 1,          # Half-width
			'W': 2,          # Wide
			'F': 2,          # Fullwidth
		}

	def strwidth(self, string):
		'''Function that returns string width.

		Is used to calculate the place given string occupies when handling 
		``width`` argument to ``.render()`` method. Must take east asian width 
		into account.

		:param unicode string:
			String whose width will be calculated.

		:return: unsigned integer.
		'''
		return sum((0 if combining(symbol) else self.width_data[east_asian_width(symbol)] for symbol in string))

	def get_theme(self, matcher_info):
		'''Get Theme object.

		Is to be overridden by subclasses to support local themes, this variant 
		only returns ``.theme`` attribute.

		:param matcher_info:
			Parameter ``matcher_info`` that ``.render()`` method received. 
			Unused.
		'''
		return self.theme

	def shutdown(self):
		'''Prepare for interpreter shutdown. The only job it is supposed to do 
		is calling ``.shutdown()`` method for all theme objects. Should be 
		overridden by subclasses in case they support local themes.
		'''
		self.theme.shutdown()

	def _get_highlighting(self, segment, mode):
		segment['highlight'] = self.colorscheme.get_highlighting(segment['highlight_group'], mode, segment.get('gradient_level'))
		if segment['divider_highlight_group']:
			segment['divider_highlight'] = self.colorscheme.get_highlighting(segment['divider_highlight_group'], mode)
		else:
			segment['divider_highlight'] = None
		return segment

	def get_segment_info(self, segment_info, mode):
		'''Get segment information.

		Must return a dictionary containing at least ``home``, ``environ`` and 
		``getcwd`` keys (see documentation for ``segment_info`` attribute). This 
		implementation merges ``segment_info`` dictionary passed to 
		``.render()`` method with ``.segment_info`` attribute, preferring keys 
		from the former. It also replaces ``getcwd`` key with function returning 
		``segment_info['environ']['PWD']`` in case ``PWD`` variable is 
		available.

		:param dict segment_info:
			Segment information that was passed to ``.render()`` method.

		:return: dict with segment information.
		'''
		r = self.segment_info.copy()
		r['mode'] = mode
		if segment_info:
			r.update(segment_info)
		if 'PWD' in r['environ']:
			r['getcwd'] = lambda: r['environ']['PWD']
		return r

	def render(self, mode=None, width=None, side=None, output_raw=False, segment_info=None, matcher_info=None):
		'''Render all segments.

		When a width is provided, low-priority segments are dropped one at
		a time until the line is shorter than the width, or only segments
		with a negative priority are left. If one or more filler segments are
		provided they will fill the remaining space until the desired width is
		reached.

		:param str mode:
			Mode string. Affects contents (colors and the set of segments) of 
			rendered string.
		:param int width:
			Maximum width text can occupy. May be exceeded if there are too much 
			non-removable segments.
		:param str side:
			One of ``left``, ``right``. Determines which side will be rendered. 
			If not present all sides are rendered.
		:param bool output_raw:
			Changes the output: if this parameter is ``True`` then in place of 
			one string this method outputs a pair ``(colored_string, 
			colorless_string)``.
		:param dict segment_info:
			Segment information. See also ``.get_segment_info()`` method.
		:param matcher_info:
			Matcher information. Is processed in ``.get_theme()`` method.
		'''
		theme = self.get_theme(matcher_info)
		segments = theme.get_segments(side, self.get_segment_info(segment_info, mode))

		# Handle excluded/included segments for the current mode
		segments = [self._get_highlighting(segment, mode) for segment in segments
			if mode not in segment['exclude_modes'] and (not segment['include_modes'] or mode in segment['include_modes'])]

		segments = [segment for segment in self._render_segments(theme, segments)]

		if not width:
			# No width specified, so we don't need to crop or pad anything
			return construct_returned_value(''.join([segment['_rendered_hl'] for segment in segments]) + self.hlstyle(), segments, output_raw)

		# Create an ordered list of segments that can be dropped
		segments_priority = sorted((segment for segment in segments if segment['priority'] is not None), key=lambda segment: segment['priority'], reverse=True)
		while sum([segment['_len'] for segment in segments]) > width and len(segments_priority):
			segments.remove(segments_priority[0])
			segments_priority.pop(0)

		# Distribute the remaining space on spacer segments
		segments_spacers = [segment for segment in segments if segment['width'] == 'auto']
		if segments_spacers:
			distribute_len, distribute_len_remainder = divmod(width - sum([segment['_len'] for segment in segments]), len(segments_spacers))
			for segment in segments_spacers:
				if segment['align'] == 'l':
					segment['_space_right'] += distribute_len
				elif segment['align'] == 'r':
					segment['_space_left'] += distribute_len
				elif segment['align'] == 'c':
					space_side, space_side_remainder = divmod(distribute_len, 2)
					segment['_space_left'] += space_side + space_side_remainder
					segment['_space_right'] += space_side
			segments_spacers[0]['_space_right'] += distribute_len_remainder

		rendered_highlighted = ''.join([segment['_rendered_hl'] for segment in self._render_segments(theme, segments)]) + self.hlstyle()

		return construct_returned_value(rendered_highlighted, segments, output_raw)

	def _render_segments(self, theme, segments, render_highlighted=True):
		'''Internal segment rendering method.

		This method loops through the segment array and compares the
		foreground/background colors and divider properties and returns the
		rendered statusline as a string.

		The method always renders the raw segment contents (i.e. without
		highlighting strings added), and only renders the highlighted
		statusline if render_highlighted is True.
		'''
		segments_len = len(segments)

		for index, segment in enumerate(segments):
			segment['_rendered_raw'] = ''
			segment['_rendered_hl'] = ''

			prev_segment = segments[index - 1] if index > 0 else theme.EMPTY_SEGMENT
			next_segment = segments[index + 1] if index < segments_len - 1 else theme.EMPTY_SEGMENT
			compare_segment = next_segment if segment['side'] == 'left' else prev_segment
			outer_padding = ' ' if (index == 0 and segment['side'] == 'left') or (index == segments_len - 1 and segment['side'] == 'right') else ''
			divider_type = 'soft' if compare_segment['highlight']['bg'] == segment['highlight']['bg'] else 'hard'

			divider_raw = theme.get_divider(segment['side'], divider_type)
			divider_spaces = theme.get_spaces()
			divider_highlighted = ''
			contents_raw = segment['contents']
			contents_highlighted = ''
			draw_divider = segment['draw_' + divider_type + '_divider']

			# Pad segments first
			if draw_divider:
				if segment['side'] == 'left':
					contents_raw = outer_padding + (segment['_space_left'] * ' ') + contents_raw + ((divider_spaces + segment['_space_right']) * ' ')
				else:
					contents_raw = ((divider_spaces + segment['_space_left']) * ' ') + contents_raw + (segment['_space_right'] * ' ') + outer_padding
			else:
				if segment['side'] == 'left':
					contents_raw = outer_padding + (segment['_space_left'] * ' ') + contents_raw + (segment['_space_right'] * ' ')
				else:
					contents_raw = (segment['_space_left'] * ' ') + contents_raw + (segment['_space_right'] * ' ') + outer_padding

			# Replace spaces with no-break spaces
			divider_raw = divider_raw.replace(' ', NBSP)
			contents_raw = contents_raw.translate(self.np_character_translations)

			# Apply highlighting to padded dividers and contents
			if render_highlighted:
				if divider_type == 'soft':
					divider_highlight_group_key = 'highlight' if segment['divider_highlight_group'] is None else 'divider_highlight'
					divider_fg = segment[divider_highlight_group_key]['fg']
					divider_bg = segment[divider_highlight_group_key]['bg']
				else:
					divider_fg = segment['highlight']['bg']
					divider_bg = compare_segment['highlight']['bg']
				divider_highlighted = self.hl(divider_raw, divider_fg, divider_bg, False)
				contents_highlighted = self.hl(self.escape(contents_raw), **segment['highlight'])

			# Append padded raw and highlighted segments to the rendered segment variables
			if draw_divider:
				if segment['side'] == 'left':
					segment['_rendered_raw'] += contents_raw + divider_raw
					segment['_rendered_hl'] += contents_highlighted + divider_highlighted
				else:
					segment['_rendered_raw'] += divider_raw + contents_raw
					segment['_rendered_hl'] += divider_highlighted + contents_highlighted
			else:
				if segment['side'] == 'left':
					segment['_rendered_raw'] += contents_raw
					segment['_rendered_hl'] += contents_highlighted
				else:
					segment['_rendered_raw'] += contents_raw
					segment['_rendered_hl'] += contents_highlighted
			segment['_len'] = self.strwidth(segment['_rendered_raw'])
			yield segment

	@classmethod
	def escape(cls, string):
		'''Method that escapes segment contents.
		'''
		return string.translate(cls.character_translations)

	def hlstyle(fg=None, bg=None, attr=None):
		'''Output highlight style string.

		Assuming highlighted string looks like ``{style}{contents}`` this method 
		should output ``{style}``. If it is called without arguments this method 
		is supposed to reset style to its default.
		'''
		raise NotImplementedError

	def hl(self, contents, fg=None, bg=None, attr=None):
		'''Output highlighted chunk.

		This implementation just outputs ``.hlstyle()`` joined with 
		``contents``.
		'''
		return self.hlstyle(fg, bg, attr) + (contents or '')

########NEW FILE########
__FILENAME__ = bash_prompt
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.renderers.shell import ShellRenderer


class BashPromptRenderer(ShellRenderer):
	'''Powerline bash prompt segment renderer.'''
	escape_hl_start = '\['
	escape_hl_end = '\]'

	character_translations = ShellRenderer.character_translations.copy()
	character_translations[ord('$')] = '\\$'
	character_translations[ord('`')] = '\\`'
	character_translations[ord('\\')] = '\\\\'


renderer = BashPromptRenderer

########NEW FILE########
__FILENAME__ = i3bar
# vim:fileencoding=utf-8:noet

from powerline.renderer import Renderer
import json


class I3barRenderer(Renderer):
	'''I3bar Segment Renderer.

	Currently works only for i3bgbar (i3 bar with custom patches).
	'''

	@staticmethod
	def hlstyle(*args, **kwargs):
		# We don't need to explicitly reset attributes, so skip those calls
		return ''

	def hl(self, contents, fg=None, bg=None, attr=None):
		segment = {
			"full_text": contents,
			"separator": False,
			"separator_block_width": 0,  # no seperators
		}

		if fg is not None:
			if fg is not False and fg[1] is not False:
				segment['color'] = "#{0:06x}".format(fg[1])
		if bg is not None:
			if bg is not False and bg[1] is not False:
				segment['background_color'] = "#{0:06x}".format(bg[1])
		# i3bar "pseudo json" requires one line at a time
		return json.dumps(segment) + ",\n"


renderer = I3barRenderer

########NEW FILE########
__FILENAME__ = ipython
# vim:fileencoding=utf-8:noet

from powerline.renderers.shell import ShellRenderer
from powerline.theme import Theme


class IpythonRenderer(ShellRenderer):
	'''Powerline ipython segment renderer.'''
	escape_hl_start = '\x01'
	escape_hl_end = '\x02'

	def get_segment_info(self, segment_info, mode):
		r = self.segment_info.copy()
		r['ipython'] = segment_info
		return r

	def get_theme(self, matcher_info):
		if matcher_info == 'in':
			return self.theme
		else:
			match = self.local_themes[matcher_info]
			try:
				return match['theme']
			except KeyError:
				match['theme'] = Theme(
					theme_config=match['config'],
					top_theme_config=self.theme_config,
					**self.theme_kwargs
				)
				return match['theme']

	def shutdown(self):
		self.theme.shutdown()
		for match in self.local_themes.values():
			if 'theme' in match:
				match['theme'].shutdown()


renderer = IpythonRenderer

########NEW FILE########
__FILENAME__ = pango_markup
# vim:fileencoding=utf-8:noet

from powerline.renderer import Renderer
from powerline.colorscheme import ATTR_BOLD, ATTR_ITALIC, ATTR_UNDERLINE

from xml.sax.saxutils import escape as _escape


class PangoMarkupRenderer(Renderer):
	'''Powerline Pango markup segment renderer.'''

	@staticmethod
	def hlstyle(*args, **kwargs):
		# We don't need to explicitly reset attributes, so skip those calls
		return ''

	def hl(self, contents, fg=None, bg=None, attr=None):
		'''Highlight a segment.'''
		awesome_attr = []
		if fg is not None:
			if fg is not False and fg[1] is not False:
				awesome_attr += ['foreground="#{0:06x}"'.format(fg[1])]
		if bg is not None:
			if bg is not False and bg[1] is not False:
				awesome_attr += ['background="#{0:06x}"'.format(bg[1])]
		if attr is not None and attr is not False:
			if attr & ATTR_BOLD:
				awesome_attr += ['font_weight="bold"']
			if attr & ATTR_ITALIC:
				awesome_attr += ['font_style="italic"']
			if attr & ATTR_UNDERLINE:
				awesome_attr += ['underline="single"']
		return '<span ' + ' '.join(awesome_attr) + '>' + contents + '</span>'

	escape = staticmethod(_escape)


renderer = PangoMarkupRenderer

########NEW FILE########
__FILENAME__ = shell
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.renderer import Renderer
from powerline.colorscheme import ATTR_BOLD, ATTR_ITALIC, ATTR_UNDERLINE


def int_to_rgb(num):
	r = (num >> 16) & 0xff
	g = (num >> 8) & 0xff
	b = num & 0xff
	return r, g, b


class ShellRenderer(Renderer):
	'''Powerline shell segment renderer.'''
	escape_hl_start = ''
	escape_hl_end = ''
	term_truecolor = False
	tmux_escape = False
	screen_escape = False

	character_translations = Renderer.character_translations.copy()

	def hlstyle(self, fg=None, bg=None, attr=None):
		'''Highlight a segment.

		If an argument is None, the argument is ignored. If an argument is
		False, the argument is reset to the terminal defaults. If an argument
		is a valid color or attribute, it's added to the ANSI escape code.
		'''
		ansi = [0]
		if fg is not None:
			if fg is False or fg[0] is False:
				ansi += [39]
			else:
				if self.term_truecolor:
					ansi += [38, 2] + list(int_to_rgb(fg[1]))
				else:
					ansi += [38, 5, fg[0]]
		if bg is not None:
			if bg is False or bg[0] is False:
				ansi += [49]
			else:
				if self.term_truecolor:
					ansi += [48, 2] + list(int_to_rgb(bg[1]))
				else:
					ansi += [48, 5, bg[0]]
		if attr is not None:
			if attr is False:
				ansi += [22]
			else:
				if attr & ATTR_BOLD:
					ansi += [1]
				elif attr & ATTR_ITALIC:
					# Note: is likely not to work or even be inverse in place of
					# italic. Omit using this in colorschemes.
					ansi += [3]
				elif attr & ATTR_UNDERLINE:
					ansi += [4]
		r = '\033[{0}m'.format(';'.join(str(attr) for attr in ansi))
		if self.tmux_escape:
			r = '\033Ptmux;' + r.replace('\033', '\033\033') + '\033\\'
		elif self.screen_escape:
			r = '\033P' + r.replace('\033', '\033\033') + '\033\\'
		return self.escape_hl_start + r + self.escape_hl_end


renderer = ShellRenderer

########NEW FILE########
__FILENAME__ = tcsh_prompt
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.renderers.zsh_prompt import ZshPromptRenderer


class TcshPromptRenderer(ZshPromptRenderer):
	'''Powerline tcsh prompt segment renderer.'''
	character_translations = ZshPromptRenderer.character_translations.copy()
	character_translations[ord('%')] = '%%'
	character_translations[ord('\\')] = '\\\\'
	character_translations[ord('^')] = '\\^'


renderer = TcshPromptRenderer

########NEW FILE########
__FILENAME__ = tmux
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.renderer import Renderer
from powerline.colorscheme import ATTR_BOLD, ATTR_ITALIC, ATTR_UNDERLINE


class TmuxRenderer(Renderer):
	'''Powerline tmux segment renderer.'''

	character_translations = Renderer.character_translations.copy()
	character_translations[ord('#')] = '##[]'

	def hlstyle(self, fg=None, bg=None, attr=None):
		'''Highlight a segment.'''
		# We don't need to explicitly reset attributes, so skip those calls
		if not attr and not bg and not fg:
			return ''
		tmux_attr = []
		if fg is not None:
			if fg is False or fg[0] is False:
				tmux_attr += ['fg=default']
			else:
				tmux_attr += ['fg=colour' + str(fg[0])]
		if bg is not None:
			if bg is False or bg[0] is False:
				tmux_attr += ['bg=default']
			else:
				tmux_attr += ['bg=colour' + str(bg[0])]
		if attr is not None:
			if attr is False:
				tmux_attr += ['nobold', 'noitalics', 'nounderscore']
			else:
				if attr & ATTR_BOLD:
					tmux_attr += ['bold']
				else:
					tmux_attr += ['nobold']
				if attr & ATTR_ITALIC:
					tmux_attr += ['italics']
				else:
					tmux_attr += ['noitalics']
				if attr & ATTR_UNDERLINE:
					tmux_attr += ['underscore']
				else:
					tmux_attr += ['nounderscore']
		return '#[' + ','.join(tmux_attr) + ']'

	def get_segment_info(self, segment_info, mode):
		r = self.segment_info.copy()
		if segment_info:
			r.update(segment_info)
		if 'pane_id' in r:
			varname = 'TMUX_PWD_' + r['pane_id'].lstrip('%')
			if varname in r['environ']:
				r['getcwd'] = lambda: r['environ'][varname]
		r['mode'] = mode
		return r


renderer = TmuxRenderer

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.bindings.vim import vim_get_func, environ
from powerline.renderer import Renderer
from powerline.colorscheme import ATTR_BOLD, ATTR_ITALIC, ATTR_UNDERLINE
from powerline.theme import Theme

import vim
import sys


try:
	from __builtin__ import unichr as chr
except ImportError:
	pass


vim_mode = vim_get_func('mode', rettype=str)
mode_translations = {
	chr(ord('V') - 0x40): '^V',
	chr(ord('S') - 0x40): '^S',
}


class VimRenderer(Renderer):
	'''Powerline vim segment renderer.'''

	character_translations = Renderer.character_translations.copy()
	character_translations[ord('%')] = '%%'

	def __init__(self, *args, **kwargs):
		if not hasattr(vim, 'strwidth'):
			# Hope nobody want to change this at runtime
			if vim.eval('&ambiwidth') == 'double':
				kwargs = dict(**kwargs)
				kwargs['ambigious'] = 2
		super(VimRenderer, self).__init__(*args, **kwargs)
		self.hl_groups = {}

	def shutdown(self):
		self.theme.shutdown()
		for match in self.local_themes.values():
			if 'theme' in match:
				match['theme'].shutdown()

	def add_local_theme(self, matcher, theme):
		if matcher in self.local_themes:
			raise KeyError('There is already a local theme with given matcher')
		self.local_themes[matcher] = theme

	def get_theme(self, matcher_info):
		for matcher in self.local_themes.keys():
			if matcher(matcher_info):
				match = self.local_themes[matcher]
				try:
					return match['theme']
				except KeyError:
					match['theme'] = Theme(theme_config=match['config'], top_theme_config=self.theme_config, **self.theme_kwargs)
					return match['theme']
		else:
			return self.theme

	if hasattr(vim, 'strwidth'):
		if sys.version_info < (3,):
			@staticmethod
			def strwidth(string):
				# Does not work with tabs, but neither is strwidth from default 
				# renderer
				return vim.strwidth(string.encode('utf-8'))
		else:
			@staticmethod  # NOQA
			def strwidth(string):
				return vim.strwidth(string)

	def get_segment_info(self, segment_info, mode):
		return segment_info or self.segment_info

	def render(self, window, window_id, winnr):
		'''Render all segments.'''
		if window is vim.current.window:
			mode = vim_mode(1)
			mode = mode_translations.get(mode, mode)
		else:
			mode = 'nc'
		segment_info = {
			'window': window,
			'mode': mode,
			'window_id': window_id,
			'winnr': winnr,
			'environ': environ,
		}
		segment_info['buffer'] = segment_info['window'].buffer
		segment_info['bufnr'] = segment_info['buffer'].number
		segment_info.update(self.segment_info)
		winwidth = segment_info['window'].width
		statusline = super(VimRenderer, self).render(
			mode=mode,
			width=winwidth,
			segment_info=segment_info,
			matcher_info=segment_info,
		)
		return statusline

	def reset_highlight(self):
		self.hl_groups.clear()

	def hlstyle(self, fg=None, bg=None, attr=None):
		'''Highlight a segment.

		If an argument is None, the argument is ignored. If an argument is
		False, the argument is reset to the terminal defaults. If an argument
		is a valid color or attribute, it's added to the vim highlight group.
		'''
		# We don't need to explicitly reset attributes in vim, so skip those calls
		if not attr and not bg and not fg:
			return ''

		if not (fg, bg, attr) in self.hl_groups:
			hl_group = {
				'ctermfg': 'NONE',
				'guifg': None,
				'ctermbg': 'NONE',
				'guibg': None,
				'attr': ['NONE'],
				'name': '',
			}
			if fg is not None and fg is not False:
				hl_group['ctermfg'] = fg[0]
				hl_group['guifg'] = fg[1]
			if bg is not None and bg is not False:
				hl_group['ctermbg'] = bg[0]
				hl_group['guibg'] = bg[1]
			if attr:
				hl_group['attr'] = []
				if attr & ATTR_BOLD:
					hl_group['attr'].append('bold')
				if attr & ATTR_ITALIC:
					hl_group['attr'].append('italic')
				if attr & ATTR_UNDERLINE:
					hl_group['attr'].append('underline')
			hl_group['name'] = ('Pl_' +
						str(hl_group['ctermfg']) + '_' +
						str(hl_group['guifg']) + '_' +
						str(hl_group['ctermbg']) + '_' +
						str(hl_group['guibg']) + '_' +
						''.join(hl_group['attr']))
			self.hl_groups[(fg, bg, attr)] = hl_group
			vim.command('hi {group} ctermfg={ctermfg} guifg={guifg} guibg={guibg} ctermbg={ctermbg} cterm={attr} gui={attr}'.format(
				group=hl_group['name'],
				ctermfg=hl_group['ctermfg'],
				guifg='#{0:06x}'.format(hl_group['guifg']) if hl_group['guifg'] is not None else 'NONE',
				ctermbg=hl_group['ctermbg'],
				guibg='#{0:06x}'.format(hl_group['guibg']) if hl_group['guibg'] is not None else 'NONE',
				attr=','.join(hl_group['attr']),
			))
		return '%#' + self.hl_groups[(fg, bg, attr)]['name'] + '#'


renderer = VimRenderer

########NEW FILE########
__FILENAME__ = zsh_prompt
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import, unicode_literals

from powerline.renderers.shell import ShellRenderer
from powerline.theme import Theme


class ZshPromptRenderer(ShellRenderer):
	'''Powerline zsh prompt segment renderer.'''
	escape_hl_start = '%{'
	escape_hl_end = '%}'

	character_translations = ShellRenderer.character_translations.copy()
	character_translations[ord('%')] = '%%'

	old_widths = {}

	def render(self, segment_info, *args, **kwargs):
		client_id = segment_info.get('client_id')
		key = (client_id, kwargs.get('side'))
		kwargs = kwargs.copy()
		width = kwargs.pop('width', None)
		local_theme = segment_info.get('local_theme')
		if client_id and local_theme:
			output_raw = False
			try:
				width = self.old_widths[key]
			except KeyError:
				pass
		else:
			output_raw = True
		ret = super(ShellRenderer, self).render(
			output_raw=output_raw,
			width=width,
			matcher_info=local_theme,
			segment_info=segment_info,
			*args, **kwargs
		)
		if output_raw:
			self.old_widths[key] = len(ret[1])
			ret = ret[0]
		return ret

	def get_theme(self, matcher_info):
		if not matcher_info:
			return self.theme
		match = self.local_themes[matcher_info]
		try:
			return match['theme']
		except KeyError:
			match['theme'] = Theme(
				theme_config=match['config'],
				top_theme_config=self.theme_config,
				**self.theme_kwargs
			)
			return match['theme']


renderer = ZshPromptRenderer

########NEW FILE########
__FILENAME__ = segment
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import
import sys


def get_segment_key(segment, theme_configs, key, module=None, default=None):
	try:
		return segment[key]
	except KeyError:
		if 'name' in segment:
			name = segment['name']
			for theme_config in theme_configs:
				if 'segment_data' in theme_config:
					for segment_key in ((module + '.' + name, name) if module else (name,)):
						try:
							return theme_config['segment_data'][segment_key][key]
						except KeyError:
							pass
	return default


def get_function(data, segment):
	oldpath = sys.path
	sys.path = data['path'] + sys.path
	segment_module = str(segment.get('module', data['default_module']))
	try:
		return None, getattr(__import__(segment_module, fromlist=[segment['name']]), segment['name']), segment_module
	finally:
		sys.path = oldpath


def get_string(data, segment):
	return data['get_key'](segment, None, 'contents'), None, None


def get_filler(data, segment):
	return None, None, None


segment_getters = {
	"function": get_function,
	"string": get_string,
	"filler": get_filler,
}


def get_attr_func(contents_func, key, args):
	try:
		func = getattr(contents_func, key)
	except AttributeError:
		return None
	else:
		if args is None:
			return lambda : func()
		else:
			return lambda pl, shutdown_event: func(pl=pl, shutdown_event=shutdown_event, **args)


def gen_segment_getter(pl, ext, path, theme_configs, default_module=None):
	data = {
		'default_module': default_module or 'powerline.segments.' + ext,
		'path': path,
	}

	def get_key(segment, module, key, default=None):
		return get_segment_key(segment, theme_configs, key, module, default)
	data['get_key'] = get_key

	def get(segment, side):
		segment_type = segment.get('type', 'function')
		try:
			get_segment_info = segment_getters[segment_type]
		except KeyError:
			raise TypeError('Unknown segment type: {0}'.format(segment_type))

		try:
			contents, _contents_func, module = get_segment_info(data, segment)
		except Exception as e:
			pl.exception('Failed to generate segment from {0!r}: {1}', segment, str(e), prefix='segment_generator')
			return None

		if segment_type == 'function':
			highlight_group = [module + '.' + segment['name'], segment['name']]
		else:
			highlight_group = segment.get('highlight_group') or segment.get('name')

		if segment_type == 'function':
			args = dict(((str(k), v) for k, v in get_key(segment, module, 'args', {}).items()))
			startup_func = get_attr_func(_contents_func, 'startup', args)
			shutdown_func = get_attr_func(_contents_func, 'shutdown', None)

			if hasattr(_contents_func, 'powerline_requires_segment_info'):
				contents_func = lambda pl, segment_info: _contents_func(pl=pl, segment_info=segment_info, **args)
			else:
				contents_func = lambda pl, segment_info: _contents_func(pl=pl, **args)
		else:
			startup_func = None
			shutdown_func = None
			contents_func = None

		return {
			'name': segment.get('name'),
			'type': segment_type,
			'highlight_group': highlight_group,
			'divider_highlight_group': None,
			'before': get_key(segment, module, 'before', ''),
			'after': get_key(segment, module, 'after', ''),
			'contents_func': contents_func,
			'contents': contents,
			'args': args if segment_type == 'function' else {},
			'priority': segment.get('priority', None),
			'draw_hard_divider': segment.get('draw_hard_divider', True),
			'draw_soft_divider': segment.get('draw_soft_divider', True),
			'draw_inner_divider': segment.get('draw_inner_divider', False),
			'side': side,
			'exclude_modes': segment.get('exclude_modes', []),
			'include_modes': segment.get('include_modes', []),
			'width': segment.get('width'),
			'align': segment.get('align', 'l'),
			'startup': startup_func,
			'shutdown': shutdown_func,
			'_rendered_raw': '',
			'_rendered_hl': '',
			'_len': 0,
			'_space_left': 0,
			'_space_right': 0,
		}

	return get

########NEW FILE########
__FILENAME__ = common
# vim:fileencoding=utf-8:noet

from __future__ import unicode_literals, absolute_import, division

import os
import sys
import re

from datetime import datetime
import socket
from multiprocessing import cpu_count as _cpu_count

from powerline.lib import add_divider_highlight_group
from powerline.lib.shell import asrun, run_cmd
from powerline.lib.url import urllib_read, urllib_urlencode
from powerline.lib.vcs import guess, tree_status
from powerline.lib.threaded import ThreadedSegment, KwThreadedSegment, with_docstring
from powerline.lib.monotonic import monotonic
from powerline.lib.humanize_bytes import humanize_bytes
from powerline.lib.unicode import u
from powerline.theme import requires_segment_info
from collections import namedtuple


cpu_count = None


@requires_segment_info
def environment(pl, segment_info, variable=None):
	'''Return the value of any defined environment variable

	:param string variable:
		The environment variable to return if found
	'''
	return segment_info['environ'].get(variable, None)


@requires_segment_info
def hostname(pl, segment_info, only_if_ssh=False, exclude_domain=False):
	'''Return the current hostname.

	:param bool only_if_ssh:
		only return the hostname if currently in an SSH session
	:param bool exclude_domain:
		return the hostname without domain if there is one
	'''
	if only_if_ssh and not segment_info['environ'].get('SSH_CLIENT'):
		return None
	if exclude_domain:
		return socket.gethostname().split('.')[0]
	return socket.gethostname()


@requires_segment_info
def branch(pl, segment_info, status_colors=False):
	'''Return the current VCS branch.

	:param bool status_colors:
		determines whether repository status will be used to determine highlighting. Default: False.

	Highlight groups used: ``branch_clean``, ``branch_dirty``, ``branch``.
	'''
	name = segment_info['getcwd']()
	repo = guess(path=name)
	if repo is not None:
		branch = repo.branch()
		scol = ['branch']
		if status_colors:
			status = tree_status(repo, pl)
			scol.insert(0, 'branch_dirty' if status and status.strip() else 'branch_clean')
		return [{
			'contents': branch,
			'highlight_group': scol,
		}]


@requires_segment_info
def cwd(pl, segment_info, dir_shorten_len=None, dir_limit_depth=None, use_path_separator=False, ellipsis='⋯'):
	'''Return the current working directory.

	Returns a segment list to create a breadcrumb-like effect.

	:param int dir_shorten_len:
		shorten parent directory names to this length (e.g. 
		:file:`/long/path/to/powerline` → :file:`/l/p/t/powerline`)
	:param int dir_limit_depth:
		limit directory depth to this number (e.g. 
		:file:`/long/path/to/powerline` → :file:`⋯/to/powerline`)
	:param bool use_path_separator:
		Use path separator in place of soft divider.
	:param str ellipsis:
		Specifies what to use in place of omitted directories. Use None to not 
		show this subsegment at all.

	Divider highlight group used: ``cwd:divider``.

	Highlight groups used: ``cwd:current_folder`` or ``cwd``. It is recommended to define all highlight groups.
	'''
	try:
		cwd = u(segment_info['getcwd']())
	except OSError as e:
		if e.errno == 2:
			# user most probably deleted the directory
			# this happens when removing files from Mercurial repos for example
			pl.warn('Current directory not found')
			cwd = "[not found]"
		else:
			raise
	home = segment_info['home']
	if home:
		home = u(home)
		cwd = re.sub('^' + re.escape(home), '~', cwd, 1)
	cwd_split = cwd.split(os.sep)
	cwd_split_len = len(cwd_split)
	cwd = [i[0:dir_shorten_len] if dir_shorten_len and i else i for i in cwd_split[:-1]] + [cwd_split[-1]]
	if dir_limit_depth and cwd_split_len > dir_limit_depth + 1:
		del(cwd[0:-dir_limit_depth])
		if ellipsis is not None:
			cwd.insert(0, ellipsis)
	ret = []
	if not cwd[0]:
		cwd[0] = '/'
	draw_inner_divider = not use_path_separator
	for part in cwd:
		if not part:
			continue
		if use_path_separator:
			part += os.sep
		ret.append({
			'contents': part,
			'divider_highlight_group': 'cwd:divider',
			'draw_inner_divider': draw_inner_divider,
		})
	ret[-1]['highlight_group'] = ['cwd:current_folder', 'cwd']
	if use_path_separator:
		ret[-1]['contents'] = ret[-1]['contents'][:-1]
		if len(ret) > 1 and ret[0]['contents'][0] == os.sep:
			ret[0]['contents'] = ret[0]['contents'][1:]
	return ret


def date(pl, format='%Y-%m-%d', istime=False):
	'''Return the current date.

	:param str format:
		strftime-style date format string
	:param bool istime:
		If true then segment uses ``time`` highlight group.

	Divider highlight group used: ``time:divider``.

	Highlight groups used: ``time`` or ``date``.
	'''
	return [{
		'contents': datetime.now().strftime(format),
		'highlight_group': (['time'] if istime else []) + ['date'],
		'divider_highlight_group': 'time:divider' if istime else None,
	}]


UNICODE_TEXT_TRANSLATION = {
	ord('\''): '’',
	ord('-'): '‐',
}


def fuzzy_time(pl, unicode_text=True):
	'''Display the current time as fuzzy time, e.g. "quarter past six".

	:param bool unicode_text:
		If true then hyphenminuses (regular ASCII ``-``) and single quotes are 
		replaced with unicode dashes and apostrophes.
	'''
	hour_str = ['twelve', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven']
	minute_str = {
		5: 'five past',
		10: 'ten past',
		15: 'quarter past',
		20: 'twenty past',
		25: 'twenty-five past',
		30: 'half past',
		35: 'twenty-five to',
		40: 'twenty to',
		45: 'quarter to',
		50: 'ten to',
		55: 'five to',
	}
	special_case_str = {
		(23, 58): 'round about midnight',
		(23, 59): 'round about midnight',
		(0, 0): 'midnight',
		(0, 1): 'round about midnight',
		(0, 2): 'round about midnight',
		(12, 0): 'noon',
	}

	now = datetime.now()

	try:
		return special_case_str[(now.hour, now.minute)]
	except KeyError:
		pass

	hour = now.hour
	if now.minute > 32:
		if hour == 23:
			hour = 0
		else:
			hour += 1
	if hour > 11:
		hour = hour - 12
	hour = hour_str[hour]

	minute = int(round(now.minute / 5.0) * 5)
	if minute == 60 or minute == 0:
		result = ' '.join([hour, 'o\'clock'])
	else:
		minute = minute_str[minute]
		result = ' '.join([minute, hour])

	if unicode_text:
		result = result.translate(UNICODE_TEXT_TRANSLATION)

	return result


def _external_ip(query_url='http://ipv4.icanhazip.com/'):
	return urllib_read(query_url).strip()


class ExternalIpSegment(ThreadedSegment):
	interval = 300

	def set_state(self, query_url='http://ipv4.icanhazip.com/', **kwargs):
		self.query_url = query_url
		super(ExternalIpSegment, self).set_state(**kwargs)

	def update(self, old_ip):
		return _external_ip(query_url=self.query_url)

	def render(self, ip, **kwargs):
		if not ip:
			return None
		return [{'contents': ip, 'divider_highlight_group': 'background:divider'}]


external_ip = with_docstring(ExternalIpSegment(),
'''Return external IP address.

:param str query_url:
	URI to query for IP address, should return only the IP address as a text string

	Suggested URIs:

	* http://ipv4.icanhazip.com/
	* http://ipv6.icanhazip.com/
	* http://icanhazip.com/ (returns IPv6 address if available, else IPv4)

Divider highlight group used: ``background:divider``.
''')


# Weather condition code descriptions available at
# http://developer.yahoo.com/weather/#codes
weather_conditions_codes = (
	('tornado',                 'stormy'),  # 0
	('tropical_storm',          'stormy'),  # 1
	('hurricane',               'stormy'),  # 2
	('severe_thunderstorms',    'stormy'),  # 3
	('thunderstorms',           'stormy'),  # 4
	('mixed_rain_and_snow',     'rainy' ),  # 5
	('mixed_rain_and_sleet',    'rainy' ),  # 6
	('mixed_snow_and_sleet',    'snowy' ),  # 7
	('freezing_drizzle',        'rainy' ),  # 8
	('drizzle',                 'rainy' ),  # 9
	('freezing_rain',           'rainy' ),  # 10
	('showers',                 'rainy' ),  # 11
	('showers',                 'rainy' ),  # 12
	('snow_flurries',           'snowy' ),  # 13
	('light_snow_showers',      'snowy' ),  # 14
	('blowing_snow',            'snowy' ),  # 15
	('snow',                    'snowy' ),  # 16
	('hail',                    'snowy' ),  # 17
	('sleet',                   'snowy' ),  # 18
	('dust',                    'foggy' ),  # 19
	('fog',                     'foggy' ),  # 20
	('haze',                    'foggy' ),  # 21
	('smoky',                   'foggy' ),  # 22
	('blustery',                'foggy' ),  # 23
	('windy',                           ),  # 24
	('cold',                    'day'   ),  # 25
	('clouds',                  'cloudy'),  # 26
	('mostly_cloudy_night',     'cloudy'),  # 27
	('mostly_cloudy_day',       'cloudy'),  # 28
	('partly_cloudy_night',     'cloudy'),  # 29
	('partly_cloudy_day',       'cloudy'),  # 30
	('clear_night',             'night' ),  # 31
	('sun',                     'sunny' ),  # 32
	('fair_night',              'night' ),  # 33
	('fair_day',                'day'   ),  # 34
	('mixed_rain_and_hail',     'rainy' ),  # 35
	('hot',                     'sunny' ),  # 36
	('isolated_thunderstorms',  'stormy'),  # 37
	('scattered_thunderstorms', 'stormy'),  # 38
	('scattered_thunderstorms', 'stormy'),  # 39
	('scattered_showers',       'rainy' ),  # 40
	('heavy_snow',              'snowy' ),  # 41
	('scattered_snow_showers',  'snowy' ),  # 42
	('heavy_snow',              'snowy' ),  # 43
	('partly_cloudy',           'cloudy'),  # 44
	('thundershowers',          'rainy' ),  # 45
	('snow_showers',            'snowy' ),  # 46
	('isolated_thundershowers', 'rainy' ),  # 47
)
# ('day',    (25, 34)),
# ('rainy',  (5, 6, 8, 9, 10, 11, 12, 35, 40, 45, 47)),
# ('cloudy', (26, 27, 28, 29, 30, 44)),
# ('snowy',  (7, 13, 14, 15, 16, 17, 18, 41, 42, 43, 46)),
# ('stormy', (0, 1, 2, 3, 4, 37, 38, 39)),
# ('foggy',  (19, 20, 21, 22, 23)),
# ('sunny',  (32, 36)),
# ('night',  (31, 33))):
weather_conditions_icons = {
	'day':           '〇',
	'blustery':      '⚑',
	'rainy':         '☔',
	'cloudy':        '☁',
	'snowy':         '❅',
	'stormy':        '☈',
	'foggy':         '〰',
	'sunny':         '☼',
	'night':         '☾',
	'windy':         '☴',
	'not_available': '�',
	'unknown':       '⚠',
}

temp_conversions = {
	'C': lambda temp: temp,
	'F': lambda temp: (temp * 9 / 5) + 32,
	'K': lambda temp: temp + 273.15,
}

# Note: there are also unicode characters for units: ℃, ℉ and  K
temp_units = {
	'C': '°C',
	'F': '°F',
	'K': 'K',
}


class WeatherSegment(ThreadedSegment):
	interval = 600

	def set_state(self, location_query=None, **kwargs):
		self.location = location_query
		self.url = None
		super(WeatherSegment, self).set_state(**kwargs)

	def update(self, old_weather):
		import json

		if not self.url:
			# Do not lock attribute assignments in this branch: they are used
			# only in .update()
			if not self.location:
				location_data = json.loads(urllib_read('http://freegeoip.net/json/'))
				self.location = ','.join([location_data['city'],
											location_data['region_code'],
											location_data['country_code']])
			query_data = {
				'q':
				'use "http://github.com/yql/yql-tables/raw/master/weather/weather.bylocation.xml" as we;'
				'select * from we where location="{0}" and unit="c"'.format(self.location).encode('utf-8'),
				'format': 'json',
			}
			self.url = 'http://query.yahooapis.com/v1/public/yql?' + urllib_urlencode(query_data)

		raw_response = urllib_read(self.url)
		if not raw_response:
			self.error('Failed to get response')
			return
		response = json.loads(raw_response)
		condition = response['query']['results']['weather']['rss']['channel']['item']['condition']
		condition_code = int(condition['code'])
		temp = float(condition['temp'])

		try:
			icon_names = weather_conditions_codes[condition_code]
		except IndexError:
			if condition_code == 3200:
				icon_names = ('not_available',)
				self.warn('Weather is not available for location {0}', self.location)
			else:
				icon_names = ('unknown',)
				self.error('Unknown condition code: {0}', condition_code)

		return (temp, icon_names)

	def render(self, weather, icons=None, unit='C', temp_format=None, temp_coldest=-30, temp_hottest=40, **kwargs):
		if not weather:
			return None

		temp, icon_names = weather

		for icon_name in icon_names:
			if icons:
				if icon_name in icons:
					icon = icons[icon_name]
					break
		else:
			icon = weather_conditions_icons[icon_names[-1]]

		temp_format = temp_format or ('{temp:.0f}' + temp_units[unit])
		converted_temp = temp_conversions[unit](temp)
		if temp <= temp_coldest:
			gradient_level = 0
		elif temp >= temp_hottest:
			gradient_level = 100
		else:
			gradient_level = (temp - temp_coldest) * 100.0 / (temp_hottest - temp_coldest)
		groups = ['weather_condition_' + icon_name for icon_name in icon_names] + ['weather_conditions', 'weather']
		return [
			{
				'contents': icon + ' ',
				'highlight_group': groups,
				'divider_highlight_group': 'background:divider',
			},
			{
				'contents': temp_format.format(temp=converted_temp),
				'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'],
				'divider_highlight_group': 'background:divider',
				'gradient_level': gradient_level,
			},
		]


weather = with_docstring(WeatherSegment(),
'''Return weather from Yahoo! Weather.

Uses GeoIP lookup from http://freegeoip.net/ to automatically determine
your current location. This should be changed if you're in a VPN or if your
IP address is registered at another location.

Returns a list of colorized icon and temperature segments depending on
weather conditions.

:param str unit:
	temperature unit, can be one of ``F``, ``C`` or ``K``
:param str location_query:
	location query for your current location, e.g. ``oslo, norway``
:param dict icons:
	dict for overriding default icons, e.g. ``{'heavy_snow' : u'❆'}``
:param str temp_format:
	format string, receives ``temp`` as an argument. Should also hold unit.
:param float temp_coldest:
	coldest temperature. Any temperature below it will have gradient level equal
	to zero.
:param float temp_hottest:
	hottest temperature. Any temperature above it will have gradient level equal
	to 100. Temperatures between ``temp_coldest`` and ``temp_hottest`` receive
	gradient level that indicates relative position in this interval
	(``100 * (cur-coldest) / (hottest-coldest)``).

Divider highlight group used: ``background:divider``.

Highlight groups used: ``weather_conditions`` or ``weather``, ``weather_temp_gradient`` (gradient) or ``weather``.
Also uses ``weather_conditions_{condition}`` for all weather conditions supported by Yahoo.
''')


def system_load(pl, format='{avg:.1f}', threshold_good=1, threshold_bad=2, track_cpu_count=False):
	'''Return system load average.

	Highlights using ``system_load_good``, ``system_load_bad`` and
	``system_load_ugly`` highlighting groups, depending on the thresholds
	passed to the function.

	:param str format:
		format string, receives ``avg`` as an argument
	:param float threshold_good:
		threshold for gradient level 0: any normalized load average below this
		value will have this gradient level.
	:param float threshold_bad:
		threshold for gradient level 100: any normalized load average above this
		value will have this gradient level. Load averages between
		``threshold_good`` and ``threshold_bad`` receive gradient level that
		indicates relative position in this interval:
		(``100 * (cur-good) / (bad-good)``).
		Note: both parameters are checked against normalized load averages.
	:param bool track_cpu_count:
		if True powerline will continuously poll the system to detect changes
		in the number of CPUs.

	Divider highlight group used: ``background:divider``.

	Highlight groups used: ``system_load_gradient`` (gradient) or ``system_load``.
	'''
	global cpu_count
	try:
		cpu_num = cpu_count = _cpu_count() if cpu_count is None or track_cpu_count else cpu_count
	except NotImplementedError:
		pl.warn('Unable to get CPU count: method is not implemented')
		return None
	ret = []
	for avg in os.getloadavg():
		normalized = avg / cpu_num
		if normalized < threshold_good:
			gradient_level = 0
		elif normalized < threshold_bad:
			gradient_level = (normalized - threshold_good) * 100.0 / (threshold_bad - threshold_good)
		else:
			gradient_level = 100
		ret.append({
			'contents': format.format(avg=avg),
			'highlight_group': ['system_load_gradient', 'system_load'],
			'divider_highlight_group': 'background:divider',
			'gradient_level': gradient_level,
		})
	ret[0]['contents'] += ' '
	ret[1]['contents'] += ' '
	return ret


try:
	import psutil

	def _get_bytes(interface):
		try:
			io_counters = psutil.net_io_counters(pernic=True)
		except AttributeError:
			io_counters = psutil.network_io_counters(pernic=True)
		if_io = io_counters.get(interface)
		if not if_io:
			return None
		return if_io.bytes_recv, if_io.bytes_sent

	def _get_interfaces():
		io_counters = psutil.network_io_counters(pernic=True)
		for interface, data in io_counters.items():
			if data:
				yield interface, data.bytes_recv, data.bytes_sent

	# psutil-2.0.0: psutil.Process.username is unbound method
	if callable(psutil.Process.username):
		def _get_user(segment_info):
			return psutil.Process(os.getpid()).username()
	# pre psutil-2.0.0: psutil.Process.username has type property
	else:
		def _get_user(segment_info):
			return psutil.Process(os.getpid()).username

	class CPULoadPercentSegment(ThreadedSegment):
		interval = 1

		def update(self, old_cpu):
			return psutil.cpu_percent(interval=None)

		def run(self):
			while not self.shutdown_event.is_set():
				try:
					self.update_value = psutil.cpu_percent(interval=self.interval)
				except Exception as e:
					self.exception('Exception while calculating cpu_percent: {0}', str(e))

		def render(self, cpu_percent, format='{0:.0f}%', **kwargs):
			if not cpu_percent:
				return None
			return [{
				'contents': format.format(cpu_percent),
				'gradient_level': cpu_percent,
				'highlight_group': ['cpu_load_percent_gradient', 'cpu_load_percent'],
			}]
except ImportError:
	def _get_bytes(interface):  # NOQA
		with open('/sys/class/net/{interface}/statistics/rx_bytes'.format(interface=interface), 'rb') as file_obj:
			rx = int(file_obj.read())
		with open('/sys/class/net/{interface}/statistics/tx_bytes'.format(interface=interface), 'rb') as file_obj:
			tx = int(file_obj.read())
		return (rx, tx)

	def _get_interfaces():  # NOQA
		for interface in os.listdir('/sys/class/net'):
			x = _get_bytes(interface)
			if x is not None:
				yield interface, x[0], x[1]

	def _get_user(segment_info):  # NOQA
		return segment_info['environ'].get('USER', None)

	class CPULoadPercentSegment(ThreadedSegment):  # NOQA
		interval = 1

		@staticmethod
		def startup(**kwargs):
			pass

		@staticmethod
		def start():
			pass

		@staticmethod
		def shutdown():
			pass

		@staticmethod
		def render(cpu_percent, pl, format='{0:.0f}%', **kwargs):
			pl.warn('psutil package is not installed, thus CPU load is not available')
			return None


cpu_load_percent = with_docstring(CPULoadPercentSegment(),
'''Return the average CPU load as a percentage.

Requires the ``psutil`` module.

:param str format:
	Output format. Accepts measured CPU load as the first argument.

Highlight groups used: ``cpu_load_percent_gradient`` (gradient) or ``cpu_load_percent``.
''')


username = False
# os.geteuid is not available on windows
_geteuid = getattr(os, 'geteuid', lambda: 1)


def user(pl, segment_info=None, hide_user=None):
	'''Return the current user.

	:param str hide_user:
		Omit showing segment for users with names equal to this string.

	Highlights the user with the ``superuser`` if the effective user ID is 0.

	Highlight groups used: ``superuser`` or ``user``. It is recommended to define all highlight groups.
	'''
	global username
	if username is False:
		username = _get_user(segment_info)
	if username is None:
		pl.warn('Failed to get username')
		return None
	if username == hide_user:
		return None
	euid = _geteuid()
	return [{
		'contents': username,
		'highlight_group': 'user' if euid != 0 else ['superuser', 'user'],
	}]
if 'psutil' not in globals():
	user = requires_segment_info(user)


if os.path.exists('/proc/uptime'):
	def _get_uptime():
		with open('/proc/uptime', 'r') as f:
			return int(float(f.readline().split()[0]))
elif 'psutil' in globals():
	from time import time

	def _get_uptime():  # NOQA
		# psutil.BOOT_TIME is not subject to clock adjustments, but time() is.
		# Thus it is a fallback to /proc/uptime reading and not the reverse.
		return int(time() - psutil.BOOT_TIME)
else:
	def _get_uptime():  # NOQA
		raise NotImplementedError


@add_divider_highlight_group('background:divider')
def uptime(pl, days_format='{days:d}d', hours_format=' {hours:d}h', minutes_format=' {minutes:d}m', seconds_format=' {seconds:d}s', shorten_len=3):
	'''Return system uptime.

	:param str days_format:
		day format string, will be passed ``days`` as the argument
	:param str hours_format:
		hour format string, will be passed ``hours`` as the argument
	:param str minutes_format:
		minute format string, will be passed ``minutes`` as the argument
	:param str seconds_format:
		second format string, will be passed ``seconds`` as the argument
	:param int shorten_len:
		shorten the amount of units (days, hours, etc.) displayed

	Divider highlight group used: ``background:divider``.
	'''
	try:
		seconds = _get_uptime()
	except NotImplementedError:
		pl.warn('Unable to get uptime. You should install psutil package')
		return None
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	time_formatted = list(filter(None, [
		days_format.format(days=days) if days and days_format else None,
		hours_format.format(hours=hours) if hours and hours_format else None,
		minutes_format.format(minutes=minutes) if minutes and minutes_format else None,
		seconds_format.format(seconds=seconds) if seconds and seconds_format else None,
		]))[0:shorten_len]
	return ''.join(time_formatted).strip()


class NetworkLoadSegment(KwThreadedSegment):
	interfaces = {}
	replace_num_pat = re.compile(r'[a-zA-Z]+')

	@staticmethod
	def key(interface='detect', **kwargs):
		return interface

	def compute_state(self, interface):
		if interface == 'detect':
			proc_exists = getattr(self, 'proc_exists', None)
			if proc_exists is None:
				proc_exists = self.proc_exists = os.path.exists('/proc/net/route')
			if proc_exists:
				# Look for default interface in routing table
				with open('/proc/net/route', 'rb') as f:
					for line in f.readlines():
						parts = line.split()
						if len(parts) > 1:
							iface, destination = parts[:2]
							if not destination.replace(b'0', b''):
								interface = iface.decode('utf-8')
								break
			if interface == 'detect':
				# Choose interface with most total activity, excluding some
				# well known interface names
				interface, total = 'eth0', -1
				for name, rx, tx in _get_interfaces():
					base = self.replace_num_pat.match(name)
					if None in (base, rx, tx) or base.group() in ('lo', 'vmnet', 'sit'):
						continue
					activity = rx + tx
					if activity > total:
						total = activity
						interface = name

		try:
			idata = self.interfaces[interface]
			try:
				idata['prev'] = idata['last']
			except KeyError:
				pass
		except KeyError:
			idata = {}
			if self.run_once:
				idata['prev'] = (monotonic(), _get_bytes(interface))
				self.shutdown_event.wait(self.interval)
			self.interfaces[interface] = idata

		idata['last'] = (monotonic(), _get_bytes(interface))
		return idata.copy()

	def render_one(self, idata, recv_format='⬇ {value:>8}', sent_format='⬆ {value:>8}', suffix='B/s', si_prefix=False, **kwargs):
		if not idata or 'prev' not in idata:
			return None

		t1, b1 = idata['prev']
		t2, b2 = idata['last']
		measure_interval = t2 - t1

		if None in (b1, b2):
			return None

		r = []
		for i, key in zip((0, 1), ('recv', 'sent')):
			format = locals()[key + '_format']
			try:
				value = (b2[i] - b1[i]) / measure_interval
			except ZeroDivisionError:
				self.warn('Measure interval zero.')
				value = 0
			max_key = key + '_max'
			is_gradient = max_key in kwargs
			hl_groups = ['network_load_' + key, 'network_load']
			if is_gradient:
				hl_groups[:0] = (group + '_gradient' for group in hl_groups)
			r.append({
				'contents': format.format(value=humanize_bytes(value, suffix, si_prefix)),
				'divider_highlight_group': 'background:divider',
				'highlight_group': hl_groups,
			})
			if is_gradient:
				max = kwargs[max_key]
				if value >= max:
					r[-1]['gradient_level'] = 100
				else:
					r[-1]['gradient_level'] = value * 100.0 / max

		return r


network_load = with_docstring(NetworkLoadSegment(),
'''Return the network load.

Uses the ``psutil`` module if available for multi-platform compatibility,
falls back to reading
:file:`/sys/class/net/{interface}/statistics/{rx,tx}_bytes`.

:param str interface:
	network interface to measure (use the special value "detect" to have powerline try to auto-detect the network interface)
:param str suffix:
	string appended to each load string
:param bool si_prefix:
	use SI prefix, e.g. MB instead of MiB
:param str recv_format:
	format string, receives ``value`` as argument
:param str sent_format:
	format string, receives ``value`` as argument
:param float recv_max:
	maximum number of received bytes per second. Is only used to compute
	gradient level
:param float sent_max:
	maximum number of sent bytes per second. Is only used to compute gradient
	level

Divider highlight group used: ``background:divider``.

Highlight groups used: ``network_load_sent_gradient`` (gradient) or ``network_load_recv_gradient`` (gradient) or ``network_load_gradient`` (gradient), ``network_load_sent`` or ``network_load_recv`` or ``network_load``.
''')


@requires_segment_info
def virtualenv(pl, segment_info):
	'''Return the name of the current Python virtualenv.'''
	return os.path.basename(segment_info['environ'].get('VIRTUAL_ENV', '')) or None


_IMAPKey = namedtuple('Key', 'username password server port folder')


class EmailIMAPSegment(KwThreadedSegment):
	interval = 60

	@staticmethod
	def key(username, password, server='imap.gmail.com', port=993, folder='INBOX', **kwargs):
		return _IMAPKey(username, password, server, port, folder)

	def compute_state(self, key):
		if not key.username or not key.password:
			self.warn('Username and password are not configured')
			return None
		try:
			import imaplib
		except imaplib.IMAP4.error as e:
			unread_count = str(e)
		else:
			mail = imaplib.IMAP4_SSL(key.server, key.port)
			mail.login(key.username, key.password)
			rc, message = mail.status(key.folder, '(UNSEEN)')
			unread_str = message[0].decode('utf-8')
			unread_count = int(re.search('UNSEEN (\d+)', unread_str).group(1))
		return unread_count

	@staticmethod
	def render_one(unread_count, max_msgs=None, **kwargs):
		if not unread_count:
			return None
		elif type(unread_count) != int or not max_msgs:
			return [{
				'contents': str(unread_count),
				'highlight_group': 'email_alert',
			}]
		else:
			return [{
				'contents': str(unread_count),
				'highlight_group': ['email_alert_gradient', 'email_alert'],
				'gradient_level': min(unread_count * 100.0 / max_msgs, 100),
			}]


email_imap_alert = with_docstring(EmailIMAPSegment(),
'''Return unread e-mail count for IMAP servers.

:param str username:
	login username
:param str password:
	login password
:param str server:
	e-mail server
:param int port:
	e-mail server port
:param str folder:
	folder to check for e-mails
:param int max_msgs:
	Maximum number of messages. If there are more messages then max_msgs then it
	will use gradient level equal to 100, otherwise gradient level is equal to
	``100 * msgs_num / max_msgs``. If not present gradient is not computed.

Highlight groups used: ``email_alert_gradient`` (gradient), ``email_alert``.
''')


class NowPlayingSegment(object):
	STATE_SYMBOLS = {
		'fallback': '♫',
		'play': '▶',
		'pause': '▮▮',
		'stop': '■',
	}

	def __call__(self, player='mpd', format='{state_symbol} {artist} - {title} ({total})', **kwargs):
		player_func = getattr(self, 'player_{0}'.format(player))
		stats = {
			'state': None,
			'state_symbol': self.STATE_SYMBOLS['fallback'],
			'album': None,
			'artist': None,
			'title': None,
			'elapsed': None,
			'total': None,
		}
		func_stats = player_func(**kwargs)
		if not func_stats:
			return None
		stats.update(func_stats)
		return format.format(**stats)

	@staticmethod
	def _convert_state(state):
		state = state.lower()
		if 'play' in state:
			return 'play'
		if 'pause' in state:
			return 'pause'
		if 'stop' in state:
			return 'stop'

	@staticmethod
	def _convert_seconds(seconds):
		return '{0:.0f}:{1:02.0f}'.format(*divmod(float(seconds), 60))

	def player_cmus(self, pl):
		'''Return cmus player information.

		cmus-remote -Q returns data with multi-level information i.e.
			status playing
			file <file_name>
			tag artist <artist_name>
			tag title <track_title>
			tag ..
			tag n
			set continue <true|false>
			set repeat <true|false>
			set ..
			set n

		For the information we are looking for we don't really care if we're on
		the tag level or the set level. The dictionary comprehension in this
		method takes anything in ignore_levels and brings the key inside that
		to the first level of the dictionary.
		'''
		now_playing_str = run_cmd(pl, ['cmus-remote', '-Q'])
		if not now_playing_str:
			return
		ignore_levels = ('tag', 'set',)
		now_playing = dict(((token[0] if token[0] not in ignore_levels else token[1],
			(' '.join(token[1:]) if token[0] not in ignore_levels else
			' '.join(token[2:]))) for token in [line.split(' ') for line in now_playing_str.split('\n')[:-1]]))
		state = self._convert_state(now_playing.get('status'))
		return {
			'state': state,
			'state_symbol': self.STATE_SYMBOLS.get(state),
			'album': now_playing.get('album'),
			'artist': now_playing.get('artist'),
			'title': now_playing.get('title'),
			'elapsed': self._convert_seconds(now_playing.get('position', 0)),
			'total': self._convert_seconds(now_playing.get('duration', 0)),
		}

	def player_mpd(self, pl, host='localhost', port=6600):
		try:
			import mpd
		except ImportError:
			now_playing = run_cmd(pl, ['mpc', 'current', '-f', '%album%\n%artist%\n%title%\n%time%', '-h', str(host), '-p', str(port)])
			if not now_playing:
				return
			now_playing = now_playing.split('\n')
			return {
				'album': now_playing[0],
				'artist': now_playing[1],
				'title': now_playing[2],
				'total': now_playing[3],
			}
		else:
			client = mpd.MPDClient()
			client.connect(host, port)
			now_playing = client.currentsong()
			if not now_playing:
				return
			status = client.status()
			client.close()
			client.disconnect()
			return {
				'state': status.get('state'),
				'state_symbol': self.STATE_SYMBOLS.get(status.get('state')),
				'album': now_playing.get('album'),
				'artist': now_playing.get('artist'),
				'title': now_playing.get('title'),
				'elapsed': self._convert_seconds(now_playing.get('elapsed', 0)),
				'total': self._convert_seconds(now_playing.get('time', 0)),
			}

	def player_spotify_dbus(self, pl, dbus=None):
		try:
			import dbus
		except ImportError:
			pl.exception('Could not add Spotify segment: requires python-dbus.')
			return
		bus = dbus.SessionBus()
		DBUS_IFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'
		DBUS_IFACE_PLAYER = 'org.freedesktop.MediaPlayer2'
		try:
			player = bus.get_object('com.spotify.qt', '/')
			iface = dbus.Interface(player, DBUS_IFACE_PROPERTIES)
			info = iface.Get(DBUS_IFACE_PLAYER, 'Metadata')
			status = iface.Get(DBUS_IFACE_PLAYER, 'PlaybackStatus')
		except dbus.exceptions.DBusException:
			return
		if not info:
			return
		state = self._convert_state(status)
		return {
			'state': state,
			'state_symbol': self.STATE_SYMBOLS.get(state),
			'album': info.get('xesam:album'),
			'artist': info.get('xesam:artist')[0],
			'title': info.get('xesam:title'),
			'total': self._convert_seconds(info.get('mpris:length') / 1e6),
		}

	def player_spotify_apple_script(self, pl):
		ascript = '''
		tell application "System Events"
			set process_list to (name of every process)
		end tell

		if process_list contains "Spotify" then
			tell application "Spotify"
				if player state is playing or player state is paused then
					set track_name to name of current track
					set artist_name to artist of current track
					set album_name to album of current track
					set track_length to duration of current track
					set trim_length to 40
					set now_playing to player state & album_name & artist_name & track_name & track_length
					if length of now_playing is less than trim_length then
						set now_playing_trim to now_playing
					else
						set now_playing_trim to characters 1 thru trim_length of now_playing as string
					end if
				else
					return player state
				end if

			end tell
		else
			return "stopped"
		end if
		'''

		spotify = asrun(pl, ascript)
		if not asrun:
			return None

		spotify_status = spotify.split(", ")
		state = self._convert_state(spotify_status[0])
		if state == 'stop':
			return None
		return {
			'state': state,
			'state_symbol': self.STATE_SYMBOLS.get(state),
			'album': spotify_status[1],
			'artist': spotify_status[2],
			'title': spotify_status[3],
			'total': self._convert_seconds(int(spotify_status[4]))
		}

	try:
		__import__('dbus')  # NOQA
	except ImportError:
		if sys.platform.startswith('darwin'):
			player_spotify = player_spotify_apple_script
		else:
			player_spotify = player_spotify_dbus  # NOQA
	else:
		player_spotify = player_spotify_dbus  # NOQA

	def player_rhythmbox(self, pl):
		now_playing = run_cmd(pl, ['rhythmbox-client', '--no-start', '--no-present', '--print-playing-format', '%at\n%aa\n%tt\n%te\n%td'])
		if not now_playing:
			return
		now_playing = now_playing.split('\n')
		return {
			'album': now_playing[0],
			'artist': now_playing[1],
			'title': now_playing[2],
			'elapsed': now_playing[3],
			'total': now_playing[4],
		}
now_playing = NowPlayingSegment()


try:
	if os.path.exists('/sys/class/power_supply/'):
		_linux_bat_fmt = '/sys/class/power_supply/{0}/capacity'
		_linux_bat = 'BAT0'
		if not os.path.exists(_linux_bat_fmt.format(_linux_bat)):
			_linux_bat = 'BAT1'
		if not os.path.exists(_linux_bat_fmt.format(_linux_bat)):
			raise NotImplementedError
		def _get_capacity(pl):
			with open(_linux_bat_fmt.format(_linux_bat), 'r') as f:
				return int(float(f.readline().split()[0]))
	else:
		raise NotImplementedError
except NotImplementedError:
	if os.path.exists('/usr/bin/pmset'):
		def _get_capacity(pl):
			import re
			battery_summary = run_cmd(pl, ['pmset', '-g', 'batt'])
			battery_percent = re.search(r'(\d+)%', battery_summary).group(1)
			return int(battery_percent)
	else:
		def _get_capacity(pl):
			raise NotImplementedError


def battery(pl, format='{capacity:3.0%}', steps=5, gamify=False, full_heart='♥', empty_heart='♥'):
	'''Return battery charge status.

	:param str format:
		Percent format in case gamify is False.
	:param int steps:
		Number of discrete steps to show between 0% and 100% capacity if gamify
		is True.
	:param bool gamify:
		Measure in hearts (♥) instead of percentages.
	:param str full_heart:
		Heart displayed for “full” part of battery.
	:param str empty_heart:
		Heart displayed for “used” part of battery. It is also displayed using
		another gradient level, so it is OK for it to be the same as full_heart.

	Highlight groups used: ``battery_gradient`` (gradient), ``battery``.
	'''
	try:
		capacity = _get_capacity(pl)
	except NotImplementedError:
		pl.warn('Unable to get battery capacity.')
		return None
	ret = []
	if gamify:
		denom = int(steps)
		numer = int(denom * capacity / 100)
		ret.append({
			'contents': full_heart * numer,
			'draw_inner_divider': False,
			'highlight_group': ['battery_gradient', 'battery'],
			'gradient_level': 99,
		})
		ret.append({
			'contents': empty_heart * (denom - numer),
			'draw_inner_divider': False,
			'highlight_group': ['battery_gradient', 'battery'],
			'gradient_level': 1,
		})
	else:
		ret.append({
			'contents': format.format(capacity=(capacity / 100.0)),
			'highlight_group': ['battery_gradient', 'battery'],
			'gradient_level': capacity,
		})
	return ret

########NEW FILE########
__FILENAME__ = i3wm
# vim:fileencoding=utf-8:noet

import i3


def calcgrp(w):
	group = []
	if w['focused']:
		group.append('w_focused')
	if w['urgent']:
		group.append('w_urgent')
	if w['visible']:
		group.append('w_visible')
	group.append('workspace')
	return group


def workspaces(pl):
	'''Return workspace list

	Highlight groups used: ``workspace``, ``w_visible``, ``w_focused``, ``w_urgent``
	'''
	return [{
		'contents': w['name'],
		'highlight_group': calcgrp(w)
	} for w in i3.get_workspaces()]

########NEW FILE########
__FILENAME__ = ipython
# vim:fileencoding=utf-8:noet

from powerline.theme import requires_segment_info


@requires_segment_info
def prompt_count(pl, segment_info):
	return str(segment_info['ipython'].prompt_count)

########NEW FILE########
__FILENAME__ = ctrlp
# vim:fileencoding=utf-8:noet

try:
	import vim
except ImportError:
	vim = object()  # NOQA

from powerline.bindings.vim import getbufvar
from powerline.segments.vim import window_cached


@window_cached
def ctrlp(pl, side):
	'''

	Highlight groups used: ``ctrlp.regex`` or ``background``, ``ctrlp.prev`` or ``background``, ``ctrlp.item`` or ``file_name``, ``ctrlp.next`` or ``background``, ``ctrlp.marked`` or ``background``, ``ctrlp.focus`` or ``background``, ``ctrlp.byfname`` or ``background``, ``ctrlp.progress`` or ``file_name``, ``ctrlp.progress`` or ``file_name``.
	'''
	ctrlp_type = getbufvar('%', 'powerline_ctrlp_type')
	ctrlp_args = getbufvar('%', 'powerline_ctrlp_args')

	return globals()['ctrlp_stl_{0}_{1}'.format(side, ctrlp_type)](pl, *ctrlp_args)


def ctrlp_stl_left_main(pl, focus, byfname, regex, prev, item, next, marked):
	'''

	Highlight groups used: ``ctrlp.regex`` or ``background``, ``ctrlp.prev`` or ``background``, ``ctrlp.item`` or ``file_name``, ``ctrlp.next`` or ``background``, ``ctrlp.marked`` or ``background``.
	'''
	marked = marked[2:-1]
	segments = []

	if int(regex):
		segments.append({
			'contents': 'regex',
			'highlight_group': ['ctrlp.regex', 'background'],
			})

	segments += [
		{
			'contents': prev + ' ',
			'highlight_group': ['ctrlp.prev', 'background'],
			'draw_inner_divider': True,
			'priority': 40,
		},
		{
			'contents': item,
			'highlight_group': ['ctrlp.item', 'file_name'],
			'draw_inner_divider': True,
			'width': 10,
			'align': 'c',
		},
		{
			'contents': ' ' + next,
			'highlight_group': ['ctrlp.next', 'background'],
			'draw_inner_divider': True,
			'priority': 40,
		},
	]

	if marked != '-':
		segments.append({
			'contents': marked,
			'highlight_group': ['ctrlp.marked', 'background'],
			'draw_inner_divider': True,
			})

	return segments


def ctrlp_stl_right_main(pl, focus, byfname, regex, prev, item, next, marked):
	'''

	Highlight groups used: ``ctrlp.focus`` or ``background``, ``ctrlp.byfname`` or ``background``.
	'''
	segments = [
		{
			'contents': focus,
			'highlight_group': ['ctrlp.focus', 'background'],
			'draw_inner_divider': True,
			'priority': 50,
		},
		{
			'contents': byfname,
			'highlight_group': ['ctrlp.byfname', 'background'],
			'priority': 50,
		},
	]

	return segments


def ctrlp_stl_left_prog(pl, progress):
	'''

	Highlight groups used: ``ctrlp.progress`` or ``file_name``.
	'''
	return [
		{
			'contents': 'Loading...',
			'highlight_group': ['ctrlp.progress', 'file_name'],
		},
	]


def ctrlp_stl_right_prog(pl, progress):
	'''

	Highlight groups used: ``ctrlp.progress`` or ``file_name``.
	'''
	return [
		{
			'contents': progress,
			'highlight_group': ['ctrlp.progress', 'file_name'],
		},
	]

########NEW FILE########
__FILENAME__ = nerdtree
# vim:fileencoding=utf-8:noet

try:
	import vim
except ImportError:
	vim = object()  # NOQA

from powerline.bindings.vim import bufvar_exists
from powerline.segments.vim import window_cached


@window_cached
def nerdtree(pl):
	'''Return directory that is shown by the current buffer.

	Highlight groups used: ``nerdtree.path`` or ``file_name``.
	'''
	if not bufvar_exists(None, 'NERDTreeRoot'):
		return None
	path_str = vim.eval('getbufvar("%", "NERDTreeRoot").path.str()')
	return [{
		'contents': path_str,
		'highlight_group': ['nerdtree.path', 'file_name'],
	}]

########NEW FILE########
__FILENAME__ = syntastic
# vim:fileencoding=utf-8:noet

try:
	import vim
except ImportError:
	vim = object()  # NOQA

from powerline.segments.vim import window_cached


@window_cached
def syntastic(pl, err_format='ERR:  {first_line} ({num}) ', warn_format='WARN:  {first_line} ({num}) '):
	'''Show whether syntastic has found any errors or warnings

	:param str err_format:
		Format string for errors.

	:param str warn_format:
		Format string for warnings.

	Highlight groups used: ``syntastic.warning`` or ``warning``, ``syntastic.error`` or ``error``.
	'''
	if not int(vim.eval('exists("g:SyntasticLoclist")')):
		return
	has_errors = int(vim.eval('g:SyntasticLoclist.current().hasErrorsOrWarningsToDisplay()'))
	if not has_errors:
		return
	errors = vim.eval('g:SyntasticLoclist.current().errors()')
	warnings = vim.eval('g:SyntasticLoclist.current().warnings()')
	segments = []
	if errors:
		segments.append({
			'contents': err_format.format(first_line=errors[0]['lnum'], num=len(errors)),
			'highlight_group': ['syntastic.error', 'error'],
		})
	if warnings:
		segments.append({
			'contents': warn_format.format(first_line=warnings[0]['lnum'], num=len(warnings)),
			'highlight_group': ['syntastic.warning', 'warning'],
		})
	return segments

########NEW FILE########
__FILENAME__ = tagbar
# vim:fileencoding=utf-8:noet

try:
	import vim
except ImportError:
	vim = object()  # NOQA

from powerline.segments.vim import window_cached


@window_cached
def current_tag(pl):
	if not int(vim.eval('exists(":Tagbar")')):
		return
	return vim.eval('tagbar#currenttag("%s", "")')

########NEW FILE########
__FILENAME__ = shell
# vim:fileencoding=utf-8:noet

from powerline.theme import requires_segment_info


@requires_segment_info
def jobnum(pl, segment_info, show_zero=False):
	'''Return the number of jobs.

	:param bool show_zero:
		If False (default) shows nothing if there are no jobs. Otherwise shows 
		zero for no jobs.
	'''
	jobnum = segment_info['args'].jobnum
	if jobnum is None or (not show_zero and jobnum == 0):
		return None
	else:
		return str(jobnum)


@requires_segment_info
def last_status(pl, segment_info):
	'''Return last exit code.

	Highlight groups used: ``exit_fail``
	'''
	if not segment_info['args'].last_exit_code:
		return None
	return [{'contents': str(segment_info['args'].last_exit_code), 'highlight_group': 'exit_fail'}]


@requires_segment_info
def last_pipe_status(pl, segment_info):
	'''Return last pipe status.

	Highlight groups used: ``exit_fail``, ``exit_success``
	'''
	last_pipe_status = segment_info['args'].last_pipe_status
	if any(last_pipe_status):
		return [{'contents': str(status), 'highlight_group': 'exit_fail' if status else 'exit_success', 'draw_inner_divider': True}
			for status in last_pipe_status]
	else:
		return None


@requires_segment_info
def mode(pl, segment_info, override={'vicmd': 'COMMND', 'viins': 'INSERT'}, default=None):
	'''Return the current mode.

	:param dict override:
		dict for overriding mode strings.
	:param str default:
		If current mode is equal to this string then this segment will not get 
		displayed. If not specified the value is taken from 
		``$POWERLINE_DEFAULT_MODE`` variable. This variable is set by zsh 
		bindings for any mode that does not start from ``vi``.
	'''
	mode = segment_info['mode']
	if not mode:
		pl.debug('No or empty _POWERLINE_MODE variable')
		return None
	default = default or segment_info['environ'].get('_POWERLINE_DEFAULT_MODE')
	if mode == default:
		return None
	try:
		return override[mode]
	except KeyError:
		# Note: with zsh line editor you can emulate as much modes as you wish. 
		# Thus having unknown mode is not an error: maybe just some developer 
		# added support for his own zle widgets. As there is no built-in mode() 
		# function like in VimL and _POWERLINE_MODE is likely be defined by our 
		# code or by somebody knowing what he is doing there is absolutely no 
		# need in keeping translations dictionary.
		return mode.upper()


@requires_segment_info
def continuation(pl, segment_info, omit_cmdsubst=True, right_align=False, renames={}):
	'''Display parser state.

	:param bool omit_cmdsubst:
		Do not display cmdsubst parser state if it is the last one.
	:param bool right_align:
		Align to the right.
	:param dict renames:
		Rename states: ``{old_name : new_name}``. If ``new_name`` is ``None`` 
		then given state is not displayed.

	Highlight groups used: ``continuation``, ``continuation:current``.
	'''
	if not segment_info.get('parser_state'):
		return None
	ret = []

	for state in segment_info['parser_state'].split():
		state = renames.get(state, state)
		if state:
			ret.append({
				'contents': state,
				'highlight_group': 'continuation',
				'draw_inner_divider': True,
			})

	if omit_cmdsubst and ret[-1]['contents'] == 'cmdsubst':
		ret.pop(-1)

	if not ret:
		ret.append({
			'contents': ''
		})

	if right_align:
		ret[0].update(width='auto', align='r')
		ret[-1]['highlight_group'] = 'continuation:current'
	else:
		ret[-1].update(width='auto', align='l', highlight_group='continuation:current')

	return ret

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet

from __future__ import unicode_literals, absolute_import, division

import os
try:
	import vim
except ImportError:
	vim = {}  # NOQA

from powerline.bindings.vim import (vim_get_func, getbufvar, vim_getbufoption,
									buffer_name, vim_getwinvar)
from powerline.theme import requires_segment_info
from powerline.lib import add_divider_highlight_group
from powerline.lib.vcs import guess, tree_status
from powerline.lib.humanize_bytes import humanize_bytes
from powerline.lib import wraps_saveargs as wraps
from collections import defaultdict

vim_funcs = {
	'virtcol': vim_get_func('virtcol', rettype=int),
	'getpos': vim_get_func('getpos'),
	'fnamemodify': vim_get_func('fnamemodify'),
	'expand': vim_get_func('expand'),
	'bufnr': vim_get_func('bufnr', rettype=int),
	'line2byte': vim_get_func('line2byte', rettype=int),
	'line': vim_get_func('line', rettype=int),
}

vim_modes = {
	'n': 'NORMAL',
	'no': 'N·OPER',
	'v': 'VISUAL',
	'V': 'V·LINE',
	'^V': 'V·BLCK',
	's': 'SELECT',
	'S': 'S·LINE',
	'^S': 'S·BLCK',
	'i': 'INSERT',
	'R': 'REPLACE',
	'Rv': 'V·RPLCE',
	'c': 'COMMND',
	'cv': 'VIM EX',
	'ce': 'EX',
	'r': 'PROMPT',
	'rm': 'MORE',
	'r?': 'CONFIRM',
	'!': 'SHELL',
}


eventfuncs = defaultdict(lambda: [])
bufeventfuncs = defaultdict(lambda: [])
defined_events = set()


# TODO Remove cache when needed
def window_cached(func):
	cache = {}

	@requires_segment_info
	@wraps(func)
	def ret(segment_info, **kwargs):
		window_id = segment_info['window_id']
		if segment_info['mode'] == 'nc':
			return cache.get(window_id)
		else:
			r = func(**kwargs)
			cache[window_id] = r
			return r

	return ret


@requires_segment_info
def mode(pl, segment_info, override=None):
	'''Return the current vim mode.

	:param dict override:
		dict for overriding default mode strings, e.g. ``{ 'n': 'NORM' }``
	'''
	mode = segment_info['mode']
	if mode == 'nc':
		return None
	if not override:
		return vim_modes[mode]
	try:
		return override[mode]
	except KeyError:
		return vim_modes[mode]


@requires_segment_info
def visual_range(pl, segment_info):
	'''Return the current visual selection range.

	Returns a value similar to `showcmd`.
	'''
	if segment_info['mode'] not in ('v', 'V', '^V'):
		return None
	pos_start = vim_funcs['getpos']('v')
	pos_end = vim_funcs['getpos']('.')
	# Workaround for vim's "excellent" handling of multibyte characters and display widths
	pos_start[2] = vim_funcs['virtcol']([pos_start[1], pos_start[2], pos_start[3]])
	pos_end[2] = vim_funcs['virtcol']([pos_end[1], pos_end[2], pos_end[3]])
	visual_start = (int(pos_start[1]), int(pos_start[2]))
	visual_end = (int(pos_end[1]), int(pos_end[2]))
	diff_rows = abs(visual_end[0] - visual_start[0]) + 1
	diff_cols = abs(visual_end[1] - visual_start[1]) + 1
	if segment_info['mode'] == '^V':
		return '{0} × {1}'.format(diff_rows, diff_cols)
	elif segment_info['mode'] == 'V' or diff_rows > 1:
		return '{0} rows'.format(diff_rows)
	else:
		return '{0} cols'.format(diff_cols)


@requires_segment_info
def modified_indicator(pl, segment_info, text='+'):
	'''Return a file modified indicator.

	:param string text:
		text to display if the current buffer is modified
	'''
	return text if int(vim_getbufoption(segment_info, 'modified')) else None


@requires_segment_info
def paste_indicator(pl, segment_info, text='PASTE'):
	'''Return a paste mode indicator.

	:param string text:
		text to display if paste mode is enabled
	'''
	return text if int(vim.eval('&paste')) else None


@requires_segment_info
def readonly_indicator(pl, segment_info, text=''):
	'''Return a read-only indicator.

	:param string text:
		text to display if the current buffer is read-only
	'''
	return text if int(vim_getbufoption(segment_info, 'readonly')) else None


@requires_segment_info
def file_directory(pl, segment_info, shorten_user=True, shorten_cwd=True, shorten_home=False):
	'''Return file directory (head component of the file path).

	:param bool shorten_user:
		shorten ``$HOME`` directory to :file:`~/`

	:param bool shorten_cwd:
		shorten current directory to :file:`./`

	:param bool shorten_home:
		shorten all directories in :file:`/home/` to :file:`~user/` instead of :file:`/home/user/`.
	'''
	name = buffer_name(segment_info['buffer'])
	if not name:
		return None
	file_directory = vim_funcs['fnamemodify'](name, (':~' if shorten_user else '')
												+ (':.' if shorten_cwd else '') + ':h')
	if not file_directory:
		return None
	if shorten_home and file_directory.startswith('/home/'):
		file_directory = b'~' + file_directory[6:]
	file_directory = file_directory.decode('utf-8', 'powerline_vim_strtrans_error')
	return file_directory + os.sep


@requires_segment_info
def file_name(pl, segment_info, display_no_file=False, no_file_text='[No file]'):
	'''Return file name (tail component of the file path).

	:param bool display_no_file:
		display a string if the buffer is missing a file name
	:param str no_file_text:
		the string to display if the buffer is missing a file name

	Highlight groups used: ``file_name_no_file`` or ``file_name``, ``file_name``.
	'''
	name = buffer_name(segment_info['buffer'])
	if not name:
		if display_no_file:
			return [{
				'contents': no_file_text,
				'highlight_group': ['file_name_no_file', 'file_name'],
			}]
		else:
			return None
	return os.path.basename(name).decode('utf-8', 'powerline_vim_strtrans_error')


@window_cached
def file_size(pl, suffix='B', si_prefix=False):
	'''Return file size in &encoding.

	:param str suffix:
		string appended to the file size
	:param bool si_prefix:
		use SI prefix, e.g. MB instead of MiB
	:return: file size or None if the file isn't saved or if the size is too big to fit in a number
	'''
	# Note: returns file size in &encoding, not in &fileencoding. But returned 
	# size is updated immediately; and it is valid for any buffer
	file_size = vim_funcs['line2byte'](len(vim.current.buffer) + 1) - 1
	if file_size < 0:
		file_size = 0
	return humanize_bytes(file_size, suffix, si_prefix)


@requires_segment_info
@add_divider_highlight_group('background:divider')
def file_format(pl, segment_info):
	'''Return file format (i.e. line ending type).

	:return: file format or None if unknown or missing file format

	Divider highlight group used: ``background:divider``.
	'''
	return vim_getbufoption(segment_info, 'fileformat') or None


@requires_segment_info
@add_divider_highlight_group('background:divider')
def file_encoding(pl, segment_info):
	'''Return file encoding/character set.

	:return: file encoding/character set or None if unknown or missing file encoding

	Divider highlight group used: ``background:divider``.
	'''
	return vim_getbufoption(segment_info, 'fileencoding') or None


@requires_segment_info
@add_divider_highlight_group('background:divider')
def file_type(pl, segment_info):
	'''Return file type.

	:return: file type or None if unknown file type

	Divider highlight group used: ``background:divider``.
	'''
	return vim_getbufoption(segment_info, 'filetype') or None


@requires_segment_info
def window_title(pl, segment_info):
	'''Return the window title.

	This currently looks at the ``quickfix_title`` window variable,
	which is used by Syntastic and Vim itself.

	It is used in the quickfix theme.'''
	try:
		return vim_getwinvar(segment_info, 'quickfix_title')
	except KeyError:
		return None


@requires_segment_info
def line_percent(pl, segment_info, gradient=False):
	'''Return the cursor position in the file as a percentage.

	:param bool gradient:
		highlight the percentage with a color gradient (by default a green to red gradient)

	Highlight groups used: ``line_percent_gradient`` (gradient), ``line_percent``.
	'''
	line_current = segment_info['window'].cursor[0]
	line_last = len(segment_info['buffer'])
	percentage = line_current * 100.0 / line_last
	if not gradient:
		return str(int(round(percentage)))
	return [{
		'contents': str(int(round(percentage))),
		'highlight_group': ['line_percent_gradient', 'line_percent'],
		'gradient_level': percentage,
	}]


@window_cached
def position(pl, position_strings={'top': 'Top', 'bottom': 'Bot', 'all': 'All'}, gradient=False):
	'''Return the position of the current view in the file as a percentage.

	:param dict position_strings:
		dict for translation of the position strings, e.g. ``{"top":"Oben", "bottom":"Unten", "all":"Alles"}``

	:param bool gradient:
		highlight the percentage with a color gradient (by default a green to red gradient)

	Highlight groups used: ``position_gradient`` (gradient), ``position``.
	'''
	line_last = len(vim.current.buffer)

	winline_first = vim_funcs['line']('w0')
	winline_last = vim_funcs['line']('w$')
	if winline_first == 1 and winline_last == line_last:
		percentage = 0.0
		content = position_strings['all']
	elif winline_first == 1:
		percentage = 0.0
		content = position_strings['top']
	elif winline_last == line_last:
		percentage = 100.0
		content = position_strings['bottom']
	else:
		percentage = winline_first * 100.0 / (line_last - winline_last + winline_first)
		content = str(int(round(percentage))) + '%'

	if not gradient:
		return content
	return [{
		'contents': content,
		'highlight_group': ['position_gradient', 'position'],
		'gradient_level': percentage,
	}]


@requires_segment_info
def line_current(pl, segment_info):
	'''Return the current cursor line.'''
	return str(segment_info['window'].cursor[0])


@requires_segment_info
def col_current(pl, segment_info):
	'''Return the current cursor column.
	'''
	return str(segment_info['window'].cursor[1] + 1)


# TODO Add &textwidth-based gradient
@window_cached
def virtcol_current(pl, gradient=True):
	'''Return current visual column with concealed characters ingored

	:param bool gradient:
		Determines whether it should show textwidth-based gradient (gradient level is ``virtcol * 100 / textwidth``).

	Highlight groups used: ``virtcol_current_gradient`` (gradient), ``virtcol_current`` or ``col_current``.
	'''
	col = vim_funcs['virtcol']('.')
	r = [{'contents': str(col), 'highlight_group': ['virtcol_current', 'col_current']}]
	if gradient:
		textwidth = int(getbufvar('%', '&textwidth'))
		r[-1]['gradient_level'] = min(col * 100 / textwidth, 100) if textwidth else 0
		r[-1]['highlight_group'].insert(0, 'virtcol_current_gradient')
	return r


def modified_buffers(pl, text='+ ', join_str=','):
	'''Return a comma-separated list of modified buffers.

	:param str text:
		text to display before the modified buffer list
	:param str join_str:
		string to use for joining the modified buffer list
	'''
	buffer_len = vim_funcs['bufnr']('$')
	buffer_mod = [str(bufnr) for bufnr in range(1, buffer_len + 1) if int(getbufvar(bufnr, '&modified') or 0)]
	if buffer_mod:
		return text + join_str.join(buffer_mod)
	return None


@requires_segment_info
def branch(pl, segment_info, status_colors=False):
	'''Return the current working branch.

	:param bool status_colors:
		determines whether repository status will be used to determine highlighting. Default: False.

	Highlight groups used: ``branch_clean``, ``branch_dirty``, ``branch``.

	Divider highlight group used: ``branch:divider``.
	'''
	name = segment_info['buffer'].name
	skip = not (name and (not vim_getbufoption(segment_info, 'buftype')))
	if not skip:
		repo = guess(path=name)
		if repo is not None:
			branch = repo.branch()
			scol = ['branch']
			if status_colors:
				status = tree_status(repo, pl)
				scol.insert(0, 'branch_dirty' if status and status.strip() else 'branch_clean')
			return [{
				'contents': branch,
				'highlight_group': scol,
				'divider_highlight_group': 'branch:divider',
			}]


@requires_segment_info
def file_vcs_status(pl, segment_info):
	'''Return the VCS status for this buffer.

	Highlight groups used: ``file_vcs_status``.
	'''
	name = segment_info['buffer'].name
	skip = not (name and (not vim_getbufoption(segment_info, 'buftype')))
	if not skip:
		repo = guess(path=name)
		if repo is not None:
			status = repo.status(os.path.relpath(name, repo.directory))
			if not status:
				return None
			status = status.strip()
			ret = []
			for status in status:
				ret.append({
					'contents': status,
					'highlight_group': ['file_vcs_status_' + status, 'file_vcs_status'],
					})
			return ret

########NEW FILE########
__FILENAME__ = shell
# vim:fileencoding=utf-8:noet

from powerline import Powerline
from powerline.lib import mergedicts, parsedotval


def mergeargs(argvalue):
	if not argvalue:
		return None
	r = {}
	for subval in argvalue:
		mergedicts(r, dict([subval]))
	return r


class ShellPowerline(Powerline):
	def __init__(self, args, **kwargs):
		self.args = args
		self.theme_option = args.theme_option
		super(ShellPowerline, self).__init__(args.ext[0], args.renderer_module, **kwargs)

	def load_main_config(self):
		r = super(ShellPowerline, self).load_main_config()
		if self.args.config:
			mergedicts(r, self.args.config)
		return r

	def load_theme_config(self, name):
		r = super(ShellPowerline, self).load_theme_config(name)
		if self.theme_option and name in self.theme_option:
			mergedicts(r, self.theme_option[name])
		return r

	def get_config_paths(self):
		if self.args.config_path:
			return [self.args.config_path]
		else:
			return super(ShellPowerline, self).get_config_paths()

	def get_local_themes(self, local_themes):
		if not local_themes:
			return {}

		return dict(((key, {'config': self.load_theme_config(val)})
					for key, val in local_themes.items()))


def get_argparser(parser=None, *args, **kwargs):
	if not parser:
		import argparse
		parser = argparse.ArgumentParser
	p = parser(*args, **kwargs)
	p.add_argument('ext', nargs=1)
	p.add_argument('side', nargs='?', choices=('left', 'right'))
	p.add_argument('-r', '--renderer_module', metavar='MODULE', type=str)
	p.add_argument('-w', '--width', type=int)
	p.add_argument('--last_exit_code', metavar='INT', type=int)
	p.add_argument('--last_pipe_status', metavar='LIST', default='', type=lambda s: [int(status) for status in s.split()])
	p.add_argument('--jobnum', metavar='INT', type=int)
	p.add_argument('-c', '--config', metavar='KEY.KEY=VALUE', action='append')
	p.add_argument('-t', '--theme_option', metavar='THEME.KEY.KEY=VALUE', action='append')
	p.add_argument('-p', '--config_path', metavar='PATH')
	p.add_argument('-R', '--renderer_arg', metavar='KEY=VAL', action='append')
	return p


def finish_args(args):
	if args.config:
		args.config = mergeargs((parsedotval(v) for v in args.config))
	if args.theme_option:
		args.theme_option = mergeargs((parsedotval(v) for v in args.theme_option))
	else:
		args.theme_option = {}
	if args.renderer_arg:
		args.renderer_arg = mergeargs((parsedotval(v) for v in args.renderer_arg))

########NEW FILE########
__FILENAME__ = theme
# vim:fileencoding=utf-8:noet

from powerline.segment import gen_segment_getter
from powerline.lib.unicode import u


def requires_segment_info(func):
	func.powerline_requires_segment_info = True
	return func


class Theme(object):
	def __init__(self,
				ext,
				theme_config,
				common_config,
				pl,
				top_theme_config=None,
				run_once=False,
				shutdown_event=None):
		self.dividers = theme_config.get('dividers', common_config['dividers'])
		self.spaces = theme_config.get('spaces', common_config['spaces'])
		self.segments = {
			'left': [],
			'right': [],
		}
		self.EMPTY_SEGMENT = {
			'contents': None,
			'highlight': {'fg': False, 'bg': False, 'attr': 0}
		}
		self.pl = pl
		theme_configs = [theme_config]
		if top_theme_config:
			theme_configs.append(top_theme_config)
		get_segment = gen_segment_getter(pl, ext, common_config['paths'], theme_configs, theme_config.get('default_module'))
		for side in ['left', 'right']:
			for segment in theme_config['segments'].get(side, []):
				segment = get_segment(segment, side)
				if not run_once:
					if segment['startup']:
						try:
							segment['startup'](pl, shutdown_event)
						except Exception as e:
							pl.error('Exception during {0} startup: {1}', segment['name'], str(e))
							continue
				self.segments[side].append(segment)

	def shutdown(self):
		for segments in self.segments.values():
			for segment in segments:
				try:
					segment['shutdown']()
				except TypeError:
					pass

	def get_divider(self, side='left', type='soft'):
		'''Return segment divider.'''
		return self.dividers[side][type]

	def get_spaces(self):
		return self.spaces

	def get_segments(self, side=None, segment_info=None):
		'''Return all segments.

		Function segments are called, and all segments get their before/after
		and ljust/rjust properties applied.
		'''
		for side in [side] if side else ['left', 'right']:
			parsed_segments = []
			for segment in self.segments[side]:
				if segment['type'] == 'function':
					self.pl.prefix = segment['name']
					try:
						contents = segment['contents_func'](self.pl, segment_info)
					except Exception as e:
						self.pl.exception('Exception while computing segment: {0}', str(e))
						continue

					if contents is None:
						continue
					if isinstance(contents, list):
						segment_base = segment.copy()
						if contents:
							draw_divider_position = -1 if side == 'left' else 0
							for key, i, newval in (
								('before', 0, ''),
								('after', -1, ''),
								('draw_soft_divider', draw_divider_position, True),
								('draw_hard_divider', draw_divider_position, True),
							):
								try:
									contents[i][key] = segment_base.pop(key)
									segment_base[key] = newval
								except KeyError:
									pass

						draw_inner_divider = None
						if side == 'right':
							append = parsed_segments.append
						else:
							pslen = len(parsed_segments)
							append = lambda item: parsed_segments.insert(pslen, item)

						for subsegment in (contents if side == 'right' else reversed(contents)):
							segment_copy = segment_base.copy()
							segment_copy.update(subsegment)
							if draw_inner_divider is not None:
								segment_copy['draw_soft_divider'] = draw_inner_divider
							draw_inner_divider = segment_copy.pop('draw_inner_divider', None)
							append(segment_copy)
					else:
						segment['contents'] = contents
						parsed_segments.append(segment)
				elif segment['width'] == 'auto' or (segment['type'] == 'string' and segment['contents'] is not None):
					parsed_segments.append(segment)
				else:
					continue
			for segment in parsed_segments:
				segment['contents'] = segment['before'] + u(segment['contents'] if segment['contents'] is not None else '') + segment['after']
				# Align segment contents
				if segment['width'] and segment['width'] != 'auto':
					if segment['align'] == 'l':
						segment['contents'] = segment['contents'].ljust(segment['width'])
					elif segment['align'] == 'r':
						segment['contents'] = segment['contents'].rjust(segment['width'])
					elif segment['align'] == 'c':
						segment['contents'] = segment['contents'].center(segment['width'])
				# We need to yield a copy of the segment, or else mode-dependent
				# segment contents can't be cached correctly e.g. when caching
				# non-current window contents for vim statuslines
				yield segment.copy()

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet

from __future__ import absolute_import

from powerline.bindings.vim import vim_get_func, vim_getvar
from powerline import Powerline
from powerline.lib import mergedicts
from powerline.matcher import gen_matcher_getter
import vim
from itertools import count

if not hasattr(vim, 'bindeval'):
	import json


def _override_from(config, override_varname):
	try:
		overrides = vim_getvar(override_varname)
	except KeyError:
		return config
	mergedicts(config, overrides)
	return config


class VimPowerline(Powerline):
	def __init__(self, pyeval='PowerlinePyeval'):
		super(VimPowerline, self).__init__('vim')
		self.last_window_id = 1
		self.window_statusline = '%!' + pyeval + '(\'powerline.statusline({0})\')'

	def add_local_theme(self, key, config):
		'''Add local themes at runtime (during vim session).

		:param str key:
			Matcher name (in format ``{matcher_module}.{module_attribute}`` or 
			``{module_attribute}`` if ``{matcher_module}`` is 
			``powerline.matchers.vim``). Function pointed by 
			``{module_attribute}`` should be hashable and accept a dictionary 
			with information about current buffer and return boolean value 
			indicating whether current window matched conditions. See also 
			:ref:`local_themes key description <config-ext-local_themes>`.

		:param dict config:
			:ref:`Theme <config-themes>` dictionary.

		:return:
			``True`` if theme was added successfully and ``False`` if theme with 
			the same matcher already exists.
		'''
		self.update_renderer()
		key = self.get_matcher(key)
		try:
			self.renderer.add_local_theme(key, {'config': config})
		except KeyError:
			return False
		else:
			return True

	def load_main_config(self):
		return _override_from(super(VimPowerline, self).load_main_config(), 'powerline_config_overrides')

	def load_theme_config(self, name):
		# Note: themes with non-[a-zA-Z0-9_] names are impossible to override 
		# (though as far as I know exists() won’t throw). Won’t fix, use proper 
		# theme names.
		return _override_from(super(VimPowerline, self).load_theme_config(name),
						'powerline_theme_overrides__' + name)

	def get_local_themes(self, local_themes):
		if not local_themes:
			return {}

		self.get_matcher = gen_matcher_getter(self.ext, self.import_paths)
		return dict(((self.get_matcher(key), {'config': self.load_theme_config(val)})
					for key, val in local_themes.items()))

	def get_config_paths(self):
		try:
			return [vim_getvar('powerline_config_path')]
		except KeyError:
			return super(VimPowerline, self).get_config_paths()

	@staticmethod
	def get_segment_info():
		return {}

	def reset_highlight(self):
		try:
			self.renderer.reset_highlight()
		except AttributeError:
			# Renderer object appears only after first `.render()` call. Thus if 
			# ColorScheme event happens before statusline is drawn for the first 
			# time AttributeError will be thrown for the self.renderer. It is 
			# fine to ignore it: no renderer == no colors to reset == no need to 
			# do anything.
			pass

	if all((hasattr(vim.current.window, attr) for attr in ('options', 'vars', 'number'))):
		def win_idx(self, window_id):
			r = None
			for window in vim.windows:
				try:
					curwindow_id = window.vars['powerline_window_id']
					if r is not None and curwindow_id == window_id:
						raise KeyError
				except KeyError:
					curwindow_id = self.last_window_id
					self.last_window_id += 1
					window.vars['powerline_window_id'] = curwindow_id
				statusline = self.window_statusline.format(curwindow_id)
				if window.options['statusline'] != statusline:
					window.options['statusline'] = statusline
				if curwindow_id == window_id if window_id else window is vim.current.window:
					r = (window, curwindow_id, window.number)
			return r
	else:
		_vim_getwinvar = staticmethod(vim_get_func('getwinvar'))
		_vim_setwinvar = staticmethod(vim_get_func('setwinvar'))

		def win_idx(self, window_id):  # NOQA
			r = None
			for winnr, window in zip(count(1), vim.windows):
				curwindow_id = self._vim_getwinvar(winnr, 'powerline_window_id')
				if curwindow_id and not (r is not None and curwindow_id == window_id):
					curwindow_id = int(curwindow_id)
				else:
					curwindow_id = self.last_window_id
					self.last_window_id += 1
					self._vim_setwinvar(winnr, 'powerline_window_id', curwindow_id)
				statusline = self.window_statusline.format(curwindow_id)
				if self._vim_getwinvar(winnr, '&statusline') != statusline:
					self._vim_setwinvar(winnr, '&statusline', statusline)
				if curwindow_id == window_id if window_id else window is vim.current.window:
					r = (window, curwindow_id, winnr)
			return r

	def statusline(self, window_id):
		window, window_id, winnr = self.win_idx(window_id) or (None, None, None)
		if not window:
			return 'No window {0}'.format(window_id)
		return self.render(window, window_id, winnr)

	def new_window(self):
		window, window_id, winnr = self.win_idx(None)
		return self.render(window, window_id, winnr)

	if not hasattr(vim, 'bindeval'):
		# Method for PowerlinePyeval function. Is here to reduce the number of 
		# requirements to __main__ globals to just one powerline object 
		# (previously it required as well vim and json)
		@staticmethod
		def pyeval():
			import __main__
			vim.command('return ' + json.dumps(eval(vim.eval('a:e'),
													__main__.__dict__)))


def setup(pyeval=None, pycmd=None):
	import sys
	import __main__
	if not pyeval:
		pyeval = 'pyeval' if sys.version_info < (3,) else 'py3eval'
	if not pycmd:
		pycmd = 'python' if sys.version_info < (3,) else 'python3'

	# pyeval() and vim.bindeval were both introduced in one patch
	if not hasattr(vim, 'bindeval'):
		vim.command(('''
				function! PowerlinePyeval(e)
					{pycmd} powerline.pyeval()
				endfunction
			''').format(pycmd=pycmd))
		pyeval = 'PowerlinePyeval'

	powerline = VimPowerline(pyeval)
	__main__.powerline = powerline

	# Cannot have this in one line due to weird newline handling (in :execute 
	# context newline is considered part of the command in just the same cases 
	# when bar is considered part of the command (unless defining function 
	# inside :execute)). vim.command is :execute equivalent regarding this case.
	vim.command('augroup Powerline')
	vim.command('	autocmd! ColorScheme * :{pycmd} powerline.reset_highlight()'.format(pycmd=pycmd))
	vim.command('	autocmd! VimLeavePre * :{pycmd} powerline.shutdown()'.format(pycmd=pycmd))
	vim.command('augroup END')

	# Is immediately changed after new_window function is run. Good for global 
	# value.
	vim.command('set statusline=%!{pyeval}(\'powerline.new_window()\')'.format(pyeval=pyeval))

########NEW FILE########
__FILENAME__ = config_mock
# vim:fileencoding=utf-8:noet
from threading import Lock
from powerline.renderer import Renderer
from powerline.lib.config import ConfigLoader
from powerline import Powerline
from copy import deepcopy
from functools import wraps


access_log = []
access_lock = Lock()


def load_json_config(config_file_path, *args, **kwargs):
	global access_log
	with access_lock:
		access_log.append(config_file_path)
	try:
		return deepcopy(config_container['config'][config_file_path])
	except KeyError:
		raise IOError(config_file_path)


def find_config_file(config, search_paths, config_file):
	if config_file.endswith('raise') and config_file not in config:
		raise IOError('fcf:' + config_file)
	return config_file


def pop_events():
	global access_log
	with access_lock:
		r = access_log[:]
		access_log = []
	return r


def log_call(func):
	@wraps(func)
	def ret(self, *args, **kwargs):
		self._calls.append((func.__name__, args, kwargs))
		return func(self, *args, **kwargs)
	return ret


class Watcher(object):
	events = set()
	lock = Lock()

	def __init__(self):
		self._calls = []

	@log_call
	def watch(self, file):
		pass

	@log_call
	def __call__(self, file):
		with self.lock:
			if file in self.events:
				self.events.remove(file)
				return True
		return False

	def _reset(self, files):
		with self.lock:
			self.events.clear()
			self.events.update(files)

	@log_call
	def unsubscribe(self):
		pass


class Logger(object):
	def __init__(self):
		self.messages = []
		self.lock = Lock()

	def _add_msg(self, attr, msg):
		with self.lock:
			self.messages.append(attr + ':' + msg)

	def _pop_msgs(self):
		with self.lock:
			r = self.messages
			self.messages = []
		return r

	def __getattr__(self, attr):
		return lambda *args, **kwargs: self._add_msg(attr, *args, **kwargs)


class SimpleRenderer(Renderer):
	def hlstyle(self, fg=None, bg=None, attr=None):
		return '<{fg} {bg} {attr}>'.format(fg=fg and fg[0], bg=bg and bg[0], attr=attr)


class TestPowerline(Powerline):
	_created = False

	@staticmethod
	def get_local_themes(local_themes):
		return local_themes

	def _will_create_renderer(self):
		return self.create_renderer_kwargs


renderer = SimpleRenderer


def get_powerline(**kwargs):
	watcher = Watcher()
	pl = TestPowerline(
		ext='test',
		renderer_module='tests.lib.config_mock',
		logger=Logger(),
		config_loader=ConfigLoader(load=load_json_config, watcher=watcher, run_once=kwargs.get('run_once')),
		**kwargs
	)
	pl._watcher = watcher
	return pl


config_container = None


def swap_attributes(cfg_container, powerline_module, replaces):
	global config_container
	config_container = cfg_container
	if not replaces:
		replaces = {
			'find_config_file': lambda *args: find_config_file(config_container['config'], *args),
		}
	for attr, val in replaces.items():
		old_val = getattr(powerline_module, attr)
		setattr(powerline_module, attr, val)
		replaces[attr] = old_val
	return replaces

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet
from tests import vim


globals().update(vim._init())

########NEW FILE########
__FILENAME__ = test_cmdline
# vim:fileencoding=utf-8:noet

'''Tests for shell.py parser'''


from powerline.shell import get_argparser, finish_args
from tests import TestCase
from tests.lib import replace_attr
import sys
if sys.version_info < (3,):
	from io import BytesIO as StrIO
else:
	from io import StringIO as StrIO  # NOQA


class TestParser(TestCase):
	def test_main_err(self):
		parser = get_argparser()
		out = StrIO()
		err = StrIO()

		def flush():
			out.truncate(0)
			err.truncate(0)

		with replace_attr(sys, 'stdout', out, 'stderr', err):
			for raising_args, raising_reg in [
				([],                                     'too few arguments|the following arguments are required: ext'),
				(['-r'],                                 'expected one argument'),
				(['shell', '-r'],                        'expected one argument'),
				(['shell', '-w'],                        'expected one argument'),
				(['shell', '-c'],                        'expected one argument'),
				(['shell', '-t'],                        'expected one argument'),
				(['shell', '-p'],                        'expected one argument'),
				(['shell', '-R'],                        'expected one argument'),
				(['shell', '--renderer_module'],         'expected one argument'),
				(['shell', '--width'],                   'expected one argument'),
				(['shell', '--last_exit_code'],          'expected one argument'),
				(['shell', '--last_pipe_status'],        'expected one argument'),
				(['shell', '--config'],                  'expected one argument'),
				(['shell', '--theme_option'],            'expected one argument'),
				(['shell', '--config_path'],             'expected one argument'),
				(['shell', '--renderer_arg'],            'expected one argument'),
				(['shell', '--jobnum'],                  'expected one argument'),
				(['-r', 'zsh_prompt'],                   'too few arguments|the following arguments are required: ext'),
				(['shell', '--last_exit_code', 'i'],     'invalid int value'),
				(['shell', '--last_pipe_status', '1 i'], 'invalid <lambda> value'),
			]:
				self.assertRaises(SystemExit, parser.parse_args, raising_args)
				self.assertFalse(out.getvalue())
				self.assertRegexpMatches(err.getvalue(), raising_reg)
				flush()

	def test_main_normal(self):
		parser = get_argparser()
		out = StrIO()
		err = StrIO()
		with replace_attr(sys, 'stdout', out, 'stderr', err):
			for argv, expargs in [
				(['shell'],                     {'ext': ['shell']}),
				(['shell', '-r', 'zsh_prompt'], {'ext': ['shell'], 'renderer_module': 'zsh_prompt'}),
				([
					'shell',
					'left',
					'-r', 'zsh_prompt',
					'--last_exit_code', '10',
					'--last_pipe_status', '10 20 30',
					'--jobnum=10',
					'-w', '100',
					'-c', 'common.term_truecolor=true',
					'-c', 'common.spaces=4',
					'-t', 'default.segment_data.hostname.before=H:',
					'-p', '.',
					'-R', 'smth={"abc":"def"}',
				], {
					'ext': ['shell'],
					'side': 'left',
					'renderer_module': 'zsh_prompt',
					'last_exit_code': 10,
					'last_pipe_status': [10, 20, 30],
					'jobnum': 10,
					'width': 100,
					'config': {'common': {'term_truecolor': True, 'spaces': 4}},
					'theme_option': {
						'default': {
							'segment_data': {
								'hostname': {
									'before': 'H:'
								}
							}
						}
					},
					'config_path': '.',
					'renderer_arg': {'smth': {'abc': 'def'}},
				}),
				(['shell', '-R', 'arg=true'], {'ext': ['shell'], 'renderer_arg': {'arg': True}}),
				(['shell', '-R', 'arg=true', '-R', 'arg='], {'ext': ['shell'], 'renderer_arg': {}}),
				(['shell', '-R', 'arg='], {'ext': ['shell'], 'renderer_arg': {}}),
				(['shell', '-t', 'default.segment_info={"hostname": {}}'], {
					'ext': ['shell'],
					'theme_option': {
						'default': {
							'segment_info': {
								'hostname': {}
							}
						}
					},
				}),
				(['shell', '-c', 'common={ }'], {'ext': ['shell'], 'config': {'common': {}}}),
			]:
				args = parser.parse_args(argv)
				finish_args(args)
				for key, val in expargs.items():
					self.assertEqual(getattr(args, key), val)
				for key, val in args.__dict__.items():
					if key not in expargs:
						self.assertFalse(val, msg='key {0} is {1} while it should be something false'.format(key, val))
				self.assertFalse(err.getvalue() + out.getvalue(), msg='unexpected output: {0!r} {1!r}'.format(
					err.getvalue(),
					out.getvalue(),
				))


if __name__ == '__main__':
	from tests import main
	main()

########NEW FILE########
__FILENAME__ = test_configuration
# vim:fileencoding=utf-8:noet

'''Dynamic configuration files tests.'''


import tests.vim as vim_module
import sys
import os
import json
from tests.lib import Args, urllib_read, replace_attr
from tests import TestCase


VBLOCK = chr(ord('V') - 0x40)
SBLOCK = chr(ord('S') - 0x40)


class TestConfig(TestCase):
	def test_vim(self):
		from powerline.vim import VimPowerline
		cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'powerline', 'config_files')
		buffers = (
			(('bufoptions',), {'buftype': 'help'}),
			(('bufname', '[Command Line]'), {}),
			(('bufoptions',), {'buftype': 'quickfix'}),
			(('bufname', 'NERD_tree_1'), {}),
			(('bufname', '__Gundo__'), {}),
			(('bufname', '__Gundo_Preview__'), {}),
			(('bufname', 'ControlP'), {}),
		)
		with open(os.path.join(cfg_path, 'config.json'), 'r') as f:
			local_themes_raw = json.load(f)['ext']['vim']['local_themes']
			# Don't run tests on external/plugin segments
			local_themes = dict((k, v) for (k, v) in local_themes_raw.items())
			self.assertEqual(len(buffers), len(local_themes))
		outputs = {}
		i = 0

		with vim_module._with('split'):
			with VimPowerline() as powerline:
				def check_output(mode, args, kwargs):
					if mode == 'nc':
						window = vim_module.windows[0]
						window_id = 2
					else:
						vim_module._start_mode(mode)
						window = vim_module.current.window
						window_id = 1
					winnr = window.number
					out = powerline.render(window, window_id, winnr)
					if out in outputs:
						self.fail('Duplicate in set #{0} ({1}) for mode {2!r} (previously defined in set #{3} ({4!r}) for mode {5!r})'.format(i, (args, kwargs), mode, *outputs[out]))
					outputs[out] = (i, (args, kwargs), mode)

				with vim_module._with('bufname', '/tmp/foo.txt'):
					with vim_module._with('globals', powerline_config_path=cfg_path):
						exclude = set(('no', 'v', 'V', VBLOCK, 's', 'S', SBLOCK, 'R', 'Rv', 'c', 'cv', 'ce', 'r', 'rm', 'r?', '!'))
						try:
							for mode in ['n', 'nc', 'no', 'v', 'V', VBLOCK, 's', 'S', SBLOCK, 'i', 'R', 'Rv', 'c', 'cv', 'ce', 'r', 'rm', 'r?', '!']:
								check_output(mode, None, None)
								for args, kwargs in buffers:
									i += 1
									if mode in exclude:
										continue
									if mode == 'nc' and args == ('bufname', 'ControlP'):
										# ControlP window is not supposed to not 
										# be in the focus
										continue
									with vim_module._with(*args, **kwargs):
										check_output(mode, args, kwargs)
						finally:
							vim_module._start_mode('n')

	def test_tmux(self):
		from powerline.segments import common
		from imp import reload
		reload(common)
		from powerline.shell import ShellPowerline
		with replace_attr(common, 'urllib_read', urllib_read):
			with ShellPowerline(Args(ext=['tmux']), run_once=False) as powerline:
				powerline.render()
			with ShellPowerline(Args(ext=['tmux']), run_once=False) as powerline:
				powerline.render()

	def test_zsh(self):
		from powerline.shell import ShellPowerline
		args = Args(last_pipe_status=[1, 0], jobnum=0, ext=['shell'], renderer_module='zsh_prompt')
		segment_info = {'args': args}
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info=segment_info)
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info=segment_info)
		segment_info['local_theme'] = 'select'
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info=segment_info)
		segment_info['local_theme'] = 'continuation'
		segment_info['parser_state'] = 'if cmdsubst'
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info=segment_info)

	def test_bash(self):
		from powerline.shell import ShellPowerline
		args = Args(last_exit_code=1, jobnum=0, ext=['shell'], renderer_module='bash_prompt', config={'ext': {'shell': {'theme': 'default_leftonly'}}})
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info={'args': args})
		with ShellPowerline(args, run_once=False) as powerline:
			powerline.render(segment_info={'args': args})

	def test_ipython(self):
		from powerline.ipython import IpythonPowerline

		class IpyPowerline(IpythonPowerline):
			path = None
			config_overrides = None
			theme_overrides = {}

		with IpyPowerline() as powerline:
			segment_info = Args(prompt_count=1)
			for prompt_type in ['in', 'in2', 'out', 'rewrite']:
				powerline.render(matcher_info=prompt_type, segment_info=segment_info)
				powerline.render(matcher_info=prompt_type, segment_info=segment_info)

	def test_wm(self):
		from powerline.segments import common
		from imp import reload
		reload(common)
		from powerline import Powerline
		with replace_attr(common, 'urllib_read', urllib_read):
			Powerline(ext='wm', renderer_module='pango_markup', run_once=True).render()
		reload(common)


old_cwd = None


def setUpModule():
	global old_cwd
	sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'path')))
	old_cwd = os.getcwd()
	from powerline.segments import vim
	globals()['vim'] = vim


def tearDownModule():
	global old_cwd
	os.chdir(old_cwd)
	old_cwd = None
	sys.path.pop(0)


if __name__ == '__main__':
	from tests import main
	main()

########NEW FILE########
__FILENAME__ = test_config_reload
# vim:fileencoding=utf-8:noet
from __future__ import unicode_literals
import powerline as powerline_module
import time
from tests import TestCase
from tests.lib import replace_item
from tests.lib.config_mock import swap_attributes, get_powerline, pop_events
from copy import deepcopy


config = {
	'config': {
		'common': {
			'dividers': {
				"left": {
					"hard": ">>",
					"soft": ">",
				},
				"right": {
					"hard": "<<",
					"soft": "<",
				},
			},
			'spaces': 0,
			'interval': 0,
		},
		'ext': {
			'test': {
				'theme': 'default',
				'colorscheme': 'default',
			},
		},
	},
	'colors': {
		'colors': {
			"col1": 1,
			"col2": 2,
			"col3": 3,
			"col4": 4,
		},
		'gradients': {
		},
	},
	'colorschemes/test/default': {
		'groups': {
			"str1": {"fg": "col1", "bg": "col2", "attr": ["bold"]},
			"str2": {"fg": "col3", "bg": "col4", "attr": ["underline"]},
		},
	},
	'colorschemes/test/2': {
		'groups': {
			"str1": {"fg": "col2", "bg": "col3", "attr": ["bold"]},
			"str2": {"fg": "col1", "bg": "col4", "attr": ["underline"]},
		},
	},
	'themes/test/default': {
		'segments': {
			"left": [
				{
					"type": "string",
					"contents": "s",
					"highlight_group": ["str1"],
				},
				{
					"type": "string",
					"contents": "g",
					"highlight_group": ["str2"],
				},
			],
			"right": [
			],
		},
	},
	'themes/test/2': {
		'segments': {
			"left": [
				{
					"type": "string",
					"contents": "t",
					"highlight_group": ["str1"],
				},
				{
					"type": "string",
					"contents": "b",
					"highlight_group": ["str2"],
				},
			],
			"right": [
			],
		},
	},
}


def sleep(interval):
	time.sleep(interval)


def add_watcher_events(p, *args, **kwargs):
	p._watcher._reset(args)
	while not p._will_create_renderer():
		sleep(kwargs.get('interval', 0.1))
		if not kwargs.get('wait', True):
			return


class TestConfigReload(TestCase):
	def assertAccessEvents(self, *args):
		self.assertEqual(set(pop_events()), set(args))

	def test_noreload(self):
		with get_powerline(run_once=True) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')
				config['config']['common']['spaces'] = 1
				add_watcher_events(p, 'config', wait=False, interval=0.05)
				# When running once thread should not start
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents()
				self.assertEqual(p.logger._pop_msgs(), [])
		# Without the following assertion test_reload_colors may fail for 
		# unknown reason (with AssertionError telling about “config” accessed 
		# one more time then needed)
		pop_events()

	def test_reload_main(self):
		with get_powerline(run_once=False) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['config']['common']['spaces'] = 1
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<1 2 1> s <2 4 False>>><3 4 4>g <4 False False>>><None None None>')
				self.assertAccessEvents('config')
				self.assertEqual(p.logger._pop_msgs(), [])

				config['config']['ext']['test']['theme'] = 'nonexistent'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<1 2 1> s <2 4 False>>><3 4 4>g <4 False False>>><None None None>')
				self.assertAccessEvents('config', 'themes/test/nonexistent')
				# It should normally handle file missing error
				self.assertEqual(p.logger._pop_msgs(), ['exception:test:powerline:Failed to create renderer: themes/test/nonexistent'])

				config['config']['ext']['test']['theme'] = 'default'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<1 2 1> s <2 4 False>>><3 4 4>g <4 False False>>><None None None>')
				self.assertAccessEvents('config', 'themes/test/default')
				self.assertEqual(p.logger._pop_msgs(), [])

				config['config']['ext']['test']['colorscheme'] = 'nonexistent'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<1 2 1> s <2 4 False>>><3 4 4>g <4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colorschemes/test/nonexistent')
				# It should normally handle file missing error
				self.assertEqual(p.logger._pop_msgs(), ['exception:test:powerline:Failed to create renderer: colorschemes/test/nonexistent'])

				config['config']['ext']['test']['colorscheme'] = '2'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<2 3 1> s <3 4 False>>><1 4 4>g <4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colorschemes/test/2')
				self.assertEqual(p.logger._pop_msgs(), [])

				config['config']['ext']['test']['theme'] = '2'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<2 3 1> t <3 4 False>>><1 4 4>b <4 False False>>><None None None>')
				self.assertAccessEvents('config', 'themes/test/2')
				self.assertEqual(p.logger._pop_msgs(), [])

				self.assertEqual(p.renderer.local_themes, None)
				config['config']['ext']['test']['local_themes'] = 'something'
				add_watcher_events(p, 'config')
				self.assertEqual(p.render(), '<2 3 1> t <3 4 False>>><1 4 4>b <4 False False>>><None None None>')
				self.assertAccessEvents('config')
				self.assertEqual(p.logger._pop_msgs(), [])
				self.assertEqual(p.renderer.local_themes, 'something')
		pop_events()

	def test_reload_unexistent(self):
		with get_powerline(run_once=False) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['config']['ext']['test']['colorscheme'] = 'nonexistentraise'
				add_watcher_events(p, 'config')
				# It may appear that p.logger._pop_msgs() is called after given 
				# exception is added to the mesagges, but before config_loader 
				# exception was added (this one: 
				# “exception:test:config_loader:Error while running condition 
				# function for key colorschemes/test/nonexistentraise: 
				# fcf:colorschemes/test/nonexistentraise”).
				# sleep(0.1)
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config')
				self.assertIn('exception:test:powerline:Failed to create renderer: fcf:colorschemes/test/nonexistentraise', p.logger._pop_msgs())

				config['colorschemes/test/nonexistentraise'] = {
					'groups': {
						"str1": {"fg": "col1", "bg": "col3", "attr": ["bold"]},
						"str2": {"fg": "col2", "bg": "col4", "attr": ["underline"]},
					},
				}
				while not p._will_create_renderer():
					sleep(0.000001)
				self.assertEqual(p.render(), '<1 3 1> s<3 4 False>>><2 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('colorschemes/test/nonexistentraise')
				self.assertEqual(p.logger._pop_msgs(), [])
		pop_events()

	def test_reload_colors(self):
		with get_powerline(run_once=False) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['colors']['colors']['col1'] = 5
				add_watcher_events(p, 'colors')
				self.assertEqual(p.render(), '<5 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('colors')
				self.assertEqual(p.logger._pop_msgs(), [])
		pop_events()

	def test_reload_colorscheme(self):
		with get_powerline(run_once=False) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['colorschemes/test/default']['groups']['str1']['bg'] = 'col3'
				add_watcher_events(p, 'colorschemes/test/default')
				self.assertEqual(p.render(), '<1 3 1> s<3 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('colorschemes/test/default')
				self.assertEqual(p.logger._pop_msgs(), [])
		pop_events()

	def test_reload_theme(self):
		with get_powerline(run_once=False) as p:
			with replace_item(globals(), 'config', deepcopy(config)):
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['themes/test/default']['segments']['left'][0]['contents'] = 'col3'
				add_watcher_events(p, 'themes/test/default')
				self.assertEqual(p.render(), '<1 2 1> col3<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('themes/test/default')
				self.assertEqual(p.logger._pop_msgs(), [])
		pop_events()

	def test_reload_theme_main(self):
		with replace_item(globals(), 'config', deepcopy(config)):
			config['config']['common']['interval'] = None
			with get_powerline(run_once=False) as p:
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['themes/test/default']['segments']['left'][0]['contents'] = 'col3'
				add_watcher_events(p, 'themes/test/default', wait=False)
				self.assertEqual(p.render(), '<1 2 1> col3<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('themes/test/default')
				self.assertEqual(p.logger._pop_msgs(), [])
				self.assertTrue(p._watcher._calls)
		pop_events()

	def test_run_once_no_theme_reload(self):
		with replace_item(globals(), 'config', deepcopy(config)):
			config['config']['common']['interval'] = None
			with get_powerline(run_once=True) as p:
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents('config', 'colors', 'colorschemes/test/default', 'themes/test/default')

				config['themes/test/default']['segments']['left'][0]['contents'] = 'col3'
				add_watcher_events(p, 'themes/test/default', wait=False)
				self.assertEqual(p.render(), '<1 2 1> s<2 4 False>>><3 4 4>g<4 False False>>><None None None>')
				self.assertAccessEvents()
				self.assertEqual(p.logger._pop_msgs(), [])
				self.assertEqual(p._watcher._calls, [])
		pop_events()


replaces = {}


def setUpModule():
	global replaces
	replaces = swap_attributes(globals(), powerline_module, replaces)


tearDownModule = setUpModule


if __name__ == '__main__':
	from tests import main
	main()

########NEW FILE########
__FILENAME__ = test_lib
# vim:fileencoding=utf-8:noet
from __future__ import division

from powerline.lib import mergedicts, add_divider_highlight_group, REMOVE_THIS_KEY
from powerline.lib.humanize_bytes import humanize_bytes
from powerline.lib.vcs import guess
from powerline.lib.threaded import ThreadedSegment, KwThreadedSegment
from powerline.lib.monotonic import monotonic
import threading
import os
import sys
import re
from time import sleep
from subprocess import call, PIPE
from functools import partial
from tests import TestCase, SkipTest
from tests.lib import Pl


def thread_number():
	return len(threading.enumerate())


class TestThreaded(TestCase):
	def test_threaded_segment(self):
		log = []
		pl = Pl()
		updates = [(None,)]
		lock = threading.Lock()
		event = threading.Event()
		block_event = threading.Event()

		class TestSegment(ThreadedSegment):
			interval = 10

			def set_state(self, **kwargs):
				event.clear()
				log.append(('set_state', kwargs))
				return super(TestSegment, self).set_state(**kwargs)

			def update(self, update_value):
				block_event.wait()
				event.set()
				# Make sleep first to prevent some race conditions
				log.append(('update', update_value))
				with lock:
					ret = updates[0]
				if isinstance(ret, Exception):
					raise ret
				else:
					return ret[0]

			def render(self, update, **kwargs):
				log.append(('render', update, kwargs))
				if isinstance(update, Exception):
					raise update
				else:
					return update

		# Non-threaded tests
		segment = TestSegment()
		block_event.set()
		updates[0] = (None,)
		self.assertEqual(segment(pl=pl), None)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('set_state', {}),
			('update', None),
			('render', None, {'pl': pl, 'update_first': True}),
		])
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		updates[0] = ('abc',)
		self.assertEqual(segment(pl=pl), 'abc')
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('set_state', {}),
			('update', None),
			('render', 'abc', {'pl': pl, 'update_first': True}),
		])
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		updates[0] = ('abc',)
		self.assertEqual(segment(pl=pl, update_first=False), 'abc')
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('set_state', {}),
			('update', None),
			('render', 'abc', {'pl': pl, 'update_first': False}),
		])
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		updates[0] = ValueError('abc')
		self.assertEqual(segment(pl=pl), None)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(len(pl.exceptions), 1)
		self.assertEqual(log, [
			('set_state', {}),
			('update', None),
		])
		log[:] = ()
		pl.exceptions[:] = ()

		segment = TestSegment()
		block_event.set()
		updates[0] = (TypeError('def'),)
		self.assertRaises(TypeError, segment, pl=pl)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('set_state', {}),
			('update', None),
			('render', updates[0][0], {'pl': pl, 'update_first': True}),
		])
		log[:] = ()

		# Threaded tests
		segment = TestSegment()
		block_event.clear()
		kwargs = {'pl': pl, 'update_first': False, 'other': 1}
		with lock:
			updates[0] = ('abc',)
		segment.startup(**kwargs)
		ret = segment(**kwargs)
		self.assertEqual(thread_number(), 2)
		block_event.set()
		event.wait()
		segment.shutdown_event.set()
		segment.thread.join()
		self.assertEqual(ret, None)
		self.assertEqual(log, [
			('set_state', {'update_first': False, 'other': 1}),
			('render', None, {'pl': pl, 'update_first': False, 'other': 1}),
			('update', None),
		])
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		kwargs = {'pl': pl, 'update_first': True, 'other': 1}
		with lock:
			updates[0] = ('def',)
		segment.startup(**kwargs)
		ret = segment(**kwargs)
		self.assertEqual(thread_number(), 2)
		segment.shutdown_event.set()
		segment.thread.join()
		self.assertEqual(ret, 'def')
		self.assertEqual(log, [
			('set_state', {'update_first': True, 'other': 1}),
			('update', None),
			('render', 'def', {'pl': pl, 'update_first': True, 'other': 1}),
		])
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		kwargs = {'pl': pl, 'update_first': True, 'interval': 0.2}
		with lock:
			updates[0] = ('abc',)
		segment.startup(**kwargs)
		start = monotonic()
		ret1 = segment(**kwargs)
		with lock:
			updates[0] = ('def',)
		self.assertEqual(thread_number(), 2)
		sleep(0.5)
		ret2 = segment(**kwargs)
		segment.shutdown_event.set()
		segment.thread.join()
		end = monotonic()
		duration = end - start
		self.assertEqual(ret1, 'abc')
		self.assertEqual(ret2, 'def')
		self.assertEqual(log[:5], [
			('set_state', {'update_first': True, 'interval': 0.2}),
			('update', None),
			('render', 'abc', {'pl': pl, 'update_first': True, 'interval': 0.2}),
			('update', 'abc'),
			('update', 'def'),
		])
		num_runs = len([e for e in log if e[0] == 'update'])
		self.assertAlmostEqual(duration / 0.2, num_runs, delta=1)
		log[:] = ()

		segment = TestSegment()
		block_event.set()
		kwargs = {'pl': pl, 'update_first': True, 'interval': 0.2}
		with lock:
			updates[0] = ('ghi',)
		segment.startup(**kwargs)
		start = monotonic()
		ret1 = segment(**kwargs)
		with lock:
			updates[0] = TypeError('jkl')
		self.assertEqual(thread_number(), 2)
		sleep(0.5)
		ret2 = segment(**kwargs)
		segment.shutdown_event.set()
		segment.thread.join()
		end = monotonic()
		duration = end - start
		self.assertEqual(ret1, 'ghi')
		self.assertEqual(ret2, None)
		self.assertEqual(log[:5], [
			('set_state', {'update_first': True, 'interval': 0.2}),
			('update', None),
			('render', 'ghi', {'pl': pl, 'update_first': True, 'interval': 0.2}),
			('update', 'ghi'),
			('update', 'ghi'),
		])
		num_runs = len([e for e in log if e[0] == 'update'])
		self.assertAlmostEqual(duration / 0.2, num_runs, delta=1)
		self.assertEqual(num_runs - 1, len(pl.exceptions))
		log[:] = ()

	def test_kw_threaded_segment(self):
		log = []
		pl = Pl()
		event = threading.Event()

		class TestSegment(KwThreadedSegment):
			interval = 10

			@staticmethod
			def key(_key=(None,), **kwargs):
				log.append(('key', _key, kwargs))
				return _key

			def compute_state(self, key):
				event.set()
				sleep(0.1)
				log.append(('compute_state', key))
				ret = key
				if isinstance(ret, Exception):
					raise ret
				else:
					return ret[0]

			def render_one(self, state, **kwargs):
				log.append(('render_one', state, kwargs))
				if isinstance(state, Exception):
					raise state
				else:
					return state

		# Non-threaded tests
		segment = TestSegment()
		event.clear()
		self.assertEqual(segment(pl=pl), None)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('key', (None,), {'pl': pl}),
			('compute_state', (None,)),
			('render_one', None, {'pl': pl}),
		])
		log[:] = ()

		segment = TestSegment()
		kwargs = {'pl': pl, '_key': ('abc',), 'update_first': False}
		event.clear()
		self.assertEqual(segment(**kwargs), 'abc')
		kwargs.update(_key=('def',))
		self.assertEqual(segment(**kwargs), 'def')
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('key', ('abc',), {'pl': pl}),
			('compute_state', ('abc',)),
			('render_one', 'abc', {'pl': pl, '_key': ('abc',)}),
			('key', ('def',), {'pl': pl}),
			('compute_state', ('def',)),
			('render_one', 'def', {'pl': pl, '_key': ('def',)}),
		])
		log[:] = ()

		segment = TestSegment()
		kwargs = {'pl': pl, '_key': ValueError('xyz'), 'update_first': False}
		event.clear()
		self.assertEqual(segment(**kwargs), None)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('key', kwargs['_key'], {'pl': pl}),
			('compute_state', kwargs['_key']),
		])
		log[:] = ()

		segment = TestSegment()
		kwargs = {'pl': pl, '_key': (ValueError('abc'),), 'update_first': False}
		event.clear()
		self.assertRaises(ValueError, segment, **kwargs)
		self.assertEqual(thread_number(), 1)
		self.assertEqual(log, [
			('key', kwargs['_key'], {'pl': pl}),
			('compute_state', kwargs['_key']),
			('render_one', kwargs['_key'][0], {'pl': pl, '_key': kwargs['_key']}),
		])
		log[:] = ()

		# Threaded tests
		segment = TestSegment()
		kwargs = {'pl': pl, 'update_first': False, '_key': ('_abc',)}
		event.clear()
		segment.startup(**kwargs)
		ret = segment(**kwargs)
		self.assertEqual(thread_number(), 2)
		segment.shutdown_event.set()
		segment.thread.join()
		self.assertEqual(ret, None)
		self.assertEqual(log[:2], [
			('key', kwargs['_key'], {'pl': pl}),
			('render_one', None, {'pl': pl, '_key': kwargs['_key']}),
		])
		self.assertLessEqual(len(log), 3)
		if len(log) > 2:
			self.assertEqual(log[2], ('compute_state', kwargs['_key']))
		log[:] = ()

		segment = TestSegment()
		kwargs = {'pl': pl, 'update_first': True, '_key': ('_abc',)}
		event.clear()
		segment.startup(**kwargs)
		ret1 = segment(**kwargs)
		kwargs.update(_key=('_def',))
		ret2 = segment(**kwargs)
		self.assertEqual(thread_number(), 2)
		segment.shutdown_event.set()
		segment.thread.join()
		self.assertEqual(ret1, '_abc')
		self.assertEqual(ret2, '_def')
		self.assertEqual(log, [
			('key', ('_abc',), {'pl': pl}),
			('compute_state', ('_abc',)),
			('render_one', '_abc', {'pl': pl, '_key': ('_abc',)}),
			('key', ('_def',), {'pl': pl}),
			('compute_state', ('_def',)),
			('render_one', '_def', {'pl': pl, '_key': ('_def',)}),
		])
		log[:] = ()


class TestLib(TestCase):
	def test_mergedicts(self):
		d = {}
		mergedicts(d, {'abc': {'def': 'ghi'}})
		self.assertEqual(d, {'abc': {'def': 'ghi'}})
		mergedicts(d, {'abc': {'def': {'ghi': 'jkl'}}})
		self.assertEqual(d, {'abc': {'def': {'ghi': 'jkl'}}})
		mergedicts(d, {})
		self.assertEqual(d, {'abc': {'def': {'ghi': 'jkl'}}})
		mergedicts(d, {'abc': {'mno': 'pqr'}})
		self.assertEqual(d, {'abc': {'def': {'ghi': 'jkl'}, 'mno': 'pqr'}})
		mergedicts(d, {'abc': {'def': REMOVE_THIS_KEY}})
		self.assertEqual(d, {'abc': {'mno': 'pqr'}})

	def test_add_divider_highlight_group(self):
		def decorated_function_name(**kwargs):
			return str(kwargs)
		func = add_divider_highlight_group('hl_group')(decorated_function_name)
		self.assertEqual(func.__name__, 'decorated_function_name')
		self.assertEqual(func(kw={}), [{'contents': repr({'kw': {}}), 'divider_highlight_group': 'hl_group'}])

	def test_humanize_bytes(self):
		self.assertEqual(humanize_bytes(0), '0 B')
		self.assertEqual(humanize_bytes(1), '1 B')
		self.assertEqual(humanize_bytes(1, suffix='bit'), '1 bit')
		self.assertEqual(humanize_bytes(1000, si_prefix=True), '1 kB')
		self.assertEqual(humanize_bytes(1024, si_prefix=True), '1 kB')
		self.assertEqual(humanize_bytes(1000000000, si_prefix=True), '1.00 GB')
		self.assertEqual(humanize_bytes(1000000000, si_prefix=False), '953.7 MiB')


class TestFilesystemWatchers(TestCase):
	def do_test_for_change(self, watcher, path):
		st = monotonic()
		while monotonic() - st < 1:
			if watcher(path):
				return
			sleep(0.1)
		self.fail('The change to {0} was not detected'.format(path))

	def test_file_watcher(self):
		from powerline.lib.file_watcher import create_file_watcher
		w = create_file_watcher(use_stat=False)
		if w.is_stat_based:
			raise SkipTest('This test is not suitable for a stat based file watcher')
		f1, f2, f3 = map(lambda x: os.path.join(INOTIFY_DIR, 'file%d' % x), (1, 2, 3))
		with open(f1, 'wb'):
			with open(f2, 'wb'):
				with open(f3, 'wb'):
					pass
		ne = os.path.join(INOTIFY_DIR, 'notexists')
		self.assertRaises(OSError, w, ne)
		self.assertTrue(w(f1))
		self.assertTrue(w(f2))
		os.utime(f1, None), os.utime(f2, None)
		self.do_test_for_change(w, f1)
		self.do_test_for_change(w, f2)
		# Repeat once
		os.utime(f1, None), os.utime(f2, None)
		self.do_test_for_change(w, f1)
		self.do_test_for_change(w, f2)
		# Check that no false changes are reported
		self.assertFalse(w(f1), 'Spurious change detected')
		self.assertFalse(w(f2), 'Spurious change detected')
		# Check that open the file with 'w' triggers a change
		with open(f1, 'wb'):
			with open(f2, 'wb'):
				pass
		self.do_test_for_change(w, f1)
		self.do_test_for_change(w, f2)
		# Check that writing to a file with 'a' triggers a change
		with open(f1, 'ab') as f:
			f.write(b'1')
		self.do_test_for_change(w, f1)
		# Check that deleting a file registers as a change
		os.unlink(f1)
		self.do_test_for_change(w, f1)
		# Test that changing the inode of a file does not cause it to stop
		# being watched
		os.rename(f3, f2)
		self.do_test_for_change(w, f2)
		self.assertFalse(w(f2), 'Spurious change detected')
		os.utime(f2, None)
		self.do_test_for_change(w, f2)

	def test_tree_watcher(self):
		from powerline.lib.tree_watcher import TreeWatcher
		tw = TreeWatcher()
		subdir = os.path.join(INOTIFY_DIR, 'subdir')
		os.mkdir(subdir)
		if tw.watch(INOTIFY_DIR).is_dummy:
			raise SkipTest('No tree watcher available')
		import shutil
		self.assertTrue(tw(INOTIFY_DIR))
		self.assertFalse(tw(INOTIFY_DIR))
		changed = partial(self.do_test_for_change, tw, INOTIFY_DIR)
		open(os.path.join(INOTIFY_DIR, 'tree1'), 'w').close()
		changed()
		open(os.path.join(subdir, 'tree1'), 'w').close()
		changed()
		os.unlink(os.path.join(subdir, 'tree1'))
		changed()
		os.rmdir(subdir)
		changed()
		os.mkdir(subdir)
		changed()
		os.rename(subdir, subdir + '1')
		changed()
		shutil.rmtree(subdir + '1')
		changed()
		os.mkdir(subdir)
		f = os.path.join(subdir, 'f')
		open(f, 'w').close()
		changed()
		with open(f, 'a') as s:
			s.write(' ')
		changed()
		os.rename(f, f + '1')
		changed()

use_mercurial = use_bzr = sys.version_info < (3, 0)


class TestVCS(TestCase):
	def do_branch_rename_test(self, repo, q):
		st = monotonic()
		while monotonic() - st < 1:
			# Give inotify time to deliver events
			ans = repo.branch()
			if hasattr(q, '__call__'):
				if q(ans):
					break
			else:
				if ans == q:
					break
			sleep(0.01)
		if hasattr(q, '__call__'):
			self.assertTrue(q(ans))
		else:
			self.assertEqual(ans, q)

	def test_git(self):
		repo = guess(path=GIT_REPO)
		self.assertNotEqual(repo, None)
		self.assertEqual(repo.branch(), 'master')
		self.assertEqual(repo.status(), None)
		self.assertEqual(repo.status('file'), None)
		with open(os.path.join(GIT_REPO, 'file'), 'w') as f:
			f.write('abc')
			f.flush()
			self.assertEqual(repo.status(), '  U')
			self.assertEqual(repo.status('file'), '??')
			call(['git', 'add', '.'], cwd=GIT_REPO)
			self.assertEqual(repo.status(), ' I ')
			self.assertEqual(repo.status('file'), 'A ')
			f.write('def')
			f.flush()
			self.assertEqual(repo.status(), 'DI ')
			self.assertEqual(repo.status('file'), 'AM')
		os.remove(os.path.join(GIT_REPO, 'file'))
		# Test changing branch
		self.assertEqual(repo.branch(), 'master')
		call(['git', 'branch', 'branch1'], cwd=GIT_REPO)
		call(['git', 'checkout', '-q', 'branch1'], cwd=GIT_REPO)
		self.do_branch_rename_test(repo, 'branch1')
		# For some reason the rest of this test fails on travis and only on
		# travis, and I can't figure out why
		if 'TRAVIS' in os.environ:
			raise SkipTest('Part of this test fails on Travis for unknown reasons')
		call(['git', 'branch', 'branch2'], cwd=GIT_REPO)
		call(['git', 'checkout', '-q', 'branch2'], cwd=GIT_REPO)
		self.do_branch_rename_test(repo, 'branch2')
		call(['git', 'checkout', '-q', '--detach', 'branch1'], cwd=GIT_REPO)
		self.do_branch_rename_test(repo, lambda b: re.match(r'^[a-f0-9]+$', b))

	if use_mercurial:
		def test_mercurial(self):
			repo = guess(path=HG_REPO)
			self.assertNotEqual(repo, None)
			self.assertEqual(repo.branch(), 'default')
			self.assertEqual(repo.status(), None)
			with open(os.path.join(HG_REPO, 'file'), 'w') as f:
				f.write('abc')
				f.flush()
				self.assertEqual(repo.status(), ' U')
				self.assertEqual(repo.status('file'), 'U')
				call(['hg', 'add', '.'], cwd=HG_REPO, stdout=PIPE)
				self.assertEqual(repo.status(), 'D ')
				self.assertEqual(repo.status('file'), 'A')
			os.remove(os.path.join(HG_REPO, 'file'))

	if use_bzr:
		def test_bzr(self):
			repo = guess(path=BZR_REPO)
			self.assertNotEqual(repo, None, 'No bzr repo found. Do you have bzr installed?')
			self.assertEqual(repo.branch(), 'test_powerline')
			self.assertEqual(repo.status(), None)
			with open(os.path.join(BZR_REPO, 'file'), 'w') as f:
				f.write('abc')
			self.assertEqual(repo.status(), ' U')
			self.assertEqual(repo.status('file'), '? ')
			call(['bzr', 'add', '-q', '.'], cwd=BZR_REPO, stdout=PIPE)
			self.assertEqual(repo.status(), 'D ')
			self.assertEqual(repo.status('file'), '+N')
			call(['bzr', 'commit', '-q', '-m', 'initial commit'], cwd=BZR_REPO)
			self.assertEqual(repo.status(), None)
			with open(os.path.join(BZR_REPO, 'file'), 'w') as f:
				f.write('def')
			self.assertEqual(repo.status(), 'D ')
			self.assertEqual(repo.status('file'), ' M')
			self.assertEqual(repo.status('notexist'), None)
			with open(os.path.join(BZR_REPO, 'ignored'), 'w') as f:
				f.write('abc')
			self.assertEqual(repo.status('ignored'), '? ')
			# Test changing the .bzrignore file should update status
			with open(os.path.join(BZR_REPO, '.bzrignore'), 'w') as f:
				f.write('ignored')
			self.assertEqual(repo.status('ignored'), None)
			# Test changing the dirstate file should invalidate the cache for
			# all files in the repo
			with open(os.path.join(BZR_REPO, 'file2'), 'w') as f:
				f.write('abc')
			call(['bzr', 'add', 'file2'], cwd=BZR_REPO, stdout=PIPE)
			call(['bzr', 'commit', '-q', '-m', 'file2 added'], cwd=BZR_REPO)
			with open(os.path.join(BZR_REPO, 'file'), 'a') as f:
				f.write('hello')
			with open(os.path.join(BZR_REPO, 'file2'), 'a') as f:
				f.write('hello')
			self.assertEqual(repo.status('file'), ' M')
			self.assertEqual(repo.status('file2'), ' M')
			call(['bzr', 'commit', '-q', '-m', 'multi'], cwd=BZR_REPO)
			self.assertEqual(repo.status('file'), None)
			self.assertEqual(repo.status('file2'), None)

			# Test changing branch
			call(['bzr', 'nick', 'branch1'], cwd=BZR_REPO, stdout=PIPE, stderr=PIPE)
			self.do_branch_rename_test(repo, 'branch1')

			# Test branch name/status changes when swapping repos
			for x in ('b1', 'b2'):
				d = os.path.join(BZR_REPO, x)
				os.mkdir(d)
				call(['bzr', 'init', '-q'], cwd=d)
				call(['bzr', 'nick', '-q', x], cwd=d)
				repo = guess(path=d)
				self.assertEqual(repo.branch(), x)
				self.assertFalse(repo.status())
				if x == 'b1':
					open(os.path.join(d, 'dirty'), 'w').close()
					self.assertTrue(repo.status())
			os.rename(os.path.join(BZR_REPO, 'b1'), os.path.join(BZR_REPO, 'b'))
			os.rename(os.path.join(BZR_REPO, 'b2'), os.path.join(BZR_REPO, 'b1'))
			os.rename(os.path.join(BZR_REPO, 'b'), os.path.join(BZR_REPO, 'b2'))
			for x, y in (('b1', 'b2'), ('b2', 'b1')):
				d = os.path.join(BZR_REPO, x)
				repo = guess(path=d)
				self.do_branch_rename_test(repo, y)
				if x == 'b1':
					self.assertFalse(repo.status())
				else:
					self.assertTrue(repo.status())

old_HGRCPATH = None
old_cwd = None


GIT_REPO = 'git_repo' + os.environ.get('PYTHON', '')
HG_REPO = 'hg_repo' + os.environ.get('PYTHON', '')
BZR_REPO = 'bzr_repo' + os.environ.get('PYTHON', '')
INOTIFY_DIR = 'inotify' + os.environ.get('PYTHON', '')


def setUpModule():
	global old_cwd
	global old_HGRCPATH
	old_cwd = os.getcwd()
	os.chdir(os.path.dirname(__file__))
	call(['git', 'init', '--quiet', GIT_REPO])
	assert os.path.isdir(GIT_REPO)
	call(['git', 'config', '--local', 'user.name', 'Foo'], cwd=GIT_REPO)
	call(['git', 'config', '--local', 'user.email', 'bar@example.org'], cwd=GIT_REPO)
	call(['git', 'commit', '--allow-empty', '--message', 'Initial commit', '--quiet'], cwd=GIT_REPO)
	if use_mercurial:
		old_HGRCPATH = os.environ.get('HGRCPATH')
		os.environ['HGRCPATH'] = ''
		call(['hg', 'init', HG_REPO])
		with open(os.path.join(HG_REPO, '.hg', 'hgrc'), 'w') as hgrc:
			hgrc.write('[ui]\n')
			hgrc.write('username = Foo <bar@example.org>\n')
	if use_bzr:
		call(['bzr', 'init', '--quiet', BZR_REPO])
		call(['bzr', 'config', 'email=Foo <bar@example.org>'], cwd=BZR_REPO)
		call(['bzr', 'config', 'nickname=test_powerline'], cwd=BZR_REPO)
		call(['bzr', 'config', 'create_signatures=0'], cwd=BZR_REPO)
	os.mkdir(INOTIFY_DIR)


def tearDownModule():
	global old_cwd
	global old_HGRCPATH
	for repo_dir in [INOTIFY_DIR, GIT_REPO] + ([HG_REPO] if use_mercurial else []) + ([BZR_REPO] if use_bzr else []):
		for root, dirs, files in list(os.walk(repo_dir, topdown=False)):
			for file in files:
				os.remove(os.path.join(root, file))
			for dir in dirs:
				os.rmdir(os.path.join(root, dir))
		os.rmdir(repo_dir)
	if use_mercurial:
		if old_HGRCPATH is None:
			os.environ.pop('HGRCPATH')
		else:
			os.environ['HGRCPATH'] = old_HGRCPATH
	os.chdir(old_cwd)


if __name__ == '__main__':
	from tests import main
	main()

########NEW FILE########
__FILENAME__ = test_segments
# vim:fileencoding=utf-8:noet

from __future__ import unicode_literals

from powerline.segments import shell, common
import tests.vim as vim_module
import sys
import os
from tests.lib import Args, urllib_read, replace_attr, new_module, replace_module_module, replace_env, Pl
from tests import TestCase


vim = None


class TestShell(TestCase):
	def test_last_status(self):
		pl = Pl()
		segment_info = {'args': Args(last_exit_code=10)}
		self.assertEqual(shell.last_status(pl=pl, segment_info=segment_info),
				[{'contents': '10', 'highlight_group': 'exit_fail'}])
		segment_info['args'].last_exit_code = 0
		self.assertEqual(shell.last_status(pl=pl, segment_info=segment_info), None)
		segment_info['args'].last_exit_code = None
		self.assertEqual(shell.last_status(pl=pl, segment_info=segment_info), None)

	def test_last_pipe_status(self):
		pl = Pl()
		segment_info = {'args': Args(last_pipe_status=[])}
		self.assertEqual(shell.last_pipe_status(pl=pl, segment_info=segment_info), None)
		segment_info['args'].last_pipe_status = [0, 0, 0]
		self.assertEqual(shell.last_pipe_status(pl=pl, segment_info=segment_info), None)
		segment_info['args'].last_pipe_status = [0, 2, 0]
		self.assertEqual(shell.last_pipe_status(pl=pl, segment_info=segment_info), [
			{'contents': '0', 'highlight_group': 'exit_success', 'draw_inner_divider': True},
			{'contents': '2', 'highlight_group': 'exit_fail', 'draw_inner_divider': True},
			{'contents': '0', 'highlight_group': 'exit_success', 'draw_inner_divider': True}
		])

	def test_jobnum(self):
		pl = Pl()
		segment_info = {'args': Args(jobnum=0)}
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info), None)
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info, show_zero=False), None)
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info, show_zero=True), '0')
		segment_info = {'args': Args(jobnum=1)}
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info), '1')
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info, show_zero=False), '1')
		self.assertEqual(shell.jobnum(pl=pl, segment_info=segment_info, show_zero=True), '1')

	def test_continuation(self):
		pl = Pl()
		self.assertEqual(shell.continuation(pl=pl, segment_info={}), None)
		segment_info = {'parser_state': 'if cmdsubst'}
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info), [
			{
				'contents': 'if',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'l',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, right_align=True), [
			{
				'contents': 'if',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'r',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, omit_cmdsubst=False), [
			{
				'contents': 'if',
				'draw_inner_divider': True,
				'highlight_group': 'continuation',
			},
			{
				'contents': 'cmdsubst',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'l',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, omit_cmdsubst=False, right_align=True), [
			{
				'contents': 'if',
				'draw_inner_divider': True,
				'highlight_group': 'continuation',
				'width': 'auto',
				'align': 'r',
			},
			{
				'contents': 'cmdsubst',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, omit_cmdsubst=True, right_align=True), [
			{
				'contents': 'if',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'r',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, omit_cmdsubst=True, right_align=True, renames={'if': 'IF'}), [
			{
				'contents': 'IF',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'r',
			},
		])
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info, omit_cmdsubst=True, right_align=True, renames={'if': None}), [
			{
				'contents': '',
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'r',
			},
		])
		segment_info = {'parser_state': 'then then then cmdsubst'}
		self.assertEqual(shell.continuation(pl=pl, segment_info=segment_info), [
			{
				'contents': 'then',
				'draw_inner_divider': True,
				'highlight_group': 'continuation',
			},
			{
				'contents': 'then',
				'draw_inner_divider': True,
				'highlight_group': 'continuation',
			},
			{
				'contents': 'then',
				'draw_inner_divider': True,
				'highlight_group': 'continuation:current',
				'width': 'auto',
				'align': 'l',
			},
		])


class TestCommon(TestCase):
	def test_hostname(self):
		pl = Pl()
		with replace_env('SSH_CLIENT', '192.168.0.12 40921 22') as segment_info:
			with replace_module_module(common, 'socket', gethostname=lambda: 'abc'):
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info), 'abc')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, only_if_ssh=True), 'abc')
			with replace_module_module(common, 'socket', gethostname=lambda: 'abc.mydomain'):
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info), 'abc.mydomain')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, exclude_domain=True), 'abc')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, only_if_ssh=True), 'abc.mydomain')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, only_if_ssh=True, exclude_domain=True), 'abc')
			segment_info['environ'].pop('SSH_CLIENT')
			with replace_module_module(common, 'socket', gethostname=lambda: 'abc'):
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info), 'abc')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, only_if_ssh=True), None)
			with replace_module_module(common, 'socket', gethostname=lambda: 'abc.mydomain'):
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info), 'abc.mydomain')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, exclude_domain=True), 'abc')
				self.assertEqual(common.hostname(pl=pl, segment_info=segment_info, only_if_ssh=True, exclude_domain=True), None)

	def test_user(self):
		new_os = new_module('os', getpid=lambda: 1)

		class Process(object):
			def __init__(self, pid):
				pass

			def username(self):
				return 'def'

			if hasattr(common, 'psutil') and not callable(common.psutil.Process.username):
				username = property(username)

		new_psutil = new_module('psutil', Process=Process)
		pl = Pl()
		with replace_env('USER', 'def') as segment_info:
			common.username = False
			with replace_attr(common, 'os', new_os):
				with replace_attr(common, 'psutil', new_psutil):
					with replace_attr(common, '_geteuid', lambda: 5):
						self.assertEqual(common.user(pl=pl, segment_info=segment_info), [
							{'contents': 'def', 'highlight_group': 'user'}
						])
						self.assertEqual(common.user(pl=pl, segment_info=segment_info, hide_user='abc'), [
							{'contents': 'def', 'highlight_group': 'user'}
						])
						self.assertEqual(common.user(pl=pl, segment_info=segment_info, hide_user='def'), None)
					with replace_attr(common, '_geteuid', lambda: 0):
						self.assertEqual(common.user(pl=pl, segment_info=segment_info), [
							{'contents': 'def', 'highlight_group': ['superuser', 'user']}
						])

	def test_branch(self):
		pl = Pl()
		segment_info = {'getcwd': os.getcwd}
		with replace_attr(common, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda: None, directory='/tmp/tests')):
			with replace_attr(common, 'tree_status', lambda repo, pl: None):
				self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=False),
						[{'highlight_group': ['branch'], 'contents': 'tests'}])
				self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=True),
						[{'contents': 'tests', 'highlight_group': ['branch_clean', 'branch']}])
		with replace_attr(common, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda: 'D  ', directory='/tmp/tests')):
			with replace_attr(common, 'tree_status', lambda repo, pl: 'D '):
				self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=False),
						[{'highlight_group': ['branch'], 'contents': 'tests'}])
				self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=True),
						[{'contents': 'tests', 'highlight_group': ['branch_dirty', 'branch']}])
				self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=False),
						[{'highlight_group': ['branch'], 'contents': 'tests'}])
		with replace_attr(common, 'guess', lambda path: None):
			self.assertEqual(common.branch(pl=pl, segment_info=segment_info, status_colors=False), None)

	def test_cwd(self):
		new_os = new_module('os', path=os.path, sep='/')
		pl = Pl()
		cwd = [None]

		def getcwd():
			wd = cwd[0]
			if isinstance(wd, Exception):
				raise wd
			else:
				return wd

		segment_info = {'getcwd': getcwd, 'home': None}
		with replace_attr(common, 'os', new_os):
			cwd[0] = '/abc/def/ghi/foo/bar'
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info), [
				{'contents': '/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'abc', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'def', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'ghi', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'foo', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			segment_info['home'] = '/abc/def/ghi'
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info), [
				{'contents': '~', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'foo', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=3), [
				{'contents': '~', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'foo', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1), [
				{'contents': '⋯', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1, ellipsis='...'), [
				{'contents': '...', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1, ellipsis=None), [
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1, use_path_separator=True), [
				{'contents': '⋯/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1, use_path_separator=True, ellipsis='...'), [
				{'contents': '.../', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=1, use_path_separator=True, ellipsis=None), [
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=2, dir_shorten_len=2), [
				{'contents': '~', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'fo', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=2, dir_shorten_len=2, use_path_separator=True), [
				{'contents': '~/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False},
				{'contents': 'fo/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False},
				{'contents': 'bar', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']}
			])
			cwd[0] = '/etc'
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, use_path_separator=False), [
				{'contents': '/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True},
				{'contents': 'etc', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, use_path_separator=True), [
				{'contents': '/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False},
				{'contents': 'etc', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			cwd[0] = '/'
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, use_path_separator=False), [
				{'contents': '/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': True, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, use_path_separator=True), [
				{'contents': '/', 'divider_highlight_group': 'cwd:divider', 'draw_inner_divider': False, 'highlight_group': ['cwd:current_folder', 'cwd']},
			])
			ose = OSError()
			ose.errno = 2
			cwd[0] = ose
			self.assertEqual(common.cwd(pl=pl, segment_info=segment_info, dir_limit_depth=2, dir_shorten_len=2),
					[{'contents': '[not found]', 'divider_highlight_group': 'cwd:divider', 'highlight_group': ['cwd:current_folder', 'cwd'], 'draw_inner_divider': True}])
			cwd[0] = OSError()
			self.assertRaises(OSError, common.cwd, pl=pl, segment_info=segment_info, dir_limit_depth=2, dir_shorten_len=2)
			cwd[0] = ValueError()
			self.assertRaises(ValueError, common.cwd, pl=pl, segment_info=segment_info, dir_limit_depth=2, dir_shorten_len=2)

	def test_date(self):
		pl = Pl()
		with replace_attr(common, 'datetime', Args(now=lambda: Args(strftime=lambda fmt: fmt))):
			self.assertEqual(common.date(pl=pl), [{'contents': '%Y-%m-%d', 'highlight_group': ['date'], 'divider_highlight_group': None}])
			self.assertEqual(common.date(pl=pl, format='%H:%M', istime=True), [{'contents': '%H:%M', 'highlight_group': ['time', 'date'], 'divider_highlight_group': 'time:divider'}])

	def test_fuzzy_time(self):
		time = Args(hour=0, minute=45)
		pl = Pl()
		with replace_attr(common, 'datetime', Args(now=lambda: time)):
			self.assertEqual(common.fuzzy_time(pl=pl), 'quarter to one')
			time.hour = 23
			time.minute = 59
			self.assertEqual(common.fuzzy_time(pl=pl), 'round about midnight')
			time.minute = 33
			self.assertEqual(common.fuzzy_time(pl=pl), 'twenty‐five to twelve')
			time.minute = 60
			self.assertEqual(common.fuzzy_time(pl=pl), 'twelve o’clock')
			time.minute = 33
			self.assertEqual(common.fuzzy_time(pl=pl, unicode_text=False), 'twenty-five to twelve')
			time.minute = 60
			self.assertEqual(common.fuzzy_time(pl=pl, unicode_text=False), 'twelve o\'clock')

	def test_external_ip(self):
		pl = Pl()
		with replace_attr(common, 'urllib_read', urllib_read):
			self.assertEqual(common.external_ip(pl=pl), [{'contents': '127.0.0.1', 'divider_highlight_group': 'background:divider'}])

	def test_uptime(self):
		pl = Pl()
		with replace_attr(common, '_get_uptime', lambda: 259200):
			self.assertEqual(common.uptime(pl=pl), [{'contents': '3d', 'divider_highlight_group': 'background:divider'}])
		with replace_attr(common, '_get_uptime', lambda: 93784):
			self.assertEqual(common.uptime(pl=pl), [{'contents': '1d 2h 3m', 'divider_highlight_group': 'background:divider'}])
			self.assertEqual(common.uptime(pl=pl, shorten_len=4), [{'contents': '1d 2h 3m 4s', 'divider_highlight_group': 'background:divider'}])
		with replace_attr(common, '_get_uptime', lambda: 65536):
			self.assertEqual(common.uptime(pl=pl), [{'contents': '18h 12m 16s', 'divider_highlight_group': 'background:divider'}])
			self.assertEqual(common.uptime(pl=pl, shorten_len=2), [{'contents': '18h 12m', 'divider_highlight_group': 'background:divider'}])
			self.assertEqual(common.uptime(pl=pl, shorten_len=1), [{'contents': '18h', 'divider_highlight_group': 'background:divider'}])

		def _get_uptime():
			raise NotImplementedError

		with replace_attr(common, '_get_uptime', _get_uptime):
			self.assertEqual(common.uptime(pl=pl), None)

	def test_weather(self):
		pl = Pl()
		with replace_attr(common, 'urllib_read', urllib_read):
			self.assertEqual(common.weather(pl=pl), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9°C', 'gradient_level': 30.0}
			])
			self.assertEqual(common.weather(pl=pl, temp_coldest=0, temp_hottest=100), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9°C', 'gradient_level': 0}
			])
			self.assertEqual(common.weather(pl=pl, temp_coldest=-100, temp_hottest=-50), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9°C', 'gradient_level': 100}
			])
			self.assertEqual(common.weather(pl=pl, icons={'cloudy': 'o'}), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': 'o '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9°C', 'gradient_level': 30.0}
			])
			self.assertEqual(common.weather(pl=pl, icons={'partly_cloudy_day': 'x'}), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': 'x '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9°C', 'gradient_level': 30.0}
			])
			self.assertEqual(common.weather(pl=pl, unit='F'), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '16°F', 'gradient_level': 30.0}
			])
			self.assertEqual(common.weather(pl=pl, unit='K'), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '264K', 'gradient_level': 30.0}
			])
			self.assertEqual(common.weather(pl=pl, temp_format='{temp:.1e}C'), [
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_condition_partly_cloudy_day', 'weather_condition_cloudy', 'weather_conditions', 'weather'], 'contents': '☁ '},
				{'divider_highlight_group': 'background:divider', 'highlight_group': ['weather_temp_gradient', 'weather_temp', 'weather'], 'contents': '-9.0e+00C', 'gradient_level': 30.0}
			])

	def test_system_load(self):
		pl = Pl()
		with replace_module_module(common, 'os', getloadavg=lambda: (7.5, 3.5, 1.5)):
			with replace_attr(common, '_cpu_count', lambda: 2):
				self.assertEqual(common.system_load(pl=pl),
						[{'contents': '7.5 ', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 100},
						{'contents': '3.5 ', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 75.0},
						{'contents': '1.5', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 0}])
				self.assertEqual(common.system_load(pl=pl, format='{avg:.0f}', threshold_good=0, threshold_bad=1),
						[{'contents': '8 ', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 100},
						{'contents': '4 ', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 100},
						{'contents': '2', 'highlight_group': ['system_load_gradient', 'system_load'], 'divider_highlight_group': 'background:divider', 'gradient_level': 75.0}])

	def test_cpu_load_percent(self):
		pl = Pl()
		with replace_module_module(common, 'psutil', cpu_percent=lambda **kwargs: 52.3):
			self.assertEqual(common.cpu_load_percent(pl=pl), [{
				'contents': '52%',
				'gradient_level': 52.3,
				'highlight_group': ['cpu_load_percent_gradient', 'cpu_load_percent'],
			}])
			self.assertEqual(common.cpu_load_percent(pl=pl, format='{0:.1f}%'), [{
				'contents': '52.3%',
				'gradient_level': 52.3,
				'highlight_group': ['cpu_load_percent_gradient', 'cpu_load_percent'],
			}])

	def test_network_load(self):
		from time import sleep

		def gb(interface):
			return None

		f = [gb]

		def _get_bytes(interface):
			return f[0](interface)

		pl = Pl()

		with replace_attr(common, '_get_bytes', _get_bytes):
			common.network_load.startup(pl=pl)
			try:
				self.assertEqual(common.network_load(pl=pl, interface='eth0'), None)
				sleep(common.network_load.interval)
				self.assertEqual(common.network_load(pl=pl, interface='eth0'), None)
				while 'prev' not in common.network_load.interfaces.get('eth0', {}):
					sleep(0.1)
				self.assertEqual(common.network_load(pl=pl, interface='eth0'), None)

				l = [0, 0]

				def gb2(interface):
					l[0] += 1200
					l[1] += 2400
					return tuple(l)
				f[0] = gb2

				while not common.network_load.interfaces.get('eth0', {}).get('prev', (None, None))[1]:
					sleep(0.1)
				self.assertEqual(common.network_load(pl=pl, interface='eth0'), [
					{'divider_highlight_group': 'background:divider', 'contents': '⬇  1 KiB/s', 'highlight_group': ['network_load_recv', 'network_load']},
					{'divider_highlight_group': 'background:divider', 'contents': '⬆  2 KiB/s', 'highlight_group': ['network_load_sent', 'network_load']},
				])
				self.assertEqual(common.network_load(pl=pl, interface='eth0', recv_format='r {value}', sent_format='s {value}'), [
					{'divider_highlight_group': 'background:divider', 'contents': 'r 1 KiB/s', 'highlight_group': ['network_load_recv', 'network_load']},
					{'divider_highlight_group': 'background:divider', 'contents': 's 2 KiB/s', 'highlight_group': ['network_load_sent', 'network_load']},
				])
				self.assertEqual(common.network_load(pl=pl, recv_format='r {value}', sent_format='s {value}', suffix='bps', interface='eth0'), [
					{'divider_highlight_group': 'background:divider', 'contents': 'r 1 Kibps', 'highlight_group': ['network_load_recv', 'network_load']},
					{'divider_highlight_group': 'background:divider', 'contents': 's 2 Kibps', 'highlight_group': ['network_load_sent', 'network_load']},
				])
				self.assertEqual(common.network_load(pl=pl, recv_format='r {value}', sent_format='s {value}', si_prefix=True, interface='eth0'), [
					{'divider_highlight_group': 'background:divider', 'contents': 'r 1 kB/s', 'highlight_group': ['network_load_recv', 'network_load']},
					{'divider_highlight_group': 'background:divider', 'contents': 's 2 kB/s', 'highlight_group': ['network_load_sent', 'network_load']},
				])
				self.assertEqual(common.network_load(pl=pl, recv_format='r {value}', sent_format='s {value}', recv_max=0, interface='eth0'), [
					{'divider_highlight_group': 'background:divider', 'contents': 'r 1 KiB/s', 'highlight_group': ['network_load_recv_gradient', 'network_load_gradient', 'network_load_recv', 'network_load'], 'gradient_level': 100},
					{'divider_highlight_group': 'background:divider', 'contents': 's 2 KiB/s', 'highlight_group': ['network_load_sent', 'network_load']},
				])

				class ApproxEqual(object):
					def __eq__(self, i):
						return abs(i - 50.0) < 1

				self.assertEqual(common.network_load(pl=pl, recv_format='r {value}', sent_format='s {value}', sent_max=4800, interface='eth0'), [
					{'divider_highlight_group': 'background:divider', 'contents': 'r 1 KiB/s', 'highlight_group': ['network_load_recv', 'network_load']},
					{'divider_highlight_group': 'background:divider', 'contents': 's 2 KiB/s', 'highlight_group': ['network_load_sent_gradient', 'network_load_gradient', 'network_load_sent', 'network_load'], 'gradient_level': ApproxEqual()},
				])
			finally:
				common.network_load.shutdown()

	def test_virtualenv(self):
		pl = Pl()
		with replace_env('VIRTUAL_ENV', '/abc/def/ghi') as segment_info:
			self.assertEqual(common.virtualenv(pl=pl, segment_info=segment_info), 'ghi')
			segment_info['environ'].pop('VIRTUAL_ENV')
			self.assertEqual(common.virtualenv(pl=pl, segment_info=segment_info), None)

	def test_environment(self):
		pl = Pl()
		variable = 'FOO'
		value = 'bar'
		with replace_env(variable, value) as segment_info:
			self.assertEqual(common.environment(pl=pl, segment_info=segment_info, variable=variable), value)
			segment_info['environ'].pop(variable)
			self.assertEqual(common.environment(pl=pl, segment_info=segment_info, variable=variable), None)

	def test_email_imap_alert(self):
		# TODO
		pass

	def test_now_playing(self):
		# TODO
		pass

	def test_battery(self):
		pl = Pl()

		def _get_capacity(pl):
			return 86

		with replace_attr(common, '_get_capacity', _get_capacity):
			self.assertEqual(common.battery(pl=pl), [{
				'contents': '86%',
				'highlight_group': ['battery_gradient', 'battery'],
				'gradient_level': 86
			}])
			self.assertEqual(common.battery(pl=pl, format='{capacity:.2f}'), [{
				'contents': '0.86',
				'highlight_group': ['battery_gradient', 'battery'],
				'gradient_level': 86
			}])
			self.assertEqual(common.battery(pl=pl, steps=7), [{
				'contents': '86%',
				'highlight_group': ['battery_gradient', 'battery'],
				'gradient_level': 86
			}])
			self.assertEqual(common.battery(pl=pl, gamify=True), [
				{
					'contents': '♥♥♥♥',
					'draw_inner_divider': False,
					'highlight_group': ['battery_gradient', 'battery'],
					'gradient_level': 99
				},
				{
					'contents': '♥',
					'draw_inner_divider': False,
					'highlight_group': ['battery_gradient', 'battery'],
					'gradient_level': 1
				}
			])
			self.assertEqual(common.battery(pl=pl, gamify=True, full_heart='+', empty_heart='-', steps='10'), [
				{
					'contents': '++++++++',
					'draw_inner_divider': False,
					'highlight_group': ['battery_gradient', 'battery'],
					'gradient_level': 99
				},
				{
					'contents': '--',
					'draw_inner_divider': False,
					'highlight_group': ['battery_gradient', 'battery'],
					'gradient_level': 1
				}
			])


class TestVim(TestCase):
	def test_mode(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.mode(pl=pl, segment_info=segment_info), 'NORMAL')
		self.assertEqual(vim.mode(pl=pl, segment_info=segment_info, override={'i': 'INS'}), 'NORMAL')
		self.assertEqual(vim.mode(pl=pl, segment_info=segment_info, override={'n': 'NORM'}), 'NORM')
		with vim_module._with('mode', 'i') as segment_info:
			self.assertEqual(vim.mode(pl=pl, segment_info=segment_info), 'INSERT')
		with vim_module._with('mode', chr(ord('V') - 0x40)) as segment_info:
			self.assertEqual(vim.mode(pl=pl, segment_info=segment_info), 'V·BLCK')
			self.assertEqual(vim.mode(pl=pl, segment_info=segment_info, override={'^V': 'VBLK'}), 'VBLK')

	def test_visual_range(self):
		# TODO
		pass

	def test_modified_indicator(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.modified_indicator(pl=pl, segment_info=segment_info), None)
		segment_info['buffer'][0] = 'abc'
		try:
			self.assertEqual(vim.modified_indicator(pl=pl, segment_info=segment_info), '+')
			self.assertEqual(vim.modified_indicator(pl=pl, segment_info=segment_info, text='-'), '-')
		finally:
			vim_module._bw(segment_info['bufnr'])

	def test_paste_indicator(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.paste_indicator(pl=pl, segment_info=segment_info), None)
		with vim_module._with('options', paste=1):
			self.assertEqual(vim.paste_indicator(pl=pl, segment_info=segment_info), 'PASTE')
			self.assertEqual(vim.paste_indicator(pl=pl, segment_info=segment_info, text='P'), 'P')

	def test_readonly_indicator(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.readonly_indicator(pl=pl, segment_info=segment_info), None)
		with vim_module._with('bufoptions', readonly=1):
			self.assertEqual(vim.readonly_indicator(pl=pl, segment_info=segment_info), '')
			self.assertEqual(vim.readonly_indicator(pl=pl, segment_info=segment_info, text='L'), 'L')

	def test_file_directory(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.file_directory(pl=pl, segment_info=segment_info), None)
		with replace_env('HOME', '/home/foo', os.environ):
			with vim_module._with('buffer', '/tmp/’’/abc') as segment_info:
				self.assertEqual(vim.file_directory(pl=pl, segment_info=segment_info), '/tmp/’’/')
			with vim_module._with('buffer', b'/tmp/\xFF\xFF/abc') as segment_info:
				self.assertEqual(vim.file_directory(pl=pl, segment_info=segment_info), '/tmp/<ff><ff>/')
			with vim_module._with('buffer', '/tmp/abc') as segment_info:
				self.assertEqual(vim.file_directory(pl=pl, segment_info=segment_info), '/tmp/')
				os.environ['HOME'] = '/tmp'
				self.assertEqual(vim.file_directory(pl=pl, segment_info=segment_info), '~/')

	def test_file_name(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info), None)
		self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info, display_no_file=True),
				[{'contents': '[No file]', 'highlight_group': ['file_name_no_file', 'file_name']}])
		self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info, display_no_file=True, no_file_text='X'),
				[{'contents': 'X', 'highlight_group': ['file_name_no_file', 'file_name']}])
		with vim_module._with('buffer', '/tmp/abc') as segment_info:
			self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info), 'abc')
		with vim_module._with('buffer', '/tmp/’’') as segment_info:
			self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info), '’’')
		with vim_module._with('buffer', b'/tmp/\xFF\xFF') as segment_info:
			self.assertEqual(vim.file_name(pl=pl, segment_info=segment_info), '<ff><ff>')

	def test_file_size(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.file_size(pl=pl, segment_info=segment_info), '0 B')
		with vim_module._with('buffer', os.path.join(os.path.dirname(__file__), 'empty')) as segment_info:
			self.assertEqual(vim.file_size(pl=pl, segment_info=segment_info), '0 B')

	def test_file_opts(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.file_format(pl=pl, segment_info=segment_info),
				[{'divider_highlight_group': 'background:divider', 'contents': 'unix'}])
		self.assertEqual(vim.file_encoding(pl=pl, segment_info=segment_info),
				[{'divider_highlight_group': 'background:divider', 'contents': 'utf-8'}])
		self.assertEqual(vim.file_type(pl=pl, segment_info=segment_info), None)
		with vim_module._with('bufoptions', filetype='python'):
			self.assertEqual(vim.file_type(pl=pl, segment_info=segment_info),
					[{'divider_highlight_group': 'background:divider', 'contents': 'python'}])

	def test_line_percent(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		segment_info['buffer'][0:-1] = [str(i) for i in range(100)]
		try:
			self.assertEqual(vim.line_percent(pl=pl, segment_info=segment_info), '1')
			vim_module._set_cursor(50, 0)
			self.assertEqual(vim.line_percent(pl=pl, segment_info=segment_info), '50')
			self.assertEqual(vim.line_percent(pl=pl, segment_info=segment_info, gradient=True),
					[{'contents': '50', 'highlight_group': ['line_percent_gradient', 'line_percent'], 'gradient_level': 50 * 100.0 / 101}])
		finally:
			vim_module._bw(segment_info['bufnr'])

	def test_position(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		try:
			segment_info['buffer'][0:-1] = [str(i) for i in range(99)]
			vim_module._set_cursor(49, 0)
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info), '50%')
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info, gradient=True),
					[{'contents': '50%', 'highlight_group': ['position_gradient', 'position'], 'gradient_level': 50.0}])
			vim_module._set_cursor(0, 0)
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info), 'Top')
			vim_module._set_cursor(97, 0)
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info, position_strings={'top': 'Comienzo', 'bottom': 'Final', 'all': 'Todo'}), 'Final')
			segment_info['buffer'][0:-1] = [str(i) for i in range(2)]
			vim_module._set_cursor(0, 0)
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info, position_strings={'top': 'Comienzo', 'bottom': 'Final', 'all': 'Todo'}), 'Todo')
			self.assertEqual(vim.position(pl=pl, segment_info=segment_info, gradient=True),
					[{'contents': 'All', 'highlight_group': ['position_gradient', 'position'], 'gradient_level': 0.0}])
		finally:
			vim_module._bw(segment_info['bufnr'])

	def test_cursor_current(self):
		pl = Pl()
		segment_info = vim_module._get_segment_info()
		self.assertEqual(vim.line_current(pl=pl, segment_info=segment_info), '1')
		self.assertEqual(vim.col_current(pl=pl, segment_info=segment_info), '1')
		self.assertEqual(vim.virtcol_current(pl=pl, segment_info=segment_info), [{
			'highlight_group': ['virtcol_current_gradient', 'virtcol_current', 'col_current'], 'contents': '1', 'gradient_level': 100.0 / 80,
		}])
		self.assertEqual(vim.virtcol_current(pl=pl, segment_info=segment_info, gradient=False), [{
			'highlight_group': ['virtcol_current', 'col_current'], 'contents': '1',
		}])

	def test_modified_buffers(self):
		pl = Pl()
		self.assertEqual(vim.modified_buffers(pl=pl), None)

	def test_branch(self):
		pl = Pl()
		with vim_module._with('buffer', '/foo') as segment_info:
			with replace_attr(vim, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda: None, directory=path)):
				with replace_attr(vim, 'tree_status', lambda repo, pl: None):
					self.assertEqual(vim.branch(pl=pl, segment_info=segment_info, status_colors=False),
							[{'divider_highlight_group': 'branch:divider', 'highlight_group': ['branch'], 'contents': 'foo'}])
					self.assertEqual(vim.branch(pl=pl, segment_info=segment_info, status_colors=True),
							[{'divider_highlight_group': 'branch:divider', 'highlight_group': ['branch_clean', 'branch'], 'contents': 'foo'}])
			with replace_attr(vim, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda: 'DU', directory=path)):
				with replace_attr(vim, 'tree_status', lambda repo, pl: 'DU'):
					self.assertEqual(vim.branch(pl=pl, segment_info=segment_info, status_colors=False),
							[{'divider_highlight_group': 'branch:divider', 'highlight_group': ['branch'], 'contents': 'foo'}])
					self.assertEqual(vim.branch(pl=pl, segment_info=segment_info, status_colors=True),
							[{'divider_highlight_group': 'branch:divider', 'highlight_group': ['branch_dirty', 'branch'], 'contents': 'foo'}])

	def test_file_vcs_status(self):
		pl = Pl()
		with vim_module._with('buffer', '/foo') as segment_info:
			with replace_attr(vim, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda file: 'M', directory=path)):
				self.assertEqual(vim.file_vcs_status(pl=pl, segment_info=segment_info),
						[{'highlight_group': ['file_vcs_status_M', 'file_vcs_status'], 'contents': 'M'}])
			with replace_attr(vim, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda file: None, directory=path)):
				self.assertEqual(vim.file_vcs_status(pl=pl, segment_info=segment_info), None)
		with vim_module._with('buffer', '/bar') as segment_info:
			with vim_module._with('bufoptions', buftype='nofile'):
				with replace_attr(vim, 'guess', lambda path: Args(branch=lambda: os.path.basename(path), status=lambda file: 'M', directory=path)):
					self.assertEqual(vim.file_vcs_status(pl=pl, segment_info=segment_info), None)

old_cwd = None


def setUpModule():
	global old_cwd
	global __file__
	sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'path')))
	old_cwd = os.getcwd()
	__file__ = os.path.abspath(__file__)
	os.chdir(os.path.dirname(__file__))
	from powerline.segments import vim
	globals()['vim'] = vim


def tearDownModule():
	global old_cwd
	os.chdir(old_cwd)
	sys.path.pop(0)


if __name__ == '__main__':
	from tests import main
	main()

########NEW FILE########
__FILENAME__ = postproc
#!/usr/bin/env python

from __future__ import unicode_literals

import os
import socket
import sys
import codecs


shell = sys.argv[1]
fname = os.path.join('tests', 'shell', shell + '.full.log')
new_fname = os.path.join('tests', 'shell', shell + '.log')
pid_fname = os.path.join('tests', 'shell', '3rd', 'pid')


with open(pid_fname, 'r') as P:
	pid = P.read().strip()
hostname = socket.gethostname()
user = os.environ['USER']

with codecs.open(fname, 'r', encoding='utf-8') as R:
	with codecs.open(new_fname, 'w', encoding='utf-8') as W:
		found_cd = False
		for line in (R if shell != 'fish' else R.read().split('\n')):
			if not found_cd:
				found_cd = ('cd tests/shell/3rd' in line)
				continue
			if 'true is the last line' in line:
				break
			line = line.translate({
				ord('\r'): None
			})
			line = line.replace(hostname, 'HOSTNAME')
			line = line.replace(user, 'USER')
			line = line.replace(pid, 'PID')
			if shell == 'fish':
				try:
					start = line.index('\033[0;')
					end = line.index('\033[0m', start)
					line = line[start:end + 4] + '\n'
				except ValueError:
					line = ''
			elif shell == 'tcsh':
				try:
					start = line.index('\033[0;')
					end = line.index(' ', start)
					line = line[start:end] + '\033[0m\n'
				except ValueError:
					line = ''
			W.write(line)

########NEW FILE########
__FILENAME__ = vim
# vim:fileencoding=utf-8:noet
_log = []
vars = {}
vvars = {'version': 703}
_window = 0
_mode = 'n'
_buf_purge_events = set()
options = {
	'paste': 0,
	'ambiwidth': 'single',
}
_last_bufnr = 0
_highlights = {}


_thread_id = None


def _set_thread_id():
	global _thread_id
	from threading import current_thread
	_thread_id = current_thread().ident


# Assuming import is done from the main thread
_set_thread_id()


def _vim(func):
	from functools import wraps
	from threading import current_thread

	@wraps(func)
	def f(*args, **kwargs):
		global _thread_id
		if _thread_id != current_thread().ident:
			raise RuntimeError('Accessing vim from separate threads is not allowed')
		_log.append((func.__name__, args))
		return func(*args, **kwargs)

	return f


class _Buffers(object):
	@_vim
	def __init__(self):
		self.d = {}

	@_vim
	def __getitem__(self, item):
		return self.d[item]

	@_vim
	def __setitem__(self, item, value):
		self.d[item] = value

	@_vim
	def __contains__(self, item):
		return item in self.d

	@_vim
	def __nonzero__(self):
		return bool(self.d)

	@_vim
	def keys(self):
		return self.d.keys()

	@_vim
	def pop(self, *args, **kwargs):
		return self.d.pop(*args, **kwargs)


buffers = _Buffers()


class _Windows(object):
	@_vim
	def __init__(self):
		self.l = []

	@_vim
	def __getitem__(self, item):
		return self.l[item]

	@_vim
	def __setitem__(self, item, value):
		self.l[item] = value

	@_vim
	def __len__(self):
		return len(self.l)

	@_vim
	def __iter__(self):
		return iter(self.l)

	@_vim
	def __nonzero__(self):
		return not not self.l

	@_vim
	def pop(self, *args, **kwargs):
		return self.l.pop(*args, **kwargs)

	@_vim
	def append(self, *args, **kwargs):
		return self.l.append(*args, **kwargs)

	@_vim
	def index(self, *args, **kwargs):
		return self.l.index(*args, **kwargs)


windows = _Windows()


@_vim
def _buffer():
	return windows[_window - 1].buffer.number


def _construct_result(r):
	import sys
	if sys.version_info < (3,):
		return r
	else:
		if type(r) is str:
			return r.encode('utf-8')
		elif type(r) is dict or type(r) is list:
			raise NotImplementedError
		return r


def _str_func(func):
	from functools import wraps

	@wraps(func)
	def f(*args, **kwargs):
		return _construct_result(func(*args, **kwargs))
	return f


def _log_print():
	import sys
	for entry in _log:
		sys.stdout.write(repr(entry) + '\n')


@_vim
def command(cmd):
	if cmd.startswith('let g:'):
		import re
		varname, value = re.compile(r'^let g:(\w+)\s*=\s*(.*)').match(cmd).groups()
		vars[varname] = value
	elif cmd.startswith('hi '):
		sp = cmd.split()
		_highlights[sp[1]] = sp[2:]
	elif cmd.startswith('function! Powerline_plugin_ctrlp'):
		# Ignore CtrlP updating functions
		pass
	else:
		raise NotImplementedError


@_vim
def eval(expr):
	if expr.startswith('g:'):
		return vars[expr[2:]]
	elif expr.startswith('&'):
		return options[expr[1:]]
	elif expr.startswith('PowerlineRegisterCachePurgerEvent'):
		_buf_purge_events.add(expr[expr.find('"') + 1:expr.rfind('"') - 1])
		return '0'
	elif expr.startswith('exists('):
		return '0'
	elif expr == 'getbufvar("%", "NERDTreeRoot").path.str()':
		import os
		assert os.path.basename(buffers[_buffer()].name).startswith('NERD_tree_')
		return '/usr/include'
	raise NotImplementedError


@_vim
def bindeval(expr):
	if expr == 'g:':
		return vars
	elif expr == '{}':
		return {}
	elif expr == '[]':
		return []
	import re
	match = re.compile(r'^function\("([^"\\]+)"\)$').match(expr)
	if match:
		return globals()['_emul_' + match.group(1)]
	else:
		raise NotImplementedError


@_vim
@_str_func
def _emul_mode(*args):
	if args and args[0]:
		return _mode
	else:
		return _mode[0]


@_vim
@_str_func
def _emul_getbufvar(bufnr, varname):
	import re
	if varname[0] == '&':
		if bufnr == '%':
			bufnr = buffers[_buffer()].number
		if bufnr not in buffers:
			return ''
		try:
			return buffers[bufnr].options[varname[1:]]
		except KeyError:
			try:
				return options[varname[1:]]
			except KeyError:
				return ''
	elif re.match('^[a-zA-Z_]+$', varname):
		if bufnr == '%':
			bufnr = buffers[_buffer()].number
		if bufnr not in buffers:
			return ''
		return buffers[bufnr].vars[varname]
	raise NotImplementedError


@_vim
@_str_func
def _emul_getwinvar(winnr, varname):
	return windows[winnr].vars[varname]


@_vim
def _emul_setwinvar(winnr, varname, value):
	windows[winnr].vars[varname] = value


@_vim
def _emul_virtcol(expr):
	if expr == '.' or isinstance(expr, list):
		return windows[_window - 1].cursor[1] + 1
	raise NotImplementedError


@_vim
def _emul_getpos(expr):
	if expr == '.' or expr == 'v':
		return [0, windows[_window - 1].cursor[0] + 1, windows[_window - 1].cursor[1] + 1, 0]
	raise NotImplementedError


@_vim
@_str_func
def _emul_fnamemodify(path, modstring):
	import os
	_modifiers = {
		'~': lambda path: path.replace(os.environ['HOME'].encode('utf-8'), b'~') if path.startswith(os.environ['HOME'].encode('utf-8')) else path,
		'.': lambda path: (lambda tpath: path if tpath[:3] == b'..' + os.sep.encode() else tpath)(os.path.relpath(path)),
		't': lambda path: os.path.basename(path),
		'h': lambda path: os.path.dirname(path),
	}

	for mods in modstring.split(':')[1:]:
		path = _modifiers[mods](path)
	return path


@_vim
@_str_func
def _emul_expand(expr):
	if expr == '<abuf>':
		return _buffer()
	raise NotImplementedError


@_vim
def _emul_bufnr(expr):
	if expr == '$':
		return _last_bufnr
	raise NotImplementedError


@_vim
def _emul_exists(varname):
	if varname.startswith('g:'):
		return varname[2:] in vars
	raise NotImplementedError


@_vim
def _emul_line2byte(line):
	buflines = _buf_lines[_buffer()]
	if line == len(buflines) + 1:
		return sum((len(s) for s in buflines)) + 1
	raise NotImplementedError


@_vim
def _emul_line(expr):
	cursorline = windows[_window - 1].cursor[0] + 1
	numlines = len(_buf_lines[_buffer()])
	if expr == 'w0':
		return max(cursorline - 5, 1)
	if expr == 'w$':
		return min(cursorline + 5, numlines)
	raise NotImplementedError


@_vim
@_str_func
def _emul_strtrans(s):
	# FIXME Do more replaces
	return s.replace(b'\xFF', b'<ff>')


@_vim
@_str_func
def _emul_bufname(bufnr):
	try:
		return buffers[bufnr]._name or b''
	except KeyError:
		return b''


_window_ids = [None]
_window_id = 0


class _Window(object):
	def __init__(self, buffer=None, cursor=(1, 0), width=80):
		global _window_id
		self.cursor = cursor
		self.width = width
		self.number = len(windows) + 1
		if buffer:
			if type(buffer) is _Buffer:
				self.buffer = buffer
			else:
				self.buffer = _Buffer(**buffer)
		else:
			self.buffer = _Buffer()
		windows.append(self)
		_window_id += 1
		_window_ids.append(_window_id)
		self.options = {}
		self.vars = {}

	def __repr__(self):
		return '<window ' + str(windows.index(self)) + '>'


_buf_lines = {}
_undostate = {}
_undo_written = {}


class _Buffer(object):
	def __init__(self, name=None):
		global _last_bufnr
		_last_bufnr += 1
		bufnr = _last_bufnr
		self.number = bufnr
		# FIXME Use unicode() for python-3
		self.name = name
		self.vars = {}
		self.options = {
			'modified': 0,
			'readonly': 0,
			'fileformat': 'unix',
			'filetype': '',
			'buftype': '',
			'fileencoding': 'utf-8',
			'textwidth': 80,
		}
		_buf_lines[bufnr] = ['']
		from copy import copy
		_undostate[bufnr] = [copy(_buf_lines[bufnr])]
		_undo_written[bufnr] = len(_undostate[bufnr])
		buffers[bufnr] = self

	@property
	def name(self):
		import sys
		if sys.version_info < (3,):
			return self._name
		else:
			return str(self._name, 'utf-8') if self._name else None

	@name.setter
	def name(self, name):
		if name is None:
			self._name = None
		else:
			import os
			if type(name) is not bytes:
				name = name.encode('utf-8')
			self._name = os.path.abspath(name)

	def __getitem__(self, line):
		return _buf_lines[self.number][line]

	def __setitem__(self, line, value):
		self.options['modified'] = 1
		_buf_lines[self.number][line] = value
		from copy import copy
		_undostate[self.number].append(copy(_buf_lines[self.number]))

	def __setslice__(self, *args):
		self.options['modified'] = 1
		_buf_lines[self.number].__setslice__(*args)
		from copy import copy
		_undostate[self.number].append(copy(_buf_lines[self.number]))

	def __getslice__(self, *args):
		return _buf_lines[self.number].__getslice__(*args)

	def __len__(self):
		return len(_buf_lines[self.number])

	def __repr__(self):
		return '<buffer ' + str(self.name) + '>'

	def __del__(self):
		bufnr = self.number
		if _buf_lines:
			_buf_lines.pop(bufnr)
		if _undostate:
			_undostate.pop(bufnr)
		if _undo_written:
			_undo_written.pop(bufnr)


class _Current(object):
	@property
	def buffer(self):
		return buffers[_buffer()]

	@property
	def window(self):
		return windows[_window - 1]


current = _Current()


_dict = None


@_vim
def _init():
	global _dict

	if _dict:
		return _dict

	_dict = {}
	for varname, value in globals().items():
		if varname[0] != '_':
			_dict[varname] = value
	_new()
	return _dict


@_vim
def _get_segment_info():
	mode_translations = {
		chr(ord('V') - 0x40): '^V',
		chr(ord('S') - 0x40): '^S',
	}
	mode = _mode
	mode = mode_translations.get(mode, mode)
	return {
		'window': windows[_window - 1],
		'buffer': buffers[_buffer()],
		'bufnr': _buffer(),
		'window_id': _window_ids[_window],
		'mode': mode,
	}


@_vim
def _launch_event(event):
	pass


@_vim
def _start_mode(mode):
	global _mode
	if mode == 'i':
		_launch_event('InsertEnter')
	elif _mode == 'i':
		_launch_event('InsertLeave')
	_mode = mode


@_vim
def _undo():
	if len(_undostate[_buffer()]) == 1:
		return
	_undostate[_buffer()].pop(-1)
	_buf_lines[_buffer()] = _undostate[_buffer()][-1]
	buf = current.buffer
	if _undo_written[_buffer()] == len(_undostate[_buffer()]):
		buf.options['modified'] = 0


@_vim
def _edit(name=None):
	global _last_bufnr
	if _buffer() and buffers[_buffer()].name is None:
		buf = buffers[_buffer()]
		buf.name = name
	else:
		buf = _Buffer(name)
		windows[_window - 1].buffer = buf


@_vim
def _new(name=None):
	global _window
	_Window(buffer={'name': name})
	_window = len(windows)


@_vim
def _split():
	global _window
	_Window(buffer=buffers[_buffer()])
	_window = len(windows)


@_vim
def _del_window(winnr):
	win = windows.pop(winnr - 1)
	_window_ids.pop(winnr)
	return win


@_vim
def _close(winnr, wipe=True):
	global _window
	win = _del_window(winnr)
	if _window == winnr:
		_window = len(windows)
	if wipe:
		for w in windows:
			if w.buffer.number == win.buffer.number:
				break
		else:
			_bw(win.buffer.number)
	if not windows:
		_Window()


@_vim
def _bw(bufnr=None):
	bufnr = bufnr or _buffer()
	winnr = 1
	for win in windows:
		if win.buffer.number == bufnr:
			_close(winnr, wipe=False)
		winnr += 1
	buffers.pop(bufnr)
	if not buffers:
		_Buffer()
	_b(max(buffers.keys()))


@_vim
def _b(bufnr):
	windows[_window - 1].buffer = buffers[bufnr]


@_vim
def _set_cursor(line, col):
	windows[_window - 1].cursor = (line, col)
	if _mode == 'n':
		_launch_event('CursorMoved')
	elif _mode == 'i':
		_launch_event('CursorMovedI')


@_vim
def _get_buffer():
	return buffers[_buffer()]


@_vim
def _set_bufoption(option, value, bufnr=None):
	buffers[bufnr or _buffer()].options[option] = value
	if option == 'filetype':
		_launch_event('FileType')


class _WithNewBuffer(object):
	def __init__(self, func, *args, **kwargs):
		self.call = lambda: func(*args, **kwargs)

	def __enter__(self):
		self.call()
		self.bufnr = _buffer()
		return _get_segment_info()

	def __exit__(self, *args):
		_bw(self.bufnr)


@_vim
def _set_dict(d, new, setfunc=None):
	if not setfunc:
		def setfunc(k, v):
			d[k] = v

	old = {}
	na = []
	for k, v in new.items():
		try:
			old[k] = d[k]
		except KeyError:
			na.append(k)
		setfunc(k, v)
	return old, na


class _WithBufOption(object):
	def __init__(self, **new):
		self.new = new

	def __enter__(self):
		self.buffer = buffers[_buffer()]
		self.old = _set_dict(self.buffer.options, self.new, _set_bufoption)[0]

	def __exit__(self, *args):
		self.buffer.options.update(self.old)


class _WithMode(object):
	def __init__(self, new):
		self.new = new

	def __enter__(self):
		self.old = _mode
		_start_mode(self.new)
		return _get_segment_info()

	def __exit__(self, *args):
		_start_mode(self.old)


class _WithDict(object):
	def __init__(self, d, **new):
		self.new = new
		self.d = d

	def __enter__(self):
		self.old, self.na = _set_dict(self.d, self.new)

	def __exit__(self, *args):
		self.d.update(self.old)
		for k in self.na:
			self.d.pop(k)


class _WithSplit(object):
	def __enter__(self):
		_split()

	def __exit__(self, *args):
		_close(2, wipe=False)


class _WithBufName(object):
	def __init__(self, new):
		self.new = new

	def __enter__(self):
		import os
		buffer = buffers[_buffer()]
		self.buffer = buffer
		self.old = buffer.name
		buffer.name = self.new
		if buffer.name and os.path.basename(buffer.name) == 'ControlP':
			buffer.vars['powerline_ctrlp_type'] = 'main'
			buffer.vars['powerline_ctrlp_args'] = ['focus', 'byfname', '0', 'prev', 'item', 'next', 'marked']

	def __exit__(self, *args):
		self.buffer.name = self.old


@_vim
def _with(key, *args, **kwargs):
	if key == 'buffer':
		return _WithNewBuffer(_edit, *args, **kwargs)
	elif key == 'bufname':
		return _WithBufName(*args, **kwargs)
	elif key == 'mode':
		return _WithMode(*args, **kwargs)
	elif key == 'bufoptions':
		return _WithBufOption(**kwargs)
	elif key == 'options':
		return _WithDict(options, **kwargs)
	elif key == 'globals':
		return _WithDict(vars, **kwargs)
	elif key == 'split':
		return _WithSplit()


class error(Exception):
	pass

########NEW FILE########
__FILENAME__ = colors_find
#!/usr/bin/env python
import sys
import os


def get_color(name, rgb):
	return name, (int(rgb[:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16))


with open(os.path.join(os.path.dirname(__file__), 'colors.map'), 'r') as f:
	colors = [get_color(*line.split('\t')) for line in f]


urgb = get_color(None, sys.argv[1])[1]


def col_distance(rgb1, rgb2):
	return sum(((rgb1[i] - rgb2[i]) ** 2 for i in range(3)))


def find_color(urgb, colors):
	cur_distance = 3 * (255 ** 2 + 1)
	cur_color = None
	for color, crgb in colors:
		dist = col_distance(urgb, crgb)
		if dist < cur_distance:
			cur_distance = dist
			cur_color = (color, crgb)
	return cur_color


cur_color = find_color(urgb, colors)

print urgb, ':', cur_color

col_1 = ';2;' + ';'.join((str(i) for i in urgb)) + 'm'
col_2 = ';2;' + ';'.join((str(i) for i in cur_color[1])) + 'm'
sys.stdout.write('\033[48' + col_1 + '\033[38' + col_2 + 'abc\033[0m <-- bg:urgb, fg:crgb\n')
sys.stdout.write('\033[48' + col_2 + '\033[38' + col_1 + 'abc\033[0m <-- bg:crgb, fg:urgb\n')

########NEW FILE########
__FILENAME__ = generate_gradients
#!/usr/bin/env python
# vim:fileencoding=utf-8:noet
'''Gradients generator
'''
from __future__ import division
import sys
import json
from powerline.colorscheme import cterm_to_hex
from itertools import groupby
import argparse

try:
	from __builtin__ import unicode
except ImportError:
	unicode = str  # NOQA


def num2(s):
	try:
		return (True, [int(v) for v in s.partition(' ')[::2]])
	except TypeError:
		return (False, [float(v) for v in s.partition(' ')[::2]])


def rgbint_to_rgb(rgbint):
	return ((rgbint >> 16) & 0xFF, (rgbint >> 8) & 0xFF, rgbint & 0xFF)


def color(s):
	if len(s) <= 3:
		return rgbint_to_rgb(cterm_to_hex[int(s)])
	else:
		return rgbint_to_rgb(int(s, 16))


def nums(s):
	return [int(i) for i in s.split()]


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('gradient', nargs='*', metavar='COLOR', type=color, help='List of colors (either indexes from 8-bit palette or 24-bit RGB in hexadecimal notation)')
p.add_argument('-n', '--num_items', metavar='INT', type=int, help='Number of items in resulting list', default=101)
p.add_argument('-N', '--num_output', metavar='INT', type=int, help='Number of characters in sample', default=101)
p.add_argument('-r', '--range', metavar='V1 V2', type=num2, help='Use this range when outputting scale')
p.add_argument('-s', '--show', action='store_true', help='If present output gradient sample')
p.add_argument('-p', '--palette', choices=('16', '256'), help='Use this palette. Defaults to 240-color palette (256 colors without first 16)')
p.add_argument('-w', '--weights', metavar='INT INT ...', type=nums, help='Adjust weights of colors. Number of weights must be equal to number of colors')

args = p.parse_args()


def linear_gradient(start_value, stop_value, start_offset, stop_offset, offset):
	return start_value + ((offset - start_offset) * (stop_value - start_value) / (stop_offset - start_offset))


def gradient(DATA):
	def gradient_function(y):
		initial_offset = 0
		for offset, start, end in DATA:
			if y <= offset:
				return [linear_gradient(start[i], end[i], initial_offset, offset, y) for i in range(3)]
			initial_offset = offset
	return gradient_function


def get_rgb(*args):
	return "%02x%02x%02x" % args


def col_distance(rgb1, rgb2):
	return sum(((rgb1[i] - rgb2[i]) ** 2 for i in range(3)))


def find_color(urgb, colors, ctrans):
	cur_distance = 3 * (255 ** 2 + 1)
	cur_color = None
	i = 0
	for crgbint in colors:
		crgb = rgbint_to_rgb(crgbint)
		dist = col_distance(urgb, crgb)
		if dist < cur_distance:
			cur_distance = dist
			cur_color = (ctrans(i), crgb)
		i += 1
	return cur_color


def print_color(color):
	if type(color) is int:
		colstr = '5;' + str(color)
	else:
		colstr = '2;' + ';'.join((str(int(round(i))) for i in color))
	sys.stdout.write('\033[48;' + colstr + 'm ')


def print_colors(colors, num):
	for i in range(num):
		color = colors[int(round(i * (len(colors) - 1) / num))]
		print_color(color)
	sys.stdout.write('\033[0m\n')


def dec_scale_generator(num):
	j = 0
	r = ''
	while num:
		r += '\033[{0}m'.format(j % 2)
		for i in range(10):
			r += str(i)
			num -= 1
			if not num:
				break
		j += 1
	r += '\033[0m\n'
	return r


m = args.num_items

maxweight = len(args.gradient) - 1
if args.weights:
	weight_sum = sum(args.weights)
	norm_weights = [100.0 * weight / weight_sum for weight in args.weights]
	steps = [0]
	for weight in norm_weights:
		steps.append(steps[-1] + weight)
	steps.pop(0)
	steps.pop(0)
else:
	step = m / maxweight
	steps = [i * step for i in range(1, maxweight + 1)]

data = [(weight, args.gradient[i - 1], args.gradient[i]) for weight, i in zip(steps, range(1, len(args.gradient)))]
gr_func = gradient(data)
gradient = [gr_func(y) for y in range(0, m)]
palettes = {
	'16': (cterm_to_hex[:16], lambda c: c),
	'256': (cterm_to_hex, lambda c: c),
	None: (cterm_to_hex[16:], lambda c: c + 16),
}
r = [get_rgb(*col) for col in gradient]
r2 = [find_color(col, *palettes[args.palette])[0] for col in gradient]
r3 = [i[0] for i in groupby(r2)]
print(json.dumps(r))
print(json.dumps(r2))
print(json.dumps(r3))
if args.show:
	print_colors(args.gradient, args.num_output)
	print_colors(gradient, args.num_output)
	print_colors(r2, args.num_output)
	print_colors(r3, args.num_output)
	if not args.range and args.num_output >= 32 and (args.num_output - 1) // 10 >= 4 and (args.num_output - 1) % 10 == 0:
		sys.stdout.write('0')
		sys.stdout.write(''.join(('%*u' % (args.num_output // 10, i) for i in range(10, 101, 10))))
		sys.stdout.write('\n')
	else:
		if args.range:
			vmin, vmax = args.range[1]
			isint = args.range[0]
		else:
			isint = True
			vmin = 0
			vmax = 100
		s = ''
		lasts = ' ' + str(vmax)
		while len(s) + len(lasts) < args.num_output:
			curpc = len(s) + 1 if s else 0
			curval = vmin + curpc * (vmax - vmin) / args.num_output
			if isint:
				curval = int(round(curval))
			s += str(curval) + ' '
		sys.stdout.write(s[:-1] + lasts + '\n')
	sys.stdout.write(dec_scale_generator(args.num_output) + '\n')

########NEW FILE########
