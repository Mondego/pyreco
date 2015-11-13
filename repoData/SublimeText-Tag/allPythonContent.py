__FILENAME__ = Edit
# edit.py
# buffer editing for both ST2 and ST3 that "just works"

import sublime
import sublime_plugin
from collections import defaultdict

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}

class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return self.args[0](view, edit)

        funcs = {
            'insert': view.insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            func(edit, *self.args)


class Edit:
    defer = defaultdict(dict)

    def __init__(self, view):
        self.view = view
        self.steps = []

    def step(self, cmd, *args):
        step = EditStep(cmd, *args)
        self.steps.append(step)

    def insert(self, point, string):
        self.step('insert', point, string)

    def erase(self, region):
        self.step('erase', region)

    def replace(self, region, string):
        self.step('replace', region, string)

    def callback(self, func):
        self.step('callback', func)

    def run(self, view, edit):
        for step in self.steps:
            step.run(view, edit)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        view = self.view
        if sublime.version().startswith('2'):
            edit = view.begin_edit()
            self.run(edit)
            view.end_edit(edit)
        else:
            key = str(hash(tuple(self.steps)))
            sublime.edit_storage[key] = self.run
            view.run_command('apply_edit', {'key': key})


class apply_edit(sublime_plugin.TextCommand):
    def run(self, edit, key):
        sublime.edit_storage.pop(key)(self.view, edit)
########NEW FILE########
__FILENAME__ = Tag
import re, sublime

class Tag():

	def __init__(self):

		Tag.regexp_is_valid								= re.compile("^[a-z0-9#\:\-_]+$", re.I);
		Tag.regexp_self_closing_optional 	= re.compile("^<?(\?xml|\!|area|base|br|col|frame|hr|img|input|link|meta|param|command|embed|source|/?li|/?p)[^a-z]", re.I);
		Tag.regexp_self_closing 					= re.compile("^<?(\?xml|\!|%|area|base|br|col|frame|hr|img|input|link|meta|param|command|embed|source)[^a-z]", re.I);
		Tag.regexp_self_closing_xml   		= re.compile("^<?(\?xml|\!)[^a-z]", re.I);
		Tag.regexp_is_closing 						= re.compile("^<?[^><]+/>", re.I);
		Tag.xml_files											= [item.lower() for item in ['xhtml', 'xml', 'rdf', 'xul', 'svg', 'xsd', 'xslt','tmTheme', 'tmPreferences', 'tmLanguage', 'sublime-snippet', 'opf', 'ncx']]

	def is_valid(self, content):
		return Tag.regexp_is_valid.match(content)

	def is_self_closing(self, content, return_optional_tags = True, is_xml= False):
		if return_optional_tags:
			if is_xml == False:
				return Tag.regexp_self_closing.match(content) or Tag.regexp_is_closing.match(content)
			else:
				return Tag.regexp_is_closing.match(content) or Tag.regexp_self_closing_xml.match(content)
		else:
			if is_xml == False:
				return Tag.regexp_self_closing_optional.match(content) or Tag.regexp_is_closing.match(content)
			else:
				return Tag.regexp_is_closing.match(content) or Tag.regexp_self_closing_xml.match(content)

	def name(self, content, return_optional_tags = True, is_xml = False):
		if content[:1] == '/' or  content[:2] == '\\/':
			tag_name = content.split('/')[1].split('>')[0].strip();
		else:
			tag_name = content.split(' ')[0].split('>')[0].strip();
		if self.is_valid(tag_name) and not self.is_self_closing(content, return_optional_tags, is_xml):
			return tag_name
		else:
			return ''

	def is_closing(self, content):
		if content[:1] == '/' or  content[:2] == '\\/' or Tag.regexp_is_closing.match(content):
			return True
		else:
			return False

	def view_is_xml(self, view):
		if view.settings().get('is_xml'):
			return True
		else:
			name = view.file_name()
			if not name:
				is_xml = '<?xml' in view.substr(sublime.Region(0, 50))
			else:
				name = ('name.'+name).split('.')
				name.reverse()
				name = name.pop(0).lower()
				is_xml = name in Tag.xml_files or '<?xml' in view.substr(sublime.Region(0, 50))
			view.settings().set('is_xml', is_xml)
			return is_xml

	def clean_html(self, content):

		# normalize
		content = content.replace('\r', '\n').replace('\t', ' ')

		# comments
		unparseable = content.split('<!--')
		content = unparseable.pop(0)
		l = len(unparseable)
		i = 0
		while i < l:
			tmp = unparseable[i].split('-->')
			content += '....'
			content += len(tmp.pop(0))*'.'
			content += '...'
			content += "...".join(tmp)
			i += 1

		# multiline line comments /* */
		if content.count('/*') == content.count('*/'):
			unparseable = content.split('/*')
			content = unparseable.pop(0)
			l = len(unparseable)
			i = 0
			while i < l:
				tmp = unparseable[i].split('*/')
				content += '..'
				content += len(tmp.pop(0))*'.'
				content += '..'
				content += "..".join(tmp)
				i += 1

		# one line comments //
		unparseable = re.split('(\s\/\/[^\n]+\n)', content)
		for comment in unparseable:
			if comment[:3] == '\n//' or comment[:3] == ' //':
				content = content.replace(comment, (len(comment))*'.')

		# one line comments #
		unparseable = re.split('(\s\#[^\n]+\n)', content)
		for comment in unparseable:
			if comment[:3] == '\n#' or comment[:3] == ' #':
				content = content.replace(comment, (len(comment))*'.')

		# script
		if content.count('<script') == content.count('</script'):
			unparseable = content.split('<script')
			content = unparseable.pop(0)
			l = len(unparseable)
			i = 0
			while i < l:
				tmp = unparseable[i].split('</script>')
				content += '.......'
				content += len(tmp.pop(0))*'.'
				content += '.........'
				content += ".........".join(tmp)
				i += 1

		# style
		if content.count('<style') == content.count('</style'):
			unparseable = content.split('<style')
			content = unparseable.pop(0)
			l = len(unparseable)
			i = 0
			while i < l:
				tmp = unparseable[i].split('</style>')
				content += '......'
				content += len(tmp.pop(0))*'.'
				content += '........'
				content += "........".join(tmp)
				i += 1

		# here-doc
		while '<<<' in content:
			content = content.replace('<<<', '...')
		while '<<' in content:
			content = content.replace('<<', '..')

		return content

########NEW FILE########
__FILENAME__ = tag_close_tag
import sublime, sublime_plugin
from Tag import Tag

Tag = Tag.Tag()

class TagCloseTagCommand(sublime_plugin.TextCommand):

	def run(self, edit):

		view = self.view
		is_xml = Tag.view_is_xml(view);

		closed_some_tag = False
		new_selections = []
		new_selections_insert = []

		for region in view.sel():
			cursorPosition = region.begin()

			tag = self.close_tag(view.substr(sublime.Region(0, cursorPosition)), is_xml)

			if tag and tag != '</':
				if region.empty():
					replace = False
					view.insert(edit, cursorPosition, tag);
				else:
					replace = True
					view.replace(edit, sublime.Region(region.begin(), region.end()), '');
					view.insert(edit, cursorPosition, tag);
				if tag != '</':
					closed_some_tag = True
					if replace:
						new_selections_insert.append(sublime.Region(region.begin()+len(tag), region.begin()+len(tag)))
					else:
						new_selections_insert.append(sublime.Region(region.end()+len(tag), region.end()+len(tag)))
				else:
					new_selections.append(sublime.Region(region.end()+len(tag), region.end()+len(tag)))
			else:
				new_selections.append(sublime.Region(region.end(), region.end()))

		view.sel().clear()

		# we inserted the "</tagname" part.
		# running the command "insert" with parameter ">" to allow
		# to the application indent these tags correctly
		if closed_some_tag:
			view.run_command('hide_auto_complete')
			for sel in new_selections_insert:
				view.sel().add(sel)
			view.run_command('insert',  {"characters": ">"})
			view.run_command('reindent',  {"force_indent": False})

		for sel in new_selections:
			view.sel().add(sel)

	def close_tag(self, data, is_xml):

		data = Tag.clean_html(data).split('<')
		data.reverse()

		try:
			i = 0
			lenght = len(data)-1
			while i < lenght:
				tag = Tag.name(data[i], True, is_xml)
				# if opening tag, close the tag
				if tag:
					if not Tag.is_closing(data[i]):
						return '</'+Tag.name(data[i], True, is_xml)+''
					# if closing tag, jump to opening tag
					else:
						i = i+1
						skip = 0
						while i < lenght:
							if Tag.name(data[i], True, is_xml) == tag:
								if not Tag.is_closing(data[i]):
									if skip == 0:
										break
									else:
										skip = skip-1
								else:
									skip = skip+1
							i = i+1
				i = i+1
			return ''
		except:
			return '';
########NEW FILE########
__FILENAME__ = tag_close_tag_on_slash
import sublime, sublime_plugin
from Tag import Tag

Tag = Tag.Tag()
def plugin_loaded():
	global s
	s = sublime.load_settings('Tag Package.sublime-settings')

class TagCloseTagOnSlashCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		if s.get('enable_close_tag_on_slash') == False:
			self.view.run_command('insert',  {"characters": "/"})
			return

		view = self.view
		is_xml = Tag.view_is_xml(view)

		closed_some_tag = False
		new_selections = []
		new_selections_insert = []

		for region in view.sel():
			cursorPosition = region.begin()
			previousCharacter = view.substr(sublime.Region(cursorPosition - 1, cursorPosition))

			if '<' == previousCharacter:
				tag = self.close_tag(view.substr(sublime.Region(0, cursorPosition)), is_xml)
				if region.empty():
					replace = False
					view.insert(edit, cursorPosition, tag);
				else:
					replace = True
					view.replace(edit, sublime.Region(region.begin(), region.end()), '');
					view.insert(edit, cursorPosition, tag);
				if tag != '/':
					closed_some_tag = True
					if replace:
						new_selections_insert.append(sublime.Region(region.begin()+len(tag), region.begin()+len(tag)))
					else:
						new_selections_insert.append(sublime.Region(region.end()+len(tag), region.end()+len(tag)))
				else:
					new_selections.append(sublime.Region(region.end()+len(tag), region.end()+len(tag)))
			else:
				if region.empty():
					view.insert(edit, cursorPosition, '/');
				else:
					view.replace(edit, sublime.Region(region.begin(), region.end()), '/');
				new_selections.append(sublime.Region(region.end(), region.end()))

		view.sel().clear()

		# we inserted the "</tagname" part.
		# running the command "insert" with parameter ">" to allow
		# to the application indent these tags correctly
		if closed_some_tag:
			view.run_command('hide_auto_complete')
			for sel in new_selections_insert:
				view.sel().add(sel)
			view.run_command('insert',  {"characters": ">"})
			view.run_command('reindent',  {"force_indent": False})

		for sel in new_selections:
			view.sel().add(sel)

	def close_tag(self, data, is_xml):

		data = Tag.clean_html(data).split('<')
		data.reverse()
		data.pop(0);

		try:
			i = 0
			lenght = len(data)-1
			while i < lenght:
				tag = Tag.name(data[i], True, is_xml)
				# if opening tag, close the tag
				if tag and not Tag.is_closing(data[i]):
					return '/'+Tag.name(data[i], True, is_xml)+''
				# if closing tag, jump to opening tag
				else:
					if tag:
						i = i+1
						skip = 0
						while i < lenght:
							if Tag.name(data[i], True, is_xml) == tag:
								if not Tag.is_closing(data[i]):
									if skip == 0:
										break
									else:
										skip = skip-1
								else:
									skip = skip+1
							i = i+1
				i = i+1
			return '/'
		except:
			return '/';
########NEW FILE########
__FILENAME__ = tag_indent
import sublime, sublime_plugin
import re

# to find on which indentation level we currently are
current_indentation_re = re.compile("^\s*")

# to leave additional new lines as is
aditional_new_lines_re = re.compile("^\s*\n+\s*\n+\s*$")

# no indentation
no_indent = re.compile("^</?(head|body)[>| ]", re.I)

# possible self closing tags:      XML-------HTML------------------------------------------------HTML5----------------
self_closing_tags = re.compile("^<(\?|\!|%|#|area|base|br|col|frame|hr|img|input|link|meta|param|command|embed|source)", re.I)

skip_content_of_this_tags_re = re.compile("^<(script|style|pre|code)(>| )", re.I)

trim_outter_left  = "abbr|acronym|dfn|em|strong|b|i|u|font|del|ins|sub|sup".split('|')
trim_outter_right = "".split('|')

trim_inner_left   = "abbr|acronym|dfn|em|strong|b|i|u|font|del|ins|sub|sup|title".split('|')
trim_inner_right  = "abbr|acronym|dfn|em|strong|b|i|u|font|del|ins|sub|sup|title".split('|')

def TagIndentBlock(data, view):

		# User settings
		settings = sublime.load_settings('Tag Package.sublime-settings')

		preserve_additional_new_lines = bool(settings.get('preserve_additional_new_lines', True))
		num_chars_considered_little_content = str(int(settings.get('little_content_means_this_number_of_characters', 60)))

		# the indent character
		if view.settings().get('translate_tabs_to_spaces') :
			indent_character = ' '*int(view.settings().get('tab_size', 4))
		else:
			indent_character = '\t'

		# on which indentation level we currently are?
		indentation_level = (current_indentation_re.search(data).group(0)).split("\n")
		current_indentation = indentation_level.pop()
		if len(indentation_level) == 1:
			beauty = "\n"+indentation_level[0]
		elif len(indentation_level) > 1:
			beauty = "\n".join(indentation_level)
		else:
			beauty = ''

		# pre processing
		if preserve_additional_new_lines == False:
			#fix comments
			data = re.sub(r'(\n\s*<\!--)', '\n\t\n\\1', data)

		# first newline should be skipped
		starting = True

		# inspiration from http://jyro.blogspot.com/2009/08/makeshift-xml-beautifier-in-python.html
		level = 0
		tags = re.split('(<[^>]+>)',data)
		lenght = len(tags)
		i = 0
		while i < lenght:
			f = tags[i]
			no_indent_match  = no_indent.match(f[:20])

			if f.strip() == '':
				if preserve_additional_new_lines and aditional_new_lines_re.match(f):
					beauty += '\n'
			elif f[0]=='<' and f[1] != '/':
				#	beauty += '1'
				if starting == False:
					beauty += '\n'
				starting = False
				beauty += current_indentation
				if not no_indent_match:
					beauty += indent_character*level
				if skip_content_of_this_tags_re.match(f[:20]):
					tag_is = re.sub(r'<([^ ]+)(>| ).*', '\\1', f[:20], 1)
					tag_is = re.compile("/"+tag_is+">$", re.I)
					beauty += f
					i = i+1
					while i < lenght:
						f = tags[i]
						if not tag_is.search(f[-20:]):
							beauty += f
							i = i+1
						else:
							beauty += f
							break
				else:
					beauty += f.strip()
					if not no_indent_match:
						level = level + 1
				#self closing tag
				if f[-2:] == '/>' or self_closing_tags.match(f):
					#beauty += '2'
					beauty += current_indentation
					if not no_indent_match:
						level = level - 1
			elif f[:2]=='</' or  f[:3]=='<\\/':
				if not no_indent_match:
					level = level - 1
				#beauty += '3'
				if starting == False:
					beauty += '\n'
				starting = False
				beauty += current_indentation
				if not no_indent_match:
					beauty += indent_character*level
				beauty += f.strip()
			else:
				#beauty += '4'
				if starting == False:
					beauty += '\n'
				starting = False
				beauty += current_indentation
				if not no_indent_match:
					beauty += indent_character*level
				beauty += f.strip()
			i = i+1

		if bool(settings.get('empty_tags_close_on_same_line', True)):
			# put empty tags on same line
			beauty = re.sub(r'<([^/!][^>]*[^/])>\s+</', '<\\1></', beauty)
			# put empty tags on same line for tags with one character
			beauty = re.sub(r'<([^/!])>\s+</', '<\\1></', beauty)

		if bool(settings.get('tags_with_little_content_on_same_line', True)):
			# put tags with little content on same line
			beauty = re.sub(r'<([^/][^>]*[^/])>\s*([^<\t\n]{1,'+num_chars_considered_little_content+'})\s*</', '<\\1>\\2</', beauty)
			# put tags with little content on same line for tags with one character
			beauty = re.sub(r'<([^/])>\s*([^<\t\n]{1,'+num_chars_considered_little_content+'})\s*</', '<\\1>\\2</', beauty)

		for tag in trim_outter_left:
			beauty = re.sub(r'\s+<'+tag+'(>| )', ' <'+tag+'\\1', beauty, re.I)
		for tag in trim_outter_right:
			beauty = re.sub(r'</'+tag+'>\s+([^\s])', '</'+tag+'> \\1', beauty, re.I)

		for tag in trim_inner_left:
			beauty = re.sub(r'<'+tag+'(>| [^>]*>)\s+([^\s])', '<'+tag+'\\1\\2', beauty, re.I)
		for tag in trim_inner_right:
			beauty = re.sub(r'\s+</'+tag+'>', '</'+tag+'> ', beauty, re.I)

		return beauty

class TagIndentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		for region in self.view.sel():
			if region.empty():
				continue
			if self.view.score_selector(region.a, 'text.html | text.xml') <= 0:
				dataRegion = region
			else:
				dataRegion = sublime.Region(self.view.line(region.begin()).begin(), region.end())
			data = TagIndentBlock(self.view.substr(dataRegion), self.view)
			self.view.replace(edit, dataRegion, data);

	def is_visible(self):
		for region in self.view.sel():
			if not region.empty():
				return True
		return False

class TagIndentDocumentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		dataRegion = sublime.Region(0, self.view.size())
		data = TagIndentBlock(self.view.substr(dataRegion).strip(), self.view)
		self.view.replace(edit, dataRegion, data);

	def is_visible(self):
		value = False
		for region in self.view.sel():
			if region.empty():
				continue
			if self.view.score_selector(region.a, 'text.html | text.xml') <= 0:
				return False
			else:
				value = True
		return value or self.view.score_selector(0, 'text.html | text.xml') > 0
########NEW FILE########
__FILENAME__ = tag_insert_as_tag
import sublime, sublime_plugin, re
from Tag import Tag

Tag = Tag.Tag()

class TagInsertAsTagCommand(sublime_plugin.TextCommand):

	def run(self, edit):
		view = self.view
		new_selections = []
		for region in view.sel():
			source = view.substr(region)
			if not source.strip():
				region = view.word(region)
				source = view.substr(region)
			if not source.strip():
				new_selections.append(sublime.Region(region.a, region.b))
				pass
			else:
				if re.match("^\s", source):
					view.replace(edit, region, '<p>'+source+'</p>')
					new_selections.append(sublime.Region(region.end()+3, region.end()+3))
				elif Tag.is_self_closing(source):
					view.replace(edit, region, '<'+source+'/>')
					new_selections.append(sublime.Region(region.end()+3, region.end()+3))
				else:
					tag = source.split('\r')[0].split('\n')[0].split(' ')[0]
					if tag and Tag.is_valid(tag) and tag != '<' and tag != '</' and tag != '>':
						view.replace(edit, region, '<'+source+'></'+tag+'>')
						new_selections.append(sublime.Region(region.end()+2, region.end()+2))
					else:
						new_selections.append(sublime.Region(region.end(), region.end()))

		view.sel().clear()
		for sel in new_selections:
			view.sel().add(sel)
########NEW FILE########
__FILENAME__ = tag_lint
import sublime, sublime_plugin
from time import time, sleep
import threading
import _thread as thread
from Tag import Tag
import re

Tag = Tag.Tag()
def plugin_loaded():
	global s, Pref, tag_lint, tag_lint_run
	s = sublime.load_settings('Tag Package.sublime-settings')
	Pref = Pref();
	Pref.load()
	s.add_on_change('reload', lambda:Pref.load())
	tag_lint = TagLint();
	tag_lint_run = tag_lint.run
	if not 'running_tag_lint_loop' in globals():
		global running_tag_lint_loop
		running_tag_lint_loop = True
		thread.start_new_thread(tag_lint_loop, ())

class Pref:
	def load(self):
		Pref.view              				              = False
		Pref.modified          				              = False
		Pref.elapsed_time      				              = 0.4
		Pref.time	      							              = time()
		Pref.wait_time	      				              = 0.8
		Pref.running           				              = False
		Pref.enable_live_tag_linting 	              = s.get('enable_live_tag_linting', True)
		Pref.hard_highlight						              = ['', 'html', 'htm', 'php', 'tpl', 'md', 'txt']
		Pref.enable_live_tag_linting_document_types	= [item.lower() for item in s.get('enable_live_tag_linting_document_types', '')]
		Pref.statuses									              = 0
		Pref.message_line							              = -1
		Pref.selection_last_line			              = -1
		Pref.message							                  = ''
		Pref.view_size							                = 0

class TagLint(sublime_plugin.EventListener):

	def on_activated(self, view):
		if not view.settings().get('is_widget') and not view.is_scratch():
			Pref.view = view
			Pref.selection_last_line = -1

	def on_load(self, view):
		if not view.settings().get('is_widget') and not view.is_scratch():
			Pref.modified = True
			Pref.view = view
			sublime.set_timeout(lambda:self.run(True), 0)

	def on_modified(self, view):
		if not view.settings().get('is_widget') and not view.is_scratch():
			Pref.modified = True
			Pref.time = time()

	def on_selection_modified(self, view):
		if Pref.enable_live_tag_linting:
			sel = view.sel()
			if sel and Pref.message_line != -1 and Pref.message != '':
				line = view.rowcol(sel[0].end())[0]
				if Pref.selection_last_line != line:
					Pref.selection_last_line = line
					if line == Pref.message_line:
						view.set_status('TagLint', Pref.message)
					else:
						Pref.statuses += 1
						sublime.set_timeout(lambda:self.clear_status(view, False), 7000);
						#view.erase_status('TagLint')
			# else:
			# 	view.erase_status('TagLint')

	def on_close(self, view):
		Pref.view = False
		Pref.modified = True

	def guess_view(self):
		if sublime.active_window() and sublime.active_window().active_view():
			Pref.view = sublime.active_window().active_view()

	def run(self, asap = False, from_command = False):
		now = time()
		if asap == False and (now - Pref.time < Pref.wait_time):
			return
		if (Pref.enable_live_tag_linting or from_command) and Pref.modified and not Pref.running:
			Pref.modified = False
			if from_command:
				Pref.view = sublime.active_window().active_view()
			if Pref.view:
				view = Pref.view
				Pref.view_size = view.size()
				if Pref.view_size > 10485760:
					return
				if Pref.view.settings().get('is_widget') or Pref.view.is_scratch():
					return
				file_ext = ('name.'+(view.file_name() or '')).split('.')
				file_ext.reverse()
				file_ext = file_ext.pop(0).lower()
				if not from_command and file_ext not in Pref.enable_live_tag_linting_document_types:
					return
				Pref.running = True
				is_xml = Tag.view_is_xml(view)
				if from_command:
					if view.sel():
						region = view.sel()[0]
						if region.empty():
							region = sublime.Region(0, view.size())
					else:
						region = sublime.Region(0, view.size())
				else:
					region = sublime.Region(0, view.size())
				original_position = region.begin()
				content = view.substr(region)
				TagLintThread(view, content, original_position, is_xml, from_command).start()
			else:
				self.guess_view()

	def display(self, view, message, invalid_tag_located_at, from_command):
		if view is not None:
			view.erase_regions("TagLint")
			if invalid_tag_located_at > -1:
				invalid_tag_located_at_start = invalid_tag_located_at
				invalid_tag_located_at_end   = invalid_tag_located_at+1
				size = view.size()
				while invalid_tag_located_at_end < size:
					end = view.substr(sublime.Region(invalid_tag_located_at_end, invalid_tag_located_at_end+1))
					if end == '>':
						invalid_tag_located_at_end += 1
						break
					elif end == '<':
						break;
					invalid_tag_located_at_end += 1
					if invalid_tag_located_at_start - invalid_tag_located_at_end > 100:
						break
				region = sublime.Region(invalid_tag_located_at_start, invalid_tag_located_at_end)
				line, col = view.rowcol(region.a);
				view.add_regions("TagLint", [region], 'variable.parameter', 'dot', sublime.PERSISTENT | sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED)
				Pref.message_line = line
				Pref.message = message
				view.set_status('TagLint', Pref.message+' in Line '+str(Pref.message_line+1)+' ')
				Pref.statuses += 1
				sublime.set_timeout(lambda:self.clear_status(view, from_command), 7000);
				if from_command:
					view.show_at_center(region)
			else:
				Pref.message_line = -1
				Pref.message = ''
				if from_command:
					view.set_status('TagLint', 'No errors found')
					Pref.statuses += 1
					sublime.set_timeout(lambda:self.clear_status(view, from_command), 7000);
				else:
					view.erase_status('TagLint')
		else:
			Pref.message_line = -1
			Pref.message = ''
		Pref.running = False

	def clear_status(self, view, from_command):
		Pref.statuses -= 1
		if view is not None and Pref.statuses == 0:
			view.erase_status('TagLint')
			if from_command and Pref.enable_live_tag_linting == False:
				view.erase_regions("TagLint")



class TagLintThread(threading.Thread):

	def __init__(self, view, content, original_position, is_xml, from_command):
		threading.Thread.__init__(self)
		self.view              = view
		self.content           = content
		self.original_position = original_position
		self.is_xml            = is_xml
		self.message           = ''
		self.invalid_tag_located_at = -1
		self.from_command 		 = from_command

	def run(self):

		begin = time()

		content           = self.content
		original_position = self.original_position
		is_xml            = self.is_xml

		# remove unparseable content

		content = Tag.clean_html(content)

		# linting: opening tags

		data = content.split('<')

		position = original_position+len(data.pop(0))

		invalid_tag_located_at = -1

		i = 0
		lenght = len(data)
		first_at = 0
		while i < lenght:
			tag = Tag.name(data[i], False, is_xml)
			if tag and tag != 'html' and tag != 'body' and tag != 'head':
				# if opening tag, then check if closing tag exists
				if not Tag.is_closing(data[i]):
					# print tag+' is opening '
					if first_at == 0:
						first_at = position
					a = i+1
					skip = 0
					while a < lenght:
						inner_tag_name    = Tag.name(data[a], False, is_xml)
						# check if same tag was found
						if inner_tag_name and inner_tag_name == tag:
							# check if tag is closing
							if Tag.is_closing(data[a]):
								if skip == 0:
									break
								else:
									skip = skip-1
							else:
								skip = skip+1
						a = a+1
					if a >= lenght:
						self.message = '"'+tag+'" tag is not closing'
						invalid_tag_located_at = position
						break
			position += len(data[i])+1
			i = i+1

		# linting: closing tags

		if invalid_tag_located_at == -1:

			position = original_position+len(content);

			data = content.split('<')
			data.reverse()

			i = 0
			lenght = len(data)-1
			while i < lenght:
				tag = Tag.name(data[i], False, is_xml)
				if tag and tag != 'html' and tag != 'body' and tag != 'head':
					# if closing tag, check if opening tag exists
					if Tag.is_closing(data[i]):
						# print tag+' is closing '
						a = i+1
						skip = 0
						while a < lenght:
							inner_tag_name    = Tag.name(data[a], False, is_xml)
							if inner_tag_name and inner_tag_name == tag:
								# check if tag is opening
								if not Tag.is_closing(data[a]):
									if skip == 0:
										break
									else:
										skip = skip-1
								else:
									skip = skip+1
							a = a+1
						if a >= lenght:
							self.message = '"'+tag+'" tag is not opening'
							invalid_tag_located_at = position-(len(data[i])+1)
							if invalid_tag_located_at < first_at:
								invalid_tag_located_at = -1
							break
				position -= len(data[i])+1
				i = i+1

		elapsed_time = time() - begin;

		# print 'Benchmark: '+str(elapsed_time)

		self.invalid_tag_located_at = invalid_tag_located_at

		sublime.set_timeout(lambda:tag_lint.display(self.view, self.message, self.invalid_tag_located_at, self.from_command), 0)



def tag_lint_loop():
	while True:
		# sleep time is adaptive, if takes more than 0.4 to calculate the word count
		# sleep_time becomes elapsed_time*3
		if Pref.running == False:
			sublime.set_timeout(lambda:tag_lint_run(), 0)
		sleep((Pref.elapsed_time*3 if Pref.elapsed_time > 0.4 else 0.4))




class TagLintCommand(sublime_plugin.WindowCommand):
	def run(self):
		Pref.modified = True
		Pref.running = False
		tag_lint_run(True, True);
########NEW FILE########
__FILENAME__ = tag_remove
import sublime, sublime_plugin
import re
from .Edit import Edit as Edit

def TagRemoveAll(data, view):
	return re.sub(r'<[^\?][^>]*>', '', data);

def TagRemoveSelected(data, tags, view):
	tags = tags.replace(',', ' ').replace(';', ' ').replace('|', ' ').replace('<', ' ').replace('>', ' ')+' '
	for tag in tags.split(' '):
		if tag:
			regexp = re.compile('<'+re.escape(tag)+'(| [^>]*)>', re.IGNORECASE)
			data = regexp.sub('', data);
			regexp = re.compile('</'+re.escape(tag)+'>', re.IGNORECASE)
			data = regexp.sub('', data);
	return data;

class TagRemoveAllInSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		for region in self.view.sel():
			if region.empty():
				continue
			dataRegion = sublime.Region(region.begin(), region.end())
			data = TagRemoveAll(self.view.substr(dataRegion), self.view)
			self.view.replace(edit, dataRegion, data);

class TagRemoveAllInDocumentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		dataRegion = sublime.Region(0, self.view.size())
		data = TagRemoveAll(self.view.substr(dataRegion), self.view)
		self.view.replace(edit, dataRegion, data);

class TagRemovePickedInSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit, tags = False):
		if not tags:
			import functools
			self.view.window().run_command('hide_panel');
			self.view.window().show_input_panel("Remove the following tags:", '', functools.partial(self.on_done, edit), None, None)
		else:
			self.on_done(edit, tags);

	def on_done(self, edit, tags):
		for region in self.view.sel():
			if region.empty():
				continue
			dataRegion = sublime.Region(region.begin(), region.end())
			data = TagRemoveSelected(self.view.substr(dataRegion), tags, self.view)
			with Edit(self.view) as edit:
				edit.replace(dataRegion, data);

class TagRemovePickedInDocumentCommand(sublime_plugin.TextCommand):
	def run(self, edit, tags = False):
		if not tags:
			import functools
			self.view.window().run_command('hide_panel');
			self.view.window().show_input_panel("Remove the following tags:", '', functools.partial(self.on_done, edit), None, None)
		else:
			self.on_done(edit, tags);

	def on_done(self, edit, tags):
		dataRegion = sublime.Region(0, self.view.size())
		data = TagRemoveSelected(self.view.substr(dataRegion), tags, self.view)
		with Edit(self.view) as edit:
			edit.replace(dataRegion, data);

########NEW FILE########
__FILENAME__ = tag_remove_attributes
import sublime, sublime_plugin
import re
from .Edit import Edit as Edit

def TagRemoveAttributesClean(data):
	regexp = re.compile('(<([a-z0-9\:\-_]+)\s+>)');
	data = regexp.sub('<\\2>', data);
	return data

def TagRemoveAttributesAll(data, view):
	return TagRemoveAttributesClean(re.sub('(<([a-z0-9\:\-_]+)\s+[^>]+>)', '<\\2>', data));

def TagRemoveAttributesSelected(data, attributes, view):
	attributes = attributes.replace(',', ' ').replace(';', ' ').replace('|', ' ')+' '
	for attribute in attributes.split(' '):
		if attribute:
			regexp = re.compile('(<([a-z0-9\:\-_]+\s+)([^>]*)\s*'+re.escape(attribute)+'="[^"]+"\s*([^>]*)>)')
			data = regexp.sub('<\\2\\3\\4>', data);
			data = TagRemoveAttributesClean(data);
	return data;

class TagRemoveAllAttributesInSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		for region in self.view.sel():
			if region.empty():
				continue
			dataRegion = sublime.Region(region.begin(), region.end())
			data = TagRemoveAttributesAll(self.view.substr(dataRegion), self.view)
			self.view.replace(edit, dataRegion, data);

class TagRemoveAllAttributesInDocumentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		dataRegion = sublime.Region(0, self.view.size())
		data = TagRemoveAttributesAll(self.view.substr(dataRegion), self.view)
		self.view.replace(edit, dataRegion, data);

class TagRemovePickedAttributesInSelectionCommand(sublime_plugin.TextCommand):
	def run(self, edit, attributes = False):
		if not attributes:
			import functools
			self.view.window().run_command('hide_panel');
			self.view.window().show_input_panel("Remove the following attributes:", '', functools.partial(self.on_done, edit), None, None)
		else:
			self.on_done(edit, attributes)

	def on_done(self, edit, attributes):
		for region in self.view.sel():
			if region.empty():
				continue
			dataRegion = sublime.Region(region.begin(), region.end())
			data = TagRemoveAttributesSelected(self.view.substr(dataRegion), attributes, self.view)
			with Edit(self.view) as edit:
				edit.replace(dataRegion, data);

class TagRemovePickedAttributesInDocumentCommand(sublime_plugin.TextCommand):
	def run(self, edit, attributes = False):
		if not attributes:
			import functools
			self.view.window().run_command('hide_panel');
			self.view.window().show_input_panel("Remove the following attributes:", '', functools.partial(self.on_done, edit), None, None)
		else:
			self.on_done(edit, attributes)

	def on_done(self, edit, attributes):
		dataRegion = sublime.Region(0, self.view.size())
		data = TagRemoveAttributesSelected(self.view.substr(dataRegion), attributes, self.view)
		with Edit(self.view) as edit:
			edit.replace(dataRegion, data);
########NEW FILE########
