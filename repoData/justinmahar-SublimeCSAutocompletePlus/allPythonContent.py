__FILENAME__ = CoffeeAutocomplete
import sublime, sublime_plugin
import re
import os
import threading
from copy import copy

try:
	# Python 3
	from . import coffee_utils
	from .coffee_utils import debug
except (ValueError):
	# Python 2
	import coffee_utils
	from coffee_utils import debug

COFFEESCRIPT_AUTOCOMPLETE_STATUS_KEY = "coffee_autocomplete"
COFFEESCRIPT_AUTOCOMPLETE_STATUS_MESSAGE = "Coffee: Autocompleting \"%s\"..."

final_completions = []
status = {"working": False}

# TODO:
# - Type hinting using comments containing square brackets [Type] on same line or previous line
# - Codo docs searching for function parameter types
# - Better symbol parsing. Assignment lookups should consider the entire set of operands.
# X Consider all super classes (support extends)
# - Consider another feature: Override/implement methods
# - Full assignment traceback (that = this, a = b = c, knows what c is)
# - Check contents of currently open views
# - Built in types

class CoffeeAutocomplete(sublime_plugin.EventListener):

	def on_query_completions(self, view, prefix, locations):

		completions = copy(final_completions)
		working = status["working"]

		# If there is a word selection and we're looking at a coffee file...
		if not completions and coffee_utils.is_coffee_syntax(view) and not working:
			if not view.match_selector(locations[0], "source.coffee -comment"):
				return []

			status["working"] = True

			current_location = locations[0]

			# Get the window
			self.window = sublime.active_window()

			# http://www.sublimetext.com/forum/viewtopic.php?f=6&t=9076
			settings = sublime.load_settings(coffee_utils.SETTINGS_FILE_NAME)

			built_in_types_settings = sublime.load_settings(coffee_utils.BUILT_IN_TYPES_SETTINGS_FILE_NAME)
			built_in_types = built_in_types_settings.get(coffee_utils.BUILT_IN_TYPES_SETTINGS_KEY)
			if not built_in_types:
				built_in_types = []

			custom_types_settings = sublime.load_settings(coffee_utils.CUSTOM_TYPES_SETTINGS_FILE_NAME)
			custom_types = custom_types_settings.get(coffee_utils.CUSTOM_TYPES_SETTINGS_KEY)
			if not custom_types:
				custom_types = []

			built_in_types.extend(custom_types)

			# Pull the excluded dirs from preferences
			excluded_dirs = settings.get(coffee_utils.PREFERENCES_COFFEE_EXCLUDED_DIRS)
			if not excluded_dirs:
				excluded_dirs = []

			restricted_to_dirs = settings.get(coffee_utils.PREFERENCES_COFFEE_RESTRICTED_TO_PATHS)
			if not restricted_to_dirs:
				restricted_to_dirs = []

			# List of all project folders
			project_folder_list = self.window.folders()

			if restricted_to_dirs:
				specific_project_folders = []
				for next_restricted_dir in restricted_to_dirs:
					for next_project_folder in project_folder_list:
						next_specific_folder = os.path.normpath(os.path.join(next_project_folder, next_restricted_dir))
						specific_project_folders.append(next_specific_folder)
				project_folder_list = specific_project_folders

			function_return_types = settings.get(coffee_utils.FUNCTION_RETURN_TYPES_SETTINGS_KEY)
			if not function_return_types:
				function_return_types = []

			this_aliases = settings.get(coffee_utils.PREFERENCES_THIS_ALIASES)
			if not this_aliases:
				this_aliases = []

			member_exclusion_regexes = settings.get(coffee_utils.PREFERENCES_MEMBER_EXCLUSION_REGEXES)
			if not member_exclusion_regexes:
				member_exclusion_regexes = []

			# Lines for the current file in view
			current_file_lines = coffee_utils.get_view_content_lines(view)

			# TODO: Smarter previous word selection
			preceding_symbol = coffee_utils.get_preceding_symbol(view, prefix, locations)
			immediately_preceding_symbol = coffee_utils.get_preceding_symbol(view, "", locations)

			preceding_function_call = coffee_utils.get_preceding_function_call(view).strip()

			# Determine preceding token, if any (if a period was typed).
			token = coffee_utils.get_preceding_token(view).strip()

			# TODO: Smarter region location
			symbol_region = sublime.Region(locations[0] - len(prefix), locations[0] - len(prefix))

			if (preceding_function_call or token or coffee_utils.THIS_SUGAR_SYMBOL == preceding_symbol) and coffee_utils.is_autocomplete_trigger(immediately_preceding_symbol):
				self.window.active_view().run_command('hide_auto_complete')

				thread = CoffeeAutocompleteThread(project_folder_list, excluded_dirs, this_aliases, current_file_lines, preceding_symbol, prefix, preceding_function_call, function_return_types, token, symbol_region, built_in_types, member_exclusion_regexes)
				thread.start()
				self.check_operation(thread, final_completions, current_location, token, status)
			else: 
				status["working"] = False

		elif completions:
			self.clear_completions(final_completions)

		return completions

	def check_operation(self, thread, final_completions, current_location, token, status, previous_progress_indicator_tuple=None):

		if not thread.is_alive():
			if thread.completions:
				final_completions.extend(thread.completions)
				# Hide the default auto-complete and show ours
				self.window.active_view().run_command('hide_auto_complete')
				sublime.set_timeout(lambda: self.window.active_view().run_command('auto_complete'), 1)

			self.window.active_view().erase_status(COFFEESCRIPT_AUTOCOMPLETE_STATUS_KEY)
			status["working"] = False
		else:
			token = thread.token
			# Create the command's goto definition text, including the selected word. For the status bar.
			status_text = COFFEESCRIPT_AUTOCOMPLETE_STATUS_MESSAGE % token
			# Get a tuple containing the progress text, progress position, and progress direction.
			# This is used to animate a progress indicator in the status bar.
			current_progress_indicator_tuple = coffee_utils.get_progress_indicator_tuple(previous_progress_indicator_tuple)
			# Get the progress text
			progress_indicator_status_text = current_progress_indicator_tuple[0]
			# Set the status bar text so the user knows what's going on
			self.window.active_view().set_status(COFFEESCRIPT_AUTOCOMPLETE_STATUS_KEY, status_text + " " + progress_indicator_status_text)
			# Check again momentarily to see if the operation has completed.
			sublime.set_timeout(lambda: self.check_operation(thread, final_completions, current_location, token, status, current_progress_indicator_tuple), 100)

	def clear_completions(self, final_completions):
		debug("Clearing completions...")
		while len(final_completions) > 0:
			final_completions.pop()

class CoffeeAutocompleteThread(threading.Thread):

	def __init__(self, project_folder_list, excluded_dirs, this_aliases, current_file_lines, preceding_symbol, prefix, preceding_function_call, function_return_types, token, symbol_region, built_in_types, member_exclusion_regexes):
		
		self.project_folder_list = project_folder_list
		self.excluded_dirs = excluded_dirs
		self.this_aliases = this_aliases
		self.current_file_lines = current_file_lines
		self.preceding_symbol = preceding_symbol
		self.prefix = prefix
		self.preceding_function_call = preceding_function_call
		self.function_return_types = function_return_types
		self.token = token
		self.symbol_region = symbol_region
		self.built_in_types = built_in_types
		self.member_exclusion_regexes = member_exclusion_regexes

		# None if no completions found, or an array of the completion tuples
		self.completions = None
		threading.Thread.__init__(self)

	def run(self):

		project_folder_list = self.project_folder_list
		excluded_dirs = self.excluded_dirs
		this_aliases = self.this_aliases
		current_file_lines = self.current_file_lines
		preceding_symbol = self.preceding_symbol
		prefix = self.prefix
		preceding_function_call = self.preceding_function_call
		function_return_types = self.function_return_types
		token = self.token
		symbol_region = self.symbol_region
		built_in_types = self.built_in_types
		member_exclusion_regexes = self.member_exclusion_regexes

		selected_word = token[token.rfind(".") + 1:]

		completions = []

		# First see if it is a special function return definition, like $ for $("#selector")
		if preceding_function_call:
			for next_return_type in function_return_types:
				function_names = next_return_type[coffee_utils.FUNCTION_RETURN_TYPE_FUNCTION_NAMES_KEY]
				if preceding_function_call in function_names:
					return_type = next_return_type[coffee_utils.FUNCTION_RETURN_TYPE_TYPE_NAME_KEY]
					completions = coffee_utils.get_completions_for_class(return_type, False, None, prefix, None, built_in_types, member_exclusion_regexes, False)

		if not completions:
			# Prepare to search globally if we need to...
			# Coffeescript filename regex
			coffeescript_filename_regex = coffee_utils.COFFEE_FILENAME_REGEX
			# All coffeescript file paths
			all_coffee_file_paths = coffee_utils.get_files_in(project_folder_list, coffeescript_filename_regex, excluded_dirs)

			# If @ typed, process as "this."
			if preceding_symbol == coffee_utils.THIS_SUGAR_SYMBOL:
				# Process as "this."
				this_type = coffee_utils.get_this_type(current_file_lines, symbol_region)
				if this_type:
					completions = coffee_utils.get_completions_for_class(this_type, False, current_file_lines, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, True)
				pass
			elif preceding_symbol == coffee_utils.PERIOD_OPERATOR:
				# If "this" or a substitute for it, process as "this."
				if selected_word == coffee_utils.THIS_KEYWORD or selected_word in this_aliases:
					# Process as "this."
					this_type = coffee_utils.get_this_type(current_file_lines, symbol_region)
					if this_type:
						completions = coffee_utils.get_completions_for_class(this_type, False, current_file_lines, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, True)
				else:
					# If TitleCase, assume a class, and that we want static properties and functions.
					if coffee_utils.is_capitalized(selected_word):
						# Assume it is either in the current view or in a coffee file somewhere
						completions = coffee_utils.get_completions_for_class(selected_word, True, current_file_lines, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, False)
						if not completions:
							# Now we search globally...
							completions = coffee_utils.get_completions_for_class(selected_word, True, None, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, False)

					# If nothing yet, assume a variable.
					if not completions:
						variable_type = coffee_utils.get_variable_type(current_file_lines, token, symbol_region, all_coffee_file_paths, built_in_types, [])
						if variable_type:
							# Assume it is either in the current view or in a coffee file somewhere
							completions = coffee_utils.get_completions_for_class(variable_type, False, current_file_lines, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, False)
					if not completions:
						# Now we search globally for a class... Maybe they're making a static call on something lowercase? Bad design, but check anyways.
						completions = coffee_utils.get_completions_for_class(selected_word, True, None, prefix, all_coffee_file_paths, built_in_types, member_exclusion_regexes, False)
		if completions:
			self.completions = completions
########NEW FILE########
__FILENAME__ = CoffeeGotoDefinition
import sublime, sublime_plugin
import re
import os
import threading

try:
	# Python 3
	from . import coffee_utils
	from .coffee_utils import debug
except (ValueError):
	# Python 2
	import coffee_utils
	from coffee_utils import debug

COMMAND_NAME = 'coffee_goto_definition'
STATUS_MESSAGE_DEFINITION_FOUND = "Coffee: Definition for \"%s\" found."
STATUS_MESSAGE_NO_DEFINITION_FOUND = "Coffee: No definition for \"%s\" found."
STATUS_MESSAGE_COFFEE_GOTO_DEFINITION = "Coffee: Goto Definition of \"%s\""

# SEARCH ORDER:
# Current file class (TitleCaps only)
# Current file function
# Current file assignment
# Global TitleCaps.coffee class
# Global search for class (TitleCaps only)
# Global search for function

# TODO:
# X Add config for "this" aliases (DONE)
# - Codo docs searching for function parameter types
# X Goto definition knows about function parameters and for loop variables
# - Smarter operand parsing. E.g. Given: this.test = "test", when goto "test", look for "this.test = ", not "test ="
# - Check contents of currently open views
# - Menu integration

class CoffeeGotoDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):

		# Get the window
		self.window = sublime.active_window()

		# The current view
		view = self.view
		# Lines for currently viewed file
		current_file_lines = coffee_utils.get_view_content_lines(view)
		
		# Get currently selected word
		coffee_utils.select_current_word(view)
		selected_word = coffee_utils.get_selected_word(view)

		selected_region = self.view.sel()[0]

		# http://www.sublimetext.com/forum/viewtopic.php?f=6&t=9076
		settings = sublime.load_settings(coffee_utils.SETTINGS_FILE_NAME)

		# Pull the excluded dirs from preferences
		excluded_dirs = settings.get(coffee_utils.PREFERENCES_COFFEE_EXCLUDED_DIRS)
		if not excluded_dirs:
			excluded_dirs = []

		restricted_to_dirs = settings.get(coffee_utils.PREFERENCES_COFFEE_RESTRICTED_TO_PATHS)
		if not restricted_to_dirs:
			restricted_to_dirs = []

		# List of all project folders
		project_folder_list = self.window.folders()

		if restricted_to_dirs:
			specific_project_folders = []
			for next_restricted_dir in restricted_to_dirs:
				for next_project_folder in project_folder_list:
					next_specific_folder = os.path.normpath(os.path.join(next_project_folder, next_restricted_dir))
					specific_project_folders.append(next_specific_folder)
			project_folder_list = specific_project_folders

		# If there is a word selection and we're looking at a coffee file...
		if len(selected_word) > 0 and coffee_utils.is_coffee_syntax(view):

			thread = CoffeeGotoDefinitionThread(project_folder_list, current_file_lines, selected_word, excluded_dirs, selected_region)
			thread.start()
			self.check_operation(thread)

	def check_operation(self, thread, previous_progress_indicator_tuple=None):
		selected_word = thread.selected_word
		if not thread.is_alive():

			# Flatten any selection ranges
			if len(self.view.sel()) > 0:
				region = self.view.sel()[0]
				debug(region)
				end_point = region.end()
				region_to_select = sublime.Region(end_point, end_point)
				coffee_utils.select_region_in_view(self.view, region_to_select)

			matched_location_tuple = thread.matched_location_tuple
			if matched_location_tuple:
				# debug("Match found!")
				file_to_open = matched_location_tuple[0]
				row = matched_location_tuple[1] + 1
				column = matched_location_tuple[2] + 1
				match = matched_location_tuple[3]
				row_start_index = matched_location_tuple[4]
				# If there is a file to open...
				if file_to_open:
					# Open the file in the editor
					coffee_utils.open_file_at_position(self.window, file_to_open, row, column)
				# Otherwise, assume we found the match in the current view
				else:
					match_end = row_start_index + match.start() + len(match.group())
					region_to_select = sublime.Region(match_end, match_end)
					coffee_utils.select_region_in_view(self.view, region_to_select)
					self.view.show(region_to_select)

				self.window.active_view().set_status(COMMAND_NAME, STATUS_MESSAGE_DEFINITION_FOUND % selected_word)
			else:
				self.window.active_view().set_status(COMMAND_NAME, STATUS_MESSAGE_NO_DEFINITION_FOUND % selected_word)

		else:
			# Create the command's goto definition text, including the selected word. For the status bar.
			goto_definition_status_text = STATUS_MESSAGE_COFFEE_GOTO_DEFINITION % selected_word
			# Get a tuple containing the progress text, progress position, and progress direction.
			# This is used to animate a progress indicator in the status bar.
			current_progress_indicator_tuple = coffee_utils.get_progress_indicator_tuple(previous_progress_indicator_tuple)
			# Get the progress text
			progress_indicator_status_text = current_progress_indicator_tuple[0]
			# Set the status bar text so the user knows what's going on
			self.window.active_view().set_status(COMMAND_NAME, goto_definition_status_text + " " + progress_indicator_status_text)
			# Check again momentarily to see if the operation has completed.
			sublime.set_timeout(lambda: self.check_operation(thread, current_progress_indicator_tuple), 100)

class CoffeeGotoDefinitionThread(threading.Thread):
	
	def __init__(self, project_folder_list, current_file_lines, selected_word, excluded_dirs, selected_region):
		self.project_folder_list = project_folder_list
		self.current_file_lines = current_file_lines
		self.selected_word = selected_word
		self.excluded_dirs = excluded_dirs
		self.selected_region = selected_region
		# None if no match was found, or a tuple containing the filename, row, column and match
		self.matched_location_tuple = None
		threading.Thread.__init__(self)

	def run(self):

		project_folder_list = self.project_folder_list
		current_file_lines = self.current_file_lines
		selected_word = self.selected_word
		excluded_dirs = self.excluded_dirs
		selected_region = self.selected_region

		# This will be assigned whem a match is made
		matched_location_tuple = None

		# The regular expression used to search for the selected class
		class_regex = coffee_utils.CLASS_REGEX % re.escape(selected_word)
		# The regex used to search for the selected function
		function_regex = coffee_utils.FUNCTION_REGEX % re.escape(selected_word)
		# The regex used to search for the selected variable assignment
		assignment_regex = coffee_utils.ASSIGNMENT_REGEX % re.escape(selected_word)
		# The regex used to search for the selected variable as a parameter in a method
		param_regex = coffee_utils.PARAM_REGEX.format(name=re.escape(selected_word))

		# The regex used to search for the selected variable as a for loop var
		for_loop_regex = coffee_utils.FOR_LOOP_REGEX % re.escape(selected_word)

		debug(("Selected: \"%s\"" % selected_word))

		# ------ CURRENT FILE: CLASS (TitleCaps ONLY) ------------

		if not matched_location_tuple:

				# If so, we assume it is a class. 
				debug("Checking for local class %s..." % selected_word)
				class_location_search_tuple = coffee_utils.find_location_of_regex_in_files(class_regex, current_file_lines, [])
				if class_location_search_tuple:
					matched_location_tuple = class_location_search_tuple

		# ------ GLOBAL SEARCH: CLASS ----------------------------

		if not matched_location_tuple:

			# Coffeescript filename regex
			coffeescript_filename_regex = coffee_utils.COFFEE_FILENAME_REGEX
			# All coffeescript file paths
			all_coffee_file_paths = coffee_utils.get_files_in(project_folder_list, coffeescript_filename_regex, excluded_dirs)

			debug("Checking globally for class %s..." % selected_word)
			# Assume it is a file called selected_word.coffee
			exact_file_name_regex = "^" + re.escape(selected_word) + "(?:" + coffee_utils.COFFEE_EXTENSIONS_WITH_PIPES + ")$"
			exact_name_file_paths = coffee_utils.get_files_in(project_folder_list, exact_file_name_regex, excluded_dirs)
			exact_location_search_tuple = coffee_utils.find_location_of_regex_in_files(class_regex, None, exact_name_file_paths)
			if exact_location_search_tuple:
				matched_location_tuple = exact_location_search_tuple
			else:
				global_class_location_search_tuple = coffee_utils.find_location_of_regex_in_files(class_regex, None, all_coffee_file_paths)
				if global_class_location_search_tuple:
					matched_location_tuple = global_class_location_search_tuple

		# ------ CURRENT FILE: FUNCTION --------------------------
		if not matched_location_tuple:
			debug("Checking for local function %s..." % selected_word)
			local_function_location_search_tuple = coffee_utils.find_location_of_regex_in_files(function_regex, current_file_lines, [])
			if local_function_location_search_tuple:
				matched_location_tuple = local_function_location_search_tuple

		# ------ CURRENT FILE: ASSIGNMENT ------------------------

		if not matched_location_tuple:
			
			debug("Checking for local assignment of %s..." % selected_word)
			backwards_match_tuple = coffee_utils.search_backwards_for(current_file_lines, assignment_regex, selected_region)
			if backwards_match_tuple:
				filename_tuple = tuple([None])
				matched_location_tuple = filename_tuple + backwards_match_tuple
			else:
				# Nothing found. Now let's look backwards for a method parameter
				param_match_tuple = coffee_utils.search_backwards_for(current_file_lines, param_regex, selected_region)
				if param_match_tuple:
					filename_tuple = tuple([None])
					matched_location_tuple = filename_tuple + param_match_tuple	
				else:
					for_loop_match_tuple = coffee_utils.search_backwards_for(current_file_lines, for_loop_regex, selected_region)
					if for_loop_match_tuple:
						filename_tuple = tuple([None])
						matched_location_tuple = filename_tuple + for_loop_match_tuple
					# Otherwise, forwards search for it. It could be defined in the constructor.
					else:
						forwards_match_tuple = coffee_utils.find_location_of_regex_in_files(assignment_regex, current_file_lines, [])
						if forwards_match_tuple:
							matched_location_tuple = forwards_match_tuple

		# ------ GLOBAL SEARCH: FUNCTION -------------------------

		if not matched_location_tuple:

			# Coffeescript filename regex
			coffeescript_filename_regex = coffee_utils.COFFEE_FILENAME_REGEX
			# All coffeescript file paths
			all_coffee_file_paths = coffee_utils.get_files_in(project_folder_list, coffeescript_filename_regex, excluded_dirs)

			debug("Checking globally for function %s..." % selected_word)
			global_function_location_search_tuple = coffee_utils.find_location_of_regex_in_files(function_regex, None, all_coffee_file_paths)
			if global_function_location_search_tuple:
				matched_location_tuple = global_function_location_search_tuple

		# ------ DOT OPERATION LOOKUP (TBD) ----------------------
		# TODO: Pull out dot operator object, determine its assignment type, find class, goto method/property.
		#	    Also, determine where to put this lookup.

		# ------ SUPER METHOD LOOKUP (TBD) -----------------------
		# TODO: If selected_word is "super", assume a function and then attempt to find 
		#       extending class and open it to the function the cursor is within.

		# ------ STORE MATCH RESULTS -----------------------------
		# If not None, then we found something that matched the search!
		if matched_location_tuple:
			self.matched_location_tuple = matched_location_tuple
########NEW FILE########
__FILENAME__ = coffee_utils
import sublime
import re
import os

# TODO:
# - Document this file.
# - Split out functionality where possible.

# This file is what happens when you code non-stop for several days.
# I tried to make the main files as easy to follow along as possible.
# This file, not so much.

# Set to true to enable debug output
DEBUG = False

SETTINGS_FILE_NAME = "CoffeeComplete Plus.sublime-settings"
PREFERENCES_COFFEE_EXCLUDED_DIRS = "coffee_autocomplete_plus_excluded_dirs"
PREFERENCES_COFFEE_RESTRICTED_TO_PATHS = "coffee_autocomplete_plus_restricted_to_paths"
PREFERENCES_THIS_ALIASES = "coffee_autocomplete_plus_this_aliases"
PREFERENCES_MEMBER_EXCLUSION_REGEXES = "coffee_autocomplete_plus_member_exclusion_regexes"
BUILT_IN_TYPES_SETTINGS_FILE_NAME = "CoffeeComplete Plus Built-In Types.sublime-settings"
BUILT_IN_TYPES_SETTINGS_KEY = "coffee_autocomplete_plus_built_in_types"
CUSTOM_TYPES_SETTINGS_FILE_NAME = "CoffeeComplete Plus Custom Types.sublime-settings"
CUSTOM_TYPES_SETTINGS_KEY = "coffee_autocomplete_plus_custom_types"
FUNCTION_RETURN_TYPES_SETTINGS_KEY = "coffee_autocomplete_plus_function_return_types"
FUNCTION_RETURN_TYPE_TYPE_NAME_KEY = "type_name"
FUNCTION_RETURN_TYPE_FUNCTION_NAMES_KEY = "function_names"

COFFEESCRIPT_SYNTAX = r"CoffeeScript"
COFFEE_EXTENSIONS_LIST = [".coffee", ".litcoffee", ".coffee.md"]
COFFEE_EXTENSIONS_WITH_PIPES = "|".join([re.escape(e) for e in COFFEE_EXTENSIONS_LIST])
CONSTRUCTOR_KEYWORDS = ["constructor", "initialize", "init"]
THIS_SUGAR_SYMBOL = "@"
THIS_KEYWORD = "this"
PERIOD_OPERATOR = "."
COFFEE_FILENAME_REGEX = r"(?:" + COFFEE_EXTENSIONS_WITH_PIPES + ")$"
CLASS_REGEX = r"class\s+%s((\s*$)|[^a-zA-Z0-9_$])"
CLASS_REGEX_ANY = r"class\s+([a-zA-Z0-9_$]+)((\s*$)|[^a-zA-Z0-9_$])"
CLASS_REGEX_WITH_EXTENDS = r"class\s+%s\s*($|(\s+extends\s+([a-zA-Z0-9_$.]+)))"
SINGLE_LINE_COMMENT_REGEX = r"#.*?$"
TYPE_HINT_COMMENT_REGEX = r"#.*?\[([a-zA-Z0-9_$]+)\].*$"
TYPE_HINT_PARAMETER_COMMENT_REGEX = r"#.*?(\[([a-zA-Z0-9_$]+)\]\s*{var_name}((\s*$)|[^a-zA-Z0-9_$]))|({var_name}\s*\[([a-zA-Z0-9_$]+)\]((\s*$)|[^a-zA-Z0-9_$]))"
# Function regular expression. Matches:
# methodName  =   (aas,bsa, casd )    ->
FUNCTION_REGEX = r"(^|[^a-zA-Z0-9_$])(%s)\s*[:]\s*(\((.*?)\))?\s*[=\-]>"
FUNCTION_REGEX_ANY = r"(^|[^a-zA-Z0-9_$])(([a-zA-Z0-9_$]+))\s*[:]\s*(\((.*?)\))?\s*[=\-]>"
# Assignment regular expression. Matches:
# asdadasd =
ASSIGNMENT_REGEX = r"(^|[^a-zA-Z0-9_$])%s\s*="
# Static assignment regex
STATIC_ASSIGNMENT_REGEX = r"^\s*([@]|(this\s*[.]))\s*([a-zA-Z0-9_$]+)\s*[:=]"
# Static function regex
STATIC_FUNCTION_REGEX = r"(^|[^a-zA-Z0-9_$])\s*([@]|(this\s*[.]))\s*([a-zA-Z0-9_$]+)\s*[:]\s*(\((.*?)\))?\s*[=\-]>"
# Regex for finding a function parameter. Call format on the string, with name=var_name
PARAM_REGEX = r"\(\s*(({name})|({name}\s*=?.*?[,].*?)|(.*?[,]\s*{name}\s*=?.*?[,].*?)|(.*?[,]\s*{name}))\s*=?.*?\)\s*[=\-]>"
# Regex for finding a variable declared in a for loop.
FOR_LOOP_REGEX = r"for\s*.*?[^a-zA-Z0-9_$]%s[^a-zA-Z0-9_$]"
# Regex for constructor @ params, used for type hinting.
CONSTRUCTOR_SELF_ASSIGNMENT_PARAM_REGEX = r"(?:(?:constructor)|(?:initialize)|(?:init))\s*[:]\s*\(\s*((@{name})|(@{name}\s*[,].*?)|(.*?[,]\s*@{name}\s*[,].*?)|(.*?[,]\s*@{name}))\s*\)\s*[=\-]>\s*$"

# Assignment with the value it's being assigned to. Matches:
# blah = new Dinosaur()
ASSIGNMENT_VALUE_WITH_DOT_REGEX = r"(^|[^a-zA-Z0-9_$])%s\s*=\s*(.*)"
ASSIGNMENT_VALUE_WITHOUT_DOT_REGEX = r"(^|[^a-zA-Z0-9_$.])%s\s*=\s*(.*)"

# Used to determining what class is being created with the new keyword. Matches:
# new Macaroni
NEW_OPERATION_REGEX = r"new\s+([a-zA-Z0-9_$.]+)"

PROPERTY_INDICATOR = u'\u25CB'
METHOD_INDICATOR = u'\u25CF'
INHERITED_INDICATOR = u'\u2C75'

BUILT_IN_TYPES_TYPE_NAME_KEY = "name"
BUILT_IN_TYPES_TYPE_ENABLED_KEY = "enabled"
BUILT_IN_TYPES_CONSTRUCTOR_KEY = "constructor"
BUILT_IN_TYPES_STATIC_PROPERTIES_KEY = "static_properties"
BUILT_IN_TYPES_STATIC_PROPERTY_NAME_KEY = "name"
BUILT_IN_TYPES_STATIC_METHODS_KEY = "static_methods"
BUILT_IN_TYPES_STATIC_METHOD_NAME_KEY = "name"
BUILT_IN_TYPES_INSTANCE_PROPERTIES_KEY = "instance_properties"
BUILT_IN_TYPES_INSTANCE_PROPERTY_NAME_KEY = "name"
BUILT_IN_TYPES_INSTANCE_METHODS_KEY = "instance_methods"
BUILT_IN_TYPES_INSTANCE_METHOD_NAME_KEY = "name"
BUILT_IN_TYPES_METHOD_NAME_KEY = "name"
BUILT_IN_TYPES_METHOD_INSERTION_KEY = "insertion"
BUILT_IN_TYPES_METHOD_ARGS_KEY = "args"
BUILT_IN_TYPES_METHOD_ARG_NAME_KEY = "name"
BUILT_IN_TYPES_INHERITS_FROM_OBJECT_KEY = "inherits_from_object"


# Utility functions
def debug(message):
    if DEBUG:
        print(message)


def select_current_word(view):
    if len(view.sel()) > 0:
        selected_text = view.sel()[0]
        word_region = view.word(selected_text)
        view.sel().clear()
        view.sel().add(word_region)


def get_selected_word(view):
    word = ""
    if len(view.sel()) > 0:
        selected_text = view.sel()[0]
        word_region = view.word(selected_text)
        word = get_word_at(view, word_region)
    return word


def get_word_at(view, region):
    word = ""
    word_region = view.word(region)
    word = view.substr(word_region)
    word = re.sub(r'[^a-zA-Z0-9_$]', '', word)
    word = word.strip()
    return word


def get_token_at(view, region):
    token = ""
    if len(view.sel()) > 0:
        selected_line = view.line(region)
        preceding_text = view.substr(sublime.Region(selected_line.begin(), region.begin())).strip()
        token_regex = r"[^a-zA-Z0-9_$.@]*?([a-zA-Z0-9_$.@]+)$"
        match = re.search(token_regex, preceding_text)
        if match:
            token = match.group(1)
    token = token.strip()
    return token


def get_preceding_symbol(view, prefix, locations):
    index = locations[0]
    symbol_region = sublime.Region(index - 1 - len(prefix), index - len(prefix))
    symbol = view.substr(symbol_region)
    return symbol


def get_preceding_function_call(view):
    function_call = ""
    if len(view.sel()) > 0:
        selected_text = view.sel()[0]
        selected_line = view.line(sublime.Region(selected_text.begin() - 1, selected_text.begin() - 1))
        preceding_text = view.substr(sublime.Region(selected_line.begin(), selected_text.begin() - 1)).strip()
        function_call_regex = r".*?([a-zA-Z0-9_$]+)\s*\(.*?\)"
        match = re.search(function_call_regex, preceding_text)
        if match:
            function_call = match.group(1)
    return function_call


def get_preceding_token(view):
    token = ""
    if len(view.sel()) > 0:
        selected_text = view.sel()[0]
        if selected_text.begin() > 2:
            token_region = sublime.Region(selected_text.begin() - 1, selected_text.begin() - 1)
            token = get_token_at(view, token_region)
    return token


# Complete this.
def get_preceding_call_chain(view):
    word = ""
    if len(view.sel()) > 0:
        selected_text = view.sel()[0]
        selected_text = view.sel()[0]
        selected_line = view.line(sublime.Region(selected_text.begin() - 1, selected_text.begin() - 1))
        preceding_text = view.substr(sublime.Region(selected_line.begin(), selected_text.begin() - 1)).strip()
        function_call_regex = r".*?([a-zA-Z0-9_$]+)\s*\(.*?\)"
        match = re.search(function_call_regex, preceding_text)
        if match:
            #function_call = match.group(1)
            pass
    return word


def is_capitalized(word):
    capitalized = False
    # Underscores are sometimes used to indicate an internal property, so we
    # find the first occurrence of an a-zA-Z character. If not found, we assume lowercase.
    az_word = re.sub("[^a-zA-Z]", "", word)
    if len(az_word) > 0:
        first_letter = az_word[0]
        capitalized = first_letter.isupper()

    # Special case for $
    capitalized = capitalized | word.startswith("$")

    return capitalized


def get_files_in(directory_list, filename_regex, excluded_dirs):
    files = []
    for next_directory in directory_list:
        # http://docs.python.org/2/library/os.html?highlight=os.walk#os.walk
        for path, dirs, filenames in os.walk(next_directory):
            # print str(path)
            for next_excluded_dir in excluded_dirs:
                try:
                    dirs.remove(next_excluded_dir)
                except:
                    pass
            for next_file_name in filenames:
                # http://docs.python.org/2/library/re.html
                match = re.search(filename_regex, next_file_name)
                if match:
                    # http://docs.python.org/2/library/os.path.html?highlight=os.path.join#os.path.join
                    next_full_path = os.path.join(path, next_file_name)
                    files.append(next_full_path)
    return files


def get_lines_for_file(file_path):
    lines = []
    try:
        # http://docs.python.org/2/tutorial/inputoutput.html
        opened_file = open(file_path, "r")  # r = read only
        lines = opened_file.readlines()
    except:
        pass
    return lines


# Returns a tuple with (row, column, match, row_start_index), or None
def get_positions_of_regex_match_in_file(file_lines, regex):
    found_a_match = False
    matched_row = -1
    matched_column = -1
    match_found = None
    line_start_index = -1

    current_row = 0

    current_line_start_index = 0
    for next_line in file_lines:
        # Remove comments
        modified_next_line = re.sub(SINGLE_LINE_COMMENT_REGEX, "", next_line)
        match = re.search(regex, modified_next_line)
        if match:
            found_a_match = True
            matched_row = current_row
            matched_column = match.end()
            match_found = match
            line_start_index = current_line_start_index
            break
        current_row = current_row + 1
        current_line_start_index = current_line_start_index + len(next_line)

    positions_tuple = None
    if found_a_match:
        positions_tuple = (matched_row, matched_column, match_found, line_start_index)

    return positions_tuple


def open_file_at_position(window, file_path, row, column):
    # Beef
    # http://www.sublimetext.com/docs/2/api_reference.html#sublime.Window
    path_with_position_encoding = file_path + ":" + str(row) + ":" + str(column)
    window.open_file(path_with_position_encoding, sublime.ENCODED_POSITION)
    return


# Returns a tuple with (file_path, row, column, match, row_start_index)
def find_location_of_regex_in_files(contents_regex, local_file_lines, global_file_path_list=[]):
    # The match tuple containing the filename and positions.
    # Will be returned as None if no matches are found.
    file_match_tuple = None

    if local_file_lines:
        # Search the file for the regex.
        positions_tuple = get_positions_of_regex_match_in_file(local_file_lines, contents_regex)
        if positions_tuple:
            # We've found a match! Save the file path plus the positions and the match itself
            file_match_tuple = tuple([None]) + positions_tuple

    # If we are to search globally...
    if not file_match_tuple and global_file_path_list:
        for next_file_path in global_file_path_list:
            if next_file_path:
                file_lines = get_lines_for_file(next_file_path)
                # Search the file for the regex.
                positions_tuple = get_positions_of_regex_match_in_file(file_lines, contents_regex)
                if positions_tuple:
                    # We've found a match! Save the file path plus the positions and the match itself
                    file_match_tuple = tuple([next_file_path]) + positions_tuple
                    # Stop the for loop
                    break
    return file_match_tuple


def select_region_in_view(view, region):
    view.sel().clear()
    view.sel().add(region)
    # Refresh hack.
    original_position = view.viewport_position()
    view.set_viewport_position((original_position[0], original_position[1] + 1))
    view.set_viewport_position(original_position)


def get_progress_indicator_tuple(previous_indicator_tuple):
    STATUS_MESSAGE_PROGRESS_INDICATOR = "[%s=%s]"
    if not previous_indicator_tuple:
        previous_indicator_tuple = ("", 0, 1)
    progress_indicator_position = previous_indicator_tuple[1]
    progress_indicator_direction = previous_indicator_tuple[2]
    # This animates a little activity indicator in the status area.
    # It animates an equals symbol bouncing back and fourth between square brackets.
    # We calculate the padding around the equal based on the last known position.
    num_spaces_before = progress_indicator_position % 8
    num_spaces_after = (7) - num_spaces_before
    # When the equals hits the edge, we change directions.
    # Direction is -1 for moving left and 1 for moving right.
    if not num_spaces_after:
        progress_indicator_direction = -1
    if not num_spaces_before:
        progress_indicator_direction = 1
    progress_indicator_position += progress_indicator_direction
    padding_before = ' ' * num_spaces_before
    padding_after = ' ' * num_spaces_after
    # Create the progress indication text
    progress_indicator_text = STATUS_MESSAGE_PROGRESS_INDICATOR % (padding_before, padding_after)
    # Return the progress indication tuple
    return (progress_indicator_text, progress_indicator_position, progress_indicator_direction)


def get_syntax_name(view):
    syntax = os.path.splitext(os.path.basename(view.settings().get('syntax')))[0]
    return syntax


def is_coffee_syntax(view):
    return bool(re.match(COFFEESCRIPT_SYNTAX, get_syntax_name(view)))


def get_this_type(file_lines, start_region):

    type_found = None
    # Search backwards from current position for the type
    # We're looking for a class definition
    class_regex = CLASS_REGEX_ANY

    match_tuple = search_backwards_for(file_lines, class_regex, start_region)
    if match_tuple:
        # debug(str(match_tuple[0]) + ", " + str(match_tuple[1]) + ", " + match_tuple[2].group(1))
        type_found = match_tuple[2].group(1)
    else:
        debug("No match!")

    return type_found


def get_variable_type(file_lines, token, start_region, global_file_path_list, built_in_types, previous_variable_names=[]):

    type_found = None

    # Check for "this"
    if token == "this":
        type_found = get_this_type(file_lines, start_region)
    elif token.startswith("@"):
        token = "this." + token[1:]

    # We're looking for a variable assignent
    assignment_regex = ASSIGNMENT_VALUE_WITH_DOT_REGEX % token

    # print "Assignment regex: " + assignment_regex

    # Search backwards from current position for the type
    if not type_found:
        match_tuple = search_backwards_for(file_lines, assignment_regex, start_region)
        if match_tuple:
            type_found = get_type_from_assignment_match_tuple(token, match_tuple, file_lines, previous_variable_names)
            # Well, we found the assignment. But we don't know what it is.
            # Let's try to find a variable name and get THAT variable type...
            if not type_found:
                type_found = get_type_from_assigned_variable_name(file_lines, token, match_tuple, global_file_path_list, built_in_types, previous_variable_names)

    # Let's try searching backwards for parameter hints in comments...
    if not type_found:
        # The regex used to search for the variable as a parameter in a method
        param_regex = PARAM_REGEX.format(name=re.escape(token))
        match_tuple = search_backwards_for(file_lines, param_regex, start_region)
        # We found the variable! it's a parameter. Let's find a comment with a type hint.
        if match_tuple:
            type_found = get_type_from_parameter_match_tuple(token, match_tuple, file_lines, previous_variable_names)

    # If backwards searching isn't working, at least try to find something...
    if not type_found:
        # Forward search from beginning for assignment:
        match_tuple = get_positions_of_regex_match_in_file(file_lines, assignment_regex)
        if match_tuple:
            type_found = get_type_from_assignment_match_tuple(token, match_tuple, file_lines, previous_variable_names)
            if not type_found:
                type_found = get_type_from_assigned_variable_name(file_lines, token, match_tuple, global_file_path_list, built_in_types, previous_variable_names)

    # If still nothing, maybe it's an @ parameter in the constructor?
    if not type_found:

        # Get the last word in the chain, if it's a chain.
        # E.g. Get variableName from this.variableName.[autocomplete]
        selected_word = token[token.rfind(".") + 1:]

        if token.startswith(THIS_KEYWORD + ".") or token.startswith(THIS_SUGAR_SYMBOL):

            # The regex used to search for the variable as a parameter in a method
            param_regex = CONSTRUCTOR_SELF_ASSIGNMENT_PARAM_REGEX.format(name=re.escape(selected_word))

            # Forward search from beginning for param:
            match_tuple = get_positions_of_regex_match_in_file(file_lines, param_regex)
            # We found the variable! it's a parameter. Let's find a comment with a type hint.
            if match_tuple:
                type_found = get_type_from_parameter_match_tuple(selected_word, match_tuple, file_lines)

        if not type_found:
            # Find something. Anything!
            word_assignment_regex = ASSIGNMENT_VALUE_WITHOUT_DOT_REGEX % selected_word

            # Forward search from beginning for assignment:
            match_tuple = get_positions_of_regex_match_in_file(file_lines, word_assignment_regex)
            if match_tuple:
                type_found = get_type_from_assignment_match_tuple(token, match_tuple, file_lines, previous_variable_names)
                if not type_found:
                    type_found = get_type_from_assigned_variable_name(file_lines, token, match_tuple, global_file_path_list, built_in_types, previous_variable_names)

    return type_found


def get_type_from_assigned_variable_name(file_lines, token, match_tuple, global_file_path_list, built_in_types, previous_variable_names=[]):

    type_found = None

    assignment_value_string = match_tuple[2].group(2).strip()
    # row start index + column index
    token_index = match_tuple[3] + match_tuple[1]
    token_region = sublime.Region(token_index, token_index)
    token_match = re.search(r"^([a-zA-Z0-9_$.]+)$", assignment_value_string)
    if token_match:
        next_token = token_match.group(1)
        if next_token not in previous_variable_names:
            previous_variable_names.append(token)
            type_found = get_variable_type(file_lines, next_token, token_region, global_file_path_list, built_in_types, previous_variable_names)

    # Determine what type a method returns
    if not type_found:
        # print "assignment_value_string: " + assignment_value_string
        method_call_regex = r"([a-zA-Z0-9_$.]+)\s*[.]\s*([a-zA-Z0-9_$]+)\s*\("
        method_call_match = re.search(method_call_regex, assignment_value_string)
        if method_call_match:
            object_name = method_call_match.group(1)
            method_name = method_call_match.group(2)
            object_type = get_variable_type(file_lines, object_name, token_region, global_file_path_list, built_in_types, previous_variable_names)
            if object_type:
                type_found = get_return_type_for_method(object_type, method_name, file_lines, global_file_path_list, built_in_types)

    return type_found


def get_return_type_for_method(object_type, method_name, file_lines, global_file_path_list, built_in_types):

    type_found = None

    next_class_to_scan = object_type

    # Search the class and all super classes
    while next_class_to_scan and not type_found:

        class_regex = CLASS_REGEX % re.escape(next_class_to_scan)
        # (file_path, row, column, match, row_start_index)
        class_location_search_tuple = find_location_of_regex_in_files(class_regex, file_lines, global_file_path_list)
        if class_location_search_tuple:

            file_found = class_location_search_tuple[0]

            # Consider if it was found locally, in the view
            if not file_found:
                class_file_lines = file_lines
            else:
                class_file_lines = get_lines_for_file(file_found)

            # If found, search for the method in question.
            method_regex = FUNCTION_REGEX % re.escape(method_name)
            positions_tuple = get_positions_of_regex_match_in_file(class_file_lines, method_regex)
            # (row, column, match, row_start_index)
            if positions_tuple:
                # Check for comments, and hopefully the return hint, on previous rows.
                matched_row = positions_tuple[0]
                row_to_check_index = matched_row - 1

                non_comment_code_reached = False
                while not non_comment_code_reached and row_to_check_index >= 0 and not type_found:
                    current_row_text = class_file_lines[row_to_check_index]

                    # Make sure this line only contains comments.
                    mod_line = re.sub(SINGLE_LINE_COMMENT_REGEX, "", current_row_text).strip()
                    # If it wasn't just a comment line...
                    if len(mod_line) > 0:
                        non_comment_code_reached = True
                    else:
                        # Search for hint: @return [TYPE]
                        return_type_hint_regex = r"@return\s*\[([a-zA-Z0-9_$]+)\]"
                        hint_match = re.search(return_type_hint_regex, current_row_text)
                        if hint_match:
                            # We found it!
                            type_found = hint_match.group(1)
                    row_to_check_index = row_to_check_index - 1

            # If nothing was found, see if the class extends another one and is inheriting the method.
            if not type_found:
                extends_regex = CLASS_REGEX_WITH_EXTENDS % next_class_to_scan
                # (row, column, match, row_start_index)
                extends_match_positions = get_positions_of_regex_match_in_file(class_file_lines, extends_regex)
                if extends_match_positions:
                    extends_match = extends_match_positions[2]
                    next_class_to_scan = extends_match.group(3)
                else:
                    next_class_to_scan = None
    return type_found


def get_type_from_assignment_match_tuple(variable_name, match_tuple, file_lines, previous_variable_names=[]):

    type_found = None
    if match_tuple:
        match = match_tuple[2]
        assignment_value_string = match.group(2)
        # Check for a type hint on current row or previous row.
        # These will override anything else.
        matched_row = match_tuple[0]
        previous_row = matched_row - 1
        current_row_text = file_lines[matched_row]
        hint_match = re.search(TYPE_HINT_COMMENT_REGEX, current_row_text)
        if hint_match:
            type_found = hint_match.group(1)
        if not type_found and previous_row >= 0:
            previous_row_text = file_lines[previous_row]
            hint_match = re.search(TYPE_HINT_COMMENT_REGEX, previous_row_text)
            if hint_match:
                type_found = hint_match.group(1)
        if not type_found:
            assignment_value_string = re.sub(SINGLE_LINE_COMMENT_REGEX, "", assignment_value_string).strip()
            type_found = get_type_from_assignment_value(assignment_value_string)
    return type_found


def get_type_from_parameter_match_tuple(variable_name, match_tuple, file_lines, previous_variable_names=[]):

    type_found = None
    if match_tuple:
        # Check for comments, and hopefully type hints, on previous rows.
        matched_row = match_tuple[0]
        row_to_check_index = matched_row - 1

        non_comment_code_reached = False
        while not non_comment_code_reached and row_to_check_index >= 0 and not type_found:
            current_row_text = file_lines[row_to_check_index]

            # Make sure this line only contains comments.
            mod_line = re.sub(SINGLE_LINE_COMMENT_REGEX, "", current_row_text).strip()
            # If it wasn't just a comment line...
            if len(mod_line) > 0:
                non_comment_code_reached = True
            else:
                # It's a comment. Let's look for a type hint in the form:
                # variable_name [TYPE] ~OR~ [TYPE] variable_name
                hint_regex = TYPE_HINT_PARAMETER_COMMENT_REGEX.format(var_name=re.escape(variable_name))
                hint_match = re.search(hint_regex, current_row_text)
                if hint_match:
                    # One of these two groups contains the type...
                    if hint_match.group(2):
                        type_found = hint_match.group(2)
                    else:
                        type_found = hint_match.group(6)
            row_to_check_index = row_to_check_index - 1
    return type_found


def get_type_from_assignment_value(assignment_value_string):
    determined_type = None

    assignment_value_string = assignment_value_string.strip()

    # Check for built in types
    object_regex = r"^\{.*\}$"
    if not determined_type:
        match = re.search(object_regex, assignment_value_string)
        if match:
            determined_type = "Object"
    double_quote_string_regex = r"(^\".*\"$)|(^.*?\+\s*\".*?\"$)|(^\".*?\"\s*\+.*?$)|(^.*?\s*\+\s*\".*?\"\s*\+\s*.*?$)"
    if not determined_type:
        match = re.search(double_quote_string_regex, assignment_value_string)
        if match:
            determined_type = "String"
    single_quote_string_regex = r"(^['].*[']$)|(^.*?\+\s*['].*?[']$)|(^['].*?[']\s*\+.*?$)|(^.*?\s*\+\s*['].*?[']\s*\+\s*.*?$)"
    if not determined_type:
        match = re.search(single_quote_string_regex, assignment_value_string)
        if match:
            determined_type = "String"
    array_regex = r"^\[.*\]\s*$"
    if not determined_type:
        match = re.search(array_regex, assignment_value_string)
        if match:
            determined_type = "Array"
    boolean_regex = r"^(true)|(false)$"
    if not determined_type:
        match = re.search(boolean_regex, assignment_value_string)
        if match:
            determined_type = "Boolean"
    # http://stackoverflow.com/questions/4703390/how-to-extract-a-floating-number-from-a-string-in-python
    number_regex = r"^[-+]?\d*\.\d+|\d+$"
    if not determined_type:
        match = re.search(number_regex, assignment_value_string)
        if match:
            determined_type = "Number"
    regexp_regex = r"^/.*/[a-z]*$"
    if not determined_type:
        match = re.search(regexp_regex, assignment_value_string)
        if match:
            determined_type = "RegExp"
    new_operation_regex = NEW_OPERATION_REGEX
    if not determined_type:
        match = re.search(new_operation_regex, assignment_value_string)
        if match:
            determined_type = get_class_from_end_of_chain(match.group(1))

    return determined_type


# Tuple returned: (matched_row, matched_column, match, row_start_index)
def search_backwards_for(file_lines, regex, start_region):

    matched_row = -1
    matched_column = -1
    match_found = None
    row_start_index = -1

    start_index = start_region.begin()
    # debug("start: " + str(start_index))
    characters_consumed = 0
    start_line = -1
    indentation_size = 0
    current_line_index = 0
    for next_line in file_lines:
        # Find the line we're starting on...
        offset = start_index - characters_consumed
        if offset <= len(next_line) + 1:
            # debug("Start line: " + next_line)
            characters_consumed = characters_consumed + len(next_line)
            indentation_size = get_indentation_size(next_line)
            start_line = current_line_index
            break

        characters_consumed = characters_consumed + len(next_line)
        current_line_index = current_line_index + 1

    row_start_index = characters_consumed

    if start_line >= 0:
        # debug("start line: " + str(start_line))
        # Go backwards, searching for the class definition.
        for i in reversed(range(start_line + 1)):
            previous_line = file_lines[i]
            # print "Next line: " + previous_line[:-1]
            row_start_index = row_start_index - len(previous_line)
            # debug("Line " + str(i) + ": " + re.sub("\n", "", previous_line))
            # Returns -1 for empty lines or lines with comments only.
            next_line_indentation = get_indentation_size(previous_line)
            #debug("Seeking <= indentation_size: " + str(indentation_size) + ", Current: " + str(next_line_indentation))
            # Ignore lines with larger indentation sizes and empty lines (or lines with comments only)
            if next_line_indentation >= 0 and next_line_indentation <= indentation_size:
                indentation_size = next_line_indentation
                # Check for the class
                match = re.search(regex, previous_line)
                if match:
                    matched_row = i
                    matched_column = match.end()
                    match_found = match
                    break
    match_tuple = None
    if match_found:
        match_tuple = (matched_row, matched_column, match_found, row_start_index)
    return match_tuple


def get_indentation_size(line_of_text):
    size = -1
    mod_line = re.sub("\n", "", line_of_text)
    mod_line = re.sub(SINGLE_LINE_COMMENT_REGEX, "", mod_line)
    # If it wasn't just a comment line...
    if len(mod_line.strip()) > 0:
        mod_line = re.sub(r"[^\t ].*", "", mod_line)
        size = len(mod_line)
    # debug("Indent size [" + str(size) + "]:\n" + re.sub("\n", "", line_of_text))
    return size


def get_completions_for_class(class_name, search_statically, local_file_lines, prefix, global_file_path_list, built_in_types, member_exclusion_regexes, show_private):

    # TODO: Use prefix to make suggestions.

    completions = []
    scanned_classes = []
    original_class_name_found = False

    function_completions = []
    object_completions = []

    # First, determine if it is a built in type and return those completions...
    # Built-in types include String, Number, etc, and are configurable in settings.
    for next_built_in_type in built_in_types:
        try:
            if next_built_in_type[BUILT_IN_TYPES_TYPE_ENABLED_KEY]:
                next_class_name = next_built_in_type[BUILT_IN_TYPES_TYPE_NAME_KEY]
                if next_class_name == class_name:
                    # We are looking at a built-in type! Collect completions for it...
                    completions = get_completions_for_built_in_type(next_built_in_type, search_statically, False, member_exclusion_regexes)
                    original_class_name_found = True
                elif next_class_name == "Function" and not function_completions:
                    function_completions = get_completions_for_built_in_type(next_built_in_type, False, True, member_exclusion_regexes)
                elif next_class_name == "Object" and not object_completions:
                    object_completions = get_completions_for_built_in_type(next_built_in_type, False, True, member_exclusion_regexes)
        except Exception as e:
            print(repr(e))

    # If we didn't find completions for a built-in type, look further...
    if not completions:
        current_class_name = class_name
        is_inherited = False
        while current_class_name and current_class_name not in scanned_classes:
            # print "Scanning " + current_class_name + "..."
            # (class_found, completions, next_class_to_scan)
            completion_tuple = (False, [], None)
            if local_file_lines:
                # print "Searching locally..."
                # Search in local file.
                if search_statically:
                    completion_tuple = collect_static_completions_from_file(local_file_lines, current_class_name, is_inherited, member_exclusion_regexes, show_private)
                else:
                    completion_tuple = collect_instance_completions_from_file(local_file_lines, current_class_name, is_inherited, member_exclusion_regexes, show_private)

            # Search globally if nothing found and not local only...
            if global_file_path_list and (not completion_tuple or not completion_tuple[0]):
                class_regex = CLASS_REGEX % re.escape(current_class_name)
                global_class_location_search_tuple = find_location_of_regex_in_files(class_regex, None, global_file_path_list)
                if global_class_location_search_tuple:
                    # If found, perform Class method collection.
                    file_to_open = global_class_location_search_tuple[0]
                    class_file_lines = get_lines_for_file(file_to_open)
                    if search_statically:
                        completion_tuple = collect_static_completions_from_file(class_file_lines, current_class_name, is_inherited, member_exclusion_regexes, show_private)
                    else:
                        completion_tuple = collect_instance_completions_from_file(class_file_lines, current_class_name, is_inherited, member_exclusion_regexes, show_private)

            if current_class_name == class_name and completion_tuple[0]:
                original_class_name_found = True

            # print "Tuple: " + str(completion_tuple)
            completions.extend(completion_tuple[1])
            scanned_classes.append(current_class_name)
            current_class_name = completion_tuple[2]
            is_inherited = True

    if original_class_name_found:
        # Add Object completions (if available) -- Everything is an Object
        completions.extend(object_completions)
        if search_statically:
            completions.extend(function_completions)

    # Remove all duplicates
    completions = list(set(completions))
    # Sort
    completions.sort()
    return completions


def case_insensitive_startswith(original_string, prefix):
    return original_string.lower().startswith(prefix.lower())


def get_completions_for_built_in_type(built_in_type, is_static, is_inherited, member_exclusion_regexes):
    completions = []
    if is_static:
        static_property_objs = built_in_type[BUILT_IN_TYPES_STATIC_PROPERTIES_KEY]
        for next_static_property_obj in static_property_objs:
            next_static_property = next_static_property_obj[BUILT_IN_TYPES_STATIC_PROPERTY_NAME_KEY]
            next_static_property_insertion = next_static_property
            try:
                next_static_property_insertion = next_static_property_obj[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
            except:
                pass
            if not is_member_excluded(next_static_property, member_exclusion_regexes):
                next_completion = get_property_completion_tuple(next_static_property, next_static_property_insertion, is_inherited)
                completions.append(next_completion)

        static_methods = built_in_type[BUILT_IN_TYPES_STATIC_METHODS_KEY]
        for next_static_method in static_methods:
            method_name = next_static_method[BUILT_IN_TYPES_METHOD_NAME_KEY]
            method_name_insertion = method_name
            try:
                method_name_insertion = next_static_method[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
            except:
                pass
            if not is_member_excluded(method_name, member_exclusion_regexes):
                method_args = []
                method_insertions = []
                method_args_objs = next_static_method[BUILT_IN_TYPES_METHOD_ARGS_KEY]
                for next_method_arg_obj in method_args_objs:
                    method_arg = next_method_arg_obj[BUILT_IN_TYPES_METHOD_ARG_NAME_KEY]
                    method_args.append(method_arg)
                    method_insertion = method_arg
                    try:
                        method_insertion = next_method_arg_obj[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
                    except:
                        pass
                    method_insertions.append(method_insertion)
                next_completion = get_method_completion_tuple(method_name, method_name_insertion, method_args, method_insertions, is_inherited)
                completions.append(next_completion)
    else:
        instance_properties = []
        instance_property_objs = built_in_type[BUILT_IN_TYPES_INSTANCE_PROPERTIES_KEY]
        for next_instance_property_obj in instance_property_objs:
            next_instance_property = next_instance_property_obj[BUILT_IN_TYPES_INSTANCE_PROPERTY_NAME_KEY]
            next_instance_property_insertion = next_instance_property
            try:
                next_instance_property_insertion = next_instance_property_obj[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
            except:
                pass
            if not is_member_excluded(next_instance_property, member_exclusion_regexes):
                instance_properties.append(next_instance_property_obj[BUILT_IN_TYPES_INSTANCE_PROPERTY_NAME_KEY])
        for next_instance_property in instance_properties:
            next_completion = get_property_completion_tuple(next_instance_property, next_instance_property_insertion, is_inherited)
            completions.append(next_completion)

        instance_methods = built_in_type[BUILT_IN_TYPES_INSTANCE_METHODS_KEY]
        for next_instance_method in instance_methods:
            method_name = next_instance_method[BUILT_IN_TYPES_METHOD_NAME_KEY]
            method_name_insertion = method_name
            try:
                method_name_insertion = next_instance_method[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
            except:
                pass
            if not is_member_excluded(method_name, member_exclusion_regexes):
                method_args = []
                method_insertions = []
                method_args_objs = next_instance_method[BUILT_IN_TYPES_METHOD_ARGS_KEY]
                for next_method_arg_obj in method_args_objs:
                    method_arg = next_method_arg_obj[BUILT_IN_TYPES_METHOD_ARG_NAME_KEY]
                    method_args.append(method_arg)
                    method_insertion = method_arg
                    try:
                        method_insertion = next_method_arg_obj[BUILT_IN_TYPES_METHOD_INSERTION_KEY]
                    except:
                        pass
                    method_insertions.append(method_insertion)
                next_completion = get_method_completion_tuple(method_name, method_name_insertion, method_args, method_insertions, is_inherited)
                completions.append(next_completion)
    return completions


def collect_instance_completions_from_file(file_lines, class_name, is_inherited, member_exclusion_regexes, show_private):

    completions = []
    extended_class = None
    class_found = False

    property_completions = []
    function_completions = []

    class_and_extends_regex = CLASS_REGEX_WITH_EXTENDS % class_name

    # Find class in file lines
    match_tuple = get_positions_of_regex_match_in_file(file_lines, class_and_extends_regex)
    if match_tuple:
        class_found = True
        row = match_tuple[0]
        match = match_tuple[2]

        extended_class = match.group(3)
        if extended_class:
            extended_class = get_class_from_end_of_chain(extended_class)

        # If anything is equal to this after the first line, stop looking.
        # At that point, the class definition has ended.
        indentation_size = get_indentation_size(file_lines[row])
        # print str(indentation_size) + ": " + file_lines[row]
        # Let's dig for some info on this class!
        if row + 1 < len(file_lines):
            inside_constructor = False
            constructor_indentation = -1
            for row_index in range(row + 1, len(file_lines)):
                next_row = file_lines[row_index]
                next_indentation = get_indentation_size(next_row)
                # print str(next_indentation) + ": " + next_row
                if next_indentation >= 0:
                    if next_indentation > indentation_size:
                        if inside_constructor and next_indentation <= constructor_indentation:
                            inside_constructor = False
                        if inside_constructor:
                            this_assignment_regex = "([@]|(this\s*[.]))\s*([a-zA-Z0-9_$]+)\s*="
                            match = re.search(this_assignment_regex, next_row)
                            if match:
                                prop = match.group(3)
                                if show_private or not is_member_excluded(prop, member_exclusion_regexes):
                                    prop_completion_alias = get_property_completion_alias(prop, is_inherited)
                                    prop_completion_insertion = get_property_completion_insertion(prop)
                                    prop_completion = (prop_completion_alias, prop_completion_insertion)
                                    if prop_completion not in property_completions:
                                        property_completions.append(prop_completion)
                        else:  # Not in constructor
                            # Look for method definitions
                            function_regex = FUNCTION_REGEX_ANY
                            match = re.search(function_regex, next_row)
                            if match and not re.search(STATIC_FUNCTION_REGEX, next_row):
                                function_name = match.group(2)
                                function_args_string = match.group(5)
                                if show_private or not is_member_excluded(function_name, member_exclusion_regexes):
                                    if not function_name in CONSTRUCTOR_KEYWORDS:
                                        function_args_list = []
                                        if function_args_string:
                                            function_args_list = function_args_string.split(",")
                                        for i in range(len(function_args_list)):
                                            # Fix each one up...
                                            next_arg = function_args_list[i]
                                            next_arg = next_arg.strip()
                                            next_arg = re.sub("[^a-zA-Z0-9_$].*", "", next_arg)
                                            function_args_list[i] = re.sub(THIS_SUGAR_SYMBOL, "", next_arg)
                                        function_alias = get_method_completion_alias(function_name, function_args_list, is_inherited)
                                        function_insertion = get_method_completion_insertion(function_name, function_args_list)
                                        function_completion = (function_alias, function_insertion)
                                        if function_completion not in function_completions:
                                            function_completions.append(function_completion)
                                    else:
                                        function_args_list = []
                                        if function_args_string:
                                            function_args_list = function_args_string.split(",")
                                        for i in range(len(function_args_list)):
                                            # Check if it starts with @ -- this indicates an auto-set class variable
                                            next_arg = function_args_list[i]
                                            next_arg = next_arg.strip()
                                            if next_arg.startswith(THIS_SUGAR_SYMBOL):
                                                # Clean it up...
                                                next_arg = re.sub(THIS_SUGAR_SYMBOL, "", next_arg)
                                                next_arg = re.sub("[^a-zA-Z0-9_$].*", "", next_arg)
                                                if show_private or not is_member_excluded(next_arg, member_exclusion_regexes):
                                                    prop_completion_alias = get_property_completion_alias(next_arg, is_inherited)
                                                    prop_completion_insertion = get_property_completion_insertion(next_arg)
                                                    prop_completion = (prop_completion_alias, prop_completion_insertion)
                                                    if prop_completion not in property_completions:
                                                        property_completions.append(prop_completion)
                                        inside_constructor = True
                                        constructor_indentation = get_indentation_size(next_row)
                    else:
                        # Indentation limit hit. We're not in the class anymore.
                        break

    completions = property_completions + function_completions
    completion_tuple = (class_found, completions, extended_class)
    return completion_tuple


def get_class_from_end_of_chain(dot_operation_chain):
    class_at_end = dot_operation_chain
    next_period_index = class_at_end.find(PERIOD_OPERATOR)
    while next_period_index >= 0:
        class_at_end = class_at_end[(next_period_index + 1):]
        class_at_end.strip()
        next_period_index = class_at_end.find(PERIOD_OPERATOR)
    if len(class_at_end) == 0:
        class_at_end = None
    return class_at_end


def collect_static_completions_from_file(file_lines, class_name, is_inherited, member_exclusion_regexes, show_private):

    completions = []
    extended_class = None
    class_found = False

    property_completions = []
    function_completions = []

    class_and_extends_regex = CLASS_REGEX_WITH_EXTENDS % class_name

    # Find class in file lines
    match_tuple = get_positions_of_regex_match_in_file(file_lines, class_and_extends_regex)
    if match_tuple:
        class_found = True
        row = match_tuple[0]
        match = match_tuple[2]

        extended_class = match.group(3)
        if extended_class:
            # Clean it up.
            next_period_index = extended_class.find(PERIOD_OPERATOR)
            while next_period_index >= 0:
                extended_class = extended_class[(next_period_index + 1):]
                extended_class.strip()
                next_period_index = extended_class.find(PERIOD_OPERATOR)
            if len(extended_class) == 0:
                extended_class = None

        # If anything is equal to this after the first line, stop looking.
        # At that point, the class definition has ended.
        indentation_size = get_indentation_size(file_lines[row])

        # Let's dig for some info on this class!
        if row + 1 < len(file_lines):

            previous_indentation = -1

            for row_index in range(row + 1, len(file_lines)):
                next_row = file_lines[row_index]
                next_indentation = get_indentation_size(next_row)
                # print str(next_indentation) + ": " + next_row
                if next_indentation >= 0:
                    if next_indentation > indentation_size:
                        # print "Next: " + str(next_indentation) + ", Prev: " + str(previous_indentation)
                        # Haven't found anything yet...
                        # Look for class-level definitions...
                        # If current line indentation is greater than previous indentation, we're in a definition
                        if next_indentation > previous_indentation and previous_indentation >= 0:
                            pass
                        # Otherwise, save this indentation and examine the current line, as it's class-level
                        else:
                            previous_indentation = next_indentation
                            function_regex = STATIC_FUNCTION_REGEX
                            match = re.search(function_regex, next_row)
                            if match:
                                function_name = match.group(4)
                                if show_private or not is_member_excluded(function_name, member_exclusion_regexes):
                                    function_args_string = match.group(6)
                                    function_args_list = []
                                    if function_args_string:
                                        function_args_list = function_args_string.split(",")
                                    for i in range(len(function_args_list)):
                                        # Fix each one up...
                                        next_arg = function_args_list[i]
                                        next_arg = next_arg.strip()
                                        next_arg = re.sub("[^a-zA-Z0-9_$].*", "", next_arg)
                                        function_args_list[i] = next_arg
                                    function_alias = get_method_completion_alias(function_name, function_args_list, is_inherited)
                                    function_insertion = get_method_completion_insertion(function_name, function_args_list)
                                    function_completion = (function_alias, function_insertion)
                                    if function_completion not in function_completions:
                                        function_completions.append(function_completion)
                            else:
                                # Look for static assignment
                                assignment_regex = STATIC_ASSIGNMENT_REGEX
                                match = re.search(assignment_regex, next_row)
                                if match:
                                    prop = match.group(3)
                                    if show_private or not is_member_excluded(prop, member_exclusion_regexes):
                                        prop_completion_alias = get_property_completion_alias(prop, is_inherited)
                                        prop_completion_insertion = get_property_completion_insertion(prop)
                                        prop_completion = (prop_completion_alias, prop_completion_insertion)
                                        if prop_completion not in property_completions:
                                            property_completions.append(prop_completion)
                    else:
                        # Indentation limit hit. We're not in the class anymore.
                        break

    completions = property_completions + function_completions
    completion_tuple = (class_found, completions, extended_class)
    return completion_tuple


def get_property_completion_alias(property_name, is_inherited=False):
    indicator = PROPERTY_INDICATOR
    if is_inherited:
        indicator = INHERITED_INDICATOR + indicator
    completion_string = indicator + " " + property_name
    return completion_string


def get_property_completion_insertion(property_name):
    completion_string = property_name
    completion_string = re.sub("[$]", "\$", completion_string)
    return completion_string


def get_property_completion_tuple(property_name, property_name_insertion, is_inherited=False):
    completion_tuple = (get_property_completion_alias(property_name, is_inherited), get_property_completion_insertion(property_name_insertion))
    return completion_tuple


def get_method_completion_alias(method_name, args, is_inherited=False):
    indicator = METHOD_INDICATOR
    if is_inherited:
        indicator = INHERITED_INDICATOR + indicator
    completion_string = indicator + " " + method_name + "("
    for i in range(len(args)):
        completion_string = completion_string + args[i]
        if i < len(args) - 1:
            completion_string = completion_string + ", "
    completion_string = completion_string + ")"
    return completion_string


def get_method_completion_insertion(method_name, args):

    no_parens = False

    completion_string = re.sub("[$]", "\$", method_name)

    if len(args) == 1:
        function_match = re.search(r".*?[=\-]>.*", args[0])
        if function_match:
            no_parens = True

    if no_parens:
        completion_string = completion_string + " "
    else:
        completion_string = completion_string + "("

    for i in range(len(args)):
        escaped_arg = re.sub("[$]", "\$", args[i])
        completion_string = completion_string + "${" + str(i + 1) + ":" + escaped_arg + "}"
        if i < len(args) - 1:
            completion_string = completion_string + ", "

    if not no_parens:
        completion_string = completion_string + ")"

    return completion_string


def get_method_completion_tuple(method_name, method_name_insertion, arg_names, arg_insertions, is_inherited=False):
    completion_tuple = (get_method_completion_alias(method_name, arg_names, is_inherited), get_method_completion_insertion(method_name_insertion, arg_insertions))
    return completion_tuple


def get_view_contents(view):
    contents = ""
    start = 0
    end = view.size() - 1
    if end > start:
        entire_doc_region = sublime.Region(start, end)
        contents = view.substr(entire_doc_region)
    return contents


def convert_file_contents_to_lines(contents):
    lines = contents.split("\n")
    count = len(lines)
    for i in range(count):
        # Don't add to the last one--that would put an extra \n
        if i < count - 1:
            lines[i] = lines[i] + "\n"
    return lines


def get_view_content_lines(view):
    return convert_file_contents_to_lines(get_view_contents(view))


def is_autocomplete_trigger(text):
    trigger = False
    trigger = trigger or text == THIS_SUGAR_SYMBOL
    trigger = trigger or text == PERIOD_OPERATOR
    return trigger


def is_member_excluded(member, exclusion_regexes):
    excluded = False
    for next_exclusion_regex in exclusion_regexes:
        if re.search(next_exclusion_regex, member):
            excluded = True
    return excluded

########NEW FILE########
