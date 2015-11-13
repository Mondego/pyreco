__FILENAME__ = all
#!/usr/bin/env python

import grammar, os, os.path, glob, sys

def must_build(source, target):
	return (not os.path.exists(target)) \
		or (os.path.getmtime(source) >= os.path.getmtime(target))

if len(sys.argv) > 1:
    dir = sys.argv[1]
else:
    dir = os.getcwd()

os.chdir(dir)

for source in glob.glob('*.JSON-tmLanguage'):
	target = grammar.xml_filename(source)
	if must_build(source, target):
		print 'Building %s' % target
		grammar.build(source)
	else:
		print '%s is up to date.' % target

########NEW FILE########
__FILENAME__ = clean
#!/usr/bin/env python

import grammar, os, os.path, glob, sys

if len(sys.argv) > 1:
    dir = sys.argv[1]
else:
    dir = os.getcwd()

os.chdir(dir)

for f in glob.glob('*.JSON-tmLanguage'):
    xml = grammar.xml_filename(f)
    if os.path.exists(xml):
        print 'Deleting ' + xml
        os.remove(xml)

########NEW FILE########
__FILENAME__ = grammar
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, re, plistlib, json, traceback

def iter_tree_dicts(tree, initpath = u''):
    stack = []
    stack.append((initpath, tree))
    while stack:
        (path, obj) = stack.pop()
        if isinstance(obj, list):
            for i in xrange(0, len(obj)):
                np = u'[%d]' % i
                stack.append((path + np, obj[i]))
        elif isinstance(obj, dict):
            yield (path, obj)
            for (k, v) in obj.iteritems():
                np = u'/' + k
                stack.append((path + np, v))

class CompilerError(ValueError):
    pass

class TokenReplacement:
    @classmethod
    def run(cls, grammar):
        if u'tokens' in grammar:
            instance = cls(grammar[u'tokens'])
            result = instance.in_grammar(grammar)
            instance.print_counts()
            del grammar[u'tokens']
            return result
        else:
            print 'No "tokens" in grammar.'
            return grammar

    def __init__(self, token_dict):
        self.token_dict = token_dict
        self.replace_counts = {}
        for k in token_dict: self.replace_counts[k] = 0

    def in_string(self, value, path):
        def replacement(match):
            name = match.group(1)
            if name in self.token_dict:
                self.replace_counts[name] += 1
                return u'(?:' + self.token_dict[name] + u')'
            else:
                msg = u'Reference to undefined token: "%s" at %s' % (name, path)
                raise CompilerError, msg

        return re.sub(u'⟪([^⟫]*)⟫', replacement, value)

    def in_tree(self, tree, initpath):
        for (path, node) in iter_tree_dicts(tree, initpath):
            for (k, v) in node.iteritems():
                if k in [u'begin', u'end', u'match']:
                    itempath = path + u'/' + k
                    node[k] = self.in_string(v, itempath)

    def in_grammar(self, grammar):
        self.in_tree(grammar.get(u'patterns', []), u'/patterns')
        for (name, r_item) in grammar.get(u'repository', {}).iteritems():
            self.in_tree(r_item, u'/repository/' + name)

    def print_counts(self):
        for (t,n) in self.replace_counts.iteritems():
            print 'Replaced %d occurrences of %s.' % (n,t)

class IncludeCheck:
    @classmethod
    def run(cls, grammar):
        cls(grammar).check_includes()
        return grammar

    def __init__(self, grammar):
        self.grammar = grammar
        self.repository = grammar.get(u'repository', {})
        self.grammar_includes = set()
        self.repo_includes = dict([(k, set()) for k in self.repository])

    def check_includes(self):
        patterns = self.grammar.get(u'patterns', [])
        for (path, node) in iter_tree_dicts(patterns, u'/patterns'):
            if u'include' in node:
                self.add_include(node[u'include'], self.grammar_includes, path)
        for (name, item) in self.repository.iteritems():
            for (path, node) in iter_tree_dicts(item, u'/repository/' + name):
                if u'include' in node:
                    incset = self.repo_includes[name]
                    self.add_include(node[u'include'], incset, path)
        self.print_unused()

    def add_include(self, name, set, path):
        if name.startswith('#'):
            item = name[1:]
            if item in self.repository:
                set.add(item)
            else:
                msg = u'Undefined repository item "%s" at %s' % (item, path)
                raise CompilerError, msg

    def print_unused(self):
        for item in self.unused_items():
            print u'Repository item "%s" is not used.' % item

    def unused_items(self):
        used = set()
        for item in self.grammar_includes:
            used |= self.usage_closure(item, used)
        return set(self.repository) - used

    def usage_closure(self, item, closure = set()):
        if item not in closure:
            closure.add(item)
            for used_item in self.repo_includes[item]:
                closure |= self.usage_closure(used_item, closure)
        return closure

PASSES = [TokenReplacement, IncludeCheck]

def xml_filename(json_file):
    path, fname = os.path.split(json_file)
    fbase, old_ext = os.path.splitext(fname)
    return os.path.join(path, fbase + '.tmLanguage')

def build(json_file):
    grammar = None
    try:
        with open(json_file) as json_content:
            grammar = json.load(json_content)
    except ValueError, e:
        print "Error parsing JSON in %s:\n  %s" % (json_file, e)
    else:
        for op in PASSES:
            try:
                op.run(grammar)
            except CompilerError, e:
                print u'Error during %s:\n  %s' % (op.__name__, e)
                return None
            except Exception:
                traceback.print_exc()
                return None

        plistlib.writePlist(grammar, xml_filename(json_file))

if __name__ == '__main__':
    build(sys.argv[1])
########NEW FILE########
__FILENAME__ = plugin
import sublime, sublime_plugin

if (sublime.version() != '') and (sublime.version() < '3000'):
    pass
else:
    from .st3 import ErlangCommandHooks

class ExecInProjectFolderCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        folders = self.window.folders()
        if len(folders) >= 1:
            kwargs['working_dir'] = folders[0]
            v = self.window.active_view()
            if v is not None and v.file_name() is not None:
                for folder in folders:
                    if v.file_name().startswith(folder):
                        kwargs['working_dir'] = folder
                        break

        self.window.run_command("exec", kwargs)

########NEW FILE########
__FILENAME__ = plugin
import sublime, sublime_plugin
import Default.symbol
import re, os.path

# ------------------------------------------------------------------------------
# -- Generic Command Hooks
TEXT_CMD_HOOKS = {}
WINDOW_CMD_HOOKS = {}

def hook_text_command(command_name, selector):
    def decorate(func):
        TEXT_CMD_HOOKS[command_name] = (selector, func)
        return func
    return decorate

def hook_window_command(command_name, selector):
    def decorate(func):
        WINDOW_CMD_HOOKS[command_name] = (selector, func)
        return func
    return decorate

class ErlangCommandHooks(sublime_plugin.EventListener):
    def on_text_command(self, view, name, args):
        if args is None:
            args = {}
        if name in TEXT_CMD_HOOKS:
            (selector, hook) = TEXT_CMD_HOOKS[name]
            if self.is_enabled(view, selector):
                return hook(view, **args)

    def on_window_command(self, window, name, args):
        if args is None:
            args = {}
        if name in WINDOW_CMD_HOOKS:
            (selector, hook) = WINDOW_CMD_HOOKS[name]
            if self.is_enabled(window.active_view(), selector):
                return hook(window, **args)

    def is_enabled(self, view, selector):
        if view:
            p = view.sel()[0].begin()
            s = view.score_selector(p, selector)
            return s > 0

# ------------------------------------------------------------------------------
# -- Goto Definition
PREFIX_MAP = [
    ('Function',  'meta.function.erlang'),
    ('Function',  'meta.function.module.erlang'),
    ('Function',  'entity.name.function.erlang'),
    ('Function',  'entity.name.function.definition.erlang'),
    ('Type',      'storage.type.erlang'),
    ('Type',      'storage.type.module.erlang'),
    ('Type',      'storage.type.definition.erlang'),
    ('Record',    'storage.type.record.erlang'),
    ('Record',    'storage.type.record.definition.erlang'),
    ('Macro',     'keyword.other.macro.erlang'),
    ('Module',    'entity.name.type.class.module.erlang'),
    ('Yecc Rule', 'entity.name.token.unquoted.yecc'),
    ('Yecc Rule', 'entity.name.token.quoted.yecc')
]

ERLANG_EXTENSIONS = ['.erl', '.hrl', '.xrl', '.yrl']

class GotoExactDefinition:
    def __init__(self, view):
        # GotoDefinition could change at any time, but I don't feel like
        # writing all of its code again just for the sake of being future-proof
        self.view = view
        self.window = view.window()
        self.goto = Default.symbol.GotoDefinition(self.window)

    def at_position(self, kind, point):
        (module, funcname, is_local) = self.get_module_in_call(point)
        matches = self.goto.lookup_symbol(kind + ': ' + funcname)
        locations = [loc for loc in matches if self.loc_is_module(loc, module)]

        if len(locations) == 0:
            sublime.status_message("No matches for %s %s:%s" %
                                   (kind.lower(), module, funcname))
            if is_local: return
            # try to find the module if nothing matched
            mod_matches = self.goto.lookup_symbol('Module: ' + module)
            if len(mod_matches) == 0:
                if len(matches) == 0:
                    sublime.status_message("No matches for %s %s" %
                                           (kind.lower(), funcname))
                else:
                    self.goto_panel(matches) # open panel with inexact matches
            elif len(mod_matches) == 1:
                self.goto.goto_location(mod_matches[0])
            else:
                self.goto_panel(mod_matches) # open panel with modules
        elif len(locations) == 1:
            self.goto.goto_location(locations[0])
        else:
            self.goto_panel(locations)

    def get_module_in_call(self, point):
        v = self.view
        this_module = self.module_name(v.file_name())
        expclass = sublime.CLASS_WORD_END | sublime.CLASS_WORD_START
        word_sep =' \"\t\n(){}[]+-*/=>,.;'
        call = v.substr(v.expand_by_class(point, expclass, word_sep))
        match = re.split('\'?:\'?', call)
        if len(match) == 2:
            return (match[0], match[1], match[0] == this_module)
        else:
            return (this_module, match[0], True)

    def loc_is_module(self, loc, expected):
        # TODO: escripts?
        lmod = self.module_name(loc[0])
        return (lmod != None) and (lmod == expected)

    def module_name(self, filename):
        (root, ext) = os.path.splitext(re.split('/', filename)[-1])
        if ext in ERLANG_EXTENSIONS:
            return root
        else:
            return None

    def goto_panel(self, locations):
        sel_idx = self.local_match_idx(locations)

        # apparently, on_highlight is not called on entry
        self.on_highlight_entry(sel_idx, locations)

        self.window.show_quick_panel(
            [self.goto.format_location(l) for l in locations],
            on_select = lambda x: self.on_select_entry(x, locations),
            selected_index = sel_idx,
            on_highlight = lambda x: self.on_highlight_entry(x, locations))

    def on_select_entry(self, x, locations):
        self.goto.select_entry(locations, x, self.view, None)

    def on_highlight_entry(self, x, locations):
        self.goto.highlight_entry(locations, x)

    def local_match_idx(self, locations):
        for idx in range(len(locations)):
            if locations[idx][0] == self.view.file_name():
                return idx
        return 0

@hook_window_command('goto_definition', 'source.erlang, source.yecc')
def erlang_goto_definition(window, symbol=None):
    if symbol is not None:
        return None

    view = window.active_view()
    point = view.sel()[0].begin()
    scope = view.scope_name(point)
    symbol = view.substr(view.word(point))

    scores = map(lambda s: sublime.score_selector(scope, s[1]), PREFIX_MAP)
    (maxscore, match) = max(zip(scores, PREFIX_MAP), key=lambda z: z[0])
    kind = match[0]

    if maxscore == 0:
        gotosym = symbol
    elif kind == 'Macro':
        gotosym = kind + ': ' + strip_before('?', symbol)
    elif kind == 'Record':
        gotosym = kind + ': ' + strip_before('#', symbol)
    elif kind == 'Function':
        GotoExactDefinition(view).at_position(kind, point)
        return ('noop', None)
    elif kind == 'Type':
        GotoExactDefinition(view).at_position(kind, point)
        return ('noop', None)
    else:
        gotosym = kind + ': ' + symbol

    return ('goto_definition', {'symbol': gotosym})

def strip_before(char, s):
    pos = s.find(char)
    return s[pos+1:]

########NEW FILE########
