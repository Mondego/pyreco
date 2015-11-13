__FILENAME__ = path_helper
import sublime
import os
from os import path

class PathHelper(object):
	def file_exists(file_name, window):
		is_legal = False
		
		if path.isfile(file_name):
			is_legal = True
		elif path.isfile(path.join(window.folders()[0], file_name)):
			file_name = path.join(window.folders()[0], file_name)
			is_legal = True

		return is_legal

	def get_file(command, window):
		is_legal = False
		file_name = ""
		parts = command.split(" ")
		arguments = []

		for part in parts:
			if is_legal:
				arguments.append(part)
				continue

			elif file_name == "":
				file_name = part
			else:
				file_name = " ".join([file_name,part])

			# I tried to DRY here by just using the function file_exists but that somehow broke everything.
			if path.isfile(file_name):
				is_legal = True
			elif path.isfile(path.join(window.folders()[0], file_name)):
				file_name = path.join(window.folders()[0], file_name)
				is_legal = True

		return is_legal, file_name, arguments

	def get_pwd(file_name):
		return path.split(file_name)[0]

	def is_same_path(first, second):
		return path.abspath(first) == path.abspath(second)

	def get_sublime_require():
		return os.path.join(sublime.packages_path(), "Ruby Debugger", "sublime_debug_require.rb")

	def get_ruby_version_discoverer():
		return os.path.join(sublime.packages_path(), "Ruby Debugger", "ruby_version_discoverer.rb")

########NEW FILE########
__FILENAME__ = view_helper
import sublime
from ..interfaces.debugger_model import DebuggerModel
from .path_helper import PathHelper

class ViewHelper(object):
	def region_in_line(region, line):
		return line.begin() <= region.begin() and line.end() >= region.end()

	def get_lines(view, regions):
		file_lines = view.lines(sublime.Region(0, view.size()))
		lines = []
		for line in file_lines:
			line_number = file_lines.index(line)
			lines += [line_number for region in regions if ViewHelper.region_in_line(region, line)]

		return lines

	def init_debug_layout(window, debug_views):
		window.set_layout({"cols" : [0,0.5,1], "rows":[0,0.7,1], "cells":[[0,0,2,1],[0,1,1,2],[1,1,2,2]]})

		for view in window.views():
			if view.name() in debug_views.keys():
				debug_views[view.name()] = view
				view.set_read_only(False)
				view.run_command("erase_all")
				view.set_read_only(True)
			elif view not in window.views_in_group(0):
				window.set_view_index(view, 0, len(window.views_in_group(0)))

		groups = [0,0]
		current_group = 0
		for view_name in debug_views.keys():
			view = debug_views[view_name]
			if view == None:
				view = window.new_file()
				view.set_scratch(True)
				view.set_read_only(True)
				view.set_name(view_name)
				view.settings().set('word_wrap', False)
				debug_views[view_name] = view

			window.set_view_index(view, current_group + 1, groups[current_group])
			groups[current_group] += 1
			current_group = (current_group + 1) % 2

		window.focus_group(0)

	def reset_debug_layout(window, debug_views):
		for view in window.views():
			if view.name() in debug_views.keys():
				window.focus_view(view)
				window.run_command("close_file")

		window.set_layout({"cols" : [0,1], "rows":[0,1], "cells":[[0,0,1,1]]})

	def set_cursor(window, file_name, line_number):
		view = window.open_file(file_name)
		while view.is_loading():
			pass
		view.add_regions("debugger", [view.lines(sublime.Region(0, view.size()))[line_number-1]], "lineHighlight", "")
		view.show(view.text_point(line_number-1,0))

		if view not in window.views_in_group(0):
			window.set_view_index(view, 0, len(window.views_in_group(0)))

	def replace_content(window, view, new_content, line_to_show, should_append):
		view.set_read_only(False)
		if not should_append:
			view.run_command('erase_all')

		view.run_command('append', {'characters': new_content})
		view.set_read_only(True)
		if not line_to_show:
			line_to_show = len(view.lines(sublime.Region(0, view.size())))
		view.show(view.text_point(line_to_show-1, 0))

		if view.name() not in DebuggerModel.REFRESHABLE_DATA:
			ViewHelper.move_to_front(window, view)

	def get_current_cursor(window, file_name):
		for view in window.views():
			if PathHelper.is_same_path(view.file_name(), file_name):
				return ViewHelper.get_lines(view, view.sel())[0]

		return None

	def move_to_front(window, debug_view):
		current_active = window.active_view()
		active_group = window.views_in_group(window.active_group())

		for group in range(0, window.num_groups()):
			if debug_view in window.views_in_group(group):
				if debug_view != window.active_view_in_group(group):
					window.focus_view(debug_view)
					if debug_view not in active_group:
						window.focus_view(current_active)

	def sync_breakpoints(window):
		for view in window.views():
			view.run_command("toggle_breakpoint", {"mode":"refresh"})


########NEW FILE########
__FILENAME__ = breakpoint
class Breakpoint(object):
	"""Represent a breakpoint"""
	def __init__(self, file_name, line_number, condition):
		super(Breakpoint, self).__init__()
		self.file_name = file_name
		self.line_number = line_number
		self.condition = condition
		
########NEW FILE########
__FILENAME__ = debugger
from abc import ABCMeta, abstractmethod

class Debugger(object):
	__metaclass__ = ABCMeta

	def __init__(self, debug_view):
		self.debug_view = debug_view

	def signal_position_changed(self, file_name, line_number):
		'''
		Raised when debugger change position
		'''
		self.debug_view.set_cursor(file_name, line_number)

	def signal_text_result(self, result, reason):
		'''
		Raised when command result is returned (Expression or Threads command for example)
		'''
		self.debug_view.add_text_result(result, reason)

	def signal_process_ended(self):
		self.debug_view.stop()

	@abstractmethod
	def run_command(self, command_type, **args):
		pass
########NEW FILE########
__FILENAME__ = debugger_connector
from abc import ABCMeta, abstractmethod

try:
	from .debugger_model import DebuggerModel
except:
	from debugger_model import DebuggerModel

class DebuggerConnector(object):
	"""Connector used to communication with debugged process"""
	__metaclass__ = ABCMeta

	def __init__(self, debugger):
		super(DebuggerConnector, self).__init__()
		self.debugger = debugger

	def log_message(self, message):
		self.debugger.signal_text_result(message, DebuggerModel.DATA_OUTPUT)

	@abstractmethod
	def start(self, current_directory, file_name, *args):
		'''
		Start and attach the process
		'''
		pass

	@abstractmethod
	def send_data(self, command, reason):
		'''
		Send command to the debugger (reason parameters is just for logging)
		'''

	@abstractmethod
	def send_without_outcome(self, command):
		'''
		Send command to the debugger when no result is returned
		'''

	@abstractmethod
	def send_input(self, command):
		'''
		Send text to the process's STDIN
		'''

	@abstractmethod
	def send_for_result(self, command, reason):
		'''
		Send command to the debugger and when result returned
		signal result with the given reason
		'''

	@abstractmethod
	def send_with_result(self, command, reason, prefix):
		'''
		Send command to the debugger and when result returned
		signal result with the given reason and prefix
		'''

	@abstractmethod
	def stop(self):
		'''
		Stop the debugger process
		'''

########NEW FILE########
__FILENAME__ = debugger_model
class DebuggerModel(object):
	"""Represent data model for debugger"""

	# Debugging data types
	DATA_WATCH = "Watch"
	DATA_IMMEDIATE = "Immediate"
	DATA_OUTPUT = "Output"
	DATA_BREAKPOINTS = "Breakpoints"
	DATA_LOCALS = "Locals"
	DATA_THREADS = "Threads"
	DATA_STACK = "Stack"

	COMMAND_DEBUG_LAYOUT = "show_debug_windows"
	COMMAND_RESET_LAYOUT = "hide_debug_windows"

	# Debugging controlling
	COMMAND_START = "start_debug"
	COMMAND_START_CURRENT_FILE = "start_debug_current_file"
	COMMAND_START_RAILS = "start_rails"
	COMMAND_STOP = "stop_debug"
	COMMAND_INTERRUPT = "interrupt"

	# Debuggin cursor movement
	COMMAND_STEP_OVER = "step_over"
	COMMAND_STEP_INTO = "step_into"
	COMMAND_STEP_UP = "step_up"
	COMMAND_STEP_DOWN = "step_down"
	COMMAND_GO_TO = "go_to"
	COMMAND_CONTINUTE = "continute"
	COMMAND_JUMP = "jump"

	# Debugging information
	COMMAND_GET_LOCATION = "get_location"
	COMMAND_GET_STACKTRACE = "get_stacktrace"
	COMMAND_GET_LOCALS = "get_locals"
	COMMAND_GET_THREADS = "get_threads"
	COMMAND_GET_EXPRESSION = "get_expression"
	COMMAND_GET_BREAKPOINTS = "get_breakpoints"

	COMMAND_SEND_INPUT = "send_input"
	COMMAND_SET_BREAKPOINT = "set_breakpoint"
	COMMAND_CLEAR_BREAKPOINTS = "clear_breakpoints"

	COMMAND_ADD_WATCH = "add_watch"
	COMMAND_GET_WATCH = "get_watch"

	REFRESHABLE_DATA = [DATA_WATCH, DATA_THREADS, DATA_STACK, DATA_LOCALS, DATA_BREAKPOINTS]

	REFRESHABLE_COMMANDS = [COMMAND_GET_THREADS, COMMAND_GET_STACKTRACE, COMMAND_GET_LOCALS, COMMAND_GET_BREAKPOINTS]

	APPENDABLE_DATA = [DATA_IMMEDIATE, DATA_OUTPUT]

	STARTERS_COMMANDS = [COMMAND_DEBUG_LAYOUT, COMMAND_RESET_LAYOUT, COMMAND_START_RAILS, COMMAND_START, COMMAND_START_CURRENT_FILE]
	COMMANDS = [COMMAND_DEBUG_LAYOUT, COMMAND_RESET_LAYOUT, COMMAND_START_RAILS, COMMAND_INTERRUPT, COMMAND_START_CURRENT_FILE, COMMAND_GO_TO, COMMAND_ADD_WATCH, COMMAND_GET_WATCH, COMMAND_START, COMMAND_STOP, COMMAND_SEND_INPUT, COMMAND_STEP_OVER, COMMAND_STEP_INTO, COMMAND_STEP_UP, COMMAND_STEP_DOWN, COMMAND_CONTINUTE, COMMAND_JUMP, COMMAND_GET_LOCATION, COMMAND_GET_STACKTRACE, COMMAND_GET_LOCALS, COMMAND_GET_THREADS, COMMAND_GET_EXPRESSION, COMMAND_GET_BREAKPOINTS, COMMAND_SET_BREAKPOINT, COMMAND_CLEAR_BREAKPOINTS]
	MOVEMENT_COMMANDS = [COMMAND_CONTINUTE, COMMAND_STEP_OVER, COMMAND_STEP_INTO, COMMAND_STEP_UP, COMMAND_STEP_DOWN, COMMAND_JUMP]
	BREAKPOINTS = []

	def __init__(self, debugger):
		super(DebuggerModel, self).__init__()
		self.debugger = debugger
		self.data = {}
		self.data[DebuggerModel.DATA_WATCH] = []
		self.data[DebuggerModel.DATA_IMMEDIATE] = ""
		self.data[DebuggerModel.DATA_OUTPUT] = ""
		self.data[DebuggerModel.DATA_BREAKPOINTS] = ""
		self.data[DebuggerModel.DATA_LOCALS] = ""
		self.data[DebuggerModel.DATA_THREADS] = ""
		self.data[DebuggerModel.DATA_STACK] = ""
		self.file_name = None
		self.line_number = None

	def get_data(self):
		return self.data

	def set_cursor(self, file_name, line_number):
		if self.file_name == file_name and self.line_number == line_number:
			return False

		self.file_name = file_name
		self.line_number = line_number

		self.referesh_data()

		return True

	def clear_cursor(self):
		self.file_name = None
		self.line_number = None

	def update_data(self, data_type, new_value):
		line_to_show = None
		should_append = False

		if data_type not in self.data.keys():
			return False

		if new_value == self.data[data_type]:
			return False

		if data_type == DebuggerModel.DATA_WATCH:
			self.update_watch_expression(new_value[0], new_value[1])
			return self.watch_to_str(), line_to_show, should_append
		elif data_type == DebuggerModel.DATA_IMMEDIATE:
			self.data[data_type] += new_value[0]+" => "+ new_value[1] + '\n'
			self.referesh_data()
		elif data_type in DebuggerModel.APPENDABLE_DATA:
			should_append = True
			if not new_value.endswith('\n'):
				new_value = new_value + '\n'
			new_value = new_value.replace("\r\n", '\n')
			self.data[data_type] += new_value
			return new_value, line_to_show, should_append
		else:
			self.data[data_type] = new_value

		if data_type == DebuggerModel.DATA_STACK:
			for idx, line in enumerate(self.data[data_type].splitlines()):
				if line.startswith("-->"):
					line_to_show = idx

		return self.data[data_type], line_to_show, should_append

	def referesh_data(self):
		# Refresh autoreferesh data
		for command in DebuggerModel.REFRESHABLE_COMMANDS:
			self.debugger.run_command(command)

		# Refresh watch
		for watch_exp in self.data[DebuggerModel.DATA_WATCH]:
			self.debugger.run_result_command(DebuggerModel.COMMAND_GET_WATCH, watch_exp[0], watch_exp[0])

	def update_watch_expression(self, watch_exp, watch_value):
		for watch in self.data[DebuggerModel.DATA_WATCH]:
			if watch_exp == watch[0]:
				watch[1] = watch_value

	def add_watch(self, watch_expression):
		self.data[DebuggerModel.DATA_WATCH].append([watch_expression, ""])
		self.debugger.run_result_command(DebuggerModel.COMMAND_GET_WATCH, watch_expression, watch_expression)

	def watch_to_str(self):
		result = []
		for exp, value in self.data[DebuggerModel.DATA_WATCH]:
			result.append(exp + " = " + value)

		return '\n'.join(result)

	def get_current_file(self):
		return self.file_name

	def get_all_breakpoints(self):
		breakpoints = []
		for breakpoint in DebuggerModel.BREAKPOINTS:
			breakpoints.append((breakpoint.file_name, breakpoint.line_number, breakpoint.condition))

		return breakpoints

########NEW FILE########
__FILENAME__ = debug_command
from abc import ABCMeta, abstractmethod

class DebugCommand(object):
	__metaclass__ = ABCMeta

	"""Represent command that use while debugging"""
	def __init__(self):
		super(DebugCommand, self).__init__()

	@abstractmethod
	def execute(self, debugger_controller, *args):
		pass
		
########NEW FILE########
__FILENAME__ = ruby_custom_debug_command
from ..interfaces import *

class RubyCustomDebugCommand(DebugCommand):
	"""Represent send start debug command"""
	def __init__(self, lambda_command):
		super(RubyCustomDebugCommand, self).__init__()
		self.lambda_command = lambda_command

	def execute(self, debugger_constroller, *args):
		self.lambda_command(debugger_constroller, *args)

########NEW FILE########
__FILENAME__ = ruby_debugger
import sublime
import re
from ..interfaces import *
from .ruby_debugger_connector import RubyDebuggerConnector
from .ruby_debug_command import RubyDebugCommand
from .ruby_custom_debug_command import RubyCustomDebugCommand

class RubyDebugger(Debugger):
	PROTOCOL = {"1.9.3": {"end_regex":r"PROMPT \(rdb:\d+\) ",
							 "line_regex":r"^=>\s+?(\d+)  .*$",
							 "file_regex":r"\[-*\d+, \d+\] in (.*)$"},
					"2.0.0": {"end_regex":r"PROMPT \(byebug\) ",
							  "line_regex":r"^=>\s+?(\d+): .*$",
							  "file_regex":r"\[-*\d+, \d+\] in (.*)$"}}

	# Define protocol
	COMMANDS = { DebuggerModel.COMMAND_GET_LOCATION:RubyDebugCommand("l=", "GetLocation"),
				 DebuggerModel.COMMAND_GET_STACKTRACE:RubyDebugCommand("where", DebuggerModel.DATA_STACK, True),
				 DebuggerModel.COMMAND_GET_LOCALS:RubyDebugCommand("info local", DebuggerModel.DATA_LOCALS, True),
				 DebuggerModel.COMMAND_GET_THREADS:RubyDebugCommand("thread l", DebuggerModel.DATA_THREADS, True),
				 DebuggerModel.COMMAND_GET_EXPRESSION:RubyDebugCommand("eval", DebuggerModel.DATA_IMMEDIATE, True),
				 DebuggerModel.COMMAND_GET_BREAKPOINTS:RubyDebugCommand("info break", DebuggerModel.DATA_BREAKPOINTS, True),

				 DebuggerModel.COMMAND_SEND_INPUT:RubyCustomDebugCommand(lambda debugger_constroller, *args: debugger_constroller.send_input(*args)),
				 DebuggerModel.COMMAND_START:RubyCustomDebugCommand(lambda debugger_constroller, *args: debugger_constroller.start(*args)),
				 DebuggerModel.COMMAND_STOP:RubyCustomDebugCommand(lambda debugger_constroller, *args: debugger_constroller.stop()),

				 DebuggerModel.COMMAND_GET_WATCH:RubyCustomDebugCommand(lambda debugger_constroller, prefix, expression: debugger_constroller.send_with_result("eval " + expression, DebuggerModel.DATA_WATCH, prefix)),
				 DebuggerModel.COMMAND_GET_EXPRESSION:RubyCustomDebugCommand(lambda debugger_constroller, prefix, expression: debugger_constroller.send_with_result("eval " + expression, DebuggerModel.DATA_IMMEDIATE, prefix)),

				 DebuggerModel.COMMAND_SET_BREAKPOINT:RubyCustomDebugCommand(lambda debugger_constroller, location: debugger_constroller.send_control_command("b " + location)),
				 DebuggerModel.COMMAND_CLEAR_BREAKPOINTS:RubyCustomDebugCommand(lambda debugger_constroller: debugger_constroller.send_control_command("delete")),
				 DebuggerModel.COMMAND_INTERRUPT:RubyCustomDebugCommand(lambda debugger_constroller: debugger_constroller.send_control_command("interrupt")),

				 DebuggerModel.COMMAND_STEP_OVER:RubyDebugCommand("n", "step_over"),
				 DebuggerModel.COMMAND_STEP_INTO:RubyDebugCommand("s", "step_into"),
				 DebuggerModel.COMMAND_STEP_UP:RubyDebugCommand("up", "step_up"),
				 DebuggerModel.COMMAND_STEP_DOWN:RubyDebugCommand("down", "step_down"),
				 DebuggerModel.COMMAND_CONTINUTE:RubyDebugCommand("c", "continue"),
				 DebuggerModel.COMMAND_JUMP:RubyDebugCommand("jump", "jump") }

	def __init__(self, debugger_view, use_bundler):
		super(RubyDebugger, self).__init__(debugger_view)
		self.connector = RubyDebuggerConnector(self, use_bundler)

	def run_command(self, command_type, *args):
		RubyDebugger.COMMANDS[command_type].execute(self.connector, *args)

	def run_result_command(self, command_type, prefix, *args):
		RubyDebugger.COMMANDS[command_type].execute(self.connector, prefix, *args)

	def match_ending(self, ruby_version, line):
		return re.match(RubyDebugger.PROTOCOL[ruby_version]["end_regex"], line)

	def match_line_cursor(self, ruby_version, line):
		return re.match(RubyDebugger.PROTOCOL[ruby_version]["line_regex"], line)

	def match_file_cursor(self, ruby_version, line):
		return re.match(RubyDebugger.PROTOCOL[ruby_version]["file_regex"], line)

########NEW FILE########
__FILENAME__ = ruby_debugger_connector
import os.path
import sublime
import time
import traceback
import socket
import subprocess
from io import StringIO
from threading import Thread
import queue
from queue import Queue
from ..interfaces import *
from ..helpers import *

class RubyDebuggerConnector(DebuggerConnector):
	"""Connector used to communication with debugged process"""
	def __init__(self, debugger, use_bundler):
		super(RubyDebuggerConnector, self).__init__(debugger)
		self.debugger = debugger
		self.process = None
		self.client = None
		self.control_client = None
		self.connected = False
		self.ruby_version = None
		self.use_bundler = use_bundler

	def start(self, current_directory, file_name, *args):
		'''
		Start and attach the process
		'''
		# Vaildate ruby versions and gem version
		if not self.validation_environment():
			return

		# Start the debuggee process
		self.start_process(current_directory, file_name, args)

		# Try to connect to process with sockets
		if not self.connect_debugger():
			return

		# Start read from socket, output, errors
		self.errors_reader = self.start_tread(lambda stream = self.process.stderr: self.output_thread(stream))
		self.outputer = self.start_tread(lambda stream = self.process.stdout: self.output_thread(stream))
		self.reader = self.start_tread(self.reader_thread)

	def validation_environment(self):
		try:
			if os.name == "posix":
				# On Unix using rvm and bash
				rvm_load = "[[ -s \"$HOME/.rvm/scripts/rvm\" ]] 2> /dev/null ; source \"$HOME/.rvm/scripts/rvm\" 2> /dev/null"
				validate_command = rvm_load + " ; exec ruby '" + PathHelper.get_ruby_version_discoverer()+"'"
				self.ruby_version = subprocess.Popen(["bash", "-c", validate_command], stdout=subprocess.PIPE).communicate()[0].splitlines()
			else:
				# On Windows not using shell, so the proces is not visible to the user
				process_params = ["ruby", PathHelper.get_ruby_version_discoverer()]
				self.ruby_version = subprocess.Popen(process_params, stdout=subprocess.PIPE).communicate()[0].splitlines()
		except Exception as ex:
			self.log_message("Could not start process: "+str(ex)+'\n')
			return False

		self.ruby_version[0] = self.ruby_version[0].decode("UTF-8")
		self.ruby_version[1] = self.ruby_version[1].decode("UTF-8")

		if self.ruby_version[1] == "UNSUPPORTED":
			self.log_message("Ruby version: "+self.ruby_version[0]+" is not supported.")
			return False

		return True

	def start_process(self, current_directory, file_name, args):
		requires = " '-r"+PathHelper.get_sublime_require()+"'"
		directory = " '-C"+current_directory+"'"
		program = " '"+file_name+"' "+" ".join(args)

		# Case of running rails
		if self.use_bundler:
				requires = " '-rbundler/setup'" + requires
				directory = " '-C"+sublime.active_window().folders()[0]+"'"

		# Initialize params acourding to OS type
		if os.name == "posix":
			# On Unix using exec and shell to get environemnt variables of ruby version
			rvm_load = "[[ -s \"$HOME/.rvm/scripts/rvm\" ]] 2> /dev/null; source \"$HOME/.rvm/scripts/rvm\" 2> /dev/null"
			process_command = rvm_load + " ; exec ruby"+directory+requires+program
			process_params = ["bash", "-c", "\""+process_command+"\""]
			self.process = subprocess.Popen(" ".join(process_params), stdin = subprocess.PIPE, stderr = subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1, shell=True, cwd=sublime.active_window().folders()[0])
		else:
			# On Windows not using shell, so the proces is not visible to the user
			process_params = ["ruby", "-C"+current_directory, "-r"+PathHelper.get_sublime_require(), file_name]
			process_params += args
			self.process = subprocess.Popen(process_params, stdin = subprocess.PIPE, stderr = subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1, shell=False)

	def connect_debugger(self):
		self.data = StringIO()
		self.requests = Queue()
		self.requests.put({"signal":False, "reason":"get_location"})

		self.connected = False
		self.log_message("Connecting... ")
		for i in range(1,9):
			try:
				self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.client.connect(("localhost", 8989))
				self.control_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.control_client.connect(("localhost", 8990))
				self.connected = True
				self.log_message("Connected"+'\n')
				break
			except Exception as ex:
				if i == 8:
					self.log_message("Connection could not be made: "+str(ex)+'\n')
					return False
				else:
					time.sleep(1)

		return True

	def start_tread(self, threads_method):
		thread  = Thread(target=threads_method)
		thread.daemon = True
		thread.start()
		return thread

	def output_thread(self, stream):
		# Always read stream`
		try:
			while True:
				bytes = stream.readline()

				if len(bytes) == 0:
					break

				result = str(bytes, "UTF-8")
				self.log_message(result)
		except Exception:
			pass

	def reader_thread(self):
		# Alwast read stream
		try:
			while True:
				bytes = self.client.recv(4096)

				if len(bytes) == 0:
					break

				result = str(bytes, "UTF-8")
				self.data.write(result)
				self.data.flush()
				# self.log_message(result)

				if self.has_end_stream():
					self.handle_response()

		except Exception as ex:
			if self.connected:
				self.log_message("Debugger exception: "+str(ex)+'\n'+" StackTrace: "+traceback.format_exc())
				self.connected = False

		self.outputer.join()
		self.errors_reader.join()

		# Signal that the process has exited
		self.log_message("Debugger stopped")
		self.debugger.signal_process_ended()

	def handle_response(self):
		results = self.split_by_results()
		next_result = results.pop()

		for result in results:
			if result:
				pass

			file_name, line_number = self.get_current_position()

			# Check wheather position was updated
			if file_name != "" and not PathHelper.is_same_path(PathHelper.get_sublime_require(), file_name):
				self.debugger.signal_position_changed(file_name, line_number)
				# self.log_message("New position: "+file_name+":"+str(line_number))

			try:
				request = self.requests.get_nowait()
				# self.log_message("Pop request: "+str(request)+", current queue size: "+str(self.requests.qsize())+", request result:"+result)

				# Check if should return the result
				if request["signal"]:
					prefix = request.get("prefix")
					data = result.strip()

					if prefix:
						data = (prefix, data)

					# Return result
					self.debugger.signal_text_result(data, request["reason"])
				else:
					pass

				if PathHelper.is_same_path(PathHelper.get_sublime_require(), file_name):
					self.debugger.run_command(DebuggerModel.COMMAND_CONTINUTE)
			except queue.Empty:
				pass

		self.data = StringIO()
		self.data.write(next_result)

	def send_data(self, command, reason):
		self.requests.put({"signal": False, "reason": reason, "command": command})
		self.send_data_internal(command)

	def send_without_outcome(self, command):
		self.send_data_internal(command)

	def send_input(self, command):
		self.process.stdin.write(bytes(command+'\n',"UTF-8"))
		self.process.stdin.flush()

	def send_control_command(self, command):
		if not self.connected:
			pass

		try:
			self.control_client.sendall(bytes(command+'\n', 'UTF-8'))
		except Exception as e:
			if self.connected:
				self.log_message("Failed communicate with process ("+command+"): "+str(e))

	def send_data_internal(self, command):
		if not self.connected:
			return

		try:
			self.client.sendall(bytes(command+'\n', 'UTF-8'))
		except Exception as e:
			if self.connected:
				self.log_message("Failed communicate with process ("+command+"): "+str(e))

	def send_for_result(self, command, reason):
		self.requests.put({"signal": True, "reason": reason, "command": command})
		self.send_data_internal(command)

	def send_with_result(self, command, reason, prefix):
		self.requests.put({"signal": True, "prefix": prefix, "reason": reason, "command": command})
		self.send_data_internal(command)

	def split_by_results(self):
		result = [""]
		for line in self.get_lines():
			if self.debugger.match_ending(self.ruby_version[0], line):
				result.insert(len(result), "")
			else:
				result[len(result)-1] += line + '\n'

		return result

	def has_end_stream(self):
		end_of_stream = False
		for line in self.get_lines():
				if self.debugger.match_ending(self.ruby_version[0], line):
					end_of_stream = True;

		return end_of_stream

	def get_current_position(self):
		current_line = -1
		current_file = ""
		end_of_stream = False

		for line in self.get_lines():
			match = self.debugger.match_line_cursor(self.ruby_version[0], line)

			if match:
				current_line = match.groups()[0]

			match = self.debugger.match_file_cursor(self.ruby_version[0], line)
			if match:
				current_file = match.groups()[0]

		return current_file, int(current_line)

	def get_lines(self):
		return self.data.getvalue().split('\n')

	def stop(self):
		self.connected = False
		self.log_message("Stopping...")
		self.send_control_command("kill")
		if self.process:
			self.process.kill()
		self.process = None

########NEW FILE########
__FILENAME__ = ruby_debug_command
from ..interfaces import *

class RubyDebugCommand(DebugCommand):
	"""Represent a command for debugger"""
	def __init__(self, command_strings, reason, is_signal_result = False, is_returning_data = True):
		super(RubyDebugCommand, self).__init__()
		self.commands = command_strings
		self.reason = reason
		self.is_signal_result = is_signal_result
		self.is_returning_data = is_returning_data

	def execute(self, debugger_constroller, *args):
		if args:
			pass
		if self.is_signal_result:
			if isinstance(self.commands, list):
				self.execute_list(debugger_constroller, self.commands.copy(), self.reason, lambda command,reason: debugger_constroller.send_for_result(command, reason))
			else:
				debugger_constroller.send_for_result(self.command_with_args(self.commands, *args), self.reason)
		elif self.is_returning_data:
			if isinstance(self.commands, list):
				self.execute_list(debugger_constroller, self.commands.copy(), self.reason, lambda command,reason: debugger_constroller.send_data(command, reason))
			else:
				debugger_constroller.send_data(self.command_with_args(self.commands, *args), self.reason)
		else:
			debugger_constroller.send_without_outcome(self.command_with_args(self.commands, *args))

	def command_with_args(self, command, *args):
		if args:
			for arg in args:
				command += " "+arg

		return command

	def execute_list(self, debugger_constroller, commands, reason, func):
		first_command = commands[0]
		commands.remove(first_command)
		func(first_command, reason)

		for command in commands:
			debugger_constroller.send_without_outcome(command)

########NEW FILE########
__FILENAME__ = debug_command
import sublime, sublime_plugin
from .debugger import *

class DebugCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		super(DebugCommand, self).__init__(window)
		self.debugger = None
		self.debugger_model = None
		self.debug_views = None

	def run(self, command, **args):
		# Allow only known commands
		if command not in DebuggerModel.COMMANDS:
			sublime.message_dialog("Unknown command: "+command)
			return
		# Allow only start command when inactive
		if not self.debugger and command not in DebuggerModel.STARTERS_COMMANDS:
			return

		# Cursor movement commands
		if command == DebuggerModel.COMMAND_JUMP:
			current_line = ViewHelper.get_current_cursor(self.window, self.debugger_model.get_current_file())

			if current_line:
				self.clear_cursor()
				self.debugger.run_command(command, str(current_line+1))
				self.debugger.run_command(DebuggerModel.COMMAND_GET_LOCATION)
		elif command == DebuggerModel.COMMAND_GO_TO:
			file_name = self.debugger_model.get_current_file()
			current_line = ViewHelper.get_current_cursor(self.window, file_name)

			if current_line:
				self.clear_cursor()
				self.debugger.run_command(DebuggerModel.COMMAND_SET_BREAKPOINT, file_name+":"+str(current_line+1))
				self.debugger.run_command(DebuggerModel.COMMAND_CONTINUTE)
				self.register_breakpoints()
		elif command in DebuggerModel.MOVEMENT_COMMANDS:
			self.clear_cursor()
			self.debugger.run_command(command, **args)
			self.debugger.run_command(DebuggerModel.COMMAND_GET_LOCATION)
		# Input commands
		elif command == DebuggerModel.COMMAND_DEBUG_LAYOUT:
			self.show_debugger_layout()
		elif command == DebuggerModel.COMMAND_RESET_LAYOUT:
			if not self.debugger_model:
				self.debugger_model = DebuggerModel(self.debugger)

			if not self.debug_views:
				self.debug_views = dict([(key, None) for key in self.debugger_model.get_data().keys()])

			ViewHelper.reset_debug_layout(self.window, self.debug_views)
		elif command == DebuggerModel.COMMAND_SEND_INPUT:
			self.window.show_input_panel("Enter input", '', lambda input_line: self.on_input_entered(input_line), None, None)
		elif command == DebuggerModel.COMMAND_GET_EXPRESSION:
			self.window.show_input_panel("Enter expression", '', lambda exp: self.on_expression_entered(exp), None, None)
		elif command == DebuggerModel.COMMAND_ADD_WATCH:
			self.window.show_input_panel("Enter watch expression", '', lambda exp: self.on_watch_entered(exp), None, None)
		# Start command
		elif command == DebuggerModel.COMMAND_START_RAILS:
			if PathHelper.file_exists("script/rails", self.window):
				self.start_command("script/rails s")
			elif PathHelper.file_exists("bin/rails", self.window): # Rails 4 support
				self.start_command("bin/rails s")
			else:
				sublime.message_dialog("Cannot find file. Are you sure you're in a rails project?")
		elif command == DebuggerModel.COMMAND_START_CURRENT_FILE:
			self.start_command(self.window.active_view().file_name())
		elif command == DebuggerModel.COMMAND_START:
			self.window.show_input_panel("Enter file name", '', lambda file_name: self.start_command(file_name), None, None)
		# Register breakpoints command
		elif command == DebuggerModel.COMMAND_SET_BREAKPOINT:
			self.register_breakpoints()
		# All othe commands
		else:
			self.debugger.run_command(command)

	def start_command(self, file_name, use_bundler=False):
		is_legal, file_path, arguments = PathHelper.get_file(file_name, self.window)

		if is_legal:
			sublime.set_timeout_async(lambda file_path=file_path,bundle=use_bundler, args=arguments: self.start_command_async(file_path, bundle, *args), 0)
		else:
			sublime.message_dialog("File: " + file_path+" does not exists")

	def start_command_async(self, file_path, use_bundler, *args):
		if self.debugger:
			self.debugger.run_command(DebuggerModel.COMMAND_STOP)

		# Initialize variables
		self.debugger = RubyDebugger(self, use_bundler)
		self.debugger_model = DebuggerModel(self.debugger)

		# Intialize debugger layout
		self.show_debugger_layout()

		# Start debugging
		self.debugger.run_command(DebuggerModel.COMMAND_START, PathHelper.get_pwd(file_path), file_path, *args)

		# Register all breakpoint
		self.register_breakpoints()

	def show_debugger_layout(self):
		if not self.debugger_model:
			self.debugger_model = DebuggerModel(self.debugger)

		self.debug_views = dict([(key, None) for key in self.debugger_model.get_data().keys()])
		ViewHelper.init_debug_layout(self.window, self.debug_views)

	def register_breakpoints(self):
		self.debugger.run_command(DebuggerModel.COMMAND_CLEAR_BREAKPOINTS)
		ViewHelper.sync_breakpoints(self.window)

		for file_name, line_number, condition in self.debugger_model.get_all_breakpoints():
			if condition:
				condition = " if "+condition
			else:
				condition = ""
			self.debugger.run_command(DebuggerModel.COMMAND_SET_BREAKPOINT, file_name+":"+str(line_number)+str(condition))

		# Refresh breakpoints window
		self.debugger.run_command(DebuggerModel.COMMAND_GET_BREAKPOINTS)

	def on_input_entered(self, input_string):
		self.debugger.run_command(DebuggerModel.COMMAND_SEND_INPUT, input_string)

	def on_expression_entered(self, expression):
		self.debugger.run_result_command(DebuggerModel.COMMAND_GET_EXPRESSION, expression, expression)
		ViewHelper.move_to_front(self.window, self.debug_views[DebuggerModel.DATA_IMMEDIATE])

	def on_watch_entered(self, expression):
		self.debugger_model.add_watch(expression)
		ViewHelper.move_to_front(self.window, self.debug_views[DebuggerModel.DATA_WATCH])

	def add_text_result(self, result, reason):
		result = self.debugger_model.update_data(reason, result)

		if result:
			new_data = result[0]
			line_to_show = result[1]
			should_append = result[2]
			ViewHelper.replace_content(self.window, self.debug_views[reason], new_data, line_to_show, should_append)

	def set_cursor(self, file_name, line_number):
		# Updating only if position changed
		if self.debugger_model.set_cursor(file_name, line_number):
			ViewHelper.set_cursor(self.window, file_name, line_number)

	def clear_cursor(self):
		for view in self.window.views():
			view.erase_regions("debugger")

		self.debugger_model.clear_cursor()

	def stop(self):
		self.clear_cursor()
		self.debugger = None

		# ViewHelper.reset_debug_layout(self.window, self.debug_views)

########NEW FILE########
__FILENAME__ = toggle_breakpoint_command
import sublime, sublime_plugin
from .debugger import *

class EraseAllCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.erase(edit, sublime.Region(0, self.view.size()))

class ToggleBreakpointCommand(sublime_plugin.TextCommand):
	def run(self, edit, mode, **args):
		if mode == "clear_all":
			for view in self.view.window().views():
				view.erase_regions("breakpoint")
				DebuggerModel.BREAKPOINTS = []
				self.view.window().run_command("debug", {"command" : "set_breakpoint"})
		elif mode == "normal":
			self.update_breakpoints()
		elif mode == "conditional":
			self.view.window().show_input_panel("Enter condition", '', lambda condition : self.update_breakpoints(condition), None, None)
		elif mode == "refresh":
			self.view.erase_regions("breakpoint")
			self.update_regions(self.view.file_name(), [], "")

	def update_breakpoints(self, condition=None):
		self.view.erase_regions("breakpoint")
		selected_lines = ViewHelper.get_lines(self.view, self.view.sel())
		self.update_regions(self.view.file_name(), selected_lines, condition)
		self.view.window().run_command("debug", {"command" : "set_breakpoint"})

	def update_regions(self, selected_file, selcted_line_numbers, condition):
		current_breakpoints = DebuggerModel.BREAKPOINTS

		unchanged = []
		unchanged_in_selected_file = []
		added = []

		for breakpoint in current_breakpoints:
			was_found = False
			for line_number in selcted_line_numbers:
				if breakpoint.line_number-1 == line_number:
					was_found = True
					break

			if not was_found and breakpoint.file_name == selected_file:
				unchanged_in_selected_file += [breakpoint]

			if not was_found :
				unchanged += [breakpoint]

		for line_number in selcted_line_numbers:
			was_found = False
			for breakpoint in current_breakpoints:
				if breakpoint.line_number-1 == line_number:
					was_found = True
					break

			if not was_found:
				added += [self.create_breakpoint(line_number, condition)]

		self.view.add_regions("breakpoint", self.to_regions(added+unchanged_in_selected_file), "string", "circle", sublime.PERSISTENT)
		DebuggerModel.BREAKPOINTS = added+unchanged

	def create_breakpoint(self, line_number, condition):
		return Breakpoint(self.view.file_name(), line_number+1, condition)

	def create_region(self, breakpoint):
		point = self.view.text_point(breakpoint.line_number-1, 0)
		region = sublime.Region(point, point)
		return region

	def to_regions(self, breakpoints):
		return [self.create_region(breakpoint) for breakpoint in breakpoints]


########NEW FILE########
