__FILENAME__ = add_code_block
#!/usr/bin/python
import re
import sublime
import sublime_plugin


# __all__ = [
#     'HayakuAddCodeBlockCommand',
#     'HayakuExpandCodeBlockCommand',
# ]

# Guessing the codestyle             1     2    3            4    5         6    7     8    9
GUESS_REGEX = re.compile(r'selector(\s*)(\{)?(\s*)property(:)?(\s*)value(;)?(\s*)(\})?(\s*)', re.IGNORECASE)


def get_hayaku_options(self):
    settings = self.view.settings()
    options = {}
    match = {}
    # Autoguessing the options
    if settings.get("hayaku_CSS_syntax_autoguess"):
        autoguess = settings.get("hayaku_CSS_syntax_autoguess")
        offset = len(autoguess[0]) - len(autoguess[0].lstrip())
        autoguess = [ s[offset:].rstrip() for s in autoguess]

        match = GUESS_REGEX.search('\n'.join(autoguess))

    # Helper to set an option got from multiple sources
    def get_setting(setting, fallback, match_group = False):
        if match_group and match:
            fallback = match.group(match_group)
        single_setting = False
        if settings.has("hayaku_" + setting):
            single_setting = settings.get("hayaku_" + setting, fallback)
        options[setting] = single_setting or fallback

    # Some hardcode for different scopes
    # (could this be defined better?)
    scope_name = self.view.scope_name(self.view.sel()[0].a)
    is_sass = sublime.score_selector(scope_name, 'source.sass') > 0
    is_stylus = sublime.score_selector(scope_name, 'source.stylus') > 0

    disable_braces = is_stylus or is_sass
    if is_stylus and match and match.group(2) and match.group(8):
        disable_braces = False

    disable_colons = is_stylus
    if match and match.group(4):
        disable_colons = False

    disable_semicolons = is_stylus or is_sass
    if is_stylus and match and match.group(6):
        disable_semicolons = False

    # Calling helper, getting all the needed options
    get_setting("CSS_whitespace_block_start_before", " ",    1 )
    get_setting("CSS_whitespace_block_start_after",  "\n\t", 3 )
    get_setting("CSS_whitespace_block_end_before",   "\n",   7 )
    get_setting("CSS_whitespace_block_end_after",    "",     9 )
    get_setting("CSS_whitespace_after_colon",        " ",    5 )
    get_setting("CSS_newline_after_expand",          False)
    get_setting("CSS_syntax_no_curly_braces",        disable_braces )
    get_setting("CSS_syntax_no_colons",              disable_colons )
    get_setting("CSS_syntax_no_semicolons",          disable_semicolons )
    get_setting("CSS_syntax_url_quotes",             (is_stylus or is_sass)     )
    get_setting("CSS_syntax_quote_symbol",           "\""      )  # or "'"
    get_setting("CSS_prefixes_disable",              False     )
    get_setting("CSS_prefixes_align",                not (is_stylus or is_sass) )
    get_setting("CSS_prefixes_only",                 []        )
    get_setting("CSS_prefixes_no_unprefixed",        False     )
    get_setting("CSS_disable_postexpand",            False     )
    get_setting("CSS_units_for_unitless_numbers",    False      )
    get_setting("CSS_colors_case",                   "uppercase" ) # or "lowercase" or "initial"
    get_setting("CSS_colors_length",                 "short"   )   # or "long"      or "initial"
    get_setting("CSS_clipboard_defaults",            ["colors","images"] )

    return options

def hayaku_get_block_snippet(options, inside = False):
    start_before = options["CSS_whitespace_block_start_before"]
    start_after = options["CSS_whitespace_block_start_after"]
    end_before = options["CSS_whitespace_block_end_before"]
    end_after = options["CSS_whitespace_block_end_after"]
    opening_brace = "{"
    closing_brace = "}"

    if options["CSS_syntax_no_curly_braces"]:
        opening_brace = ""
        closing_brace = ""
        if '\n' in start_before:
            start_after = ""
        end_after = ""

    if inside:
        opening_brace = ""
        closing_brace = ""
        start_before = ""
        end_after = ""

    return ''.join([
          start_before
        , opening_brace
        , start_after
        , "$0"
        , end_before
        , closing_brace
        , end_after
    ])

# Command
class HayakuExpandCodeBlockCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # TODO: consume the braces and whitespaces around and inside
        self.view.run_command("insert_snippet", {"contents": hayaku_get_block_snippet(get_hayaku_options(self),True)})

class HayakuAddCodeBlockCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        result = '/* OVERRIDE ME */'

        # Determine the limits for place searching
        regions = self.view.sel()
        region = regions[0]
        line = self.view.line(region)
        stop_point = self.view.find('[}]\s*',line.begin())
        if stop_point is not None and not (-1, -1):
            end = stop_point.end()
        else:
            end = self.view.find('[^}]*',line.begin()).end()
        where_to_search = self.view.substr(
            sublime.Region(
                line.begin(),
                end
            )
        )

        options = get_hayaku_options(self)

        # Insert a code block if we must
        found_insert_position = re.search('^([^}{]*?[^;,}{\s])\s*(?=\n|$)',where_to_search)
        if found_insert_position is not None:
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(len(found_insert_position.group(1)) + line.begin(), len(found_insert_position.group(1)) + line.begin()))

            result = hayaku_get_block_snippet(options)
        else:
            # Place a caret + create a new line otherwise
            # FIXME: the newline is not perfectly inserted. Must rethink it so there wouldn't
            # be replacement of all whitespaces and would be better insertion handling
            found_insert_rule = re.search('^(([^}]*?[^;]?)\s*)(?=\})',where_to_search)
            if found_insert_rule:
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(len(found_insert_rule.group(2)) + line.begin(), len(found_insert_rule.group(1)) + line.begin()))

                result = ''.join([
                      options["CSS_whitespace_block_start_after"]
                    , "$0"
                    , options["CSS_whitespace_block_end_before"]
                ])

        self.view.run_command("insert_snippet", {"contents": result})

########NEW FILE########
__FILENAME__ = contexts
#!/usr/bin/python
import re
import sublime
import sublime_plugin

REGEX_WHITESPACES = re.compile(r'^\s*$')

class HayakuSingleCaretContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_single_caret":
            return None

        # Multiple blocks inserting doesn't make sense
        if len(view.sel()) > 1:
            return None

        # TODO: understand selection, but don't replace it on code block inserting
        if not view.sel()[0].empty():
            return None

        return True

class HayakuAtCssContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_at_css":
            return None

        # Looking for the scope
        if not view.score_selector(view.sel()[0].begin(),'source.css, source.stylus, source.sass, source.scss, source.less'):
            return None

        return True

class HayakuAddCodeBlockContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_add_code_block":
            return None

        # Determining the left and the right parts
        region = view.sel()[0]
        line = view.line(region)
        left_part = view.substr(sublime.Region(line.begin(), region.begin()))
        right_part = view.substr(sublime.Region(region.begin(), line.end()))

        # Check if the line isn't just a line of whitespace
        if REGEX_WHITESPACES.search(left_part + right_part) is not None:
            return None
        # Simple check if the left part is ok
        if left_part.find(';') != -1:
            return None
        # Simple check if the right part is ok
        if right_part.find(';') != -1:
            return None

        return True

class HayakuAddLineContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_add_line":
            return None

        # Determining the left and the right parts
        region = view.sel()[0]
        line = view.line(region)
        left_part = view.substr(sublime.Region(line.begin(), region.begin()))
        right_part = view.substr(sublime.Region(region.begin(), line.end()))

        # Simple check if the left part is ok
        if re.search(';\s*$|[^\s;\{] [^;\{]+$',left_part) is None:
            return None

        # Simple check if the right part is ok
        if re.search('^\s*\}?$',right_part) is None:
            return None

        return True


class HayakuStyleContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_css_context":
            return None

        regions = view.sel()
        # We won't do anything for multiple carets for now
        if len(regions) > 1:
            return None

        region = regions[0]

        # We don't do anything for selection for now
        if not region.empty():
            return None

        # Looking for the scope
        # TODO: Make it expandable in HTML's attributes (+ left/right fixes)
        if view.score_selector(region.begin(),'source.css -meta.selector.css, source.stylus, source.sass, source.scss, source.less') == 0:
            return None

        # Determining the left and the right parts
        line = view.line(region)
        left_part = view.substr(sublime.Region(line.begin(), region.begin()))
        right_part = view.substr(sublime.Region(region.begin(),line.end()))

        # Simple check if the left part is ok
        # 1. Caret is not straight after semicolon, slash or plus sign
        # 2. We're not at the empty line
        # 3. There were no property/value like entities before caret
        #                  1      2         3
        if re.search('[;\s\/\+]$|^$|[^\s;\{] [^;\{]+$',left_part) is not None:
            return None

        # Simple check if the right part is ok
        # 1. The next symbol after caret is not space or curly brace
        # 2. There could be only full property+value part afterwards
        #                 1           2
        if re.search('^[^\s\}]|^\s[^:\}]+[;\}]',right_part) is not None:
            return None

        return True

# Context-commands to jump out of multiple selections in snippets
class HayakuGoingUpContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_going_up":
            return None
        if len(view.sel()) > 1:
            region = view.sel()[0]
            view.sel().clear()
            view.sel().add(region)
        return None

class HayakuGoingDownContext(sublime_plugin.EventListener):
    def on_query_context(self, view, key, *args):
        if key != "hayaku_going_down":
            return None
        if len(view.sel()) > 1:
            region = view.sel()[1]
            view.sel().clear()
            view.sel().add(region)
        return None

########NEW FILE########
__FILENAME__ = css_dict_driver
# -*- coding: utf-8 -*-
# (c) 2012 Sergey Mezentsev
import string

from itertools import chain, product, starmap


def parse_dict_json(raw_dict):
    result_dict = {}

    valuable = (i for i in raw_dict if 'name' in i and 'values' in i)

    def strip(s):
        return string.strip(s) if hasattr(string, 'strip') else s.strip()

    for i in valuable:
        name, values, default = i['name'], i['values'], i.get('default')
        names = name if isinstance(name, list) else map(strip, name.split(','))
        for n in names:
            assert n not in result_dict

            val = { 'values': values }

            if default is not None:
                val['default'] = default

            if 'prefixes' in i:
                val['prefixes'] = i['prefixes']
                if 'no-unprefixed-property' in i:
                    val['no-unprefixed-property'] = i['no-unprefixed-property']
            else:
                assert 'no-unprefixed-property' not in i

            result_dict[n] = val

    return result_dict

get_css_dict_cache = None
def get_css_dict():
    global get_css_dict_cache
    if get_css_dict_cache is not None:
        return get_css_dict_cache
    else:
        CSS_DICT_DIR = 'dictionaries'
        CSS_DICT_FILENAME = 'hayaku_CSS_dictionary.json'
        DICT_KEY = 'hayaku_CSS_dictionary'

        import json
        import os
        try:
            import sublime
            css_dict = sublime.load_settings(CSS_DICT_FILENAME).get(DICT_KEY)
            if css_dict is None:
                import zipfile
                zf = zipfile.ZipFile(os.path.dirname(os.path.realpath(__file__)))
                f = zf.read('{0}/{1}'.format(CSS_DICT_DIR, CSS_DICT_FILENAME))
                css_dict = json.loads(f.decode())[DICT_KEY]
        except ImportError:
            css_dict_path = os.path.join(CSS_DICT_DIR, CSS_DICT_FILENAME)
            css_dict = json.load(open(css_dict_path))[DICT_KEY]

        assert css_dict is not None
        get_css_dict_cache = parse_dict_json(css_dict)
        return get_css_dict_cache

def css_defaults(name, css_dict):
    """Находит первое значение по-умолчанию
    background -> #FFF
    color -> #FFF
    content -> ""
    """
    cur = css_dict.get(name) or css_dict.get(name[1:-1])
    if cur is None:
        return None
    default = cur.get('default')
    if default is not None:
        return default

    for v in cur['values']:
        if v.startswith('<') and v.endswith('>'):
            ret = css_defaults(v, css_dict)
            if ret is not None:
                return ret

def css_flat(name, values=None, css_dict=None):
    """Все значения у свойства (по порядку)
    left -> [u'auto', u'<dimension>', u'<number>', u'<length>', u'.em', u'.ex',
            u'.vw', u'.vh', u'.vmin', u'.vmax', u'.ch', u'.rem', u'.px', u'.cm',
            u'.mm', u'.in', u'.pt', u'.pc', u'<percentage>', u'.%']
    """
    cur = css_dict.get(name) or css_dict.get(name[1:-1])
    if values is None:
        values = []
    if cur is None:
        return values
    for value in cur['values']:
        values.append(value)
        if value.startswith('<') and value.endswith('>'):
            values = css_flat(value, values, css_dict)
    return values

def css_flat_list(name, css_dict):
    """Возвращает список кортежей (свойство, возможное значение)
    left -> [(left, auto), (left, <integer>), (left, .px)...]
    """
    return list(product((name,), css_flat(name, css_dict=get_css_dict())))

def get_flat_css():
    return list(chain.from_iterable(starmap(css_flat_list, ((i, get_css_dict()) for i in get_css_dict()))))

########NEW FILE########
__FILENAME__ = hayaku
# -*- coding: utf-8 -*-
import os
import re

from itertools import chain, product

import sublime
import sublime_plugin

def import_dir(name, fromlist=()):
    PACKAGE_EXT = '.sublime-package'
    dirname = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    if dirname.endswith(PACKAGE_EXT):
        dirname = dirname[:-len(PACKAGE_EXT)]
    return __import__('{0}.{1}'.format(dirname, name), fromlist=fromlist)


try:
    extract = import_dir('probe', ('extract',)).extract
except ImportError:
    from probe import extract

try:
    make_template = import_dir('templates', ('make_template',)).make_template
except ImportError:
    from templates import make_template

try:
    parse_dict_json = import_dir('css_dict_driver', ('parse_dict_json',)).parse_dict_json
except ImportError:
    from css_dict_driver import parse_dict_json

try:
    get_hayaku_options = import_dir('add_code_block', ('add_code_block',)).get_hayaku_options
except ImportError:
    from add_code_block import get_hayaku_options


# The maximum size of a single propery to limit the lookbehind
MAX_SIZE_CSS = len('-webkit-transition-timing-function')

ABBR_REGEX = re.compile(r'[\s|;|{]([\.:%#a-z-,\d]+!?)$', re.IGNORECASE)




class HayakuCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        cur_pos = self.view.sel()[0].begin()
        start_pos = cur_pos - MAX_SIZE_CSS
        if start_pos < 0:
            start_pos = 0
        # TODO: Move this to the contexts, it's not needed here
        probably_abbr = self.view.substr(sublime.Region(start_pos, cur_pos))
        match = ABBR_REGEX.search(probably_abbr)
        if match is None:
            self.view.insert(edit, cur_pos, '\t')
            return

        abbr = match.group(1)

        # Extracting the data from the abbr
        args = extract(abbr)

        if not args:
            return

        # Getting the options and making a snippet
        # from the extracted data
        get_hayaku_options(self)
        options = get_hayaku_options(self)
        template = make_template(args, options)

        if template is None:
            return

        # Inserting the snippet
        new_cur_pos = cur_pos - len(abbr)
        assert cur_pos - len(abbr) >= 0
        self.view.erase(edit, sublime.Region(new_cur_pos, cur_pos))

        self.view.run_command("insert_snippet", {"contents": template})


# Helpers for getting the right indent for the Add Line Command
WHITE_SPACE_FINDER = re.compile(r'^(\s*)(-)?[\w]*')
def get_line_indent(line):
    return WHITE_SPACE_FINDER.match(line).group(1)

def is_prefixed_property(line):
    return WHITE_SPACE_FINDER.match(line).group(2) is not None

def get_previous_line(view, line_region):
    return view.line(line_region.a - 1)

def get_nearest_indent(view):
    line_region = view.line(view.sel()[0])
    line = view.substr(line_region)
    line_prev_region = get_previous_line(view,line_region)

    found_indent = None
    first_indent = None
    first_is_ok = True
    is_nested = False

    # Can we do smth with all those if-else noodles?
    if not is_prefixed_property(line):
        first_indent = get_line_indent(line)
        if not is_prefixed_property(view.substr(line_prev_region)):
            return first_indent
        if is_prefixed_property(view.substr(line_prev_region)):
            first_is_ok = False
    while not found_indent and line_prev_region != view.line(sublime.Region(0)):
        line_prev = view.substr(line_prev_region)
        if not first_indent:
            if not is_prefixed_property(line_prev):
                first_indent = get_line_indent(line_prev)
                if is_prefixed_property(view.substr(get_previous_line(view,line_prev_region))):
                    first_is_ok = False
        else:
            if not is_prefixed_property(line_prev) and not is_prefixed_property(view.substr(get_previous_line(view,line_prev_region))):
                found_indent = min(first_indent,get_line_indent(line_prev))

        line_prev_region = get_previous_line(view,line_prev_region)
        if line_prev.count("{"):
            is_nested = True

    if found_indent and found_indent < first_indent and not is_prefixed_property(view.substr(get_previous_line(view,line_region))) and first_is_ok or is_nested:
        found_indent = found_indent + "    "

    if not found_indent:
        if first_indent:
            found_indent = first_indent
        else:
            found_indent = ""
    return found_indent

class HayakuAddLineCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        nearest_indent = get_nearest_indent(self.view)

        # Saving current auto_indent setting
        # This hack fixes ST2's bug with incorrect auto_indent for snippets
        # It seems that with auto indent off it uses right auto_indent there lol.
        current_auto_indent = self.view.settings().get("auto_indent")
        self.view.settings().set("auto_indent",False)

        self.view.run_command('insert', {"characters": "\n"})
        self.view.erase(edit, sublime.Region(self.view.line(self.view.sel()[0]).a, self.view.sel()[0].a))
        self.view.run_command('insert', {"characters": nearest_indent})
        self.view.settings().set("auto_indent",current_auto_indent)

########NEW FILE########
__FILENAME__ = probe
# -*- coding: utf-8 -*-
# (c) 2012 Sergey Mezentsev
import os
import re
from itertools import product, chain

def import_dir(name, fromlist=()):
    PACKAGE_EXT = '.sublime-package'
    dirname = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    if dirname.endswith(PACKAGE_EXT):
        dirname = dirname[:-len(PACKAGE_EXT)]
    return __import__('{0}.{1}'.format(dirname, name), fromlist=fromlist)


try:
    imp = import_dir('css_dict_driver', ('css_defaults', 'get_css_dict', 'get_flat_css', 'css_flat_list'))
    css_defaults = imp.css_defaults
    get_css_dict = imp.get_css_dict
    get_flat_css = imp.get_flat_css
    css_flat_list = imp.css_flat_list
except ImportError:
    from css_dict_driver import css_defaults, get_css_dict, get_flat_css, css_flat_list

# TODO: Move this to dicts etc.
PRIORITY_PROPERTIES = [ 'display', 'color', 'margin', 'position', 'padding', 'width', 'background', 'zoom', 'height', 'top', 'vertical-align', 'overflow', 'left', 'margin-right', 'float', 'margin-left', 'cursor', 'text-decoration', 'font-size', 'margin-top', 'border', 'background-position', 'font', 'margin-bottom', 'padding-left', 'right', 'padding-right', 'line-height', 'white-space', 'text-align', 'border-color', 'padding-top', 'z-index', 'border-bottom', 'visibility', 'border-radius', 'padding-bottom', 'font-weight', 'clear', 'max-width', 'border-top', 'border-width', 'content', 'bottom', 'background-color', 'opacity', 'background-image', 'box-shadow', 'border-collapse', 'text-overflow', 'filter', 'border-right', 'text-indent', 'clip', 'min-width', 'min-height', 'border-left', 'max-height', 'border-right-color', 'border-top-color', 'transition', 'resize', 'overflow-x', 'list-style', 'word-wrap', 'border-left-color', 'word-spacing', 'background-repeat', 'user-select', 'border-bottom-color', 'box-sizing', 'border-top-left-radius', 'font-family', 'border-bottom-width', 'outline', 'border-bottom-right-radius', 'border-right-width', 'border-top-width', 'font-style', 'text-transform', 'border-bottom-left-radius', 'border-left-width', 'border-spacing', 'border-style', 'border-top-right-radius', 'text-shadow', 'border-image', 'overflow-y', 'table-layout', 'background-size', 'behavior', 'body', 'name', 'letter-spacing', 'background-clip', 'pointer-events', 'transform', 'counter-reset', ]

# __all__ = [
#     'extract',
# ]

STATIC_ABBR = dict([
    ('b', 'bottom'), # Sides consistency
    ('ba', 'background'), # Instead of background-attachment
    ('bg', 'background'), # Instead of background: linear-gradient
    ('bd', 'border'), # Instead of border-style: dashed;
    ('bbc', 'border-bottom-color'), # Instead of background-break continuous
    ('br', 'border-right'), # Instead of border-radius
    ('bt', 'border-top'), # Instead of border: thick
    ('bdr', 'border-right'), # Instead of border-radius
    ('bds', 'border-style'), # Instead of border-spacing
    ('bo', 'border'), # Instead of background-origin
    ('bos', 'border-style'), # Instead of box-shadow (?)
    ('ct', 'content'), # Istead of color transparent
    ('f', 'font'), # Istead of float (do we really need this?)
    ('p', 'padding'), # Instead of position (w/h/p/m consistency)
    ('pr', 'padding-right'), # Instead of position relative
])

PAIRS = dict([
    ('bg', 'background'), # Instead of border-style: groove;
    ('bd', 'border'), # Instead of background (Zen CSS support)
    ('pg', 'page'),
    ('lt', 'letter'),
    ('tf', 'transform'),
    ('tr', 'transition'),
])

def get_all_properties():
    all_properties = list(get_css_dict().keys())

    # раширить парами "свойство значение" (например "position absolute")
    for prop_name in all_properties:
        property_values = css_flat_list(prop_name, get_css_dict())
        extends_sieve = (i for i in property_values if not i[1].startswith('<'))
        unit_sieve = (i for i in extends_sieve if not i[1].startswith('.'))
        all_properties.extend('{0} {1}'.format(prop_name, v[1]) for v in unit_sieve)
    return all_properties


def score(a, b):
    """Оценочная функция"""
    s = 0

    # увеличивает вес свойству со значением (они разделены пробелом)
    if a and ' ' == a[-1]:
        s += 3.0

    # уменьшить, если буква находится не на грницах слова
    if '-' in a[1:-1] or '-' in b[1:-1]:
        s += -2.0

    # уменьшить, если буква находится не на грницах слова
    if ' ' in a[1:-1] or ' ' in b[1:-1]:
        s += -0.5

    # если буква в начале слова после -
    if a and a[-1] == '-':
        s += 1.05

    # если буквы подряд
    if len(a) == 1:
        s += 1.0

    return s

def string_score(arr):
    """Получает оценку разбиения"""
    # s = sum(score(arr[i-1], arr[i]) for i in range(1, len(arr)))
    # if s >0 :
    #     print arr, s
    return sum(score(arr[i-1], arr[i]) for i in range(1, len(arr)))

def tree(css_property, abbr):
    # функция генерирует деревья (разбиения) из строки
    # (abvbc, abc) -> [[a, bvb ,c], [avb, b, c]]
    # print '\n', css_property
    if len(css_property) < len(abbr):
        return set([])
    trees = [[css_property[0], css_property[1:],],]
    for level in range(1, len(abbr)):
        # print level, trees
        for tr in trees:
            if level == 1 and len(trees) == 1:
                trees = []
            # находит индексы букв
            indexes = []
            i = -1
            try:
                while True:
                    i = tr[-1].index(abbr[level], i+1)
                    indexes.append(i)
            except ValueError:
                pass
            # print 'indexes len', len(indexes)
            for ind in indexes:
                if level == 1:
                    car = tr[:-1]
                    cdr = tr[-1]
                    first = cdr[:ind]
                    second = cdr[ind:]
                    add = []
                    add.append(car[-1] + first)
                    add.append(second)
                    # print '\t', car, '|', cdr,'|', first,'|', second, '-', add, level, '=', tr
                    trees.append(add)
                else:
                    car = tr[:-1]
                    cdr = tr[-1]
                    first = cdr[:ind]
                    second = cdr[ind:]
                    add = car
                    add.append(first)
                    add.append(second)
                    # print '\t', car, '|', cdr,'|', first,'|', second, '-', add, level, '=', tr
                    # print repr(first)
                    trees.append(add)
                # break
            trees_i = set([tuple(t) for t in trees if len(t) == level+1])
            trees = [list(t) for t in trees_i]
            # print 'trees_i', trees_i
            # break
            # print
        # break

    # удалить разбиения с двумя "-" в шилде
    ret = set([tuple(t) for t in trees])
    filtered = []
    for s in ret: # каждое элемент в сете
        for t in s: # каждый шилд в элементе
            # print '\t', t
            if t.count('-') > 1:
                break
        else:
            filtered.append(s)
    # print set([tuple(t) for t in trees])
    # print filtered
    return filtered


def prop_value(s1, val):
    """Генератор возвращает свойства и значения разделённые пробелом
    Из всех свойств выбирает только с совпадающим порядком букв"""
    for pv in get_all_properties():
        if ' ' not in pv.strip():
            continue
        prop, value = pv.split()
        if sub_string(value, val):
            if sub_string(prop, s1):
                yield '{0} {1}'.format(prop, value).strip()

def sub_string(string, sub):
    """Функция проверяет, следуют ли буквы в нужном порядке в слове"""
    index = 0
    for c in sub:
        try:
            index += string[index:].index(c)+1
        except ValueError:
            return False
    else:
        return True

def segmentation(abbr):
    """Разбивает абрревиатуру на элементы"""

    # Части аббревиатуры
    parts = {
        'abbr': abbr # todo: выкинуть, используется только в тестах
    }

    # Проверка на important свойство
    if '!' == abbr[-1]:
        abbr = abbr[:-1]
        parts['important'] = True
    else:
        parts['important'] = False

    # TODO: вынести regex в compile
    # todo: начать тестировать regex
    m = re.search(r'^([a-z]?[a-z-]*[a-z]).*$', abbr)
    property_ = m if m is None else m.group(1)
    if property_ is None:
        # Аббревиатура не найдена
        return parts
    # del m

    parts['property-value'] = property_

    # удалить из аббревиатуры property
    abbr = abbr[len(property_):]

    if abbr:
        parts['property-name'] = property_
        del parts['property-value']

    # убрать zen-style разделитель
    if abbr and ':' == abbr[0]:
        abbr = abbr[1:]

    if not abbr:
        return parts

    parts.update(value_parser(abbr))

    if 'value' in parts:
        assert parts['value'] is None
        del parts['value']
    elif ('type-value' not in parts and 'type-name' not in parts):
        parts['keyword-value'] = abbr

    # TODO: сохранять принимаемые значения, например parts['allow'] = ['<color_values>']
    return parts

def value_parser(abbr):
    # todo: поддержка аббревиатур "w-.e" то есть "width -|em"
    parts = {}

    # Checking the color
    # Better to replace with regex to simplify it
    dot_index = 0
    if '.' in abbr:
        dot_index = abbr.index('.')
    if abbr[0] == '#':
        parts['color'] = (abbr[1:dot_index or 99])
        if dot_index:
            parts['color_alpha'] = (abbr[dot_index:])
        parts['value'] = None
    try:
        if all((c.isupper() or c.isdigit() or c == '.') for c in abbr) and 0 <= int(abbr[:dot_index or 99], 16) <= 0xFFFFFF:
            parts['color'] = abbr[:dot_index or 99]
            if dot_index:
                parts['color_alpha'] = (abbr[dot_index:])
            parts['value'] = None
    except ValueError:
        pass

    # Проверка на цифровое значение
    val = None

    numbers = re.sub("[a-z%]+$", "", abbr)
    try:
        val = float(numbers)
        val = int(numbers)
    except ValueError:
        pass

    if val is not None:
        parts['type-value'] = val
        if abbr != numbers:
            parts['type-name'] = abbr[len(numbers):]

    return parts

def extract(s1):
    """В зависимости от найденных компонент в аббревиатуре применяет функцию extract"""
    # print repr(s1)
    prop_iter = []
    parts = segmentation(s1)
    abbr_value = False
    if 'property-name' in parts:
        if parts['important']:
            s1 = s1[:-1]
        if s1[-1] != ':' and s1 != parts['property-name']:
            abbr_value = True

    if 'color' in parts:
        prop_iter.extend(prop for prop, val in get_flat_css() if val == '<color_values>')

    if isinstance(parts.get('type-value'), int):
        prop_iter.extend(prop for prop, val in get_flat_css() if val == '<integer>')

    if isinstance(parts.get('type-value'), float):
        # TODO: добавить deg, grad, time
        prop_iter.extend(prop for prop, val in get_flat_css() if val in ('<length>', '<number>', 'percentage'))

    if 'keyword-value' in parts and not parts['keyword-value']:
        prop_iter.extend(get_all_properties())

    if 'keyword-value' in parts:
        prop_iter.extend(prop_value(parts['property-name'], parts['keyword-value']))
    elif 'color' not in parts or 'type-value' in parts:
        prop_iter.extend(get_all_properties())

    assert parts.get('property-name', '') or parts.get('property-value', '')
    abbr = ' '.join([
        parts.get('property-name', '') or parts.get('property-value', ''),
        parts.get('keyword-value', ''),
    ])

    # предустановленные правила
    abbr = abbr.strip()
    if abbr in STATIC_ABBR:
        property_ = STATIC_ABBR[abbr]
    else:
        starts_properties = []
        # todo: переделать механизм PAIRS
        # надо вынести константы в css-dict
        # по две буквы (bd, bg, ba)
        pair = PAIRS.get(abbr[:2], None)
        if pair is not None:
            starts_properties = [prop for prop in prop_iter if prop.startswith(pair) and sub_string(prop, abbr)]
        if not starts_properties:
            starts_properties = [prop for prop in prop_iter if prop[0] == abbr[0] and sub_string(prop, abbr)]

        if 'type-value' in parts:
            starts_properties = [i for i in starts_properties if ' ' not in i]

        property_ = hayaku_extract(abbr, starts_properties, PRIORITY_PROPERTIES, string_score)

    property_, value = property_.split(' ') if ' ' in property_ else (property_, None)
    # print property_, value
    if not property_:
        return {}

    parts['property-name'] = property_

    if value is not None:
        parts['keyword-value'] = value

    # Проверка соответствия свойства и значения

    allow_values = [val for prop, val in get_flat_css() if prop == parts['property-name']]

    if 'color' in parts and '<color_values>' not in allow_values:
        del parts['color']
    if 'type-value' in parts and not any((t in allow_values) for t in ['<integer>', 'percentage', '<length>', '<number>', '<alphavalue>']):
        del parts['type-value']
    if 'keyword-value' in parts and parts['keyword-value'] not in allow_values:
        del parts['keyword-value']

    if all([
            'keyword-value' not in parts,
            'type-value' not in parts,
            'color' not in parts,
        ]) and abbr_value:
        return {}

    # Добавить значение по-умолчанию
    if parts['property-name'] in get_css_dict():
        default_value = css_defaults(parts['property-name'], get_css_dict())
        if default_value is not None:
            parts['default-value'] = default_value
        obj = get_css_dict()[parts['property-name']]
        if 'prefixes' in obj:
            parts['prefixes'] = obj['prefixes']
            if 'no-unprefixed-property' in obj:
                parts['no-unprefixed-property'] = obj['no-unprefixed-property']

    if parts['abbr'] == parts.get('property-value'):
        del parts['property-value']

    return parts

def hayaku_extract(abbr, filtered, priority=None, score_func=None):
    # выбирает только те правила куда входят все буквы в нужном порядке

    #  все возможные разбиения
    trees_filtered = []
    for property_ in filtered:
        trees_filtered.extend(tree(property_, abbr))

    # оценки к разбиениям
    if score_func is not None:
        scores = [(score_func(i), i) for i in trees_filtered]

        # выбрать с максимальной оценкой
        if scores:
            max_score = max(s[0] for s in scores)
            filtered_scores = (i for s, i in scores if s == max_score)
            filtered = [''.join(t) for t in filtered_scores]
            if len(filtered) == 1:
                return ''.join(filtered[0])

    # выбрать более приоритетные
    if len(filtered) == 1:
        return filtered[0]
    elif len(filtered) > 1 and priority is not None:
        # выбирает по приоритету
        prior = []
        for f in filtered:
            p = f.split(' ')[0] if ' ' in f else f
            try:
                prior.append((priority.index(p), f))
            except ValueError:
                prior.append((len(priority)+1, f))
        prior.sort()
        try:
            return prior[0][1]
        except IndexError:
            return ''
    else:
        return ''

########NEW FILE########
__FILENAME__ = templates
# -*- coding: utf-8 -*-
import json
import os
import re

import sublime

def import_dir(name, fromlist=()):
    PACKAGE_EXT = '.sublime-package'
    dirname = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
    if dirname.endswith(PACKAGE_EXT):
        dirname = dirname[:-len(PACKAGE_EXT)]
    return __import__('{0}.{1}'.format(dirname, name), fromlist=fromlist)


try:
    get_flat_css = import_dir('css_dict_driver', ('get_flat_css',)).get_flat_css
except ImportError:
    from css_dict_driver import get_flat_css

try:
    imp = import_dir('probe', ('hayaku_extract', 'sub_string'))
    hayaku_extract, sub_string = imp.hayaku_extract, imp.sub_string
except ImportError:
    from probe import hayaku_extract, sub_string


COLOR_REGEX = re.compile(r'#([0-9a-fA-F]{3,6})')
COLOR_WO_HASH_REGEX = re.compile(r'^([0-9a-fA-F]{3,6})')
COMPLEX_COLOR_REGEX = re.compile(r'^\s*(#?([a-fA-F\d]{3}|[a-fA-F\d]{6})|(rgb|hsl)a?\([^\)]+\))\s*$')
IMAGE_REGEX = re.compile(r'^\s*([^\s]+\.(jpg|jpeg|gif|png))\s*$')

CAPTURING_GROUPS = re.compile(r'(?<!\\)\((?!\?[^<])')
CAPTURES = re.compile(r'(\(\?|\$)(\d+)|^(\d)')

def align_prefix(property_name, prefix_list, no_unprefixed_property, aligned_prefixes, use_only):
    """Если есть префиксы, сделать шаблон с правильными отступами"""

    # if no_unprefixed_property:
        # prefix_list = ('-{0}-{1}'.format(prefix_list[0], property_name),)

    # skip if `use_only` is empty
    if use_only:
        prefix_list = [p for p in prefix_list if p in use_only]

    if prefix_list:
        prefix_list = ['-{0}-{1}'.format(p, property_name) for p in prefix_list]
        if not no_unprefixed_property:
            prefix_list.append(property_name)
        if not aligned_prefixes:
            return prefix_list
        max_length = max(len(p) for p in prefix_list)
        # TODO: сделать сортировку по размеру значений в prefix_list
        return tuple((' '*(max_length-len(p))) + p for p in prefix_list)
    return (property_name,)

def hex_to_coloralpha(hex):
    if len(hex) == 1:
        hex = hex*2
    return round(float(int(hex, 16)) / 255, 2)

def color_expand(color,alpha):
    if not color:
        return '#'
    if len(color) == 1:
        if color == '#':
            color = ''
        else:
            color = color * 3
    elif len(color) == 2:
        if color[0] == '#':
            color = color[1] * 3
        else:
            color = color * 3
    elif len(color) == 3:
        if color[0] == '#':
            color = color[1:] * 3
        else:
            color = color
    elif len(color) == 4:
        if color[0] != '#' and alpha == 1:
            alpha = hex_to_coloralpha(color[3])
            color = color[:3]
        else:
            return color
    elif len(color) == 5:
        if color[0] != '#':
            alpha = hex_to_coloralpha(color[3:5])
            color = color[:3]
        else:
            alpha = hex_to_coloralpha(color[4]*2)
            color = color[1:4]
    elif len(color) == 6:
        if color[0] != '#':
            pass
        else:
            alpha = hex_to_coloralpha(color[4:5])
            color = color[1:4]
    elif len(color) == 7:
        color = color[1:]
    else:
        return color

    # Convert color to rgba if there is some alpha
    if alpha == '.' or float(alpha) < 1:
        if alpha == '.':
            alpha = '.${1:5}' # adding caret for entering alpha value
        if alpha == '.0' or alpha == 0:
            alpha = '0'
        if len(color) == 3:
            color = color[0] * 2 + color[1] * 2 + color[2] * 2
        return "rgba({0},{1},{2},{3})".format(int(color[:2],16), int(color[2:4],16), int(color[4:],16), alpha)

    return '#{0}'.format(color)

def length_expand(name, value, unit, options=None):
    if options is None:
        options = {}

    if unit and 'percents'.startswith(unit):
        unit = '%'

    if isinstance(value, float):
        full_unit = options.get('CSS_default_unit_decimal', 'em')
    else:
        full_unit = options.get('CSS_default_unit', 'px')

    if '<number>' in [val for prop, val in get_flat_css() if prop == name] and not options.get('CSS_units_for_unitless_numbers'):
        full_unit = ''

    if value == 0:
        return '0'
    if value == '':
        return ''

    if unit:
        units = (val[1:] for key, val in get_flat_css() if key == name and val.startswith('.'))
        req_units = [u for u in units if sub_string(u, unit)]

        PRIORITY = ("em", "ex", "vw", "vh", "vmin", "vmax" "vm", "ch", "rem",
            "px", "cm", "mm", "in", "pt", "pc")
        full_unit = hayaku_extract(unit, req_units, PRIORITY)
        if not full_unit:
            return


    return '{0}{1}'.format(value, full_unit)

def expand_value(args, options=None):
    if 'keyword-value' in args:
        return args['keyword-value']
    if args['property-name'] in set(p for p, v in get_flat_css() if v == '<color_values>'):
        if 'color' in args and not args['color']:
            return '#'
        return color_expand(args.get('color', ''),args.get('color_alpha', 1))
    elif args['property-name'] in set(p for p, v in get_flat_css() if v.startswith('.')) and 'keyword-value' not in args:
        ret = length_expand(args['property-name'], args.get('type-value', ''), args.get('type-name', ''), options)
        return ret
    elif 'type-value' in args:
        return str(args['type-value'])
    return args.get('keyword-value', '')

def split_for_snippet(values, offset=0):
    split_lefts = [[]]
    split_rights = [[]]
    parts = 0
    new_offset = offset

    for value in (v for v in values if len(v) > 1):
        for i in range(1, len(value)):
            if value[:i] not in [item for sublist in split_lefts for item in sublist] + values:
                if len(split_lefts[parts]) > 98:
                    parts += 1
                    split_lefts.append([])
                    split_rights.append([])
                split_lefts[parts].append(value[:i])
                split_rights[parts].append(value[i:])
                new_offset += 1

    for index in range(0, parts + 1):
        split_lefts[index] = ''.join('({0}$)?'.format(re.escape(i)) for i in split_lefts[index])
        split_rights[index] = ''.join('(?{0}:{1})'.format(i+1+offset,re.escape(f)) for i,f in enumerate(split_rights[index]))

    return (split_lefts, split_rights, new_offset)

def convert_to_parts(parts):
    matches = []
    inserts = []
    parts_count = 1

    # Function for offsetting the captured groups in inserts
    def offset_captures(match):
        if match.group(3):
            return '()' + match.group(3)
        else:
            number = int(match.group(2))
            return match.group(1) + str(number + parts_count)

    for part in parts:
        matches.append(''.join([
            '(?=(',
            part['match'],
            ')?)',
            ]))
        inserts.append(''.join([
            '(?',
            str(parts_count),
            ':',
            CAPTURES.sub(offset_captures, part['insert']),
            ')',
            ]))
        # Incrementing the counter, adding the number of internal capturing groups
        parts_count += 1 + len(CAPTURING_GROUPS.findall(part['match'] ))
    return { "matches": matches, "inserts": inserts }

def generate_snippet(data):
    value = data.get('value')
    before = ''.join([
        '_PROPERTY_',
        data.get('colon'),
        data.get('space'),
        ])
    after = ''
    importance = ''
    if data.get('important'):
        importance = ' !important'

    if value:
        after = importance + data.get('semicolon')
    else:
        if not importance:
            importance_splitted = split_for_snippet(["!important"])
            importance = ''.join([
                '${1/.*?',
                importance_splitted[0][0],
                '$/',
                importance_splitted[1][0],
                '/}',
                ])

        befores = convert_to_parts(data["before"])
        before = ''.join([
            '${1/^',
            ''.join(befores["matches"]),
            '.+$|.*/',
            before,
            ''.join(befores["inserts"]),
            '/m}',
            ])


        if data.get('semicolon') == '':
            data['semicolon'] = ' '

        afters = convert_to_parts(data["after"])
        after = ''.join([
            '${1/^',
            ''.join(afters["matches"]),
            '.+$|.*/',
            ''.join(afters["inserts"]),
            '/m}',
            data.get('autovalues'),
            importance,
            data.get('semicolon'),
            ])
        value = ''.join([
            '${1:',
            data.get('default'),
            '}',
            ])
    return (before + value + after).replace('{','{{').replace('}','}}').replace('_PROPERTY_','{0}')


def make_template(args, options):
    whitespace        = options.get('CSS_whitespace_after_colon', '')
    disable_semicolon = options.get('CSS_syntax_no_semicolons', False)
    disable_colon     = options.get('CSS_syntax_no_colons', False)
    disable_prefixes  = options.get('CSS_prefixes_disable', False)
    option_color_length = options.get('CSS_colors_length').lower()

    clipboard = sublime.get_clipboard()

    if not whitespace and disable_colon:
        whitespace = ' '

    value = expand_value(args, options)
    if value is None:
        return

    if value.startswith('[') and value.endswith(']'):
        value = False

    semicolon = ';'
    colon = ':'

    if disable_semicolon:
        semicolon = ''
    if disable_colon:
        colon = ''

    snippet_parts = {
        'colon': colon,
        'semicolon': semicolon,
        'space': whitespace,
        'default': args.get('default-value',''),
        'important': args.get('important'),
        'before': [],
        'after': [],
        'autovalues': '',
    }

    # Handling prefixes
    property_ = (args['property-name'],)
    if not disable_prefixes:
        property_ = align_prefix(
            args['property-name'],
            args.get('prefixes', []),
            args.get('no-unprefixed-property', False) or options.get('CSS_prefixes_no_unprefixed', False),
            options.get('CSS_prefixes_align', True),
            options.get('CSS_prefixes_only', []),
            )

    # Replace the parens with a tabstop snippet
    # TODO: Move the inside snippets to the corresponding snippets dict
    if value and '()' in value:
        if value.replace('()', '') in ['rotate','rotateX','rotateY','rotateZ','skew','skewX','skewY']:
            value = value.replace('()', '($1${1/^((?!0$)-?(\d*.)?\d+)?.*$/(?1:deg)/m})')
        else:
            value = value.replace('()', '($1)')

    # Do things when there is no value expanded
    if not value or value == "#":
        if not options.get('CSS_disable_postexpand', False):
            auto_values = [val for prop, val in get_flat_css() if prop == args['property-name']]
            if auto_values:
                units = []
                values = []

                for p_value in (v for v in auto_values if len(v) > 1):
                    if p_value.startswith('.'):
                        units.append(p_value[1:])
                    elif not p_value.startswith('<'):
                        values.append(p_value)

                values_splitted = split_for_snippet(values)
                snippet_values = ''
                for index in range(0,len(values_splitted[0])):
                    snippet_values += ''.join([
                        '${1/^\s*',
                        values_splitted[0][index],
                        '.*/',
                        values_splitted[1][index],
                        '/m}',
                        ])
                snippet_parts['autovalues'] += snippet_values

                snippet_units = ''
                # TODO: find out when to use units or colors
                # TODO: Rewrite using after
                if units and value != "#":
                    units_splitted = split_for_snippet(units, 4)
                    snippet_parts['before'].append({
                        "match":  "%$",
                        "insert": "100"
                        })
                    # If there can be `number` in value, don't add `em` automatically
                    optional_unit_for_snippet = '(?2:(?3::0)em:px)'
                    if '<number>' in auto_values and not options.get('CSS_units_for_unitless_numbers'):
                        optional_unit_for_snippet = '(?2:(?3::0):)'
                    snippet_units = ''.join([
                        '${1/^\s*((?!0$)(?=.)[\d\-]*(\.)?(\d+)?((?=.)',
                        units_splitted[0][0],
                        ')?$)?.*/(?4:',
                        units_splitted[1][0],
                        ':(?1:' + optional_unit_for_snippet + '))/m}',
                        ])
                    snippet_parts['autovalues'] += snippet_units

                # Adding snippets for colors
                if value == "#":
                    value = ''
                    # Insert hash and doubling letters
                    snippet_parts['before'].append({
                        "match":  "([0-9a-fA-F]{1,6}|[0-9a-fA-F]{3,6}\s*(!\w*\s*)?)$",
                        "insert": "#"
                        })
                    # Different handling based on color_length setting
                    if option_color_length in ('short' 'shorthand'):
                        snippet_parts['after'].append({
                            "match": "#?((?<firstFoundColorChar>[0-9a-fA-F])(?:(\g{firstFoundColorChar})|[0-9a-fA-F])?)$",
                            "insert": "(?1:(?3:($2):$1$1))"
                            })
                    elif option_color_length in ('long' 'longhand'):
                        snippet_parts['after'].append({
                            "match": "#?((?<firstFoundColorChar>[0-9a-fA-F])\g{firstFoundColorChar}\g{firstFoundColorChar})$",
                            "insert": "(?1:$1)"
                            })
                        snippet_parts['after'].append({
                            "match": "#?([0-9a-fA-F]([0-9a-fA-F])?)$",
                            "insert": "(?1:(?2:($1$1):$1$1$1$1$1)"
                            })
                    else:
                        snippet_parts['after'].append({
                            "match": "#?([0-9a-fA-F]{1,2})$",
                            "insert": "(?1:$1$1)"
                            })
                    # Insert `rgba` thingies
                    snippet_parts['before'].append({
                        "match":  "(\d{1,3}%?),(\.)?.*$",
                        "insert": "rgba\((?2:$1,$1,)"
                        })
                    snippet_parts['after'].append({
                        "match": "(\d{1,3}%?),(\.)?(.+)?$",
                        "insert": "(?2:(?3::5):(?3::$1,$1,1))\)"
                        })

                    # Getting the value from the clipboard
                    # TODO: Move to the whole clipboard2default function
                    check_clipboard_for_color = COMPLEX_COLOR_REGEX.match(clipboard)
                    if check_clipboard_for_color and 'colors' in options.get('CSS_clipboard_defaults'):
                        snippet_parts['default'] = check_clipboard_for_color.group(1)
                        if COLOR_WO_HASH_REGEX.match(snippet_parts['default']):
                            snippet_parts['default'] = '#' + snippet_parts['default']
                # TODO: move this out of `if not value`,
                #       so we could use it for found `url()` values
                if '<url>' in auto_values:
                    snippet_parts['before'].append({
                        "match":  "[^\s]+\.(jpg|jpeg|gif|png)$",
                        "insert": "url\("
                        })
                    snippet_parts['after'].append({
                        "match": "[^\s]+\.(jpg|jpeg|gif|png)$",
                        "insert": "\)"
                        })
                    check_clipboard_for_image = IMAGE_REGEX.match(clipboard)
                    if check_clipboard_for_image and 'images' in options.get('CSS_clipboard_defaults'):
                        quote_symbol = ''
                        if options.get('CSS_syntax_url_quotes'):
                            quote_symbol = options.get('CSS_syntax_quote_symbol')
                        snippet_parts['default'] = 'url(' + quote_symbol + check_clipboard_for_image.group(1) + quote_symbol + ')'


    snippet_parts['value'] = value or ''

    snippet = generate_snippet(snippet_parts)

    # Apply settings to the colors in the values
    def restyle_colors(match):
        color = match.group(1)
        # Change case of the colors in the value
        if options.get('CSS_colors_case').lower() in ('uppercase' 'upper'):
            color = color.upper()
        elif options.get('CSS_colors_case').lower() in ('lowercase' 'lower'):
            color = color.lower()
        # Make colors short or longhand
        if option_color_length in ('short' 'shorthand') and len(color) == 6:
            if color[0] == color[1] and color[2] == color[3] and color[4] == color[5]:
                color = color[0] + color[2] + color[4]
        elif option_color_length in ('long' 'longhand') and len(color) == 3:
            color = color[0] * 2 + color[1] * 2 + color[2] * 2
        return '#' + color
    snippet = COLOR_REGEX.sub(restyle_colors, snippet)

    # Apply setting of the prefered quote symbol

    if options.get('CSS_syntax_quote_symbol') == "'" and '"' in snippet:
        snippet = snippet.replace('"',"'")
    if options.get('CSS_syntax_quote_symbol') == '"' and "'" in snippet:
        snippet = snippet.replace("'",'"')

    newline_ending = ''
    if options.get('CSS_newline_after_expand'):
        newline_ending = '\n'
    return '\n'.join(snippet.format(prop) for prop in property_) + newline_ending

# TODO
# display: -moz-inline-box;
# display: inline-block;

# background-image: -webkit-linear-gradient(top,rgba(255,255,255,0.6),rgba(255,255,255,0));
# background-image:    -moz-linear-gradient(top,rgba(255,255,255,0.6),rgba(255,255,255,0));
# background-image:      -o-linear-gradient(top,rgba(255,255,255,0.6),rgba(255,255,255,0));
# background-image:         linear-gradient(top,rgba(255,255,255,0.6),rgba(255,255,255,0));

########NEW FILE########
