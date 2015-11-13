__FILENAME__ = help_it
'''
    Integrated from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2674
    Plugin inspired and modified from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2242

    keys;
        { "keys": ["alt+f1"], "command": "help_it" }
'''
import sublime
import sublime_plugin
import webbrowser
import re


class helpItCommand(sublime_plugin.TextCommand):

    """
    This will search a word in a language's documenation or google it with it's scope otherwise
    """

    def run(self, edit):
        if len(self.view.file_name()) > 0:
            settings = sublime.load_settings('orgmode.sublime-settings')
            item = None
            word = self.view.substr(self.view.word(self.view.sel()[0].begin()))
            scope = self.view.scope_name(self.view.sel()[0].begin()).strip()
            getlang = scope.split('.')
            language = getlang[-1]
            if language == 'basic':
                language = getlang[-2]

            if language == 'html':  # HTML shows up A LOT for internal CSS, PHP and JS
                if 'php' in getlang:
                    language = 'php'
                elif 'js' in getlang:
                    language = 'js'
                elif 'css' in getlang:
                    language = 'css'

            # Map languages if needed. For example: Map .less files to .css
            # searches
            print('language: ' + language)
            if settings.get(language) is not None:
                print('lang found in settings: ' + language)
                item = settings.get(language)
                if 'map' in item:
                    language = item['map']

            sublime.status_message(
                'helpIt invoked-- ' + 'Scope: ' + scope + ' Word: ' + word + ' Language: ' + language)
            for region in self.view.sel():
                phrase = self.view.substr(region)
                search = 'http://google.com/search?q=%s'
                custom = False

                # Define our search term
                if not region.empty():
                    term = phrase
                else:
                    term = word

                if item != None:
                    if 'sub' in item:  # check for sub searches based on our term
                        subs = item['sub']
                        for sub in subs:
                            if 'contains' in sub and 'url' in sub:  # Make sure we have everything
                                if term.count(sub['contains']):
                                    if 'remove' in sub:
                                        term = re.sub(sub['remove'], '', term)
                                    search = sub['url']
                                    custom = True
                                    break

                    if not custom:
                        if isinstance(item, str):
                            search = item
                            custom = True
                        elif 'url' in item:
                            search = item['url']
                            custom = True

                if not custom:
                    term += " " + language

                try:
                    search = search % (term)
                    print(search)
                except TypeError:
                    print("No replacements")

                webbrowser.open_new_tab(search)
        else:
            pass

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0

########NEW FILE########
__FILENAME__ = navigation_history

'''
http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2738

https://github.com/optilude/SublimeTextMisc


Put this in your "Packages" directory and then configure "Key bindings - User" to use it. I use these keybindings for it on OS X:

  { "keys": ["alt+left"], "command": "navigation_history_back"},
  { "keys": ["alt+right"], "command": "navigation_history_forward"}

'''


import sublime
import sublime_plugin
from collections import deque

MAX_SIZE = 64
LINE_THRESHOLD = 2


class Location(object):

    """A location in the history
    """
    def __init__(self, path, line, col):
        self.path = path
        self.line = line
        self.col = col

    def __eq__(self, other):
        return self.path == other.path and self.line == other.line

    def __ne__(self, other):
        return not self.__eq__(other)

    def __bool__(self):
        return (self.path is not None and self.line is not None)

    def near(self, other):
        return self.path == other.path and abs(self.line - other.line) <= LINE_THRESHOLD

    def copy(self):
        return Location(self.path, self.line, self.col)


class History(object):

    """Keep track of the history for a single window
    """

    def __init__(self, max_size=MAX_SIZE):
        self._current = None                # current location as far as the
                                            # history is concerned
        self._back = deque([], max_size)    # items before self._current
        self._forward = deque([], max_size)  # items after self._current

        self._last_movement = None          # last recorded movement

    def record_movement(self, location):
        """Record movement to the given location, pushing history if
        applicable
        """

        if location:
            if self.has_changed(location):
                self.push(location)
            self.mark_location(location)

    def mark_location(self, location):
        """Remember the current location, for the purposes of being able
        to do a has_changed() check.
        """
        self._last_movement = location.copy()

    def has_changed(self, location):
        """Determine if the given location combination represents a
        significant enough change to warrant pushing history.
        """

        return self._last_movement is None or not self._last_movement.near(location)

    def push(self, location):
        """Push the given location to the back history. Clear the forward
        history.
        """

        if self._current is not None:
            self._back.append(self._current.copy())
        self._current = location.copy()
        self._forward.clear()

    def back(self):
        """Move backward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._back:
            return None

        self._forward.appendleft(self._current)
        self._current = self._back.pop()
        self._last_movement = self._current  # preempt, so we don't re-push
        return self._current

    def forward(self):
        """Move forward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._forward:
            return None

        self._back.append(self._current)
        self._current = self._forward.popleft()
        self._last_movement = self._current  # preempt, so we don't re-push
        return self._current

_histories = {}  # window id -> History


def get_history():
    """Get a History object for the current window,
    creating a new one if required
    """

    window = sublime.active_window()
    if window is None:
        return None

    window_id = window.id()
    history = _histories.get(window_id, None)
    if history is None:
        _histories[window_id] = history = History()
    return history


class NavigationHistoryRecorder(sublime_plugin.EventListener):

    """Keep track of history
    """

    def on_selection_modified(self, view):
        """When the selection is changed, possibly record movement in the
        history
        """
        history = get_history()
        if history is None:
            return

        path = view.file_name()
        row, col = view.rowcol(view.sel()[0].a)
        history.record_movement(Location(path, row + 1, col + 1))

    # def on_close(self, view):
    #     """When a view is closed, check to see if the window was closed too
    #     and clean up orphan histories
    #     """
    #
    # XXX: This doesn't work - event runs before window is removed
    # from sublime.windows()
    #
    #     windows_with_history = set(_histories.keys())
    #     window_ids = set([w.id() for w in sublime.windows()])
    #     closed_windows = windows_with_history.difference(window_ids)
    #     for window_id in closed_windows:
    #         del _histories[window_id]


class NavigationHistoryBack(sublime_plugin.TextCommand):

    """Go back in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.back()
        if location:
            window = sublime.active_window()
            window.open_file("%s:%d:%d" % (
                location.path, location.line, location.col), sublime.ENCODED_POSITION)


class NavigationHistoryForward(sublime_plugin.TextCommand):

    """Go forward in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.forward()
        if location:
            window = sublime.active_window()
            window.open_file("%s:%d:%d" % (
                location.path, location.line, location.col), sublime.ENCODED_POSITION)

########NEW FILE########
__FILENAME__ = orgmode
'''
Settings in orgmode.sublime-settings are:
- orgmode.open_link.resolvers: See DEFAULT_OPEN_LINK_RESOLVERS.
- orgmode.open_link.resolver.abstract.commands: See DEFAULT_OPEN_LINK_COMMANDS in resolver.abstract.
For more settings see headers of specific resolvers.
'''

import sys
import re
import os.path
import sublime
import sublime_plugin
import fnmatch
import datetime


try:
    import importlib
except ImportError:
    pass


DEFAULT_OPEN_LINK_RESOLVERS = [
    'http',
    'https',
    'prompt',
    'redmine',
    'jira',
    'crucible',
    'fisheye',
    'email',
    'local_file',
]


class OrgmodeNewTaskDocCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.new_file()
        view.set_syntax_file('Packages/orgmode/orgmode.tmLanguage')


def find_resolvers():
    base = os.path.dirname(os.path.abspath(__file__))
    path = base + '/resolver'
    available_resolvers = {}
    for root, dirnames, filenames in os.walk(base + '/resolver'):
        for filename in fnmatch.filter(filenames, '*.py'):
            module_path = 'orgmode.resolver.' + filename.split('.')[0]
            if sys.version_info[0] < 3:
                module_path = 'resolver.' + filename.split('.')[0]
                name = filename.split('.')[0]
                module = __import__(module_path, globals(), locals(), name)
                module = reload(module)
            else:
                module = importlib.import_module(module_path)
            if '__init__' in filename or 'abstract' in filename:
                continue
            available_resolvers[filename.split('.')[0]] = module
    return available_resolvers
available_resolvers = find_resolvers()


class OrgmodeOpenLinkCommand(sublime_plugin.TextCommand):

    def __init__(self, *args, **kwargs):
        super(OrgmodeOpenLinkCommand, self).__init__(*args, **kwargs)
        settings = sublime.load_settings('orgmode.sublime-settings')
        wanted_resolvers = settings.get(
            'orgmode.open_link.resolvers', DEFAULT_OPEN_LINK_RESOLVERS)
        self.resolvers = [available_resolvers[name].Resolver(self.view)
                          for name in wanted_resolvers]

    def resolve(self, content):
        for resolver in self.resolvers:
            result = resolver.resolve(content)
            if result is not None:
                return resolver, result
        return None, None

    def is_valid_scope(self, sel):
        scope_name = self.view.scope_name(sel.end())
        return 'orgmode.link' in scope_name

    def extract_content(self, region):
        content = self.view.substr(region)
        if content.startswith('[[') and content.endswith(']]'):
            content = content[2:-2]
        return content

    def run(self, edit):
        view = self.view
        for sel in view.sel():
            if not self.is_valid_scope(sel):
                continue
            region = view.extract_scope(sel.end())
            content = self.extract_content(region)
            resolver, content = self.resolve(content)
            if content is None:
                sublime.error_message('Could not resolve link:\n%s' % content)
                continue
            resolver.execute(content)


class OrgmodeOpenPythonRefCommand(OrgmodeOpenLinkCommand):

    def __init__(self, *args, **kwargs):
        super(OrgmodeOpenPythonRefCommand, self).__init__(*args, **kwargs)
        pattern = r'.+", line (?P<line>\d+), in (?P<symbol>.+)$'
        self.regex = re.compile(pattern)

    def is_valid_scope(self, sel):
        scope_name = self.view.scope_name(sel.end())
        return 'filepath reference orgmode.python.traceback' in scope_name

    def extract_content(self, region):
        content = self.view.substr(region)
        outer_region = self.view.extract_scope(region.end() + 1)
        scope_name = self.view.scope_name(region.end() + 1)
        # print scope_name
        if 'reference orgmode.python.traceback' in scope_name:
            outer_content = self.view.substr(outer_region)
            # print outer_content
            match = self.regex.match(outer_content)
            if match:
                # print match.groupdict()
                content += ':%s' % match.group('line')
        return content


class OrgmodeCycleInternalLinkCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        sels = view.sel()
        sel = sels[0]
        if 'orgmode.link.internal' not in view.scope_name(sel.end()):
            return
        region = view.extract_scope(sel.end())
        content = view.substr(region).strip()
        if content.startswith('{{') and content.endswith('}}'):
            content = '* %s' % content[2:-2]
        found = self.view.find(content, region.end(), sublime.LITERAL)
        if not found:  # Try wrapping around buffer.
            found = self.view.find(content, 0, sublime.LITERAL)
        same = region.a == found.a and region.b == found.b
        if not found or same:
            sublime.status_message('No sibling found for: %s' % content)
            return
        found = view.extract_scope(found.begin())
        sels.clear()
        sels.add(sublime.Region(found.begin()))
        try:
            import show_at_center_and_blink
            view.run_command('show_at_center_and_blink')
        except ImportError:
            view.show_at_center(found)


class AbstractCheckboxCommand(sublime_plugin.TextCommand):

    def __init__(self, *args, **kwargs):
        super(AbstractCheckboxCommand, self).__init__(*args, **kwargs)
        indent_pattern = r'^(\s*).*$'
        summary_pattern = r'(\[\d*[/]\d*\])'
        checkbox_pattern = r'(\[[X ]\])'
        self.indent_regex = re.compile(indent_pattern)
        self.summary_regex = re.compile(summary_pattern)
        self.checkbox_regex = re.compile(checkbox_pattern)

    def get_indent(self, content):
        if isinstance(content, sublime.Region):
            content = self.view.substr(content)
        match = self.indent_regex.match(content)
        indent = match.group(1)
        return indent

    def find_parent(self, region):
        view = self.view
        row, col = view.rowcol(region.begin())
        line = view.line(region)
        content = view.substr(line)
        # print content
        indent = len(self.get_indent(content))
        # print repr(indent)
        row -= 1
        found = False
        while row >= 0:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            if len(content.strip()):
                cur_indent = len(self.get_indent(content))
                if cur_indent < indent:
                    found = True
                    break
            row -= 1
        if found:
            # print row
            point = view.text_point(row, 0)
            line = view.line(point)
            return line

    def find_children(self, region):
        view = self.view
        row, col = view.rowcol(region.begin())
        line = view.line(region)
        content = view.substr(line)
        # print content
        indent = len(self.get_indent(content))
        # print repr(indent)
        row += 1
        child_indent = None
        children = []
        last_row, _ = view.rowcol(view.size())
        while row <= last_row:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            summary = self.get_summary(line)
            if summary and content.lstrip().startswith("*"):
                 break
            if self.checkbox_regex.search(content):
                cur_indent = len(self.get_indent(content))
                # check for end of descendants
                if cur_indent <= indent:
                    break
                # only immediate children
                if child_indent is None:
                    child_indent = cur_indent
                if cur_indent == child_indent:
                    children.append(line)
            row += 1
        return children

    def find_siblings(self, child, parent):
        view = self.view
        row, col = view.rowcol(parent.begin())
        parent_indent = self.get_indent(parent)
        child_indent = self.get_indent(child)
        # print '***', repr(parent_indent), repr(child_indent)
        siblings = []
        row += 1
        last_row, _ = view.rowcol(view.size())
        while row <= last_row:  # Don't go past end of document.
            line = view.text_point(row, 0)
            line = view.line(line)
            content = view.substr(line)
            # print content
            if len(content.strip()):
                cur_indent = self.get_indent(content)
                if len(cur_indent) <= len(parent_indent):
                    # print 'OUT'
                    break  # Indent same as parent found!
                if len(cur_indent) == len(child_indent):
                    # print 'MATCH'
                    siblings.append((line, content))
            row += 1
        return siblings

    def get_summary(self, line):
        view = self.view
        row, _ = view.rowcol(line.begin())
        content = view.substr(line)
        # print content
        match = self.summary_regex.search(content)
        if not match:
            return None
        # summary = match.group(1)
        # print(repr(summary))
        # print dir(match), match.start(), match.span()
        col_start, col_stop = match.span()
        return sublime.Region(
            view.text_point(row, col_start),
            view.text_point(row, col_stop),
        )

    def get_checkbox(self, line):
        view = self.view
        row, _ = view.rowcol(line.begin())
        content = view.substr(line)
        # print content
        match = self.checkbox_regex.search(content)
        if not match:
            return None
        # checkbox = match.group(1)
        # print repr(checkbox)
        # print dir(match), match.start(), match.span()
        col_start, col_stop = match.span()
        return sublime.Region(
            view.text_point(row, col_start),
            view.text_point(row, col_stop),
        )

    def is_checked(self, line):
        return '[X]' in self.view.substr(line)

    def recalc_summary(self, region):
        # print('recalc_summary')
        children = self.find_children(region)
        if not len(children) > 0:
            return (0, 0)
        # print children
        num_children = len(children)
        checked_children = len(
            [child for child in children if self.is_checked(child)])
        # print ('checked_children: ' + str(checked_children) + ', num_children: ' + str(num_children))
        return (num_children, checked_children)

    def update_line(self, edit, region, parent_update=True):
        print ('update_line', self.view.rowcol(region.begin())[0]+1)
        (num_children, checked_children) = self.recalc_summary(region)
        if not num_children > 0:
            return False
        # update region checkbox
        if checked_children == num_children:
            self.toggle_checkbox(edit, region, True)
        else:
            self.toggle_checkbox(edit, region, False)
        # update region summary
        self.update_summary(edit, region, checked_children, num_children)

        children = self.find_children(region)
        for child in children:
            line = self.view.line(child)
            summary = self.get_summary(self.view.line(child))
            if summary:
                return self.update_line(edit, line, parent_update=False)

        if parent_update:
            parent = self.find_parent(region)
            if parent:
                self.update_line(edit, parent)

        return True

    def update_summary(self, edit, region, checked_children, num_children):
        # print('update_summary', self.view.rowcol(region.begin())[0]+1)
        view = self.view
        summary = self.get_summary(region)
        if not summary:
            return False
        # print('checked_children: ' + str(checked_children) + ', num_children: ' + str(num_children))
        view.replace(edit, summary, '[%d/%d]' % (
            checked_children, num_children))

    def toggle_checkbox(self, edit, region, checked=None, recurse_up=False, recurse_down=False):
        # print 'toggle_checkbox', self.view.rowcol(region.begin())[0]+1
        view = self.view
        checkbox = self.get_checkbox(region)
        if not checkbox:
            return False
        # if checked is not specified, toggle checkbox
        if checked is None:
            checked = not self.is_checked(checkbox)
        view.replace(edit, checkbox, '[%s]' % (
            'X' if checked else ' '))
        if recurse_down:
            # all children should follow
            children = self.find_children(region)
            for child in children:
                self.toggle_checkbox(edit, child, checked, recurse_down=True)
        if recurse_up:
            # update parent
            parent = self.find_parent(region)
            if parent:
                self.update_line(edit, parent)


class OrgmodeToggleCheckboxCommand(AbstractCheckboxCommand):

    def run(self, edit):
        view = self.view
        backup = []
        for sel in view.sel():
            if 'orgmode.checkbox' not in view.scope_name(sel.end()):
                continue
            backup.append(sel)
            checkbox = view.extract_scope(sel.end())
            line = view.line(checkbox)
            self.toggle_checkbox(edit, line, recurse_up=True, recurse_down=True)
        view.sel().clear()
        for region in backup:
            view.sel().add(region)


class OrgmodeRecalcCheckboxSummaryCommand(AbstractCheckboxCommand):

    def run(self, edit):
        view = self.view
        backup = []
        for sel in view.sel():
            if 'orgmode.checkbox.summary' not in view.scope_name(sel.end()):
                continue
            backup.append(sel)
            summary = view.extract_scope(sel.end())
            line = view.line(summary)
            self.update_line(edit, line)
        view.sel().clear()
        for region in backup:
            view.sel().add(region)


class OrgmodeLinkCompletions(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        import os
        from glob import glob
        # print 'view =', view
        # print 'preifx =', prefix
        # print 'locations =', locations
        location = locations[0]
        if not 'orgmode.link' in view.scope_name(location):
            return []
        region = view.extract_scope(location)
        content = view.substr(region)
        inner_region = region
        if content.startswith('[[') and content.endswith(']]'):
            content = content[2:-2]
            inner_region = sublime.Region(region.begin() + 2, region.end() - 2)
        if not inner_region.contains(location):
            return []
        content = view.substr(sublime.Region(inner_region.begin(), location))
        content = os.path.expandvars(content)
        content = os.path.expanduser(content)
        # print 'region =', region
        # print 'content =', content
        path, base = os.path.split(content)
        # print 'split =', path, base
        if not len(path):
            path = os.path.dirname(view.file_name())
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(view.file_name()), path)
        # print 'path =', path, base
        pattern = os.path.join(path, '%s*' % base)
        # print 'pattern =', pattern
        files = glob(pattern)
        basename = os.path.basename
        isdir = os.path.isdir
        for pos, item in enumerate(files[:]):
            expr = basename(item)
            snippet = basename(item)
            if isdir(item):
                expr += '/'
                snippet += '/'
            files[pos] = (expr, snippet)
        # print 'files =', files
        if not files:
            return [(base + '/', base)]
        return files


class OrgmodeDateCompleter(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        self.settings = sublime.load_settings('orgmode.sublime-settings')
        self.date_format = self.settings.get(
            'orgmode.autocomplete.date', "%Y-%m-%d %H:%M")
        self.date_format_cmd = self.settings.get(
            'orgmode.autocomplete.date.cmd', "date")

        return [
            (self.date_format_cmd, datetime.datetime.now().strftime(
                self.date_format)),
            ("week", str(datetime.datetime.now().isocalendar()[1])),
        ]

########NEW FILE########
__FILENAME__ = orgmode_store
from gzip import GzipFile
from os import makedirs
from os.path import dirname
from pickle import load, dump
import sublime
import sublime_plugin


class OrgmodeStore(sublime_plugin.EventListener):

    def __init__(self, *args, **kwargs):
        self.debug = False
        self.db = {}
        self.store = dirname(
            sublime.packages_path()) + '/Settings/orgmode-store.bin.gz'
        try:
            makedirs(dirname(self.store))
        except:
            pass
        try:
            with GzipFile(self.store, 'rb') as f:
                self.db = load(f)
        except:
            self.db = {}

        self.on_load(sublime.active_window().active_view())
        for window in sublime.windows():
            self.on_load(window.active_view())

    def on_load(self, view):
        self.restore(view, 'on_load')

    def on_deactivated(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        if index != (-1, -1):  # if the view was not closed
            self.save(view, 'on_deactivated')

    def on_activated(self, view):
        self.restore(view, 'on_activated')

    def on_pre_close(self, view):
        self.save(view, 'on_pre_close')

    def on_pre_save(self, view):
        self.save(view, 'on_pre_save')

    def save(self, view, where='unknow'):
        if view is None or not view.file_name():
            return

        if view.is_loading():
            sublime.set_timeout(lambda: self.save(view, where), 100)
            return

        _id = self.view_index(view)
        if _id not in self.db:
            self.db[_id] = {}

        # if the result of the new collected data is different
        # from the old data, then will write to disk
        # this will hold the old value for comparison
        old_db = dict(self.db[_id])

        # if the size of the view change outside the application skip
        # restoration
        self.db[_id]['id'] = int(view.size())

        # marks
        self.db[_id]['m'] = [[item.a, item.b]
                       for item in view.get_regions("mark")]
        if self.debug:
            print('marks: ' + str(self.db[_id]['m']))

        # previous folding save, to be able to refold
        if 'f' in self.db[_id] and list(self.db[_id]['f']) != []:
            self.db[_id]['pf'] = list(self.db[_id]['f'])

        # folding
        self.db[_id]['f'] = [[item.a, item.b] for item in view.folded_regions()]
        if self.debug:
            print('fold: ' + str(self.db[_id]['f']))

        # write to disk only if something changed
        if old_db != self.db[_id] or where == 'on_deactivated':
            with GzipFile(self.store, 'wb') as f:
                dump(self.db, f, -1)

    def view_index(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        return str(window.id()) + str(index)

    def restore(self, view, where='unknow'):
        if view is None or not view.file_name():
            return

        if view.is_loading():
            sublime.set_timeout(lambda: self.restore(view, where), 100)
            return

        _id = self.view_index(view)
        if self.debug:
            print('-----------------------------------')
            print('RESTORING from: ' + where)
            print('file: ' + view.file_name())
            print('_id: ' + _id)

        if _id in self.db:
            # fold
            rs = []
            for r in self.db[_id]['f']:
                rs.append(sublime.Region(int(r[0]), int(r[1])))
            if len(rs):
                view.fold(rs)
                if self.debug:
                    print("fold: " + str(rs))

            # marks
            rs = []
            for r in self.db[_id]['m']:
                rs.append(sublime.Region(int(r[0]), int(r[1])))
            if len(rs):
                view.add_regions(
                    "mark", rs, "mark", "dot", sublime.HIDDEN | sublime.PERSISTENT)
                if self.debug:
                    print('marks: ' + str(self.db[_id]['m']))


class OrgmodeFoldingCommand(sublime_plugin.TextCommand):
    """
    Bind to TAB key, and if the current line is not
    a headline, a \t would be inserted.
    """

    def run(self, edit):
        (row,col) = self.view.rowcol(self.view.sel()[0].begin())
        line = row + 1
        print(line)
        for s in self.view.sel():
            r = self.view.full_line(s)
            if self._is_region_folded(r.b + 1, self.view):
                self.view.run_command("unfold")
                return

        pt = self.view.text_point(line, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pt))
        self.view.run_command("fold")

    def _is_region_folded(self, region, view):
        for i in view.folded_regions():
            if i.contains(region):
                return True
        return False
########NEW FILE########
__FILENAME__ = abstract
# -*- coding: utf-8 -*-
import sys
import subprocess
import sublime


DEFAULT_OPEN_LINK_COMMANDS = dict(
    # Standard universal can opener for OSX.
    darwin=['open'],
    win32=['cmd', '/C', 'start'],
    linux=['xdg-open'],
)


class AbstractLinkResolver(object):

    def __init__(self, view):
        self.view = view
        self.settings = sublime.load_settings('orgmode.sublime-settings')
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_LINK_COMMANDS)

    def extract(self, content):
        return content

    def replace(self, content):
        return content

    def resolve(self, content):
        match = self.extract(content)
        if not match:
            return None
        return self.replace(match)

    def get_link_command(self):
        platform = sys.platform
        for key, val in self.link_commands.items():
            if key in platform:
                return val
        return None

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nPlatform not yet supported.')
            return None

        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        cmd = command + [content]
        arg_list_wrapper = self.settings.get(
            "orgmode.open_link.resolver.abstract.arg_list_wrapper", [])
        if arg_list_wrapper:
            cmd = arg_list_wrapper + [' '.join(cmd)]
            source_filename = '\"' + self.view.file_name() + '\"'
            cmd += [source_filename]
            if sys.platform != 'win32':
                cmd += ['--origin', source_filename, '--quiet']

        print('*****')
        print(repr(content), content)
        print(cmd)
        sublime.status_message('Executing: %s' % cmd)

        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = str(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = str(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)


class AbstractRegexLinkResolver(AbstractLinkResolver):

    def __init__(self, view):
        self.view = view
        self.settings = sublime.load_settings('orgmode.sublime-settings')
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_LINK_COMMANDS)
        self.regex = None

    def extract(self, content):
        if self.regex is None:
            return content
        match = self.regex.match(content)
        return match

    def replace(self, match):
        return match.groups()[1]

########NEW FILE########
__FILENAME__ = crucible

import re
from .abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.crucible.pattern'
PATTERN_DEFAULT = r'^(crucible|cru|cr):(?P<review>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.crucible.url'
URL_DEFAULT = 'http://sandbox.fisheye.atlassian.com/cru/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        return self.url % match.group('review')

########NEW FILE########
__FILENAME__ = email

import re
from .abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.email.pattern'
PATTERN_DEFAULT = r'^(?P<type>email|mailto):(?P<email>[^/]+)(/(?P<subject>.+))?$'
URL_SETTING = 'orgmode.open_link.resolver.email.url'
URL_DEFAULT = 'mailto:%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        match = match.groupdict()
        if match['type'] == 'mailto':
            url = self.url % match['email']
            if match['subject']:
                url += '?subject=%s' % match['subject']
            return url
        if match['type'] == 'email':
            return dict(email=match['email'], path=match['subject'])

    def execute(self, content):
        if isinstance(content, dict) and 'email' in content:
            import sublime
            # TODO Implement email opener here.
            sublime.error_message('Email opener not implemented yet.')
            raise NotImplemented()
        else:
            return super(Resolver, self).execute(content)

########NEW FILE########
__FILENAME__ = fisheye

import re
from .abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.fisheye.pattern'
PATTERN_DEFAULT = r'^(fisheye|fish|fe):(?P<repo>[^/]+)(/(?P<rev>.+))?$'
URL_SETTING = 'orgmode.open_link.resolver.fisheye.url'
URL_DEFAULT = 'http://sandbox.fisheye.atlassian.com/changelog/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        match = match.groupdict()
        url = self.url % match['repo']
        if match['rev']:
            url += '?cs=%s' % match['rev']
        return url

########NEW FILE########
__FILENAME__ = http

import sys
import re
import subprocess
import sublime
from .abstract import AbstractRegexLinkResolver

try:
    import urllib.request, urllib.parse, urllib.error
except ImportError:
    import urllib



PATTERN_SETTING = 'orgmode.open_link.resolver.http.pattern'
PATTERN_DEFAULT = r'^(http):(?P<url>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.http.url'
URL_DEFAULT = 'http:%s'


DEFAULT_OPEN_HTTP_LINK_COMMANDS = dict(
    darwin=['open'],
    win32=['cmd', '/C'],
    linux=['xdg-open'],
)


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_HTTP_LINK_COMMANDS)

    def replace(self, match):
        return self.url % match.group('url')

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None
            
        # cmd.exe quote is needed, http://ss64.com/nt/syntax-esc.html
        # escape these: ^\  ^&  ^|  ^>  ^<  ^^
        if sys.platform == 'win32':
            content = content.replace("^", "^^")
            content = content.replace("&", "^&")
            content = content.replace("\\", "^\\")
            content = content.replace("|", "^|")
            content = content.replace("<", "^<")
            content = content.replace(">", "^>")


        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = command + ['start ' + content]

        print('HTTP*****')
        print(repr(content), content)
        print(repr(cmd))
        print(cmd)
        sublime.status_message('Executing: %s' % cmd)
        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = str(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = str(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)

########NEW FILE########
__FILENAME__ = https

import re
import sys
import subprocess
import sublime
from .abstract import AbstractRegexLinkResolver

try:
    import urllib.request, urllib.parse, urllib.error
except ImportError:
    import urllib


PATTERN_SETTING = 'orgmode.open_link.resolver.https.pattern'
PATTERN_DEFAULT = r'^(https):(?P<url>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.https.url'
URL_DEFAULT = 'https:%s'

DEFAULT_OPEN_HTTP_LINK_COMMANDS = dict(
    darwin=['open'],
    win32=['cmd', '/C'],
    linux=['xdg-open'],
)


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_HTTP_LINK_COMMANDS)

    def replace(self, match):
        return self.url % match.group('url')

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None

        # cmd.exe quote is needed, http://ss64.com/nt/syntax-esc.html
        # escape these: ^\  ^&  ^|  ^>  ^<  ^^
        if sys.platform == 'win32':
            content = content.replace("^", "^^")
            content = content.replace("&", "^&")
            content = content.replace("\\", "^\\")
            content = content.replace("|", "^|")
            content = content.replace("<", "^<")
            content = content.replace(">", "^>")

        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = command + ['start ' + content]

        print('HTTP*****')
        print(repr(content), content)
        print(repr(cmd))
        print(cmd)
        sublime.status_message('Executing: %s' % cmd)
        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = str(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = str(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)

########NEW FILE########
__FILENAME__ = jira

import re
from .abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.jira.pattern'
PATTERN_DEFAULT = r'^(jira|j):(?P<issue>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.jira.url'
URL_DEFAULT = 'http://sandbox.onjira.com/browse/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        return self.url % match.group('issue')

########NEW FILE########
__FILENAME__ = local_file

import re
import os
from fnmatch import fnmatch
import sublime
from .abstract import AbstractLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.local_file.pattern'
PATTERN_DEFAULT = r'^(?P<filepath>.+?)(?::(?P<row>\d+)(?::(?P<col>\d+))?)?$'

FORCE_LOAD_SETTING = 'orgmode.open_link.resolver.local_file.force_into_sublime'
FORCE_LOAD_DEFAULT = ['*.txt', '*.org', '*.py', '*.rb',
                      '*.html', '*.css', '*.js', '*.php', '*.c', '*.cpp', '*.h']


class Resolver(AbstractLinkResolver):

    '''
    @todo: If the link is a local org-file open it directly via sublime, otherwise use OPEN_LINK_COMMAND.
    '''

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.force_load_patterns = get(FORCE_LOAD_SETTING, FORCE_LOAD_DEFAULT)

    def file_is_excluded(self, filepath):
        basename = os.path.basename(filepath)
        for pattern in self.force_load_patterns:
            if fnmatch(basename, pattern):
                print('found in force_load_patterns')
                return False
        return True

        folder_exclude_patterns = self.settings.get('folder_exclude_patterns')
        if basename in folder_exclude_patterns:
            print('found in folder_exclude_patterns')
            return True
        file_exclude_patterns = self.settings.get('file_exclude_patterns')
        for pattern in file_exclude_patterns:
            if fnmatch(basename, pattern):
                print('found in file_exclude_patterns')
                return True
        return False

    def expand_path(self, filepath):
        filepath = os.path.expandvars(filepath)
        filepath = os.path.expanduser(filepath)

        match = self.regex.match(filepath)
        if match:
            filepath, row, col = match.group(
                'filepath'), match.group('row'), match.group('col')
        else:
            row = None
            col = None

        drive, filepath = os.path.splitdrive(filepath)
        if not filepath.startswith('/'):  # If filepath is relative...
            cwd = os.path.dirname(self.view.file_name())
            testfile = os.path.join(cwd, filepath)
            if os.path.exists(testfile):  # See if it exists here...
                filepath = testfile

        filepath = ''.join([drive, filepath]) if drive else filepath
        print('filepath: ' + filepath)
        if not self.file_is_excluded(filepath):
            if row:
                filepath += ':%s' % row
            if col:
                filepath += ':%s' % col
            print('file_is_excluded')
            self.view.window().open_file(filepath, sublime.ENCODED_POSITION)
            return True

        return filepath

    def replace(self, content):
        content = self.expand_path(content)
        return content

    def execute(self, content):
        if content is not True:
            print('normal open')
            return super(Resolver, self).execute(content)

########NEW FILE########
__FILENAME__ = prompt

import re
import sys
import subprocess
import sublime
from .abstract import AbstractRegexLinkResolver

DEFAULT_OPEN_PROMPT_LINK_COMMANDS = dict(
    darwin=['open', '-a', 'Terminal'],
    win32=['cmd'],
    linux=['gnome-terminal'],
)


PATTERN_SETTING = 'orgmode.open_link.resolver.prompt.pattern'
PATTERN_DEFAULT = r'^(cmd:|prompt:)(?P<path>.+)$'
PROMPT_SETTING = 'orgmode.open_link.resolver.prompt.path'
PROMPT_DEFAULT_WIN32 = '%s'
PROMPT_DEFAULT_LINUX = '--working-directory=%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_PROMPT_LINK_COMMANDS)
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        if sys.platform == 'win32' or sys.platform == 'darwin':
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_WIN32)
        else:
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_LINUX)
 
    def replace(self, match):
        return self.url % match.group('path')

    def get_link_command(self):
        platform = sys.platform
        for key, val in self.link_commands.items():
            if key in platform:
                return val
        return None

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None

        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = 'cmd /C start cmd.exe /K "cd /d '+content+'"'

        print('PROMPT*****')
        print(repr(content))
        print(cmd)
        # \"cd /d c:\dev\apps\"' is not recognized as an internal or external command,
        sublime.status_message('Executing: %s' % cmd)
        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = str(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = str(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)

########NEW FILE########
__FILENAME__ = redmine

import re
from .abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.redmine.pattern'
PATTERN_DEFAULT = r'^(issue:|redmine:|#)(?P<issue>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.redmine.url'
URL_DEFAULT = 'http://redmine.org/issues/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        return self.url % match.group('issue')

########NEW FILE########
