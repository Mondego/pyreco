__FILENAME__ = OpenRSpecFile
import sublime
import sublime_plugin
import re, inspect, os
from RSpec import shared

class OpenRspecFileCommand(sublime_plugin.WindowCommand):

	def run(self):
		if not self.window.active_view():
			return

		self.views = []
		window = self.window
		current_file_path = self.window.active_view().file_name()

		if re.search(r"\w+\.rb$", current_file_path):

			current_file = re.search(r"([\w\.]+)$", current_file_path).group(1)
			base_name = re.search(r"(\w+)\.(\w+)$", current_file).group(1)
			base_name = re.sub('_spec', '', base_name)

			source_matcher = re.compile("[/\\\\]" + base_name + "\.rb$")
			test_matcher   = re.compile("[/\\\\]" + base_name + "_spec\.rb$")

			target_group = shared.other_group_in_pair(window)

			print("Current file: " + current_file)
			if  re.search(re.compile(base_name + "_spec\.rb$"), current_file):
				self.open_project_file(source_matcher, window, target_group)
			elif re.search(re.compile(base_name + "\.rb$"), current_file):
				self.open_project_file(test_matcher, window, target_group)
			else:
	 			print("Current file is not valid for RSpec switch file!")

	def open_project_file(self, file_matcher, window, group=-1):
		for root, dirs, files in os.walk(window.folders()[0]):
			for f in files:
				if re.search(r"\.rb$", f):
					cur_file = os.path.join(root, f)
					# print("Assessing: " + cur_file)
					if file_matcher.search(cur_file):
						file_view = window.open_file(os.path.join(root, f))
						if group >= 0: # don't set the view unless specified
							window.run_command('move_to_group', {'group': group})
						self.views.append(file_view)
						print("Opened: " + f)
						return
		print("No matching files!")

########NEW FILE########
__FILENAME__ = RSpecCreateModule
import sublime, sublime_plugin, time
import re
from RSpec import shared

_patterns = dict((k, re.compile('_*' + v)) for (k, v)
                    in dict(allcamel=r'(?:[A-Z]+[a-z0-9]*)+$',
                            trailingcamel=r'[a-z]+(?:[A-Z0-9]*[a-z0-9]*)+$',
                            underscores=r'(?:[a-z]+_*)+[a-z0-9]+$').items())

_caseTransition = re.compile('([A-Z][a-z]+)')

def translate(name, _from, to):
    leading_underscores = str()
    while name[0] == '_':
        leading_underscores += '_'
        name = name[1:]

    if _from in ('allcamel', 'trailingcamel'):
        words = _caseTransition.split(name)
    else:
        words = name.split('_')

    words = list(w for w in words if w is not None and 0 < len(w))

    camelize = lambda words: ''.join(w[0].upper() + w[1:] for w in words)

    v = dict(smushed=lambda: ''.join(words).lower(),
             allcamel=lambda: camelize(words),
             trailingcamel=lambda: words[0].lower() + camelize(words[1:]),
             underscores=lambda: '_'.join(words).lower())[to]()

    return leading_underscores + v


class RspecCreateModuleCommand(sublime_plugin.WindowCommand):
	def run(self):
		# self.view.insert(edit, 0, "Hello, World!")
		self.window.show_input_panel("Enter module name:", "", self.on_done, None, None)

	def on_done(self, text):

		# create the module
		module = self.window.new_file()
		module.set_syntax_file('Packages/Ruby/Ruby.tmLanguage')
		module.set_name(translate(text, 'allcamel', 'underscores') + '.rb')
		module_template = "\n\
class " + text + "\n\
end"
		edit = module.begin_edit()
		module.insert(edit, 0, module_template)
		module.end_edit(edit)

		# create the spec
		spec = self.window.new_file()
		self.window.run_command('move_to_group', {'group': shared.other_group_in_pair(self.window)})
		spec.set_syntax_file('Packages/Ruby/Ruby.tmLanguage')
		spec.set_name(translate(text, 'allcamel', 'underscores') + '_spec.rb')
		spec_template = "require 'spec_helper'\n\
require '" + translate(text, 'allcamel', 'underscores') + "'\n\n\
describe " + text + " do\n\
\tit \"should do something\"\n\
end"
		edit = spec.begin_edit()
		spec.insert(edit, 0, spec_template)
		spec.end_edit(edit)

		# try:
		# except ValueError:
		#     pass

########NEW FILE########
__FILENAME__ = RSpecDetectFileType
import sublime, sublime_plugin
import os

class RSpecDetectFileTypeCommand(sublime_plugin.EventListener):
	""" Detects current file type if the file's extension isn't conclusive """
	""" Modified for Ruby on Rails and Sublime Text 2 """
	""" Original pastie here: http://pastie.org/private/kz8gtts0cjcvkec0d4quqa """

	def on_load(self, view):
		filename = view.file_name()
		if not filename: # buffer has never been saved
			return

		name = os.path.basename(filename.lower())
		if name[-8:] == "_spec.rb":
			set_syntax(view, "RSpec", "RSpec")
		elif name == "factories.rb":
			set_syntax(view, "RSpec", "RSpec")
		# elif name == "gemfile":
		#   set_syntax(view, "Ruby on Rails", "Rails")
		# elif name[-2:] == "rb":
		#   set_syntax(view, "Ruby on Rails", "Rails")


def set_syntax(view, syntax, path=None):
	if path is None:
		path = syntax
	view.settings().set('syntax', 'Packages/'+ path + '/' + syntax + '.tmLanguage')
	print("Switched syntax to: " + syntax)
########NEW FILE########
__FILENAME__ = shared
"""Returns the neighbour focus group for the current window."""
def other_group_in_pair(window):
  if window.active_group() % 2 == 0:
    target_group = window.active_group()+1
  else:
    target_group = window.active_group()-1
  return min(target_group, window.num_groups()-1)

########NEW FILE########
