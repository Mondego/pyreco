__FILENAME__ = main
import sublime
import sublime_plugin

import os
import sys
import threading

# Load modules
try:
    from .xdebug import *
except:
    from xdebug import *

# Set Python libraries from system installation
python_path = config.get_value(S.KEY_PYTHON_PATH)
if python_path:
    python_path = os.path.normpath(python_path.replace("\\", "/"))
    python_dynload = os.path.join(python_path, 'lib-dynload')
    if python_dynload not in sys.path:
        sys.path.append(python_dynload)

# Define path variables
try:
    S.PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
    S.PACKAGE_FOLDER = os.path.basename(S.PACKAGE_PATH)
except:
    pass


# Initialize package
sublime.set_timeout(lambda: load.xdebug(), 1000)


# Define event listener for view(s)
class EventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        filename = view.file_name()
        # Scroll the view to current breakpoint line
        if filename and filename in S.SHOW_ROW_ONLOAD:
            V.show_at_row(view, S.SHOW_ROW_ONLOAD[filename])
            del S.SHOW_ROW_ONLOAD[filename]
        # Render breakpoint markers
        sublime.set_timeout(lambda: V.render_regions(view), 0)

    def on_activated(self, view):
        # Render breakpoint markers
        V.render_regions(view)

    def on_post_save(self, view):
        filename = view.file_name()
        # Render breakpoint markers
        V.render_regions(view)
        # Update config when settings file or sublime-project has been saved
        if filename and (filename.endswith(S.FILE_PACKAGE_SETTINGS) or filename.endswith('.sublime-project')):
            config.load_package_values()
            config.load_project_values()
        #TODO: Save new location of breakpoints on save

    def on_selection_modified(self, view):
        # Show details in output panel of selected variable in context window
        if view.name() == V.TITLE_WINDOW_CONTEXT:
            V.show_context_output(view)
        elif view.name() == V.TITLE_WINDOW_BREAKPOINT:
            V.toggle_breakpoint(view)
        elif view.name() == V.TITLE_WINDOW_STACK:
            V.toggle_stack(view)
        elif view.name() == V.TITLE_WINDOW_WATCH:
            V.toggle_watch(view)
        else:
            pass


class XdebugBreakpointCommand(sublime_plugin.TextCommand):
    """
    Add/Remove breakpoint(s) for rows (line numbers) in selection.
    """
    def run(self, edit, rows=None, condition=None, enabled=None, filename=None):
        # Get filename in current view and check if is a valid filename
        if filename is None:
            filename = self.view.file_name()
        if not filename or not os.path.isfile(filename):
            return

        # Add entry for file in breakpoint data
        if filename not in S.BREAKPOINT:
            S.BREAKPOINT[filename] = {}

        # When no rows are defined, use selected rows (line numbers), filtering empty rows
        if rows is None:
            rows = V.region_to_rows(self.view.sel(), filter_empty=True)

        # Loop through rows
        for row in rows:
            expression = None
            if condition is not None and len(condition.strip()) > 0:
                expression = condition
            # Check if breakpoint exists
            breakpoint_exists = row in S.BREAKPOINT[filename]
            # Disable/Remove breakpoint
            if breakpoint_exists:
                if S.BREAKPOINT[filename][row]['id'] is not None and session.is_connected(show_status=True):
                    async_session = session.SocketHandler(session.ACTION_REMOVE_BREAKPOINT, breakpoint_id=S.BREAKPOINT[filename][row]['id'])
                    async_session.start()
                if enabled is False:
                    S.BREAKPOINT[filename][row]['enabled'] = False
                elif enabled is None:
                    del S.BREAKPOINT[filename][row]
            # Add/Enable breakpoint
            if not breakpoint_exists or enabled is True:
                if row not in S.BREAKPOINT[filename]:
                    S.BREAKPOINT[filename][row] = { 'id': None, 'enabled': True, 'expression': expression }
                else:
                    S.BREAKPOINT[filename][row]['enabled'] = True
                    if condition is not None:
                        S.BREAKPOINT[filename][row]['expression'] = expression
                    else:
                        expression = S.BREAKPOINT[filename][row]['expression']
                if session.is_connected(show_status=True):
                    async_session = session.SocketHandler(session.ACTION_SET_BREAKPOINT, filename=filename, lineno=row, expression=expression)
                    async_session.start()

        # Render breakpoint markers
        V.render_regions()

        # Update breakpoint list
        try:
            if V.has_debug_view(V.TITLE_WINDOW_BREAKPOINT):
                V.show_content(V.DATA_BREAKPOINT)
        except:
            pass

        # Save breakpoint data to file
        util.save_breakpoint_data()


class XdebugConditionalBreakpointCommand(sublime_plugin.TextCommand):
    """
    Add conditional breakpoint(s) for rows (line numbers) in selection.
    """
    def run(self, edit):
        self.view.window().show_input_panel('Breakpoint condition', '', self.on_done, self.on_change, self.on_cancel)

    def on_done(self, condition):
        self.view.run_command('xdebug_breakpoint', {'condition': condition, 'enabled': True})

    def on_change(self, line):
        pass

    def on_cancel(self):
        pass


class XdebugClearBreakpointsCommand(sublime_plugin.TextCommand):
    """
    Clear breakpoints in selected view.
    """
    def run(self, edit):
        filename = self.view.file_name()
        if filename and filename in S.BREAKPOINT:
            rows = H.dictionary_keys(S.BREAKPOINT[filename])
            self.view.run_command('xdebug_breakpoint', {'rows': rows, 'filename': filename})
            # Continue debug session when breakpoints are cleared on current script being debugged
            if S.BREAKPOINT_ROW and self.view.file_name() == S.BREAKPOINT_ROW['filename']:
                self.view.window().run_command('xdebug_execute', {'command': 'run'})

    def is_enabled(self):
        filename = self.view.file_name()
        if filename and S.BREAKPOINT and filename in S.BREAKPOINT and S.BREAKPOINT[filename]:
            return True
        return False

    def is_visible(self):
        filename = self.view.file_name()
        if filename and S.BREAKPOINT and filename in S.BREAKPOINT and S.BREAKPOINT[filename]:
            return True
        return False


class XdebugClearAllBreakpointsCommand(sublime_plugin.WindowCommand):
    """
    Clear breakpoints from all views.
    """
    def run(self):
        view = sublime.active_window().active_view()
        # Unable to run to line when no view available
        if view is None:
            return

        for filename, breakpoint_data in S.BREAKPOINT.items():
            if breakpoint_data:
                rows = H.dictionary_keys(breakpoint_data)
                view.run_command('xdebug_breakpoint', {'rows': rows, 'filename': filename})
        # Continue debug session when breakpoints are cleared on current script being debugged
        self.window.run_command('xdebug_execute', {'command': 'run'})

    def is_enabled(self):
        if S.BREAKPOINT:
            for filename, breakpoint_data in S.BREAKPOINT.items():
                if breakpoint_data:
                    return True
        return False

    def is_visible(self):
        if S.BREAKPOINT:
            for filename, breakpoint_data in S.BREAKPOINT.items():
                if breakpoint_data:
                    return True
        return False


class XdebugRunToLineCommand(sublime_plugin.WindowCommand):
    """
    Run script to current selected line in view, ignoring all other breakpoints.
    """
    def run(self):
        view = sublime.active_window().active_view()
        # Unable to run to line when no view available
        if view is None:
            return
        # Determine filename for current view and check if is a valid filename
        filename = view.file_name()
        if not filename or not os.path.isfile(filename):
            return
        # Get first line from selected rows and make sure it is not empty
        rows = V.region_to_rows(filter_empty=True)
        if rows is None or len(rows) == 0:
            return
        lineno = rows[0]
        # Check if breakpoint does not already exists
        breakpoint_exists = False
        if filename in S.BREAKPOINT and lineno in S.BREAKPOINT[filename]:
            breakpoint_exists = True
        # Store line number and filename for temporary breakpoint in session
        if not breakpoint_exists:
            S.BREAKPOINT_RUN = { 'filename': filename, 'lineno': lineno }
        # Set breakpoint and run script
        view.run_command('xdebug_breakpoint', {'rows': [lineno], 'enabled': True, 'filename': filename})
        self.window.run_command('xdebug_execute', {'command': 'run'})

    def is_enabled(self):
        return S.BREAKPOINT_ROW is not None and session.is_connected()

    def is_visible(self):
        return S.BREAKPOINT_ROW is not None and session.is_connected()


class XdebugSessionStartCommand(sublime_plugin.WindowCommand):
    """
    Start Xdebug session, listen for request response from debugger engine.
    """
    def run(self, launch_browser=False, restart=False):
        # Define new session with DBGp protocol
        S.SESSION = protocol.Protocol()
        S.SESSION_BUSY = False
        S.BREAKPOINT_EXCEPTION = None
        S.BREAKPOINT_ROW = None
        S.CONTEXT_DATA.clear()
        async_session = session.SocketHandler(session.ACTION_WATCH, check_watch_view=True)
        async_session.start()
        # Remove temporary breakpoint
        if S.BREAKPOINT_RUN is not None and S.BREAKPOINT_RUN['filename'] in S.BREAKPOINT and S.BREAKPOINT_RUN['lineno'] in S.BREAKPOINT[S.BREAKPOINT_RUN['filename']]:
            self.window.active_view().run_command('xdebug_breakpoint', {'rows': [S.BREAKPOINT_RUN['lineno']], 'filename': S.BREAKPOINT_RUN['filename']})
        S.BREAKPOINT_RUN = None
        # Set debug layout
        self.window.run_command('xdebug_layout')
        # Launch browser
        if launch_browser or (config.get_value(S.KEY_LAUNCH_BROWSER) and not restart):
            util.launch_browser()

        # Start thread which will run method that listens for response on configured port
        threading.Thread(target=self.listen).start()

    def listen(self):
        # Start listening for response from debugger engine
        S.SESSION.listen()
        # On connect run method which handles connection
        if S.SESSION and S.SESSION.connected:
            sublime.set_timeout(self.connected, 0)

    def connected(self):
        sublime.set_timeout(lambda: sublime.status_message('Xdebug: Connected'), 100)

        async_session = session.SocketHandler(session.ACTION_INIT)
        async_session.start()

    def is_enabled(self):
        if S.SESSION:
            return False
        return True

    def is_visible(self, launch_browser=False):
        if S.SESSION:
            return False
        if launch_browser and (config.get_value(S.KEY_LAUNCH_BROWSER) or not config.get_value(S.KEY_URL)):
            return False
        return True


class XdebugSessionRestartCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command('xdebug_session_stop', {'restart': True})
        self.window.run_command('xdebug_session_start', {'restart': True})
        sublime.set_timeout(lambda: sublime.status_message('Xdebug: Restarted debugging session. Reload page to continue debugging.'), 100)

    def is_enabled(self):
        if S.SESSION:
            return True
        return False

    def is_visible(self):
        if S.SESSION:
            return True
        return False


class XdebugSessionStopCommand(sublime_plugin.WindowCommand):
    """
    Stop Xdebug session, close connection and stop listening to debugger engine.
    """
    def run(self, close_windows=False, launch_browser=False, restart=False):
        try:
            S.SESSION.clear()
        except:
            pass
        finally:
            S.SESSION = None
            S.SESSION_BUSY = False
            S.BREAKPOINT_EXCEPTION = None
            S.BREAKPOINT_ROW = None
            S.CONTEXT_DATA.clear()
            async_session = session.SocketHandler(session.ACTION_WATCH, check_watch_view=True)
            async_session.start()
            # Remove temporary breakpoint
            if S.BREAKPOINT_RUN is not None and S.BREAKPOINT_RUN['filename'] in S.BREAKPOINT and S.BREAKPOINT_RUN['lineno'] in S.BREAKPOINT[S.BREAKPOINT_RUN['filename']]:
                self.window.active_view().run_command('xdebug_breakpoint', {'rows': [S.BREAKPOINT_RUN['lineno']], 'filename': S.BREAKPOINT_RUN['filename']})
            S.BREAKPOINT_RUN = None
        # Launch browser
        if launch_browser or (config.get_value(S.KEY_LAUNCH_BROWSER) and not restart):
            util.launch_browser()
        # Close or reset debug layout
        if close_windows or config.get_value(S.KEY_CLOSE_ON_STOP):
            if config.get_value(S.KEY_DISABLE_LAYOUT):
                self.window.run_command('xdebug_layout', {'close_windows': True})
            else:
                self.window.run_command('xdebug_layout', {'restore': True})
        else:
            self.window.run_command('xdebug_layout')
        # Render breakpoint markers
        V.render_regions()

    def is_enabled(self):
        if S.SESSION:
            return True
        return False

    def is_visible(self, close_windows=False, launch_browser=False):
        if S.SESSION:
            if close_windows and config.get_value(S.KEY_CLOSE_ON_STOP):
                return False
            if launch_browser and (config.get_value(S.KEY_LAUNCH_BROWSER) or not config.get_value(S.KEY_URL)):
                return False
            return True
        return False


class XdebugExecuteCommand(sublime_plugin.WindowCommand):
    """
    Execute command, handle breakpoints and reload session when page execution has completed.

    Keyword arguments:
    command -- Command to send to debugger engine.
    """
    def run(self, command=None):
        async_session = session.SocketHandler(session.ACTION_EXECUTE, command=command)
        async_session.start()

    def is_enabled(self):
        return session.is_connected()


class XdebugContinueCommand(sublime_plugin.WindowCommand):
    """
    Continuation commands when on breakpoint, show menu by default if no command has been passed as argument.

    Keyword arguments:
    command -- Continuation command to execute.
    """
    commands = H.new_dictionary()
    commands[dbgp.RUN] = 'Run'
    commands[dbgp.STEP_OVER] = 'Step Over'
    commands[dbgp.STEP_INTO] = 'Step Into'
    commands[dbgp.STEP_OUT] = 'Step Out'
    commands[dbgp.STOP] = 'Stop'
    commands[dbgp.DETACH] = 'Detach'

    command_index = H.dictionary_keys(commands)
    command_options = H.dictionary_values(commands)

    def run(self, command=None):
        if not command or not command in self.commands:
            self.window.show_quick_panel(self.command_options, self.callback)
        else:
            self.callback(command)

    def callback(self, command):
        if command == -1 or S.SESSION_BUSY:
            return
        if isinstance(command, int):
            command = self.command_index[command]

        self.window.run_command('xdebug_execute', {'command': command})

    def is_enabled(self):
        return S.BREAKPOINT_ROW is not None and session.is_connected()

    def is_visible(self):
        return S.BREAKPOINT_ROW is not None and session.is_connected()


class XdebugStatusCommand(sublime_plugin.WindowCommand):
    """
    Get status from debugger engine.
    """
    def run(self):
        async_session = session.SocketHandler(session.ACTION_STATUS)
        async_session.start()

    def is_enabled(self):
        return session.is_connected()

    def is_visible(self):
        return session.is_connected()


class XdebugEvaluateCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel('Evaluate', '', self.on_done, self.on_change, self.on_cancel)

    def on_done(self, expression):
        async_session = session.SocketHandler(session.ACTION_EVALUATE, expression=expression)
        async_session.start()

    def on_change(self, expression):
        pass

    def on_cancel(self):
        pass

    def is_enabled(self):
        return session.is_connected()

    def is_visible(self):
        return session.is_connected()


class XdebugUserExecuteCommand(sublime_plugin.WindowCommand):
    """
    Open input panel, allowing user to execute arbitrary command according to DBGp protocol.
    Note: Transaction ID is automatically generated by session module.
    """
    def run(self):
        self.window.show_input_panel('DBGp command', '', self.on_done, self.on_change, self.on_cancel)

    def on_done(self, line):
        # Split command and arguments, define arguments when only command is defined.
        if ' ' in line:
            command, args = line.split(' ', 1)
        else:
            command, args = line, ''

        async_session = session.SocketHandler(session.ACTION_USER_EXECUTE, command=command, args=args)
        async_session.start()

    def on_change(self, line):
        pass

    def on_cancel(self):
        pass

    def is_enabled(self):
        return session.is_connected()

    def is_visible(self):
        return session.is_connected()


class XdebugWatchCommand(sublime_plugin.WindowCommand):
    """
    Add/Edit/Remove watch expression.
    """
    def run(self, clear=False, edit=False, remove=False, update=False):
        self.edit = edit
        self.remove = remove
        self.watch_index = None
        # Clear watch expressions in list
        if clear:
            try:
                # Python 3.3+
                S.WATCH.clear()
            except AttributeError:
                del S.WATCH[:]
            # Update watch view
            self.update_view()
        # Edit or remove watch expression
        elif edit or remove:
            # Generate list with available watch expressions
            watch_options = []
            for index, item in enumerate(S.WATCH):
                watch_item = '[{status}] - {expression}'.format(index=index, expression=item['expression'], status='enabled' if item['enabled'] else 'disabled')
                watch_options.append(watch_item)
            self.window.show_quick_panel(watch_options, self.callback)
        elif update:
            self.update_view()
        # Set watch expression
        else:
            self.set_expression()

    def callback(self, index):
        # User has cancelled action
        if index == -1:
            return
        # Make sure index is valid integer
        if isinstance(index, int) or H.is_digit(index):
            self.watch_index = int(index)
            # Edit watch expression
            if self.edit:
                self.set_expression()
            # Remove watch expression
            else:
                S.WATCH.pop(self.watch_index)
                # Update watch view
                self.update_view()

    def on_done(self, expression):
        # User did not set expression
        if not expression:
            return
        # Check if expression is not already defined
        matches = [x for x in S.WATCH if x['expression'] == expression]
        if matches:
            sublime.status_message('Xdebug: Watch expression already defined.')
            return
        # Add/Edit watch expression in session
        watch = {'expression': expression, 'enabled': True, 'value': None, 'type': None}
        if self.watch_index is not None and isinstance(self.watch_index, int):
            try:
                S.WATCH[self.watch_index]['expression'] = expression
            except:
                S.WATCH.insert(self.watch_index, watch)
        else:
            S.WATCH.append(watch)
        # Update watch view
        self.update_view()

    def on_change(self, line):
        pass

    def on_cancel(self):
        pass

    def set_expression(self):
        # Show user input for setting watch expression
        self.window.show_input_panel('Watch expression', '', self.on_done, self.on_change, self.on_cancel)

    def update_view(self):
        async_session = session.SocketHandler(session.ACTION_WATCH, check_watch_view=True)
        async_session.start()
        # Save watch data to file
        util.save_watch_data()

    def is_visible(self, clear=False, edit=False, remove=False):
        if (clear or edit or remove) and not S.WATCH:
            return False
        return True


class XdebugViewUpdateCommand(sublime_plugin.TextCommand):
    """
    Update content of sublime.Edit object in view, instead of using begin_edit/end_edit.

    Keyword arguments:
    data -- Content data to populate sublime.Edit object with.
    readonly -- Make sublime.Edit object read only.
    """
    def run(self, edit, data=None, readonly=False):
        view = self.view
        view.set_read_only(False)
        view.erase(edit, sublime.Region(0, view.size()))
        if data is not None:
            view.insert(edit, 0, data)
        if readonly:
            view.set_read_only(True)


class XdebugLayoutCommand(sublime_plugin.WindowCommand):
    """
    Toggle between debug and default window layouts.
    """
    def run(self, restore=False, close_windows=False, keymap=False):
        # Get active window
        window = sublime.active_window()
        # Do not restore layout or close windows while debugging
        if S.SESSION and (restore or close_windows or keymap):
            return
        # Set layout, unless user disabled debug layout
        if not config.get_value(S.KEY_DISABLE_LAYOUT):
            if restore or keymap:
                V.set_layout('normal')
            else:
                V.set_layout('debug')
        # Close all debugging related windows
        if close_windows or restore or keymap:
            V.close_debug_windows()
            return
        # Reset data in debugging related windows
        V.show_content(V.DATA_BREAKPOINT)
        V.show_content(V.DATA_CONTEXT)
        V.show_content(V.DATA_STACK)
        V.show_content(V.DATA_WATCH)
        panel = window.get_output_panel('xdebug')
        panel.run_command("xdebug_view_update")
        # Close output panel
        window.run_command('hide_panel', {"panel": 'output.xdebug'})

    def is_enabled(self, restore=False, close_windows=False):
        disable_layout = config.get_value(S.KEY_DISABLE_LAYOUT)
        if close_windows and (not disable_layout or not V.has_debug_view()):
            return False
        if restore and disable_layout:
            return False
        return True

    def is_visible(self, restore=False, close_windows=False):
        if S.SESSION:
            return False
        disable_layout = config.get_value(S.KEY_DISABLE_LAYOUT)
        if close_windows and (not disable_layout or not V.has_debug_view()):
            return False
        if restore and disable_layout:
            return False
        if restore:
            try:
                return sublime.active_window().get_layout() == config.get_value(S.KEY_DEBUG_LAYOUT, S.LAYOUT_DEBUG)
            except:
                pass
        return True


class XdebugSettingsCommand(sublime_plugin.WindowCommand):
    """
    Show settings file.
    """
    def run(self, default=True):
        # Show default settings in package when available
        if default and S.PACKAGE_FOLDER is not None:
            package = S.PACKAGE_FOLDER
        # Otherwise show User defined settings
        else:
            package = "User"
        # Strip .sublime-package of package name for syntax file
        package_extension = ".sublime-package"
        if package.endswith(package_extension):
            package = package[:-len(package_extension)]
        # Open settings file
        self.window.run_command('open_file', {'file': '${packages}/' + package + '/' + S.FILE_PACKAGE_SETTINGS });
########NEW FILE########
__FILENAME__ = config
import sublime

# Settings variables
try:
    from . import settings as S
except:
    import settings as S


def load_project_values():
    try:
        settings = sublime.active_window().active_view().settings()
        # Use 'xdebug' as key which contains dictionary with project values for package
        S.CONFIG_PROJECT = settings.get(S.KEY_XDEBUG)
    except:
        pass


def load_package_values():
    # Clear previous settings
    config = {}
    try:
        # Load default/user package settings
        settings = sublime.load_settings(S.FILE_PACKAGE_SETTINGS)
        # Loop through all configuration keys
        for key in S.CONFIG_KEYS:
            # Set in config if available
            if settings and settings.has(key):
                config[key] = settings.get(key)
    except:
        pass
    # Set settings in memory
    S.CONFIG_PACKAGE = config


def get_value(key, default_value=None):
    """
    Get value from package/project configuration settings.
    """
    # Get value from project configuration
    value = get_project_value(key)
    # Use package configuration when value has not been found
    if value is None:
        value = get_package_value(key)
    # Return package/project value
    if value is not None:
        return value
    # Otherwise use default value
    return default_value


def get_package_value(key, default_value=None):
    """
    Get value from default/user package configuration settings.
    """
    try:
        config = sublime.load_settings(S.FILE_PACKAGE_SETTINGS)
        if config and config.has(key):
            return config.get(key)
    except RuntimeError:
        sublime.set_timeout(lambda: load_package_values(), 0)
        if S.CONFIG_PACKAGE:
            if key in S.CONFIG_PACKAGE:
                return S.CONFIG_PACKAGE[key]

    return default_value


def get_project_value(key, default_value=None):
    """
    Get value from project configuration settings.
    """
    # Load project coniguration settings
    try:
        load_project_values()
    except RuntimeError:
        sublime.set_timeout(lambda: load_project_values(), 0)

    # Find value in project configuration
    if S.CONFIG_PROJECT:
        if key in S.CONFIG_PROJECT:
            return S.CONFIG_PROJECT[key]

    # Otherwise use default value
    return default_value


def get_window_value(key, default_value=None):
    """
    Get value from window session settings.

    NOTE: Window object in Sublime Text 2 has no Settings.
    """
    try:
        settings = sublime.active_window().settings()
        if settings.has(S.KEY_XDEBUG):
            xdebug = settings.get(S.KEY_XDEBUG)
            if isinstance(xdebug, dict) and key in xdebug.keys():
                return xdebug[key]
    except:
        pass
    return default_value


def set_package_value(key, value=None):
    """
    Set value in package configuration settings.
    """
    try:
        config = sublime.load_settings(S.FILE_PACKAGE_SETTINGS)
        if value is not None:
            config.set(key, value)
        elif config and config.has(key):
            return config.erase(key)
    except:
        pass


def set_project_value(key, value=None):
    """
    Set value in project configuration settings.
    """
    # Unable to set project value if no project file
    if not sublime.active_window().project_file_name():
        return False
    # Get current project data
    project = sublime.active_window().project_data()
    # Make sure project data is a dictionary
    if not isinstance(project, dict):
        project = {}
    # Create settings entries if they are undefined
    if S.KEY_SETTINGS not in project.keys() or not isinstance(project[S.KEY_SETTINGS], dict):
        project[S.KEY_SETTINGS] = {}
    if S.KEY_XDEBUG not in project[S.KEY_SETTINGS].keys() or not isinstance(project[S.KEY_SETTINGS][S.KEY_XDEBUG], dict):
        project[S.KEY_SETTINGS][S.KEY_XDEBUG] = {}
    # Update Xdebug settings
    if value is not None:
        project[S.KEY_SETTINGS][S.KEY_XDEBUG][key] = value
    elif key in project[S.KEY_SETTINGS][S.KEY_XDEBUG].keys():
        del project[S.KEY_SETTINGS][S.KEY_XDEBUG][key]
    # Save project data
    sublime.active_window().set_project_data(project)
    return True


def set_window_value(key, value=None):
    """
    Set value in window session settings.

    NOTE: Window object in Sublime Text 2 has no Settings.
    """
    try:
        settings = sublime.active_window().settings()
        if settings.has(S.KEY_XDEBUG):
            xdebug = settings.get(S.KEY_XDEBUG)
        else:
            xdebug = {}
        if value is not None:
            xdebug[key] = value
        elif key in xdebug.keys():
            del xdebug[key]
        settings.set(S.KEY_XDEBUG, xdebug)
    except:
        pass
########NEW FILE########
__FILENAME__ = dbgp
"""
Status and feature management commands
"""
STATUS = 'status';
FEATURE_GET = 'feature_get';
FEATURE_SET = 'feature_set';
FEATURE_NAME_MAXCHILDREN = 'max_children'
FEATURE_NAME_MAXDATA = 'max_data'
FEATURE_NAME_MAXDEPTH = 'max_depth'


"""
Continuation commands
"""
RUN = 'run';
STEP_INTO = 'step_into';
STEP_OVER = 'step_over';
STEP_OUT = 'step_out';
STOP = 'stop';
DETACH = 'detach';


"""
Breakpoint commands
"""
BREAKPOINT_SET = 'breakpoint_set'
BREAKPOINT_GET = 'breakpoint_get'
BREAKPOINT_UPDATE = 'breakpoint_update'
BREAKPOINT_REMOVE = 'breakpoint_remove'
BREAKPOINT_LIST = 'breakpoint_list'


"""
Context/Stack/Property commands
"""
CONTEXT_NAMES = 'context_names'
CONTEXT_GET = 'context_get'
STACK_DEPTH = 'stack-depth'
STACK_GET = 'stack_get'
PROPERTY_GET = 'property_get'
PROPERTY_SET = 'property_set'
PROPERTY_VALUE = 'property_value'


"""
Extendend commands
"""
STDIN = 'stdin'
BREAK = 'break'
EVAL = 'eval'
EXPR = 'expr'
EXEC = 'exec'


"""
Status codes
"""
STATUS_STARTING = 'starting';
STATUS_STOPPING = 'stopping';
STATUS_STOPPED = 'stopped';
STATUS_RUNNING = 'running';
STATUS_BREAK = 'break';


"""
Reason codes
"""
REASON_OK = 'ok';
REASON_ERROR = 'error';
REASON_ABORTED = 'aborted';
REASON_EXCEPTION = 'exception';


"""
Response attributes/elements
"""
ATTRIBUTE_STATUS = 'status'
ATTRIBUTE_REASON = 'reason'
ATTRIBUTE_SUCCESS = 'success'
ATTRIBUTE_BREAKPOINT_ID = 'id'
ELEMENT_INIT = 'init'
ELEMENT_BREAKPOINT = 'xdebug:message'
ELEMENT_ERROR = 'error'
ELEMENT_MESSAGE = 'message'
ELEMENT_PROPERTY = 'property'
ELEMENT_STACK = 'stack'
ELEMENT_PATH_INIT = '{urn:debugger_protocol_v1}init'
ELEMENT_PATH_BREAKPOINT = '{http://xdebug.org/dbgp/xdebug}message'
ELEMENT_PATH_ERROR = '{urn:debugger_protocol_v1}error'
ELEMENT_PATH_MESSAGE = '{urn:debugger_protocol_v1}message'
ELEMENT_PATH_PROPERTY = '{urn:debugger_protocol_v1}property'
ELEMENT_PATH_STACK = '{urn:debugger_protocol_v1}stack'

"""
Initialization attributes
"""
INIT_APPID = 'appid'
INIT_IDEKEY = 'idekey'
INIT_SESSION = 'session'
INIT_THREAD = 'thread'
INIT_PARENT = 'parent'
INIT_LANGUAGE = 'language'
INIT_PROTOCOL_VERSION = 'protocol_version'
INIT_FILEURI = 'fileuri'


"""
Breakpoint atrributes
"""
BREAKPOINT_TYPE = 'type'
BREAKPOINT_FILENAME = 'filename'
BREAKPOINT_LINENO = 'lineno'
BREAKPOINT_STATE = 'state'
BREAKPOINT_FUNCTION = 'function'
BREAKPOINT_TEMPORARY = 'temporary'
BREAKPOINT_HIT_COUNT = 'hit_count'
BREAKPOINT_HIT_VALUE = 'hit_value'
BREAKPOINT_HIT_CONDITION = 'hit_condition'
BREAKPOINT_EXCEPTION = 'exception'
BREAKPOINT_EXPRESSION = 'expression'


"""
Property attributes
"""
PROPERTY_NAME = 'name'
PROPERTY_FULLNAME = 'fullname'
PROPERTY_CLASSNAME = 'classname'
PROPERTY_PAGE = 'page'
PROPERTY_PAGESIZE = 'pagesize'
PROPERTY_TYPE = 'type'
PROPERTY_FACET = 'facet'
PROPERTY_SIZE = 'size'
PROPERTY_CHILDREN = 'children'
PROPERTY_NUMCHILDREN = 'numchildren'
PROPERTY_KEY = 'key'
PROPERTY_ADDRESS = 'address'
PROPERTY_ENCODING = 'encoding'


"""
Stack attributes
"""
STACK_LEVEL = 'level'
STACK_TYPE = 'type'
STACK_FILENAME = 'filename'
STACK_LINENO = 'lineno'
STACK_WHERE = 'where'
STACK_CMDBEGIN = 'cmdbegin'
STACK_CMDEND = 'cmdend'
########NEW FILE########
__FILENAME__ = ElementInclude
#
# ElementTree
# $Id: ElementInclude.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# limited xinclude support for element trees
#
# history:
# 2003-08-15 fl   created
# 2003-11-14 fl   fixed default loader
#
# Copyright (c) 2003-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Limited XInclude support for the ElementTree package.
##

import copy
import ElementTree

XINCLUDE = "{http://www.w3.org/2001/XInclude}"

XINCLUDE_INCLUDE = XINCLUDE + "include"
XINCLUDE_FALLBACK = XINCLUDE + "fallback"

##
# Fatal include error.

class FatalIncludeError(SyntaxError):
    pass

##
# Default loader.  This loader reads an included resource from disk.
#
# @param href Resource reference.
# @param parse Parse mode.  Either "xml" or "text".
# @param encoding Optional text encoding.
# @return The expanded resource.  If the parse mode is "xml", this
#    is an ElementTree instance.  If the parse mode is "text", this
#    is a Unicode string.  If the loader fails, it can return None
#    or raise an IOError exception.
# @throws IOError If the loader fails to load the resource.

def default_loader(href, parse, encoding=None):
    file = open(href)
    if parse == "xml":
        data = ElementTree.parse(file).getroot()
    else:
        data = file.read()
        if encoding:
            data = data.decode(encoding)
    file.close()
    return data

##
# Expand XInclude directives.
#
# @param elem Root element.
# @param loader Optional resource loader.  If omitted, it defaults
#     to {@link default_loader}.  If given, it should be a callable
#     that implements the same interface as <b>default_loader</b>.
# @throws FatalIncludeError If the function fails to include a given
#     resource, or if the tree contains malformed XInclude elements.
# @throws IOError If the function fails to load a given resource.

def include(elem, loader=None):
    if loader is None:
        loader = default_loader
    # look for xinclude elements
    i = 0
    while i < len(elem):
        e = elem[i]
        if e.tag == XINCLUDE_INCLUDE:
            # process xinclude directive
            href = e.get("href")
            parse = e.get("parse", "xml")
            if parse == "xml":
                node = loader(href, parse)
                if node is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                node = copy.copy(node)
                if e.tail:
                    node.tail = (node.tail or "") + e.tail
                elem[i] = node
            elif parse == "text":
                text = loader(href, parse, e.get("encoding"))
                if text is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                if i:
                    node = elem[i-1]
                    node.tail = (node.tail or "") + text
                else:
                    elem.text = (elem.text or "") + text + (e.tail or "")
                del elem[i]
                continue
            else:
                raise FatalIncludeError(
                    "unknown parse type in xi:include tag (%r)" % parse
                )
        elif e.tag == XINCLUDE_FALLBACK:
            raise FatalIncludeError(
                "xi:fallback tag must be child of xi:include (%r)" % e.tag
                )
        else:
            include(e, loader)
        i = i + 1


########NEW FILE########
__FILENAME__ = ElementPath
#
# ElementTree
# $Id: ElementPath.py 1858 2004-06-17 21:31:41Z Fredrik $
#
# limited xpath support for element trees
#
# history:
# 2003-05-23 fl   created
# 2003-05-28 fl   added support for // etc
# 2003-08-27 fl   fixed parsing of periods in element names
#
# Copyright (c) 2003-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Implementation module for XPath support.  There's usually no reason
# to import this module directly; the <b>ElementTree</b> does this for
# you, if needed.
##

import re

xpath_tokenizer = re.compile(
    "(::|\.\.|\(\)|[/.*:\[\]\(\)@=])|((?:\{[^}]+\})?[^/:\[\]\(\)@=\s]+)|\s+"
    ).findall

class xpath_descendant_or_self:
    pass

##
# Wrapper for a compiled XPath.

class Path:

    ##
    # Create an Path instance from an XPath expression.

    def __init__(self, path):
        tokens = xpath_tokenizer(path)
        # the current version supports 'path/path'-style expressions only
        self.path = []
        self.tag = None
        if tokens and tokens[0][0] == "/":
            raise SyntaxError("cannot use absolute path on element")
        while tokens:
            op, tag = tokens.pop(0)
            if tag or op == "*":
                self.path.append(tag or op)
            elif op == ".":
                pass
            elif op == "/":
                self.path.append(xpath_descendant_or_self())
                continue
            else:
                raise SyntaxError("unsupported path syntax (%s)" % op)
            if tokens:
                op, tag = tokens.pop(0)
                if op != "/":
                    raise SyntaxError(
                        "expected path separator (%s)" % (op or tag)
                        )
        if self.path and isinstance(self.path[-1], xpath_descendant_or_self):
            raise SyntaxError("path cannot end with //")
        if len(self.path) == 1 and isinstance(self.path[0], type("")):
            self.tag = self.path[0]

    ##
    # Find first matching object.

    def find(self, element):
        tag = self.tag
        if tag is None:
            nodeset = self.findall(element)
            if not nodeset:
                return None
            return nodeset[0]
        for elem in element:
            if elem.tag == tag:
                return elem
        return None

    ##
    # Find text for first matching object.

    def findtext(self, element, default=None):
        tag = self.tag
        if tag is None:
            nodeset = self.findall(element)
            if not nodeset:
                return default
            return nodeset[0].text or ""
        for elem in element:
            if elem.tag == tag:
                return elem.text or ""
        return default

    ##
    # Find all matching objects.

    def findall(self, element):
        nodeset = [element]
        index = 0
        while 1:
            try:
                path = self.path[index]
                index = index + 1
            except IndexError:
                return nodeset
            set = []
            if isinstance(path, xpath_descendant_or_self):
                try:
                    tag = self.path[index]
                    if not isinstance(tag, type("")):
                        tag = None
                    else:
                        index = index + 1
                except IndexError:
                    tag = None # invalid path
                for node in nodeset:
                    new = list(node.getiterator(tag))
                    if new and new[0] is node:
                        set.extend(new[1:])
                    else:
                        set.extend(new)
            else:
                for node in nodeset:
                    for node in node:
                        if path == "*" or node.tag == path:
                            set.append(node)
            if not set:
                return []
            nodeset = set

_cache = {}

##
# (Internal) Compile path.

def _compile(path):
    p = _cache.get(path)
    if p is not None:
        return p
    p = Path(path)
    if len(_cache) >= 100:
        _cache.clear()
    _cache[path] = p
    return p

##
# Find first matching object.

def find(element, path):
    return _compile(path).find(element)

##
# Find text for first matching object.

def findtext(element, path, default=None):
    return _compile(path).findtext(element, default)

##
# Find all matching objects.

def findall(element, path):
    return _compile(path).findall(element)


########NEW FILE########
__FILENAME__ = ElementTree
#
# ElementTree
# $Id: ElementTree.py 2326 2005-03-17 07:45:21Z fredrik $
#
# light-weight XML support for Python 1.5.2 and later.
#
# history:
# 2001-10-20 fl   created (from various sources)
# 2001-11-01 fl   return root from parse method
# 2002-02-16 fl   sort attributes in lexical order
# 2002-04-06 fl   TreeBuilder refactoring, added PythonDoc markup
# 2002-05-01 fl   finished TreeBuilder refactoring
# 2002-07-14 fl   added basic namespace support to ElementTree.write
# 2002-07-25 fl   added QName attribute support
# 2002-10-20 fl   fixed encoding in write
# 2002-11-24 fl   changed default encoding to ascii; fixed attribute encoding
# 2002-11-27 fl   accept file objects or file names for parse/write
# 2002-12-04 fl   moved XMLTreeBuilder back to this module
# 2003-01-11 fl   fixed entity encoding glitch for us-ascii
# 2003-02-13 fl   added XML literal factory
# 2003-02-21 fl   added ProcessingInstruction/PI factory
# 2003-05-11 fl   added tostring/fromstring helpers
# 2003-05-26 fl   added ElementPath support
# 2003-07-05 fl   added makeelement factory method
# 2003-07-28 fl   added more well-known namespace prefixes
# 2003-08-15 fl   fixed typo in ElementTree.findtext (Thomas Dartsch)
# 2003-09-04 fl   fall back on emulator if ElementPath is not installed
# 2003-10-31 fl   markup updates
# 2003-11-15 fl   fixed nested namespace bug
# 2004-03-28 fl   added XMLID helper
# 2004-06-02 fl   added default support to findtext
# 2004-06-08 fl   fixed encoding of non-ascii element/attribute names
# 2004-08-23 fl   take advantage of post-2.1 expat features
# 2005-02-01 fl   added iterparse implementation
# 2005-03-02 fl   fixed iterparse support for pre-2.2 versions
#
# Copyright (c) 1999-2005 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2005 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

__all__ = [
    # public symbols
    "Comment",
    "dump",
    "Element", "ElementTree",
    "fromstring",
    "iselement", "iterparse",
    "parse",
    "PI", "ProcessingInstruction",
    "QName",
    "SubElement",
    "tostring",
    "TreeBuilder",
    "VERSION", "XML",
    "XMLTreeBuilder",
    ]

##
# The <b>Element</b> type is a flexible container object, designed to
# store hierarchical data structures in memory. The type can be
# described as a cross between a list and a dictionary.
# <p>
# Each element has a number of properties associated with it:
# <ul>
# <li>a <i>tag</i>. This is a string identifying what kind of data
# this element represents (the element type, in other words).</li>
# <li>a number of <i>attributes</i>, stored in a Python dictionary.</li>
# <li>a <i>text</i> string.</li>
# <li>an optional <i>tail</i> string.</li>
# <li>a number of <i>child elements</i>, stored in a Python sequence</li>
# </ul>
#
# To create an element instance, use the {@link #Element} or {@link
# #SubElement} factory functions.
# <p>
# The {@link #ElementTree} class can be used to wrap an element
# structure, and convert it from and to XML.
##

import string, sys, re

class _SimpleElementPath:
    # emulate pre-1.2 find/findtext/findall behaviour
    def find(self, element, tag):
        for elem in element:
            if elem.tag == tag:
                return elem
        return None
    def findtext(self, element, tag, default=None):
        for elem in element:
            if elem.tag == tag:
                return elem.text or ""
        return default
    def findall(self, element, tag):
        if tag[:3] == ".//":
            return element.getiterator(tag[3:])
        result = []
        for elem in element:
            if elem.tag == tag:
                result.append(elem)
        return result

try:
    import ElementPath
except ImportError:
    # FIXME: issue warning in this case?
    ElementPath = _SimpleElementPath()

# TODO: add support for custom namespace resolvers/default namespaces
# TODO: add improved support for incremental parsing

VERSION = "1.2.6"

##
# Internal element class.  This class defines the Element interface,
# and provides a reference implementation of this interface.
# <p>
# You should not create instances of this class directly.  Use the
# appropriate factory functions instead, such as {@link #Element}
# and {@link #SubElement}.
#
# @see Element
# @see SubElement
# @see Comment
# @see ProcessingInstruction

class _ElementInterface:
    # <tag attrib>text<child/>...</tag>tail

    ##
    # (Attribute) Element tag.

    tag = None

    ##
    # (Attribute) Element attribute dictionary.  Where possible, use
    # {@link #_ElementInterface.get},
    # {@link #_ElementInterface.set},
    # {@link #_ElementInterface.keys}, and
    # {@link #_ElementInterface.items} to access
    # element attributes.

    attrib = None

    ##
    # (Attribute) Text before first subelement.  This is either a
    # string or the value None, if there was no text.

    text = None

    ##
    # (Attribute) Text after this element's end tag, but before the
    # next sibling element's start tag.  This is either a string or
    # the value None, if there was no text.

    tail = None # text after end tag, if any

    def __init__(self, tag, attrib):
        self.tag = tag
        self.attrib = attrib
        self._children = []

    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))

    ##
    # Creates a new element object of the same type as this element.
    #
    # @param tag Element tag.
    # @param attrib Element attributes, given as a dictionary.
    # @return A new element instance.

    def makeelement(self, tag, attrib):
        return Element(tag, attrib)

    ##
    # Returns the number of subelements.
    #
    # @return The number of subelements.

    def __len__(self):
        return len(self._children)

    ##
    # Returns the given subelement.
    #
    # @param index What subelement to return.
    # @return The given subelement.
    # @exception IndexError If the given element does not exist.

    def __getitem__(self, index):
        return self._children[index]

    ##
    # Replaces the given subelement.
    #
    # @param index What subelement to replace.
    # @param element The new element value.
    # @exception IndexError If the given element does not exist.
    # @exception AssertionError If element is not a valid object.

    def __setitem__(self, index, element):
        assert iselement(element)
        self._children[index] = element

    ##
    # Deletes the given subelement.
    #
    # @param index What subelement to delete.
    # @exception IndexError If the given element does not exist.

    def __delitem__(self, index):
        del self._children[index]

    ##
    # Returns a list containing subelements in the given range.
    #
    # @param start The first subelement to return.
    # @param stop The first subelement that shouldn't be returned.
    # @return A sequence object containing subelements.

    def __getslice__(self, start, stop):
        return self._children[start:stop]

    ##
    # Replaces a number of subelements with elements from a sequence.
    #
    # @param start The first subelement to replace.
    # @param stop The first subelement that shouldn't be replaced.
    # @param elements A sequence object with zero or more elements.
    # @exception AssertionError If a sequence member is not a valid object.

    def __setslice__(self, start, stop, elements):
        for element in elements:
            assert iselement(element)
        self._children[start:stop] = list(elements)

    ##
    # Deletes a number of subelements.
    #
    # @param start The first subelement to delete.
    # @param stop The first subelement to leave in there.

    def __delslice__(self, start, stop):
        del self._children[start:stop]

    ##
    # Adds a subelement to the end of this element.
    #
    # @param element The element to add.
    # @exception AssertionError If a sequence member is not a valid object.

    def append(self, element):
        assert iselement(element)
        self._children.append(element)

    ##
    # Inserts a subelement at the given position in this element.
    #
    # @param index Where to insert the new subelement.
    # @exception AssertionError If the element is not a valid object.

    def insert(self, index, element):
        assert iselement(element)
        self._children.insert(index, element)

    ##
    # Removes a matching subelement.  Unlike the <b>find</b> methods,
    # this method compares elements based on identity, not on tag
    # value or contents.
    #
    # @param element What element to remove.
    # @exception ValueError If a matching element could not be found.
    # @exception AssertionError If the element is not a valid object.

    def remove(self, element):
        assert iselement(element)
        self._children.remove(element)

    ##
    # Returns all subelements.  The elements are returned in document
    # order.
    #
    # @return A list of subelements.
    # @defreturn list of Element instances

    def getchildren(self):
        return self._children

    ##
    # Finds the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        return ElementPath.find(self, path)

    ##
    # Finds text for the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        return ElementPath.findtext(self, path, default)

    ##
    # Finds all matching subelements, by tag name or path.
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        return ElementPath.findall(self, path)

    ##
    # Resets an element.  This function removes all subelements, clears
    # all attributes, and sets the text and tail attributes to None.

    def clear(self):
        self.attrib.clear()
        self._children = []
        self.text = self.tail = None

    ##
    # Gets an element attribute.
    #
    # @param key What attribute to look for.
    # @param default What to return if the attribute was not found.
    # @return The attribute value, or the default value, if the
    #     attribute was not found.
    # @defreturn string or None

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    ##
    # Sets an element attribute.
    #
    # @param key What attribute to set.
    # @param value The attribute value.

    def set(self, key, value):
        self.attrib[key] = value

    ##
    # Gets a list of attribute names.  The names are returned in an
    # arbitrary order (just like for an ordinary Python dictionary).
    #
    # @return A list of element attribute names.
    # @defreturn list of strings

    def keys(self):
        return self.attrib.keys()

    ##
    # Gets element attributes, as a sequence.  The attributes are
    # returned in an arbitrary order.
    #
    # @return A list of (name, value) tuples for all attributes.
    # @defreturn list of (string, string) tuples

    def items(self):
        return self.attrib.items()

    ##
    # Creates a tree iterator.  The iterator loops over this element
    # and all subelements, in document order, and returns all elements
    # with a matching tag.
    # <p>
    # If the tree structure is modified during iteration, the result
    # is undefined.
    #
    # @param tag What tags to look for (default is to return all elements).
    # @return A list or iterator containing all the matching elements.
    # @defreturn list or iterator

    def getiterator(self, tag=None):
        nodes = []
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            nodes.append(self)
        for node in self._children:
            nodes.extend(node.getiterator(tag))
        return nodes

# compatibility
_Element = _ElementInterface

##
# Element factory.  This function returns an object implementing the
# standard Element interface.  The exact class or type of that object
# is implementation dependent, but it will always be compatible with
# the {@link #_ElementInterface} class in this module.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param tag The element name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @return An element instance.
# @defreturn Element

def Element(tag, attrib={}, **extra):
    attrib = attrib.copy()
    attrib.update(extra)
    return _ElementInterface(tag, attrib)

##
# Subelement factory.  This function creates an element instance, and
# appends it to an existing element.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param parent The parent element.
# @param tag The subelement name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @return An element instance.
# @defreturn Element

def SubElement(parent, tag, attrib={}, **extra):
    attrib = attrib.copy()
    attrib.update(extra)
    element = parent.makeelement(tag, attrib)
    parent.append(element)
    return element

##
# Comment element factory.  This factory function creates a special
# element that will be serialized as an XML comment.
# <p>
# The comment string can be either an 8-bit ASCII string or a Unicode
# string.
#
# @param text A string containing the comment string.
# @return An element instance, representing a comment.
# @defreturn Element

def Comment(text=None):
    element = Element(Comment)
    element.text = text
    return element

##
# PI element factory.  This factory function creates a special element
# that will be serialized as an XML processing instruction.
#
# @param target A string containing the PI target.
# @param text A string containing the PI contents, if any.
# @return An element instance, representing a PI.
# @defreturn Element

def ProcessingInstruction(target, text=None):
    element = Element(ProcessingInstruction)
    element.text = target
    if text:
        element.text = element.text + " " + text
    return element

PI = ProcessingInstruction

##
# QName wrapper.  This can be used to wrap a QName attribute value, in
# order to get proper namespace handling on output.
#
# @param text A string containing the QName value, in the form {uri}local,
#     or, if the tag argument is given, the URI part of a QName.
# @param tag Optional tag.  If given, the first argument is interpreted as
#     an URI, and this argument is interpreted as a local name.
# @return An opaque object, representing the QName.

class QName:
    def __init__(self, text_or_uri, tag=None):
        if tag:
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return hash(self.text)
    def __cmp__(self, other):
        if isinstance(other, QName):
            return cmp(self.text, other.text)
        return cmp(self.text, other)

##
# ElementTree wrapper class.  This class represents an entire element
# hierarchy, and adds some extra support for serialization to and from
# standard XML.
#
# @param element Optional root element.
# @keyparam file Optional file handle or name.  If given, the
#     tree is initialized with the contents of this XML file.

class ElementTree:

    def __init__(self, element=None, file=None):
        assert element is None or iselement(element)
        self._root = element # first node
        if file:
            self.parse(file)

    ##
    # Gets the root element for this tree.
    #
    # @return An element instance.
    # @defreturn Element

    def getroot(self):
        return self._root

    ##
    # Replaces the root element for this tree.  This discards the
    # current contents of the tree, and replaces it with the given
    # element.  Use with care.
    #
    # @param element An element instance.

    def _setroot(self, element):
        assert iselement(element)
        self._root = element

    ##
    # Loads an external XML document into this element tree.
    #
    # @param source A file name or file object.
    # @param parser An optional parser instance.  If not given, the
    #     standard {@link XMLTreeBuilder} parser is used.
    # @return The document root element.
    # @defreturn Element

    def parse(self, source, parser=None):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        if not parser:
            parser = XMLTreeBuilder()
        while 1:
            data = source.read(32768)
            if not data:
                break
            parser.feed(data)
        self._root = parser.close()
        return self._root

    ##
    # Creates a tree iterator for the root element.  The iterator loops
    # over all elements in this tree, in document order.
    #
    # @param tag What tags to look for (default is to return all elements)
    # @return An iterator.
    # @defreturn iterator

    def getiterator(self, tag=None):
        assert self._root is not None
        return self._root.getiterator(tag)

    ##
    # Finds the first toplevel element with given tag.
    # Same as getroot().find(path).
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.find(path)

    ##
    # Finds the element text for the first toplevel element with given
    # tag.  Same as getroot().findtext(path).
    #
    # @param path What toplevel element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.findtext(path, default)

    ##
    # Finds all toplevel elements with the given tag.
    # Same as getroot().findall(path).
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
        return self._root.findall(path)

    ##
    # Writes the element tree to a file, as XML.
    #
    # @param file A file name, or a file object opened for writing.
    # @param encoding Optional output encoding (default is US-ASCII).

    def write(self, file, encoding="us-ascii"):
        assert self._root is not None
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not encoding:
            encoding = "us-ascii"
        elif encoding != "utf-8" and encoding != "us-ascii":
            file.write("<?xml version='1.0' encoding='%s'?>\n" % encoding)
        self._write(file, self._root, encoding, {})

    def _write(self, file, node, encoding, namespaces):
        # write XML to file
        tag = node.tag
        if tag is Comment:
            file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
        elif tag is ProcessingInstruction:
            file.write("<?%s?>" % _escape_cdata(node.text, encoding))
        else:
            items = node.items()
            xmlns_items = [] # new namespaces in this scope
            try:
                if isinstance(tag, QName) or tag[:1] == "{":
                    tag, xmlns = fixtag(tag, namespaces)
                    if xmlns: xmlns_items.append(xmlns)
            except TypeError:
                _raise_serialization_error(tag)
            file.write("<" + _encode(tag, encoding))
            if items or xmlns_items:
                items.sort() # lexical order
                for k, v in items:
                    try:
                        if isinstance(k, QName) or k[:1] == "{":
                            k, xmlns = fixtag(k, namespaces)
                            if xmlns: xmlns_items.append(xmlns)
                    except TypeError:
                        _raise_serialization_error(k)
                    try:
                        if isinstance(v, QName):
                            v, xmlns = fixtag(v, namespaces)
                            if xmlns: xmlns_items.append(xmlns)
                    except TypeError:
                        _raise_serialization_error(v)
                    file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                               _escape_attrib(v, encoding)))
                for k, v in xmlns_items:
                    file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                               _escape_attrib(v, encoding)))
            if node.text or len(node):
                file.write(">")
                if node.text:
                    file.write(_escape_cdata(node.text, encoding))
                for n in node:
                    self._write(file, n, encoding, namespaces)
                file.write("</" + _encode(tag, encoding) + ">")
            else:
                file.write(" />")
            for k, v in xmlns_items:
                del namespaces[v]
        if node.tail:
            file.write(_escape_cdata(node.tail, encoding))

# --------------------------------------------------------------------
# helpers

##
# Checks if an object appears to be a valid element object.
#
# @param An element instance.
# @return A true value if this is an element object.
# @defreturn flag

def iselement(element):
    # FIXME: not sure about this; might be a better idea to look
    # for tag/attrib/text attributes
    return isinstance(element, _ElementInterface) or hasattr(element, "tag")

##
# Writes an element tree or element structure to sys.stdout.  This
# function should be used for debugging only.
# <p>
# The exact output format is implementation dependent.  In this
# version, it's written as an ordinary XML file.
#
# @param elem An element tree or an individual element.

def dump(elem):
    # debugging
    if not isinstance(elem, ElementTree):
        elem = ElementTree(elem)
    elem.write(sys.stdout)
    tail = elem.getroot().tail
    if not tail or tail[-1] != "\n":
        sys.stdout.write("\n")

def _encode(s, encoding):
    try:
        return s.encode(encoding)
    except AttributeError:
        return s # 1.5.2: assume the string uses the right encoding

if sys.version[:3] == "1.5":
    _escape = re.compile(r"[&<>\"\x80-\xff]+") # 1.5.2
else:
    _escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

_escape_map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
}

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
}

def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode_entity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escape_entities(m, map=_escape_map):
        out = []
        append = out.append
        for char in m.group():
            text = map.get(char)
            if text is None:
                text = "&#%d;" % ord(char)
            append(text)
        return string.join(out, "")
    try:
        return _encode(pattern.sub(escape_entities, text), "ascii")
    except TypeError:
        _raise_serialization_error(text)

#
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

def _escape_cdata(text, encoding=None, replace=string.replace):
    # escape character data
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encode_entity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib(text, encoding=None, replace=string.replace):
    # escape attribute value
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encode_entity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "'", "&apos;") # FIXME: overkill
        text = replace(text, "\"", "&quot;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def fixtag(tag, namespaces):
    # given a decorated tag (of the form {uri}tag), return prefixed
    # tag and namespace declaration, if any
    if isinstance(tag, QName):
        tag = tag.text
    namespace_uri, tag = string.split(tag[1:], "}", 1)
    prefix = namespaces.get(namespace_uri)
    if prefix is None:
        prefix = _namespace_map.get(namespace_uri)
        if prefix is None:
            prefix = "ns%d" % len(namespaces)
        namespaces[namespace_uri] = prefix
        if prefix == "xml":
            xmlns = None
        else:
            xmlns = ("xmlns:%s" % prefix, namespace_uri)
    else:
        xmlns = None
    return "%s:%s" % (prefix, tag), xmlns

##
# Parses an XML document into an element tree.
#
# @param source A filename or file object containing XML data.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLTreeBuilder} parser is used.
# @return An ElementTree instance

def parse(source, parser=None):
    tree = ElementTree()
    tree.parse(source, parser)
    return tree

##
# Parses an XML document into an element tree incrementally, and reports
# what's going on to the user.
#
# @param source A filename or file object containing XML data.
# @param events A list of events to report back.  If omitted, only "end"
#     events are reported.
# @return A (event, elem) iterator.

class iterparse:

    def __init__(self, source, events=None):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        self._file = source
        self._events = []
        self._index = 0
        self.root = self._root = None
        self._parser = XMLTreeBuilder()
        # wire up the parser for event reporting
        parser = self._parser._parser
        append = self._events.append
        if events is None:
            events = ["end"]
        for event in events:
            if event == "start":
                try:
                    parser.ordered_attributes = 1
                    parser.specified_attributes = 1
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start_list):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
                except AttributeError:
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
            elif event == "end":
                def handler(tag, event=event, append=append,
                            end=self._parser._end):
                    append((event, end(tag)))
                parser.EndElementHandler = handler
            elif event == "start-ns":
                def handler(prefix, uri, event=event, append=append):
                    try:
                        uri = _encode(uri, "ascii")
                    except UnicodeError:
                        pass
                    append((event, (prefix or "", uri)))
                parser.StartNamespaceDeclHandler = handler
            elif event == "end-ns":
                def handler(prefix, event=event, append=append):
                    append((event, None))
                parser.EndNamespaceDeclHandler = handler

    def next(self):
        while 1:
            try:
                item = self._events[self._index]
            except IndexError:
                if self._parser is None:
                    self.root = self._root
                    try:
                        raise StopIteration
                    except NameError:
                        raise IndexError
                # load event buffer
                del self._events[:]
                self._index = 0
                data = self._file.read(16384)
                if data:
                    self._parser.feed(data)
                else:
                    self._root = self._parser.close()
                    self._parser = None
            else:
                self._index = self._index + 1
                return item

    try:
        iter
        def __iter__(self):
            return self
    except NameError:
        def __getitem__(self, index):
            return self.next()

##
# Parses an XML document from a string constant.  This function can
# be used to embed "XML literals" in Python code.
#
# @param source A string containing XML data.
# @return An Element instance.
# @defreturn Element

def XML(text):
    parser = XMLTreeBuilder()
    parser.feed(text)
    return parser.close()

##
# Parses an XML document from a string constant, and also returns
# a dictionary which maps from element id:s to elements.
#
# @param source A string containing XML data.
# @return A tuple containing an Element instance and a dictionary.
# @defreturn (Element, dictionary)

def XMLID(text):
    parser = XMLTreeBuilder()
    parser.feed(text)
    tree = parser.close()
    ids = {}
    for elem in tree.getiterator():
        id = elem.get("id")
        if id:
            ids[id] = elem
    return tree, ids

##
# Parses an XML document from a string constant.  Same as {@link #XML}.
#
# @def fromstring(text)
# @param source A string containing XML data.
# @return An Element instance.
# @defreturn Element

fromstring = XML

##
# Generates a string representation of an XML element, including all
# subelements.
#
# @param element An Element instance.
# @return An encoded string containing the XML data.
# @defreturn string

def tostring(element, encoding=None):
    class dummy:
        pass
    data = []
    file = dummy()
    file.write = data.append
    ElementTree(element).write(file, encoding)
    return string.join(data, "")

##
# Generic element structure builder.  This builder converts a sequence
# of {@link #TreeBuilder.start}, {@link #TreeBuilder.data}, and {@link
# #TreeBuilder.end} method calls to a well-formed element structure.
# <p>
# You can use this class to build an element structure using a custom XML
# parser, or a parser for some other XML-like format.
#
# @param element_factory Optional element factory.  This factory
#    is called to create new Element instances, as necessary.

class TreeBuilder:

    def __init__(self, element_factory=None):
        self._data = [] # data collector
        self._elem = [] # element stack
        self._last = None # last element
        self._tail = None # true if we're after an end tag
        if element_factory is None:
            element_factory = _ElementInterface
        self._factory = element_factory

    ##
    # Flushes the parser buffers, and returns the toplevel documen
    # element.
    #
    # @return An Element instance.
    # @defreturn Element

    def close(self):
        assert len(self._elem) == 0, "missing end tags"
        assert self._last != None, "missing toplevel element"
        return self._last

    def _flush(self):
        if self._data:
            if self._last is not None:
                text = string.join(self._data, "")
                if self._tail:
                    assert self._last.tail is None, "internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, "internal error (text)"
                    self._last.text = text
            self._data = []

    ##
    # Adds text to the current element.
    #
    # @param data A string.  This should be either an 8-bit string
    #    containing ASCII text, or a Unicode string.

    def data(self, data):
        self._data.append(data)

    ##
    # Opens a new element.
    #
    # @param tag The element name.
    # @param attrib A dictionary containing element attributes.
    # @return The opened element.
    # @defreturn Element

    def start(self, tag, attrs):
        self._flush()
        self._last = elem = self._factory(tag, attrs)
        if self._elem:
            self._elem[-1].append(elem)
        self._elem.append(elem)
        self._tail = 0
        return elem

    ##
    # Closes the current element.
    #
    # @param tag The element name.
    # @return The closed element.
    # @defreturn Element

    def end(self, tag):
        self._flush()
        self._last = self._elem.pop()
        assert self._last.tag == tag,\
               "end tag mismatch (expected %s, got %s)" % (
                   self._last.tag, tag)
        self._tail = 1
        return self._last

##
# Element structure builder for XML source data, based on the
# <b>expat</b> parser.
#
# @keyparam target Target object.  If omitted, the builder uses an
#     instance of the standard {@link #TreeBuilder} class.
# @keyparam html Predefine HTML entities.  This flag is not supported
#     by the current implementation.
# @see #ElementTree
# @see #TreeBuilder

class XMLTreeBuilder:

    def __init__(self, html=0, target=None):
        try:
            from xml.parsers import expat
        except ImportError:
            raise ImportError(
                "No module named expat; use SimpleXMLTreeBuilder instead"
                )
        self._parser = parser = expat.ParserCreate(None, "}")
        if target is None:
            target = TreeBuilder()
        self._target = target
        self._names = {} # name memo cache
        # callbacks
        parser.DefaultHandlerExpand = self._default
        parser.StartElementHandler = self._start
        parser.EndElementHandler = self._end
        parser.CharacterDataHandler = self._data
        # let expat do the buffering, if supported
        try:
            self._parser.buffer_text = 1
        except AttributeError:
            pass
        # use new-style attribute handling, if supported
        try:
            self._parser.ordered_attributes = 1
            self._parser.specified_attributes = 1
            parser.StartElementHandler = self._start_list
        except AttributeError:
            pass
        encoding = None
        if not parser.returns_unicode:
            encoding = "utf-8"
        # target.xml(encoding, None)
        self._doctype = None
        self.entity = {}

    def _fixtext(self, text):
        # convert text string to ascii, if possible
        try:
            return _encode(text, "ascii")
        except UnicodeError:
            return text

    def _fixname(self, key):
        # expand qname, and convert name string to ascii, if possible
        try:
            name = self._names[key]
        except KeyError:
            name = key
            if "}" in name:
                name = "{" + name
            self._names[key] = name = self._fixtext(name)
        return name

    def _start(self, tag, attrib_in):
        fixname = self._fixname
        tag = fixname(tag)
        attrib = {}
        for key, value in attrib_in.items():
            attrib[fixname(key)] = self._fixtext(value)
        return self._target.start(tag, attrib)

    def _start_list(self, tag, attrib_in):
        fixname = self._fixname
        tag = fixname(tag)
        attrib = {}
        if attrib_in:
            for i in range(0, len(attrib_in), 2):
                attrib[fixname(attrib_in[i])] = self._fixtext(attrib_in[i+1])
        return self._target.start(tag, attrib)

    def _data(self, text):
        return self._target.data(self._fixtext(text))

    def _end(self, tag):
        return self._target.end(self._fixname(tag))

    def _default(self, text):
        prefix = text[:1]
        if prefix == "&":
            # deal with undefined entities
            try:
                self._target.data(self.entity[text[1:-1]])
            except KeyError:
                from xml.parsers import expat
                raise expat.error(
                    "undefined entity %s: line %d, column %d" %
                    (text, self._parser.ErrorLineNumber,
                    self._parser.ErrorColumnNumber)
                    )
        elif prefix == "<" and text[:9] == "<!DOCTYPE":
            self._doctype = [] # inside a doctype declaration
        elif self._doctype is not None:
            # parse doctype contents
            if prefix == ">":
                self._doctype = None
                return
            text = string.strip(text)
            if not text:
                return
            self._doctype.append(text)
            n = len(self._doctype)
            if n > 2:
                type = self._doctype[1]
                if type == "PUBLIC" and n == 4:
                    name, type, pubid, system = self._doctype
                elif type == "SYSTEM" and n == 3:
                    name, type, system = self._doctype
                    pubid = None
                else:
                    return
                if pubid:
                    pubid = pubid[1:-1]
                self.doctype(name, pubid, system[1:-1])
                self._doctype = None

    ##
    # Handles a doctype declaration.
    #
    # @param name Doctype name.
    # @param pubid Public identifier.
    # @param system System identifier.

    def doctype(self, name, pubid, system):
        pass

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        self._parser.Parse(data, 0)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        self._parser.Parse("", 1) # end of data
        tree = self._target.close()
        del self._target, self._parser # get rid of circular references
        return tree

########NEW FILE########
__FILENAME__ = HTMLTreeBuilder
#
# ElementTree
# $Id: HTMLTreeBuilder.py 2325 2005-03-16 15:50:43Z fredrik $
#
# a simple tree builder, for HTML input
#
# history:
# 2002-04-06 fl   created
# 2002-04-07 fl   ignore IMG and HR end tags
# 2002-04-07 fl   added support for 1.5.2 and later
# 2003-04-13 fl   added HTMLTreeBuilder alias
# 2004-12-02 fl   don't feed non-ASCII charrefs/entities as 8-bit strings
# 2004-12-05 fl   don't feed non-ASCII CDATA as 8-bit strings
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from HTML files.
##

import htmlentitydefs
import re, string, sys
import mimetools, StringIO

import ElementTree

AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
IGNOREEND = "img", "hr", "meta", "link", "br"

if sys.version[:3] == "1.5":
    is_not_ascii = re.compile(r"[\x80-\xff]").search # 1.5.2
else:
    is_not_ascii = re.compile(eval(r'u"[\u0080-\uffff]"')).search

try:
    from HTMLParser import HTMLParser
except ImportError:
    from sgmllib import SGMLParser
    # hack to use sgmllib's SGMLParser to emulate 2.2's HTMLParser
    class HTMLParser(SGMLParser):
        # the following only works as long as this class doesn't
        # provide any do, start, or end handlers
        def unknown_starttag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
        def unknown_endtag(self, tag):
            self.handle_endtag(tag)

##
# ElementTree builder for HTML source code.  This builder converts an
# HTML document or fragment to an ElementTree.
# <p>
# The parser is relatively picky, and requires balanced tags for most
# elements.  However, elements belonging to the following group are
# automatically closed: P, LI, TR, TH, and TD.  In addition, the
# parser automatically inserts end tags immediately after the start
# tag, and ignores any end tags for the following group: IMG, HR,
# META, and LINK.
#
# @keyparam builder Optional builder object.  If omitted, the parser
#     uses the standard <b>elementtree</b> builder.
# @keyparam encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.  Note that if your
#     document uses a non-ASCII compatible encoding, you must decode
#     the document before parsing.
#
# @see elementtree.ElementTree

class HTMLTreeBuilder(HTMLParser):

    # FIXME: shouldn't this class be named Parser, not Builder?

    def __init__(self, builder=None, encoding=None):
        self.__stack = []
        if builder is None:
            builder = ElementTree.TreeBuilder()
        self.__builder = builder
        self.encoding = encoding or "iso-8859-1"
        HTMLParser.__init__(self)

    ##
    # Flushes parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        HTMLParser.close(self)
        return self.__builder.close()

    ##
    # (Internal) Handles start tags.

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            # look for encoding directives
            http_equiv = content = None
            for k, v in attrs:
                if k == "http-equiv":
                    http_equiv = string.lower(v)
                elif k == "content":
                    content = v
            if http_equiv == "content-type" and content:
                # use mimetools to parse the http header
                header = mimetools.Message(
                    StringIO.StringIO("%s: %s\n\n" % (http_equiv, content))
                    )
                encoding = header.getparam("charset")
                if encoding:
                    self.encoding = encoding
        if tag in AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for k, v in attrs:
                attrib[string.lower(k)] = v
        self.__builder.start(tag, attrib)
        if tag in IGNOREEND:
            self.__stack.pop()
            self.__builder.end(tag)

    ##
    # (Internal) Handles end tags.

    def handle_endtag(self, tag):
        if tag in IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.__builder.end(tag)

    ##
    # (Internal) Handles character references.

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.__builder.data(chr(char))
        else:
            self.__builder.data(unichr(char))

    ##
    # (Internal) Handles entity references.

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.__builder.data(chr(entity))
            else:
                self.__builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    ##
    # (Internal) Handles character data.

    def handle_data(self, data):
        if isinstance(data, type('')) and is_not_ascii(data):
            # convert to unicode, but only if necessary
            data = unicode(data, self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary

##
# An alias for the <b>HTMLTreeBuilder</b> class.

TreeBuilder = HTMLTreeBuilder

##
# Parse an HTML document or document fragment.
#
# @param source A filename or file object containing HTML data.
# @param encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.
# @return An ElementTree instance

def parse(source, encoding=None):
    return ElementTree.parse(source, HTMLTreeBuilder(encoding=encoding))

if __name__ == "__main__":
    import sys
    ElementTree.dump(parse(open(sys.argv[1])))

########NEW FILE########
__FILENAME__ = SgmlopXMLTreeBuilder
#
# ElementTree
# $Id$
#
# A simple XML tree builder, based on the sgmlop library.
#
# Note that this version does not support namespaces.  This may be
# changed in future versions.
#
# history:
# 2004-03-28 fl   created
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML, based on the SGMLOP parser.
# <p>
# The current version does not support XML namespaces.
# <p>
# This tree builder requires the <b>sgmlop</b> extension module
# (available from
# <a href='http://effbot.org/downloads'>http://effbot.org/downloads</a>).
##

import ElementTree

##
# ElementTree builder for XML source data, based on the SGMLOP parser.
#
# @see elementtree.ElementTree

class TreeBuilder:

    def __init__(self, html=0):
        try:
            import sgmlop
        except ImportError:
            raise RuntimeError("sgmlop parser not available")
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        self.__parser = sgmlop.XMLParser()
        self.__parser.register(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        self.__parser.feed(data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        self.__parser.close()
        self.__parser = None
        return self.__builder.close()

    def finish_starttag(self, tag, attrib):
        self.__builder.start(tag, attrib)

    def finish_endtag(self, tag):
        self.__builder.end(tag)

    def handle_data(self, data):
        self.__builder.data(data)

########NEW FILE########
__FILENAME__ = SimpleXMLTreeBuilder
#
# ElementTree
# $Id: SimpleXMLTreeBuilder.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# A simple XML tree builder, based on Python's xmllib
#
# Note that due to bugs in xmllib, this builder does not fully support
# namespaces (unqualified attributes are put in the default namespace,
# instead of being left as is).  Run this module as a script to find
# out if this affects your Python version.
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-08-17 fl   added xmllib sanity test
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML files, using <b>xmllib</b>.
# This module can be used instead of the standard tree builder, for
# Python versions where "expat" is not available (such as 1.5.2).
# <p>
# Note that due to bugs in <b>xmllib</b>, the namespace support is
# not reliable (you can run the module as a script to find out exactly
# how unreliable it is on your Python version).
##

import xmllib, string

import ElementTree

##
# ElementTree builder for XML source data.
#
# @see elementtree.ElementTree

class TreeBuilder(xmllib.XMLParser):

    def __init__(self, html=0):
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        xmllib.XMLParser.__init__(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        xmllib.XMLParser.feed(self, data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        xmllib.XMLParser.close(self)
        return self.__builder.close()

    def handle_data(self, data):
        self.__builder.data(data)

    handle_cdata = handle_data

    def unknown_starttag(self, tag, attrs):
        attrib = {}
        for key, value in attrs.items():
            attrib[fixname(key)] = value
        self.__builder.start(fixname(tag), attrib)

    def unknown_endtag(self, tag):
        self.__builder.end(fixname(tag))


def fixname(name, split=string.split):
    # xmllib in 2.0 and later provides limited (and slightly broken)
    # support for XML namespaces.
    if " " not in name:
        return name
    return "{%s}%s" % tuple(split(name, " ", 1))


if __name__ == "__main__":
    import sys
    # sanity check: look for known namespace bugs in xmllib
    p = TreeBuilder()
    text = """\
    <root xmlns='default'>
       <tag attribute='value' />
    </root>
    """
    p.feed(text)
    tree = p.close()
    status = []
    # check for bugs in the xmllib implementation
    tag = tree.find("{default}tag")
    if tag is None:
        status.append("namespaces not supported")
    if tag is not None and tag.get("{default}attribute"):
        status.append("default namespace applied to unqualified attribute")
    # report bugs
    if status:
        print "xmllib doesn't work properly in this Python version:"
        for bug in status:
            print "-", bug
    else:
        print "congratulations; no problems found in xmllib"


########NEW FILE########
__FILENAME__ = SimpleXMLWriter
#
# SimpleXMLWriter
# $Id: SimpleXMLWriter.py 2312 2005-03-02 18:13:39Z fredrik $
#
# a simple XML writer
#
# history:
# 2001-12-28 fl   created
# 2002-11-25 fl   fixed attribute encoding
# 2002-12-02 fl   minor fixes for 1.5.2
# 2004-06-17 fl   added pythondoc markup
# 2004-07-23 fl   added flush method (from Jay Graves)
# 2004-10-03 fl   added declaration method
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The SimpleXMLWriter module is
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to write XML files, without having to deal with encoding
# issues, well-formedness, etc.
# <p>
# The current version does not provide built-in support for
# namespaces. To create files using namespaces, you have to provide
# "xmlns" attributes and explicitly add prefixes to tags and
# attributes.
#
# <h3>Patterns</h3>
#
# The following example generates a small XHTML document.
# <pre>
#
# from elementtree.SimpleXMLWriter import XMLWriter
# import sys
#
# w = XMLWriter(sys.stdout)
#
# html = w.start("html")
#
# w.start("head")
# w.element("title", "my document")
# w.element("meta", name="generator", value="my application 1.0")
# w.end()
#
# w.start("body")
# w.element("h1", "this is a heading")
# w.element("p", "this is a paragraph")
#
# w.start("p")
# w.data("this is ")
# w.element("b", "bold")
# w.data(" and ")
# w.element("i", "italic")
# w.data(".")
# w.end("p")
#
# w.close(html)
# </pre>
##

import re, sys, string

try:
    unicode("")
except NameError:
    def encode(s, encoding):
        # 1.5.2: application must use the right encoding
        return s
    _escape = re.compile(r"[&<>\"\x80-\xff]+") # 1.5.2
else:
    def encode(s, encoding):
        return s.encode(encoding)
    _escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

def encode_entity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escape_entities(m):
        out = []
        for char in m.group():
            out.append("&#%d;" % ord(char))
        return string.join(out, "")
    return encode(pattern.sub(escape_entities, text), "ascii")

del _escape

#
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

def escape_cdata(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

def escape_attrib(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "'", "&apos;")
    s = replace(s, "\"", "&quot;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

##
# XML writer class.
#
# @param file A file or file-like object.  This object must implement
#    a <b>write</b> method that takes an 8-bit string.
# @param encoding Optional encoding.

class XMLWriter:

    def __init__(self, file, encoding="us-ascii"):
        if not hasattr(file, "write"):
            file = open(file, "w")
        self.__write = file.write
        if hasattr(file, "flush"):
            self.flush = file.flush
        self.__open = 0 # true if start tag is open
        self.__tags = []
        self.__data = []
        self.__encoding = encoding

    def __flush(self):
        # flush internal buffers
        if self.__open:
            self.__write(">")
            self.__open = 0
        if self.__data:
            data = string.join(self.__data, "")
            self.__write(escape_cdata(data, self.__encoding))
            self.__data = []

    ##
    # Writes an XML declaration.

    def declaration(self):
        encoding = self.__encoding
        if encoding == "us-ascii" or encoding == "utf-8":
            self.__write("<?xml version='1.0'?>\n")
        else:
            self.__write("<?xml version='1.0' encoding='%s'?>\n" % encoding)

    ##
    # Opens a new element.  Attributes can be given as keyword
    # arguments, or as a string/string dictionary. You can pass in
    # 8-bit strings or Unicode strings; the former are assumed to use
    # the encoding passed to the constructor.  The method returns an
    # opaque identifier that can be passed to the <b>close</b> method,
    # to close all open elements up to and including this one.
    #
    # @param tag Element tag.
    # @param attrib Attribute dictionary.  Alternatively, attributes
    #    can be given as keyword arguments.
    # @return An element identifier.

    def start(self, tag, attrib={}, **extra):
        self.__flush()
        tag = escape_cdata(tag, self.__encoding)
        self.__data = []
        self.__tags.append(tag)
        self.__write("<%s" % tag)
        if attrib or extra:
            attrib = attrib.copy()
            attrib.update(extra)
            attrib = attrib.items()
            attrib.sort()
            for k, v in attrib:
                k = escape_cdata(k, self.__encoding)
                v = escape_attrib(v, self.__encoding)
                self.__write(" %s=\"%s\"" % (k, v))
        self.__open = 1
        return len(self.__tags)-1

    ##
    # Adds a comment to the output stream.
    #
    # @param comment Comment text, as an 8-bit string or Unicode string.

    def comment(self, comment):
        self.__flush()
        self.__write("<!-- %s -->\n" % escape_cdata(comment, self.__encoding))

    ##
    # Adds character data to the output stream.
    #
    # @param text Character data, as an 8-bit string or Unicode string.

    def data(self, text):
        self.__data.append(text)

    ##
    # Closes the current element (opened by the most recent call to
    # <b>start</b>).
    #
    # @param tag Element tag.  If given, the tag must match the start
    #    tag.  If omitted, the current element is closed.

    def end(self, tag=None):
        if tag:
            assert self.__tags, "unbalanced end(%s)" % tag
            assert escape_cdata(tag, self.__encoding) == self.__tags[-1],\
                   "expected end(%s), got %s" % (self.__tags[-1], tag)
        else:
            assert self.__tags, "unbalanced end()"
        tag = self.__tags.pop()
        if self.__data:
            self.__flush()
        elif self.__open:
            self.__open = 0
            self.__write(" />")
            return
        self.__write("</%s>" % tag)

    ##
    # Closes open elements, up to (and including) the element identified
    # by the given identifier.
    #
    # @param id Element identifier, as returned by the <b>start</b> method.

    def close(self, id):
        while len(self.__tags) > id:
            self.end()

    ##
    # Adds an entire element.  This is the same as calling <b>start</b>,
    # <b>data</b>, and <b>end</b> in sequence. The <b>text</b> argument
    # can be omitted.

    def element(self, tag, text=None, attrib={}, **extra):
        apply(self.start, (tag, attrib), extra)
        if text:
            self.data(text)
        self.end()

    ##
    # Flushes the output stream.

    def flush(self):
        pass # replaced by the constructor

########NEW FILE########
__FILENAME__ = TidyHTMLTreeBuilder
#
# ElementTree
# $Id: TidyHTMLTreeBuilder.py 2304 2005-03-01 17:42:41Z fredrik $
#

from elementtidy.TidyHTMLTreeBuilder import *

########NEW FILE########
__FILENAME__ = TidyTools
#
# ElementTree
# $Id: TidyTools.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# tools to run the "tidy" command on an HTML or XHTML file, and return
# the contents as an XHTML element tree.
#
# history:
# 2002-10-19 fl   added to ElementTree library; added getzonebody function
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#

##
# Tools to build element trees from HTML, using the external <b>tidy</b>
# utility.
##

import glob, string, os, sys

from ElementTree import ElementTree, Element

NS_XHTML = "{http://www.w3.org/1999/xhtml}"

##
# Convert an HTML or HTML-like file to XHTML, using the <b>tidy</b>
# command line utility.
#
# @param file Filename.
# @param new_inline_tags An optional list of valid but non-standard
#     inline tags.
# @return An element tree, or None if not successful.

def tidy(file, new_inline_tags=None):

    command = ["tidy", "-qn", "-asxml"]

    if new_inline_tags:
        command.append("--new-inline-tags")
        command.append(string.join(new_inline_tags, ","))

    # FIXME: support more tidy options!

    # convert
    os.system(
        "%s %s >%s.out 2>%s.err" % (string.join(command), file, file, file)
        )
    # check that the result is valid XML
    try:
        tree = ElementTree()
        tree.parse(file + ".out")
    except:
        print "*** %s:%s" % sys.exc_info()[:2]
        print ("*** %s is not valid XML "
               "(check %s.err for info)" % (file, file))
        tree = None
    else:
        if os.path.isfile(file + ".out"):
            os.remove(file + ".out")
        if os.path.isfile(file + ".err"):
            os.remove(file + ".err")

    return tree

##
# Get document body from a an HTML or HTML-like file.  This function
# uses the <b>tidy</b> function to convert HTML to XHTML, and cleans
# up the resulting XML tree.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getbody(file, **options):
    # get clean body from text file

    # get xhtml tree
    try:
        tree = apply(tidy, (file,), options)
        if tree is None:
            return
    except IOError, v:
        print "***", v
        return None

    NS = NS_XHTML

    # remove namespace uris
    for node in tree.getiterator():
        if node.tag.startswith(NS):
            node.tag = node.tag[len(NS):]

    body = tree.getroot().find("body")

    return body

##
# Same as <b>getbody</b>, but turns plain text at the start of the
# document into an H1 tag.  This function can be used to parse zone
# documents.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getzonebody(file, **options):

    body = getbody(file, **options)
    if body is None:
        return

    if body.text and string.strip(body.text):
        title = Element("h1")
        title.text = string.strip(body.text)
        title.tail = "\n\n"
        body.insert(0, title)

    body.text = None

    return body

if __name__ == "__main__":

    import sys
    for arg in sys.argv[1:]:
        for file in glob.glob(arg):
            print file, "...", tidy(file)

########NEW FILE########
__FILENAME__ = XMLTreeBuilder
#
# ElementTree
# $Id: XMLTreeBuilder.py 2305 2005-03-01 17:43:09Z fredrik $
#
# an XML tree builder
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-07-27 fl   require expat (1.5.2 code can use SimpleXMLTreeBuilder)
# 2002-08-17 fl   use tag/attribute name memo cache
# 2002-12-04 fl   moved XMLTreeBuilder to the ElementTree module
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Tools to build element trees from XML files.
##

import ElementTree

##
# (obsolete) ElementTree builder for XML source data, based on the
# <b>expat</b> parser.
# <p>
# This class is an alias for ElementTree.XMLTreeBuilder.  New code
# should use that version instead.
#
# @see elementtree.ElementTree

class TreeBuilder(ElementTree.XMLTreeBuilder):
    pass

##
# (experimental) An alternate builder that supports manipulation of
# new elements.

class FancyTreeBuilder(TreeBuilder):

    def __init__(self, html=0):
        TreeBuilder.__init__(self, html)
        self._parser.StartNamespaceDeclHandler = self._start_ns
        self._parser.EndNamespaceDeclHandler = self._end_ns
        self.namespaces = []

    def _start(self, tag, attrib_in):
        elem = TreeBuilder._start(self, tag, attrib_in)
        self.start(elem)

    def _start_list(self, tag, attrib_in):
        elem = TreeBuilder._start_list(self, tag, attrib_in)
        self.start(elem)

    def _end(self, tag):
        elem = TreeBuilder._end(self, tag)
        self.end(elem)

    def _start_ns(self, prefix, value):
        self.namespaces.insert(0, (prefix, value))

    def _end_ns(self, prefix):
        assert self.namespaces.pop(0)[0] == prefix, "implementation confused"

    ##
    # Hook method that's called when a new element has been opened.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.  The tag name and attributes are,
    #     set, but it has no children, and the text and tail attributes
    #     are still empty.

    def start(self, element):
        pass

    ##
    # Hook method that's called when a new element has been closed.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.

    def end(self, element):
        pass

########NEW FILE########
__FILENAME__ = helper
"""
Helper module for Python version 3.0 and above
- Ordered dictionaries
- Encoding/decoding urls
- Unicode/Bytes (for sending/receiving data from/to socket, base64)
- Exception handling (except Exception as e)
"""

import base64
import urllib.parse
from collections import OrderedDict

def modulename():
	return "Helper module for Python version 3.0 and above"

def url_decode(uri):
	return urllib.parse.unquote(uri)

def url_encode(uri):
	return urllib.parse.quote(uri)

def new_dictionary():
	return OrderedDict()

def dictionary_keys(dictionary):
	return list(dictionary.keys())

def dictionary_values(dictionary):
	return list(dictionary.values())

def data_read(data):
	# Convert bytes to string
	return data.decode('utf8')

def data_write(data):
	# Convert string to bytes
	return bytes(data, 'utf8')

def base64_decode(data):
	# Base64 returns decoded byte string, decode to convert to UTF8 string
	return base64.b64decode(data).decode('utf8')

def base64_encode(data):
	# Base64 needs ascii input to encode, which returns Base64 byte string, decode to convert to UTF8 string
	return base64.b64encode(data.encode('ascii')).decode('utf8')

def unicode_chr(code):
	return chr(code)

def unicode_string(string):
	# Python 3.* uses unicode by default
	return string

def is_digit(string):
	# Check if string is digit
	return isinstance(string, str) and string.isdigit()
########NEW FILE########
__FILENAME__ = helper_26
"""
Helper module for Python version 2.6 and below
- Ordered dictionaries
- Encoding/decoding urls
- Unicode
- Exception handling (except Exception, e)
"""

import base64
from urllib import unquote, quote
try:
	from ordereddict import OrderedDict
except:
	pass

def modulename():
	return "Helper module for Python version 2.6 and below"

def url_decode(uri):
	return unquote(uri)

def url_encode(uri):
	return quote(uri)

def new_dictionary():
	try:
		return OrderedDict()
	except:
		return {}

def dictionary_keys(dictionary):
	return dictionary.keys()

def dictionary_values(dictionary):
	return dictionary.values()

def data_read(data):
	# Data for reading/receiving already a string in version 2.*
	return data

def data_write(data):
	# Using string in version 2.* for sending/writing data
	return data

def base64_decode(data):
	return base64.b64decode(data)

def base64_encode(data):
	return base64.b64encode(data)

def unicode_chr(code):
	return unichr(code)

def unicode_string(string):
	if isinstance(string, unicode):
		return string
	return string.decode('utf8', 'replace')

def is_digit(string):
	# Check if basestring (str, unicode) is digit
	return isinstance(string, basestring) and string.isdigit()
########NEW FILE########
__FILENAME__ = helper_27
"""
Helper module for Python version 2.7
- Ordered dictionaries
- Encoding/decoding urls
- Unicode
- Exception handling (except Exception as e)
"""

import base64
from urllib import unquote, quote
from collections import OrderedDict

def modulename():
	return "Helper module for Python version 2.7"

def url_decode(uri):
	return unquote(uri)

def url_encode(uri):
	return quote(uri)

def new_dictionary():
	return OrderedDict()

def dictionary_keys(dictionary):
	return list(dictionary.keys())

def dictionary_values(dictionary):
	return list(dictionary.values())

def data_read(data):
	# Data for reading/receiving already a string in version 2.*
	return data

def data_write(data):
	# Using string in version 2.* for sending/writing data
	return data

def base64_decode(data):
	return base64.b64decode(data)

def base64_encode(data):
	return base64.b64encode(data)

def unicode_chr(code):
	return unichr(code)

def unicode_string(string):
	if isinstance(string, unicode):
		return string
	return string.decode('utf8', 'replace')

def is_digit(string):
	# Check if basestring (str, unicode) is digit
	return isinstance(string, basestring) and string.isdigit()
########NEW FILE########
__FILENAME__ = ordereddict
# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = load
import sublime

import os

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# Load modules
from .view import DATA_BREAKPOINT, DATA_CONTEXT, DATA_STACK, DATA_WATCH, TITLE_WINDOW_BREAKPOINT, TITLE_WINDOW_CONTEXT, TITLE_WINDOW_STACK, TITLE_WINDOW_WATCH, has_debug_view, render_regions, show_content
from .util import load_breakpoint_data, load_watch_data
from .log import clear_output, debug, info
from .config import get_window_value, set_window_value, load_package_values, load_project_values


def xdebug():
    # Clear log file
    clear_output()
    if not S.PACKAGE_FOLDER:
        info("Unable to resolve current path for package.")
    info("==== Loading '%s' package ====" % S.PACKAGE_FOLDER)

    # Load config in package/project configuration
    load_package_values()
    load_project_values()

    # Load breakpoint data
    try:
        load_breakpoint_data()
    finally:
        # Render breakpoint markers
        render_regions()

    # Load watch data
    load_watch_data()

    # Clear/Reset content in debug windows
    if has_debug_view(TITLE_WINDOW_BREAKPOINT):
        show_content(DATA_BREAKPOINT)
    if has_debug_view(TITLE_WINDOW_CONTEXT):
        show_content(DATA_CONTEXT)
    if has_debug_view(TITLE_WINDOW_STACK):
        show_content(DATA_STACK)
    if has_debug_view(TITLE_WINDOW_WATCH):
        show_content(DATA_WATCH)

    # Check for conflicting packages
    if S.PACKAGE_FOLDER:
        # Get package list from Package Control
        packages = None
        try:
            packages = sublime.load_settings('Package Control.sublime-settings').get('installed_packages', [])
        except:
            pass
        # Make sure it is a list
        if not isinstance(packages, list):
            packages = []
        # Get packages inside Package directory
        for package_name in os.listdir(sublime.packages_path()):
            if package_name not in packages:
                packages.append(package_name)
        # Strip .sublime-package of package name for comparison
        package_extension = ".sublime-package"
        current_package = S.PACKAGE_FOLDER
        if current_package.endswith(package_extension):
            current_package = current_package[:-len(package_extension)]
        # Search for other conflicting packages
        conflict = []
        for package in packages:
            if package.endswith(package_extension):
                package = package[:-len(package_extension)]
            if (package.lower().count("xdebug") or package.lower().count("moai")) and package != current_package:
                conflict.append(package)
        # Show message if conficting packages have been found
        if conflict:
            info("Conflicting packages detected.")
            debug(conflict)
            if not get_window_value('hide_conflict', False):
                sublime.error_message("The following package(s) could cause conflicts with '{package}':\n\n{other}\n\nPlease consider removing the package(s) above when experiencing any complications." \
                                        .format(package=S.PACKAGE_FOLDER, other='\n'.join(conflict)))
                set_window_value('hide_conflict', True)
        else:
            set_window_value('hide_conflict', False)
########NEW FILE########
__FILENAME__ = log
import sublime

import logging
import os

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# Config module
from .config import get_value


def clear_output():
    # Clear previous output file and configure logging module
    output_file = os.path.join(sublime.packages_path(), 'User', S.FILE_LOG_OUTPUT)
    logging.basicConfig(filename=output_file, filemode='w', level=logging.DEBUG, format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%p')


def debug(message=None):
    if not get_value(S.KEY_DEBUG) or message is None:
        return
    # Write message to output file
    logging.debug(message)


def info(message=None):
    if message is None:
        return
    # Write message to output file
    logging.info(message)
########NEW FILE########
__FILENAME__ = protocol
import re
import socket
import sys

# Helper module
try:
    from .helper import H
except:
    from helper import H

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# Config module
from .config import get_value

# Log module
from .log import debug

# HTML entities
try:
    from html.entities import name2codepoint
except ImportError:
    from htmlentitydefs import name2codepoint

# XML parser
try:
    from xml.etree import cElementTree as ET
except ImportError:
    try:
        from xml.etree import ElementTree as ET
    except ImportError:
        from .elementtree import ElementTree as ET
try:
    from xml.parsers import expat
except ImportError:
    # Module xml.parsers.expat missing, using SimpleXMLTreeBuilder
    from .elementtree import SimpleXMLTreeBuilder
    ET.XMLTreeBuilder = SimpleXMLTreeBuilder.TreeBuilder


ILLEGAL_XML_UNICODE_CHARACTERS = [
    (0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F), (0x7F, 0x84),
    (0x86, 0x9F), (0xD800, 0xDFFF), (0xFDD0, 0xFDDF),
    (0xFFFE, 0xFFFF),
    (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
    (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
    (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
    (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
    (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
    (0x10FFFE, 0x10FFFF) ]

ILLEGAL_XML_RANGES = ["%s-%s" % (H.unicode_chr(low), H.unicode_chr(high))
                  for (low, high) in ILLEGAL_XML_UNICODE_CHARACTERS
                  if low < sys.maxunicode]

ILLEGAL_XML_RE = re.compile(H.unicode_string('[%s]') % H.unicode_string('').join(ILLEGAL_XML_RANGES))



class Protocol(object):
    """
    Class for connecting with debugger engine which uses DBGp protocol.
    """

    # Maximum amount of data to be received at once by socket
    read_size = 1024

    def __init__(self):
        # Set port number to listen for response
        self.port = get_value(S.KEY_PORT, S.DEFAULT_PORT)
        self.clear()

    def transaction_id():
        """
        Standard argument for sending commands, an unique numerical ID.
        """
        def fget(self):
            self._transaction_id += 1
            return self._transaction_id

        def fset(self, value):
            self._transaction_id = value

        def fdel(self):
            self._transaction_id = 0
        return locals()

    # Transaction ID property
    transaction_id = property(**transaction_id())

    def clear(self):
        """
        Clear variables, reset transaction_id, close socket connection.
        """
        self.buffer = ''
        self.connected = False
        self.listening = False
        del self.transaction_id
        try:
            self.socket.close()
        except:
            pass
        self.socket = None

    def unescape(self, string):
        """
        Convert HTML entities and character references to ordinary characters.
        """
        def convert(matches):
            text = matches.group(0)
            # Character reference
            if text[:2] == "&#":
                try:
                    if text[:3] == "&#x":
                        return H.unicode_chr(int(text[3:-1], 16))
                    else:
                        return H.unicode_chr(int(text[2:-1]))
                except ValueError:
                    pass
            # Named entity
            else:
                try:
                    # Following are not needed to be converted for XML
                    if text[1:-1] == "amp" or text[1:-1] == "gt" or text[1:-1] == "lt":
                        pass
                    else:
                        text = H.unicode_chr(name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text
        return re.sub("&#?\w+;", convert, string)

    def read_until_null(self):
        """
        Get response data from debugger engine.
        """
        # Check socket connection
        if self.connected:
            # Get result data from debugger engine
            try:
                while not '\x00' in self.buffer:
                    self.buffer += H.data_read(self.socket.recv(self.read_size))
                data, self.buffer = self.buffer.split('\x00', 1)
                return data
            except:
                e = sys.exc_info()[1]
                raise ProtocolConnectionException(e)
        else:
            raise ProtocolConnectionException("Xdebug is not connected")

    def read_data(self):
        """
        Get response data from debugger engine and verify length of response.
        """
        # Verify length of response data
        length = self.read_until_null()
        message = self.read_until_null()
        if int(length) == len(message):
            return message
        else:
            raise ProtocolException("Length mismatch encountered while reading the Xdebug message")

    def read(self, return_string=False):
        """
        Get response from debugger engine as XML document object.
        """
        # Get result data from debugger engine and verify length of response
        data = self.read_data()

        # Show debug output
        debug('[Response data] %s' % data)

        # Return data string
        if return_string:
            return data

        # Remove special character quoting
        data = self.unescape(data)

        # Replace invalid XML characters
        data = ILLEGAL_XML_RE.sub('?', data)

        # Create XML document object
        document = ET.fromstring(data)
        return document

    def send(self, command, *args, **kwargs):
        """
        Send command to the debugger engine according to DBGp protocol.
        """
        # Expression is used for conditional and watch type breakpoints
        expression = None

        # Seperate 'expression' from kwargs
        if 'expression' in kwargs:
            expression = kwargs['expression']
            del kwargs['expression']

        # Generate unique Transaction ID
        transaction_id = self.transaction_id

        # Append command/arguments to build list
        build_command = [command, '-i %i' % transaction_id]
        if args:
            build_command.extend(args)
        if kwargs:
            build_command.extend(['-%s %s' % pair for pair in kwargs.items()])

        # Remove leading/trailing spaces and build command string
        build_command = [part.strip() for part in build_command if part.strip()]
        command = ' '.join(build_command)
        if expression:
            command += ' -- ' + H.base64_encode(expression)

        # Show debug output
        debug('[Send command] %s' % command)

        # Send command to debugger engine
        try:
            self.socket.send(H.data_write(command + '\x00'))
        except:
            e = sys.exc_info()[1]
            raise ProtocolConnectionException(e)

    def listen(self):
        """
        Create socket server which listens for connection on configured port.
        """
        # Create socket server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if server:
            # Configure socket server
            try:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.settimeout(1)
                server.bind(('', self.port))
                server.listen(1)
                self.listening = True
                self.socket = None
            except:
                e = sys.exc_info()[1]
                raise ProtocolConnectionException(e)

            # Accept incoming connection on configured port
            while self.listening:
                try:
                    self.socket, address = server.accept()
                    self.listening = False
                except socket.timeout:
                    pass

            # Check if a connection has been made
            if self.socket:
                self.connected = True
                self.socket.settimeout(None)
            else:
                self.connected = False
                self.listening = False

            # Close socket server
            try:
                server.close()
            except:
                pass
            server = None

            # Return socket connection
            return self.socket
        else:
            raise ProtocolConnectionException('Could not create socket server.')


class ProtocolException(Exception):
    pass


class ProtocolConnectionException(ProtocolException):
    pass
########NEW FILE########
__FILENAME__ = session
import sublime

import sys
import threading

# Helper module
try:
    from .helper import H
except:
    from helper import H

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# DBGp protocol constants
try:
    from . import dbgp
except:
    import dbgp

# Config module
from .config import get_value

# Log module
from .log import debug, info

# Protocol module
from .protocol import ProtocolConnectionException

# Util module
from .util import get_real_path

# View module
from .view import DATA_CONTEXT, DATA_STACK, DATA_WATCH, TITLE_WINDOW_WATCH, generate_context_output, generate_stack_output, get_response_properties, has_debug_view, render_regions, show_content, show_file, show_panel_content


ACTION_EVALUATE = "action_evaluate"
ACTION_EXECUTE = "action_execute"
ACTION_INIT = "action_init"
ACTION_REMOVE_BREAKPOINT = "action_remove_breakpoint"
ACTION_SET_BREAKPOINT = "action_set_breakpoint"
ACTION_STATUS = "action_status"
ACTION_USER_EXECUTE = "action_user_execute"
ACTION_WATCH = "action_watch"


def is_connected(show_status=False):
    """
    Check if client is connected to debugger engine.

    Keyword arguments:
    show_status -- Show message why client is not connected in status bar.
    """
    if S.SESSION and S.SESSION.connected:
        return True
    elif S.SESSION and show_status:
        sublime.status_message('Xdebug: Waiting for response from debugger engine.')
    elif show_status:
        sublime.status_message('Xdebug: No Xdebug session running.')
    return False


def connection_error(message):
    """
    Template for showing error message on connection error/loss.

    Keyword arguments:
    message -- Exception/reason of connection error/loss.
    """
    sublime.error_message("Please restart Xdebug debugging session.\nDisconnected from Xdebug debugger engine.\n" + message)
    info("Connection lost with debugger engine.")
    debug(message)
    # Reset connection
    try:
        S.SESSION.clear()
    except:
        pass
    finally:
        S.SESSION = None
        S.SESSION_BUSY = False
        S.BREAKPOINT_EXCEPTION = None
        S.BREAKPOINT_ROW = None
        S.BREAKPOINT_RUN = None
        S.CONTEXT_DATA.clear()
        async_session = SocketHandler(ACTION_WATCH)
        async_session.start()
    # Reset layout
    sublime.active_window().run_command('xdebug_layout')
    # Render breakpoint markers
    render_regions()


class SocketHandler(threading.Thread):
    def __init__(self, action, **options):
        threading.Thread.__init__(self)
        self.action = action
        self.options = options

    def get_option(self, option, default_value=None):
        if option in self.options.keys():
            return self.options[option]
        return default_value

    def run_command(self, command, args=None):
        if not isinstance(args, dict):
            args = {}
        self.timeout(lambda: self._run_command(command, args))

    def _run_command(self, command, args=None):
        try:
            sublime.active_window().run_command(command, args)
        except:
            # In case active_window() is not available
            pass

    def run_view_command(self, command, args=None):
        if not isinstance(args, dict):
            args = {}
        self.timeout(lambda: self._run_view_command)

    def _run_view_command(self, command, args=None):
        try:
            sublime.active_window().active_view().run_command(command, args)
        except:
            # In case there is no active_view() available
            pass

    def status_message(self, message):
        sublime.set_timeout(lambda: sublime.status_message(message), 100)

    def timeout(self, function):
        sublime.set_timeout(function, 0)

    def run(self):
        # Make sure an action is defined
        if not self.action:
            return
        try:
            S.SESSION_BUSY = True
            # Evaluate
            if self.action == ACTION_EVALUATE:
                self.evaluate(self.get_option('expression'))
            # Execute
            elif self.action == ACTION_EXECUTE:
                self.execute(self.get_option('command'))
            # Init
            elif self.action == ACTION_INIT:
                self.init()
            # Remove breakpoint
            elif self.action == ACTION_REMOVE_BREAKPOINT:
                self.remove_breakpoint(self.get_option('breakpoint_id'))
            # Set breakpoint
            elif self.action == ACTION_SET_BREAKPOINT:
                self.set_breakpoint(self.get_option('filename'), self.get_option('lineno'), self.get_option('expression'))
            # Status
            elif self.action == ACTION_STATUS:
                self.status()
            # User defined execute
            elif self.action == ACTION_USER_EXECUTE:
                self.user_execute(self.get_option('command'), self.get_option('args'))
            # Watch expression
            elif self.action == ACTION_WATCH:
                self.watch_expression()
        # Show dialog on connection error
        except ProtocolConnectionException:
            e = sys.exc_info()[1]
            self.timeout(lambda: connection_error("%s" % e))
        finally:
            S.SESSION_BUSY = False


    def evaluate(self, expression):
        if not expression or not is_connected():
            return
        # Send 'eval' command to debugger engine with code to evaluate
        S.SESSION.send(dbgp.EVAL, expression=expression)
        if get_value(S.KEY_PRETTY_OUTPUT):
            response = S.SESSION.read()
            properties = get_response_properties(response, expression)
            response = generate_context_output(properties)
        else:
            response = S.SESSION.read(return_string=True)

        # Show response data in output panel
        self.timeout(lambda: show_panel_content(response))


    def execute(self, command):
        # Do not execute if no command is set
        if not command or not is_connected():
            return

        # Send command to debugger engine
        S.SESSION.send(command)
        response = S.SESSION.read()

        # Reset previous breakpoint values
        S.BREAKPOINT_EXCEPTION = None
        S.BREAKPOINT_ROW = None
        S.CONTEXT_DATA.clear()
        self.watch_expression()
        # Set debug layout
        self.run_command('xdebug_layout')

        # Handle breakpoint hit
        for child in response:
            if child.tag == dbgp.ELEMENT_BREAKPOINT or child.tag == dbgp.ELEMENT_PATH_BREAKPOINT:
                # Get breakpoint attribute values
                fileuri = child.get(dbgp.BREAKPOINT_FILENAME)
                lineno = child.get(dbgp.BREAKPOINT_LINENO)
                exception = child.get(dbgp.BREAKPOINT_EXCEPTION)
                filename = get_real_path(fileuri)
                if (exception):
                    info(exception + ': ' + child.text)
                    # Remember Exception name and first line of message
                    S.BREAKPOINT_EXCEPTION = { 'name': exception, 'message': child.text.split('\n')[0], 'filename': fileuri, 'lineno': lineno }

                # Check if temporary breakpoint is set and hit
                if S.BREAKPOINT_RUN is not None and S.BREAKPOINT_RUN['filename'] == filename and S.BREAKPOINT_RUN['lineno'] == lineno:
                    # Remove temporary breakpoint
                    if S.BREAKPOINT_RUN['filename'] in S.BREAKPOINT and S.BREAKPOINT_RUN['lineno'] in S.BREAKPOINT[S.BREAKPOINT_RUN['filename']]:
                        self.run_view_command('xdebug_breakpoint', {'rows': [S.BREAKPOINT_RUN['lineno']], 'filename': S.BREAKPOINT_RUN['filename']})
                    S.BREAKPOINT_RUN = None
                # Skip if temporary breakpoint was not hit
                if S.BREAKPOINT_RUN is not None and (S.BREAKPOINT_RUN['filename'] != filename or S.BREAKPOINT_RUN['lineno'] != lineno):
                    self.run_command('xdebug_execute', {'command': 'run'})
                    return
                # Show debug/status output
                self.status_message('Xdebug: Breakpoint')
                info('Break: ' + filename + ':' + lineno)
                # Store line number of breakpoint for displaying region marker
                S.BREAKPOINT_ROW = { 'filename': filename, 'lineno': lineno }
                # Focus/Open file window view
                self.timeout(lambda: show_file(filename, lineno))

        # On breakpoint get context variables and stack history
        if response.get(dbgp.ATTRIBUTE_STATUS) == dbgp.STATUS_BREAK:
            # Context variables
            context = self.get_context_values()
            self.timeout(lambda: show_content(DATA_CONTEXT, context))

            # Stack history
            stack = self.get_stack_values()
            self.timeout(lambda: show_content(DATA_STACK, stack))

            # Watch expressions
            self.watch_expression()

        # Reload session when session stopped, by reaching end of file or interruption
        if response.get(dbgp.ATTRIBUTE_STATUS) == dbgp.STATUS_STOPPING or response.get(dbgp.ATTRIBUTE_STATUS) == dbgp.STATUS_STOPPED:
            self.run_command('xdebug_session_stop', {'restart': True})
            self.run_command('xdebug_session_start', {'restart': True})
            self.status_message('Xdebug: Finished executing file on server. Reload page to continue debugging.')

        # Render breakpoint markers
        self.timeout(lambda: render_regions())


    def get_context_values(self):
        """
        Get variables in current context.
        """
        if not is_connected():
            return

        context = H.new_dictionary()
        try:
            # Super global variables
            if get_value(S.KEY_SUPER_GLOBALS):
                S.SESSION.send(dbgp.CONTEXT_GET, c=1)
                response = S.SESSION.read()
                context.update(get_response_properties(response))

            # Local variables
            S.SESSION.send(dbgp.CONTEXT_GET)
            response = S.SESSION.read()
            context.update(get_response_properties(response))
        except ProtocolConnectionException:
            e = sys.exc_info()[1]
            self.timeout(lambda: connection_error("%s" % e))

        # Store context variables in session
        S.CONTEXT_DATA = context

        return generate_context_output(context)


    def get_stack_values(self):
        """
        Get stack information for current context.
        """
        response = None
        if is_connected():
            try:
                # Get stack information
                S.SESSION.send(dbgp.STACK_GET)
                response = S.SESSION.read()
            except ProtocolConnectionException:
                e = sys.exc_info()[1]
                self.timeout(lambda: connection_error("%s" % e))
        return generate_stack_output(response)


    def get_watch_values(self):
        """
        Evaluate all watch expressions in current context.
        """
        for index, item in enumerate(S.WATCH):
            # Reset value for watch expression
            S.WATCH[index]['value'] = None

            # Evaluate watch expression when connected to debugger engine
            if is_connected():
                if item['enabled']:
                    watch_value = None
                    try:
                        S.SESSION.send(dbgp.EVAL, expression=item['expression'])
                        response = S.SESSION.read()

                        watch_value = get_response_properties(response, item['expression'])
                    except ProtocolConnectionException:
                        pass

                    S.WATCH[index]['value'] = watch_value


    def init(self):
        if not is_connected():
            return

        # Connection initialization
        init = S.SESSION.read()

        # More detailed internal information on properties
        S.SESSION.send(dbgp.FEATURE_SET, n='show_hidden', v=1)
        response = S.SESSION.read()

        # Set max children limit
        max_children = get_value(S.KEY_MAX_CHILDREN)
        if max_children is not False and max_children is not True and isinstance(max_children, int):
            S.SESSION.send(dbgp.FEATURE_SET, n=dbgp.FEATURE_NAME_MAXCHILDREN, v=max_children)
            response = S.SESSION.read()

        # Set max data limit
        max_data = get_value(S.KEY_MAX_DATA)
        if max_data is not False and max_data is not True and isinstance(max_data, int):
            S.SESSION.send(dbgp.FEATURE_SET, n=dbgp.FEATURE_NAME_MAXDATA, v=max_data)
            response = S.SESSION.read()

        # Set max depth limit
        max_depth = get_value(S.KEY_MAX_DEPTH)
        if max_depth is not False and max_depth is not True and isinstance(max_depth, int):
            S.SESSION.send(dbgp.FEATURE_SET, n=dbgp.FEATURE_NAME_MAXDEPTH, v=max_depth)
            response = S.SESSION.read()

        # Set breakpoints for files
        for filename, breakpoint_data in S.BREAKPOINT.items():
            if breakpoint_data:
                for lineno, bp in breakpoint_data.items():
                    if bp['enabled']:
                        self.set_breakpoint(filename, lineno, bp['expression'])
                        debug('breakpoint_set: ' + filename + ':' + lineno)

        # Set breakpoints for exceptions
        break_on_exception = get_value(S.KEY_BREAK_ON_EXCEPTION)
        if isinstance(break_on_exception, list):
            for exception_name in break_on_exception:
                self.set_exception(exception_name)

        # Determine if client should break at first line on connect
        if get_value(S.KEY_BREAK_ON_START):
            # Get init attribute values
            fileuri = init.get(dbgp.INIT_FILEURI)
            filename = get_real_path(fileuri)
            # Show debug/status output
            self.status_message('Xdebug: Break on start')
            info('Break on start: ' + filename )
            # Store line number of breakpoint for displaying region marker
            S.BREAKPOINT_ROW = { 'filename': filename, 'lineno': 1 }
            # Focus/Open file window view
            self.timeout(lambda: show_file(filename, 1))

            # Context variables
            context = self.get_context_values()
            self.timeout(lambda: show_content(DATA_CONTEXT, context))

            # Stack history
            stack = self.get_stack_values()
            if not stack:
                stack = H.unicode_string('[{level}] {filename}.{where}:{lineno}\n' \
                                          .format(level=0, where='{main}', lineno=1, filename=fileuri))
            self.timeout(lambda: show_content(DATA_STACK, stack))

            # Watch expressions
            self.watch_expression()
        else:
            # Tell script to run it's process
            self.run_command('xdebug_execute', {'command': 'run'})


    def remove_breakpoint(self, breakpoint_id):
        if not breakpoint_id or not is_connected():
            return

        S.SESSION.send(dbgp.BREAKPOINT_REMOVE, d=breakpoint_id)
        response = S.SESSION.read()


    def set_breakpoint(self, filename, lineno, expression=None):
        if not filename or not lineno or not is_connected():
            return

        # Get path of file on server
        fileuri = get_real_path(filename, True)
        # Set breakpoint
        S.SESSION.send(dbgp.BREAKPOINT_SET, t='line', f=fileuri, n=lineno, expression=expression)
        response = S.SESSION.read()
        # Update breakpoint id
        breakpoint_id = response.get(dbgp.ATTRIBUTE_BREAKPOINT_ID)
        if breakpoint_id:
            S.BREAKPOINT[filename][lineno]['id'] = breakpoint_id


    def set_exception(self, exception):
        if not is_connected():
            return

        S.SESSION.send(dbgp.BREAKPOINT_SET, t='exception', x='"%s"' % exception)
        response = S.SESSION.read()


    def status(self):
        if not is_connected():
            return

        # Send 'status' command to debugger engine
        S.SESSION.send(dbgp.STATUS)
        response = S.SESSION.read()
        # Show response in status bar
        self.status_message("Xdebug status: " + response.get(dbgp.ATTRIBUTE_REASON) + ' - ' + response.get(dbgp.ATTRIBUTE_STATUS))


    def user_execute(self, command, args=None):
        if not command or not is_connected():
            return

        # Send command to debugger engine
        S.SESSION.send(command, args)
        response = S.SESSION.read(return_string=True)

        # Show response data in output panel
        self.timeout(lambda: show_panel_content(response))


    def watch_expression(self):
        # Evaluate watch expressions
        self.get_watch_values()
        # Show watch expression
        self.timeout(lambda: self._watch_expression(self.get_option('check_watch_view', False)))


    def _watch_expression(self, check_watch_view):
        # Do not show if we only want to show content when Watch view is not available
        if check_watch_view and not has_debug_view(TITLE_WINDOW_WATCH):
            return

        show_content(DATA_WATCH)
########NEW FILE########
__FILENAME__ = settings
DEFAULT_PORT = 9000
DEFAULT_IDE_KEY = 'sublime.xdebug'

PACKAGE_PATH = None
PACKAGE_FOLDER = None

FILE_LOG_OUTPUT = 'Xdebug.log'
FILE_BREAKPOINT_DATA = 'Xdebug.breakpoints'
FILE_PACKAGE_SETTINGS = 'Xdebug.sublime-settings'
FILE_WATCH_DATA = 'Xdebug.expressions'

KEY_SETTINGS = 'settings'
KEY_XDEBUG = 'xdebug'

KEY_PATH_MAPPING = "path_mapping"
KEY_URL = "url"
KEY_IDE_KEY = "ide_key"
KEY_PORT = "port"
KEY_SUPER_GLOBALS = "super_globals"
KEY_MAX_CHILDREN = "max_children"
KEY_MAX_DATA = "max_data"
KEY_MAX_DEPTH = "max_depth"
KEY_BREAK_ON_START = "break_on_start"
KEY_BREAK_ON_EXCEPTION = "break_on_exception"
KEY_CLOSE_ON_STOP = "close_on_stop"
KEY_HIDE_PASSWORD = "hide_password"
KEY_PRETTY_OUTPUT = "pretty_output"
KEY_LAUNCH_BROWSER = "launch_browser"
KEY_BROWSER_NO_EXECUTE = "browser_no_execute"
KEY_DISABLE_LAYOUT = "disable_layout"
KEY_DEBUG_LAYOUT = "debug_layout"

KEY_BREAKPOINT_GROUP = "breakpoint_group"
KEY_BREAKPOINT_INDEX = "breakpoint_index"
KEY_CONTEXT_GROUP = "context_group"
KEY_CONTEXT_INDEX = "context_index"
KEY_STACK_GROUP = "stack_group"
KEY_STACK_INDEX = "stack_index"
KEY_WATCH_GROUP = "watch_group"
KEY_WATCH_INDEX = "watch_index"

KEY_BREAKPOINT_CURRENT = 'breakpoint_current'
KEY_BREAKPOINT_DISABLED = 'breakpoint_disabled'
KEY_BREAKPOINT_ENABLED = 'breakpoint_enabled'
KEY_CURRENT_LINE = 'current_line'

KEY_PYTHON_PATH = "python_path"
KEY_DEBUG = "debug"

# Region scope sources
REGION_KEY_BREAKPOINT = 'xdebug_breakpoint'
REGION_KEY_CURRENT = 'xdebug_current'
REGION_KEY_DISABLED = 'xdebug_disabled'
REGION_SCOPE_BREAKPOINT = 'comment.line.settings'
REGION_SCOPE_CURRENT = 'string.quoted.settings'

# Window layout for debugging output
LAYOUT_DEBUG = {
                "cols": [0.0, 0.5, 1.0],
                "rows": [0.0, 0.7, 1.0],
                "cells": [[0, 0, 2, 1], [0, 1, 1, 2], [1, 1, 2, 2]]
                }
# Default single layout (similar to Alt+Shift+1)
LAYOUT_NORMAL = {
                "cols": [0.0, 1.0],
                "rows": [0.0, 1.0],
                "cells": [[0, 0, 1, 1]]
                }

RESTORE_LAYOUT = None
RESTORE_INDEX = None

SESSION_BUSY = False

SESSION = None
BREAKPOINT = {}
CONTEXT_DATA = {}
WATCH = []

BREAKPOINT_EXCEPTION = None
# Breakpoint line number in script being debugged
BREAKPOINT_ROW = None
# Placholder for temporary breakpoint filename and line number
BREAKPOINT_RUN = None
# Will hold breakpoint line number to show for file which is being loaded
SHOW_ROW_ONLOAD = {}

CONFIG_PROJECT = None
CONFIG_PACKAGE = None
CONFIG_KEYS = [
	KEY_PATH_MAPPING,
	KEY_URL,
	KEY_IDE_KEY,
	KEY_PORT,
	KEY_SUPER_GLOBALS,
	KEY_MAX_CHILDREN,
	KEY_MAX_DATA,
	KEY_MAX_DEPTH,
	KEY_BREAK_ON_START,
	KEY_BREAK_ON_EXCEPTION,
	KEY_CLOSE_ON_STOP,
	KEY_HIDE_PASSWORD,
	KEY_PRETTY_OUTPUT,
	KEY_LAUNCH_BROWSER,
	KEY_BROWSER_NO_EXECUTE,
	KEY_DISABLE_LAYOUT,
	KEY_DEBUG_LAYOUT,
	KEY_BREAKPOINT_GROUP,
	KEY_BREAKPOINT_INDEX,
	KEY_CONTEXT_GROUP,
	KEY_CONTEXT_INDEX,
	KEY_STACK_GROUP,
	KEY_STACK_INDEX,
	KEY_WATCH_GROUP,
	KEY_WATCH_INDEX,
	KEY_BREAKPOINT_CURRENT,
	KEY_BREAKPOINT_DISABLED,
	KEY_BREAKPOINT_ENABLED,
	KEY_CURRENT_LINE,
	KEY_PYTHON_PATH,
	KEY_DEBUG
]
########NEW FILE########
__FILENAME__ = util
import sublime

import json
import os
import re
import sys
import webbrowser

# Helper module
try:
    from .helper import H
except:
    from helper import H

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# Config module
from .config import get_value

# Log module
from .log import debug, info


def get_real_path(uri, server=False):
    """
    Get real path

    Keyword arguments:
    uri -- Uri of file that needs to be mapped and located
    server -- Map local path to server path

    TODO: Fix mapping for root (/) and drive letters (P:/)
    """
    if uri is None:
        return uri

    # URLdecode uri
    uri = H.url_decode(uri)

    # Split scheme from uri to get absolute path
    try:
        # scheme:///path/file => scheme, /path/file
        # scheme:///C:/path/file => scheme, C:/path/file
        transport, filename = uri.split(':///', 1) 
    except:
        filename = uri

    # Normalize path for comparison and remove duplicate/trailing slashes
    uri = os.path.normpath(filename)

    # Pattern for checking if uri is a windows path
    drive_pattern = re.compile(r'^[a-zA-Z]:[\\/]')

    # Append leading slash if filesystem is not Windows
    if not drive_pattern.match(uri) and not os.path.isabs(uri):
        uri = os.path.normpath('/' + uri)

    path_mapping = get_value(S.KEY_PATH_MAPPING)
    if isinstance(path_mapping, dict):
        # Go through path mappings
        for server_path, local_path in path_mapping.items():
            server_path = os.path.normpath(server_path)
            local_path = os.path.normpath(local_path)
            # Replace path if mapping available
            if server:
                # Map local path to server path
                if local_path in uri:
                    uri = uri.replace(local_path, server_path)
                    break
            else:
                # Map server path to local path
                if server_path in uri:
                    uri = uri.replace(server_path, local_path)
                    break
    else:
        sublime.set_timeout(lambda: sublime.status_message("Xdebug: No path mapping defined, returning given path."), 100)

    # Replace slashes
    if not drive_pattern.match(uri):
        uri = uri.replace("\\", "/")

    # Append scheme
    if server:
        return H.url_encode("file://" + uri)

    return uri


def get_region_icon(icon):
    # Default icons for color schemes from default theme
    default_current = 'bookmark'
    default_disabled = 'dot'
    default_enabled = 'circle'

    # Package icons (without .png extension)
    package_breakpoint_current = 'breakpoint_current'
    package_breakpoint_disabled = 'breakpoint_disabled'
    package_breakpoint_enabled = 'breakpoint_enabled'
    package_current_line = 'current_line'

    # List to check for duplicate icon entries
    icon_list = [default_current, default_disabled, default_enabled]

    # Determine icon path
    icon_path = None
    if S.PACKAGE_FOLDER is not None:
        # Strip .sublime-package of package name for comparison
        package_extension = ".sublime-package"
        current_package = S.PACKAGE_FOLDER
        if current_package.endswith(package_extension):
            current_package = current_package[:-len(package_extension)]
        if sublime.version() == '' or int(sublime.version()) > 3000:
            # ST3: Packages/Xdebug Client/icons/breakpoint_enabled.png
            icon_path = "Packages/" + current_package + '/icons/{0}.png'
        else:
            # ST2: ../Xdebug Client/icons/breakpoint_enabled
            icon_path = "../" + current_package + '/icons/{0}'
        # Append icon path to package icons
        package_breakpoint_current = icon_path.format(package_breakpoint_current)
        package_breakpoint_disabled = icon_path.format(package_breakpoint_disabled)
        package_breakpoint_enabled = icon_path.format(package_breakpoint_enabled)
        package_current_line = icon_path.format(package_current_line)
        # Add to duplicate list
        icon_list.append(icon_path.format(package_breakpoint_current))
        icon_list.append(icon_path.format(package_breakpoint_disabled))
        icon_list.append(icon_path.format(package_breakpoint_enabled))
        icon_list.append(icon_path.format(package_current_line))

    # Get user defined icons from settings
    breakpoint_current = get_value(S.KEY_BREAKPOINT_CURRENT)
    breakpoint_disabled = get_value(S.KEY_BREAKPOINT_DISABLED)
    breakpoint_enabled = get_value(S.KEY_BREAKPOINT_ENABLED)
    current_line = get_value(S.KEY_CURRENT_LINE)

    # Duplicate check, enabled breakpoint
    if breakpoint_enabled not in icon_list:
        icon_list.append(breakpoint_enabled)
    else:
        breakpoint_enabled = None
    # Duplicate check, disabled breakpoint
    if breakpoint_disabled not in icon_list:
        icon_list.append(breakpoint_disabled)
    else:
        breakpoint_disabled = None
    # Duplicate check, current line
    if current_line not in icon_list:
        icon_list.append(current_line)
    else:
        current_line = None
    # Duplicate check, current breakpoint
    if breakpoint_current not in icon_list:
        icon_list.append(breakpoint_current)
    else:
        breakpoint_current = None

    # Use default/package icon if no user defined or duplicate detected
    if not breakpoint_current and icon_path is not None:
        breakpoint_current = package_breakpoint_current
    if not breakpoint_disabled:
        breakpoint_disabled = default_disabled if icon_path is None else package_breakpoint_disabled
    if not breakpoint_enabled:
        breakpoint_enabled = default_enabled if icon_path is None else package_breakpoint_enabled
    if not current_line:
        current_line = default_current if icon_path is None else package_current_line

    # Return icon for icon name
    if icon == S.KEY_CURRENT_LINE:
        return current_line
    elif icon == S.KEY_BREAKPOINT_CURRENT:
        return breakpoint_current
    elif icon == S.KEY_BREAKPOINT_DISABLED:
        return breakpoint_disabled
    elif icon == S.KEY_BREAKPOINT_ENABLED:
        return breakpoint_enabled
    else:
        info("Invalid icon name. (" + icon + ")")
        return


def launch_browser():
    url = get_value(S.KEY_URL)
    if not url:
        sublime.set_timeout(lambda: sublime.status_message('Xdebug: No URL defined in (project) settings file.'), 100)
        return
    ide_key = get_value(S.KEY_IDE_KEY, S.DEFAULT_IDE_KEY)
    operator = '?'

    # Check if url already has query string
    if url.count("?"):
        operator = '&'

    # Start debug session
    if S.SESSION and (S.SESSION.listening or not S.SESSION.connected):
        webbrowser.open(url + operator + 'XDEBUG_SESSION_START=' + ide_key)
    # Stop debug session
    else:
        # Check if we should execute script
        if get_value(S.KEY_BROWSER_NO_EXECUTE):
            # Without executing script
            webbrowser.open(url + operator + 'XDEBUG_SESSION_STOP_NO_EXEC=' + ide_key)
        else:
            # Run script normally
            webbrowser.open(url + operator + 'XDEBUG_SESSION_STOP=' + ide_key)


def load_breakpoint_data():
    data_path = os.path.join(sublime.packages_path(), 'User', S.FILE_BREAKPOINT_DATA)
    data = {}
    try:
        data_file = open(data_path, 'rb')
    except:
        e = sys.exc_info()[1]
        info('Failed to open %s.' % data_path)
        debug(e)

    try:
        data = json.loads(H.data_read(data_file.read()))
    except:
        e = sys.exc_info()[1]
        info('Failed to parse %s.' % data_path)
        debug(e)

    # Do not use deleted files or entries without breakpoints
    if data:
        for filename, breakpoint_data in data.copy().items():
            if not breakpoint_data or not os.path.isfile(filename):
                del data[filename]

    if not isinstance(S.BREAKPOINT, dict):
        S.BREAKPOINT = {}

    # Set breakpoint data
    S.BREAKPOINT.update(data)


def load_watch_data():
    data_path = os.path.join(sublime.packages_path(), 'User', S.FILE_WATCH_DATA)
    data = []
    try:
        data_file = open(data_path, 'rb')
    except:
        e = sys.exc_info()[1]
        info('Failed to open %s.' % data_path)
        debug(e)

    try:
        data = json.loads(H.data_read(data_file.read()))
    except:
        e = sys.exc_info()[1]
        info('Failed to parse %s.' % data_path)
        debug(e)

    # Check if expression is not already defined
    duplicates = []
    for index, entry in enumerate(data):
        matches = [x for x in S.WATCH if x['expression'] == entry['expression']]
        if matches:
            duplicates.append(entry)
        else:
            # Unset any previous value
            data[index]['value'] = None
    for duplicate in duplicates:
        data.remove(duplicate)

    if not isinstance(S.WATCH, list):
        S.WATCH = []

    # Set watch data
    S.WATCH.extend(data)


def save_breakpoint_data():
    data_path = os.path.join(sublime.packages_path(), 'User', S.FILE_BREAKPOINT_DATA)
    with open(data_path, 'wb') as data:
        data.write(H.data_write(json.dumps(S.BREAKPOINT)))


def save_watch_data():
    data_path = os.path.join(sublime.packages_path(), 'User', S.FILE_WATCH_DATA)
    with open(data_path, 'wb') as data:
        data.write(H.data_write(json.dumps(S.WATCH)))
########NEW FILE########
__FILENAME__ = view
import sublime

import operator
import os
import re

# Helper module
try:
    from .helper import H
except:
    from helper import H

# Settings variables
try:
    from . import settings as S
except:
    import settings as S

# DBGp protocol constants
try:
    from . import dbgp
except:
    import dbgp

# Config module
from .config import get_value, get_window_value, set_window_value

# Util module
from .util import get_real_path, get_region_icon, save_watch_data


DATA_BREAKPOINT = 'breakpoint'
DATA_CONTEXT = 'context'
DATA_STACK = 'stack'
DATA_WATCH = 'watch'

TITLE_WINDOW_BREAKPOINT = "Xdebug Breakpoint"
TITLE_WINDOW_CONTEXT = "Xdebug Context"
TITLE_WINDOW_STACK = "Xdebug Stack"
TITLE_WINDOW_WATCH = "Xdebug Watch"


def close_debug_windows():
    """
    Close all debugging related views in active window.
    """
    window = sublime.active_window()
    for view in window.views():
        if is_debug_view(view):
            window.focus_view(view)
            window.run_command('close')
    window.run_command('hide_panel', {"panel": 'output.xdebug'})


def generate_breakpoint_output():
    """
    Generate output with all configured breakpoints.
    """
    # Get breakpoints for files
    values = H.unicode_string('')
    if S.BREAKPOINT is None:
        return values
    for filename, breakpoint_data in sorted(S.BREAKPOINT.items()):
        breakpoint_entry = ''
        if breakpoint_data:
            breakpoint_entry += "=> %s\n" % filename
            # Sort breakpoint data by line number
            for lineno, bp in sorted(breakpoint_data.items(), key=lambda item: (int(item[0]) if isinstance(item[0], int) or H.is_digit(item[0]) else float('inf'), item[0])):
                # Do not show temporary breakpoint
                if S.BREAKPOINT_RUN is not None and S.BREAKPOINT_RUN['filename'] == filename and S.BREAKPOINT_RUN['lineno'] == lineno:
                    continue
                # Whether breakpoint is enabled or disabled
                breakpoint_entry += '\t'
                if bp['enabled']:
                    breakpoint_entry += '|+|'
                else:
                    breakpoint_entry += '|-|'
                # Line number
                breakpoint_entry += ' %s' % lineno
                # Conditional expression
                if bp['expression'] is not None:
                    breakpoint_entry += ' -- "%s"' % bp['expression']
                breakpoint_entry += "\n"
        values += H.unicode_string(breakpoint_entry)
    return values


def generate_context_output(context, indent=0):
    """
    Generate readable context from dictionary with context data.

    Keyword arguments:
    context -- Dictionary with context data.
    indent -- Indent level.
    """
    # Generate output text for values
    values = H.unicode_string('')
    if not isinstance(context, dict):
        return values
    for variable in context.values():
        has_children = False
        property_text = ''
        # Set indentation
        for i in range(indent): property_text += '\t'
        # Property with value
        if variable['value'] is not None:
            if variable['name']:
                property_text += '{name} = '
            property_text += '({type}) {value}\n'
        # Property with children
        elif isinstance(variable['children'], dict) and variable['numchildren'] is not None:
            has_children = True
            if variable['name']:
                property_text += '{name} = '
            property_text += '{type}[{numchildren}]\n'
        # Unknown property
        else:
            if variable['name']:
                property_text += '{name} = '
            property_text += '<{type}>\n'

        # Remove newlines in value to prevent incorrect indentation
        value = ''
        if variable['value'] and len(variable['value']) > 0:
            value = variable['value'].replace("\r\n", "\n").replace("\n", " ")

        # Format string and append to output
        values += H.unicode_string(property_text \
                        .format(value=value, type=variable['type'], name=variable['name'], numchildren=variable['numchildren']))

        # Append property children to output
        if has_children:
            # Get children for property (no need to convert, already unicode)
            values += generate_context_output(variable['children'], indent+1)
            # Use ellipsis to indicate that results have been truncated
            limited = False
            if isinstance(variable['numchildren'], int) or H.is_digit(variable['numchildren']):
                if int(variable['numchildren']) != len(variable['children']):
                    limited = True
            elif len(variable['children']) > 0 and not variable['numchildren']:
                limited = True
            if limited:
                for i in range(indent+1): values += H.unicode_string('\t')
                values += H.unicode_string('...\n')
    return values


def generate_stack_output(response):
    values = H.unicode_string('')

    # Display exception name and message
    if S.BREAKPOINT_EXCEPTION:
        values += H.unicode_string('[{name}] {message}\n' \
                                  .format(name=S.BREAKPOINT_EXCEPTION['name'], message=S.BREAKPOINT_EXCEPTION['message']))

    # Walk through elements in response
    has_output = False
    try:
        for child in response:
            # Get stack attribute values
            if child.tag == dbgp.ELEMENT_STACK or child.tag == dbgp.ELEMENT_PATH_STACK:
                stack_level = child.get(dbgp.STACK_LEVEL, 0)
                stack_type = child.get(dbgp.STACK_TYPE)
                stack_file = H.url_decode(child.get(dbgp.STACK_FILENAME))
                stack_line = child.get(dbgp.STACK_LINENO, 0)
                stack_where = child.get(dbgp.STACK_WHERE, '{unknown}')
                # Append values
                values += H.unicode_string('[{level}] {filename}.{where}:{lineno}\n' \
                                          .format(level=stack_level, type=stack_type, where=stack_where, lineno=stack_line, filename=stack_file))
                has_output = True
    except:
        pass

    # When no stack use values from exception
    if not has_output and S.BREAKPOINT_EXCEPTION:
        values += H.unicode_string('[{level}] {filename}.{where}:{lineno}\n' \
                                  .format(level=0, where='{unknown}', lineno=S.BREAKPOINT_EXCEPTION['lineno'], filename=S.BREAKPOINT_EXCEPTION['filename']))

    return values


def generate_watch_output():
    """
    Generate output with all watch expressions.
    """
    values = H.unicode_string('')
    if S.WATCH is None:
        return values
    for watch_data in S.WATCH:
        watch_entry = ''
        if watch_data and isinstance(watch_data, dict):
            # Whether watch expression is enabled or disabled
            if 'enabled' in watch_data.keys():
                if watch_data['enabled']:
                    watch_entry += '|+|'
                else:
                    watch_entry += '|-|'
            # Watch expression
            if 'expression' in watch_data.keys():
                watch_entry += ' "%s"' % watch_data['expression']
            # Evaluated value
            if watch_data['value'] is not None:
                watch_entry += ' = ' + generate_context_output(watch_data['value'])
            else:
                watch_entry += "\n"
        values += H.unicode_string(watch_entry)
    return values


def get_context_variable(context, variable_name):
    """
    Find a variable in the context data.

    Keyword arguments:
    context -- Dictionary with context data to search.
    variable_name -- Name of variable to find.
    """
    if isinstance(context, dict):
        if variable_name in context:
            return context[variable_name]
        for variable in context.values():
            if isinstance(variable['children'], dict):
                children = get_context_variable(variable['children'], variable_name)
                if children:
                    return children


def get_debug_index(name=None):
    """
    Retrieve configured group/index position of of debug view(s) within active window.
    Returns list with tuple entries for all debug views or single tuple when specified name of debug view.
    Structure of tuple entry for debug view is as followed:
    (group position in window, index position in group, name/title of debug view)

    Keyword arguments:
    name -- Name of debug view to get group/index position.
    """
    # Set group and index for each debug view
    breakpoint_group = get_value(S.KEY_BREAKPOINT_GROUP, -1)
    breakpoint_index = get_value(S.KEY_BREAKPOINT_INDEX, 0)
    context_group = get_value(S.KEY_CONTEXT_GROUP, -1)
    context_index = get_value(S.KEY_CONTEXT_INDEX, 0)
    stack_group = get_value(S.KEY_STACK_GROUP, -1)
    stack_index = get_value(S.KEY_STACK_INDEX, 0)
    watch_group = get_value(S.KEY_WATCH_GROUP, -1)
    watch_index = get_value(S.KEY_WATCH_INDEX, 0)

    # Create list with all debug views and sort by group/index
    debug_list = []
    debug_list.append((breakpoint_group, breakpoint_index, TITLE_WINDOW_BREAKPOINT))
    debug_list.append((context_group, context_index, TITLE_WINDOW_CONTEXT))
    debug_list.append((stack_group, stack_index, TITLE_WINDOW_STACK))
    debug_list.append((watch_group, watch_index, TITLE_WINDOW_WATCH))
    debug_list.sort(key=operator.itemgetter(0,1))

    # Recalculate group/index position within boundaries of active window
    window = sublime.active_window()
    group_limit = window.num_groups()-1
    sorted_list = []
    last_group = None
    last_index = 0
    for debug in debug_list:
        group, index, title = debug
        # Set group position
        if group > group_limit:
            group = group_limit
        # Set index position
        if group == last_group:
            last_index += 1
        else:
            index_limit = len(window.views_in_group(group))
            if index > index_limit:
                index = index_limit
            last_group = group
            last_index = index
        # Add debug view with new group/index
        sorted_list.append((group, last_index, title))
    # Sort recalculated list by group/index
    sorted_list.sort(key=operator.itemgetter(0,1))

    # Find specified view by name/title of debug view
    if name is not None:
        try:
            return [view[2] for view in sorted_list].index(name)
        except ValueError:
            return None

    # List with all debug views
    return sorted_list


def get_response_properties(response, default_key=None):
    """
    Return a dictionary with available properties from response.

    Keyword arguments:
    response -- Response from debugger engine.
    default_key -- Index key to use when property has no name.
    """
    properties = H.new_dictionary()
    # Walk through elements in response
    for child in response:
        # Read property elements
        if child.tag == dbgp.ELEMENT_PROPERTY or child.tag == dbgp.ELEMENT_PATH_PROPERTY:
            # Get property attribute values
            property_name_short = child.get(dbgp.PROPERTY_NAME)
            property_name = child.get(dbgp.PROPERTY_FULLNAME, property_name_short)
            property_type = child.get(dbgp.PROPERTY_TYPE)
            property_children = child.get(dbgp.PROPERTY_CHILDREN)
            property_numchildren = child.get(dbgp.PROPERTY_NUMCHILDREN)
            property_classname = child.get(dbgp.PROPERTY_CLASSNAME)
            property_encoding = child.get(dbgp.PROPERTY_ENCODING)
            property_value = None

            # Set property value
            if child.text:
                property_value = child.text
                # Try to decode property value when encoded with base64
                if property_encoding is not None and property_encoding == 'base64':
                    try:
                        property_value = H.base64_decode(child.text)
                    except:
                        pass

            if property_name is not None and len(property_name) > 0:
                property_key = property_name
                # Ignore following properties
                if property_name == "::":
                    continue

                # Avoid nasty static functions/variables from turning in an infinitive loop
                if property_name.count("::") > 1:
                    continue

                # Filter password values
                if get_value(S.KEY_HIDE_PASSWORD, True) and property_name.lower().find('password') != -1 and property_value is not None:
                    property_value = '******'
            else:
                property_key = default_key

            # Store property
            if property_key:
                properties[property_key] = { 'name': property_name, 'type': property_type, 'value': property_value, 'numchildren': property_numchildren, 'children' : None }

                # Get values for children
                if property_children:
                    properties[property_key]['children'] = get_response_properties(child, default_key)

                # Set classname, if available, as type for object
                if property_classname and property_type == 'object':
                    properties[property_key]['type'] = property_classname
        # Handle error elements
        elif child.tag == dbgp.ELEMENT_ERROR or child.tag == dbgp.ELEMENT_PATH_ERROR:
            message = 'error'
            for step_child in child:
                if step_child.tag == dbgp.ELEMENT_MESSAGE or step_child.tag == dbgp.ELEMENT_PATH_MESSAGE and step_child.text:
                    message = step_child.text
                    break
            if default_key:
                properties[default_key] = { 'name': None, 'type': message, 'value': None, 'numchildren': None, 'children': None }
    return properties


def has_debug_view(name=None):
    """
    Determine if active window has any or specific debug view(s).

    Keyword arguments:
    name -- Name of debug view to search for in active window.
    """
    for view in sublime.active_window().views():
        if is_debug_view(view):
            if name is not None:
                if view.name() == name:
                    return True
            else:
                return True
    return False


def is_debug_view(view):
    """
    Check if view name matches debug name/title.

    Keyword arguments:
    view -- View reference which to check if name matches debug name/title.
    """
    return view.name() == TITLE_WINDOW_BREAKPOINT or view.name() == TITLE_WINDOW_CONTEXT or view.name() == TITLE_WINDOW_STACK or view.name() == TITLE_WINDOW_WATCH


def set_layout(layout):
    """
    Toggle between debug and default window layouts.
    """
    # Get active window and set reference to active view
    window = sublime.active_window()
    previous_active = window.active_view()

    # Do not set layout when disabled
    if get_value(S.KEY_DISABLE_LAYOUT):
        S.RESTORE_LAYOUT = window.get_layout()
        set_window_value('restore_layout', S.RESTORE_LAYOUT)
        S.RESTORE_INDEX = H.new_dictionary()
        set_window_value('restore_index', S.RESTORE_INDEX)
        return

    # Show debug layout
    if layout == 'debug':
        debug_layout = get_value(S.KEY_DEBUG_LAYOUT, S.LAYOUT_DEBUG)
        if window.get_layout() != debug_layout:
            # Save current layout
            S.RESTORE_LAYOUT = window.get_layout()
            set_window_value('restore_layout', S.RESTORE_LAYOUT)
            # Remember view indexes
            S.RESTORE_INDEX = H.new_dictionary()
            for view in window.views():
                view_id = "%d" % view.id()
                group, index = window.get_view_index(view)
                S.RESTORE_INDEX[view_id] = { "group": group, "index": index }
            set_window_value('restore_index', S.RESTORE_INDEX)
            # Set debug layout
            window.set_layout(S.LAYOUT_NORMAL)
        window.set_layout(debug_layout)
    # Show previous (single) layout
    else:
        # Get previous layout configuration
        if S.RESTORE_LAYOUT is None:
            S.RESTORE_LAYOUT = get_window_value('restore_layout', S.LAYOUT_NORMAL)
        if S.RESTORE_INDEX is None:
            S.RESTORE_INDEX = get_window_value('restore_index', {})
        # Restore layout
        window.set_layout(S.LAYOUT_NORMAL)
        window.set_layout(S.RESTORE_LAYOUT)
        for view in window.views():
            view_id = "%d" % view.id()
            # Set view indexes
            if view_id in H.dictionary_keys(S.RESTORE_INDEX):
                v = S.RESTORE_INDEX[view_id]
                window.set_view_index(view, v["group"], v["index"])

    # Restore focus to previous active view
    if not previous_active is None:
        window.focus_view(previous_active)


def show_content(data, content=None):
    """
    Show content for specific data type in assigned window view.
    Note: When view does not exists, it will create one.
    """

    # Hande data type
    if data == DATA_BREAKPOINT:
        title = TITLE_WINDOW_BREAKPOINT
        content = generate_breakpoint_output()
    elif data == DATA_CONTEXT:
        title = TITLE_WINDOW_CONTEXT
    elif data == DATA_STACK:
        title = TITLE_WINDOW_STACK
    elif data == DATA_WATCH:
        title = TITLE_WINDOW_WATCH
        content = generate_watch_output()
    else:
        return

    # Get list of group/index for all debug views
    debug_index = get_debug_index()

    # Find group/index of debug view for current data type
    try:
        key = [debug[2] for debug in debug_index].index(title)
    except ValueError:
        return
    # Set group and index position
    group, index, _ = debug_index[key]

    # Get active window and set reference to active view
    window = sublime.active_window()
    previous_active = window.active_view_in_group(window.active_group())

    # Loop through views in active window
    found = False
    view = None
    previous_key = -1
    active_debug = None
    for v in window.views():
        # Search for view assigned to data type
        if v.name() == title:
            found = True
            view = v
            continue
        # Adjust group/index of debug view depending on other debug view(s)
        if is_debug_view(v):
            try:
                current_key = [debug[2] for debug in debug_index].index(v.name())
            except ValueError:
                continue
            # Get current position of view
            view_group, view_index = window.get_view_index(v)
            # Recalculate group/index for debug view
            current_group, current_index, _ = debug_index[current_key]
            if group == current_group:
                if key > previous_key and key < current_key:
                    index = view_index
                if key > current_key:
                    index = view_index + 1
                    # Remember debug view for setting focus
                    if v == window.active_view_in_group(group):
                        active_debug = v
            previous_key = current_key

    # Make sure index position is not out of boundary
    index_limit = len(window.views_in_group(group))
    if index > index_limit:
        index = index_limit

    # Create new view if it does not exists
    if not found:
        view = window.new_file()
        view.set_scratch(True)
        view.set_read_only(True)
        view.set_name(title)
        window.set_view_index(view, group, index)
        # Set focus back to active debug view
        if active_debug is not None:
            window.focus_view(active_debug)

    # Strip .sublime-package of package name for syntax file
    package_extension = ".sublime-package"
    package = S.PACKAGE_FOLDER
    if package.endswith(package_extension):
        package = package[:-len(package_extension)]

    # Configure view settings
    view.settings().set('word_wrap', False)
    view.settings().set('syntax', 'Packages/' + package + '/Xdebug.tmLanguage')

    # Set content for view and fold all indendation blocks
    view.run_command('xdebug_view_update', {'data': content, 'readonly': True})
    if data == DATA_CONTEXT or data == DATA_WATCH:
        view.run_command('fold_all')

    # Restore focus to previous active view/group
    if previous_active is not None:
        window.focus_view(previous_active)
    else:
        window.focus_group(0)


def show_context_output(view):
    """
    Show selected variable in an output panel when clicked in context window.

    Keyword arguments:
    view -- View reference which holds the context window.
    """
    # Check if there is a debug session and context data
    if S.SESSION and S.SESSION.connected and S.CONTEXT_DATA:
        try:
            # Get selected point in view
            point = view.sel()[0]
            # Check if selected point uses variable scope
            if point.size() == 0 and sublime.score_selector(view.scope_name(point.a), 'variable'):
                # Find variable in line which contains the point
                line = view.substr(view.line(point))
                pattern = re.compile('^\\s*(\\$.*?)\\s+\\=')
                match = pattern.match(line)
                if match:
                    # Get variable details from context data
                    variable_name = match.group(1)
                    variable = get_context_variable(S.CONTEXT_DATA, variable_name)
                    if variable:
                        # Convert details to text output
                        variables = H.new_dictionary()
                        variables[variable_name] = variable
                        data = generate_context_output(variables)
                        # Show context variables and children in output panel
                        window = sublime.active_window()
                        panel = window.get_output_panel('xdebug')
                        panel.run_command("xdebug_view_update", {'data' : data} )
                        panel.run_command('set_setting', {"setting": 'word_wrap', "value": True})
                        window.run_command('show_panel', {"panel": 'output.xdebug'})
        except:
            pass


def show_file(filename, row=None):
    """
    Open or focus file in window, which is currently being debugged.

    Keyword arguments:
    filename -- Absolute path of file on local device.
    """
    # Check if file exists if being referred to file system
    if os.path.exists(filename):
        # Get active window
        window = sublime.active_window()
        window.focus_group(0)
        # Check if file is already open
        found = False
        view = window.find_open_file(filename)
        if not view is None:
            found = True
            window.focus_view(view)
            # Set focus to row (line number)
            show_at_row(view, row)
        # Open file if not open
        if not found:
            view = window.open_file(filename)
            window.focus_view(view)
            # Set focus to row (line number) when file is loaded
            S.SHOW_ROW_ONLOAD[filename] = row


def show_panel_content(content):
    # Show response data in output panel
    try:
        window = sublime.active_window()
        panel = window.get_output_panel('xdebug')
        panel.run_command('xdebug_view_update', {'data': content})
        panel.run_command('set_setting', {"setting": 'word_wrap', "value": True})
        window.run_command('show_panel', {'panel': 'output.xdebug'})
    except:
        print(content)


def show_at_row(view, row=None):
    """
    Scroll the view to center on the given row (line number).

    Keyword arguments:
    - view -- Which view to scroll to center on row.
    - row -- Row where to center the view.
    """
    if row is not None:
        try:
            # Convert row (line number) to region
            row_region = rows_to_region(row)[0].a
            # Scroll the view to row
            view.show_at_center(row_region)
        except:
            # When defining row_region index could be out of bounds
            pass


def rows_to_region(rows):
    """
    Convert rows (line numbers) to a region (selection/cursor position).

    Keyword arguments:
    - rows -- Row number(s) to convert to region(s).
    """

    # Get current active view
    view = sublime.active_window().active_view()
    # Unable to convert rows to regions when no view available
    if view is None:
        return

    # List for containing regions to return
    region = []

    # Create list if it is a singleton
    if not isinstance(rows, list):
        rows = [rows]

    for row in rows:
        # Check if row is a digit
        if isinstance(row, int) or H.is_digit(row):
            # Convert from 1 based to a 0 based row (line) number
            row_number = int(row) - 1
            # Calculate offset point for row
            offset_point = view.text_point(row_number, 0)
            # Get region for row by offset point
            region_row = view.line(offset_point)
            # Add to list for result
            region.append(region_row)

    return region


def region_to_rows(region=None, filter_empty=False):
    """
    Convert a region (selection/cursor position) to rows (line numbers).

    Keyword arguments:
    - region -- sublime.Selection/sublime.RegionSet or sublime.Region to convert to row number(s).
    - filter_empty -- Filter empty rows (line numbers).
    """

    # Get current active view
    view = sublime.active_window().active_view()
    # Unable to convert regions to rows when no view available
    if view is None:
        return

    # Use current selection/cursor position if no region defined
    if region is None:
        region = view.sel()

    # List for containing rows (line numbers) to return
    rows = []

    # Create list if it is a singleton
    if isinstance(region, sublime.Region):
        region = [region]

    # Split the region up, so that each region returned exists on exactly one line
    region_split = []
    for region_part in region:
        region_split.extend(view.split_by_newlines(region_part))

    # Get row (line) number for each region area
    for region_area in region_split:
        # Retrieve line region for current region area
        row_line = view.line(region_area)
        # Check if line region is empty
        if filter_empty and row_line.empty():
            continue
        # Get beginning coordination point of line region
        row_point = row_line.begin()
        # Retrieve row (line) number and column number of region
        row, col = view.rowcol(row_point)
        # Convert from 0 based to a 1 based row (line) number
        row_number = str(row + 1)
        # Add to list for result
        rows.append(row_number)

    return rows


def render_regions(view=None):
    """
    Set breakpoint/current line marker(s) for current active view.

    Note: View rendering conflict when using same icon for different scopes in add_regions().
    """
    # Get current active view
    if view is None:
        view = sublime.active_window().active_view()
    # Unable to set regions when no view available
    if view is None:
        return

    # Do no set regions if view is empty or still loading
    if view.size() == 0 or view.is_loading():
        return

    # Remove all markers to avoid marker conflict
    view.erase_regions(S.REGION_KEY_BREAKPOINT)
    view.erase_regions(S.REGION_KEY_CURRENT)
    view.erase_regions(S.REGION_KEY_DISABLED)

    # Get filename of current view and check if is a valid filename
    filename = view.file_name()
    if not filename:
        return

    # Determine icon for regions
    icon_current = get_region_icon(S.KEY_CURRENT_LINE)
    icon_disabled = get_region_icon(S.KEY_BREAKPOINT_DISABLED)
    icon_enabled = get_region_icon(S.KEY_BREAKPOINT_ENABLED)

    # Get all (disabled) breakpoint rows (line numbers) for file
    breakpoint_rows = []
    disabled_rows = []
    if filename in S.BREAKPOINT and isinstance(S.BREAKPOINT[filename], dict):
        for lineno, bp in S.BREAKPOINT[filename].items():
            # Do not show temporary breakpoint
            if S.BREAKPOINT_RUN is not None and S.BREAKPOINT_RUN['filename'] == filename and S.BREAKPOINT_RUN['lineno'] == lineno:
                continue
            # Determine if breakpoint is enabled or disabled
            if bp['enabled']:
                breakpoint_rows.append(lineno)
            else:
                disabled_rows.append(lineno)

    # Get current line from breakpoint hit
    if S.BREAKPOINT_ROW is not None:
        # Make sure current breakpoint is in this file
        if filename == S.BREAKPOINT_ROW['filename']:
            # Remove current line number from breakpoint rows to avoid marker conflict
            if S.BREAKPOINT_ROW['lineno'] in breakpoint_rows:
                breakpoint_rows.remove(S.BREAKPOINT_ROW['lineno'])
                # Set icon for current breakpoint
                icon_breakpoint_current = get_region_icon(S.KEY_BREAKPOINT_CURRENT)
                if icon_breakpoint_current:
                    icon_current = icon_breakpoint_current
            if S.BREAKPOINT_ROW['lineno'] in disabled_rows:
                disabled_rows.remove(S.BREAKPOINT_ROW['lineno'])
            # Set current line marker
            if icon_current:
                view.add_regions(S.REGION_KEY_CURRENT, rows_to_region(S.BREAKPOINT_ROW['lineno']), S.REGION_SCOPE_CURRENT, icon_current, sublime.HIDDEN)

    # Set breakpoint marker(s)
    if breakpoint_rows and icon_enabled:
        view.add_regions(S.REGION_KEY_BREAKPOINT, rows_to_region(breakpoint_rows), S.REGION_SCOPE_BREAKPOINT, icon_enabled, sublime.HIDDEN)
    if disabled_rows and icon_disabled:
        view.add_regions(S.REGION_KEY_DISABLED, rows_to_region(disabled_rows), S.REGION_SCOPE_BREAKPOINT, icon_disabled, sublime.HIDDEN)


def toggle_breakpoint(view):
    try:
        # Get selected point in view
        point = view.sel()[0]
        # Check if selected point uses breakpoint line scope
        if point.size() == 3 and sublime.score_selector(view.scope_name(point.a), 'xdebug.output.breakpoint.line'):
            # Find line number of breakpoint
            line = view.substr(view.line(point))
            pattern = re.compile('^\\s*(?:(\\|\\+\\|)|(\\|-\\|))\\s*(?P<line_number>\\d+)\\s*(?:(--)(.*)|.*)')
            match = pattern.match(line)
            # Check if it has found line number
            if match and match.group('line_number'):
                # Get all breakpoint filenames
                breakpoint_file = view.find_by_selector('xdebug.output.breakpoint.file')
                # Locate line with filename related to selected breakpoint
                file_line = None
                for entry in breakpoint_file:
                    # Stop searching if we have passed selected breakpoint
                    if entry > point:
                        break
                    file_line = view.substr(view.line(entry))
                # Do not continue without line containing filename
                if file_line is None:
                    return
                # Remove unnecessary text from line to get filename
                file_pattern = re.compile('^\\s*(=>)\\s*(?P<filename>.*)')
                file_match = file_pattern.match(file_line)
                # Check if it is a valid filename
                if file_match and file_match.group('filename'):
                    filename = file_match.group('filename')
                    line_number = match.group('line_number')
                    enabled = None
                    # Disable breakpoint
                    if sublime.score_selector(view.scope_name(point.a), 'entity') and S.BREAKPOINT[filename][line_number]['enabled']:
                        enabled = False
                    # Enable breakpoint
                    if sublime.score_selector(view.scope_name(point.a), 'keyword') and not S.BREAKPOINT[filename][line_number]['enabled']:
                        enabled = True
                    # Toggle breakpoint only if it has valid value
                    if enabled is None:
                        return
                    sublime.active_window().run_command('xdebug_breakpoint', {"enabled": enabled, "rows": [line_number], "filename": filename})
        # Check if selected point uses breakpoint file scope
        elif point.size() > 3 and sublime.score_selector(view.scope_name(point.a), 'xdebug.output.breakpoint.file'):
            # Get filename from selected line in view
            file_line = view.substr(view.line(point))
            file_pattern = re.compile('^\\s*(=>)\\s*(?P<filename>.*)')
            file_match = file_pattern.match(file_line)
            # Show file when it's a valid filename
            if file_match and file_match.group('filename'):
                filename = file_match.group('filename')
                show_file(filename)
    except:
        pass


def toggle_stack(view):
    try:
        # Get selected point in view
        point = view.sel()[0]
        # Check if selected point uses stack entry scope
        if point.size() > 3 and sublime.score_selector(view.scope_name(point.a), 'xdebug.output.stack.entry'):
            # Get fileuri and line number from selected line in view
            line = view.substr(view.line(point))
            pattern = re.compile('^(\[\d+\])\s*(?P<fileuri>.*)(\..*)(\s*:.*?(?P<lineno>\d+))\s*(\((.*?):.*\)|$)')
            match = pattern.match(line)
            # Show file when it's a valid fileuri
            if match and match.group('fileuri'):
                filename = get_real_path(match.group('fileuri'))
                lineno = 0
                if match.group('lineno'):
                    lineno = match.group('lineno')
                show_file(filename, lineno)
    except:
        pass


def toggle_watch(view):
    # Do not try to toggle when no watch expressions defined
    if not S.WATCH:
        return
    try:
        # Get selected point in view
        point = view.sel()[0]
        # Check if selected point uses watch entry scope
        if point.size() == 3 and sublime.score_selector(view.scope_name(point.a), 'xdebug.output.watch.entry'):
            # Determine if watch entry is enabled or disabled
            line = view.substr(view.line(point))
            pattern = re.compile('^(?:(?P<enabled>\\|\\+\\|)|(?P<disabled>\\|-\\|))\\.*')
            match = pattern.match(line)
            if match and (match.group('enabled') or match.group('disabled')):
                # Get all entries and determine index by line/point match
                watch = view.find_by_selector('xdebug.output.watch.entry')
                watch_index = 0
                for entry in watch:
                    # Stop searching if we have passed selected breakpoint
                    if entry > point:
                        break
                    # Only increment watch index when it contains expression
                    watch_line = view.substr(view.line(entry))
                    watch_match = pattern.match(watch_line)
                    if watch_match and (watch_match.group('enabled') or watch_match.group('disabled')):
                        watch_index += 1
                # Disable watch expression
                if sublime.score_selector(view.scope_name(point.a), 'entity') and S.WATCH[watch_index]['enabled']:
                    S.WATCH[watch_index]['enabled'] = False
                # Enable watch expression
                if sublime.score_selector(view.scope_name(point.a), 'keyword') and not S.WATCH[watch_index]['enabled']:
                    S.WATCH[watch_index]['enabled'] = True
                # Update watch view and save watch data to file
                sublime.active_window().run_command('xdebug_watch', {"update": True})
    except:
        pass
########NEW FILE########
