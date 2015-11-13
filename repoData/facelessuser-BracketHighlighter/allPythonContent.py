__FILENAME__ = bh_core
from os.path import basename, exists, join, normpath
import sublime
import sublime_plugin
from time import time, sleep
import thread
import ure
from bh_plugin import BracketPlugin, BracketRegion, ImportModule
from collections import namedtuple
import traceback

ure.set_cache_directory(join(sublime.packages_path(), "User"), "bh")

BH_MATCH_TYPE_NONE = 0
BH_MATCH_TYPE_SELECTION = 1
BH_MATCH_TYPE_EDIT = 2
DEFAULT_STYLES = {
    "default": {
        "icon": "dot",
        "color": "brackethighlighter.default",
        "style": "underline"
    },
    "unmatched": {
        "icon": "question",
        "color": "brackethighlighter.unmatched",
        "style": "outline"
    }
}
HV_RSVD_VALUES = ["__default__", "__bracket__"]

HIGH_VISIBILITY = False

GLOBAL_ENABLE = True


def bh_logging(msg):
    print("BracketHighlighter: %s" % msg)


def bh_debug(msg):
    if sublime.load_settings("bh_core.sublime-settings").get('debug_enable', False):
        bh_logging(msg)


def underline(regions):
    """
    Convert sublime regions into underline regions
    """

    r = []
    for region in regions:
        start = region.begin()
        end = region.end()
        while start < end:
            r.append(sublime.Region(start))
            start += 1
    return r


def load_modules(obj, loaded):
    """
    Load bracket plugin modules
    """

    plib = obj.get("plugin_library")
    if plib is None:
        return

    try:
        module = ImportModule.import_module(plib, loaded)
        obj["compare"] = getattr(module, "compare", None)
        obj["post_match"] = getattr(module, "post_match", None)
        obj["validate"] = getattr(module, "validate", None)
        loaded.add(plib)
    except:
        bh_logging("Could not load module %s\n%s" % (plib, str(traceback.format_exc())))
        raise


def select_bracket_style(option):
    """
    Configure style of region based on option
    """

    style = sublime.HIDE_ON_MINIMAP
    if option == "outline":
        style |= sublime.DRAW_OUTLINED
    elif option == "none":
        style |= sublime.HIDDEN
    elif option == "underline":
        style |= sublime.DRAW_EMPTY_AS_OVERWRITE
    return style


def select_bracket_icons(option, icon_path):
    """
    Configure custom gutter icons if they can be located.
    """

    icon = ""
    small_icon = ""
    open_icon = ""
    small_open_icon = ""
    close_icon = ""
    small_close_icon = ""
    # Icon exist?
    if not option == "none" and not option == "":
        if exists(normpath(join(sublime.packages_path(), icon_path, option + ".png"))):
            icon = "../%s/%s" % (icon_path, option)
        if exists(normpath(join(sublime.packages_path(), icon_path, option + "_small.png"))):
            small_icon = "../%s/%s" % (icon_path, option + "_small")
        if exists(normpath(join(sublime.packages_path(), icon_path, option + "_open.png"))):
            open_icon = "../%s/%s" % (icon_path, option + "_open")
        else:
            open_icon = icon
        if exists(normpath(join(sublime.packages_path(), icon_path, option + "_open_small.png"))):
            small_open_icon = "../%s/%s" % (icon_path, option + "_open_small")
        else:
            small_open_icon = small_icon
        if exists(normpath(join(sublime.packages_path(), icon_path, option + "_close.png"))):
            close_icon = "../%s/%s" % (icon_path, option + "_close")
        else:
            close_icon = icon
        if exists(normpath(join(sublime.packages_path(), icon_path, option + "_close_small.png"))):
            small_close_icon = "../%s/%s" % (icon_path, option + "_close_small")
        else:
            small_close_icon = small_icon

    return icon, small_icon, open_icon, small_open_icon, close_icon, small_close_icon


def exclude_bracket(enabled, filter_type, language_list, language):
    """
    Exclude or include brackets based on filter lists.
    """

    exclude = True
    if enabled:
        # Black list languages
        if filter_type == 'blacklist':
            exclude = False
            if language != None:
                for item in language_list:
                    if language == item.lower():
                        exclude = True
                        break
        #White list languages
        elif filter_type == 'whitelist':
            if language != None:
                for item in language_list:
                    if language == item.lower():
                        exclude = False
                        break
    return exclude


class BhEventMgr(object):
    """
    Object to manage when bracket events should be launched.
    """

    @classmethod
    def load(cls):
        """
        Initialize variables for determining
        when to initiate a bracket matching event.
        """

        cls.wait_time = 0.12
        cls.time = time()
        cls.modified = False
        cls.type = BH_MATCH_TYPE_SELECTION
        cls.ignore_all = False

BhEventMgr.load()


class BhThreadMgr(object):
    """
    Object to help track when a new thread needs to be started.
    """

    restart = False


class BhEntry(object):
    """
    Generic object for bracket regions.
    """

    def move(self, begin, end):
        """
        Create a new object with the points moved to the specified locations.
        """

        return self._replace(begin=begin, end=end)

    def size(self):
        """
        Size of bracket selection.
        """

        return abs(self.begin - self.end)

    def toregion(self):
        """
        Convert to sublime Region.
        """

        return sublime.Region(self.begin, self.end)


class BracketEntry(namedtuple('BracketEntry', ['begin', 'end', 'type'], verbose=False), BhEntry):
    """
    Bracket object.
    """

    pass


class ScopeEntry(namedtuple('ScopeEntry', ['begin', 'end', 'scope', 'type'], verbose=False), BhEntry):
    """
    Scope bracket object.
    """

    pass


class BracketSearchSide(object):
    """
    Userful structure to specify bracket matching direction.
    """

    left = 0
    right = 1


class BracektSearchType(object):
    """
    Userful structure to specify bracket matching direction.
    """

    opening = 0
    closing = 1


class BracketSearch(object):
    """
    Object that performs regex search on the view's buffer and finds brackets.
    """

    def __init__(self, bfr, window, center, pattern, scope_check, scope):
        """
        Prepare the search object
        """

        self.center = center
        self.pattern = pattern
        self.bfr = bfr
        self.scope = scope
        self.scope_check = scope_check
        self.prev_match = [None, None]
        self.return_prev = [False, False]
        self.done = [False, False]
        self.start = [None, None]
        self.left = [[], []]
        self.right = [[], []]
        self.findall(window)

    def reset_end_state(self):
        """
        Reset the the current search flags etc.
        This is usually done before searching the other direction.
        """

        self.start = [None, None]
        self.done = [False, False]
        self.prev_match = [None, None]
        self.return_prev = [False, False]

    def remember(self, match_type):
        """
        Remember the current match.
        Don't get the next bracket on the next
        request, but return the current one again.
        """

        self.return_prev[match_type] = True
        self.done[match_type] = False

    def findall(self, window):
        """
        Find all of the brackets and sort them
        to "left of the cursor" and "right of the cursor"
        """

        for m in self.pattern.finditer(self.bfr, window[0], window[1]):
            g = m.lastindex
            try:
                start = m.start(g)
                end = m.end(g)
            except:
                continue

            match_type = int(not bool(g % 2))
            bracket_id = (g / 2) - match_type

            if not self.scope_check(start, bracket_id, self.scope):
                if (end <= self.center if match_type else start < self.center):
                    self.left[match_type].append(BracketEntry(start, end, bracket_id))
                elif (end > self.center if match_type else start >= self.center):
                    self.right[match_type].append(BracketEntry(start, end, bracket_id))

    def get_open(self, bracket_code):
        """
        Get opening bracket.  Accepts a bracket code that
        determines which side of the cursor the next match is returned from.
        """

        for b in self._get_bracket(bracket_code, BracektSearchType.opening):
            yield b

    def get_close(self, bracket_code):
        """
        Get closing bracket.  Accepts a bracket code that
        determines which side of the cursor the next match is returned from.
        """

        for b in self._get_bracket(bracket_code, BracektSearchType.closing):
            yield b

    def is_done(self, match_type):
        """
        Retrieve done flag.
        """

        return self.done[match_type]

    def _get_bracket(self, bracket_code, match_type):
        """
        Get the next bracket.  Accepts bracket code that determines
        which side of the cursor the next match is returned from and
        the match type which determines whether a opening or closing
        bracket is desired.
        """

        if self.done[match_type]:
            return
        if self.return_prev[match_type]:
            self.return_prev[match_type] = False
            yield self.prev_match[match_type]
        if bracket_code == BracketSearchSide.left:
            if self.start[match_type] is None:
                self.start[match_type] = len(self.left[match_type])
            for x in reversed(range(0, self.start[match_type])):
                b = self.left[match_type][x]
                self.prev_match[match_type] = b
                self.start[match_type] -= 1
                yield b
        else:
            if self.start[match_type] is None:
                self.start[match_type] = 0
            for x in range(self.start[match_type], len(self.right[match_type])):
                b = self.right[match_type][x]
                self.prev_match[match_type] = b
                self.start[match_type] += 1
                yield b

        self.done[match_type] = True


class BracketDefinition(object):
    """
    Normal bracket definition.
    """

    def __init__(self, bracket):
        """
        Setup the bracket object by reading the passed in dictionary.
        """

        self.name = bracket["name"]
        self.style = bracket.get("style", "default")
        self.compare = bracket.get("compare")
        sub_search = bracket.get("find_in_sub_search", "false")
        self.find_in_sub_search_only = sub_search == "only"
        self.find_in_sub_search = sub_search == "true" or self.find_in_sub_search_only
        self.post_match = bracket.get("post_match")
        self.validate = bracket.get("validate")
        self.scope_exclude_exceptions = bracket.get("scope_exclude_exceptions", [])
        self.scope_exclude = bracket.get("scope_exclude", [])
        self.ignore_string_escape = bracket.get("ignore_string_escape", False)


class ScopeDefinition(object):
    """
    Scope bracket definition.
    """

    def __init__(self, bracket):
        """
        Setup the bracket object by reading the passed in dictionary.
        """

        self.style = bracket.get("style", "default")
        self.open = ure.compile("\\A" + bracket.get("open", "."), ure.MULTILINE | ure.IGNORECASE)
        self.close = ure.compile(bracket.get("close", ".") + "\\Z", ure.MULTILINE | ure.IGNORECASE)
        self.name = bracket["name"]
        sub_search = bracket.get("sub_bracket_search", "false")
        self.sub_search_only = sub_search == "only"
        self.sub_search = self.sub_search_only == True or sub_search == "true"
        self.compare = bracket.get("compare")
        self.post_match = bracket.get("post_match")
        self.validate = bracket.get("validate")
        self.scopes = bracket["scopes"]


class StyleDefinition(object):
    """
    Styling definition.
    """

    def __init__(self, name, style, default_highlight, icon_path):
        """
        Setup the style object by reading the
        passed in dictionary. And other parameters.
        """

        self.name = name
        self.selections = []
        self.open_selections = []
        self.close_selections = []
        self.center_selections = []
        self.color = style.get("color", default_highlight["color"])
        self.style = select_bracket_style(style.get("style", default_highlight["style"]))
        self.underline = self.style & sublime.DRAW_EMPTY_AS_OVERWRITE
        (
            self.icon, self.small_icon, self.open_icon,
            self.small_open_icon, self.close_icon, self.small_close_icon
        ) = select_bracket_icons(style.get("icon", default_highlight["icon"]), icon_path)
        self.no_icon = ""


class BhToggleStringEscapeModeCommand(sublime_plugin.TextCommand):
    """
    Toggle between regex escape and
    string escape for brackets in strings.
    """

    def run(self, edit):
        default_mode = sublime.load_settings("bh_core.sublime-settings").get('bracket_string_escape_mode', 'string')
        if self.view.settings().get('bracket_string_escape_mode', default_mode) == "regex":
            self.view.settings().set('bracket_string_escape_mode', "string")
            sublime.status_message("Bracket String Escape Mode: string")
        else:
            self.view.settings().set('bracket_string_escape_mode', "regex")
            sublime.status_message("Bracket String Escape Mode: regex")


class BhShowStringEscapeModeCommand(sublime_plugin.TextCommand):
    """
    Shoe current string escape mode for sub brackets in strings.
    """

    def run(self, edit):
        default_mode = sublime.load_settings("BracketHighlighter.sublime-settings").get('bracket_string_escape_mode', 'string')
        sublime.status_message("Bracket String Escape Mode: %s" % self.view.settings().get('bracket_string_escape_mode', default_mode))


class BhToggleHighVisibilityCommand(sublime_plugin.ApplicationCommand):
    """
    Toggle a high visibility mode that
    highlights the entire bracket extent.
    """

    def run(self):
        global HIGH_VISIBILITY
        HIGH_VISIBILITY = not HIGH_VISIBILITY


class BhToggleEnableCommand(sublime_plugin.ApplicationCommand):
    """
    Toggle global enable for BracketHighlighter.
    """

    def run(self):
        global GLOBAL_ENABLE
        GLOBAL_ENABLE = not GLOBAL_ENABLE


class BhKeyCommand(sublime_plugin.WindowCommand):
    """
    Command to process shortcuts, menu calls, and command palette calls.
    This is how BhCore is called with different options.
    """

    def run(self, threshold=True, lines=False, adjacent=False, ignore={}, plugin={}):
        # Override events
        BhEventMgr.ignore_all = True
        BhEventMgr.modified = False
        self.bh = BhCore(
            threshold,
            lines,
            adjacent,
            ignore,
            plugin,
            True
        )
        self.view = self.window.active_view()
        sublime.set_timeout(self.execute, 100)

    def execute(self):
        bh_debug("Key Event")
        self.bh.match(self.view)
        BhEventMgr.ignore_all = False
        BhEventMgr.time = time()


class BhCore(object):
    """
    Bracket matching class.
    """
    plugin_reload = False

    def __init__(self, override_thresh=False, count_lines=False, adj_only=None, ignore={}, plugin={}, keycommand=False):
        """
        Load settings and setup reload events if settings changes.
        """

        self.settings = sublime.load_settings("bh_core.sublime-settings")
        self.keycommand = keycommand
        if not keycommand:
            self.settings.clear_on_change('reload')
            self.settings.add_on_change('reload', self.setup)
        self.setup(override_thresh, count_lines, adj_only, ignore, plugin)

    def setup(self, override_thresh=False, count_lines=False, adj_only=None, ignore={}, plugin={}):
        """
        Initialize class settings from settings file and inputs.
        """

        # Init view params
        self.last_id_view = None
        self.last_id_sel = None
        self.view_tracker = (None, None)
        self.ignore_threshold = override_thresh or bool(self.settings.get("ignore_threshold", False))
        self.adj_only = adj_only if adj_only is not None else bool(self.settings.get("match_only_adjacent", False))
        self.auto_selection_threshold = int(self.settings.get("auto_selection_threshold", 10))
        self.no_multi_select_icons = bool(self.settings.get("no_multi_select_icons", False))
        self.count_lines = count_lines
        self.default_string_escape_mode = str(self.settings.get('bracket_string_escape_mode', "string"))

        # Init bracket objects
        self.bracket_types = self.settings.get("brackets", [])
        self.scope_types = self.settings.get("scope_brackets", [])

        # Init selection params
        self.use_selection_threshold = True
        self.selection_threshold = int(self.settings.get("search_threshold", 5000))
        self.new_select = False
        self.loaded_modules = set([])

        # High Visibility options
        self.hv_style = select_bracket_style(self.settings.get("high_visibility_style", "outline"))
        self.hv_underline = self.hv_style & sublime.DRAW_EMPTY_AS_OVERWRITE
        self.hv_color = self.settings.get("high_visibility_color", HV_RSVD_VALUES[1])

        # Init plugin
        self.plugin = None
        self.transform = set([])
        if 'command' in plugin:
            self.plugin = BracketPlugin(plugin, self.loaded_modules)
            self.new_select = True
            if 'type' in plugin:
                for t in plugin["type"]:
                    self.transform.add(t)

    def eval_show_unmatched(self, show_unmatched, exception, language):
        """
        Determine if show_unmatched should be enabled for the current view
        """
        answer = True
        if show_unmatched is True or show_unmatched is False:
            answer = show_unmatched
        if isinstance(exception, list):
            for option in exception:
                if option.lower() == language:
                    answer = not answer
                    break
        return answer

    def init_bracket_regions(self):
        """
        Load up styled regions for brackets to use.
        """

        self.bracket_regions = {}
        styles = self.settings.get("bracket_styles", DEFAULT_STYLES)
        icon_path = self.settings.get("icon_path", "Theme - Default").replace('\\', '/').strip('/')
        # Make sure default and unmatched styles in styles
        for key, value in DEFAULT_STYLES.items():
            if key not in styles:
                styles[key] = value
                continue
            for k, v in value.items():
                if k not in styles[key]:
                    styles[key][k] = v
        # Initialize styles
        default_settings = styles["default"]
        for k, v in styles.items():
            self.bracket_regions[k] = StyleDefinition(k, v, default_settings, icon_path)

    def is_valid_definition(self, params, language):
        """
        Ensure bracket definition should be and can be loaded.
        """

        return (
            not exclude_bracket(
                params.get("enabled", True),
                params.get("language_filter", "blacklist"),
                params.get("language_list", []),
                language
            ) and
            params["open"] is not None and params["close"] is not None
        )

    def init_brackets(self, language):
        """
        Initialize bracket match definition objects from settings file.
        """

        self.find_regex = []
        self.sub_find_regex = []
        self.index_open = {}
        self.index_close = {}
        self.brackets = []
        self.scopes = []
        self.view_tracker = (language, self.view.id())
        self.enabled = False
        self.sels = []
        self.multi_select = False
        self.check_compare = False
        self.check_validate = False
        self.check_post_match = False
        scopes = {}
        loaded_modules = self.loaded_modules.copy()

        for params in self.bracket_types:
            if self.is_valid_definition(params, language):
                try:
                    load_modules(params, loaded_modules)
                    entry = BracketDefinition(params)
                    if not self.check_compare and entry.compare is not None:
                        self.check_compare = True
                    if not self.check_validate and entry.validate is not None:
                        self.check_validate = True
                    if not self.check_post_match and entry.post_match is not None:
                        self.check_post_match = True
                    self.brackets.append(entry)
                    if not entry.find_in_sub_search_only:
                        self.find_regex.append(params["open"])
                        self.find_regex.append(params["close"])
                    else:
                        self.find_regex.append(r"([^\s\S])")
                        self.find_regex.append(r"([^\s\S])")

                    if entry.find_in_sub_search:
                        self.sub_find_regex.append(params["open"])
                        self.sub_find_regex.append(params["close"])
                    else:
                        self.sub_find_regex.append(r"([^\s\S])")
                        self.sub_find_regex.append(r"([^\s\S])")
                except Exception, e:
                    bh_logging(e)

        scope_count = 0
        for params in self.scope_types:
            if self.is_valid_definition(params, language):
                try:
                    load_modules(params, loaded_modules)
                    entry = ScopeDefinition(params)
                    if not self.check_compare and entry.compare is not None:
                        self.check_compare = True
                    if not self.check_validate and entry.validate is not None:
                        self.check_validate = True
                    if not self.check_post_match and entry.post_match is not None:
                        self.check_post_match = True
                    for x in entry.scopes:
                        if x not in scopes:
                            scopes[x] = scope_count
                            scope_count += 1
                            self.scopes.append({"name": x, "brackets": [entry]})
                        else:
                            self.scopes[scopes[x]]["brackets"].append(entry)
                except Exception, e:
                    bh_logging(e)

        if len(self.brackets):
            bh_debug(
                "Search patterns:\n" +
                "(?:%s)\n" % '|'.join(self.find_regex) +
                "(?:%s)" % '|'.join(self.sub_find_regex)
            )
            self.sub_pattern = ure.compile("(?:%s)" % '|'.join(self.sub_find_regex), ure.MULTILINE | ure.IGNORECASE)
            self.pattern = ure.compile("(?:%s)" % '|'.join(self.find_regex), ure.MULTILINE | ure.IGNORECASE)
            self.enabled = True

    def init_match(self):
        """
        Initialize matching for the current view's syntax.
        """

        self.chars = 0
        self.lines = 0
        syntax = self.view.settings().get('syntax')
        language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
        show_unmatched = self.settings.get("show_unmatched", True),
        show_unmatched_exceptions = self.settings.get("show_unmatched_exceptions", [])

        if language != self.view_tracker[0] or self.view.id() != self.view_tracker[1]:
            self.init_bracket_regions()
            self.init_brackets(language)
            self.show_unmatched = self.eval_show_unmatched(show_unmatched, show_unmatched_exceptions, language)
        else:
            for r in self.bracket_regions.values():
                r.selections = []
                r.open_selections = []
                r.close_selections = []
                r.center_selections = []

    def unique(self):
        """
        Check if the current selection(s) is different from the last.
        """

        id_view = self.view.id()
        id_sel = "".join([str(sel.a) for sel in self.view.sel()])
        is_unique = False
        if id_view != self.last_id_view or id_sel != self.last_id_sel:
            self.last_id_view = id_view
            self.last_id_sel = id_sel
            is_unique = True
        return is_unique

    def store_sel(self, regions):
        """
        Store the current selection selection to be set at the end.
        """

        if self.new_select:
            for region in regions:
                self.sels.append(region)

    def change_sel(self):
        """
        Change the view's selections.
        """

        if self.new_select and len(self.sels) > 0:
            if self.multi_select == False:
                self.view.show(self.sels[0])
            self.view.sel().clear()
            map(lambda x: self.view.sel().add(x), self.sels)

    def hv_highlight_color(self, b_value):
        """
        High visibility highlight decesions.
        """

        color = self.hv_color
        if self.hv_color == HV_RSVD_VALUES[0]:
            color = self.bracket_regions["default"].color
        elif self.hv_color == HV_RSVD_VALUES[1]:
            color = b_value
        return color

    def highlight_regions(self, name, icon_type, selections, bracket, regions):
        """
        Apply the highlightes for the highlight region.
        """

        if len(selections):
            self.view.add_regions(
                name,
                getattr(bracket, selections),
                self.hv_highlight_color(bracket.color) if HIGH_VISIBILITY else bracket.color,
                getattr(bracket, icon_type),
                self.hv_style if HIGH_VISIBILITY else bracket.style
            )
            regions.append(name)

    def highlight(self, view):
        """
        Highlight all bracket regions.
        """

        for region_key in self.view.settings().get("bh_regions", []):
            self.view.erase_regions(region_key)

        regions = []
        icon_type = "no_icon"
        open_icon_type = "no_icon"
        close_icon_type = "no_icon"
        if not self.no_multi_select_icons or not self.multi_select:
            icon_type = "small_icon" if self.view.line_height() < 16 else "icon"
            open_icon_type = "small_open_icon" if self.view.line_height() < 16 else "open_icon"
            close_icon_type = "small_close_icon" if self.view.line_height() < 16 else "close_icon"
        for name, r in self.bracket_regions.items():
            self.highlight_regions("bh_" + name, icon_type, "selections", r, regions)
            self.highlight_regions("bh_" + name + "_center", "no_icon", "center_selections", r, regions)
            self.highlight_regions("bh_" + name + "_open", open_icon_type, "open_selections", r, regions)
            self.highlight_regions("bh_" + name + "_close", close_icon_type, "close_selections", r, regions)
        # Track which regions were set in the view so that they can be cleaned up later.
        self.view.settings().set("bh_regions", regions)

    def get_search_bfr(self, sel):
        """
        Read in the view's buffer for scanning for brackets etc.
        """

        # Determine how much of the buffer to search
        view_min = 0
        view_max = self.view.size()
        if not self.ignore_threshold:
            left_delta = sel.a - view_min
            right_delta = view_max - sel.a
            limit = self.selection_threshold / 2
            rpad = limit - left_delta if left_delta < limit else 0
            lpad = limit - right_delta if right_delta < limit else 0
            llimit = limit + lpad
            rlimit = limit + rpad
            self.search_window = (
                sel.a - llimit if left_delta >= llimit else view_min,
                sel.a + rlimit if right_delta >= rlimit else view_max
            )
        else:
            self.search_window = (0, view_max)

        # Search Buffer
        return self.view.substr(sublime.Region(0, view_max))

    def match(self, view, force_match=True):
        """
        Preform matching brackets surround the selection(s)
        """

        if view == None:
            return

        view.settings().set("BracketHighlighterBusy", True)

        if not GLOBAL_ENABLE:
            for region_key in view.settings().get("bh_regions", []):
                view.erase_regions(region_key)
            view.settings().set("BracketHighlighterBusy", False)
            return

        if self.keycommand:
            BhCore.plugin_reload = True

        if not self.keycommand and BhCore.plugin_reload:
            self.setup()
            BhCore.plugin_reload = False

        # Setup views
        self.view = view
        self.last_view = view
        num_sels = len(view.sel())
        self.multi_select = (num_sels > 1)

        if self.unique() or force_match:
            # Initialize
            self.init_match()

            # Nothing to search for
            if not self.enabled:
                view.settings().set("BracketHighlighterBusy", False)
                return

            # Abort if selections are beyond the threshold
            if self.use_selection_threshold and num_sels >= self.selection_threshold:
                self.highlight(view)
                view.settings().set("BracketHighlighterBusy", False)
                return

            multi_select_count = 0
            # Process selections.
            for sel in view.sel():
                bfr = self.get_search_bfr(sel)
                if not self.ignore_threshold and multi_select_count >= self.auto_selection_threshold:
                    self.store_sel([sel])
                    multi_select_count += 1
                    continue
                if not self.find_scopes(bfr, sel):
                    self.sub_search_mode = False
                    self.find_matches(bfr, sel)
                multi_select_count += 1

        # Highlight, focus, and display lines etc.
        self.change_sel()
        self.highlight(view)
        if self.count_lines:
            sublime.status_message('In Block: Lines ' + str(self.lines) + ', Chars ' + str(self.chars))
        view.settings().set("BracketHighlighterBusy", False)

    def save_incomplete_regions(self, left, right, regions):
        """
        Store single incomplete brackets for highlighting.
        """

        found = left if left is not None else right
        bracket = self.bracket_regions["unmatched"]
        if bracket.underline:
            bracket.selections += underline((found.toregion(),))
        else:
            bracket.selections += [found.toregion()]
        self.store_sel(regions)

    def save_regions(self, left, right, regions):
        """
        Saved matched regions.  Perform any special considerations for region formatting.
        """

        bracket = self.bracket_regions.get(self.bracket_style, self.bracket_regions["default"])
        lines = abs(self.view.rowcol(right.begin)[0] - self.view.rowcol(left.end)[0] + 1)
        if self.count_lines:
            self.chars += abs(right.begin - left.end)
            self.lines += lines
        if HIGH_VISIBILITY:
            if lines <= 1:
                if self.hv_underline:
                    bracket.selections += underline((sublime.Region(left.begin, right.end),))
                else:
                    bracket.selections += [sublime.Region(left.begin, right.end)]
            else:
                bracket.open_selections += [sublime.Region(left.begin)]
                if self.hv_underline:
                    bracket.center_selections += underline((sublime.Region(left.begin + 1, right.end - 1),))
                else:
                    bracket.center_selections += [sublime.Region(left.begin, right.end)]
                bracket.close_selections += [sublime.Region(right.begin)]
        elif bracket.underline:
            if lines <= 1:
                bracket.selections += underline((left.toregion(), right.toregion()))
            else:
                bracket.open_selections += [sublime.Region(left.begin)]
                bracket.close_selections += [sublime.Region(right.begin)]
                if left.size():
                    bracket.center_selections += underline((sublime.Region(left.begin + 1, left.end),))
                if right.size():
                    bracket.center_selections += underline((sublime.Region(right.begin + 1, right.end),))
        else:
            if lines <= 1:
                bracket.selections += [left.toregion(), right.toregion()]
            else:
                bracket.open_selections += [left.toregion()]
                bracket.close_selections += [right.toregion()]
        self.store_sel(regions)

    def sub_search(self, sel, search_window, bfr, scope=None):
        """
        Search a scope bracket match for bracekts within.
        """

        bracket = None
        left, right = self.match_brackets(bfr, search_window, sel, scope)

        regions = [sublime.Region(sel.a, sel.b)]

        if left is not None and right is not None:
            bracket = self.brackets[left.type]
            left, right, regions, nobracket = self.run_plugin(bracket.name, left, right, regions)
            if nobracket:
                return True

        # Matched brackets
        if left is not None and right is not None and bracket is not None:
            self.save_regions(left, right, regions)
            return True
        return False

    def find_scopes(self, bfr, sel):
        """
        Find brackets by scope definition.
        """

        # Search buffer
        left, right, bracket, sub_matched = self.match_scope_brackets(bfr, sel)
        if sub_matched:
            return True
        regions = [sublime.Region(sel.a, sel.b)]

        if left is not None and right is not None:
            left, right, regions, _ = self.run_plugin(bracket.name, left, right, regions)
            if left is None and right is None:
                self.store_sel(regions)
                return True

        if left is not None and right is not None:
            self.save_regions(left, right, regions)
            return True
        elif (left is not None or right is not None) and self.show_invalid:
            self.save_incomplete_regions(left, right, regions)
            return True
        return False

    def find_matches(self, bfr, sel):
        """
        Find bracket matches
        """

        bracket = None
        left, right = self.match_brackets(bfr, self.search_window, sel)

        regions = [sublime.Region(sel.a, sel.b)]

        if left is not None and right is not None:
            bracket = self.brackets[left.type]
            left, right, regions, _ = self.run_plugin(bracket.name, left, right, regions)

        # Matched brackets
        if left is not None and right is not None and bracket is not None:
            self.save_regions(left, right, regions)

        # Unmatched brackets
        elif (left is not None or right is not None) and self.show_unmatched:
            self.save_incomplete_regions(left, right, regions)

        else:
            self.store_sel(regions)

    def escaped(self, pt, ignore_string_escape, scope):
        """
        Check if sub bracket in string scope is escaped.
        """

        if not ignore_string_escape:
            return False
        if scope and scope.startswith("string"):
            return self.string_escaped(pt)
        return False

    def string_escaped(self, pt):
        """
        Check if bracket is follows escaping characters.
        Account for if in string or regex string scope.
        """

        escaped = False
        start = pt - 1
        first = False
        if self.view.settings().get("bracket_string_escape_mode", self.default_string_escape_mode) == "string":
            first = True
        while self.view.substr(start) == "\\":
            if first:
                first = False
            else:
                escaped = False if escaped else True
            start -= 1
        return escaped

    def is_illegal_scope(self, pt, bracket_id, scope=None):
        """
        Check if scope at pt X should be ignored.
        """

        bracket = self.brackets[bracket_id]
        if self.sub_search_mode and not bracket.find_in_sub_search:
            return True
        illegal_scope = False
        # Scope sent in, so we must be scanning whatever this scope is
        if scope != None:
            if self.escaped(pt, bracket.ignore_string_escape, scope):
                illegal_scope = True
            return illegal_scope
        # for exception in bracket.scope_exclude_exceptions:
        elif len(bracket.scope_exclude_exceptions) and self.view.match_selector(pt, ", ".join(bracket.scope_exclude_exceptions)):
            pass
        elif len(bracket.scope_exclude) and self.view.match_selector(pt, ", ".join(bracket.scope_exclude)):
            illegal_scope = True
        return illegal_scope

    def validate(self, b, bracket_type, bfr, scope_bracket=False):
        """
        Validate bracket.
        """

        match = True

        if not self.check_validate:
            return match

        bracket = self.scopes[b.scope]["brackets"][b.type] if scope_bracket else self.brackets[b.type]
        if bracket.validate is not None:
            try:
                match = bracket.validate(
                    bracket.name,
                    BracketRegion(b.begin, b.end),
                    bracket_type,
                    bfr
                )
            except:
                bh_logging("Plugin Bracket Find Error:\n%s" % str(traceback.format_exc()))
        return match

    def compare(self, first, second, bfr, scope_bracket=False):
        """
        Compare brackets.  This function allows bracket plugins to add aditional logic.
        """

        if scope_bracket:
            match = first is not None and second is not None
        else:
            match = first.type == second.type

        if not self.check_compare:
            return match

        if match:
            bracket = self.scopes[first.scope]["brackets"][first.type] if scope_bracket else self.brackets[first.type]
            try:
                if bracket.compare is not None and match:
                    match = bracket.compare(
                        bracket.name,
                        BracketRegion(first.begin, first.end),
                        BracketRegion(second.begin, second.end),
                        bfr
                    )
            except:
                bh_logging("Plugin Compare Error:\n%s" % str(traceback.format_exc()))
        return match

    def post_match(self, left, right, center, bfr, scope_bracket=False):
        """
        Peform special logic after a match has been made.
        This function allows bracket plugins to add aditional logic.
        """

        if left is not None:
            if scope_bracket:
                bracket = self.scopes[left.scope]["brackets"][left.type]
                bracket_scope = left.scope
            else:
                bracket = self.brackets[left.type]
            bracket_type = left.type
        elif right is not None:
            if scope_bracket:
                bracket = self.scopes[right.scope]["brackets"][right.type]
                bracket_scope = right.scope
            else:
                bracket = self.brackets[right.type]
            bracket_type = right.type
        else:
            return left, right

        self.bracket_style = bracket.style

        if not self.check_post_match:
            return left, right

        if bracket.post_match is not None:
            try:
                lbracket, rbracket, self.bracket_style = bracket.post_match(
                    self.view,
                    bracket.name,
                    bracket.style,
                    BracketRegion(left.begin, left.end) if left is not None else None,
                    BracketRegion(right.begin, right.end) if right is not None else None,
                    center,
                    bfr,
                    self.search_window
                )

                if scope_bracket:
                    left = ScopeEntry(lbracket.begin, lbracket.end, bracket_scope, bracket_type) if lbracket is not None else None
                    right = ScopeEntry(rbracket.begin, rbracket.end, bracket_scope, bracket_type) if rbracket is not None else None
                else:
                    left = BracketEntry(lbracket.begin, lbracket.end, bracket_type) if lbracket is not None else None
                    right = BracketEntry(rbracket.begin, rbracket.end, bracket_type) if rbracket is not None else None
            except:
                bh_logging("Plugin Post Match Error:\n%s" % str(traceback.format_exc()))
        return left, right

    def run_plugin(self, name, left, right, regions):
        """
        Run a bracket plugin.
        """

        lbracket = BracketRegion(left.begin, left.end)
        rbracket = BracketRegion(right.begin, right.end)
        nobracket = False

        if (
            ("__all__" in self.transform or name in self.transform) and
            self.plugin != None and
            self.plugin.is_enabled()
        ):
            lbracket, rbracket, regions, nobracket = self.plugin.run_command(self.view, name, lbracket, rbracket, regions)
            left = left.move(lbracket.begin, lbracket.end) if lbracket is not None else None
            right = right.move(rbracket.begin, rbracket.end) if rbracket is not None else None
        return left, right, regions, nobracket

    def match_scope_brackets(self, bfr, sel):
        """
        See if scope should be searched, and then check
        endcaps to determine if valid scope bracket.
        """

        center = sel.a
        left = None
        right = None
        scope_count = 0
        before_center = center - 1
        bracket_count = 0
        partial_find = None
        max_size = self.view.size() - 1
        selected_scope = None
        bracket = None

        # Cannot be inside a bracket pair if cursor is at zero
        if center == 0:
            return left, right, selected_scope, False

        # Identify if the cursor is in a scope with bracket definitions
        for s in self.scopes:
            scope = s["name"]
            extent = None
            exceed_limit = False
            if self.view.match_selector(center, scope) and self.view.match_selector(before_center, scope):
                extent = self.view.extract_scope(center)
                while not exceed_limit and extent.begin() != 0:
                    if self.view.match_selector(extent.begin() - 1, scope):
                        extent = extent.cover(self.view.extract_scope(extent.begin() - 1))
                        if extent.begin() < self.search_window[0] or extent.end() > self.search_window[1]:
                            extent = None
                            exceed_limit = True
                    else:
                        break
                while not exceed_limit and extent.end() != max_size:
                    if self.view.match_selector(extent.end(), scope):
                        extent = extent.cover(self.view.extract_scope(extent.end()))
                        if extent.begin() < self.search_window[0] or extent.end() > self.search_window[1]:
                            extent = None
                            exceed_limit = True
                    else:
                        break

            if extent is None:
                scope_count += 1
                continue

            # Search the bracket patterns of this scope
            # to determine if this scope matches the rules.
            bracket_count = 0
            scope_bfr = bfr[extent.begin():extent.end()]
            for b in s["brackets"]:
                m = b.open.search(scope_bfr)
                if m and m.group(1):
                    left = ScopeEntry(extent.begin() + m.start(1), extent.begin() + m.end(1), scope_count, bracket_count)
                    if left is not None and not self.validate(left, 0, bfr, True):
                        left = None
                m = b.close.search(scope_bfr)
                if m and m.group(1):
                    right = ScopeEntry(extent.begin() + m.start(1), extent.begin() + m.end(1), scope_count, bracket_count)
                    if right is not None and not self.validate(right, 1, bfr, True):
                        right = None
                if not self.compare(left, right, bfr, scope_bracket=True):
                    left, right = None, None
                # Track partial matches.  If a full match isn't found,
                # return the first partial match at the end.
                if partial_find is None and bool(left) != bool(right):
                    partial_find = (left, right)
                    left = None
                    right = None
                if left and right:
                    break
                bracket_count += 1
            if left and right:
                break
            scope_count += 1

        # Full match not found.  Return partial match (if any).
        if (left is None or right is None) and partial_find is not None:
            left, right = partial_find[0], partial_find[1]

        # Make sure cursor in highlighted sub group
        if (left and center <= left.begin) or (right and center >= right.end):
            left, right = None, None

        if left is not None:
            selected_scope = self.scopes[left.scope]["name"]
        elif right is not None:
            selected_scope = self.scopes[right.scope]["name"]

        if left is not None and right is not None:
            bracket = self.scopes[left.scope]["brackets"][left.type]
            if bracket.sub_search:
                self.sub_search_mode = True
                if self.sub_search(sel, (left.begin, right.end), bfr, scope):
                    return left, right, self.brackets[left.type], True
                elif bracket.sub_search_only:
                    left, right, bracket = None, None, None

        if self.adj_only:
            left, right = self.adjacent_check(left, right, center)

        left, right = self.post_match(left, right, center, bfr, scope_bracket=True)
        return left, right, bracket, False

    def match_brackets(self, bfr, window, sel, scope=None):
        """
        Regex bracket matching.
        """

        center = sel.a
        left = None
        right = None
        stack = []
        pattern = self.pattern if not self.sub_search_mode else self.sub_pattern
        bsearch = BracketSearch(bfr, window, center, pattern, self.is_illegal_scope, scope)
        for o in bsearch.get_open(BracketSearchSide.left):
            if not self.validate(o, 0, bfr):
                continue
            if len(stack) and bsearch.is_done(BracektSearchType.closing):
                if self.compare(o, stack[-1], bfr):
                    stack.pop()
                    continue
            for c in bsearch.get_close(BracketSearchSide.left):
                if not self.validate(c, 1, bfr):
                    continue
                if o.end <= c.begin:
                    stack.append(c)
                    continue
                elif len(stack):
                    bsearch.remember(BracektSearchType.closing)
                    break

            if len(stack):
                b = stack.pop()
                if self.compare(o, b, bfr):
                    continue
            else:
                left = o
            break

        bsearch.reset_end_state()
        stack = []

        # Grab each closest closing right side bracket and attempt to match it.
        # If the closing bracket cannot be matched, select it.
        for c in bsearch.get_close(BracketSearchSide.right):
            if not self.validate(c, 1, bfr):
                continue
            if len(stack) and bsearch.is_done(BracektSearchType.opening):
                if self.compare(stack[-1], c, bfr):
                    stack.pop()
                    continue
            for o in bsearch.get_open(BracketSearchSide.right):
                if not self.validate(o, 0, bfr):
                    continue
                if o.end <= c.begin:
                    stack.append(o)
                    continue
                else:
                    bsearch.remember(BracektSearchType.opening)
                    break

            if len(stack):
                b = stack.pop()
                if self.compare(b, c, bfr):
                    continue
            else:
                if left is None or self.compare(left, c, bfr):
                    right = c
            break

        if self.adj_only:
            left, right = self.adjacent_check(left, right, center)

        return self.post_match(left, right, center, bfr)

    def adjacent_check(self, left, right, center):
        if left and right:
            if left.end < center < right.begin:
                left, right = None, None
        elif (left and left.end < center) or (right and center < right.begin):
            left, right = None, None
        return left, right

bh_match = BhCore().match
bh_debug("Match object loaded.")


class BhListenerCommand(sublime_plugin.EventListener):
    """
    Manage when to kick off bracket matching.
    Try and reduce redundant requests by letting the
    background thread ensure certain needed match occurs
    """

    def on_load(self, view):
        """
        Search brackets on view load.
        """

        if self.ignore_event(view):
            return
        BhEventMgr.type = BH_MATCH_TYPE_SELECTION
        sublime.set_timeout(bh_run, 0)

    def on_modified(self, view):
        """
        Update highlighted brackets when the text changes.
        """

        if self.ignore_event(view):
            return
        BhEventMgr.type = BH_MATCH_TYPE_EDIT
        BhEventMgr.modified = True
        BhEventMgr.time = time()

    def on_activated(self, view):
        """
        Highlight brackets when the view gains focus again.
        """

        if self.ignore_event(view):
            return
        BhEventMgr.type = BH_MATCH_TYPE_SELECTION
        sublime.set_timeout(bh_run, 0)

    def on_selection_modified(self, view):
        """
        Highlight brackets when the selections change.
        """

        if self.ignore_event(view):
            return
        if BhEventMgr.type != BH_MATCH_TYPE_EDIT:
            BhEventMgr.type = BH_MATCH_TYPE_SELECTION
        now = time()
        if now - BhEventMgr.time > BhEventMgr.wait_time:
            sublime.set_timeout(bh_run, 0)
        else:
            BhEventMgr.modified = True
            BhEventMgr.time = now

    def ignore_event(self, view):
        """
        Ignore request to highlight if the view is a widget,
        or if it is too soon to accept an event.
        """

        return (view.settings().get('is_widget') or BhEventMgr.ignore_all)


def bh_run():
    """
    Kick off matching of brackets
    """

    BhEventMgr.modified = False
    window = sublime.active_window()
    view = window.active_view() if window != None else None
    BhEventMgr.ignore_all = True
    bh_match(view, True if BhEventMgr.type == BH_MATCH_TYPE_EDIT else False)
    BhEventMgr.ignore_all = False
    BhEventMgr.time = time()


def bh_loop():
    """
    Start thread that will ensure highlighting happens after a barage of events
    Initial highlight is instant, but subsequent events in close succession will
    be ignored and then accounted for with one match by this thread
    """

    while not BhThreadMgr.restart:
        if BhEventMgr.modified == True and time() - BhEventMgr.time > BhEventMgr.wait_time:
            sublime.set_timeout(bh_run, 0)
        sleep(0.5)

    if BhThreadMgr.restart:
        BhThreadMgr.restart = False
        sublime.set_timeout(lambda: thread.start_new_thread(bh_loop, ()), 0)

if sublime.load_settings("bh_core.sublime-settings").get('high_visibility_enabled_by_default', False):
    HIGH_VISIBILITY = True

if not 'running_bh_loop' in globals():
    running_bh_loop = True
    thread.start_new_thread(bh_loop, ())
    bh_debug("Starting Thread")
else:
    bh_debug("Restarting Thread")
    BhThreadMgr.restart = True

########NEW FILE########
__FILENAME__ = bashsupport
def validate(name, bracket, bracket_side, bfr):
    return bfr[bracket.begin:bracket.end].islower()


def compare(name, first, second, bfr):
    o = bfr[first.begin:first.end]
    c = bfr[second.begin:second.end]

    match = False
    if o == "if" and c == "fi":
        match = True
    elif o in ["select", "for", "while", "until"] and c == "done":
        match = True
    elif o == "case" and c == "esac":
        match = True
    return match

########NEW FILE########
__FILENAME__ = bracketremove
import bh_plugin
import re
import sublime


class BracketRemove(bh_plugin.BracketPluginCommand):
    def decrease_indent_level(self, edit, row_first, row_last):
        tab_size = self.view.settings().get("tab_size", 4)
        indents = re.compile(r"^(?:\t| {%d}| *)((?:\t| {%d}| )*)([\s\S]*)" % (tab_size, tab_size))
        if not self.single_line:
            for x in reversed(range(row_first, row_last + 1)):
                line = self.view.full_line(self.view.text_point(x, 0))
                text = self.view.substr(line)
                m = indents.match(text)
                if m:
                    self.view.replace(edit, line, m.group(1) + m.group(2))

    def run(self, edit, name, remove_content=False, remove_indent=False, remove_block=False):
        if remove_content:
            self.view.replace(edit, sublime.Region(self.left.begin, self.right.end), "")
        else:
            row_first = self.view.rowcol(self.left.end)[0] + 1
            row_last = self.view.rowcol(self.right.begin)[0] - 1
            self.single_line = not row_first <= row_last
            if remove_block and not self.single_line:
                self.view.replace(edit, self.view.full_line(self.right.toregion()), "")
            else:
                self.view.replace(edit, self.right.toregion(), "")
            if remove_indent:
                self.decrease_indent_level(edit, row_first, row_last)
            if remove_block and not self.single_line:
                self.view.replace(edit, self.view.full_line(self.left.toregion()), "")
            else:
                self.view.replace(edit, self.left.toregion(), "")

        self.left = None
        self.right = None
        self.nobracket = True


def plugin():
    return BracketRemove

########NEW FILE########
__FILENAME__ = bracketselect
import bh_plugin
import sublime

DEFAULT_TAGS = ["cfml", "html", "angle"]


class SelectBracket(bh_plugin.BracketPluginCommand):
    def run(self, edit, name, select='', tags=DEFAULT_TAGS, always_include_brackets=False):
        current_left, current_right = self.selection[0].begin(), self.selection[0].end()
        left, right = self.left, self.right
        first, last = left.end, right.begin
        if select == 'left':
            if name in tags and left.size() > 1:
                first, last = left.begin + 1, left.begin + 1
                if first == current_left and last == current_right:
                    first, last = left.begin, left.begin
            else:
                first, last = left.end, left.end
                if first == current_left and last == current_right:
                    first, last = left.begin, left.begin
        elif select == 'right':
            if left.end != right.end:
                if name in tags and left.size() > 1:
                    first, last = right.begin + 1, right.begin + 1
                    if first == current_left and last == current_right:
                        first, last = right.end, right.end
                else:
                    first, last = right.begin, right.begin
                    if first == current_left and last == current_right:
                        first, last = right.end, right.end
            else:
                # There is no second bracket, so just select the first
                if name in tags and left.size() > 1:
                    first, last = left.begin + 1, left.begin + 1
                else:
                    first, last = right.end, right.end
                    if first == current_left and last == current_right:
                        first, last = right.end, right.end
        elif first == current_left and last == current_right or always_include_brackets:
            first, last = left.begin, right.end

        self.selection = [sublime.Region(first, last)]


def plugin():
    return SelectBracket

########NEW FILE########
__FILENAME__ = erlangcase
def validate(name, bracket, bracket_side, bfr):
    text = bfr[bracket.begin:bracket.end]
    return text.lower() == text

########NEW FILE########
__FILENAME__ = foldbracket
import bh_plugin
import sublime


class FoldBrackets(bh_plugin.BracketPluginCommand):
    def run(self, edit, name):
        content = sublime.Region(self.left.end, self.right.begin)
        new_content = [content]
        if content.size > 0:
            if self.view.fold(content) == False:
                new_content = self.view.unfold(content)
        self.selection = new_content


def plugin():
    return FoldBrackets

########NEW FILE########
__FILENAME__ = phpkeywords
def compare(name, first, second, bfr):
    return "end" + bfr[first.begin:first.end].lower() == bfr[second.begin:second.end].lower()

########NEW FILE########
__FILENAME__ = rubykeywords
import re


def post_match(view, name, style, first, second, center, bfr, threshold):
    if first is not None:
        # Strip whitespace from the beginning of first bracket
        open_bracket = bfr[first.begin:first.end]
        print (open_bracket)
        if open_bracket != "do":
            m = re.match(r"(\s*\b)[\w\W]*", open_bracket)
            if m:
                first = first.move(first.begin + m.end(1), first.end)
    return first, second, style

########NEW FILE########
__FILENAME__ = swapbrackets
import sublime
from bh_plugin import ImportModule as ImpMod
BracketRemove = ImpMod.import_from("bh_modules.bracketremove", "BracketRemove")


class SwapBrackets(BracketRemove):
    def run(self, edit, name, remove_content=False, remove_indent=False, remove_block=False):
        offset = self.left.toregion().size()
        selection = [sublime.Region(self.left.begin, self.right.begin - offset)]
        left = self.left.move(self.left.end, self.left.end)
        right = self.right.move(self.right.begin, self.right.begin)
        super(SwapBrackets, self).run(edit, name)
        self.selection = selection
        self.left = left
        self.right = right
        self.nobracket = False


def plugin():
    return SwapBrackets

########NEW FILE########
__FILENAME__ = swapquotes
import bh_plugin
import sublime


class SwapQuotes(bh_plugin.BracketPluginCommand):
    def escaped(self, idx):
        view = self.view
        escaped = False
        while idx >= 0 and view.substr(idx) == '\\':
            escaped = ~escaped
            idx -= 1
        return escaped

    def run(self, edit, name):
        view = self.view
        quote = view.substr(self.left.begin)
        if quote != "'" and quote != '"':
            return
        new = "'" if (quote == '"') else '"'
        old = quote
        begin = self.left.end
        end = self.right.begin
        content_end = self.right.begin

        view.replace(edit, self.left.toregion(), view.substr(self.left.toregion()).replace(old, new))
        view.replace(edit, self.right.toregion(), view.substr(self.right.toregion()).replace(old, new))

        offset = 0
        while begin < end + offset:
            char = view.substr(begin)
            if char == old and self.escaped(begin - 1):
                view.replace(edit, sublime.Region(begin - 1, begin), '')
                offset -= 1
                content_end -= 1
            elif char == new and not self.escaped(begin - 1):
                view.insert(edit, begin, "\\")
                offset += 1
                content_end += 1
            begin += 1

        self.right = self.right.move(content_end, end + offset)
        self.selection = [sublime.Region(content_end)]


def plugin():
    return SwapQuotes

########NEW FILE########
__FILENAME__ = tagattrselect
import bh_plugin


class SelectAttr(bh_plugin.BracketPluginCommand):
    def run(self, edit, name, direction='right'):
        if self.left.size() <= 1:
            return
        tag_name = r'[\w\:\.\-]+'
        attr_name = r'''([\w\-\.:]+)(?:\s*=\s*(?:(?:"((?:\.|[^"])*)")|(?:'((?:\.|[^'])*)')|([^>\s]+)))?'''
        tname = self.view.find(tag_name, self.left.begin)
        current_region = self.selection[0]
        current_pt = self.selection[0].b
        region = self.view.find(attr_name, tname.b)
        selection = self.selection

        if direction == 'left':
            last = None

            # Keep track of last attr
            if region != None and current_pt <= region.b and region.b < self.left.end:
                last = region

            while region != None and region.b < self.left.end:
                # Select attribute until you have closest to the left of selection
                if (
                    current_pt > region.b or
                    (
                        current_pt <= region.b and current_region.a >= region.a and not
                        (
                            region.a == current_region.a and region.b == current_region.b
                        )
                    )
                ):
                    selection = [region]
                    last = None
                # Update last attr
                elif last != None:
                    last = region
                region = self.view.find(attr_name, region.b)
            # Wrap right
            if last != None:
                selection = [last]
        else:
            first = None
            # Keep track of first attr
            if region != None and region.b < self.left.end:
                first = region

            while region != None and region.b < self.left.end:
                # Select closest attr to the right of the selection
                if(
                    current_pt < region.b or
                    (
                        current_pt <= region.b and current_region.a >= region.a and not
                        (
                            region.a == current_region.a and region.b == current_region.b
                        )
                    )
                ):
                    selection = [region]
                    first = None
                    break
                region = self.view.find(attr_name, region.b)
            # Wrap left
            if first != None:
                selection = [first]
        self.selection = selection


def plugin():
    return SelectAttr

########NEW FILE########
__FILENAME__ = tagnameselect
import bh_plugin


class TagNameSelect(bh_plugin.BracketPluginCommand):
    def run(self, edit, name):
        if self.left.size() > 1:
            tag_name = '[\w\:\.\-]+'
            region1 = self.view.find(tag_name, self.left.begin)
            region2 = self.view.find(tag_name, self.right.begin)
            self.selection = [region1, region2]


def plugin():
    return TagNameSelect

########NEW FILE########
__FILENAME__ = tags
import re
from collections import namedtuple
import sublime
from os.path import basename

FLAGS = re.MULTILINE | re.IGNORECASE
HTML_START = re.compile(r'''<([\w\:\.\-]+)((?:\s+[\w\-:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^>\s]+))?)*)\s*(\/?)>''', FLAGS)
CFML_START = re.compile(r'''<([\w\:\.\-]+)((?:\s+[\w\-\.:]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^>\s]+))?)*|(?:(?<=cfif)|(?<=cfelseif))[^>]+)\s*(\/?)>''', FLAGS)
START_TAG = {
    "html": HTML_START,
    "xhtml": HTML_START,
    "cfml": CFML_START
}
END_TAG = re.compile(r'<\/([\w\:\.\-]+)[^>]*>', FLAGS)

self_closing_tags = set("colgroup dd dt li options p td tfoot th thead tr".split())
single_tags = set("area base basefont br col frame hr img input isindex link meta param embed".split())


class TagEntry(namedtuple('TagEntry', ['begin', 'end', 'name', 'self_closing', 'single'], verbose=False)):
    def move(self, begin, end):
        return self._replace(begin=begin, end=end)


def compare_languge(language, lang_list):
    found = False
    for l in lang_list:
        if language == l.lower():
            found = True
            break
    return found


def get_tag_mode(view, tag_mode_config):
    default_mode = None
    syntax = view.settings().get('syntax')
    language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
    for mode in ["html", "xhtml", "cfml"]:
        if compare_languge(language, tag_mode_config.get(mode, [])):
            return mode
    return default_mode


def post_match(view, name, style, first, second, center, bfr, threshold):
    left, right = first, second
    threshold = [0, len(bfr)] if threshold is None else threshold
    tag_settings = sublime.load_settings("bh_core.sublime-settings")
    tag_mode = get_tag_mode(view, tag_settings.get("tag_mode", {}))
    tag_style = tag_settings.get("tag_style", "angle")
    bracket_style = style

    if first is not None and tag_mode is not None:
        matcher = TagMatch(view, bfr, threshold, first, second, center, tag_mode)
        left, right = matcher.match()
        if not matcher.no_tag:
            bracket_style = tag_style

    return left, right, bracket_style


class TagSearch(object):
    def __init__(self, view, bfr, window, center, pattern, match_type):
        self.start = window[0]
        self.end = window[1]
        self.center = center
        self.pattern = pattern
        self.match_type = match_type
        self.bfr = bfr
        self.prev_match = None
        self.return_prev = False
        self.done = False
        self.view = view
        self.scope_exclude = sublime.load_settings("bh_core.sublime-settings").get("tag_scope_exclude")

    def scope_check(self, pt):
        illegal_scope = False
        for exclude in self.scope_exclude:
            illegal_scope |= bool(self.view.score_selector(pt, exclude))
        return illegal_scope

    def reset_end_state(self):
        self.done = False
        self.prev_match = None
        self.return_prev = False

    def remember(self):
        self.return_prev = True
        self.done = False

    def get_tags(self, bracket_code):
        if self.done:
            return
        if self.return_prev:
            self.return_prev = False
            yield self.prev_match
        for m in self.pattern.finditer(self.bfr, self.start, self.end):
            name = m.group(1).lower()
            if not self.match_type:
                single = bool(m.group(3) != "" or name in single_tags)
                self_closing = name in self_closing_tags or name.startswith("cf")
            else:
                single = False
                self_closing = False
            start = m.start(0)
            end = m.end(0)
            if not self.scope_check(start):
                self.prev_match = TagEntry(start, end, name, self_closing, single)
                self.start = end
                yield self.prev_match
        self.done = True


class TagMatch(object):
    def __init__(self, view, bfr, threshold, first, second, center, mode):
        self.view = view
        self.bfr = bfr
        self.mode = mode
        tag, tag_type, tag_end = self.get_first_tag(first[0])
        self.left, self.right = None, None
        self.window = None
        self.no_tag = False
        if tag and first[0] < center < tag_end:
            if tag.single:
                self.left = tag
                self.right = tag
            else:
                if tag_type == "open":
                    self.left = tag
                    self.window = (tag_end, len(bfr) if threshold is None else threshold[1])
                else:
                    self.right = tag
                    self.window = (0 if threshold is None else threshold[0], first[0])
        else:
            self.left = first
            self.right = second
            self.no_tag = True

    def get_first_tag(self, offset):
        tag = None
        tag_type = None
        self_closing = False
        single = False
        m = START_TAG[self.mode].match(self.bfr[offset:])
        end = None
        if m:
            name = m.group(1).lower()
            single = bool(m.group(3) != "" or name in single_tags)
            if self.mode == "html":
                self_closing = name in self_closing_tags
            elif self.mode == "cfml":
                self_closing = name in self_closing_tags or name.startswith("cf")
            start = m.start(0) + offset
            end = m.end(0) + offset
            tag = TagEntry(start, end, name, self_closing, single)
            tag_type = "open"
            self.center = end
        else:
            m = END_TAG.match(self.bfr[offset:])
            if m:
                name = m.group(1).lower()
                start = m.start(0) + offset
                end = m.end(0) + offset
                tag = TagEntry(start, end, name, self_closing, single)
                tag_type = "close"
                self.center = offset
        return tag, tag_type, end

    def compare_tags(self, left, right):
        return left.name == right.name

    def resolve_self_closing(self, stack, c):
        found_tag = None
        b = stack[-1]
        if self.compare_tags(b, c):
            found_tag = b
            stack.pop()
        else:
            while b is not None and b.self_closing:
                stack.pop()
                if len(stack):
                    b = stack[-1]
                    if self.compare_tags(b, c):
                        found_tag = b
                        stack.pop()
                        break
                else:
                    b = None
        return found_tag

    def match(self):
        stack = []

        # No tags to search for
        if self.no_tag or (self.left and self.right):
            return self.left, self.right

        # Init tag matching objects
        osearch = TagSearch(self.view, self.bfr, self.window, self.center, START_TAG[self.mode], 0)
        csearch = TagSearch(self.view, self.bfr, self.window, self.center, END_TAG, 1)

        # Searching for opening or closing tag to match
        match_type = 0 if self.right else 1

        # Match the tags
        for c in csearch.get_tags(match_type):
            if len(stack) and osearch.done:
                if self.resolve_self_closing(stack, c):
                    continue
            for o in osearch.get_tags(match_type):
                if o.end <= c.begin:
                    if not o.single:
                        stack.append(o)
                    continue
                else:
                    osearch.remember()
                    break

            if len(stack):
                if self.resolve_self_closing(stack, c):
                    continue
            elif match_type == 0 and not osearch.done:
                continue
            if match_type == 1:
                if self.left is None or self.compare_tags(self.left, c):
                    self.right = c
                elif self.left.self_closing:
                    self.right = self.left
            break

        if match_type == 0:
            # Find the rest of the the unmatched left side open brackets
            # approaching the cursor if all closing brackets were matched
            # Select the most recent open bracket on the stack.
            for o in osearch.get_tags(0):
                if not o.single:
                    stack.append(o)
            if len(stack):
                self.left = self.resolve_self_closing(stack, self.right)
        elif self.right is None and self.left is not None and self.left.self_closing:
            # Account for the opening tag that was found being a self closing
            self.right = self.left

        return self.left, self.right

########NEW FILE########
__FILENAME__ = bh_plugin
import sublime
from os.path import normpath, join
import imp
from collections import namedtuple
import sys
import traceback
import warnings


class BracketRegion (namedtuple('BracketRegion', ['begin', 'end'], verbose=False)):
    """
    Bracket Regions for plugins
    """

    def move(self, begin, end):
        """
        Move bracket region to different points
        """

        return self._replace(begin=begin, end=end)

    def size(self):
        """
        Get the size of the region
        """

        return abs(self.begin - self.end)

    def toregion(self):
        """
        Convert to sublime region
        """

        return sublime.Region(self.begin, self.end)


def is_bracket_region(obj):
    """
    Check if object is a BracketRegion
    """

    return isinstance(obj, BracketRegion)


class ImportModule(object):
    @classmethod
    def import_module(cls, module_name, loaded=None):
        # Pull in built-in and custom plugin directory
        if module_name.startswith("bh_modules."):
            path_name = join(sublime.packages_path(), "BracketHighlighter", normpath(module_name.replace('.', '/')))
        else:
            path_name = join(sublime.packages_path(), normpath(module_name.replace('.', '/')))
        path_name += ".py"
        if loaded is not None and module_name in loaded:
            module = sys.modules[module_name]
        else:
            with warnings.catch_warnings(record=True) as w:
                # Ignore warnings about plugin folder not being a python package
                warnings.simplefilter("always")
                module = imp.new_module(module_name)
                sys.modules[module_name] = module
                source = None
                with open(path_name) as f:
                    source = f.read().replace('\r', '')
                cls.__execute_module(source, module_name)
                w = filter(lambda i: issubclass(i.category, UserWarning), w)
        return module

    @classmethod
    def __execute_module(cls, source, module_name):
        exec(compile(source, module_name, 'exec'), sys.modules[module_name].__dict__)

    @classmethod
    def import_from(cls, module_name, attribute):
        return getattr(cls.import_module(module_name), attribute)


class BracketPlugin(object):
    """
    Class for preparing and running plugins
    """

    def __init__(self, plugin, loaded):
        """
        Load plugin module
        """

        self.enabled = False
        self.args = plugin['args'] if ("args" in plugin) else {}
        self.plugin = None
        if 'command' in plugin:
            plib = plugin['command']
            try:
                module = ImportModule.import_module(plib, loaded)
                self.plugin = getattr(module, 'plugin')()
                loaded.add(plib)
                self.enabled = True
            except Exception:
                print 'BracketHighlighter: Load Plugin Error: %s\n%s' % (plugin['command'], traceback.format_exc())

    def is_enabled(self):
        """
        Check if plugin is enabled
        """

        return self.enabled

    def run_command(self, view, name, left, right, selection):
        """
        Load arguments into plugin and run
        """

        plugin = self.plugin()
        setattr(plugin, "left", left)
        setattr(plugin, "right", right)
        setattr(plugin, "view", view)
        setattr(plugin, "selection", selection)
        setattr(plugin, "nobracket", False)
        edit = view.begin_edit()
        self.args["edit"] = edit
        self.args["name"] = name
        try:
            nobracket = False
            plugin.run(**self.args)
            left, right, selection, nobracket = plugin.left, plugin.right, plugin.selection, plugin.nobracket
        except Exception:
            print "BracketHighlighter: Plugin Run Error:\n%s" % str(traceback.format_exc())
        view.end_edit(edit)
        return left, right, selection, nobracket


class BracketPluginCommand(object):
    """
    Bracket Plugin base class
    """

    def run(self, bracket, content, selection):
        """
        Runs the plugin class
        """

        pass

########NEW FILE########
__FILENAME__ = bh_remove
import sublime_plugin
from collections import namedtuple

MENU = namedtuple("Menu", "simple content block block_indent")(
    "Remove Brackets",
    "Remove Brackets and Content",
    "Remove Brackets: Block",
    "Remove Brackets: Indented Block"
)


class BhRemoveBracketsCommand(sublime_plugin.WindowCommand):
    """
    Command to remove current highlighted brackets and optionally content
    """

    def remove_brackets(self, value):
        """
        Perform removal of brackets
        """

        if value != -1:
            menu_item = MENU[value]
            indent = menu_item == MENU.block_indent
            block = menu_item == MENU.block or menu_item == MENU.block_indent
            content = menu_item == MENU.content

            self.window.run_command(
                "bh_key",
                {
                    "plugin": {
                        "type": ["__all__"],
                        "command": "bh_modules.bracketremove",
                        "args": {
                            "remove_indent": indent,
                            "remove_block": block,
                            "remove_content": content
                        }
                    }
                }
            )

    def run(self):
        """
        Show menu of removal options
        """

        self.window.show_quick_panel(
            list(MENU),
            self.remove_brackets
        )

########NEW FILE########
__FILENAME__ = bh_swapping
import sublime
import sublime_plugin
import bh_wrapping


class SwapBrackets(bh_wrapping.WrapBrackets):
    def wrap(self, wrap_entry):
        if wrap_entry < 0:
            return

        self._style = ["inline"]

        self.brackets = self._brackets[wrap_entry]
        self.wrap_brackets(0)


class SwapBracketsCommand(sublime_plugin.WindowCommand):
    def finalize(self, callback):
        if self.view is not None:
            if not self.view.settings().get("BracketHighlighterBusy", False):
                callback()
            else:
                sublime.set_timeout(lambda: self.finalize(callback), 100)

    def swap_brackets(self, value):
        if value < 0:
            return

        self.brackets = self.wrap._brackets[value]

        self.window.run_command(
            "bh_key",
            {
                "plugin": {
                    "type": ["__all__"],
                    "command": "bh_modules.swapbrackets"
                }
            }
        )

        self.view = self.window.active_view()

        sublime.set_timeout(lambda: self.finalize(lambda: self.wrap.wrap(value)), 100)

    def run(self):
        view = self.window.active_view()
        if view is None:
            return
        self.wrap = SwapBrackets(view, "bh_swapping.sublime-settings", "swapping")

        if len(self.wrap._menu):
            self.window.show_quick_panel(
                self.wrap._menu,
                self.swap_brackets
            )

########NEW FILE########
__FILENAME__ = bh_wrapping
import sublime
import sublime_plugin
from os.path import basename
import re


BH_TABSTOPS = re.compile(r"(\$\{BH_(SEL|TAB)(?:\:([^\}]+))?\})")
TAB_REGION = "bh_plugin_wrapping_tabstop"
SEL_REGION = "bh_plugin_wrapping_select"
OUT_REGION = "bh_plugin_wrapping_outlier"

VALID_INSERT_STYLES = (
    ("inline", "Inline Insert"),
    ("block", "Block Insert"),
    ("indent_block", "Indented Block Insert")
)


def exclude_entry(enabled, filter_type, language_list, language):
    """
    Exclude bracket wrapping entry by filter
    """

    exclude = True
    if enabled:
        # Black list languages
        if filter_type == 'blacklist':
            exclude = False
            if language != None:
                for item in language_list:
                    if language == item.lower():
                        exclude = True
                        break
        #White list languages
        elif filter_type == 'whitelist':
            if language != None:
                for item in language_list:
                    if language == item.lower():
                        exclude = False
                        break
    return exclude


class TextInsertion(object):
    """
    Wrapper class for inserting text
    """

    def __init__(self, view, edit):
        """
        Store view and edit objects
        """

        self.view = view
        self.edit = edit

    def insert(self, pt, text):
        """
        Peform insertion
        """

        return self.view.insert(self.edit, pt, text)


class WrapBrackets(object):
    """
    Wrap the current selection(s) with the defined wrapping options
    """

    def __init__(self, view, setting_file, attribute):
        self.view = view
        self._menu = []
        self._brackets = []
        self._insert = []
        self._style = []
        self.read_wrap_entries(setting_file, attribute)

    def inline(self, edit, sel):
        """
        Inline wrap
        """

        ti = TextInsertion(self.view, edit)

        offset1 = ti.insert(sel.begin(), self.brackets[0])
        self.insert_regions.append(sublime.Region(sel.begin(), sel.begin() + offset1))
        offset2 = ti.insert(sel.end() + offset1, self.brackets[1])
        self.insert_regions.append(sublime.Region(sel.end() + offset1, sel.end() + offset1 + offset2))

    def block(self, edit, sel, indent=False):
        """
        Wrap brackets around selection and block off the content
        """

        # Calculate number of lines between brackets
        self.calculate_lines(sel)
        # Calculate the current indentation of first bracket
        self.calculate_indentation(sel)

        ti = TextInsertion(self.view, edit)

        line_offset = 0
        first_end = 0
        second_end = 0
        second_start = sel.end()

        for b in reversed(self.brackets[1].split('\n')):
            second_end += ti.insert(sel.end(), "\n" + self.indent_to_col + b)
        num_open_lines = self.brackets[0].count('\n')
        for b in reversed(self.brackets[0].split('\n')):
            if line_offset == num_open_lines:
                line = b + "\n"
            else:
                line = self.indent_to_col + b + "\n"
            first_end += ti.insert(sel.begin(), line)
            line_offset += 1
        self.insert_regions.append(sublime.Region(sel.begin(), sel.begin() + first_end))

        if indent:
            second_start += self.indent_content(ti, line_offset)
        else:
            pt = self.view.text_point(self.first_line + line_offset, 0)
            second_start += ti.insert(pt, self.indent_to_col)

        self.insert_regions.append(sublime.Region(first_end + second_start, first_end + second_start + second_end))

    def indent_content(self, ti, line_offset):
        """
        Indent the block content
        """

        first = True
        offset = 0
        for l in range(line_offset, self.total_lines + line_offset):
            pt = self.view.text_point(self.first_line + l, 0)
            if first:
                offset += ti.insert(pt, self.indent_to_col + "\t")
                first = False
            else:
                offset += ti.insert(pt, "\t")
        return offset

    def calculate_lines(self, sel):
        """
        Calculate lines between brackets
        """

        self.first_line, self.col_position = self.view.rowcol(sel.begin())
        last_line = self.view.rowcol(sel.end())[0]
        self.total_lines = last_line - self.first_line + 1

    def calculate_indentation(self, sel):
        """
        Calculate how much lines should be indented
        """

        tab_size = self.view.settings().get("tab_size", 4)
        tab_count = self.view.substr(sublime.Region(sel.begin() - self.col_position, sel.begin())).count('\t')
        spaces = self.col_position - tab_count
        self.indent_to_col = "\t" * tab_count + "\t" * (spaces / tab_size) + " " * (spaces % tab_size if spaces >= tab_size else spaces)

    def select(self, edit):
        """
        Select defined regions after wrapping
        """

        self.view.sel().clear()
        map(lambda x: self.view.sel().add(x), self.insert_regions)

        final_sel = []
        initial_sel = []
        for s in self.view.sel():
            string = self.view.substr(s)
            matches = [m for m in BH_TABSTOPS.finditer(string)]
            multi_offset = 0
            if matches:
                for m in matches:
                    r = sublime.Region(s.begin() + multi_offset + m.start(1), s.begin() + multi_offset + m.end(1))
                    if m.group(3):
                        replace = m.group(3)
                        self.view.erase(edit, r)
                        added = self.view.insert(edit, r.begin(), replace)
                        final_sel.append(sublime.Region(s.begin() + multi_offset + m.start(1), s.begin() + multi_offset + m.start(1) + added))
                        multi_offset += added - r.size()
                    else:
                        self.view.erase(edit, r)
                        final_sel.append(sublime.Region(s.begin() + multi_offset + m.start(1)))
                        multi_offset -= r.size()
                    if m.group(2) == "SEL":
                        initial_sel.append(final_sel[-1])

        if len(initial_sel) != len(final_sel):
            self.view.add_regions(TAB_REGION, final_sel, "", "", sublime.HIDDEN)

        # Re-position cursor
        self.view.sel().clear()
        if len(initial_sel):
            map(lambda x: self.view.sel().add(x), initial_sel)
        elif len(final_sel):
            self.view.sel().add(final_sel[0])

    def read_wrap_entries(self, setting_file, attribute):
        """
        Read wrap entries from the settings file
        """

        settings = sublime.load_settings(setting_file)
        syntax = self.view.settings().get('syntax')
        language = basename(syntax).replace('.tmLanguage', '').lower() if syntax != None else "plain text"
        wrapping = settings.get(attribute, [])
        for i in wrapping:
            if not exclude_entry(i["enabled"], i["language_filter"], i["language_list"], language):
                for j in i.get("entries", []):
                    try:
                        menu_entry = j["name"]
                        bracket_entry = j["brackets"]
                        insert_style = j.get("insert_style", ["inline"])
                        self._menu.append(menu_entry)
                        self._brackets.append(bracket_entry)
                        self._insert.append(insert_style)
                    except Exception:
                        pass

    def wrap_brackets(self, value):
        """
        Wrap selection(s) with defined brackets
        """

        if value < 0:
            return

        # Use new edit object since the main run has already exited
        # and the old edit is more than likely closed now
        edit = self.view.begin_edit()

        # Wrap selections with brackets
        style = self._style[value]
        self.insert_regions = []

        for sel in self.view.sel():
            # Determine indentation style
            if style == "indent_block":
                self.block(edit, sel, True)
            elif style == "block":
                self.block(edit, sel)
            else:
                self.inline(edit, sel)

        self.select(edit)

        self.view.end_edit(edit)

    def wrap_style(self, value):
        """
        Choose insert style for wrapping.
        """

        if value < 0:
            return

        style = []

        self.brackets = self._brackets[value]
        for s in VALID_INSERT_STYLES:
            if s[0] in self._insert[value]:
                self._style.append(s[0])
                style.append(s[1])

        if len(style) > 1:
            self.view.window().show_quick_panel(
                style,
                self.wrap_brackets
            )
        else:
            self.wrap_brackets(0)


class WrapBracketsCommand(sublime_plugin.TextCommand, WrapBrackets):
    def run(self, edit):
        """
        Display the wrapping menu
        """

        self._menu = []
        self._brackets = []
        self._insert = []
        self._style = []
        self.read_wrap_entries("bh_wrapping.sublime-settings", "wrapping")

        if len(self._menu):
            self.view.window().show_quick_panel(
                self._menu,
                self.wrap_style
            )


class BhNextWrapSelCommand(sublime_plugin.TextCommand):
    """
    Navigate wrapping tab stop regions
    """

    def run(self, edit):
        """
        Look for the next wrapping tab stop region
        """

        regions = self.view.get_regions(SEL_REGION) + self.view.get_regions(OUT_REGION)
        if len(regions):
            self.view.sel().clear()
            map(lambda x: self.view.sel().add(x), regions)

        # Clean up unneed sections
        self.view.erase_regions(SEL_REGION)
        self.view.erase_regions(OUT_REGION)


class BhWrapListener(sublime_plugin.EventListener):
    """
    Listen for wrapping tab stop tabbing
    """

    def on_query_context(self, view, key, operator, operand, match_all):
        """
        Mark the next regions to navigate to.
        """

        accept_query = False
        if key == "bh_wrapping":
            select = []
            outlier = []
            regions = view.get_regions(TAB_REGION)
            tabstop = []
            sels = view.sel()

            if len(regions) == 0:
                return False

            for s in sels:
                count = 0
                found = False
                for r in regions[:]:
                    if found:
                        select.append(r)
                        tabstop.append(r)
                        del regions[count]
                        break
                    if r.begin() <= s.begin() <= r.end():
                        del regions[count]
                        found = True
                        continue
                    count += 1
                if not found:
                    outlier.append(s)
            tabstop += regions

            if len(tabstop) == len(select):
                if len(tabstop):
                    tabstop = []
                    accept_query = True
            elif len(tabstop) != 0:
                accept_query = True

            # Mark regions to make the "next" command aware of what to do
            view.add_regions(SEL_REGION, select, "", "", sublime.HIDDEN)
            view.add_regions(OUT_REGION, outlier, "", "", sublime.HIDDEN)
            view.add_regions(TAB_REGION, tabstop, "", "", sublime.HIDDEN)

        return accept_query

########NEW FILE########
__FILENAME__ = ure
"""
ure - unicode re

A simple script that wraps the re interface with methods to handle unicode properties.
Patterns will all have re.UNICODE enabled and unicode property formats will be replaced
with the unicode characters in that category.

Example:
r"\p{Ll}\p{Lu}"

Licensed under MIT
Copyright (c) 2013 Isaac Muse <isaacmuse@gmail.com>
"""
import re
import sys
from os.path import exists, join
try:
    import unicodedata
except:
    from os.path import dirname
    sys.path.append(dirname(sys.executable))
    import unicodedata
try:
    import cpickle as pickle
except:
    import pickle
from os import unlink
PY3 = sys.version_info[0] >= 3
uchr = chr if PY3 else unichr

DEBUG = re.DEBUG
I = re.I
IGNORECASE = re.IGNORECASE
L = re.L
LOCALE = re.LOCALE
M = re.M
MULTILINE = re.MULTILINE
S = re.S
DOTALL = re.DOTALL
U = re.U
UNICODE = re.UNICODE
X = re.X
VERBOSE = re.VERBOSE
escape = re.escape
purge = re.purge

_unicode_properties = None
_unicode_key_pattern = None
_loaded = False
if "_use_cache" not in globals():
    _use_cache = None
    _cache_prefix = ""


def set_cache_directory(pth, prefix=""):
    """
    Set cache path
    """
    global _use_cache
    global _cache_prefix
    if exists(pth):
        _use_cache = pth
        _cache_prefix = prefix


def _build_unicode_property_table(unicode_range):
    """
    Build property table for unicode range.
    """
    table = {}
    p = None
    for i in range(*unicode_range):
        try:
            c = uchr(i)
            p = unicodedata.category(c)
        except:
            continue
        if p[0] not in table:
            table[p[0]] = {}
        if p[1] not in table[p[0]]:
            table[p[0]][p[1]] = []
        table[p[0]][p[1]].append(c)

    # Join as one string
    for k1, v1 in table.items():
        for k2, v2 in v1.items():
            v1[k2] = ''.join(v2)

    return table


def _build_unicode_key_pattern():
    """
    Build regex key pattern
    """
    unicode_prop = r"\p\{(%s)\}"
    unicode_keys = []
    for k1, v1 in _unicode_properties.items():
        unicode_keys.append("%s(?:%s)" % (k1, "|".join(v1.keys())))
    return re.compile(unicode_prop % "|".join(unicode_keys), re.UNICODE)


def _init_unicode():
    """
    Prepare unicode property tables and key pattern
    """
    global _loaded
    global _unicode_properties
    global _unicode_key_pattern
    if _use_cache is not None:
        props = join(_use_cache, "%s_unicode_properties.cache" % _cache_prefix)
        if (not exists(join(_use_cache, "%s_unicode_properties.cache" % _cache_prefix))):
            _unicode_properties = _build_unicode_property_table((0x0000, 0x10FFFF))
            _unicode_key_pattern = _build_unicode_key_pattern()

            try:
                with open(props, 'wb') as f:
                    pickle.dump(_unicode_key_pattern, f)
                    pickle.dump(_unicode_properties, f)
            except Exception as e:
                if exists(props):
                    unlink(props)
        else:
            try:
                with open(props, 'rb') as f:
                    _unicode_key_pattern = pickle.load(f)
                    _unicode_properties = pickle.load(f)
            except Exception as e:
                if exists(props):
                    unlink(props)
                _unicode_properties = _build_unicode_property_table((0x0000, 0x10FFFF))
                _unicode_key_pattern = _build_unicode_key_pattern()
    else:
        _unicode_properties = _build_unicode_property_table((0x0000, 0x10FFFF))
        _unicode_key_pattern = _build_unicode_key_pattern()

    _loaded = True


def find_char_groups(s):
    """
    Find character groups
    """
    pos = 0
    groups = []
    escaped = False
    found = False
    first = None
    for c in s:
        if c == "\\":
            escaped = not escaped
        elif escaped:
            escaped = False
        elif c == "[" and not found:
            found = True
            first = pos
        elif c == "]" and found:
            groups.append((first, pos))
        pos += 1
    return groups


def get_unicode_category(prop):
    """
    Retrieve the unicode category from the table
    """
    p1, p2 = (prop[0], prop[1]) if len(prop) > 1 else (prop[0], None)
    return ''.join([x for x in _unicode_properties[p1].values()]) if p2 is None else _unicode_properties[p1][p2]


def parse_unicode_properties(re_pattern):
    """
    Replaces regex property notation with unicode values
    """

    # Init unicode table if it has not already been initialized
    global _loaded
    if not _loaded:
        _init_unicode()

    char_groups = find_char_groups(re_pattern)
    ure_pattern = re_pattern
    for p in reversed(list(_unicode_key_pattern.finditer(re_pattern))):
        v = get_unicode_category(p.group(1))
        brackets = True
        if v is None:
            continue
        for g in char_groups:
            if p.start(0) >= g[0] and p.end(0) <= g[1]:
                brackets = False
                break
        if brackets:
            v = "[" + v + "]"
        ure_pattern = ure_pattern[:p.start(0) - 1] + v + ure_pattern[p.end(0): len(ure_pattern)]
    return ure_pattern


def compile(pattern, flags=0):
    """
    compile after parsing unicode properties and set flag to unicode
    """
    return re.compile(parse_unicode_properties(pattern), flags | re.UNICODE)


def search(pattern, string, flags=0):
    """
    search after parsing unicode properties and set flag to unicode
    """
    re.search(parse_unicode_properties(pattern), string, flags | re.UNICODE)


def match(pattern, string, flags=0):
    """
    match after parsing unicode properties and set flag to unicode
    """
    re.match(parse_unicode_properties(pattern), string, flags | re.UNICODE)


def split(pattern, string, maxsplit=0, flags=0):
    """
    split after parsing unicode properties and set flag to unicode
    """
    re.split(parse_unicode_properties(pattern), string, maxsplit, flags | re.UNICODE)


def findall(pattern, string, flags=0):
    """
    findall after parsing unicode properties and set flag to unicode
    """
    re.findall(parse_unicode_properties(pattern), string, flags | re.UNICODE)


def finditer(pattern, string, flags=0):
    """
    finditer after parsing unicode properties and set flag to unicode
    """
    re.finditer(parse_unicode_properties(pattern), string, flags | re.UNICODE)


def sub(pattern, repl, string, count=0, flags=0):
    """
    sub after parsing unicode properties and set flag to unicode
    """
    re.sub(parse_unicode_properties(pattern), repl, string, count, flags | re.UNICODE)


def subn(pattern, repl, string, count=0, flags=0):
    """
    subn after parsing unicode properties and set flag to unicode
    """
    re.subn(parse_unicode_properties(pattern), repl, string, flags | re.UNICODE)


# _init_unicode()

if __name__ == "__main__":
    from os.path import dirname, abspath
    print(__file__)
    set_cache_directory(dirname(abspath(__file__)), "test")
    print("Testing ure's unicode properties replacement")
    print(parse_unicode_properties(r"\p{Ll}"))

########NEW FILE########
