__FILENAME__ = ipython_config
# Configuration file for ipython.

c = get_config()

#------------------------------------------------------------------------------
# InteractiveShellApp configuration
#------------------------------------------------------------------------------

# A Mixin for applications that start InteractiveShell instances.
# 
# Provides configurables for loading extensions and executing files as part of
# configuring a Shell environment.
# 
# The following methods should be called by the :meth:`initialize` method of the
# subclass:
# 
#   - :meth:`init_path`
#   - :meth:`init_shell` (to be implemented by the subclass)
#   - :meth:`init_gui_pylab`
#   - :meth:`init_extensions`
#   - :meth:`init_code`

# Execute the given command string.
# c.InteractiveShellApp.code_to_run = ''

# lines of code to run at IPython startup.
# c.InteractiveShellApp.exec_lines = []

# Enable GUI event loop integration ('qt', 'wx', 'gtk', 'glut', 'pyglet',
# 'osx').
# c.InteractiveShellApp.gui = None

# Pre-load matplotlib and numpy for interactive use, selecting a particular
# matplotlib backend and loop integration.
# c.InteractiveShellApp.pylab = None

# If true, an 'import *' is done from numpy and pylab, when using pylab
# c.InteractiveShellApp.pylab_import_all = True

# A list of dotted module names of IPython extensions to load.
# c.InteractiveShellApp.extensions = []

# Run the module as a script.
# c.InteractiveShellApp.module_to_run = ''

# dotted module name of an IPython extension to load.
# c.InteractiveShellApp.extra_extension = ''

# List of files to run at IPython startup.
# c.InteractiveShellApp.exec_files = []

# A file to be run
# c.InteractiveShellApp.file_to_run = ''

#------------------------------------------------------------------------------
# TerminalIPythonApp configuration
#------------------------------------------------------------------------------

# TerminalIPythonApp will inherit config from: BaseIPythonApplication,
# Application, InteractiveShellApp

# Execute the given command string.
# c.TerminalIPythonApp.code_to_run = ''

# The IPython profile to use.
# c.TerminalIPythonApp.profile = u'default'

# Set the log level by value or name.
# c.TerminalIPythonApp.log_level = 30

# Whether to display a banner upon starting IPython.
# c.TerminalIPythonApp.display_banner = True

# lines of code to run at IPython startup.
# c.TerminalIPythonApp.exec_lines = []

# Enable GUI event loop integration ('qt', 'wx', 'gtk', 'glut', 'pyglet',
# 'osx').
# c.TerminalIPythonApp.gui = None

# Pre-load matplotlib and numpy for interactive use, selecting a particular
# matplotlib backend and loop integration.
# c.TerminalIPythonApp.pylab = None

# Suppress warning messages about legacy config files
# c.TerminalIPythonApp.ignore_old_config = False

# Create a massive crash report when IPython encounters what may be an internal
# error.  The default is to append a short message to the usual traceback
# c.TerminalIPythonApp.verbose_crash = False

# If a command or file is given via the command-line, e.g. 'ipython foo.py
# c.TerminalIPythonApp.force_interact = False

# If true, an 'import *' is done from numpy and pylab, when using pylab
# c.TerminalIPythonApp.pylab_import_all = True

# Whether to install the default config files into the profile dir. If a new
# profile is being created, and IPython contains config files for that profile,
# then they will be staged into the new directory.  Otherwise, default config
# files will be automatically generated.
# c.TerminalIPythonApp.copy_config_files = False

# The name of the IPython directory. This directory is used for logging
# configuration (through profiles), history storage, etc. The default is usually
# $HOME/.ipython. This options can also be specified through the environment
# variable IPYTHONDIR.
# c.TerminalIPythonApp.ipython_dir = u'/Users/preston/.ipython'

# Run the module as a script.
# c.TerminalIPythonApp.module_to_run = ''

# Start IPython quickly by skipping the loading of config files.
# c.TerminalIPythonApp.quick = False

# A list of dotted module names of IPython extensions to load.
# c.TerminalIPythonApp.extensions = []

# The Logging format template
# c.TerminalIPythonApp.log_format = '[%(name)s] %(message)s'

# dotted module name of an IPython extension to load.
# c.TerminalIPythonApp.extra_extension = ''

# List of files to run at IPython startup.
# c.TerminalIPythonApp.exec_files = []

# Whether to overwrite existing config files when copying
# c.TerminalIPythonApp.overwrite = False

# A file to be run
# c.TerminalIPythonApp.file_to_run = ''

#------------------------------------------------------------------------------
# TerminalInteractiveShell configuration
#------------------------------------------------------------------------------

# TerminalInteractiveShell will inherit config from: InteractiveShell

# auto editing of files with syntax errors.
# c.TerminalInteractiveShell.autoedit_syntax = False

# Use colors for displaying information about objects. Because this information
# is passed through a pager (like 'less'), and some pagers get confused with
# color codes, this capability can be turned off.
# c.TerminalInteractiveShell.color_info = True

# 
# c.TerminalInteractiveShell.history_length = 10000

# Don't call post-execute functions that have failed in the past.
# c.TerminalInteractiveShell.disable_failing_post_execute = False

# Show rewritten input, e.g. for autocall.
# c.TerminalInteractiveShell.show_rewritten_input = True

# Set the color scheme (NoColor, Linux, or LightBG).
# c.TerminalInteractiveShell.colors = 'LightBG'

# Autoindent IPython code entered interactively.
# c.TerminalInteractiveShell.autoindent = True

# 
# c.TerminalInteractiveShell.separate_in = '\n'

# Enable magic commands to be called without the leading %.
# c.TerminalInteractiveShell.automagic = True

# Deprecated, use PromptManager.in2_template
# c.TerminalInteractiveShell.prompt_in2 = '   .\\D.: '

# 
# c.TerminalInteractiveShell.separate_out = ''

# Deprecated, use PromptManager.in_template
# c.TerminalInteractiveShell.prompt_in1 = 'In [\\#]: '

# Enable deep (recursive) reloading by default. IPython can use the deep_reload
# module which reloads changes in modules recursively (it replaces the reload()
# function, so you don't need to change anything to use it). deep_reload()
# forces a full reload of modules whose code may have changed, which the default
# reload() function does not.  When deep_reload is off, IPython will use the
# normal reload(), but deep_reload will still be available as dreload().
# c.TerminalInteractiveShell.deep_reload = False

# Number of lines of your screen, used to control printing of very long strings.
# Strings longer than this number of lines will be sent through a pager instead
# of directly printed.  The default value for this is 0, which means IPython
# will auto-detect your screen size every time it needs to print certain
# potentially long strings (this doesn't change the behavior of the 'print'
# keyword, it's only triggered internally). If for some reason this isn't
# working well (it needs curses support), specify it yourself. Otherwise don't
# change the default.
# c.TerminalInteractiveShell.screen_length = 0

# Set the editor used by IPython (default to $EDITOR/vi/notepad).
# c.TerminalInteractiveShell.editor = 'mvim -f -c "au VimLeave * !open -a Terminal"'

# Deprecated, use PromptManager.justify
# c.TerminalInteractiveShell.prompts_pad_left = True

# The part of the banner to be printed before the profile
# c.TerminalInteractiveShell.banner1 = 'Python 2.7.2 (default, Jun 20 2012, 16:23:33) \nType "copyright", "credits" or "license" for more information.\n\nIPython 0.13.2 -- An enhanced Interactive Python.\n?         -> Introduction and overview of IPython\'s features.\n%quickref -> Quick reference.\nhelp      -> Python\'s own help system.\nobject?   -> Details about \'object\', use \'object??\' for extra details.\n'

# 
# c.TerminalInteractiveShell.readline_parse_and_bind = ['tab: complete', '"\\C-l": clear-screen', 'set show-all-if-ambiguous on', '"\\C-o": tab-insert', '"\\C-r": reverse-search-history', '"\\C-s": forward-search-history', '"\\C-p": history-search-backward', '"\\C-n": history-search-forward', '"\\e[A": history-search-backward', '"\\e[B": history-search-forward', '"\\C-k": kill-line', '"\\C-u": unix-line-discard']

# The part of the banner to be printed after the profile
# c.TerminalInteractiveShell.banner2 = ''

# 
# c.TerminalInteractiveShell.separate_out2 = ''

# 
# c.TerminalInteractiveShell.wildcards_case_sensitive = True

# 
# c.TerminalInteractiveShell.debug = False

# Set to confirm when you try to exit IPython with an EOF (Control-D in Unix,
# Control-Z/Enter in Windows). By typing 'exit' or 'quit', you can force a
# direct exit without any confirmation.
# c.TerminalInteractiveShell.confirm_exit = True

# 
# c.TerminalInteractiveShell.ipython_dir = ''

# 
# c.TerminalInteractiveShell.readline_remove_delims = '-/~'

# Start logging to the default log file.
# c.TerminalInteractiveShell.logstart = False

# The name of the logfile to use.
# c.TerminalInteractiveShell.logfile = ''

# The shell program to be used for paging.
# c.TerminalInteractiveShell.pager = 'less'

# Make IPython automatically call any callable object even if you didn't type
# explicit parentheses. For example, 'str 43' becomes 'str(43)' automatically.
# The value can be '0' to disable the feature, '1' for 'smart' autocall, where
# it is not applied if there are no more arguments on the line, and '2' for
# 'full' autocall, where all callable objects are automatically called (even if
# no arguments are present).
# c.TerminalInteractiveShell.autocall = 0

# Save multi-line entries as one entry in readline history
# c.TerminalInteractiveShell.multiline_history = True

# 
# c.TerminalInteractiveShell.readline_use = True

# Start logging to the given file in append mode.
# c.TerminalInteractiveShell.logappend = ''

# 
# c.TerminalInteractiveShell.xmode = 'Context'

# 
# c.TerminalInteractiveShell.quiet = False

# Enable auto setting the terminal title.
# c.TerminalInteractiveShell.term_title = False

# 
# c.TerminalInteractiveShell.object_info_string_level = 0

# Deprecated, use PromptManager.out_template
# c.TerminalInteractiveShell.prompt_out = 'Out[\\#]: '

# Set the size of the output cache.  The default is 1000, you can change it
# permanently in your config file.  Setting it to 0 completely disables the
# caching system, and the minimum value accepted is 20 (if you provide a value
# less than 20, it is reset to 0 and a warning is issued).  This limit is
# defined because otherwise you'll spend more time re-flushing a too small cache
# than working
# c.TerminalInteractiveShell.cache_size = 1000

# 'all', 'last', 'last_expr' or 'none', specifying which nodes should be run
# interactively (displaying output from expressions).
# c.TerminalInteractiveShell.ast_node_interactivity = 'last_expr'

# Automatically call the pdb debugger after every exception.
# c.TerminalInteractiveShell.pdb = False

#------------------------------------------------------------------------------
# PromptManager configuration
#------------------------------------------------------------------------------

# This is the primary interface for producing IPython's prompts.

# Output prompt. '\#' will be transformed to the prompt number
# c.PromptManager.out_template = 'Out[\\#]: '

# Continuation prompt.
# c.PromptManager.in2_template = '   .\\D.: '

# If True (default), each prompt will be right-aligned with the preceding one.
# c.PromptManager.justify = True

# Input prompt.  '\#' will be transformed to the prompt number
# c.PromptManager.in_template = 'In [\\#]: '

# 
# c.PromptManager.color_scheme = 'Linux'

#------------------------------------------------------------------------------
# HistoryManager configuration
#------------------------------------------------------------------------------

# A class to organize all history-related functionality in one place.

# HistoryManager will inherit config from: HistoryAccessor

# 
# c.HistoryManager.db_log_output = False

# Path to file to use for SQLite history database.
# 
# By default, IPython will put the history database in the IPython profile
# directory.  If you would rather share one history among profiles, you can set
# this value in each, so that they are consistent.
# 
# Due to an issue with fcntl, SQLite is known to misbehave on some NFS mounts.
# If you see IPython hanging, try setting this to something on a local disk,
# e.g::
# 
#     ipython --HistoryManager.hist_file=/tmp/ipython_hist.sqlite
# c.HistoryManager.hist_file = u''

# 
# c.HistoryManager.db_cache_size = 0

#------------------------------------------------------------------------------
# ProfileDir configuration
#------------------------------------------------------------------------------

# An object to manage the profile directory and its resources.
# 
# The profile directory is used by all IPython applications, to manage
# configuration, logging and security.
# 
# This object knows how to find, create and manage these directories. This
# should be used by any code that wants to handle profiles.

# Set the profile location directly. This overrides the logic used by the
# `profile` option.
# c.ProfileDir.location = u''

#------------------------------------------------------------------------------
# PlainTextFormatter configuration
#------------------------------------------------------------------------------

# The default pretty-printer.
# 
# This uses :mod:`IPython.lib.pretty` to compute the format data of the object.
# If the object cannot be pretty printed, :func:`repr` is used. See the
# documentation of :mod:`IPython.lib.pretty` for details on how to write pretty
# printers.  Here is a simple example::
# 
#     def dtype_pprinter(obj, p, cycle):
#         if cycle:
#             return p.text('dtype(...)')
#         if hasattr(obj, 'fields'):
#             if obj.fields is None:
#                 p.text(repr(obj))
#             else:
#                 p.begin_group(7, 'dtype([')
#                 for i, field in enumerate(obj.descr):
#                     if i > 0:
#                         p.text(',')
#                         p.breakable()
#                     p.pretty(field)
#                 p.end_group(7, '])')

# PlainTextFormatter will inherit config from: BaseFormatter

# 
# c.PlainTextFormatter.type_printers = {}

# 
# c.PlainTextFormatter.newline = '\n'

# 
# c.PlainTextFormatter.float_precision = ''

# 
# c.PlainTextFormatter.verbose = False

# 
# c.PlainTextFormatter.deferred_printers = {}

# 
# c.PlainTextFormatter.pprint = True

# 
# c.PlainTextFormatter.max_width = 79

# 
# c.PlainTextFormatter.singleton_printers = {}

#------------------------------------------------------------------------------
# IPCompleter configuration
#------------------------------------------------------------------------------

# Extension of the completer class with IPython-specific features

# IPCompleter will inherit config from: Completer

# Instruct the completer to omit private method names
# 
# Specifically, when completing on ``object.<tab>``.
# 
# When 2 [default]: all names that start with '_' will be excluded.
# 
# When 1: all 'magic' names (``__foo__``) will be excluded.
# 
# When 0: nothing will be excluded.
# c.IPCompleter.omit__names = 2

# Whether to merge completion results into a single list
# 
# If False, only the completion results from the first non-empty completer will
# be returned.
# c.IPCompleter.merge_completions = True

# Instruct the completer to use __all__ for the completion
# 
# Specifically, when completing on ``object.<tab>``.
# 
# When True: only those names in obj.__all__ will be included.
# 
# When False [default]: the __all__ attribute is ignored
# c.IPCompleter.limit_to__all__ = False

# Activate greedy completion
# 
# This will enable completion on elements of lists, results of function calls,
# etc., but can be unsafe because the code is actually evaluated on TAB.
# c.IPCompleter.greedy = False

#------------------------------------------------------------------------------
# ScriptMagics configuration
#------------------------------------------------------------------------------

# Magics for talking to scripts
# 
# This defines a base `%%script` cell magic for running a cell with a program in
# a subprocess, and registers a few top-level magics that call %%script with
# common interpreters.

# Extra script cell magics to define
# 
# This generates simple wrappers of `%%script foo` as `%%foo`.
# 
# If you want to add script magics that aren't on your path, specify them in
# script_paths
# c.ScriptMagics.script_magics = []

# Dict mapping short 'ruby' names to full paths, such as '/opt/secret/bin/ruby'
# 
# Only necessary for items in script_magics where the default path will not find
# the right interpreter.
# c.ScriptMagics.script_paths = {}

########NEW FILE########
__FILENAME__ = ipython_notebook_config
# Configuration file for ipython-notebook.

c = get_config()

#------------------------------------------------------------------------------
# NotebookApp configuration
#------------------------------------------------------------------------------

# NotebookApp will inherit config from: BaseIPythonApplication, Application

# The IPython profile to use.
# c.NotebookApp.profile = u'default'

# The url for MathJax.js.
# c.NotebookApp.mathjax_url = ''

# The IP address the notebook server will listen on.
c.NotebookApp.ip = '*'

# The base URL for the notebook server
# c.NotebookApp.base_project_url = '/'

# Create a massive crash report when IPython encounters what may be an internal
# error.  The default is to append a short message to the usual traceback
# c.NotebookApp.verbose_crash = False

# The number of additional ports to try if the specified port is not available.
# c.NotebookApp.port_retries = 50

# Whether to install the default config files into the profile dir. If a new
# profile is being created, and IPython contains config files for that profile,
# then they will be staged into the new directory.  Otherwise, default config
# files will be automatically generated.
# c.NotebookApp.copy_config_files = False

# The base URL for the kernel server
# c.NotebookApp.base_kernel_url = '/'

# The port the notebook server will listen on.
c.NotebookApp.port = 8888

# Whether to overwrite existing config files when copying
# c.NotebookApp.overwrite = False

# Whether to prevent editing/execution of notebooks.
# c.NotebookApp.read_only = False

# Whether to enable MathJax for typesetting math/TeX
# 
# MathJax is the javascript library IPython uses to render math/LaTeX. It is
# very large, so you may want to disable it if you have a slow internet
# connection, or for offline use of the notebook.
# 
# When disabled, equations etc. will appear as their untransformed TeX source.
# c.NotebookApp.enable_mathjax = True

# Whether to open in a browser after starting. The specific browser used is
# platform dependent and determined by the python standard library `webbrowser`
# module, unless it is overridden using the --browser (NotebookApp.browser)
# configuration option.
c.NotebookApp.open_browser = False

# The full path to an SSL/TLS certificate file.
# c.NotebookApp.certfile = u''

# The hostname for the websocket server.
# c.NotebookApp.websocket_host = ''

# The name of the IPython directory. This directory is used for logging
# configuration (through profiles), history storage, etc. The default is usually
# $HOME/.ipython. This options can also be specified through the environment
# variable IPYTHONDIR.
# c.NotebookApp.ipython_dir = u'/Users/preston/.ipython'

# Set the log level by value or name.
# c.NotebookApp.log_level = 20

# Hashed password to use for web authentication.
# 
# To generate, type in a python/IPython shell:
# 
#   from IPython.lib import passwd; passwd()
# 
# The string should be of the form type:salt:hashed-password.
# c.NotebookApp.password = u''

# The Logging format template
# c.NotebookApp.log_format = '[%(name)s] %(message)s'

# The full path to a private key file for usage with SSL/TLS.
# c.NotebookApp.keyfile = u''

# Supply overrides for the tornado.web.Application that the IPython notebook
# uses.
# c.NotebookApp.webapp_settings = {}

# Specify what command to use to invoke a web browser when opening the notebook.
# If not specified, the default browser will be determined by the `webbrowser`
# standard library module, which allows setting of the BROWSER environment
# variable to override it.
# c.NotebookApp.browser = u''

#------------------------------------------------------------------------------
# IPKernelApp configuration
#------------------------------------------------------------------------------

# IPython: an enhanced interactive Python shell.

# IPKernelApp will inherit config from: KernelApp, BaseIPythonApplication,
# Application, InteractiveShellApp

# The importstring for the DisplayHook factory
# c.IPKernelApp.displayhook_class = 'IPython.zmq.displayhook.ZMQDisplayHook'

# Set the IP or interface on which the kernel will listen.
# c.IPKernelApp.ip = '127.0.0.1'

# 
# c.IPKernelApp.parent_appname = u''

# Create a massive crash report when IPython encounters what may be an internal
# error.  The default is to append a short message to the usual traceback
# c.IPKernelApp.verbose_crash = False

# Run the module as a script.
# c.IPKernelApp.module_to_run = ''

# set the shell (ROUTER) port [default: random]
# c.IPKernelApp.shell_port = 0

# Whether to overwrite existing config files when copying
# c.IPKernelApp.overwrite = False

# Execute the given command string.
# c.IPKernelApp.code_to_run = ''

# set the stdin (DEALER) port [default: random]
# c.IPKernelApp.stdin_port = 0

# Set the log level by value or name.
# c.IPKernelApp.log_level = 30

# lines of code to run at IPython startup.
# c.IPKernelApp.exec_lines = []

# The importstring for the OutStream factory
# c.IPKernelApp.outstream_class = 'IPython.zmq.iostream.OutStream'

# Whether to create profile dir if it doesn't exist
# c.IPKernelApp.auto_create = False

# set the heartbeat port [default: random]
# c.IPKernelApp.hb_port = 0

# redirect stdout to the null device
# c.IPKernelApp.no_stdout = False

# dotted module name of an IPython extension to load.
# c.IPKernelApp.extra_extension = ''

# A file to be run
# c.IPKernelApp.file_to_run = ''

# The IPython profile to use.
# c.IPKernelApp.profile = u'default'

# Pre-load matplotlib and numpy for interactive use, selecting a particular
# matplotlib backend and loop integration.
# c.IPKernelApp.pylab = None

# kill this process if its parent dies.  On Windows, the argument specifies the
# HANDLE of the parent process, otherwise it is simply boolean.
# c.IPKernelApp.parent = 0

# JSON file in which to store connection info [default: kernel-<pid>.json]
# 
# This file will contain the IP, ports, and authentication key needed to connect
# clients to this kernel. By default, this file will be created in the security-
# dir of the current profile, but can be specified by absolute path.
# c.IPKernelApp.connection_file = ''

# If true, an 'import *' is done from numpy and pylab, when using pylab
# c.IPKernelApp.pylab_import_all = True

# The name of the IPython directory. This directory is used for logging
# configuration (through profiles), history storage, etc. The default is usually
# $HOME/.ipython. This options can also be specified through the environment
# variable IPYTHONDIR.
# c.IPKernelApp.ipython_dir = u'/Users/preston/.ipython'

# ONLY USED ON WINDOWS Interrupt this process when the parent is signalled.
# c.IPKernelApp.interrupt = 0

# Whether to install the default config files into the profile dir. If a new
# profile is being created, and IPython contains config files for that profile,
# then they will be staged into the new directory.  Otherwise, default config
# files will be automatically generated.
# c.IPKernelApp.copy_config_files = False

# List of files to run at IPython startup.
# c.IPKernelApp.exec_files = []

# Enable GUI event loop integration ('qt', 'wx', 'gtk', 'glut', 'pyglet',
# 'osx').
# c.IPKernelApp.gui = None

# A list of dotted module names of IPython extensions to load.
# c.IPKernelApp.extensions = []

# redirect stderr to the null device
# c.IPKernelApp.no_stderr = False

# The Logging format template
# c.IPKernelApp.log_format = '[%(name)s] %(message)s'

# set the iopub (PUB) port [default: random]
# c.IPKernelApp.iopub_port = 0

#------------------------------------------------------------------------------
# ZMQInteractiveShell configuration
#------------------------------------------------------------------------------

# A subclass of InteractiveShell for ZMQ.

# ZMQInteractiveShell will inherit config from: InteractiveShell

# Use colors for displaying information about objects. Because this information
# is passed through a pager (like 'less'), and some pagers get confused with
# color codes, this capability can be turned off.
# c.ZMQInteractiveShell.color_info = True

# 
# c.ZMQInteractiveShell.history_length = 10000

# Don't call post-execute functions that have failed in the past.
# c.ZMQInteractiveShell.disable_failing_post_execute = False

# Show rewritten input, e.g. for autocall.
# c.ZMQInteractiveShell.show_rewritten_input = True

# Set the color scheme (NoColor, Linux, or LightBG).
# c.ZMQInteractiveShell.colors = 'LightBG'

# 
# c.ZMQInteractiveShell.separate_in = '\n'

# Deprecated, use PromptManager.in2_template
# c.ZMQInteractiveShell.prompt_in2 = '   .\\D.: '

# 
# c.ZMQInteractiveShell.separate_out = ''

# Deprecated, use PromptManager.in_template
# c.ZMQInteractiveShell.prompt_in1 = 'In [\\#]: '

# Enable deep (recursive) reloading by default. IPython can use the deep_reload
# module which reloads changes in modules recursively (it replaces the reload()
# function, so you don't need to change anything to use it). deep_reload()
# forces a full reload of modules whose code may have changed, which the default
# reload() function does not.  When deep_reload is off, IPython will use the
# normal reload(), but deep_reload will still be available as dreload().
# c.ZMQInteractiveShell.deep_reload = False

# Make IPython automatically call any callable object even if you didn't type
# explicit parentheses. For example, 'str 43' becomes 'str(43)' automatically.
# The value can be '0' to disable the feature, '1' for 'smart' autocall, where
# it is not applied if there are no more arguments on the line, and '2' for
# 'full' autocall, where all callable objects are automatically called (even if
# no arguments are present).
# c.ZMQInteractiveShell.autocall = 0

# 
# c.ZMQInteractiveShell.separate_out2 = ''

# Deprecated, use PromptManager.justify
# c.ZMQInteractiveShell.prompts_pad_left = True

# 
# c.ZMQInteractiveShell.readline_parse_and_bind = ['tab: complete', '"\\C-l": clear-screen', 'set show-all-if-ambiguous on', '"\\C-o": tab-insert', '"\\C-r": reverse-search-history', '"\\C-s": forward-search-history', '"\\C-p": history-search-backward', '"\\C-n": history-search-forward', '"\\e[A": history-search-backward', '"\\e[B": history-search-forward', '"\\C-k": kill-line', '"\\C-u": unix-line-discard']

# Enable magic commands to be called without the leading %.
# c.ZMQInteractiveShell.automagic = True

# 
# c.ZMQInteractiveShell.debug = False

# 
# c.ZMQInteractiveShell.object_info_string_level = 0

# 
# c.ZMQInteractiveShell.ipython_dir = ''

# 
# c.ZMQInteractiveShell.readline_remove_delims = '-/~'

# Start logging to the default log file.
# c.ZMQInteractiveShell.logstart = False

# The name of the logfile to use.
# c.ZMQInteractiveShell.logfile = ''

# 
# c.ZMQInteractiveShell.wildcards_case_sensitive = True

# Save multi-line entries as one entry in readline history
# c.ZMQInteractiveShell.multiline_history = True

# Start logging to the given file in append mode.
# c.ZMQInteractiveShell.logappend = ''

# 
# c.ZMQInteractiveShell.xmode = 'Context'

# 
# c.ZMQInteractiveShell.quiet = False

# Deprecated, use PromptManager.out_template
# c.ZMQInteractiveShell.prompt_out = 'Out[\\#]: '

# Set the size of the output cache.  The default is 1000, you can change it
# permanently in your config file.  Setting it to 0 completely disables the
# caching system, and the minimum value accepted is 20 (if you provide a value
# less than 20, it is reset to 0 and a warning is issued).  This limit is
# defined because otherwise you'll spend more time re-flushing a too small cache
# than working
# c.ZMQInteractiveShell.cache_size = 1000

# 'all', 'last', 'last_expr' or 'none', specifying which nodes should be run
# interactively (displaying output from expressions).
# c.ZMQInteractiveShell.ast_node_interactivity = 'last_expr'

# Automatically call the pdb debugger after every exception.
# c.ZMQInteractiveShell.pdb = False

#------------------------------------------------------------------------------
# ProfileDir configuration
#------------------------------------------------------------------------------

# An object to manage the profile directory and its resources.
# 
# The profile directory is used by all IPython applications, to manage
# configuration, logging and security.
# 
# This object knows how to find, create and manage these directories. This
# should be used by any code that wants to handle profiles.

# Set the profile location directly. This overrides the logic used by the
# `profile` option.
# c.ProfileDir.location = u''

#------------------------------------------------------------------------------
# Session configuration
#------------------------------------------------------------------------------

# Object for handling serialization and sending of messages.
# 
# The Session object handles building messages and sending them with ZMQ sockets
# or ZMQStream objects.  Objects can communicate with each other over the
# network via Session objects, and only need to work with the dict-based IPython
# message spec. The Session will handle serialization/deserialization, security,
# and metadata.
# 
# Sessions support configurable serialiization via packer/unpacker traits, and
# signing with HMAC digests via the key/keyfile traits.
# 
# Parameters ----------
# 
# debug : bool
#     whether to trigger extra debugging statements
# packer/unpacker : str : 'json', 'pickle' or import_string
#     importstrings for methods to serialize message parts.  If just
#     'json' or 'pickle', predefined JSON and pickle packers will be used.
#     Otherwise, the entire importstring must be used.
# 
#     The functions must accept at least valid JSON input, and output *bytes*.
# 
#     For example, to use msgpack:
#     packer = 'msgpack.packb', unpacker='msgpack.unpackb'
# pack/unpack : callables
#     You can also set the pack/unpack callables for serialization directly.
# session : bytes
#     the ID of this Session object.  The default is to generate a new UUID.
# username : unicode
#     username added to message headers.  The default is to ask the OS.
# key : bytes
#     The key used to initialize an HMAC signature.  If unset, messages
#     will not be signed or checked.
# keyfile : filepath
#     The file containing a key.  If this is set, `key` will be initialized
#     to the contents of the file.

# Username for the Session. Default is your system username.
# c.Session.username = 'preston'

# The name of the packer for serializing messages. Should be one of 'json',
# 'pickle', or an import name for a custom callable serializer.
# c.Session.packer = 'json'

# The UUID identifying this session.
# c.Session.session = u''

# execution key, for extra authentication.
# c.Session.key = ''

# Debug output in the Session
# c.Session.debug = False

# The name of the unpacker for unserializing messages. Only used with custom
# functions for `packer`.
# c.Session.unpacker = 'json'

# path to file containing execution key.
# c.Session.keyfile = ''

#------------------------------------------------------------------------------
# MappingKernelManager configuration
#------------------------------------------------------------------------------

# A KernelManager that handles notebok mapping and HTTP error handling

# MappingKernelManager will inherit config from: MultiKernelManager

# The max raw message size accepted from the browser over a WebSocket
# connection.
# c.MappingKernelManager.max_msg_size = 65536

# Kernel heartbeat interval in seconds.
# c.MappingKernelManager.time_to_dead = 3.0

# The kernel manager class.  This is configurable to allow subclassing of the
# KernelManager for customized behavior.
# c.MappingKernelManager.kernel_manager_class = 'IPython.zmq.blockingkernelmanager.BlockingKernelManager'

# Delay (in seconds) before sending first heartbeat.
# c.MappingKernelManager.first_beat = 5.0

#------------------------------------------------------------------------------
# NotebookManager configuration
#------------------------------------------------------------------------------

# Automatically create a Python script when saving the notebook.
# 
# For easier use of import, %run and %load across notebooks, a <notebook-
# name>.py script will be created next to any <notebook-name>.ipynb on each
# save.  This can also be set with the short `--script` flag.
# c.NotebookManager.save_script = False

# The directory to use for notebooks.
# c.NotebookManager.notebook_dir = u'/Users/preston/Projects/code/notebook-docker'

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python
# coding=utf8

import json
import os
import re
import threading
import time
from unicodedata import normalize

import docker
from flask import Flask, render_template, session, g, redirect, url_for
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, TextField

import psutil
import requests

app = Flask(__name__)

app.config['BOOTSTRAP_USE_MINIFIED'] = True
app.config['BOOTSTRAP_USE_CDN'] = True
app.config['BOOTSTRAP_FONTAWESOME'] = True
app.config['SECRET_KEY'] = 'devkey'

CONTAINER_STORAGE = "/usr/local/etc/jiffylab/webapp/containers.json"
SERVICES_HOST = '127.0.0.1'
BASE_IMAGE = 'ptone/jiffylab-base'

initial_memory_budget = psutil.virtual_memory().free  # or can use available for vm

# how much memory should each container be limited to
CONTAINER_MEM_LIMIT = 1024 * 1024 * 100
# how much memory must remain in order for a new container to start?
MEM_MIN = CONTAINER_MEM_LIMIT + 1024 * 1024 * 20

app.config.from_object(__name__)
app.config.from_envvar('FLASKAPP_SETTINGS', silent=True)

Bootstrap(app)

docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                  version='1.6',
                  timeout=10)

lock = threading.Lock()


class ContainerException(Exception):
    """
    There was some problem generating or launching a docker container
    for the user
    """
    pass


class UserForm(Form):
    # TODO use HTML5 email input
    email = TextField('Email', description='Please enter your email address.')


@app.before_request
def get_current_user():
    g.user = None
    email = session.get('email')
    if email is not None:
        g.user = email

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates a slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def get_image(image_name=BASE_IMAGE):
    # TODO catch ConnectionError - requests.exceptions.ConnectionError
    for image in docker_client.images():
        if image['Repository'] == image_name and image['Tag'] == 'latest':
            return image
    raise ContainerException("No image found")
    return None


def lookup_container(name):
    # TODO should this be reset at startup?
    container_store = app.config['CONTAINER_STORAGE']
    if not os.path.exists(container_store):
        with lock:
            json.dump({}, open(container_store, 'wb'))
        return None
    containers = json.load(open(container_store, 'rb'))
    try:
        return containers[name]
    except KeyError:
        return None


def check_memory():
    """
    Check that we have enough memory "budget" to use for this container

    Note this is hard because while each container may not be using its full
    memory limit amount, you have to consider it like a check written to your
    account, you never know when it may be cashed.
    """
    # the overbook factor says that each container is unlikely to be using its
    # full memory limit, and so this is a guestimate of how much you can overbook
    # your memory
    overbook_factor = .8
    remaining_budget = initial_memory_budget - len(docker_client.containers()) * CONTAINER_MEM_LIMIT * overbook_factor
    if remaining_budget < MEM_MIN:
        raise ContainerException("Sorry, not enough free memory to start your container")



def remember_container(name, containerid):
    container_store = app.config['CONTAINER_STORAGE']
    with lock:
        if not os.path.exists(container_store):
            containers = {}
        else:
            containers = json.load(open(container_store, 'rb'))
        containers[name] = containerid
        json.dump(containers, open(container_store, 'wb'))


def forget_container(name):
    container_store = app.config['CONTAINER_STORAGE']
    with lock:
        if not os.path.exists(container_store):
            return False
        else:
            containers = json.load(open(container_store, 'rb'))
        try:
            del(containers[name])
            json.dump(containers, open(container_store, 'wb'))
        except KeyError:
            return False
        return True

def add_portmap(cont):
    if cont['Ports']:
        # a bit of a crazy comprehension to turn:
        # Ports': u'49166->8888, 49167->22'
        # into a useful dict {8888: 49166, 22: 49167}
        cont['portmap'] = dict([(p['PrivatePort'], p['PublicPort']) for p in cont['Ports']])

        # wait until services are up before returning container
        # TODO this could probably be factored better when next
        # service added
        # this should be done via ajax in the browser
        # this will loop and kill the server if it stalls on docker
        ipy_wait = shellinabox_wait = True
        while ipy_wait or shellinabox_wait:
            if ipy_wait:
                try:
                    requests.head("http://{host}:{port}".format(
                            host=app.config['SERVICES_HOST'],
                            port=cont['portmap'][8888]))
                    ipy_wait = False
                except requests.exceptions.ConnectionError:
                    pass

            if shellinabox_wait:
                try:
                    requests.head("http://{host}:{port}".format(
                            host=app.config['SERVICES_HOST'],
                            port=cont['portmap'][4200]))
                    shellinabox_wait = False
                except requests.exceptions.ConnectionError:
                    pass
            time.sleep(.2)
            print 'waiting', app.config['SERVICES_HOST']
        return cont


def get_container(cont_id, all=False):
    # TODO catch ConnectionError
    for cont in docker_client.containers(all=all):
        if cont_id in cont['Id']:
            return cont
    return None


def get_or_make_container(email):
    # TODO catch ConnectionError
    name = slugify(unicode(email)).lower()
    container_id = lookup_container(name)
    if not container_id:
        image = get_image()
        cont = docker_client.create_container(
                image['Id'],
                None,
                hostname="{user}box".format(user=name.split('-')[0]),
                mem_limit=CONTAINER_MEM_LIMIT,
                ports=[8888, 4200],
                )

        remember_container(name, cont['Id'])
        container_id = cont['Id']

    container = get_container(container_id, all=True)

    if not container:
        # we may have had the container cleared out
        forget_container(name)
        print 'recurse'
        # recurse
        # TODO DANGER- could have a over-recursion guard?
        return get_or_make_container(email)

    if "Up" not in container['Status']:
        # if the container is not currently running, restart it
        check_memory()
        docker_client.start(container_id, publish_all_ports=True)
        # refresh status
        container = get_container(container_id)
    container = add_portmap(container)
    return container


@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        container = None
        form = UserForm()
        print g.user
        if g.user:
            # show container:
            container = get_or_make_container(g.user)
        else:
            if form.validate_on_submit():
                g.user = form.email.data
                session['email'] = g.user
                container = get_or_make_container(g.user)
        return render_template('index.html',
                container=container,
                form=form,
                servicehost=app.config['SERVICES_HOST'],
                )
    except ContainerException as e:
        session.pop('email', None)
        return render_template('error.html', error=e)


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('email', None)
    return redirect(url_for('index'))


if '__main__' == __name__:
    # app.run(debug=True, host='0.0.0.0')
    pass



########NEW FILE########
__FILENAME__ = server
from app import app

if '__main__' == __name__:
    app.run(debug=False, host='0.0.0.0', port=5000)

########NEW FILE########
