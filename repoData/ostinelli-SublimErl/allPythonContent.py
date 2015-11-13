__FILENAME__ = sublimerl_autocompiler
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================

# imports
import sublime, sublime_plugin
import os, threading
from sublimerl_core import SUBLIMERL, SublimErlProjectLoader


# test runner
class SublimErlAutocompiler(SublimErlProjectLoader):

	def __init__(self, view):
		# init super
		SublimErlProjectLoader.__init__(self, view)
		# init
		self.panel_name = 'sublimerl_autocompiler'
		self.panel_buffer = ''
		# setup panel
		self.setup_panel()

	def setup_panel(self):
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmLanguage"))
		self.panel.settings().set("color_scheme", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def hide_panel(self):
		self.window.run_command("hide_panel")

	def log(self, text):
		self.panel_buffer += text.encode('utf-8')
		sublime.set_timeout(self.update_panel, 0)

	def compile(self):
		retcode, data = self.compile_source(skip_deps=True)
		if retcode != 0:
			self.log(data)
		else:
			sublime.set_timeout(self.hide_panel, 0)

# listener
class SublimErlAutocompilerListener(sublime_plugin.EventListener):

	# CALLBACK ON VIEW SAVE
	def on_post_save(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# ensure context matches
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		autocompiler = SublimErlAutocompiler(view)
		# compile saved file & reload completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# compile
				autocompiler.compile()
		SublimErlThread().start()

########NEW FILE########
__FILENAME__ = sublimerl_completion
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================

# imports
import sublime, sublime_plugin
import os, threading, pickle, json, re
from sublimerl_core import SUBLIMERL, SublimErlProjectLoader

SUBLIMERL_COMPLETIONS = {
	'erlang_libs': {
		'completions': {},
		'load_in_progress': False,
		'rebuilt': False
	},
	'current_project': {
		'completions': {},
		'load_in_progress': False,
		'rebuild_in_progress': False
	}
}

# erlang module name completions
class SublimErlModuleNameCompletions():

	def set_completions(self):
		# if errors occurred
		if SUBLIMERL.plugin_path == None: return
		# load json
		completions_full_path = os.path.join(SUBLIMERL.plugin_path, 'completion', 'Erlang-Libs.sublime-completions.full')
		if os.path.exists(completions_full_path):
			f = open(completions_full_path)
			file_json = json.load(f)
			f.close()
			# filter

			completions = []
			for m in file_json['completions']:
				valid = True
				for regex in SUBLIMERL.completion_skip_erlang_libs:
					if re.search(regex, m['trigger']):
						valid = False
						break
				if valid == True: completions.append(m)
			# generate completion file
			file_json['completions'] = completions
			f = open(os.path.join(SUBLIMERL.plugin_path, 'completion', 'Erlang-Libs.sublime-completions'), 'w')
			f.write(json.dumps(file_json))
			f.close()

	def set_completions_threaded(self):
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.set_completions()
		SublimErlThread().start()

SublimErlModuleNameCompletions().set_completions_threaded()


# completions
class SublimErlCompletions(SublimErlProjectLoader):

	def get_available_completions(self):
		# load current erlang libs
		if SUBLIMERL_COMPLETIONS['erlang_libs']['completions'] == {}: self.load_erlang_lib_completions()
		# start rebuilding: only done once per sublimerl session
		# [i.e. needs sublime text restart to regenerate erlang completions]
		self.generate_erlang_lib_completions()
		# generate & load project files
		self.generate_project_completions()

	def get_completion_filename(self, code_type):
		if code_type == 'erlang_libs': return 'Erlang-Libs'
		elif code_type == 'current_project': return 'Current-Project'

	def load_erlang_lib_completions(self):
		self.load_completions('erlang_libs')

	def load_current_project_completions(self):
		self.load_completions('current_project')

	def load_completions(self, code_type):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] = True
		# load
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				global SUBLIMERL_COMPLETIONS
				# load completetions from file
				disasm_filepath = os.path.join(SUBLIMERL.plugin_path, "completion", "%s.disasm" % this.get_completion_filename(code_type))
				if os.path.exists(disasm_filepath):
					# load file
					f = open(disasm_filepath, 'r')
					completions = pickle.load(f)
					f.close()
					# set
					SUBLIMERL_COMPLETIONS[code_type]['completions'] = completions

				# release lock
				SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] = False

		SublimErlThread().start()

	def generate_erlang_lib_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['erlang_libs']['rebuilt'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS['erlang_libs']['rebuilt'] = True

		# rebuild
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				# get dirs
				dest_file_base = os.path.join(SUBLIMERL.completions_path, "Erlang-Libs")
				# get erlang libs info
				current_erlang_libs = [name for name in os.listdir(SUBLIMERL.erlang_libs_path) if os.path.isdir(os.path.join(SUBLIMERL.erlang_libs_path, name))]
				# read file of previous erlang libs
				dirinfo_path = os.path.join(SUBLIMERL.completions_path, "Erlang-Libs.dirinfo")
				if os.path.exists(dirinfo_path):
					f = open(dirinfo_path, 'rb')
					erlang_libs = pickle.load(f)
					f.close()
					if current_erlang_libs == erlang_libs:
						# same erlang libs, do not regenerate
						return
				# different erlang libs -> regenerate
				this.status("Regenerating Erlang lib completions...")
				# set cwd
				os.chdir(SUBLIMERL.support_path)
				# start gen
				this.execute_os_command("python sublimerl_libparser.py %s %s" % (this.shellquote(SUBLIMERL.erlang_libs_path), this.shellquote(dest_file_base)))
				# rename file to .full
				os.rename("%s.sublime-completions" % dest_file_base, "%s.sublime-completions.full" % dest_file_base)
				# save dir information
				f = open(dirinfo_path, 'wb')
				pickle.dump(current_erlang_libs, f)
				f.close()
				# regenerate completions based on options
				SublimErlModuleNameCompletions().set_completions()
				# trigger event to reload completions
				this.load_erlang_lib_completions()
				this.status("Finished regenerating Erlang lib completions.")

		SublimErlThread().start()

	def generate_project_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] = True

		# rebuild
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				global SUBLIMERL_COMPLETIONS
				this.status("Regenerating Project completions...")
				# get dir
				dest_file_base = os.path.join(SUBLIMERL.completions_path, "Current-Project")
				# set cwd
				os.chdir(SUBLIMERL.support_path)
				# start gen
				this.execute_os_command("python sublimerl_libparser.py %s %s" % (this.shellquote(this.project_root), this.shellquote(dest_file_base)))
				# release lock
				SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] = False
				# trigger event to reload completions
				this.load_current_project_completions()
				this.status("Finished regenerating Project completions.")

		SublimErlThread().start()


# listener
class SublimErlCompletionsListener(sublime_plugin.EventListener):

	# CALLBACK ON VIEW SAVE
	def on_post_save(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# ensure context matches
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		completions = SublimErlCompletions(view)
		# compile saved file & reload completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# trigger event to reload completions
				completions.generate_project_completions()
		SublimErlThread().start()

	# CALLBACK ON VIEW LOADED
	def on_load(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# only trigger within erlang
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		completions = SublimErlCompletions(view)
		# get completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# trigger event to reload completions
				completions.get_available_completions()
		SublimErlThread().start()

	# CALLBACK ON QUERY COMPLETIONS
	def on_query_completions(self, view, prefix, locations):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# only trigger within erlang
		if not view.match_selector(locations[0], "source.erlang"): return []

		# only trigger if : was hit
		pt = locations[0] - len(prefix) - 1
		ch = view.substr(sublime.Region(pt, pt + 1))
		if ch != ':': return []

		# get function name that triggered the autocomplete
		function_name = view.substr(view.word(pt))
		if function_name.strip() == ':': return
		# check for existance
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['erlang_libs']['completions'].has_key(function_name):
			available_completions = SUBLIMERL_COMPLETIONS['erlang_libs']['completions'][function_name]
		elif SUBLIMERL_COMPLETIONS['current_project']['completions'].has_key(function_name):
			available_completions = SUBLIMERL_COMPLETIONS['current_project']['completions'][function_name]
		else: return

		# return snippets
		return (available_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

########NEW FILE########
__FILENAME__ = sublimerl_core
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================

# globals
SUBLIMERL_VERSION = '0.5.1'

# imports
import sublime, sublime_plugin
import os, subprocess, re

# plugin initialized (Sublime might need to be restarted if some env configs / preferences change)
class SublimErlGlobal():

	def __init__(self):
		# default
		self.initialized = False
		self.init_errors = []

		self.plugin_path = None
		self.completions_path = None
		self.support_path = None

		self.erl_path = None
		self.escript_path = None
		self.rebar_path = None
		self.dialyzer_path = None
		self.erlang_libs_path = None

		self.last_test = None
		self.last_test_type = None
		self.test_in_progress = False

		self.env = None
		self.settings = None
		self.completion_skip_erlang_libs = None

		# initialize
		self.set_settings()
		self.set_env()
		self.set_completion_skip_erlang_libs()

		if self.set_paths() == True and self.set_erlang_libs_path() == True:
			# available
			self.initialized = True

	def set_settings(self):
		self.settings = sublime.load_settings('SublimErl.sublime-settings')

	def set_env(self):
		# TODO: enhance the finding of paths
		self.env = os.environ.copy()
		if sublime.platform() == 'osx':
			# get relevant file paths
			etc_paths = ['/etc/paths']
			for f in os.listdir('/etc/paths.d'):
				etc_paths.append(os.path.join('/etc/paths.d', f))
			# bash profile
			bash_profile_path = os.path.join(os.getenv('HOME'), '.bash_profile')
			# get env paths
			additional_paths = "%s:%s" % (self._readfiles_one_path_per_line(etc_paths), self._readfiles_exported_paths([bash_profile_path]))
			# add
			self.env['PATH'] = self.env['PATH'] + additional_paths

	def _readfiles_one_path_per_line(self, file_paths):
		concatenated_paths = []
		for file_path in file_paths:
			if os.path.exists(file_path):
				f = open(file_path, 'r')
				paths = f.read()
				f.close()
				paths = paths.split('\n')
				for path in paths:
					concatenated_paths.append(path.strip())
		return ':'.join(concatenated_paths)

	def _readfiles_exported_paths(self, file_paths):
		concatenated_paths = []
		for file_path in file_paths:
			if os.path.exists(file_path):
				p = subprocess.Popen(". %s; echo $PATH" % file_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				path, stderr = p.communicate()
				concatenated_paths.append(path.strip())
		return ''.join(concatenated_paths)

	def set_paths(self):

		def log(message):
			self.init_errors.append(message)
			print "SublimErl Init Error: %s" % message

		def test_path(path):
			return path != None and os.path.exists(path)

		# erl check
		self.erl_path = self.settings.get('erl_path', self.get_exe_path('erl'))
		if test_path(self.erl_path) == False:
			log("Erlang binary (erl) cannot be found.")

		# escript check
		self.escript_path = self.settings.get('escript_path', self.get_exe_path('escript'))
		if test_path(self.escript_path) == False:
			log("Erlang binary (escript) cannot be found.")

		# rebar
		self.rebar_path = self.settings.get('rebar_path', self.get_exe_path('rebar'))
		if test_path(self.rebar_path) == False:
			log("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return False
			return False

		# dialyzer check
		self.dialyzer_path = self.settings.get('dialyzer_path', self.get_exe_path('dialyzer'))
		if test_path(self.dialyzer_path) == False:
			log("Erlang Dyalizer cannot be found.")
			return False

		# paths
		self.plugin_path = os.path.join(sublime.packages_path(), 'SublimErl')
		self.completions_path = os.path.join(self.plugin_path, "completion")
		self.support_path = os.path.join(self.plugin_path, "support")

		return True

	def strip_code_for_parsing(self, code):
		code = self.strip_comments(code)
		code = self.strip_quoted_content(code)
		return self.strip_record_with_dots(code)

	def strip_comments(self, code):
		# strip comments but keep the same character count
		return re.sub(re.compile(r"%(.*)\n"), lambda m: (len(m.group(0)) - 1) * ' ' + '\n', code)

	def strip_quoted_content(self, code):
		# strip quoted content
		regex = re.compile(r"(\"([^\"]*)\")", re.MULTILINE + re.DOTALL)
		for m in regex.finditer(code):
			code = code[:m.start()] + (len(m.groups()[0]) * ' ') + code[m.end():]
		return code

	def strip_record_with_dots(self, code):
		# strip records with dot notation
		return re.sub(re.compile(r"(\.[a-z]+)"), lambda m: len(m.group(0)) * ' ', code)

	def get_erlang_module_name(self, view):
		# find module declaration and get module name
		module_region = view.find(r"^\s*-\s*module\s*\(\s*(?:[a-zA-Z0-9_]+)\s*\)\s*\.", 0)
		if module_region != None:
			m = re.match(r"^\s*-\s*module\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.", view.substr(module_region))
			return m.group(1)

	def get_exe_path(self, name):
		retcode, data = self.execute_os_command('which %s' % name)
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			return data

	def set_erlang_libs_path(self):
		# run escript to get erlang lib path
		os.chdir(self.support_path)
		escript_command = "sublimerl_utility.erl lib_dir"
		retcode, data = self.execute_os_command('%s %s' % (self.escript_path, escript_command))
		self.erlang_libs_path = data
		return self.erlang_libs_path != ''

	def set_completion_skip_erlang_libs(self):
		self.completion_skip_erlang_libs = self.settings.get('completion_skip_erlang_libs', [])

	def execute_os_command(self, os_cmd):
		# start proc
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=self.env)
		stdout, stderr = p.communicate()
		return (p.returncode, stdout)


	def shellquote(self, s):
		return "'" + s.replace("'", "'\\''") + "'"


# initialize
SUBLIMERL = SublimErlGlobal()


# project loader
class SublimErlProjectLoader():

	def __init__(self, view):
		# init
		self.view = view
		self.window = view.window()
		self.status_buffer = ''

		self.erlang_module_name = None
		self.project_root = None
		self.test_root = None
		self.app_name = None

		self.set_erlang_module_name()
		self.set_project_roots()
		self.set_app_name()

	def set_erlang_module_name(self):
		self.erlang_module_name = SUBLIMERL.get_erlang_module_name(self.view)

	def set_project_roots(self):
		# get project & file roots
		current_file_path = os.path.dirname(self.view.file_name())
		project_root, file_test_root = self.find_project_roots(current_file_path)

		if project_root == file_test_root == None:
			self.project_root = self.test_root = None
			return

		# save
		self.project_root = os.path.abspath(project_root)
		self.test_root = os.path.abspath(file_test_root)

	def find_project_roots(self, current_dir, project_root_candidate=None, file_test_root_candidate=None):
		# if rebar.config or an ebin directory exists, save as potential candidate
		if os.path.exists(os.path.join(current_dir, 'rebar.config')) or os.path.exists(os.path.join(current_dir, 'ebin')):
			# set project root candidate
			project_root_candidate = current_dir
			# set test root candidate if none set yet
			if file_test_root_candidate == None: file_test_root_candidate = current_dir

		current_dir_split = current_dir.split(os.sep)
		# if went up to root, stop and return current candidate
		if len(current_dir_split) < 2: return (project_root_candidate, file_test_root_candidate)
		# walk up directory
		current_dir_split.pop()
		return self.find_project_roots(os.sep.join(current_dir_split), project_root_candidate, file_test_root_candidate)

	def set_app_name(self):
		# get app file
		src_path = os.path.join(self.test_root, 'src')
		for f in os.listdir(src_path):
			if f.endswith('.app.src'):
				app_file_path = os.path.join(src_path, f)
				self.app_name = self.find_app_name(app_file_path)

	def find_app_name(self, app_file_path):
		f = open(app_file_path, 'rb')
		app_desc = f.read()
		f.close()
		m = re.search(r"{\s*application\s*,\s*('?[A-Za-z0-9_]+'?)\s*,\s*\[", app_desc)
		if m:
			return m.group(1)

	def update_status(self):
		if len(self.status_buffer):
			sublime.status_message(self.status_buffer)
			self.status_buffer = ''

	def status(self, text):
		self.status_buffer += text
		sublime.set_timeout(self.update_status, 0)

	def log(self, text):
		pass

	def get_test_env(self):
		env = SUBLIMERL.env.copy()
		env['PATH'] = "%s:%s:" % (env['PATH'], self.project_root)
		return env

	def compile_source(self, skip_deps=False):
		# compile to ebin
		options = 'skip_deps=true' if skip_deps else ''
		retcode, data = self.execute_os_command('%s compile %s' % (SUBLIMERL.rebar_path, options), dir_type='project', block=True, log=False)
		return (retcode, data)

	def shellquote(self, s):
		return SUBLIMERL.shellquote(s)

	def execute_os_command(self, os_cmd, dir_type=None, block=False, log=True):
		# set dir
		if dir_type == 'project': os.chdir(self.project_root)
		elif dir_type == 'test': os.chdir(self.test_root)

		if log == True: self.log("%s$ %s\n\n" % (os.getcwd(), os_cmd))

		# start proc
		current_env = self.get_test_env()
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=current_env)
		if block == True:
			stdout, stderr = p.communicate()
			return (p.returncode, stdout)
		else:
			stdout = []
			for line in p.stdout:
				self.log(line)
				stdout.append(line)
			return (p.returncode, ''.join(stdout))


# common text command class
class SublimErlTextCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# run only if context matches
		if self._context_match():
			# check
			if SUBLIMERL.initialized == False:
				# self.log("SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors))
				print "SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors)
				return
			else:
				return self.run_command(edit)

	def _context_match(self):
		# context matches if lang is source.erlang and if platform is not windows
		caret = self.view.sel()[0].a
		if 'source.erlang' in self.view.scope_name(caret) and sublime.platform() != 'windows': return True
		else: return False

	def is_enabled(self):
		# context menu
		if self._context_match(): return self.show_contextual_menu()

	def show_contextual_menu(self):
		# can be overridden
		return True

########NEW FILE########
__FILENAME__ = sublimerl_formatter
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================


# imports
import sublime, sublime_plugin, os, tempfile
from sublimerl_core import SUBLIMERL, SublimErlTextCommand, SublimErlProjectLoader


# main autoformat
class SublimErlAutoFormat():

	def __init__(self, view, edit):
		self.view = view
		self.edit = edit

	def format(self):
		# save current caret position
		current_region = self.view.sel()[0]
		# save current file contents to temp file
		region_full = sublime.Region(0, self.view.size())
		content = self.view.substr(region_full).encode('utf-8')
		temp = tempfile.NamedTemporaryFile(delete=False)
		temp.write(content)
		temp.close()
		# call erlang formatter
		os.chdir(SUBLIMERL.support_path)
		escript_command = "sublimerl_formatter.erl %s" % SUBLIMERL.shellquote(temp.name)
		retcode, data = SUBLIMERL.execute_os_command('%s %s' % (SUBLIMERL.escript_path, escript_command))
		# delete temp file
		os.remove(temp.name)
		if retcode == 0:
			# substitute text
			self.view.replace(self.edit, region_full, data.decode('utf-8'))
			# reset caret to original position
			self.view.sel().clear()
			self.view.sel().add(current_region)
			self.view.show(current_region)


# format command
class SublimErlAutoFormatCommand(SublimErlTextCommand):
	def run_command(self, edit):
		formatter = SublimErlAutoFormat(self.view, edit)
		formatter.format()

########NEW FILE########
__FILENAME__ = sublimerl_function_search
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================


# imports
import sublime
import os, time, threading, pickle
from sublimerl_core import SUBLIMERL, SublimErlTextCommand, SublimErlProjectLoader
from sublimerl_completion import SUBLIMERL_COMPLETIONS


# main autoformat
class SublimErlFunctionSearch():

	def __init__(self, view):
		# init
		self.view = view
		self.window = view.window()
		self.search_completions = []

	def show(self):
		# get completions
		self.set_search_completions()
		# strip out just the function name to be displayed
		completions = []
		for name, filepath, lineno in self.search_completions:
			completions.append(name)
		# open quick panel
		sublime.active_window().show_quick_panel(completions, self.on_select)

	def set_search_completions(self):
		# load file
		searches_filepath = os.path.join(SUBLIMERL.plugin_path, "completion", "Current-Project.searches")
		f = open(searches_filepath, 'r')
		searches = pickle.load(f)
		f.close()
		self.search_completions = searches

	def on_select(self, index):
		# get file and line
		name, filepath, lineno = self.search_completions[index]
		# open module at function position
		self.open_file_and_goto_line(filepath, lineno)

	def open_file_and_goto_line(self, filepath, line):
		# open file
		self.new_view = self.window.open_file(filepath)
		# wait until file is loaded before going to the appropriate line
		this = self
		self.check_file_loading()
		class SublimErlThread(threading.Thread):
			def run(self):
				# wait until file has done loading
				s = 0
				while this.is_loading and s < 3:
					time.sleep(0.1)
					sublime.set_timeout(this.check_file_loading, 0)
					s += 1
				# goto line
				def goto_line():
					# goto line
					this.new_view.run_command("goto_line", {"line": line} )
					# remove unused attrs
					del this.new_view
					del this.is_loading
				if not this.is_loading: sublime.set_timeout(goto_line, 0)

		SublimErlThread().start()

	def check_file_loading(self):
		self.is_loading = self.new_view.is_loading()


# repeat last test
class SublimErlFunctionSearchCommand(SublimErlTextCommand):
	def run_command(self, edit):
		search = SublimErlFunctionSearch(self.view)
		search.show()

########NEW FILE########
__FILENAME__ = sublimerl_man
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================


# imports
import sublime
import os
from sublimerl_core import SUBLIMERL, SublimErlTextCommand, SublimErlGlobal


# show man
class SublimErlMan():

	def __init__(self, view):
		# init
		self.view = view
		self.window = view.window()
		self.module_names = []

		self.panel_name = 'sublimerl_man'
		self.panel_buffer = ''
		# setup panel
		self.setup_panel()

	def setup_panel(self):
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmLanguage"))
		self.panel.settings().set("color_scheme", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def hide_panel(self):
		self.window.run_command("hide_panel")

	def log(self, text):
		self.panel_buffer += text
		sublime.set_timeout(self.update_panel, 0)

	def show(self):
		# set modules
		self.set_module_names()
		# open quick panel
		sublime.active_window().show_quick_panel(self.module_names, self.on_select)

	def set_module_names(self):
		# load file
		modules_filepath = os.path.join(SUBLIMERL.plugin_path, "completion", "Erlang-libs.sublime-completions")
		f = open(modules_filepath, 'r')
		contents = eval(f.read())
		f.close()
		# strip out just the module names to be displayed
		module_names = []
		for t in contents['completions']:
			module_names.append(t['trigger'])
		self.module_names = module_names

	def on_select(self, index):
		# get file and line
		module_name = self.module_names[index]
		# open man
		retcode, data = SUBLIMERL.execute_os_command("%s -man %s | col -b" % (SUBLIMERL.erl_path, module_name))
		if retcode == 0: self.log(data)


# man command
class SublimErlManCommand(SublimErlTextCommand):
	def run_command(self, edit):
		man = SublimErlMan(self.view)
		man.show()

########NEW FILE########
__FILENAME__ = sublimerl_tests_integration
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================


# imports
import sublime
import os, subprocess, re, threading, webbrowser
from sublimerl_core import SUBLIMERL_VERSION, SUBLIMERL, SublimErlTextCommand, SublimErlProjectLoader


# test runner
class SublimErlTestRunner(SublimErlProjectLoader):

	def __init__(self, view):
		# init super
		SublimErlProjectLoader.__init__(self, view)

		# init
		self.initialized = False
		self.panel_name = 'sublimerl_tests'
		self.panel_buffer = ''

		# don't proceed if a test is already running
		global SUBLIMERL
		if SUBLIMERL.test_in_progress == True: return
		SUBLIMERL.test_in_progress = True

		# setup panel
		self.setup_panel()
		# run
		if self.init_tests() == True:
			self.initialized = True
		else:
			SUBLIMERL.test_in_progress = False

	def setup_panel(self):
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlTests.hidden-tmLanguage"))
		self.panel.settings().set("color_scheme", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlTests.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def log(self, text):
		self.panel_buffer += text.encode('utf-8')
		sublime.set_timeout(self.update_panel, 0)

	def log_error(self, error_text):
		self.log("Error => %s\n[ABORTED]\n" % error_text)

	def init_tests(self):
		if SUBLIMERL.initialized == False:
			self.log("SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors))

		# file saved?
		if self.view.is_scratch():
			self.log_error("Please save this file to proceed.")
			return False
		elif os.path.splitext(self.view.file_name())[1] != '.erl':
			self.log_error("This is not a .erl file.")
			return False

		# check module name
		if self.erlang_module_name == None:
			self.log_error("Cannot find a -module declaration: please add one to proceed.")
			return False

		# save project's root paths
		if self.project_root == None or self.test_root == None:
			self.log_error("This code does not seem to be part of an OTP compilant project.")
			return False

		# all ok
		return True

	def compile_eunit_no_run(self):
		# call rebar to compile -  HACK: passing in a non-existing suite forces rebar to not run the test suite
		os_cmd = '%s eunit suites=sublimerl_unexisting_test' % SUBLIMERL.rebar_path
		if self.app_name: os_cmd += ' apps=%s' % self.app_name
		retcode, data = self.execute_os_command(os_cmd, dir_type='project', block=True, log=False)

		if re.search(r"There were no tests to run", data) != None:
			# expected error returned (due to the hack)
			return 0
		# send the data to panel
		self.log(data)

	def reset_last_test(self):
		global SUBLIMERL

		SUBLIMERL.last_test = None
		SUBLIMERL.last_test_type = None

	def start_test(self, new=True):
		# do not continue if no previous test exists and a redo was asked
		if SUBLIMERL.last_test == None and new == False: return
		# set test
		if new == True: self.reset_last_test()
		# test callback
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)
		self.start_test_cmd(new)

	def start_test_cmd(self, new):
		# placeholder for inheritance
		pass

	def on_test_ended(self):
		global SUBLIMERL
		SUBLIMERL.test_in_progress = False


# dialyzer test runner
class SublimErlDialyzerTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		if new == True:
			# save test module
			module_tests_name = self.erlang_module_name

			SUBLIMERL.last_test = module_tests_name
			SUBLIMERL.last_test_type = 'dialyzer'
		else:
			# retrieve test module
			module_tests_name = SUBLIMERL.last_test

		# run test
		this = self
		filename = self.view.file_name()
		class SublimErlThread(threading.Thread):
			def run(self):
				this.dialyzer_test(module_tests_name, filename)
		SublimErlThread().start()

	def dialyzer_test(self, module_tests_name, filename):
		# run dialyzer for file
		self.log("Running Dialyzer tests for \"%s\".\n\n" % filename)
		# compile eunit
		self.compile_eunit_no_run()
		# run dialyzer
		retcode, data = self.execute_os_command('%s -n .eunit/%s.beam' % (SUBLIMERL.dialyzer_path, module_tests_name), dir_type='test', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
		# get outputs
		if re.search(r"passed successfully", data):
			self.log("\n=> TEST(S) PASSED.\n")
		else:
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


# eunit test runner
class SublimErlEunitTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		# run test
		if new == True:
			# get test module name
			pos = self.erlang_module_name.find("_tests")
			if pos == -1:
				# tests are in the same file
				module_name = self.erlang_module_name
			else:
				# tests are in different files
				module_name = self.erlang_module_name[0:pos]

			# get function name depending on cursor position
			function_name = self.get_test_function_name()

			# save test
			module_tests_name = self.erlang_module_name
			SUBLIMERL.last_test = (module_name, module_tests_name, function_name)
			SUBLIMERL.last_test_type = 'eunit'

		else:
			# retrieve test info
			module_name, module_tests_name, function_name = SUBLIMERL.last_test

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.eunit_test(module_name, module_tests_name, function_name)
		SublimErlThread().start()

	def get_test_function_name(self):
		# get current line position
		cursor_position = self.view.sel()[0].a
		# get module content
		region_full = sublime.Region(0, self.view.size())
		module = SUBLIMERL.strip_code_for_parsing(self.view.substr(region_full))
		# parse regions
		regex = re.compile(r"([a-z0-9][a-zA-Z0-9_]*_test(_)?\s*\(\s*\)\s*->[^.]*\.)", re.MULTILINE)
		for m in regex.finditer(module):
			if m.start() <= cursor_position and cursor_position <= m.end():
				function_content = m.groups()[0]
				return function_content[:function_content.index('(')]

	def eunit_test(self, module_name, module_tests_name, function_name):
		if function_name != None:
			# specific function provided, start single test
			self.log("Running test \"%s:%s/0\" for target module \"%s.erl\".\n\n" % (module_tests_name, function_name, module_name))
			# compile source code and run single test
			self.compile_eunit_run_suite(module_tests_name, function_name)
		else:
			# run all test functions in file
			if module_tests_name != module_name:
				self.log("Running all tests in module \"%s.erl\" for target module \"%s.erl\".\n\n" % (module_tests_name, module_name))
			else:
				self.log("Running all tests for target module \"%s.erl\".\n\n" % module_name)
			# compile all source code and test module
			self.compile_eunit_run_suite(module_tests_name)

	def compile_eunit_run_suite(self, suite, function_name=None):
		os_cmd = '%s eunit suites=%s' % (SUBLIMERL.rebar_path, suite)

		if function_name != None: os_cmd += ' tests=%s' % function_name
		if self.app_name: os_cmd += ' apps=%s' % self.app_name

		os_cmd += ' skip_deps=true'

		retcode, data = self.execute_os_command(os_cmd, dir_type='project', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
		# get outputs
		if re.search(r"Test passed.", data):
			# single test passed
			self.log("\n=> TEST PASSED.\n")

		elif re.search(r"All \d+ tests passed.", data):
			# multiple tests passed
			passed_count = re.search(r"All (\d+) tests passed.", data).group(1)
			self.log("\n=> %s TESTS PASSED.\n" % passed_count)

		elif re.search(r"Failed: \d+.", data):
			# some tests failed
			failed_count = re.search(r"Failed: (\d+).", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)

		elif re.search(r"There were no tests to run.", data):
			self.log("\n=> NO TESTS TO RUN.\n")

		else:
			self.log(data)
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


# eunit test runner
class SublimErlCtTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		# run test
		if new == True:
			pos = self.erlang_module_name.find("_SUITE")
			module_tests_name = self.erlang_module_name[0:pos]

			# save test
			SUBLIMERL.last_test = module_tests_name
			SUBLIMERL.last_test_type = 'ct'

		else:
			module_tests_name = SUBLIMERL.last_test

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.ct_test(module_tests_name)
		SublimErlThread().start()

	def ct_test(self, module_tests_name):
		# run CT for suite
		self.log("Running tests of Common Tests SUITE \"%s_SUITE.erl\".\n\n" % module_tests_name)
		os_cmd = '%s ct suites=%s skip_deps=true' % (SUBLIMERL.rebar_path, module_tests_name)
		# compile all source code
		self.compile_source()
		# run suite
		retcode, data = self.execute_os_command(os_cmd, dir_type='test', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
		# get outputs
		if re.search(r"DONE.", data):
			# test passed
			passed_count = re.search(r"(\d+) ok, 0 failed(?:, 1 skipped)? of \d+ test cases", data).group(1)
			if int(passed_count) > 0:
				self.log("=> %s TEST(S) PASSED.\n" % passed_count)
			else:
				self.log("=> NO TESTS TO RUN.\n")

		elif re.search(r"ERROR: One or more tests failed", data):
			failed_count = re.search(r"\d+ ok, (\d+) failed(?:, 1 skipped)? of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)

		else:
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


### Commands
# test runners
class SublimErlTestRunners():

	def dialyzer_test(self, view):
		test_runner = SublimErlDialyzerTestRunner(view)
		if test_runner.initialized == False: return
		test_runner.start_test()

	def ct_or_eunit_test(self, view, new=True):
		if SUBLIMERL.last_test_type == 'ct' or SUBLIMERL.get_erlang_module_name(view).find("_SUITE") != -1:
			# ct
			test_runner = SublimErlCtTestRunner(view)
		else:
			# eunit
			test_runner = SublimErlEunitTestRunner(view)

		if test_runner.initialized == False: return
		test_runner.start_test(new=new)


# dialyzer tests
class SublimErlDialyzerCommand(SublimErlTextCommand):
	def run_command(self, edit):
		SublimErlTestRunners().dialyzer_test(self.view)


# start new test
class SublimErlTestCommand(SublimErlTextCommand):
	def run_command(self, edit):
		SublimErlTestRunners().ct_or_eunit_test(self.view)


# repeat last test
class SublimErlRedoCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		if SUBLIMERL.last_test_type == 'dialyzer': SublimErlTestRunners().dialyzer_test(self.view, new=False)
		elif SUBLIMERL.last_test_type == 'eunit' or SUBLIMERL.last_test_type == 'ct': SublimErlTestRunners().ct_or_eunit_test(self.view, new=False)

	def show_contextual_menu(self):
		return SUBLIMERL.last_test != None


# open CT results
class SublimErlCtResultsCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# open CT results
		loader = SublimErlProjectLoader(self.view)
		index_path = os.path.abspath(os.path.join(loader.project_root, 'logs', 'index.html'))
		if os.path.exists(index_path): webbrowser.open(index_path)

	def show_contextual_menu(self):
		loader = SublimErlProjectLoader(self.view)
		index_path = os.path.abspath(os.path.join(loader.project_root, 'logs', 'index.html'))
		return os.path.exists(index_path)

########NEW FILE########
__FILENAME__ = sublimerl_libparser
# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================

import sys, re, os, fnmatch, pickle, string, unittest

class SublimErlLibParser():

	def __init__(self):
		# compile default regexes
		self.regex = {
			'all': re.compile(r"(.*)", re.MULTILINE),
			'export_section': re.compile(r"^\s*-\s*export\s*\(\s*\[\s*([^\]]*)\s*\]\s*\)\s*\.", re.DOTALL + re.MULTILINE),
			'varname': re.compile(r"^[A-Z][a-zA-Z0-9_]*$"),
			'{': re.compile(r"\{.*\}"),
			'<<': re.compile(r"<<.*>>"),
			'[': re.compile(r"\[.*\]")
		}

	def strip_comments(self, code):
		# strip comments but keep the same character count
		return re.sub(re.compile(r"%(.*)\n"), lambda m: (len(m.group(0)) - 1) * ' ' + '\n', code)

	def generate_completions(self, starting_dir, dest_file_base):
		# init
		disasms = {}
		completions = []
		searches = []
		# loop directory
		rel_dirs = []
		for root, dirnames, filenames in os.walk(starting_dir):
			if 'reltool.config' in filenames:
				# found a release directory, we will ignore autocompletion for these files
				rel_dirs.append(root)
			# loop filenames ending in .erl
			for filename in fnmatch.filter(filenames, r"*.erl"):
				if '.eunit' not in root.split('/'):
					# exclude eunit files
					filepath = os.path.join(root, filename)
					# check if in release directory
					if not (True in [filepath.find(rel_dir) != -1 for rel_dir in rel_dirs]):
						# not in a release directory, get module name
						module_name, module_ext = os.path.splitext(filename)
						# get module content
						f = open(filepath, 'r')
						module = self.strip_comments(f.read())
						f.close()
						# get completions
						module_completions, line_numbers = self.get_completions(module)
						if len(module_completions) > 0:
							# set disasm
							disasms[module_name] = sorted(module_completions, key=lambda k: k[0])
							# set searches
							for i in range(0, len(module_completions)):
								function, completion = module_completions[i]
								searches.append(("%s:%s" % (module_name, function), filepath, line_numbers[i]))
							# set module completions
							completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (module_name, module_name))

		# add BIF completions?
		if disasms.has_key('erlang'):
			# we are generating erlang disasm
			bif_completions = self.bif_completions()
			for k in bif_completions.keys():
				disasms[k].extend(bif_completions[k])
				# sort
				disasms[k] = sorted(disasms[k], key=lambda k: k[0])
			# erlang completions
			for c in bif_completions['erlang']:
				completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (c[0], c[1]))
		else:
			# we are generating project disasm -> write to files: searches
			f_searches = open("%s.searches" % dest_file_base, 'wb')
			pickle.dump(sorted(searches, key=lambda k: k[0]), f_searches)
			f_searches.close()

		# write to files: disasms
		f_disasms = open("%s.disasm" % dest_file_base, 'wb')
		pickle.dump(disasms, f_disasms)
		f_disasms.close()
		# write to files: completions
		f_completions = open("%s.sublime-completions" % dest_file_base, 'wb')
		if len(completions) > 0:
			f_completions.write("{ \"scope\": \"source.erlang\", \"completions\": [\n" + ',\n'.join(completions) + "\n]}")
		else:
			f_completions.write("{}")
		f_completions.close()

	def get_completions(self, module):
		# get export portion in code module

		all_completions = []
		all_line_numbers = []
		for m in self.regex['export_section'].finditer(module):
			export_section = m.groups()[0]
			if export_section:
				# get list of exports
				exports = self.get_code_list(export_section)
				if len(exports) > 0:
					# add to existing completions
					completions, line_numbers = self.generate_module_completions(module, exports)
					all_completions.extend(completions)
					all_line_numbers.extend(line_numbers)
		# return all_completions
		return (all_completions, all_line_numbers)

	def bif_completions(self):
		# default BIFs not available in modules
		return {
			'erlang': [
				('abs/1', 'abs(${1:Number}) $2'),
				('atom_to_binary/2', 'atom_to_binary(${1:Atom}, ${2:Encoding}) $3'),
				('atom_to_list/1', 'atom_to_list(${1:Atom}) $2'),
				('binary_part/2', 'binary_part(${1:Subject}, ${2:PosLen}) $3'),
				('binary_part/3', 'binary_part(${1:Subject}, ${2:Start}, ${3:Length}) $4'),
				('binary_to_atom/2', 'binary_to_atom(${1:Binary}, ${2:Encoding}) $3'),
				('binary_to_existing_atom/2', 'binary_to_existing_atom(${1:Binary}, ${2:Encoding}) $3'),
				('binary_to_list/1', 'binary_to_list(${1:Binary}) $2'),
				('binary_to_list/3', 'binary_to_list(${1:Binary}, ${2:Start}, ${3:Stop}) $4'),
				('bitstring_to_list/1', 'bitstring_to_list(${1:Bitstring}) $2'),
				('binary_to_term/2', 'binary_to_term(${1:Binary}, ${2:Opts}) $3'),
				('bit_size/1', 'bit_size(${1:Bitstring}) $2'),
				('byte_size/1', 'byte_size(${1:Bitstring}) $2'),
				('check_old_code/1', 'check_old_code(${1:Module}) $2'),
				('check_process_code/2', 'check_process_code(${1:Pid}, ${2:Module}) $3'),
				('date/0', 'date() $1'),
				('delete_module/1', 'delete_module(${1:Module}) $2'),
				('demonitor/1', 'demonitor(${1:MonitorRef}) $2'),
				('demonitor/2', 'demonitor(${1:MonitorRef}, ${2:OptionList}) $3'),
				('element/2', 'element(${1:N}, ${2:Tuple}) $3'),
				('erase/0', 'erase() $1'),
				('erase/1', 'erase(${1:Key}) $2'),
				('error/1', 'error(${1:Reason}) $2'),
				('error/2', 'error(${1:Reason}, ${2:Args}) $3'),
				('exit/1', 'exit(${1:Reason}) $2'),
				('exit/2', 'exit(${1:Reason}, ${2:Args}) $3'),
				('float/1', 'float(${1:Number}) $2'),
				('float_to_list/1', 'float_to_list(${1:Float}) $2'),
				('garbage_collect/0', 'garbage_collect() $1'),
				('garbage_collect/1', 'garbage_collect(${1:Pid}) $2'),
				('get/0', 'get() $1'),
				('get/1', 'get(${1:Key}) $2'),
				('get_keys/1', 'get_keys(${1:Val}) $2'),
				('group_leader/0', 'group_leader() $1'),
				('group_leader/2', 'group_leader(${1:GroupLeader}, ${2:Pid}) $3'),
				('halt/0', 'halt() $1'),
				('halt/1', 'halt(${1:Status}) $2'),
				('halt/2', 'halt(${1:Status}, ${2:Options}) $3'),
				('hd/1', 'hd(${1:List}) $2'),
				('integer_to_list/1', 'integer_to_list(${1:Integer}) $2'),
				('iolist_to_binary/1', 'iolist_to_binary(${1:IoListOrBinary}) $2'),
				('iolist_size/1', 'iolist_size(${1:Item}) $2'),
				('is_alive/0', 'is_alive() $1'),
				('is_atom/1', 'is_atom(${1:Term}) $2'),
				('is_binary/1', 'is_binary(${1:Term}) $2'),
				('is_bitstring/1', 'is_bitstring(${1:Term}) $2'),
				('is_boolean/1', 'is_boolean(${1:Term}) $2'),
				('is_float/1', 'is_float(${1:Term}) $2'),
				('is_function/1', 'is_function(${1:Term}) $2'),
				('is_function/2', 'is_function(${1:Term}, ${2:Arity}) $3'),
				('is_integer/1', 'is_integer(${1:Term}) $2'),
				('is_list/1', 'is_list(${1:Term}) $2'),
				('is_number/1', 'is_number(${1:Term}) $2'),
				('is_pid/1', 'is_pid(${1:Term}) $2'),
				('is_port/1', 'is_port(${1:Term}) $2'),
				('is_process_alive/1', 'is_process_alive(${1:Pid}) $2'),
				('is_record/2', 'is_record(${1:Term}, ${2:RecordTag}) $3'),
				('is_record/3', 'is_record(${1:Term}, ${2:RecordTag}, ${3:Size}) $4'),
				('is_reference/1', 'is_reference(${1:Term}) $2'),
				('is_tuple/1', 'is_tuple(${1:Term}) $2'),
				('length/1', 'length(${1:List}) $2'),
				('link/1', 'link(${1:Pid}) $2'),
				('list_to_atom/1', 'list_to_atom(${1:String}) $2'),
				('list_to_binary/1', 'list_to_binary(${1:IoList}) $2'),
				('list_to_bitstring/1', 'list_to_bitstring(${1:BitstringList}) $2'),
				('list_to_existing_atom/1', 'list_to_existing_atom(${1:String}) $2'),
				('list_to_float/1', 'list_to_float(${1:String}) $2'),
				('list_to_integer/1', 'list_to_integer(${1:String}) $2'),
				('list_to_pid/1', 'list_to_pid(${1:String}) $2'),
				('list_to_tuple/1', 'list_to_tuple(${1:List}) $2'),
				('load_module/2', 'load_module(${1:Module}, ${2:Binary}) $3'),
				('make_ref/0', 'make_ref() $1'),
				('module_loaded/1', 'module_loaded(${1:Module}) $2'),
				('monitor/2', 'monitor(${1:Type}, ${2:Item}) $3'),
				('monitor_node/2', 'monitor_node(${1:Node}, ${2:Flag}) $3'),
				('node/0', 'node() $1'),
				('node/1', 'node(${1:Arg}) $2'),
				('nodes/1', 'nodes(${1:Arg}) $2'),
				('now/0', 'now() $1'),
				('open_port/2', 'open_port(${1:PortName}, ${2:PortSettings}) $3'),
				('pid_to_list/1', 'pid_to_list(${1:Pid}) $2'),
				('port_close/1', 'port_close(${1:Port}) $2'),
				('port_command/2', 'port_command(${1:Port}, ${2:Data}) $3'),
				('port_command/3', 'port_command(${1:Port}, ${2:Data}, ${3:OptionList}) $4'),
				('port_connect/2', 'port_connect(${1:Port}, ${2:Pid}) $3'),
				('port_control/3', 'port_control(${1:Port}, ${2:Operation}, ${3:Data}) $4'),
				('pre_loaded/0', 'pre_loaded() $1'),
				('process_flag/2', 'process_flag(${1:Flag}, ${2:Value}) $3'),
				('process_flag/3', 'process_flag(${1:Pid}, ${2:Flag}, ${3:Value}) $4'),
				('process_info/1', 'process_info(${1:Pid}) $2'),
				('process_info/2', 'process_info(${1:Pid}, ${2:ItemSpec}) $3'),
				('processes/0', 'processes() $1'),
				('purge_module/1', 'purge_module(${1:Module}) $2'),
				('put/2', 'put(${1:Key}, ${2:Val}) $3'),
				('register/2', 'put(${1:RegName}, ${2:PidOrPort}) $3'),
				('registered/0', 'registered() $1'),
				('round/1', 'round(${1:Number}) $2'),
				('self/0', 'self() $1'),
				('setelement/3', 'setelement(${1:Index}, ${2:Tuple1}, ${3:Value}) $4'),
				('size/1', 'size(${1:Item}) $2'),
				('spawn/3', 'spawn(${1:Module}, ${2:Function}) $3, ${3:Args}) $4'),
				('spawn_link/3', 'spawn_link(${1:Module}, ${2:Function}, ${3:Args}) $4'),
				('split_binary/2', 'split_binary(${1:Bin}, ${2:Pos}) $3'),
				('statistics/1', 'statistics(${1:Type}) $2'),
				('term_to_binary/1', 'term_to_binary(${1:Term}) $2'),
				('term_to_binary/2', 'term_to_binary(${1:Term}, ${2:Options}) $3'),
				('throw/1', 'throw(${1:Any}) $2'),
				('time/0', 'time() $1'),
				('tl/1', 'tl(${1:List1}) $2'),
				('trunc/1', 'trunc(${1:Number}) $2'),
				('tuple_size/1', 'tuple_size(${1:Tuple}) $2'),
				('tuple_to_list/1', 'tuple_to_list(${1:Tuple}) $2'),
				('unlink/1', 'unlink(${1:Id}) $2'),
				('unregister/1', 'unregister(${1:RegName}) $2'),
				('whereis/1', 'whereis(${1:RegName}) $2')
			],
			'lists': [
				('member/2', 'member(${1:Elem}, ${2:List}) $3'),
				('reverse/2', 'reverse(${1:List1}, ${2:Tail}) $3'),
				('keymember/3', 'keymember(${1:Key}, ${2:N}, ${3:TupleList}) $4'),
				('keysearch/3', 'keysearch(${1:Key}, ${2:N}, ${3:TupleList}) $4'),
				('keyfind/3', 'keyfind(${1:Key}, ${2:N}, ${3:TupleList}) $4')
			]
		}

	def generate_module_completions(self, module, exports):
		# get exports for a module

		completions = []
		line_numbers = []
		for export in exports:
			# split param count definition
			fun = export.split('/')
			if len(fun) == 2:
				# get params
				params, lineno = self.generate_params(fun, module)
				if params != None:
					# add
					completions.append((export, '%s%s' % (fun[0].strip(), params)))
					line_numbers.append(lineno)
		return (completions, line_numbers)

	def generate_params(self, fun, module):
		# generate params for a specific function name

		# get params count
		arity = int(fun[1])
		# init
		current_params = []
		lineno = 0
		# get params
		regex = re.compile(r"%s\((.*)\)\s*->" % re.escape(fun[0]), re.MULTILINE)
		for m in regex.finditer(module):
			params = m.groups()[0]
			# strip out the eventual condition part ('when')
			params = params.split('when')[0].strip()
			if params[-1:] == ')': params = params[:-1]
			# split
			params = self.split_params(params)
			if len(params) == arity:
				# function definition has the correct arity
				# get match line number if this is not a -spec line
				spec_def_pos = module.rfind('-spec', 0, m.start())
				not_a_spec_definition = spec_def_pos == -1 or len(module[spec_def_pos + 5:m.start()].strip()) > 0
				if not_a_spec_definition and lineno == 0: lineno = module.count('\n', 0, m.start()) + 1
				# add to params
				if current_params != []:
					for i in range(0, len(params)):
						if current_params[i] == '*' and self.regex['varname'].search(params[i]):
							# found a valid variable name
							current_params[i] = params[i]
				else:
					# init params
					current_params = params
		# ensure current params have variable names
		for i in range(0, len(current_params)):
			if current_params[i] == '*':
				current_params[i] = '${%d:Param%d}' % (i + 1, i + 1)
			else:
				current_params[i] = '${%d:%s}' % (i + 1, current_params[i])
		# return
		return ('(' + ', '.join(current_params) + ') $%d' % (len(current_params) + 1), lineno)

	def split_params(self, params):
		# return list of params, with proper variable name or wildcard if invalid

		# replace content of graffles with *
		params = self.regex['{'].sub("*", params)
		# replace content of <<>> with *
		params = self.regex['<<'].sub("*", params)
		# replace content of [] with *
		params = self.regex['['].sub("*", params)
		# take away comments and split per line
		params = self.get_code_list(params)
		for p in range(0, len(params)):
			# split on =
			splitted_param = params[p].split('=')
			if len(splitted_param) > 1:
				params[p] = splitted_param[1].strip()
			# spit on :: for spec declarations
			params[p] = params[p].split('::')[0]
			# convert to * where necessary
			if not self.regex['varname'].search(params[p]):
				params[p] = '*'
		# return
		return params

	def get_code_list(self, code):
		# loop every line and add code lines
		cleaned_code_list = []
		for m in self.regex['all'].finditer(code):
			groups = m.groups()
			for i in range(0, len(groups)):
				code_line = groups[i].strip()
				if len(code_line) > 0:
					code_lines = code_line.split(',')
					for code_line in code_lines:
						code_line = code_line.strip()
						if len(code_line) > 0:
							cleaned_code_list.append(code_line)
		return cleaned_code_list


class TestSequenceFunctions(unittest.TestCase):

	def setUp(self):
		self.parser = SublimErlLibParser()

	def test_split_params(self):
		fixtures = [
			("One, Two, Three", ["One", "Two", "Three"]),
			("One", ["One"]),
			("One, <<>>, Three", ["One", "*", "Three"]),
			("One, [], Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB}, Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD}}, Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD}} = Two, Three", ["One", "Two", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD} = TwoE} = Two, Three", ["One", "Two", "Three"]),
			("#client{name=Name} = Client", ["Client"]),
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.split_params(fixtures[f][0]), fixtures[f][1])

	def test_generate_params(self):
		fixtures = [
			(('start', '3'),"""
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, <<>>, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, {Abc, Cde}, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, <<Abc:16/binary, Cde/binary>>, Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc|R] = Two, Three) -> ok

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc|R], Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc, R], Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, Two, Three, Four) -> ok.
							start(One, {Abc, Cde} = Two, Three) -> ok;
							start(One, <<>>, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 3)),
			(('start', '0'),"""
							-spec start() -> ok.
							start() -> ok;
							""", ("() $1", 3)),
			(('start', '1'),"""
							start(#client{name=Name} = Client) -> ok.

							""", ("(${1:Client}) $2", 2)),
			(('start', '2'),"""
							start(Usr, Opts) when is_binary(Usr), is_list(Opts) -> ok.

							""", ("(${1:Usr}, ${2:Opts}) $3", 2)),
			(('start', '1'),"""
							start( << _:3/bytes,Body/binary >> = Data) -> ok.

							""", ("(${1:Data}) $2", 2)),
			(('start', '2'),"""
							start(Usr, Opts) when is_binary(Usr), is_list(Opts) -> ok.

							""", ("(${1:Usr}, ${2:Opts}) $3", 2)),
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.generate_params(fixtures[f][0], fixtures[f][1]), fixtures[f][2])

	def test_get_completions(self):
		fixtures = [
			("""
			-export([zero/0, one/1, two/2, three/3, four/4]).

			zero() -> ok.
			one(One) -> ok.
			two(Two1, Two2) -> ok.
			three(Three1, Three2, Three3) -> ok.
			four(Four1, <<>>, Four3, Four4) -> ok;
			four(Four1, {Four2A, Four2B, <<>>} = Four2, Four3, Four4) -> ok;
			""",
			([
				('zero/0', 'zero() $1'),
				('one/1', 'one(${1:One}) $2'),
				('two/2', 'two(${1:Two1}, ${2:Two2}) $3'),
				('three/3', 'three(${1:Three1}, ${2:Three2}, ${3:Three3}) $4'),
				('four/4', 'four(${1:Four1}, ${2:Four2}, ${3:Four3}, ${4:Four4}) $5')
			], [4, 5, 6, 7, 8])),

			("""
			-export([zero/0]).
			-export([one/1, two/2, three/3, four/4]).

			zero() -> three(Three1wrong, Three2wrong, Three3wrong).
			one(One) -> ok.
			two(Two1, Two2) -> ok.
			-spec three(ThreeParam1::list(), ThreeParam2::list(), ThreeParam3::atom()) -> ok.
			three(Three1, Three2, Three3) -> ok.
			four(Four1, <<>>, Four3, Four4) -> ok;
			four(Four1, {Four2A, Four2B, <<>>} = Four2, Four3, Four4) -> ok;
			""",
			([
				('zero/0', 'zero() $1'),
				('one/1', 'one(${1:One}) $2'),
				('two/2', 'two(${1:Two1}, ${2:Two2}) $3'),
				('three/3', 'three(${1:ThreeParam1}, ${2:ThreeParam2}, ${3:ThreeParam3}) $4'),
				('four/4', 'four(${1:Four1}, ${2:Four2}, ${3:Four3}, ${4:Four4}) $5')
			], [5, 6, 7, 9, 10]))
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.get_completions(fixtures[f][0]), fixtures[f][1])


if __name__ == '__main__':
	if (len(sys.argv) == 2):
		if sys.argv[1] == 'test':
			sys.argv = [sys.argv[0]]
			unittest.main()

	elif (len(sys.argv) == 3):
		starting_dir = sys.argv[1]
		dest_file_base = sys.argv[2]
		parser = SublimErlLibParser()
		parser.generate_completions(starting_dir, dest_file_base)


########NEW FILE########
