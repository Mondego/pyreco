__FILENAME__ = swi
import hashlib
import functools
import glob
import sublime
import sublime_plugin
import websocket
import urllib2
import threading
import json
import types
import os
import re
import wip
import time
from wip import utils
from wip import Console
from wip import Runtime
from wip import Debugger
from wip import Network
from wip import Page
import sys

reload(sys.modules['wip.utils'])
reload(sys.modules['wip.Console'])
reload(sys.modules['wip.Runtime'])
reload(sys.modules['wip.Debugger'])
reload(sys.modules['wip.Network'])
reload(sys.modules['wip.Page'])

brk_object = {}
buffers = {}
protocol = None
original_layout = None
window = None
debug_view = None
debug_url = None
file_to_scriptId = []
project_folders = []
last_clicked = None
paused = False
current_line = None
reload_on_start = False
reload_on_save = False
set_script_source = False
current_call_frame = None
current_call_frame_position = None
open_stack_current_in_new_tab = True
timing = time.time()


# scriptId_fileName = {}

breakpoint_active_icon = '../Web Inspector/icons/breakpoint_active'
breakpoint_inactive_icon = '../Web Inspector/icons/breakpoint_inactive'
breakpoint_current_icon = '../Web Inspector/icons/breakpoint_current'


####################################################################################
#   PROTOCOL
####################################################################################

# Define protocol to communicate with remote debugger by web sockets
class Protocol(object):
    def __init__(self):
        self.next_id = 0
        self.commands = {}
        self.notifications = {}
        self.last_log_object = None

    def connect(self, url, on_open=None, on_close=None):
        print 'SWI: Connecting to ' + url
        websocket.enableTrace(False)
        self.last_break = None
        self.last_log_object = None
        self.url = url
        self.on_open = on_open
        self.on_close = on_close
        thread = threading.Thread(target=self.thread_callback)
        thread.start()

    # start connect with new thread
    def thread_callback(self):
        print 'SWI: Thread started'
        self.socket = websocket.WebSocketApp(self.url, on_message=self.message_callback, on_open=self.open_callback, on_close=self.close_callback)
        self.socket.run_forever()
        print 'SWI: Thread stoped'

    # send command and increment command counter
    def send(self, command, callback=None, options=None):
        command.id = self.next_id
        command.callback = callback
        command.options = options
        self.commands[command.id] = command
        self.next_id += 1
        # print 'SWI: ->> ' + json.dumps(command.request)
        self.socket.send(json.dumps(command.request))

    # subscribe to notification with callback
    def subscribe(self, notification, callback):
        notification.callback = callback
        self.notifications[notification.name] = notification

    # unsubscribe
    def unsubscribe(self, notification):
        del self.notifications[notification.name]

    # unsubscribe
    def message_callback(self, ws, message):
        parsed = json.loads(message)
        # print 'SWI: <<- ' + message
        # print ''
        if 'method' in parsed:
            if parsed['method'] in self.notifications:
                notification = self.notifications[parsed['method']]
                if 'params' in parsed:
                    data = notification.parser(parsed['params'])
                else:
                    data = None
                notification.callback(data, notification)
            # else:
                # print 'SWI: New unsubscrib notification --- ' + parsed['method']
        else:
            if parsed['id'] in self.commands:

                command = self.commands[parsed['id']]

                if 'error' in parsed:
                    sublime.set_timeout(lambda: sublime.error_message(parsed['error']['message']), 0)
                else:
                    if 'result' in parsed:
                        command.data = command.parser(parsed['result'])
                    else:
                        command.data = None

                    if command.callback:
                        command.callback(command)
            # print 'SWI: Command response with ID ' + str(parsed['id'])

    def open_callback(self, ws):
        if self.on_open:
            self.on_open()
        print 'SWI: WebSocket opened'

    def close_callback(self, ws):
        if self.on_close:
            self.on_close()
        print 'SWI: WebSocket closed'


####################################################################################
#   COMMANDS
####################################################################################

class SwiDebugCommand(sublime_plugin.TextCommand):
    '''
    The SWIdebug main quick panel menu
    '''
    def run(self, editswi):
        mapping = {}
        try:
            urllib2.urlopen('http://127.0.0.1:' + get_setting('chrome_remote_port') + '/json')

            mapping = {}

            if paused:
                mapping['swi_debug_resume'] = 'Resume execution'
                mapping['swi_debug_evaluate_on_call_frame'] = 'Evaluate selection'
                #mapping['swi_debug_step_into'] = 'Step into'
                #mapping['swi_debug_step_out'] = 'Step out'
                #mapping['swi_debug_step_over'] = 'Step over'
            else:
                #mapping['swi_debug_clear_all_breakpoint'] = 'Clear all Breakpoints'
                mapping['swi_debug_breakpoint'] = 'Add/Remove Breakpoint'

            if protocol:
                mapping['swi_debug_clear_console'] = 'Clear console'
                mapping['swi_debug_stop'] = 'Stop debugging'
                mapping['swi_debug_reload'] = 'Reload page'
            else:
                mapping['swi_debug_start'] = 'Start debugging'
        except:
            mapping['swi_debug_start_chrome'] = 'Start Google Chrome with remote debug port ' + get_setting('chrome_remote_port')

        self.cmds = mapping.keys()
        self.items = mapping.values()
        self.view.window().show_quick_panel(self.items, self.command_selected)

    def command_selected(self, index):
        if index == -1:
            return

        command = self.cmds[index]

        if command == 'swi_debug_start':
            response = urllib2.urlopen('http://127.0.0.1:' + get_setting('chrome_remote_port') + '/json')
            pages = json.loads(response.read())
            mapping = {}
            for page in pages:
                if 'webSocketDebuggerUrl' in page:
                    if page['url'].find('chrome-extension://') == -1:
                        mapping[page['webSocketDebuggerUrl']] = page['url']

            self.urls = mapping.keys()
            items = mapping.values()
            self.view.window().show_quick_panel(items, self.remote_debug_url_selected)
            return

        self.view.run_command(command)

    def remote_debug_url_selected(self, index):
        if index == -1:
            return

        url = self.urls[index]

        global window
        window = sublime.active_window()

        global original_layout
        original_layout = window.get_layout()

        global debug_view
        debug_view = window.active_view()

        window.set_layout(get_setting('console_layout'))

        load_breaks()
        self.view.run_command('swi_debug_start', {'url': url})


class SwiDebugStartChromeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        window = sublime.active_window()

        window.run_command('exec', {
            "cmd": [os.getenv('GOOGLE_CHROME_PATH', '')+get_setting('chrome_path')[sublime.platform()], '--remote-debugging-port=' + get_setting('chrome_remote_port'), '--profile-directory='+ get_setting('chrome_profile'), '']
        })


class SwiDebugStartCommand(sublime_plugin.TextCommand):

    def run(self, edit, url):
        global file_to_scriptId
        file_to_scriptId = []
        window = sublime.active_window()
        global project_folders
        project_folders = window.folders()
        print 'Starting SWI'
        self.url = url
        global protocol
        if(protocol):
            print 'SWI: Socket closed'
            protocol.socket.close()
        else:
            print 'SWI: Creating protocol'
            protocol = Protocol()
            protocol.connect(self.url, self.connected, self.disconnected)

        global reload_on_start
        reload_on_start = get_setting('reload_on_start')

        global reload_on_save
        reload_on_save = get_setting('reload_on_save')

        global set_script_source
        set_script_source = get_setting('set_script_source')

        global open_stack_current_in_new_tab
        open_stack_current_in_new_tab = get_setting('open_stack_current_in_new_tab')

    def connected(self):
        protocol.subscribe(wip.Console.messageAdded(), self.messageAdded)
        protocol.subscribe(wip.Console.messageRepeatCountUpdated(), self.messageRepeatCountUpdated)
        protocol.subscribe(wip.Console.messagesCleared(), self.messagesCleared)
        protocol.subscribe(wip.Debugger.scriptParsed(), self.scriptParsed)
        protocol.subscribe(wip.Debugger.paused(), self.paused)
        protocol.subscribe(wip.Debugger.resumed(), self.resumed)
        protocol.send(wip.Debugger.enable())
        protocol.send(wip.Console.enable())
        protocol.send(wip.Debugger.canSetScriptSource(), self.canSetScriptSource)
        if reload_on_start:
            protocol.send(wip.Network.clearBrowserCache())
            protocol.send(wip.Page.reload(), on_reload)

    def disconnected(self):
        sublime.set_timeout(lambda: debug_view.run_command('swi_debug_stop'), 0)

    def messageAdded(self, data, notification):
        sublime.set_timeout(lambda: console_add_message(data), 0)

    def messageRepeatCountUpdated(self, data, notification):
        sublime.set_timeout(lambda: console_repeat_message(data['count']), 0)

    def messagesCleared(self, data, notification):
        sublime.set_timeout(lambda: clear_view('console'), 0)

    def scriptParsed(self, data, notification):
        url = data['url']
        if url != '':
            url_parts = url.split("/")
            scriptId = str(data['scriptId'])
            file_name = ''

            script = get_script(data['url'])

            if script:
                script['scriptId'] = str(scriptId)
                file_name = script['file']
            else:
                del url_parts[0:3]
                while len(url_parts) > 0:
                    for folder in project_folders:
                        if sublime.platform() == "windows":
                            files = glob.glob(folder + "\\*\\" + "\\".join(url_parts))
                        else:
                            files = glob.glob(folder + "/*/" + "/".join(url_parts))

                        if len(files) > 0 and files[0] != '':
                            file_name = files[0]
                            file_to_scriptId.append({'file': file_name, 'scriptId': str(scriptId), 'sha1': hashlib.sha1(data['url']).hexdigest()})
                    del url_parts[0]

            if get_breakpoints_by_full_path(file_name):
                for line in get_breakpoints_by_full_path(file_name).keys():
                    location = wip.Debugger.Location({'lineNumber': int(line), 'scriptId': scriptId})
                    protocol.send(wip.Debugger.setBreakpoint(location), self.breakpointAdded)

    def paused(self, data, notification):
        sublime.set_timeout(lambda: window.set_layout(get_setting('stack_layout')), 0)

        sublime.set_timeout(lambda: console_show_stack(data['callFrames']), 0)

        scriptId = data['callFrames'][0].location.scriptId
        line_number = data['callFrames'][0].location.lineNumber
        file_name = find_script(str(scriptId))
        first_scope = data['callFrames'][0].scopeChain[0]

        if open_stack_current_in_new_tab:
            title = {'objectId': first_scope.object.objectId, 'name': "%s:%s (%s)" % (file_name, line_number, first_scope.type)}
        else:
            title = {'objectId': first_scope.object.objectId, 'name': "Breakpoint Local"}

        global current_call_frame
        current_call_frame = data['callFrames'][0].callFrameId

        global current_call_frame_position
        current_call_frame_position = "%s:%s" % (file_name, line_number)

        sublime.set_timeout(lambda: protocol.send(wip.Runtime.getProperties(first_scope.object.objectId, True), console_add_properties, title), 30)
        sublime.set_timeout(lambda: open_script_and_focus_line(scriptId, line_number), 100)

        global paused
        paused = True

    def resumed(self, data, notification):
        sublime.set_timeout(lambda: clear_view('stack'), 0)

        global current_line
        current_line = None

        global current_call_frame
        current_call_frame = None

        global current_call_frame_position
        current_call_frame_position = None

        sublime.set_timeout(lambda: lookup_view(self.view).view_breakpoints(), 50)

        global paused
        paused = False

    def breakpointAdded(self, command):
        breakpointId = command.data['breakpointId']
        scriptId = command.data['actualLocation'].scriptId
        lineNumber = command.data['actualLocation'].lineNumber

        try:
            breakpoint = get_breakpoints_by_scriptId(str(scriptId))[str(lineNumber)]
            breakpoint['status'] = 'enabled'
            breakpoint['breakpointId'] = str(breakpointId)
        except:
            pass

        try:
            breaks = get_breakpoints_by_scriptId(str(scriptId))[str(lineNumber)]

            lineNumber = str(lineNumber)
            lineNumberSend = str(command.params['lineNumber'])

            if lineNumberSend in breaks and lineNumber != lineNumberSend:
                breaks[lineNumber] = breaks[lineNumberSend].copy()
                del breaks[lineNumberSend]

            breaks[lineNumber]['status'] = 'enabled'
            breaks[lineNumber]['breakpointId'] = str(breakpointId)
        except:
            pass

        sublime.set_timeout(lambda: save_breaks(), 0)
        sublime.set_timeout(lambda: lookup_view(self.view).view_breakpoints(), 0)

    def canSetScriptSource(self, command):
        global set_script_source
        if set_script_source:
            set_script_source = command.data['result']


class SwiDebugResumeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        protocol.send(wip.Debugger.resume())


class SwiDebugStepIntoCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        protocol.send(wip.Debugger.stepInto())


class SwiDebugStepOutCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        protocol.send(wip.Debugger.stepOut())


class SwiDebugStepOverCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        protocol.send(wip.Debugger.stepOver())


class SwiDebugClearConsoleCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        sublime.set_timeout(lambda: clear_view('console'), 0)


class SwiDebugEvaluateOnCallFrameCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        for region in self.view.sel():
            title = self.view.substr(region)
            if current_call_frame_position:
                title = "%s on %s" % (self.view.substr(region), current_call_frame_position)
            protocol.send(wip.Debugger.evaluateOnCallFrame(current_call_frame, self.view.substr(region)), self.evaluated, {'name': title})

    def evaluated(self, command):
        if command.data.type == 'object':
            protocol.send(wip.Runtime.getProperties(command.data.objectId, True), console_add_properties, command.options)
        else:
            sublime.set_timeout(lambda: console_add_evaluate(command.data), 0)


class SwiDebugBreakpointCommand(sublime_plugin.TextCommand):
    '''
    Toggle a breakpoint
    '''
    def run(self, edit):
        view = lookup_view(self.view)
        row = str(view.rows(view.lines())[0])
        init_breakpoint_for_file(view.file_name())
        breaks = get_breakpoints_by_full_path(view.file_name())
        if row in breaks:
            if protocol:
                if row in breaks:
                    protocol.send(wip.Debugger.removeBreakpoint(breaks[row]['breakpointId']))

            del_breakpoint_by_full_path(view.file_name(), row)
        else:
            if protocol:
                scriptId = find_script(view.file_name())
                if scriptId:
                    location = wip.Debugger.Location({'lineNumber': int(row), 'scriptId': scriptId})
                    protocol.send(wip.Debugger.setBreakpoint(location), self.breakpointAdded, view.file_name())
            else:
                set_breakpoint_by_full_path(view.file_name(), row)

        view.view_breakpoints()

    def breakpointAdded(self, command):
        breakpointId = command.data['breakpointId']
        scriptId = command.data['actualLocation'].scriptId
        lineNumber = command.data['actualLocation'].lineNumber

        init_breakpoint_for_file(command.options)

        sublime.set_timeout(lambda: set_breakpoint_by_scriptId(str(scriptId), str(lineNumber), 'enabled', breakpointId), 0)
        # Scroll to position where breakpoints have resolved
        sublime.set_timeout(lambda: lookup_view(self.view).view_breakpoints(), 0)


class SwiDebugStopCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global window

        window.focus_group(1)
        for view in window.views_in_group(1):
            window.run_command("close")

        window.focus_group(2)
        for view in window.views_in_group(2):
            window.run_command("close")

        window.set_layout(original_layout)

        disable_all_breakpoints()

        lookup_view(self.view).view_breakpoints()

        global paused
        paused = False

        global current_line
        current_line = None
        sublime.set_timeout(lambda: lookup_view(self.view).view_breakpoints(), 0)

        global protocol
        if protocol:
            try:
                protocol.socket.close()
            except:
                print 'SWI: Can\'t close soket'
            finally:
                protocol = None


class SwiDebugReloadCommand(sublime_plugin.TextCommand):
    def run(self, view):
        if(protocol):
            protocol.send(wip.Network.clearBrowserCache())
            protocol.send(wip.Page.reload(), on_reload)


####################################################################################
#   VIEW
####################################################################################

class SwiDebugView(object):
    '''
    The SWIDebugView is sort of a normal view with some convenience methods.

    See lookup_view.
    '''
    def __init__(self, view):
        self.view = view
        self.context_data = {}
        self.clicks = []
        self.prev_click_position = 0

    def __getattr__(self, attr):
        if hasattr(self.view, attr):
            return getattr(self.view, attr)
        if attr.startswith('on_'):
            return self
        raise(AttributeError, "%s does not exist" % attr)

    def __call__(self, *args, **kwargs):
        pass

    def uri(self):
        return 'file://' + os.path.realpath(self.view.file_name())

    def lines(self, data=None):
        lines = []
        if data is None:
            regions = self.view.sel()
        else:
            if type(data) != types.ListType:
                data = [data]
            regions = []
            for item in data:
                if type(item) == types.IntType or item.isdigit():
                    regions.append(self.view.line(self.view.text_point(int(item) - 1, 0)))
                else:
                    regions.append(item)
        for region in regions:
            lines.extend(self.view.split_by_newlines(region))
        return [self.view.line(line) for line in lines]

    def rows(self, lines):
        if not type(lines) == types.ListType:
            lines = [lines]
        return [self.view.rowcol(line.begin())[0] + 1 for line in lines]

    def insert_click(self, a, b, click_type, data):
        insert_before = 0
        new_region = sublime.Region(a, b)
        regions = self.view.get_regions('swi_log_clicks')
        for region in regions:
            if new_region.b < region.a:
                break
            insert_before += 1

        self.clicks.insert(insert_before, {'click_type': click_type, 'data': data})

        regions.append(new_region)
        self.view.add_regions('swi_log_clicks', regions, get_setting('interactive_scope'), sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED)

    def print_click(self, edit, position, text, click_type, data):
        insert_length = self.insert(edit, position, text)
        self.insert_click(position, position + insert_length, click_type, data)

    def remove_click(self, index):
        regions = self.view.get_regions('swi_log_clicks')
        del regions[index]
        self.view.add_regions('swi_log_clicks', regions, get_setting('interactive_scope'), sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED)

    def clear_clicks(self):
        self.clicks = []

    def view_breakpoints(self):
        self.view.erase_regions('swi_breakpoint_inactive')
        self.view.erase_regions('swi_breakpoint_active')
        self.view.erase_regions('swi_breakpoint_current')

        if not self.view.file_name():
            return

        breaks = get_breakpoints_by_full_path(self.view.file_name())

        if not breaks:
            return

        enabled = []
        disabled = []

        for key in breaks.keys():
            if breaks[key]['status'] == 'enabled' and str(current_line) != key:
                enabled.append(key)
            if breaks[key]['status'] == 'disabled' and str(current_line) != key:
                disabled.append(key)

        self.view.add_regions('swi_breakpoint_active', self.lines(enabled), get_setting('breakpoint_scope'), breakpoint_active_icon, sublime.HIDDEN)
        self.view.add_regions('swi_breakpoint_inactive', self.lines(disabled), get_setting('breakpoint_scope'), breakpoint_inactive_icon, sublime.HIDDEN)
        if current_line:
            self.view.add_regions('swi_breakpoint_current', self.lines([current_line]), get_setting('current_line_scope'), breakpoint_current_icon, sublime.DRAW_EMPTY)

    def check_click(self):
        if not self.name().startswith('SWI'):
            return

        cursor = self.sel()[0].a

        if cursor == self.prev_click_position:
            return

        self.prev_click_position = cursor
        click_counter = 0
        click_regions = self.get_regions('swi_log_clicks')
        for click in click_regions:
            if cursor > click.a and cursor < click.b:

                if click_counter < len(self.clicks):
                    click = self.clicks[click_counter]

                    if click['click_type'] == 'goto_file_line':
                        open_script_and_focus_line(click['data']['scriptId'], click['data']['line'])

                    if click['click_type'] == 'goto_call_frame':
                        callFrame = click['data']['callFrame']

                        scriptId = callFrame.location.scriptId
                        line_number = callFrame.location.lineNumber
                        file_name = find_script(str(scriptId))

                        open_script_and_focus_line(scriptId, line_number)

                        first_scope = callFrame.scopeChain[0]

                        if open_stack_current_in_new_tab:
                            title = {'objectId': first_scope.object.objectId, 'name': "%s:%s (%s)" % (file_name.split('/')[-1], line_number, first_scope.type)}
                        else:
                            title = {'objectId': first_scope.object.objectId, 'name': "Breakpoint Local"}

                        sublime.set_timeout(lambda: protocol.send(wip.Runtime.getProperties(first_scope.object.objectId, True), console_add_properties, title), 30)

                        global current_call_frame
                        current_call_frame = callFrame.callFrameId

                        global current_call_frame_position
                        current_call_frame_position = "%s:%s" % (file_name.split('/')[-1], line_number)

                    if click['click_type'] == 'get_params':
                        if protocol:
                            protocol.send(wip.Runtime.getProperties(click['data']['objectId'], True), console_add_properties, click['data'])

                    if click['click_type'] == 'command':
                        self.remove_click(click_counter)
                        self.run_command(click['data'])

            click_counter += 1


def lookup_view(v):
    '''
    Convert a Sublime View into an SWIDebugView
    '''
    if isinstance(v, SwiDebugView):
        return v
    if isinstance(v, sublime.View):
        id = v.buffer_id()
        if id in buffers:
            buffers[id].view = v
        else:
            buffers[id] = SwiDebugView(v)
        return buffers[id]
    return None


####################################################################################
#   EventListener
####################################################################################

class EventListener(sublime_plugin.EventListener):
    def on_new(self, view):
        lookup_view(view).on_new()

    def on_clone(self, view):
        lookup_view(view).on_clone()

    def on_load(self, view):
        lookup_view(view).view_breakpoints()
        lookup_view(view).on_load()

    def on_close(self, view):
        lookup_view(view).on_close()

    def on_pre_save(self, view):
        lookup_view(view).on_pre_save()

    def on_post_save(self, view):
        print view.file_name().find('.js')
        if protocol and reload_on_save:
            protocol.send(wip.Network.clearBrowserCache())
            if view.file_name().find('.css') > 0 or view.file_name().find('.less') > 0 or view.file_name().find('.sass') > 0 or view.file_name().find('.scss') > 0 or view.file_name().find('.styl') > 0:
                protocol.send(wip.Runtime.evaluate("var files = document.getElementsByTagName('link');var links = [];for (var a = 0, l = files.length; a < l; a++) {var elem = files[a];var rel = elem.rel;if (typeof rel != 'string' || rel.length === 0 || rel === 'stylesheet') {links.push({'elem': elem,'href': elem.getAttribute('href').split('?')[0],'last': false});}}for ( a = 0, l = links.length; a < l; a++) {var link = links[a];link.elem.setAttribute('href', (link.href + '?x=' + Math.random()));}"))
            elif view.file_name().find('.js') > 0:
                scriptId = find_script(view.file_name())
                if scriptId and set_script_source:
                    scriptSource = view.substr(sublime.Region(0, view.size()))
                    protocol.send(wip.Debugger.setScriptSource(scriptId, scriptSource), self.paused)
                else:
                    protocol.send(wip.Page.reload(), on_reload)
            else:
                protocol.send(wip.Page.reload(), on_reload)
        lookup_view(view).on_post_save()

    def on_modified(self, view):
        lookup_view(view).on_modified()
        lookup_view(view).view_breakpoints()

    def on_selection_modified(self, view):
        #lookup_view(view).on_selection_modified()
        global timing
        now = time.time()
        if now - timing > 0.08:
            timing = now
            sublime.set_timeout(lambda: lookup_view(view).check_click(), 0)
        else:
            timing = now

    def on_activated(self, view):
        lookup_view(view).on_activated()
        lookup_view(view).view_breakpoints()

    def on_deactivated(self, view):
        lookup_view(view).on_deactivated()

    def on_query_context(self, view, key, operator, operand, match_all):
        lookup_view(view).on_query_context(key, operator, operand, match_all)

    def paused(self, command):
        global paused

        if not paused:
            return

        data = command.data
        sublime.set_timeout(lambda: window.set_layout(get_setting('stack_layout')), 0)

        sublime.set_timeout(lambda: console_show_stack(data['callFrames']), 0)

        scriptId = data['callFrames'][0].location.scriptId
        line_number = data['callFrames'][0].location.lineNumber
        file_name = find_script(str(scriptId))
        first_scope = data['callFrames'][0].scopeChain[0]

        if open_stack_current_in_new_tab:
            title = {'objectId': first_scope.object.objectId, 'name': "%s:%s (%s)" % (file_name, line_number, first_scope.type)}
        else:
            title = {'objectId': first_scope.object.objectId, 'name': "Breakpoint Local"}

        sublime.set_timeout(lambda: protocol.send(wip.Runtime.getProperties(first_scope.object.objectId, True), console_add_properties, title), 30)
        sublime.set_timeout(lambda: open_script_and_focus_line(scriptId, line_number), 100)


####################################################################################
#   GLOBAL HANDLERS
####################################################################################

def on_reload(command):
    global file_to_scriptId
    file_to_scriptId = []


####################################################################################
#   Console
####################################################################################

def find_view(console_type, title=''):
    found = False
    v = None
    window = sublime.active_window()

    if console_type.startswith('console'):
        group = 1
        fullName = "SWI Console"

    if console_type == 'stack':
        group = 2
        fullName = "SWI Breakpoint stack"

    if console_type.startswith('eval'):
        group = 1
        fullName = "SWI Object evaluate"

    fullName = fullName + ' ' + title

    for v in window.views():
        if v.name() == fullName:
            found = True
            break

    if not found:
        v = window.new_file()
        v.set_scratch(True)
        v.set_read_only(False)
        v.set_name(fullName)
        v.settings().set('word_wrap', False)

    window.set_view_index(v, group, 0)

    if console_type.startswith('console'):
        v.set_syntax_file('Packages/Web Inspector/swi_log.tmLanguage')

    if console_type == 'stack':
        v.set_syntax_file('Packages/Web Inspector/swi_stack.tmLanguage')

    if console_type.startswith('eval'):
        v.set_syntax_file('Packages/Web Inspector/swi_log.tmLanguage')

    window.focus_view(v)

    v.set_read_only(False)

    return lookup_view(v)


def clear_view(view):
    v = find_view(view)

    edit = v.begin_edit()

    v.erase(edit, sublime.Region(0, v.size()))

    v.end_edit(edit)
    v.show(v.size())
    window.focus_group(0)
    lookup_view(v).clear_clicks()


def console_repeat_message(count):
    v = find_view('console')

    edit = v.begin_edit()

    if count > 2:
        erase_to = v.size() - len(u' \u21AA Repeat:' + str(count - 1) + '\n')
        v.erase(edit, sublime.Region(erase_to, v.size()))
    v.insert(edit, v.size(), u' \u21AA Repeat:' + str(count) + '\n')

    v.end_edit(edit)
    v.show(v.size())
    window.focus_group(0)


def console_add_evaluate(eval_object):
    v = find_view('console')

    edit = v.begin_edit()

    insert_position = v.size()
    v.insert(edit, insert_position, str(eval_object) + ' ')

    v.insert(edit, v.size(), "\n")

    v.end_edit(edit)
    v.show(v.size())
    window.focus_group(0)


def console_add_message(message):
    v = find_view('console')

    edit = v.begin_edit()

    if message.level == 'debug':
        level = "D"
    if message.level == 'error':
        level = "E"
    if message.level == 'log':
        level = "L"
    if message.level == 'tip':
        level = "T"
    if message.level == 'warning':
        level = "W"

    v.insert(edit, v.size(), "[%s] " % (level))
    # Add file and line
    scriptId = None
    if message.url:
        scriptId = find_script(message.url)
        if scriptId:
            url = message.url.split("/")[-1]
        else:
            url = message.url
    else:
        url = '---'

    if message.line:
        line = message.line
    else:
        line = 0

    insert_position = v.size()
    insert_length = v.insert(edit, insert_position, "%s:%d" % (url, line))

    if scriptId and line > 0:
        v.insert_click(insert_position, insert_position + insert_length, 'goto_file_line', {'scriptId': scriptId, 'line': str(line)})

    v.insert(edit, v.size(), " ")

    # Add text
    if len(message.parameters) > 0:
        for param in message.parameters:
            insert_position = v.size()
            insert_length = v.insert(edit, insert_position, str(param) + ' ')
            if param.type == 'object':
                v.insert_click(insert_position, insert_position + insert_length - 1, 'get_params', {'objectId': param.objectId})
    else:
        v.insert(edit, v.size(), message.text)

    v.insert(edit, v.size(), "\n")

    if level == "E" and message.stackTrace:
        stack_start = v.size()

        for callFrame in message.stackTrace:
            scriptId = find_script(callFrame.url)
            file_name = callFrame.url.split('/')[-1]

            v.insert(edit, v.size(),  u'\t\u21E1 ')

            if scriptId:
                v.print_click(edit, v.size(), "%s:%s %s" % (file_name, callFrame.lineNumber, callFrame.functionName), 'goto_file_line', {'scriptId': scriptId, 'line': str(callFrame.lineNumber)})
            else:
                v.insert(edit, v.size(),  "%s:%s %s" % (file_name, callFrame.lineNumber, callFrame.functionName))

            v.insert(edit, v.size(), "\n")

        v.fold(sublime.Region(stack_start-1, v.size()-1))

    v.end_edit(edit)
    v.show(v.size())
    window.focus_group(0)


def console_add_properties(command):
    sublime.set_timeout(lambda: console_print_properties(command), 0)


def console_print_properties(command):

    if 'name' in command.options:
        name = command.options['name']
    else:
        name = str(command.options['objectId'])

    if 'prev' in command.options:
        prev = command.options['prev'] + ' -> ' + name
    else:
        prev = name

    v = find_view('eval', name)

    edit = v.begin_edit()
    v.erase(edit, sublime.Region(0, v.size()))

    v.insert(edit, v.size(), prev)

    v.insert(edit, v.size(), "\n\n")

    for prop in command.data:
        v.insert(edit, v.size(), prop.name + ': ')
        insert_position = v.size()
        if(prop.value):
            insert_length = v.insert(edit, insert_position, str(prop.value) + '\n')
            if prop.value.type == 'object':
                v.insert_click(insert_position, insert_position + insert_length - 1, 'get_params', {'objectId': prop.value.objectId, 'name': prop.name, 'prev': prev})

    v.end_edit(edit)
    v.show(0)
    window.focus_group(0)


def console_show_stack(callFrames):

    v = find_view('stack')

    edit = v.begin_edit()
    v.erase(edit, sublime.Region(0, v.size()))

    v.insert(edit, v.size(), "\n")
    v.print_click(edit, v.size(), "\tResume\t", 'command', 'swi_debug_resume')
    v.print_click(edit, v.size(), "\tStep Over\t", 'command', 'swi_debug_step_over')
    v.print_click(edit, v.size(), "\tStep Into\t", 'command', 'swi_debug_step_into')
    v.print_click(edit, v.size(), "\tStep Out\t", 'command', 'swi_debug_step_out')
    v.insert(edit, v.size(), "\n\n")

    for callFrame in callFrames:
        line = str(callFrame.location.lineNumber)
        file_name = find_script(str(callFrame.location.scriptId))

        if file_name:
            file_name = file_name.split('/')[-1]
        else:
            file_name = '-'

        insert_position = v.size()
        insert_length = v.insert(edit, insert_position, "%s:%s" % (file_name, line))

        if file_name != '-':
            v.insert_click(insert_position, insert_position + insert_length, 'goto_call_frame', {'callFrame': callFrame})

        v.insert(edit, v.size(), " %s\n" % (callFrame.functionName))

        for scope in callFrame.scopeChain:
            v.insert(edit, v.size(), "\t")
            insert_position = v.size()
            insert_length = v.insert(edit, v.size(), "%s\n" % (scope.type))
            if scope.object.type == 'object':
                v.insert_click(insert_position, insert_position + insert_length - 1, 'get_params', {'objectId': scope.object.objectId, 'name': "%s:%s (%s)" % (file_name, line, scope.type)})

    v.end_edit(edit)
    v.show(0)
    window.focus_group(0)


####################################################################################
#   All about breaks
####################################################################################


def get_project():
    if not sublime.active_window():
        return None
    win_id = sublime.active_window().id()
    project = None
    reg_session = os.path.join(sublime.packages_path(), "..", "Settings", "Session.sublime_session")
    auto_save = os.path.join(sublime.packages_path(), "..", "Settings", "Auto Save Session.sublime_session")
    session = auto_save if os.path.exists(auto_save) else reg_session

    if not os.path.exists(session) or win_id == None:
        return project

    try:
        with open(session, 'r') as f:
            # Tabs in strings messes things up for some reason
            j = json.JSONDecoder(strict=False).decode(f.read())
            for w in j['windows']:
                if w['window_id'] == win_id:
                    if "workspace_name" in w:
                        if sublime.platform() == "windows":
                            # Account for windows specific formatting
                            project = os.path.normpath(w["workspace_name"].lstrip("/").replace("/", ":/", 1))
                        else:
                            project = w["workspace_name"]
                        break
    except:
        pass

    # Throw out empty project names
    if project == None or re.match(".*\\.sublime-project", project) == None or not os.path.exists(project):
        project = None

    return project


def load_breaks():
    # if not get_project():
    #     sublime.error_message('Can\' load breaks')
    #     brk_object = {}
    #     return
    # breaks_file = os.path.splitext(get_project())[0] + '-breaks.json'
    # global brk_object
    # if not os.path.exists(breaks_file):
    #     with open(breaks_file, 'w') as f:
    #         f.write('{}')

    # try:
    #     with open(breaks_file, 'r') as f:
    #         brk_object = json.loads(f.read())
    # except:
    #     brk_object = {}
    global brk_object
    brk_object = get_setting('breaks')


def save_breaks():
    # try:
    #     breaks_file = os.path.splitext(get_project())[0] + '-breaks.json'
    #     with open(breaks_file, 'w') as f:
    #         f.write(json.dumps(brk_object, sort_keys=True, indent=4, separators=(',', ': ')))
    # except:
    #     pass
    s = sublime.load_settings("swi.sublime-settings")
    s.set('breaks', brk_object)
    sublime.save_settings("swi.sublime-settings")

    #print breaks


def full_path_to_file_name(path):
    return os.path.basename(os.path.realpath(path))


def set_breakpoint_by_full_path(file_name, line, status='disabled', breakpointId=None):
    breaks = get_breakpoints_by_full_path(file_name)

    if not line in breaks:
        breaks[line] = {}
        breaks[line]['status'] = status
        breaks[line]['breakpointId'] = str(breakpointId)
    else:
        breaks[line]['status'] = status
        breaks[line]['breakpointId'] = str(breakpointId)
    save_breaks()


def del_breakpoint_by_full_path(file_name, line):
    breaks = get_breakpoints_by_full_path(file_name)

    if line in breaks:
        del breaks[line]
    save_breaks()


def get_breakpoints_by_full_path(file_name):
    if file_name in brk_object:
        return brk_object[file_name]

    return None


def set_breakpoint_by_scriptId(scriptId, line, status='disabled', breakpointId=None):
    file_name = find_script(str(scriptId))
    if file_name:
        set_breakpoint_by_full_path(file_name, line, status, breakpointId)


def del_breakpoint_by_scriptId(scriptId, line):
    file_name = find_script(str(scriptId))
    if file_name:
        del_breakpoint_by_full_path(file_name, line)


def get_breakpoints_by_scriptId(scriptId):
    file_name = find_script(str(scriptId))
    if file_name:
        return get_breakpoints_by_full_path(file_name)

    return None


def init_breakpoint_for_file(file_path):
    if not file_path in brk_object:
        brk_object[file_path] = {}


def disable_all_breakpoints():
    for file_name in brk_object:
        for line in brk_object[file_name]:
            brk_object[file_name][line]['status'] = 'disabled'
            if 'breakpointId' in brk_object[file_name][line]:
                del brk_object[file_name][line]['breakpointId']

    save_breaks()


####################################################################################
#   Utils
####################################################################################

def get_setting(key):
    s = sublime.load_settings("swi.sublime-settings")
    if s and s.has(key):
        return s.get(key)


def find_script(scriptId_or_file_or_url):
    sha = hashlib.sha1(scriptId_or_file_or_url).hexdigest()
    for item in file_to_scriptId:
        if item['scriptId'] == scriptId_or_file_or_url:
            return item['file']
        if item['file'] == scriptId_or_file_or_url:
            return item['scriptId']
        if item['sha1'] == sha:
            return item['scriptId']

    return None

def get_script(scriptId_or_file_or_url):
    sha = hashlib.sha1(scriptId_or_file_or_url).hexdigest()
    for item in file_to_scriptId:
        if item['scriptId'] == scriptId_or_file_or_url:
            return item
        if item['file'] == scriptId_or_file_or_url:
            return item
        if item['sha1'] == sha:
            return item

    return None


def do_when(conditional, callback, *args, **kwargs):
    if conditional():
        return callback(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)


def open_script_and_focus_line(scriptId, line_number):
    file_name = find_script(str(scriptId))
    window = sublime.active_window()
    window.focus_group(0)
    view = window.open_file(file_name, sublime.TRANSIENT)
    do_when(lambda: not view.is_loading(), lambda: view.run_command("goto_line", {"line": line_number}))


def open_script_and_show_current_breakpoint(scriptId, line_number):
    file_name = find_script(str(scriptId))
    window.focus_group(0)
    view = window.open_file(file_name, sublime.TRANSIENT)
    do_when(lambda: not view.is_loading(), lambda: view.run_command("goto_line", {"line": line_number}))
    #do_when(lambda: not view.is_loading(), lambda: focus_line_and_highlight(view, line_number))


def focus_line_and_highlight(view, line_number):
    view.run_command("goto_line", {"line": line_number})
    global current_line
    current_line = line_number
    lookup_view(view).view_breakpoints()

sublime.set_timeout(lambda: load_breaks(), 1000)

########NEW FILE########
__FILENAME__ = websocket
"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""        


import socket
from urlparse import urlparse
import os
import struct
import uuid
import sha
import base64
import logging

"""
websocket python client.
=========================

This version support only hybi-13.
Please see http://tools.ietf.org/html/rfc6455 for protocol.
"""


# websocket supported version.
VERSION = 13

# closing frame status codes.
STATUS_NORMAL = 1000
STATUS_GOING_AWAY = 1001
STATUS_PROTOCOL_ERROR = 1002
STATUS_UNSUPPORTED_DATA_TYPE = 1003
STATUS_STATUS_NOT_AVAILABLE = 1005
STATUS_ABNORMAL_CLOSED = 1006
STATUS_INVALID_PAYLOAD = 1007
STATUS_POLICY_VIOLATION = 1008
STATUS_MESSAGE_TOO_BIG = 1009
STATUS_INVALID_EXTENSION = 1010
STATUS_UNEXPECTED_CONDITION = 1011
STATUS_TLS_HANDSHAKE_ERROR = 1015

logger = logging.getLogger()

class WebSocketException(Exception):
    """
    websocket exeception class.
    """
    pass

default_timeout = None
traceEnabled = False

def enableTrace(tracable):
    """
    turn on/off the tracability.

    tracable: boolean value. if set True, tracability is enabled.
    """
    global traceEnabled
    traceEnabled = tracable
    if tracable:
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)

def setdefaulttimeout(timeout):
    """
    Set the global timeout setting to connect.

    timeout: default socket timeout time. This value is second.
    """
    global default_timeout
    default_timeout = timeout

def getdefaulttimeout():
    """
    Return the global timeout setting(second) to connect.
    """
    return default_timeout

def _parse_url(url):
    """
    parse url and the result is tuple of 
    (hostname, port, resource path and the flag of secure mode)

    url: url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)
    url = url.rstrip("/")

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port  = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    return (hostname, port, resource, is_secure)

def create_connection(url, timeout=None, **options):
    """
    connect to url and return websocket object.

    Connect to url and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied, the global default timeout setting returned by getdefauttimeout() is used.
    You can customize using 'options'.
    If you set "headers" dict object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.org/",
    ...     headers={"User-Agent": "MyProgram"})

    timeout: socket timeout time. This value is integer.
             if you set None for this value, it means "use default_timeout value"

    options: current support option is only "header".
             if you set header as dict value, the custom HTTP headers are added.
    """
    websock = WebSocket()
    websock.settimeout(timeout != None and timeout or default_timeout)
    websock.connect(url, **options)
    return websock

_MAX_INTEGER = (1 << 32) -1
_AVAILABLE_KEY_CHARS = range(0x21, 0x2f + 1) + range(0x3a, 0x7e + 1)
_MAX_CHAR_BYTE = (1<<8) -1

# ref. Websocket gets an update, and it breaks stuff.
# http://axod.blogspot.com/2010/06/websocket-gets-update-and-it-breaks.html

def _create_sec_websocket_key():
    uid = uuid.uuid4()
    return base64.encodestring(uid.bytes).strip()

_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
    }

class _SSLSocketWrapper(object):
    def __init__(self, sock):
        self.ssl = socket.ssl(sock)

    def recv(self, bufsize):
        return self.ssl.read(bufsize)
    
    def send(self, payload):
        return self.ssl.write(payload)

_BOOL_VALUES = (0, 1)
def _is_bool(*values):
    for v in values:
        if v not in _BOOL_VALUES:
            return False
    
    return True

class ABNF(object):
    """
    ABNF frame class.
    see http://tools.ietf.org/html/rfc5234
    and http://tools.ietf.org/html/rfc6455#section-5.2
    """
    
    # operation code values.
    OPCODE_TEXT   = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE  = 0x8
    OPCODE_PING   = 0x9
    OPCODE_PONG   = 0xa
    
    # available operation code value tuple
    OPCODES = (OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE,
                OPCODE_PING, OPCODE_PONG)

    # opcode human readable string
    OPCODE_MAP = {
        OPCODE_TEXT: "text",
        OPCODE_BINARY: "binary",
        OPCODE_CLOSE: "close",
        OPCODE_PING: "ping",
        OPCODE_PONG: "pong"
        }

    # data length threashold.
    LENGTH_7  = 0x7d
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    def __init__(self, fin = 0, rsv1 = 0, rsv2 = 0, rsv3 = 0,
                 opcode = OPCODE_TEXT, mask = 1, data = ""):
        """
        Constructor for ABNF.
        please check RFC for arguments.
        """
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = mask
        self.data = data
        self.get_mask_key = os.urandom

    @staticmethod
    def create_frame(data, opcode):
        """
        create frame to send text, binary and other data.
        
        data: data to send. This is string value(byte array).
            if opcode is OPCODE_TEXT and this value is uniocde,
            data value is conveted into unicode string, automatically.

        opcode: operation code. please see OPCODE_XXX.
        """
        if opcode == ABNF.OPCODE_TEXT and isinstance(data, unicode):
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(1, 0, 0, 0, opcode, 1, data)

    def format(self):
        """
        format this object to string(byte array) to send data to server.
        """
        if not _is_bool(self.fin, self.rsv1, self.rsv2, self.rsv3):
            raise ValueError("not 0 or 1")
        if self.opcode not in ABNF.OPCODES:
            raise ValueError("Invalid OPCODE")
        length = len(self.data)
        if length >= ABNF.LENGTH_63:
            raise ValueError("data is too long")
        
        frame_header = chr(self.fin << 7
                           | self.rsv1 << 6 | self.rsv2 << 5 | self.rsv3 << 4
                           | self.opcode)
        if length < ABNF.LENGTH_7:
            frame_header += chr(self.mask << 7 | length)
        elif length < ABNF.LENGTH_16:
            frame_header += chr(self.mask << 7 | 0x7e)
            frame_header += struct.pack("!H", length)
        else:
            frame_header += chr(self.mask << 7 | 0x7f)
            frame_header += struct.pack("!Q", length)
        
        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            return frame_header + self._get_masked(mask_key)

    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)
        return mask_key + "".join(s)

    @staticmethod
    def mask(mask_key, data):
        """
        mask or unmask data. Just do xor for each byte

        mask_key: 4 byte string(byte).
        
        data: data to mask/unmask.
        """
        _m = map(ord, mask_key)
        _d = map(ord, data)
        for i in range(len(_d)):
            _d[i] ^= _m[i % 4]
        s = map(chr, _d)
        return "".join(s)

class WebSocket(object):
    """
    Low level WebSocket interface.
    This class is based on
      The WebSocket protocol draft-hixie-thewebsocketprotocol-76
      http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76

    We can connect to the websocket server and send/recieve data.
    The following example is a echo client.

    >>> import websocket
    >>> ws = websocket.WebSocket()
    >>> ws.connect("ws://echo.websocket.org")
    >>> ws.send("Hello, Server")
    >>> ws.recv()
    'Hello, Server'
    >>> ws.close()
    
    get_mask_key: a callable to produce new mask keys, see the set_mask_key 
      function's docstring for more details
    """
    def __init__(self, get_mask_key = None):
        """
        Initalize WebSocket object.
        """
        self.connected = False
        self.io_sock = self.sock = socket.socket()
        self.get_mask_key = get_mask_key
        
    def set_mask_key(self, func):
        """
        set function to create musk key. You can custumize mask key generator.
        Mainly, this is for testing purpose.

        func: callable object. the fuct must 1 argument as integer.
              The argument means length of mask key.
              This func must be return string(byte array),
              which length is argument specified.
        """
        self.get_mask_key = func

    def settimeout(self, timeout):
        """
        Set the timeout to the websocket.
        
        timeout: timeout time(second).
        """
        self.sock.settimeout(timeout)

    def gettimeout(self):
        """
        Get the websocket timeout(second).
        """
        return self.sock.gettimeout()
    
    def connect(self, url, **options):
        """
        Connect to url. url is websocket url scheme. ie. ws://host:port/resource
        You can customize using 'options'.
        If you set "headers" dict object, you can set your own custom header.
        
        >>> ws = WebSocket()
        >>> ws.connect("ws://echo.websocket.org/",
        ...     headers={"User-Agent": "MyProgram"})

        timeout: socket timeout time. This value is integer.
                 if you set None for this value,
                 it means "use default_timeout value"

        options: current support option is only "header".
                 if you set header as dict value,
                 the custom HTTP headers are added.

        """
        hostname, port, resource, is_secure = _parse_url(url)
        # TODO: we need to support proxy
        self.sock.connect((hostname, port))
        if is_secure:
            self.io_sock = _SSLSocketWrapper(self.sock)
        self._handshake(hostname, port, resource, **options)

    def _handshake(self, host, port, resource, **options):
        sock = self.io_sock
        headers = []
        headers.append("GET %s HTTP/1.1" % resource)
        headers.append("Upgrade: websocket")
        headers.append("Connection: Upgrade")
        if port == 80:
            hostport = host
        else:
            hostport = "%s:%d" % (host, port)
        headers.append("Host: %s" % hostport)
        headers.append("Origin: %s" % hostport)
   
        key = _create_sec_websocket_key()
        headers.append("Sec-WebSocket-Key: %s" % key)
        headers.append("Sec-WebSocket-Protocol: chat, superchat")
        headers.append("Sec-WebSocket-Version: %s" % VERSION)
        if "header" in options:
            headers.extend(options["header"])

        headers.append("")
        headers.append("")

        header_str = "\r\n".join(headers)
        sock.send(header_str)
        if traceEnabled:
            logger.debug( "--- request header ---")
            logger.debug( header_str)
            logger.debug("-----------------------")

        status, resp_headers = self._read_headers()
        if status != 101:
            self.close()
            raise WebSocketException("Handshake Status %d" % status)

        success = self._validate_header(resp_headers, key)
        if not success:
            self.close()
            raise WebSocketException("Invalid WebSocket Header")

        self.connected = True
    
    def _validate_header(self, headers, key):
        for k, v in _HEADERS_TO_CHECK.iteritems():
            r = headers.get(k, None)
            if not r:
                return False
            r = r.lower()
            if v != r:
                return False

        result = headers.get("sec-websocket-accept", None)
        if not result:
            return False
        result = result.lower()
        
        value = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hashed = base64.encodestring(sha.sha(value).digest()).strip().lower()
        return hashed == result

    def _read_headers(self):
        status = None
        headers = {}
        if traceEnabled:
            logger.debug("--- response header ---")
            
        while True:
            line = self._recv_line()
            if line == "\r\n":
                break
            line = line.strip()
            if traceEnabled:
                logger.debug(line)
            if not status:
                status_info = line.split(" ", 2)
                status = int(status_info[1])
            else:
                kv = line.split(":", 1)
                if len(kv) == 2:
                    key, value = kv
                    headers[key.lower()] = value.strip().lower()
                else:
                    raise WebSocketException("Invalid header")

        if traceEnabled:
            logger.debug("-----------------------")
        
        return status, headers    
    
    def send(self, payload, opcode = ABNF.OPCODE_TEXT):
        """
        Send the data as string. 

        payload: Payload must be utf-8 string or unicoce,
                  if the opcode is OPCODE_TEXT.
                  Otherwise, it must be string(byte array)

        opcode: operation code to send. Please see OPCODE_XXX.
        """
        frame = ABNF.create_frame(payload, opcode)
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        self.io_sock.send(data)
        if traceEnabled:
            logger.debug("send: " + repr(data))

    def ping(self, payload = ""):
        """
        send ping data.
        
        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload):
        """
        send pong data.
        
        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self):
        """
        Receive string data(byte array) from the server.

        return value: string(byte array) value.
        """
        opcode, data = self.recv_data()
        return data

    def recv_data(self):
        """
        Recieve data with operation code.
        
        return  value: tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if not frame:
                # handle error: 
                # 'NoneType' object has no attribute 'opcode'
                raise WebSocketException("Not a valid frame %s" % frame)
            elif frame.opcode in (ABNF.OPCODE_TEXT, ABNF.OPCODE_BINARY):
                return (frame.opcode, frame.data)
            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return (frame.opcode, None)
            elif frame.opcode == ABNF.OPCODE_PING:
                self.pong("Hi!")


    def recv_frame(self):
        """
        recieve data as frame from server.

        return value: ABNF frame object.
        """
        header_bytes = self._recv(2)
        if not header_bytes:
            return None
        b1 = ord(header_bytes[0])
        fin = b1 >> 7 & 1
        rsv1 = b1 >> 6 & 1
        rsv2 = b1 >> 5 & 1
        rsv3 = b1 >> 4 & 1
        opcode = b1 & 0xf
        b2 = ord(header_bytes[1])
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

        length_data = ""
        if length == 0x7e:
            length_data = self._recv(2)
            length = struct.unpack("!H", length_data)[0]
        elif length == 0x7f:
            length_data = self._recv(8)
            length = struct.unpack("!Q", length_data)[0]

        mask_key = ""
        if mask:
            mask_key = self._recv(4)
        data = self._recv_strict(length)
        if traceEnabled:
            recieved = header_bytes + length_data + mask_key + data
            logger.debug("recv: " + repr(recieved))

        if mask:
            data = ABNF.mask(mask_key, data)
        
        frame = ABNF(fin, rsv1, rsv2, rsv3, opcode, mask, data)
        return frame

    def send_close(self, status = STATUS_NORMAL, reason = ""):
        """
        send close data to the server.
        
        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)
        


    def close(self, status = STATUS_NORMAL, reason = ""):
        """
        Close Websocket object

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if self.connected:
            if status < 0 or status >= ABNF.LENGTH_16:
                raise ValueError("code is invalid range")

            try:
                self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)
                timeout = self.sock.gettimeout()
                self.sock.settimeout(3)
                try:
                    frame = self.recv_frame()
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.error("close status: " + repr(frame.data))
                except:
                    pass
                self.sock.settimeout(timeout)
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
        self._closeInternal()

    def _closeInternal(self):
        self.connected = False
        self.sock.close()
        self.io_sock = self.sock
        
    def _recv(self, bufsize):
        bytes = self.io_sock.recv(bufsize)
        return bytes

    def _recv_strict(self, bufsize):
        remaining = bufsize
        bytes = ""
        while remaining:
            bytes += self._recv(remaining)
            remaining = bufsize - len(bytes)
            
        return bytes

    def _recv_line(self):
        line = []
        while True:
            c = self._recv(1)
            line.append(c)
            if c == "\n":
                break
        return "".join(line)
            
class WebSocketApp(object):
    """
    Higher level of APIs are provided. 
    The interface is like JavaScript WebSocket object.
    """
    def __init__(self, url,
                 on_open = None, on_message = None, on_error = None, 
                 on_close = None, keep_running = True, get_mask_key = None):
        """
        url: websocket url.
        on_open: callable object which is called at opening websocket.
          this function has one argument. The arugment is this class object.
        on_message: callbale object which is called when recieved data.
         on_message has 2 arguments. 
         The 1st arugment is this class object.
         The passing 2nd arugment is utf-8 string which we get from the server.
       on_error: callable object which is called when we get error.
         on_error has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is exception object.
       on_close: callable object which is called when closed the connection.
         this function has one argument. The arugment is this class object.
       keep_running: a boolean flag indicating whether the app's main loop should
         keep running, defaults to True
       get_mask_key: a callable to produce new mask keys, see the WebSocket.set_mask_key's
         docstring for more information
        """
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.keep_running = keep_running
        self.get_mask_key = get_mask_key
        self.sock = None

    def send(self, data):
        """
        send message. data must be utf-8 string or unicode.
        """
        self.sock.send(data)

    def close(self):
        """
        close websocket connection.
        """
        self.keep_running = False
        self.sock.close()

    def run_forever(self):
        """
        run event loop for WebSocket framework.
        This loop is infinite loop and is alive during websocket is available.
        """
        if self.sock:
            raise WebSocketException("socket is already opened")
        try:
            self.sock = WebSocket(self.get_mask_key)
            self.sock.connect(self.url)
            self._run_with_no_err(self.on_open)
            while self.keep_running:
                data = self.sock.recv()
                if data is None:
                    break
                self._run_with_no_err(self.on_message, data)
        except Exception, e:
            self._run_with_no_err(self.on_error, e)
        finally:
            self.sock.close()
            self._run_with_no_err(self.on_close)
            self.sock = None

    def _run_with_no_err(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception, e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.error(e)


if __name__ == "__main__":
    enableTrace(True)
    ws = create_connection("ws://echo.websocket.org/")
    print "Sending 'Hello, World'..."
    ws.send("Hello, World")
    print "Sent"
    print "Receiving..."
    result =  ws.recv()
    print "Received '%s'" % result
    ws.close()

########NEW FILE########
__FILENAME__ = Console
from utils import Command, Notification, WIPObject
from Runtime import RemoteObject
from Network import RequestId


### Console.clearMessages
def clearMessages():
    command = Command('Console.clearMessages')
    return command


### Console.disable
def disable():
    command = Command('Console.disable')
    return command


### Console.enable
def enable():
    command = Command('Console.enable')
    return command


### Console.messageAdded
def messageAdded():
    notification = Notification('Console.messageAdded')
    return notification


def messageAdded_parser(params):
    result = ConsoleMessage(params['message'])
    return result


### Console.messageRepeatCountUpdated
def messageRepeatCountUpdated():
    notification = Notification('Console.messageRepeatCountUpdated')
    return notification


def messageRepeatCountUpdate_parser(params):
    return params['count']


### Console.messagesCleared
def messagesCleared():
    notification = Notification('Console.messagesCleared')
    return notification


class CallFrame(WIPObject):
    def __init__(self, value):
        self.set(value, 'columnNumber')
        self.set(value, 'functionName')
        self.set(value, 'lineNumber')
        self.set(value, 'url')


class ConsoleMessage(WIPObject):
    def __init__(self, value):
        self.set(value, 'level')
        self.set(value, 'line')
        self.set_class(value, 'networkRequestId', RequestId)
        self.parameters = []
        if 'parameters' in value:
            for param in value['parameters']:
                self.parameters.append(RemoteObject(param))
        self.set(value, 'repeatCount', 1)
        self.set_class(value, 'stackTrace', StackTrace)
        self.set(value, 'text')
        self.set(value, 'url')


class StackTrace(list):
    def __init__(self, value):
        for callFrame in value:
            self.append(CallFrame(callFrame))

########NEW FILE########
__FILENAME__ = Debugger
from utils import Command, Notification, WIPObject
from Runtime import RemoteObject
import json


### Console.clearMessages
def canSetScriptSource():
    command = Command('Debugger.canSetScriptSource', {})
    return command


def enable():
    command = Command('Debugger.enable', {})
    return command


def evaluateOnCallFrame(callFrameId, expression):
    params = {}
    params['callFrameId'] = callFrameId()
    params['expression'] = expression
    command = Command('Debugger.evaluateOnCallFrame', params)
    return command


def evaluateOnCallFrame_parser(result):
    data = RemoteObject(result['result'])
    return data


def disable():
    command = Command('Debugger.disable', {})
    return command


def resume():
    command = Command('Debugger.resume', {})
    return command


def stepInto():
    command = Command('Debugger.stepInto', {})
    return command


def stepOut():
    command = Command('Debugger.stepOut', {})
    return command


def stepOver():
    command = Command('Debugger.stepOver', {})
    return command


def removeBreakpoint(breakpointId):
    params = {}
    params['breakpointId'] = breakpointId
    command = Command('Debugger.removeBreakpoint', params)
    return command


def setBreakpoint(location, condition=None):
    params = {}
    params['location'] = location()

    if condition:
        params['condition'] = condition

    command = Command('Debugger.setBreakpoint', params)
    return command


def setBreakpoint_parser(result):
    data = {}
    data['breakpointId'] = BreakpointId(result['breakpointId'])
    data['actualLocation'] = Location(result['actualLocation'])
    return data


def setScriptSource(scriptId, scriptSource):
    params = {}
    params['scriptId'] = scriptId
    params['scriptSource'] = scriptSource

    command = Command('Debugger.setScriptSource', params)
    return command


def setScriptSource_parser(result):
    data = {}
    data['callFrames'] = []
    for callFrame in result['callFrames']:
        data['callFrames'].append(CallFrame(callFrame))
    return data


def setBreakpointByUrl(lineNumber, url=None, urlRegex=None, columnNumber=None, condition=None):
    params = {}
    params['lineNumber'] = lineNumber
    if url:
        params['url'] = url

    if urlRegex:
        params['urlRegex'] = urlRegex

    if columnNumber:
        params['columnNumber'] = columnNumber

    if condition:
        params['condition'] = condition

    command = Command('Debugger.setBreakpointByUrl', params)
    return command


def setBreakpointByUrl_parser(result):
    data = {}
    data['breakpointId'] = BreakpointId(result['breakpointId'])
    data['locations'] = []
    for location in result['locations']:
        data['locations'].append(Location(location))
    return data


def scriptParsed():
    notification = Notification('Debugger.scriptParsed')
    return notification


def scriptParsed_parser(params):
    return {'scriptId': ScriptId(params['scriptId']), 'url': params['url']}


def paused():
    notification = Notification('Debugger.paused')
    return notification


def paused_parser(params):
    data = {}
    data['callFrames'] = []
    for callFrame in params['callFrames']:
        data['callFrames'].append(CallFrame(callFrame))
    data['reason'] = params['reason']
    return data


def resumed():
    notification = Notification('Debugger.resumed')
    return notification


class BreakpointId(WIPObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __call__(self):
        return self.value


class CallFrameId(WIPObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __call__(self):
        return self.value


class ScriptId(WIPObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __call__(self):
        return self.value


class Scope(WIPObject):
    def __init__(self, value):
        self.set_class(value, 'object', RemoteObject)
        self.set(value, 'type')


class Location(WIPObject):
    def __init__(self, value):
        self.set(value, 'columnNumber')
        self.set(value, 'lineNumber')
        self.set_class(value, 'scriptId', ScriptId)

    def __call__(self):
        obj = {}
        if self.columnNumber:
            obj['columnNumber'] = self.columnNumber
        obj['lineNumber'] = self.lineNumber
        obj['scriptId'] = self.scriptId()
        return obj


class CallFrame(WIPObject):
    def __init__(self, value):
        self.set_class(value, 'callFrameId', CallFrameId)
        self.set(value, 'functionName')
        self.set_class(value, 'location', Location)
        self.scopeChain = []
        if 'scopeChain' in value:
            for scope in value['scopeChain']:
                self.scopeChain.append(Scope(scope))
        self.set_class(value, 'this', RemoteObject)

    def __str__(self):
        return "%s:%d %s" % (self.location.scriptId, self.location.lineNumber, self.functionName)

########NEW FILE########
__FILENAME__ = DOM
# not implemented now

########NEW FILE########
__FILENAME__ = DOMDebugger
# not implemented now

########NEW FILE########
__FILENAME__ = Network
from utils import WIPObject, Command


def clearBrowserCache():
    command = Command('Network.clearBrowserCache', {})
    return command


def canClearBrowserCache():
    command = Command('Network.canClearBrowserCache', {})
    return command


def setCacheDisabled(value):
    command = Command('Network.setCacheDisabled', {'cacheDisabled': value})
    return command


class RequestId(WIPObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

########NEW FILE########
__FILENAME__ = Page
from utils import Command


def reload():
    command = Command('Page.reload', {})
    return command

########NEW FILE########
__FILENAME__ = Runtime
import json
from utils import WIPObject, Command


def evaluate(expression, objectGroup=None, returnByValue=None):
    params = {}

    params['expression'] = expression

    if(objectGroup):
        params['objectGroup'] = objectGroup

    if(returnByValue):
        params['returnByValue'] = returnByValue

    command = Command('Runtime.evaluate', params)
    return command


def getProperties(objectId, ownProperties=False):
    params = {}

    params['objectId'] = str(objectId)
    params['ownProperties'] = ownProperties

    command = Command('Runtime.getProperties', params)
    return command


def getProperties_parser(result):
    data = []
    for propertyDescriptor in result['result']:
        data.append(PropertyDescriptor(propertyDescriptor))
    return data


class RemoteObject(WIPObject):
    def __init__(self, value):
        self.set(value, 'className')
        self.set(value, 'description')
        self.set_class(value, 'objectId', RemoteObjectId)
        self.set(value, 'subtype')
        self.set(value, 'type')
        self.set(value, 'value')

    def __str__(self):
        if self.type == 'boolean':
            return str(self.value)
        if self.type == 'string':
            return str(self.value)
        if self.type == 'undefined':
            return 'undefined'
        if self.type == 'number':
            return str(self.value)
        if self.type == 'object':
            if not self.objectId():
                return 'null'
            else:
                if self.className:
                    return self.className
                if self.description:
                    return self.description
                return '{ ... }'
        if self.type == 'function':
            return self.description.split('\n')[0]


class PropertyDescriptor(WIPObject):
    def __init__(self, _value):
        self.set(_value, 'configurable')
        self.set(_value, 'enumerable')
        #self.set_class(_value, 'get', RemoteObject)
        #self.set_class(_value, 'set', RemoteObject)
        self.set(_value, 'name')
        self.set_class(_value, 'value', RemoteObject)
        self.set(_value, 'wasThrown')
        self.set(_value, 'writable')

    def __str__(self):
        return self.name


class RemoteObjectId(WIPObject):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __call__(self):
        return self.value

    def dumps(self):
        objid = json.loads(self.value)
        return "Object_%d_%d" % (objid['injectedScriptId'], objid['id'])

    def loads(self, text):
        parts = text.split('_')
        self.value = '{"injectedScriptId":%s,"id":%s}' % (parts[1], parts[2])
        return self.value

########NEW FILE########
__FILENAME__ = utils
class WIPObject(object):
    def set(self, obj, name, default=None):
        setattr(self, name, obj.get(name, default))

    def set_class(self, obj, name, classObject):
        if name in obj:
            setattr(self, name, classObject(obj[name]))
        else:
            setattr(self, name, None)

    def parse_to_class(self, obj, name, classObject):
        if name in obj:
            setattr(self, name, classObject.parse(obj[name]))
        else:
            setattr(self, name, None)


class Notification(object):
    def __init__(self, notification_name):
        self.name = notification_name
        try:
            self.parser = eval('wip.' + notification_name + '_parser', {'wip': __import__('wip')})
        except:
            self.parser = Notification.default_parser
        self.lastResponse = None
        self.callback = None

    @staticmethod
    def default_parser(params):
        print params
        return params


class Command(object):
    def __init__(self, method_name, params={}):
        self.request = {'id': 0, 'method': '', 'params': params}
        self.method = method_name
        try:
            self.parser = eval('wip.' + method_name + '_parser', {'wip': __import__('wip')})
        except:
            self.parser = Command.default_parser
        self.params = params
        self.options = None
        self.callback = None
        self.response = None
        self.error = None
        self.data = None

    def get_id(self):
        return self.request['id']

    def set_id(self, value):
        self.request['id'] = value

    def get_method(self):
        return self.request['method']

    def set_method(self, value):
        self.request['method'] = value

    id = property(get_id, set_id)
    method = property(get_method, set_method)

    @staticmethod
    def default_parser(params):
        return params

########NEW FILE########
