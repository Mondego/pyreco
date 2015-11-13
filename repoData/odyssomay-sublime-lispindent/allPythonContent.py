__FILENAME__ = commands
import re
import sublime, sublime_plugin
try:
	import indent
except:
	from lispindent import indent

def indent_line(edit, view, line, options):
	line_str = view.substr(line)
	current_indent = indent.current_indent(line_str)
	new_indent = indent.indent(view, line.begin(), options)
	if not current_indent == new_indent:
		view.replace(edit,
		   sublime.Region(line.begin(),
		                  line.begin() + current_indent),
		   " " * new_indent)

def indent_selection(edit, view, idx, options):
	total = len(view.lines(view.sel()[idx]))

	for i in range(total):
		line = view.lines(view.sel()[idx])[i]
		indent_line(edit, view, line, options)

def indent_selections(edit, view, options):
	total = len(view.sel())

	for i in range(total):
		indent_selection(edit, view, i, options)

def insert_newline_and_indent(edit, view, options):
	total = len(view.sel())
	out = []

	for i in range(total):
		region = view.sel()[i]
		view.erase(edit, region)
		idx = region.begin()
		out += [sublime.Region(idx, idx)]

	sel = view.sel()
	sel.clear()
	for region in out: sel.add(region)

	for i in range(total):
		idx = view.sel()[i].begin()
		view.insert(edit, idx,
			"\n" + indent.get_indent_str(view, idx, options))
			
	view.show(sel)

###############################
## View file type + regexps

views = {}
filetypes = []
options = {}

def get_lisp_file_type(view):
	for (language, regex, syntax) in filetypes:
		view_syntax = view.settings().get('syntax')
		syntax_matches = syntax and view_syntax.endswith(syntax)
		file_name = view.file_name()
		filename_matches = file_name and regex.match(file_name)
		if filename_matches or syntax_matches:
			return language

def get_view_file_type(view):
	vwid = view.id()
	if vwid in views: return views[vwid]

def get_view_options(view):
	ft = get_view_file_type(view)
	if ft and (ft in options):
		return options[ft]

def should_use_lisp_indent(view):
	# Fix for SublimeREPL
	# Necessary because lispindent activates on syntax.
	if view.settings().get("repl"):
		return False
	return view.id() in views

def test_view(view):
	vwid = view.id()
	if not vwid in views:
		file_type = get_lisp_file_type(view)
		if file_type: views[vwid] = file_type

def test_current_view():
	win = sublime.active_window()
	if win:
		view = win.active_view()
		test_view(view)

def join_regex(regex):
	if isinstance(regex, str):
		return regex
	else:
		out = ""
		for part in regex: out += part
		return out

settings = None
def reload_languages():
	l = settings.get("languages")
	for language, opts in l.items():
		regex = join_regex(opts["regex"])
		compiled = {
			"detect": re.compile(opts["detect"]),
			"default_indent": opts["default_indent"],
			"regex": re.compile(regex)
		}
		filetypes.append((language, compiled["detect"], opts.get("syntax", None)))
		options[language] = compiled

reload_has_init = False
def init_env():
	global reload_has_init
	global settings
	if not reload_has_init:
		settings = sublime.load_settings("lispindent.sublime-settings")
		settings.add_on_change("languages", reload_languages)
		reload_languages()
		reload_has_init = True
		test_current_view()

###############################
## Commands

class LispindentCommand(sublime_plugin.TextCommand):  
	def run(self, edit):
		init_env()
		view = self.view
		test_view(view)
		if should_use_lisp_indent(view):
			indent_selections(edit, view, get_view_options(view))
		else:
			view.run_command("reindent")

class LispindentinsertnewlineCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		init_env()
		view = self.view
		test_view(view)
		if should_use_lisp_indent(view):
			insert_newline_and_indent(edit, view, get_view_options(view))
		else:
			view.run_command("insert", {"characters": "\n"})

class LispIndentListenerCommand(sublime_plugin.EventListener):
	def on_query_context(self, view, key, operator, operand, match_all):
		if key == "shoulduselispindent":
			init_env()
			test_view(view)
			return should_use_lisp_indent(view)

####
#### Override
def listen_to_syntax_change(view):
	def on_syntax_change():
		# this should "reload the view"
		pass

	view.settings().add_on_change("syntax", on_syntax_change)

class ViewOverrideRunNNNNNNNNNNNNNNNNNNNNNNCommand(sublime_plugin.TextCommand):
	def __init__(this, view):
		old_run_command = getattr(view, "run_command")

		def new_run_command(name, args={}):
			if name == "reindent":
				init_env()
				test_view(view)
				if should_use_lisp_indent(view):
					old_run_command("lispindent")
				else:
					old_run_command("reindent")
			else:
				old_run_command(name, args)

		setattr(view, "run_command", new_run_command)

		listen_to_syntax_change(view)

	def run(this, edit):
		pass

########NEW FILE########
__FILENAME__ = indent
import sublime, sublime_plugin
import re

####
#### Get Line without comments & strings
def overlapping_regions(test_region, regions):
	out = []
	for region in regions:
		if region.intersects(test_region):
			out += [region]

	return out

no_whitespace_matcher = re.compile("[^\s]")
def remove_overlapping_regions(string, region, regions):
	for r in regions:
		b = max(r.begin(), region.begin()) - region.begin()
		e = min(r.end(), region.end()) - region.begin()
		replacement = no_whitespace_matcher.sub("_", string[b:e])
		string = string[:b] + replacement + string[e:]

	return string

def get_string_for_region(view, region):
	comments = overlapping_regions(
		region, view.find_by_selector("comment"))
	strings = overlapping_regions(
		region, view.find_by_selector("string"))

	line_str = view.substr(region)
	line_str = remove_overlapping_regions(line_str, region, strings)
	line_str = remove_overlapping_regions(line_str, region, comments)

	return line_str

####
#### String detection
def is_point_inside_regions(point, regions):
	for region in regions:
		if point > region.begin() and point < region.end():
			return region

	return False

def is_inside_string(view, point):
	test_region = sublime.Region(point, point)
	regions = view.find_by_selector("string")
	return is_point_inside_regions(point, regions)

####
#### Indenting
indent_matcher = re.compile("^[ \t]*")
def current_indent(s):
	return len(indent_matcher.match(s).group(0))

operator_split_matcher = re.compile("[ \[\]\(\)\{\}]")
def get_operator(line_str, idx):
	operator_str = line_str[idx + 1:]
	return operator_split_matcher.split(operator_str)[0]

def bracket_indent(idx):      return idx + 1
def two_space_indent(idx):    return idx + 2
def operator_indent(op, idx): return idx + len(op) + 2

whitespace_matcher = re.compile("\s*$")
def parentheses_indent(line_str, idx, options):
	op = get_operator(line_str, idx)
	
	if op == "": return bracket_indent(idx)
	elif whitespace_matcher.match(line_str[idx + len(op) + 1:]):
		return two_space_indent(idx)

	is_match = options['regex'].match(op)
	if options["default_indent"] == "two_space":
		if is_match: return operator_indent(op, idx)
		else:        return two_space_indent(idx)
	else:
		if is_match: return two_space_indent(idx)
		else:        return operator_indent(op, idx)
	return idx + 2

def update_counts(counts, char):
	(pa, br, cbr) = counts
	if char == '(': pa += 1
	elif char == ')': pa -= 1
	elif char == '[': br += 1
	elif char == ']': br -= 1
	elif char == '{': cbr += 1
	elif char == '}': cbr -= 1
	return (pa, br, cbr)

def indent(view, idx, options):
	str_region = is_inside_string(view, idx)
	if str_region:
		b = str_region.begin()
		return b - view.line(b).begin()

	lines = reversed(view.split_by_newlines(sublime.Region(0, idx)))
	pa, br, cbr = 0, 0, 0

	for line in lines:
		line_str = get_string_for_region(view, line)
		for idx in range(len(line_str) - 1, -1, -1):
			c = line_str[idx]
			
			(pa, br, cbr) = update_counts((pa, br, cbr), c)
			if br > 0 or cbr > 0: return bracket_indent(idx)
			elif pa > 0:
				if idx > 0 and line_str[idx - 1] == "'":
					return bracket_indent(idx)
				else:
					return parentheses_indent(line_str, idx, options)
		if pa == 0 and br == 0 and cbr == 0:
			return current_indent(line_str)
	return 0

def get_indent_str(view, idx, options):
	return " " * indent(view, idx, options)
########NEW FILE########
