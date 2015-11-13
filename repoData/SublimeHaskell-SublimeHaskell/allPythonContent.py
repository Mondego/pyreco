__FILENAME__ = autobuild
import sublime
import sublime_plugin

if int(sublime.version()) < 3000:
    from sublime_haskell_common import attach_sandbox, get_cabal_project_dir_and_name_of_view, get_setting
else:
    from SublimeHaskell.sublime_haskell_common import attach_sandbox, get_cabal_project_dir_and_name_of_view, get_setting


class SublimeHaskellAutobuild(sublime_plugin.EventListener):
    def on_post_save(self, view):
        auto_build_enabled = get_setting('enable_auto_build')
        auto_check_enabled = get_setting('enable_auto_check')
        auto_lint_enabled = get_setting('enable_auto_lint')
        cabal_project_dir, cabal_project_name = get_cabal_project_dir_and_name_of_view(view)

        # auto build enabled and file within a cabal project
        if auto_build_enabled and cabal_project_dir is not None:
            view.window().run_command('sublime_haskell_build_auto')
        # try to ghc-mod check
        elif get_setting('enable_ghc_mod'):
            if auto_check_enabled and auto_lint_enabled:
                view.window().run_command('sublime_haskell_ghc_mod_check_and_lint')
            elif auto_check_enabled:
                view.window().run_command('sublime_haskell_ghc_mod_check')
            elif auto_lint_enabled:
                view.window().run_command('sublime_haskell_ghc_mod_lint')


def current_cabal_build():
    """Current cabal build command"""
    args = []
    if get_setting('use_cabal_dev'):
        args += ['cabal-dev']
    else:
        args += ['cabal']

    args += ['build']

    return attach_sandbox(args)

########NEW FILE########
__FILENAME__ = autocomplete
import json
import os
import re
import sublime
import sublime_plugin
import threading
import time

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    import symbols
    import cache
    import util
    import hdocs
    from ghci import ghci_info
    from haskell_docs import haskell_docs
    from hdevtools import start_hdevtools, stop_hdevtools
else:
    from SublimeHaskell.sublime_haskell_common import *
    import SublimeHaskell.symbols as symbols
    import SublimeHaskell.cache as cache
    import SublimeHaskell.util as util
    import SublimeHaskell.hdocs as hdocs
    from SublimeHaskell.ghci import ghci_info
    from SublimeHaskell.haskell_docs import haskell_docs
    from SublimeHaskell.hdevtools import start_hdevtools, stop_hdevtools


# If true, files that have not changed will not be re-inspected.
CHECK_MTIME = True

MODULE_INSPECTOR_SOURCE_PATH = None
MODULE_INSPECTOR_EXE_PATH = None
MODULE_INSPECTOR_OBJ_DIR = None
CABAL_INSPECTOR_SOURCE_PATH = None
CABAL_INSPECTOR_EXE_PATH = None
CABAL_INSPECTOR_OBJ_DIR = None
INSPECTOR_ENABLED = False
INSPECTOR_RUNNING = False

# ModuleInspector output
MODULE_INSPECTOR_RE = re.compile(r'ModuleInfo:(?P<result>.+)')

# The agent sleeps this long between inspections.
AGENT_SLEEP_TIMEOUT = 60.0

# Checks if we are in a LANGUAGE pragma.
LANGUAGE_RE = re.compile(r'.*{-#\s+LANGUAGE.*')

# Checks if we are in an import statement.
IMPORT_RE = re.compile(r'.*import(\s+qualified)?\s+')
IMPORT_RE_PREFIX = re.compile(r'^\s*import(\s+qualified)?\s+(.*)$')
IMPORT_QUALIFIED_POSSIBLE_RE = re.compile(r'.*import\s+(?P<qualifiedprefix>\S*)$')

# Checks if a word contains only alhanums, -, and _, and dot
NO_SPECIAL_CHARS_RE = re.compile(r'^(\w|[\-\.])*$')

# Get symbol qualified prefix and its name
SYMBOL_RE = re.compile(r'((?P<module>\w+(\.\w+)*)\.)?(?P<identifier>\w*)$')
# Get symbol module scope and its name within import statement
IMPORT_SYMBOL_RE = re.compile(r'import(\s+qualified)?\s+(?P<module>\w+(\.\w+)*)(\s+as\s+(?P<as>\w+))?\s*\(.*?(?P<identifier>\w*)$')

def get_line_contents(view, location):
    """
    Returns contents of line at the given location.
    """
    return view.substr(sublime.Region(view.line(location).a, location))

def get_line_contents_before_region(view, region):
    """
    Returns contents of line before the given region (including it).
    """
    return view.substr(sublime.Region(view.line(region).a, region.b))

def get_qualified_name(s):
    """
    'bla bla bla Data.List.fo' -> ('Data.List', 'Data.List.fo')
    """
    if len(s) == 0:
        return ('', '')
    quals = s.split()[-1].split('.')
    filtered = map(lambda s: list(filter(lambda c: c.isalpha() or c.isdigit() or c == '_', s)), quals)
    return ('.'.join(filtered[0:len(filtered) - 1]), '.'.join(filtered))

def get_qualified_symbol(line):
    """
    Get module context of symbol and symbol itself
    Returns (module, name, is_import_list), where module (or one of) can be None
    """
    res = IMPORT_SYMBOL_RE.search(line)
    if res:
        return (res.group('module'), res.group('identifier'), True)
    res = SYMBOL_RE.search(line)
    # res always match
    return (res.group('module'), res.group('identifier'), False)

def get_qualified_symbol_at_region(view, region):
    """
    Get module context of symbol and symbol itself for line before (and with) word on region
    Returns (module, name), where module (or one of) can be None
    """
    word_region = view.word(region)
    preline = get_line_contents_before_region(view, word_region)
    return get_qualified_symbol(preline)


# Gets available LANGUAGE options and import modules from ghc-mod
def get_ghcmod_language_pragmas():

    if get_setting_async('enable_ghc_mod'):
        return call_ghcmod_and_wait(['lang']).splitlines()

    return []


# Autocompletion data
class AutoCompletion(object):
    """Information for completion"""
    def __init__(self):
        self.language_pragmas = get_ghcmod_language_pragmas()

        # cabal name => set of modules, where cabal name is 'cabal' for cabal or sandbox path for cabal-devs
        self.module_completions = LockedObject({})

        # Currently used projects
        # name => project where project is:
        #   dir - project dir
        #   cabal - cabal file
        #   executables - list of executables where executable is
        #     name - name of executable
        self.projects = LockedObject({})

        # Storage of information
        self.database = symbols.Database()

        # keywords
        # TODO: keywords can't appear anywhere, we can suggest in right places
        self.keyword_completions = map(
            lambda k: (k + '\t(keyword)', k),
            ['case', 'data', 'instance', 'type', 'where', 'deriving', 'import', 'module'])

        self.current_filename = None

    def clear_inspected(self):
        # self.info = {}
        # self.std_info = {}
        self.projects.object = {}
        self.database = symbols.Database()

    def unalias_module_name(self, view, alias):
        "Get module names by alias"
        current_file_name = view.file_name()
        with self.database.files as files:
            if current_file_name in files:
                return files[current_file_name].unalias(alias)
        return []

    def get_completions(self, view, prefix, locations):
        "Get all the completions that apply to the current file."

        current_file_name = view.file_name()

        if not current_file_name:
            return []

        self.current_filename = current_file_name

        # Contents of the line under the first cursor
        line_contents = get_line_contents(view, locations[0])

        # If the current line is an import line, gives us (My.Module, ident)
        (qualified_module, symbol_name, is_import_list) = get_qualified_symbol(line_contents)
        qualified_prefix = '{0}.{1}'.format(qualified_module, symbol_name) if qualified_module else symbol_name

        # The list of completions we're going to assemble
        completions = []

        # Complete with modules too
        if qualified_module and not is_import_list:
            completions.extend(self.get_module_completions_for(qualified_prefix))

        moduleImports = []

        cur_info = None
        with self.database.files as files:
            if current_file_name in files:
                cur_info = files[current_file_name]

        if cur_info:
            if qualified_module:
                # If symbol is qualified, use completions from module specified
                moduleImports.append(qualified_module)
                moduleImports.extend([i.module for i in cur_info.imports.values() if i.import_as == qualified_module])
            else:
                # Otherwise, use completions from all importred unqualified modules and from this module
                moduleImports.append('Prelude')
                moduleImports.extend([i.module for i in cur_info.imports.values() if not i.is_qualified])
                # Add this module as well
                completions.extend(self.completions_for_module(cur_info, current_file_name))
                # Add keyword completions and module completions
                completions.extend(self.keyword_completions)
                completions.extend(self.get_module_completions_for(qualified_prefix, [i.module for i in cur_info.imports.values()]))

        for mi in set(moduleImports):
            completions.extend(self.completions_for(mi, current_file_name))

        return list(set(completions))

    def completions_for_module(self, module, filename = None):
        """
        Returns completions for module
        """
        if not module:
            return []
        return map(lambda d: d.suggest(), module.declarations.values())

    def completions_for(self, module_name, filename = None):
        """
        Returns completions for module
        """
        with self.database.modules as modules:
            if module_name not in modules:
                return []
            # TODO: Show all possible completions?
            return self.completions_for_module(symbols.get_visible_module(modules[module_name], filename), filename)

    def get_import_completions(self, view, prefix, locations):

        self.current_filename = view.file_name()

        # Contents of the current line up to the cursor
        line_contents = get_line_contents(view, locations[0])

        # Autocompletion for import statements
        if get_setting('auto_complete_imports'):
            match_import_list = IMPORT_SYMBOL_RE.search(line_contents)
            if match_import_list:
                module_name = match_import_list.group('module')
                import_list_completions = []

                import_list_completions.extend(self.completions_for(module_name, self.current_filename))

                return import_list_completions

            match_import = IMPORT_RE_PREFIX.match(line_contents)
            if match_import:
                (qualified, pref) = match_import.groups()
                import_completions = self.get_module_completions_for(pref)

                # Right after "import "? Propose "qualified" as well!
                qualified_match = IMPORT_QUALIFIED_POSSIBLE_RE.match(line_contents)
                if qualified_match:
                    qualified_prefix = qualified_match.group('qualifiedprefix')
                    if qualified_prefix == "" or "qualified".startswith(qualified_prefix):
                        import_completions.insert(0, (u"qualified", "qualified "))

                return list(set(import_completions))

        return []

    def get_special_completions(self, view, prefix, locations):

        # Contents of the current line up to the cursor
        line_contents = get_line_contents(view, locations[0])

        # Autocompletion for LANGUAGE pragmas
        if get_setting('auto_complete_language_pragmas'):
            # TODO handle multiple selections
            match_language = LANGUAGE_RE.match(line_contents)
            if match_language:
                return [(to_unicode(c),) * 2 for c in self.language_pragmas]

        return []

    def get_module_completions_for(self, qualified_prefix, modules = None):
        def module_next_name(mname):
            """
            Returns next name for prefix
            pref = Control.Con, mname = Control.Concurrent.MVar, result = Concurrent.MVar
            """
            suffix = mname.split('.')[(len(qualified_prefix.split('.')) - 1):]
            # Sublime replaces full module name with suffix, if it contains no dots?
            return suffix[0]

        module_list = modules if modules else self.get_current_module_completions()
        return list(set((module_next_name(m) + '\t(module)', module_next_name(m)) for m in module_list if m.startswith(qualified_prefix)))

    def get_current_module_completions(self):
        completions = []

        cabal = current_cabal()

        with self.database.get_cabal_modules() as cabal_modules:
            completions.extend(list(cabal_modules.keys()))

        if self.current_filename:
            (project_path, _) = get_cabal_project_dir_and_name_of_file(self.current_filename)
            if project_path:
                completions.extend([m.name for m in self.database.get_project_modules(project_path).values()])

        with self.module_completions as module_completions:
            if cabal in module_completions:
                completions.extend(module_completions[cabal])

        return set(completions)


autocompletion = AutoCompletion()



def can_complete_qualified_symbol(info):
    """
    Helper function, returns whether sublime_haskell_complete can run for (module, symbol, is_import_list)
    """
    (module_name, symbol_name, is_import_list) = info
    if not module_name:
        return False

    if is_import_list:
        return module_name in autocompletion.get_current_module_completions()
    else:
        return list(filter(lambda m: m.startswith(module_name), autocompletion.get_current_module_completions())) != []

class SublimeHaskellComplete(sublime_plugin.TextCommand):
    """ Shows autocompletion popup """
    def run(self, edit, characters):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), characters)

        if can_complete_qualified_symbol(get_qualified_symbol_at_region(self.view, self.view.sel()[0])):
            self.view.run_command("hide_auto_complete")
            sublime.set_timeout(self.do_complete, 1)

    def do_complete(self):
        self.view.run_command("auto_complete")

    def is_enabled(self):
        return is_enabled_haskell_command(self.view, False)



class SublimeHaskellBrowseDeclarations(sublime_plugin.WindowCommand):
    """
    Show all available declarations from current cabal and opened projects
    """
    def run(self):
        self.decls = []
        self.declarations = []

        # (module, ident) => symbols.Declaration
        decls = {}

        with autocompletion.database.files as files:
            for m in files.values():
                for decl in m.declarations.values():
                    decls[(m.name, decl.name)] = decl

        for decl in decls.values():
            self.decls.append(decl)
            self.declarations.append(decl.module.name + ': ' + decl.brief())

        self.window.show_quick_panel(self.declarations, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        view = self.window.active_view()
        if not view:
            return

        decl = self.decls[idx]

        view.run_command('sublime_haskell_symbol_info', {
            'filename': decl.location.filename,
            'decl': decl.name })

    def is_enabled(self):
        return is_enabled_haskell_command(None, False)



class SublimeHaskellGoToAnyDeclaration(sublime_plugin.WindowCommand):
    def run(self):
        self.files = []
        self.declarations = []

        with autocompletion.database.files as files:
            for f, m in files.items():
                for decl in m.declarations.values():
                    self.files.append([f, str(decl.location.line), str(decl.location.column)])
                    self.declarations.append([decl.brief(), '{0}:{1}:{2}'.format(decl.module.name, decl.location.line, decl.location.column)])

        self.window.show_quick_panel(self.declarations, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        self.window.open_file(':'.join(self.files[idx]), sublime.ENCODED_POSITION)

    def is_enabled(self):
        return is_enabled_haskell_command(None, False)



class SublimeHaskellReinspectAll(sublime_plugin.WindowCommand):
    def run(self):
        global INSPECTOR_ENABLED

        if INSPECTOR_ENABLED:
            autocompletion.clear_inspected()
            inspector.mark_all_files(self.window)
        else:
            show_status_message("inspector_enabled setting is false", isok=False)



class SublimeHaskellSymbolInfoCommand(sublime_plugin.TextCommand):
    """
    Show information about selected symbol

    """
    def run(self, edit, filename = None, module_name = None, decl = None):
        if decl and filename:
            with autocompletion.database.files as files:
                if filename in files:
                    m = files[filename]
                    if decl in m.declarations:
                        self.show_symbol_info(m.declarations[decl])
                    else:
                        show_status_message('Symbol "{0}" not found in {1}'.format(decl, filename))
                else:
                    show_status_message('No info about module in {0}'.format(filename))
            return

        if decl and module_name:
            with autocompletion.database.get_cabal_modules() as cabal_modules:
                if module_name in cabal_modules:
                    m = cabal_modules[module_name]
                    if decl in m.declarations:
                        self.show_symbol_info(m.declarations[decl])
                    else:
                        show_status_message('Symbol "{0}" not found in {1}'.format(decl, filename))
                else:
                    show_status_message('No info about module {0}'.format(module_name))
            return

        (module_word, ident, _) = get_qualified_symbol_at_region(self.view, self.view.sel()[0])
        full_name = '{0}.{1}'.format(module_word, ident) if module_word else ident

        current_file_name = self.view.file_name()

        candidates = []

        imported_symbol_not_found = False

        with autocompletion.database.symbols as decl_symbols:
            if ident in decl_symbols:

                decls = decl_symbols[ident] if not module_word else [d for d in decl_symbols[ident] if d.full_name() == full_name]

                modules_dict = symbols.declarations_modules(decls, lambda ms: symbols.get_visible_module(ms, current_file_name)).values()

                with autocompletion.database.files as files:
                    if current_file_name in files:
                        cur_info = files[current_file_name]

                        if not module_word or module_word == cur_info.name:
                            # this module declaration
                            candidates.extend([m.declarations[ident] for m in modules_dict if symbols.is_this_module(cur_info, m) and ident in m.declarations])
                        if not candidates:
                            # declarations from imported modules
                            candidates.extend([m.declarations[ident] for m in modules_dict if symbols.is_imported_module(cur_info, m, module_word) and ident in m.declarations])
                        if not candidates:
                            imported_symbol_not_found = True
                            # show all possible candidates
                            candidates.extend([m.declarations[ident] for m in modules_dict if ident in m.declarations])

                    # No info about imports for this file, just add all declarations
                    else:
                        candidates.extend([m.declarations[ident] for m in modules_dict if ident in m.declarations])

            else:
                imported_symbol_not_found = True

        if imported_symbol_not_found or not candidates:
            browse_for_module = False
            browse_module_candidate = None
            with autocompletion.database.modules as modules:
                if full_name in modules:
                    # Browse symbols in module
                    browse_for_module = True
                    browse_module_candidate = symbols.get_preferred_module(modules[full_name], current_file_name)

            if browse_for_module:
                if browse_module_candidate:
                    self.view.window().run_command('sublime_haskell_browse_module', {
                        'module_name': browse_module_candidate.name,
                        'filename': current_file_name })
                    return
                else:
                    show_status_message("No info about module {0}".format(full_name))
                    return
            elif not candidates:
                # Sometimes ghc-mod returns no info about module, but module exists
                # So there are no info about valid symbol
                # But if user sure, that symbol exists, he can force to call for ghci to get info
                import_list = []
                with autocompletion.database.files as files:
                    if current_file_name in files:
                        import_list.extend(files[current_file_name].imports.keys())

                if module_word:
                    # Full qualified name, just call to ghci_info
                    info = ghci_info(module_word, ident)
                    if info:
                        self.show_symbol_info(info)
                        return
                elif import_list:
                    # Allow user to select module
                    self.candidates = [(m, ident) for m in import_list]
                    self.view.window().show_quick_panel([
                        ['Select imported module', 'from where {0} may be imported'.format(ident)],
                        ['No, thanks']], self.on_import_selected)
                    return

                show_status_message('Symbol "{0}" not found'.format(ident), False)
                return

        if not candidates:
            show_status_message('Symbol "{0}" not found'.format(ident), False)
            return

        if len(candidates) == 1:
            self.show_symbol_info(candidates[0])
            return

        self.candidates = candidates
        self.view.window().show_quick_panel([[c.qualified_name()] for c in candidates], self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        self.show_symbol_info(self.candidates[idx])

    def on_import_selected(self, idx):
        if idx == 0: # Yes, select imported module
            self.view.window().show_quick_panel(['{0}.{1}'.format(i[0], i[1]) for i in self.candidates], self.on_candidate_selected)

    def on_candidate_selected(self, idx):
        if idx == -1:
            return

        (module_name, ident_name) = self.candidates[idx]
        info = util.symbol_info(self.view.file_name(), module_name, ident_name)
        if info:
            self.show_symbol_info(info)
        else:
            show_status_message("Can't get info for {0}.{1}".format(module_name, ident_name), False)

    def show_symbol_info(self, decl):
        output_view = self.view.window().get_output_panel('sublime_haskell_symbol_info')
        output_view.set_read_only(False)

        util.refine_decl(decl)

        # TODO: Move to separate command for Sublime Text 3
        output_view.run_command('sublime_haskell_output_text', {
            'text': decl.detailed() })

        output_view.sel().clear()
        output_view.set_read_only(True)

        self.view.window().run_command('show_panel', {
            'panel': 'output.' + 'sublime_haskell_symbol_info' })

    def browse_module(self, module):
        with autocompletion.database.modules as modules:
            decls = list(module.declarations.values())
            self.candidates = decls
            self.view.window().show_quick_panel([[decl.brief(), decl.docs.splitlines()[0]] if decl.docs else [decl.brief()] for decl in decls], self.on_done)

    def is_enabled(self):
        return is_enabled_haskell_command(self.view, False)



class SublimeHaskellBrowseModule(sublime_plugin.WindowCommand):
    """
    Browse module symbols
    """
    def run(self, module_name = None, filename = None):
        if module_name:
            with autocompletion.database.modules as modules:
                if module_name not in modules:
                    show_status_message('Module "{0}" not found'.format(module_name), False)
                    return

                current_file_name = filename if filename else self.window.active_view().file_name()

                module_candidate = symbols.get_preferred_module(modules[module_name], current_file_name)

                if hdocs.load_module_docs(module_candidate):
                # FIXME: Not here!
                    cache.dump_cabal_cache(autocompletion.database, module_candidate.cabal)

                decls = list(module_candidate.declarations.values())
                self.candidates = sorted(decls, key = lambda d: d.brief())

                self.window.show_quick_panel([[decl.brief(), decl.docs.splitlines()[0]] if decl.docs else [decl.brief()] for decl in self.candidates], self.on_symbol_selected)
                return

        self.candidates = []

        with autocompletion.database.files as files:
            for fname, m in files.items():
                self.candidates.append([m.name, fname])

        with autocompletion.database.get_cabal_modules() as cabal_modules:
            for m in cabal_modules.values():
                self.candidates.append([m.name])

        self.candidates.sort(key = lambda c: c[0])

        self.window.show_quick_panel(self.candidates, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return

        module_name = self.candidates[idx][0]
        self.window.run_command('sublime_haskell_browse_module', {
            'module_name': module_name })

    def on_symbol_selected(self, idx):
        if idx == -1:
            return

        candidate = self.candidates[idx]

        if candidate.module.location:
            self.window.active_view().run_command('sublime_haskell_symbol_info', {
                'filename': candidate.module.location.filename,
                'decl': candidate.name })
        else:
            self.window.active_view().run_command('sublime_haskell_symbol_info', {
                'module_name': candidate.module.name,
                'decl': candidate.name })

class SublimeHaskellGoToDeclaration(sublime_plugin.TextCommand):
    def run(self, edit):
        (module_word, ident, _) = get_qualified_symbol_at_region(self.view, self.view.sel()[0])

        full_name = '.'.join([module_word, ident]) if module_word else ident

        current_file_name = self.view.file_name()
        current_project = get_cabal_project_dir_of_file(current_file_name)

        module_candidates = []
        candidates = []

        with autocompletion.database.symbols as decl_symbols:
            if ident not in decl_symbols:
                show_status_message('Declaration for "{0}" not found'.format(ident), False)
                return

            decls = decl_symbols[ident]

            modules_dict = symbols.flatten(symbols.declarations_modules(decls, lambda ms: list(filter(symbols.is_by_sources, ms))).values())

            with autocompletion.database.files as files:
                if current_file_name in files:
                    cur_info = files[current_file_name]

                    if not module_word or module_word == cur_info.name:
                        # this module declarations
                        candidates.extend([m.declarations[ident] for m in modules_dict if symbols.is_this_module(cur_info, m) and ident in m.declarations])
                    if not candidates:
                        # declarations from imported modules within this project
                        candidates.extend([m.declarations[ident] for m in modules_dict if symbols.is_imported_module(cur_info, m, module_word) and symbols.is_within_project(m, cur_info.location.project) and ident in m.declarations])
                    if not candidates:
                        # declarations from imported modules within other projects
                        candidates.extend([m.declarations[ident] for m in modules_dict if symbols.is_imported_module(cur_info, m, module_word) and ident in m.declarations])
                    if not candidates:
                        # show all possible candidates
                        candidates.extend([m.declarations[ident] for m in modules_dict if ident in m.declarations])

                # No info about imports for this file, just add all declarations
                else:
                    candidates.extend([m.declarations[ident] for m in modules_dict if ident in declarations])

        with autocompletion.database.modules as modules:
            if full_name in modules:
                modules_list = list(filter(symbols.is_by_sources, modules[full_name]))

                # Find module in this project
                module_candidates.extend([m for m in modules_list if symbols.is_within_project(m, current_project)])
                if not module_candidates:
                    # Modules from other projects
                    module_candidates.extend(modules_list)

        if not candidates and not module_candidates:
            show_status_message('Declaration for "{0}" not found'.format(ident), False)
            return

        if len(candidates) + len(module_candidates) == 1:
            if len(module_candidates) == 1:
                self.view.window().open_file(module_candidates[0].location.filename)
                return
            if len(candidates) == 1:
                self.view.window().open_file(candidates[0].location.position(), sublime.ENCODED_POSITION)
                return

        # many candidates
        self.select_candidates = [([c.name, c.location.position()], True) for c in candidates] + [([m.name, m.location.filename], False) for m in module_candidates]
        self.view.window().show_quick_panel([c[0] for c in self.select_candidates], self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return

        selected = self.select_candidates[idx]
        if selected[1]:
            self.view.window().open_file(selected[0][1], sublime.ENCODED_POSITION)
        else:
            self.view.window().open_file(selected[0][1])

    def is_enabled(self):
        return is_enabled_haskell_command(self.view, False)



class StandardInspectorAgent(threading.Thread):
    def __init__(self):
        super(StandardInspectorAgent, self).__init__()
        self.daemon = True

        self.modules_lock = threading.Lock()
        self.modules_to_load = []

        self.cabal_lock = threading.Lock()
        self.cabal_to_load = []

        self.module_docs = LockedObject([])

        self.update_event = threading.Event()

    def run(self):
        self.load_module_completions()

        while True:
            load_modules = []
            with self.modules_lock:
                load_modules = self.modules_to_load
                self.modules_to_load = []

            cabal = current_cabal()

            if len(load_modules) > 0:
                try:
                    for m in load_modules:
                        self._load_standard_module(m, cabal)
                        # self._load_standard_module_docs(m, cabal)
                except:
                    continue

            load_module_docs = []
            with self.module_docs as module_docs:
                load_module_docs = module_docs[:]
                module_docs[:] = []

            if len(load_module_docs) > 0:
                for m in load_module_docs:
                    self._load_standard_module_docs(m, cabal)

            with self.cabal_lock:
                load_cabal = self.cabal_to_load
                self.cabal_to_load = []

            if len(load_cabal) > 0:
                try:
                    for c in load_cabal:
                        self.load_module_completions(c)
                except:
                    continue

            if len(load_modules) > 0:
                cache.dump_cabal_cache(autocompletion.database)

            self.update_event.wait(AGENT_SLEEP_TIMEOUT)
            self.update_event.clear()

    def load_module_info(self, module_name):
        with self.modules_lock:
            self.modules_to_load.append(module_name)
        self.update_event.set()

    def load_module_docs(self, module_name):
        with self.module_docs as module_docs:
            module_docs.append(module_name)
        self.update_event.set()

    def load_cabal_info(self, cabal_name = None):
        if not cabal_name:
            cabal_name = current_cabal()

        with self.cabal_lock:
            self.cabal_to_load.append(cabal_name)
        self.update_event.set()

    # Load modules info for cabal/cabal-dev specified
    def load_module_completions(self, cabal = None):
        if not get_setting_async('enable_ghc_mod'):
            return

        if not cabal:
            cabal = current_cabal()


        try:
            with status_message_process('Loading standard modules info for {0}'.format(cabal)) as s:
                cache_begin_time = time.clock()
                cache.load_cabal_cache(autocompletion.database, cabal)
                cache_end_time = time.clock()
                log('loading standard modules cache for {0} within {1} seconds'.format(cabal, cache_end_time - cache_begin_time))

                modules = None
                with autocompletion.module_completions as module_completions:
                    if cabal in module_completions:
                        return
                    module_completions[cabal] = set(call_ghcmod_and_wait(['list'], cabal = cabal).splitlines())
                    modules = module_completions[cabal].copy()

                begin_time = time.clock()
                log('loading standard modules info for {0}'.format(cabal))

                loaded_modules = 0
                for m in modules:
                    self._load_standard_module(m, cabal)
                    # self._load_standard_module_docs(m, cabal)
                    loaded_modules += 1
                    s.percentage_message(loaded_modules, len(modules))

                end_time = time.clock()
                log('loading standard modules info for {0} within {1} seconds'.format(cabal, end_time - begin_time))

                cache.dump_cabal_cache(autocompletion.database, cabal)

        except Exception as e:
            log('loading standard modules info for {0} failed with {1}'.format(cabal, e))


    def _load_standard_module(self, module_name, cabal = None):
        if not cabal:
            cabal = current_cabal()

        with autocompletion.database.get_cabal_modules(cabal) as cabal_modules:
            if module_name in cabal_modules:
                return

        if get_setting_async('enable_ghc_mod'):
            try:
                m = util.browse_module(module_name, cabal = cabal)

                if m:
                    autocompletion.database.add_module(m)

            except Exception as e:
                log('Inspecting in-cabal module {0} failed: {1}'.format(module_name, e))

    def _load_standard_module_docs(self, module_name, cabal = None):
        if not cabal:
            cabal = current_cabal()

        with autocompletion.database.get_cabal_modules(cabal) as cabal_modules:
            if module_name in cabal_modules:
                try:
                    hdocs.load_module_docs(cabal_modules[module_name])

                except Exception as e:
                    log('Loading docs for in-cabal module {0} failed: {1}'.format(module_name, e))



std_inspector = None



class InspectorAgent(threading.Thread):
    def __init__(self):
        # Call the superclass constructor:
        super(InspectorAgent, self).__init__()
        # Make this thread daemonic so that it won't prevent the program
        # from exiting.
        self.daemon = True
        # Files that need to be re-inspected:
        self.dirty_files_lock = threading.Lock()
        self.dirty_files = []

        self.active_files = LockedObject([])

        # Event that is set (notified) when files have changed
        self.reinspect_event = threading.Event()

    CABALMSG = 'Compiling Haskell CabalInspector'
    MODULEMSG = 'Compiling Haskell ModuleInspector'

    def run(self):
        # Compile the CabalInspector:
        with status_message(InspectorAgent.CABALMSG) as s:

            exit_code, out, err = call_and_wait(['ghc',
                '--make', CABAL_INSPECTOR_SOURCE_PATH,
                '-o', CABAL_INSPECTOR_EXE_PATH,
                '-outputdir', CABAL_INSPECTOR_OBJ_DIR])

            if exit_code != 0:
                s.fail()
                error_msg = u"SublimeHaskell: Failed to compile CabalInspector\n{0}".format(err)
                wait_for_window(lambda w: self.show_errors(w, error_msg))
                # Continue anyway

        # Compile the ModuleInspector:
        with status_message(InspectorAgent.MODULEMSG) as s:

            exit_code, out, err = call_and_wait(['ghc',
                '--make', MODULE_INSPECTOR_SOURCE_PATH,
                '-package', 'ghc',
                '-o', MODULE_INSPECTOR_EXE_PATH,
                '-outputdir', MODULE_INSPECTOR_OBJ_DIR])

            if exit_code != 0:
                s.fail()
                error_msg = u"SublimeHaskell: Failed to compile ModuleInspector\n{0}".format(err)
                wait_for_window(lambda w: self.show_errors(w, error_msg))
                return

        # For first time, inspect all open folders and files
        wait_for_window(lambda w: self.mark_all_files(w))
        self.mark_active_files()

        # TODO: If compilation failed, we can't proceed; handle this.
        # Periodically wake up and see if there is anything to inspect.
        while True:
            files_to_reinspect = []
            files_to_doc = []
            with self.dirty_files_lock:
                files_to_reinspect = self.dirty_files
                self.dirty_files = []
            with self.active_files as active_files:
                files_to_doc = active_files[:]
                active_files[:] = []
            # Find the cabal project corresponding to each "dirty" file:
            cabal_dirs = []
            standalone_files = []
            for filename in files_to_reinspect:
                d = get_cabal_project_dir_of_file(filename)
                if d is not None:
                    cabal_dirs.append(d)
                else:
                    standalone_files.append(filename)
            # Eliminate duplicate project directories:
            cabal_dirs = list(set(cabal_dirs))
            standalone_files = list(set(standalone_files))
            for i, d in enumerate(cabal_dirs):
                self._refresh_all_module_info(d, i + 1, len(cabal_dirs))
            for f in standalone_files:
                self._refresh_module_info(f)
            for f in files_to_doc:
                with autocompletion.database.files as files:
                    if f in files:
                        for i in files[f].imports.values():
                            std_inspector.load_module_docs(i.module)
            self.reinspect_event.wait(AGENT_SLEEP_TIMEOUT)
            self.reinspect_event.clear()

    def mark_active_files(self):
        def mark_active_files_():
            for w in sublime.windows():
                for v in w.views():
                    with self.active_files as active_files:
                        active_files.append(v.file_name())
        sublime.set_timeout(lambda: mark_active_files_, 0)
        self.reinspect_event.set()

    def mark_all_files(self, window):
        folder_files = []
        for folder in window.folders():
            folder_files.extend(list_files_in_dir_recursively(folder))
        with self.dirty_files_lock:
            self.dirty_files.extend([f for f in folder_files if f.endswith('.hs')])
        self.reinspect_event.set()

    def show_errors(self, window, error_text):
        sublime.set_timeout(lambda: output_error(window, error_text), 0)

    def mark_file_active(self, filename):
        with self.active_files as active_files:
            active_files.append(filename)
        self.reinspect_event.set()

    def mark_file_dirty(self, filename):
        "Report that a file should be reinspected."
        if filename is None:
            return

        with self.dirty_files_lock:
            self.dirty_files.append(filename)
        self.reinspect_event.set()

    def _refresh_all_module_info(self, cabal_dir, index, count):
        "Rebuild module information for all files under the specified directory."
        begin_time = time.clock()
        log('reinspecting project ({0})'.format(cabal_dir))
        # Process all files within the Cabal project:
        # TODO: Only process files within the .cabal file's "src" directory.
        (project_name, cabal_file) = get_cabal_in_dir(cabal_dir)

        with status_message_process('Reinspecting ({0}/{1}) {2}'.format(index, count, project_name), priority = 1) as s:
            cache.load_project_cache(autocompletion.database, cabal_dir)

            # set project and read cabal
            if cabal_file and project_name:
                self._refresh_project_info(cabal_dir, project_name, cabal_file)

            files_in_dir = list_files_in_dir_recursively(cabal_dir)
            haskell_source_files = [x for x in files_in_dir if x.endswith('.hs') and ('dist/build/autogen' not in x)]
            filenames_loaded = 0
            for filename in haskell_source_files:
                self._refresh_module_info(filename, False)
                filenames_loaded += 1
                s.percentage_message(filenames_loaded, len(haskell_source_files))
            end_time = time.clock()
            log('total inspection time: {0} seconds'.format(end_time - begin_time))

            cache.dump_project_cache(autocompletion.database, cabal_dir)

    def _refresh_project_info(self, cabal_dir, project_name, cabal_file):
        exit_code, out, err = call_and_wait(
            [CABAL_INSPECTOR_EXE_PATH, cabal_file])

        if exit_code == 0:
            new_info = json.loads(out)

            if 'error' not in new_info:
                if 'executables' in new_info and 'library' in new_info:
                    with autocompletion.projects as projects:
                        projects[project_name] = {
                            'dir': cabal_dir,
                            'cabal': os.path.basename(cabal_file),
                            'library': new_info['library'],
                            'executables': new_info['executables'],
                            'tests': new_info['tests'] }

    def _refresh_module_info(self, filename, standalone = True):
        "Rebuild module information for the specified file."
        # TODO: Only do this within Haskell files in Cabal projects.
        # TODO: Currently the ModuleInspector only delivers top-level functions
        #       with hand-written type signatures. This code should make that clear.
        # If the file hasn't changed since it was last inspected, do nothing:
        if not filename.endswith('.hs'):
            return

        with autocompletion.database.files as files:
            if filename in files:
                last_inspection_time = files[filename].last_inspection_time
                modification_time = os.stat(filename).st_mtime
                # Skip if we already inspected after last modification
                if modification_time <= last_inspection_time:
                    # log('skipping inspecting %s' % filename)
                    return
                else:
                    files[filename].last_inspection_time = time.time()

        ghc_opts = get_ghc_opts()
        ghc_opts_args = [' '.join(ghc_opts)] if ghc_opts else []

        exit_code, stdout, stderr = call_and_wait(
            [MODULE_INSPECTOR_EXE_PATH, filename] + ghc_opts_args, cwd = get_source_dir(filename))

        module_inspector_out = MODULE_INSPECTOR_RE.search(stdout)

        # Update only when module is ok
        if exit_code == 0 and module_inspector_out:
            new_info = json.loads(module_inspector_out.group('result'))

            if 'error' not in new_info:
                # # Load standard modules
                if 'imports' in new_info:
                    for mi in new_info['imports']:
                        if 'importName' in mi:
                            std_inspector.load_module_info(mi['importName'])

                try:
                    def make_import(import_info):
                        import_name = import_info['importName']
                        ret = symbols.Import(import_name, import_info['qualified'], import_info['as'])
                        return (import_name, ret)

                    module_imports = dict(map(make_import, new_info['imports']))
                    import_list = new_info['exportList'] if ('exportList' in new_info and new_info['exportList'] is not None) else []

                    new_module = symbols.Module(new_info['moduleName'], import_list, module_imports, {}, symbols.module_location(filename), last_inspection_time=time.time())
                    for d in new_info['declarations']:
                        location = symbols.Location(filename, d['line'], d['column'])
                        if d['what'] == 'function':
                            new_function = symbols.Function(d['name'], d['type'], d['docs'], location, new_module)
                            util.refine_type(new_function)
                            new_module.add_declaration(new_function)
                        elif d['what'] == 'type':
                            new_module.add_declaration(symbols.Type(d['name'], d['context'], d['args'], None, d['docs'], location))
                        elif d['what'] == 'newtype':
                            new_module.add_declaration(symbols.Newtype(d['name'], d['context'], d['args'], None, d['docs'], location))
                        elif d['what'] == 'data':
                            new_module.add_declaration(symbols.Data(d['name'], d['context'], d['args'], None, d['docs'], location))
                        elif d['what'] == 'class':
                            new_module.add_declaration(symbols.Class(d['name'], d['context'], d['args'], d['docs'], location))
                        else:
                            new_module.add_declaration(symbols.Declaration(d['name'], 'declaration', d['docs'], location))

                    autocompletion.database.add_file(filename, new_module)

                    if standalone:
                        # Do we need save cache for standalone files?
                        pass

                    for i in new_module.imports.values():
                        std_inspector.load_module_info(i.module)

                except Exception as e:
                    log('Inspecting file {0} failed: {1}'.format(filename, e))

            else:
                log('ModuleInspector returns error: {0}'.format(new_info['error']))

        else:
            log('ModuleInspector exited with code {0}. Stderr: {1}'.format(exit_code, stderr))


def list_files_in_dir_recursively(base_dir):
    """Return a list of a all files in a directory, recursively.
    The files will be specified by full paths."""
    files = []
    for dirname, dirnames, filenames in os.walk(base_dir):
        for filename in filenames:
            files.append(os.path.join(base_dir, dirname, filename))
    return files



inspector = None



class SublimeHaskellAutocomplete(sublime_plugin.EventListener):
    def __init__(self):
        self.local_settings = {
            'enable_ghc_mod': None,
            'use_cabal_dev': None,
            'cabal_dev_sandbox': None,
        }

        for s in self.local_settings.keys():
            self.local_settings[s] = get_setting(s)

        # Subscribe to settings changes to update data
        get_settings().add_on_change('enable_ghc_mod', lambda: self.on_setting_changed())

    def on_setting_changed(self):
        global INSPECTOR_ENABLED

        INSPECTOR_ENABLED = get_setting('inspect_modules')

        # Start the inspector if needed
        # TODO Also stop it if needed!
        if INSPECTOR_ENABLED and not INSPECTOR_RUNNING:
            start_inspector()
        elif (not INSPECTOR_ENABLED) and INSPECTOR_RUNNING:
            # TODO Implement stopping it
            log('The ModuleInspector cannot be stopped as of now. You have to restart Sublime for that.')

        same = True
        for k, v in self.local_settings.items():
            r = get_setting(k)
            same = same and v == r
            self.local_settings[k] = r

        # Update cabal status of active view
        window = sublime.active_window()
        if window:
            view = window.active_view()
            if view:
                self.set_cabal_status(view)

        if INSPECTOR_ENABLED and not same:
            # TODO: Changed completion settings! Update autocompletion data properly
            # For now at least try to load cabal modules info
            std_inspector.load_cabal_info()
            pass

    def on_query_completions(self, view, prefix, locations):
        if not is_haskell_source(view):
            return []

        begin_time = time.clock()
        # Only suggest symbols if the current file is part of a Cabal project.

        completions = (autocompletion.get_import_completions(view, prefix, locations) +
                       autocompletion.get_special_completions(view, prefix, locations))

        if not completions:
            completions = autocompletion.get_completions(view, prefix, locations)

        end_time = time.clock()
        log('time to get completions: {0} seconds'.format(end_time - begin_time))
        # Don't put completions with special characters (?, !, ==, etc.)
        # into completion because that wipes all default Sublime completions:
        # See http://www.sublimetext.com/forum/viewtopic.php?t=8659
        # TODO: work around this
        comp = [c for c in completions if NO_SPECIAL_CHARS_RE.match(c[0].split('\t')[0])]
        if get_setting('inhibit_completions') and len(comp) != 0:
            return (comp, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        return comp

    def set_cabal_status(self, view):
        filename = view.file_name()
        if filename:
            (cabal_dir, project_name) = get_cabal_project_dir_and_name_of_file(filename)
            cabal = 'cabal-dev' if get_setting_async('use_cabal_dev') else 'cabal'
            if project_name:
                view.set_status('sublime_haskell_cabal', '{0}: {1}'.format(cabal, project_name))

    def on_new(self, view):
        global INSPECTOR_ENABLED

        self.set_cabal_status(view)
        if is_haskell_source(view):
            filename = view.file_name()
            if INSPECTOR_ENABLED:
                inspector.mark_file_dirty(filename)
                inspector.mark_file_active(filename)

    def on_load(self, view):
        global INSPECTOR_ENABLED

        self.set_cabal_status(view)
        if is_haskell_source(view):
            filename = view.file_name()
            if INSPECTOR_ENABLED:
                inspector.mark_file_dirty(filename)
                inspector.mark_file_active(filename)

    def on_activated(self, view):
        self.set_cabal_status(view)

    def on_post_save(self, view):
        global INSPECTOR_ENABLED

        if is_haskell_source(view):
            if INSPECTOR_ENABLED:
                inspector.mark_file_dirty(view.file_name())

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'auto_completion_popup':
            return get_setting('auto_completion_popup')
        elif key == 'is_haskell_source':
            return is_haskell_source(view)
        elif key == "is_module_completion" or key == "is_import_completion":
            chars = {
                "is_module_completion": '.',
                "is_import_completion": '(' }

            region = view.sel()[0]
            if region.a != region.b:
                return False
            word_region = view.word(region)
            preline = get_line_contents_before_region(view, word_region)
            preline += chars[key]
            return can_complete_qualified_symbol(get_qualified_symbol(preline))
        else:
            return False


def start_inspector():
    global INSPECTOR_RUNNING

    if INSPECTOR_RUNNING:
        raise Exception('SublimeHaskell: ModuleInspector is already running!')

    log('starting ModuleInspector')

    global std_inspector
    std_inspector = StandardInspectorAgent()
    std_inspector.start()

    global inspector
    inspector = InspectorAgent()
    inspector.start()

    INSPECTOR_RUNNING = True


def plugin_loaded():
    global MODULE_INSPECTOR_SOURCE_PATH
    global MODULE_INSPECTOR_EXE_PATH
    global MODULE_INSPECTOR_OBJ_DIR
    global CABAL_INSPECTOR_SOURCE_PATH
    global CABAL_INSPECTOR_EXE_PATH
    global CABAL_INSPECTOR_OBJ_DIR
    global INSPECTOR_ENABLED
    global INSPECTOR_RUNNING

    package_path = sublime_haskell_package_path()
    cache_path = sublime_haskell_cache_path()

    MODULE_INSPECTOR_SOURCE_PATH = os.path.join(package_path, 'ModuleInspector.hs')
    MODULE_INSPECTOR_EXE_PATH = os.path.join(cache_path, 'ModuleInspector')
    MODULE_INSPECTOR_OBJ_DIR = os.path.join(cache_path, 'obj/ModuleInspector')
    CABAL_INSPECTOR_SOURCE_PATH = os.path.join(package_path, 'CabalInspector.hs')
    CABAL_INSPECTOR_EXE_PATH = os.path.join(cache_path, 'CabalInspector')
    CABAL_INSPECTOR_OBJ_DIR = os.path.join(cache_path, 'obj/CabalInspector')
    INSPECTOR_ENABLED = get_setting('inspect_modules')

    if INSPECTOR_ENABLED:
        start_inspector()

    # TODO: How to stop_hdevtools() in Sublime Text 2?
    start_hdevtools()

def plugin_unloaded():
    # Does this work properly on exit?
    stop_hdevtools()

if int(sublime.version()) < 3000:
    plugin_loaded()

########NEW FILE########
__FILENAME__ = cabalbuild
import os
import sublime
import sublime_plugin
import copy
from threading import Thread

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    from parseoutput import run_chain_build_thread
    from autocomplete import autocompletion
else:
    from SublimeHaskell.sublime_haskell_common import *
    from SublimeHaskell.parseoutput import run_chain_build_thread
    from SublimeHaskell.autocomplete import autocompletion

OUTPUT_PANEL_NAME = "haskell_run_output"

cabal_tool = {
    True: {'command': 'cabal-dev', 'message': 'Cabal-Dev', 'extra': lambda cmd: attach_sandbox(cmd)},
    False: {'command': 'cabal', 'message': 'Cabal', 'extra': lambda cmd: cmd},
}

cabal_config = {
    'clean': {'steps': [['clean']], 'message': 'Cleaning'},
    'configure': {'steps': [['configure', '--enable-tests']], 'message': 'Configure'},
    'build': {'steps': [['build']], 'message': 'Building'},
    'typecheck': {'steps': [['build', '--ghc-options=-c']], 'message': 'Checking'},
    # Commands with warnings:
    # Run fast, incremental build first. Then build everything with -Wall and -fno-code
    # If the incremental build fails, the second step is not executed.
    'build_then_warnings': {'steps': [['build'], ['build', '-v0', '--ghc-options=-fforce-recomp -Wall -fno-code']], 'message': 'Building'},
    'typecheck_then_warnings': {'steps': [['build', '--ghc-options=-c'], ['build', '-v0', '--ghc-options=-fforce-recomp -Wall -fno-code']], 'message': 'Checking'},

    'rebuild': {'steps': [['clean'], ['configure', '--enable-tests'], ['build']], 'message': 'Rebuilding'},
    'install': {'steps': [['install', '--enable-tests']], 'message': 'Installing'},
    'test': {'steps': [['test']], 'message': 'Testing'}
}


# GLOBAL STATE

# Contains names of projects currently being built.
# To be updated only from the UI thread.
projects_being_built = set()


# Base command
class SublimeHaskellBaseCommand(sublime_plugin.WindowCommand):

    def build(self, command, use_cabal_dev=None, filter_project = None):
        select_project(
            self.window,
            lambda n, d: run_build(self.window.active_view(), n, d, cabal_config[command], use_cabal_dev),
            filter_project = filter_project)


# Select project from list
# on_selected accepts name of project and directory of project
# filter_project accepts name of project and project-info as it appears in AutoCompletion object
#   and returns whether this project must appear in selection list
def select_project(window, on_selected, filter_project = None):
    ps = [(name, info) for (name, info) in autocompletion.projects.object.items() if not filter_project or filter_project(name, info)]

    def run_selected(psel):
        on_selected(psel[0], psel[1]['dir'])

    if len(ps) == 0:
        return
    if len(ps) == 1:  # There's only one project, build it
        run_selected(ps[0])
        return

    cabal_project_dir, cabal_project_name = get_cabal_project_dir_and_name_of_view(window.active_view())

    # Returns tuple to sort by
    #   is this project is current? return False to be first on sort
    #   name of project to sort alphabetically
    def compare(proj_name):
        return (proj_name != cabal_project_name, proj_name)

    ps.sort(key = lambda p: compare(p[0]))

    def on_done(idx):
        if idx != -1:
            run_selected(ps[idx])

    window.show_quick_panel(list(map(lambda m: [m[0], m[1]['dir']], ps)), on_done)


def run_build(view, project_name, project_dir, config, use_cabal_dev=None):
    global projects_being_built

    # Don't build if a build is already running for this project
    # We compare the project_name for simplicity (projects with same
    # names are of course possible, but unlikely, so we let them wait)
    if project_name in projects_being_built:
        log("Not building '%s' because it is already being built" % project_name)
        sublime_status_message('Already building %s' % project_name)
        return
    # Set project as building
    projects_being_built.add(project_name)

    # Run cabal or cabal-dev
    if use_cabal_dev is None:
        use_cabal_dev = get_setting_async('use_cabal_dev')

    tool = cabal_tool[use_cabal_dev]

    # Title of tool: Cabal, Cabal-Dev
    tool_title = tool['message']
    # Title of action: Cleaning, Building, etc.
    action_title = config['message']
    # Extra arguments lambda
    extra_args = tool['extra']
    # Tool name: cabal, cabal-dev
    tool_name = tool['command']
    # Tool arguments (commands): build, clean, etc.
    tool_steps = config['steps']

    # Assemble command lines to run (possibly multiple steps)
    commands = [extra_args([tool_name] + step) for step in tool_steps]

    log('running build commands: {0}'.format(commands))

    def done_callback():
        # Set project as done being built so that it can be built again
        projects_being_built.remove(project_name)

    # Run them
    run_chain_build_thread(
        view,
        project_dir,
        tool_title + ': ' + action_title + ' ' + project_name,
        commands,
        on_done=done_callback)


class SublimeHaskellSwitchCabalDev(sublime_plugin.WindowCommand):
    def run(self):
        use_cabal_dev = get_setting('use_cabal_dev')
        sandbox = get_setting('cabal_dev_sandbox')
        sandboxes = get_setting('cabal_dev_sandbox_list')

        sandboxes.append(sandbox)
        sandboxes = list(set(sandboxes))
        set_setting('cabal_dev_sandbox_list', sandboxes)

        # No candboxes
        if len(sandboxes) == 0:
            sublime_status_message('There is nothing to switch to')
            set_setting('use_cabal_dev', False)
            save_settings()
            return

        # One sandbox, just switch
        if len(sandboxes) == 1:
            set_setting('use_cabal_dev', not use_cabal_dev)
            if use_cabal_dev:
                now_using = 'Cabal'
            else:
                now_using = 'Cabal-Dev'
            sublime_status_message('Switched to ' + now_using)
            save_settings()
            return

        # Many sandboxes, show list
        self.sorted_sands = sandboxes
        # Move previously used sandbox (or cabal) on top
        self.sorted_sands.remove(sandbox)
        if use_cabal_dev:
            self.sorted_sands.insert(0, sandbox)
            self.sorted_sands.insert(0, "<Cabal>")
        else:
            self.sorted_sands.insert(0, "<Cabal>")
            self.sorted_sands.insert(0, sandbox)

        self.window.show_quick_panel(self.sorted_sands, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        selected = self.sorted_sands[idx]
        if selected == "<Cabal>":
            set_setting('use_cabal_dev', False)
        else:
            set_setting('use_cabal_dev', True)
            set_setting('cabal_dev_sandbox', selected)

        save_settings()


# Default build system (cabal or cabal-dev)

class SublimeHaskellClean(SublimeHaskellBaseCommand):
    def run(self):
        self.build('clean')


class SublimeHaskellConfigure(SublimeHaskellBaseCommand):
    def run(self):
        self.build('configure')


class SublimeHaskellBuild(SublimeHaskellBaseCommand):
    def run(self):
        self.build('build_then_warnings')


class SublimeHaskellTypecheck(SublimeHaskellBaseCommand):
    def run(self):
        self.build('typecheck_then_warnings')


class SublimeHaskellRebuild(SublimeHaskellBaseCommand):
    def run(self):
        self.build('rebuild')


class SublimeHaskellInstall(SublimeHaskellBaseCommand):
    def run(self):
        self.build('install')

class SublimeHaskellTest(SublimeHaskellBaseCommand):
    def run(self):
        def has_tests(name, info):
            return len(info['tests']) > 0

        self.build('test', filter_project = has_tests)

# Auto build current project
class SublimeHaskellBuildAuto(SublimeHaskellBaseCommand):
    def run(self):
        current_project_dir, current_project_name = get_cabal_project_dir_and_name_of_view(self.window.active_view())
        if current_project_name and current_project_dir:
            build_mode = get_setting('auto_build_mode')
            run_tests = get_setting('auto_run_tests')

            build_command = {
               'normal': 'build',
               'normal-then-warnings': 'build_then_warnings',
               'typecheck': 'typecheck',
               'typecheck-then-warnings': 'typecheck_then_warnings',
            }.get(build_mode)

            if not build_command:
                output_error(self.window, "SublimeHaskell: invalid auto_build_mode '%s'" % build_mode)

            config = copy.deepcopy(cabal_config[build_command])

            if run_tests:
                has_tests = False

                with autocompletion.projects as projects:
                    if current_project_name in projects:
                        has_tests = len(projects[current_project_name]['tests']) > 0

                if has_tests:
                    config['steps'].extend(cabal_config['test']['steps'])

            run_build(self.window.active_view(), current_project_name, current_project_dir, config, None)


class SublimeHaskellRun(SublimeHaskellBaseCommand):
    def run(self):
        self.executables = []
        ps = []
        with autocompletion.projects as projects:
            for p, info in projects.items():
                for e in info['executables']:
                    ps.append((p + ": " + e['name'], {
                        'dir': info['dir'],
                        'name': e['name']
                    }))

        # Nothing to run
        if len(ps) == 0:
            sublime_status_message('Nothing to run')
            return

        cabal_project_dir, cabal_project_name = get_cabal_project_dir_and_name_of_view(self.window.active_view())

        # Show current project first
        ps.sort(key = lambda s: (not s[0].startswith(cabal_project_name), s[0]))

        self.executables = list(map(lambda m: m[1], ps))
        self.window.show_quick_panel(list(map(lambda m: m[0], ps)), self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        selected = self.executables[idx]
        name = selected['name']
        base_dir = selected['dir']
        bin_file = os.path.join(selected['dir'], 'dist', 'build', name, name)

        hide_output(self.window)

        # Run in thread
        thread = Thread(
            target=run_binary,
            args=(name, bin_file, base_dir))
        thread.start()


def run_binary(name, bin_file, base_dir):
    with status_message_process('Running {0}'.format(name), priority = 5) as s:
        exit_code, out, err = call_and_wait(bin_file, cwd=base_dir)
        window = sublime.active_window()
        if not window:
            return
        if exit_code == 0:
            sublime.set_timeout(lambda: write_output(window, out, base_dir), 0)
        else:
            s.fail()
            sublime.set_timeout(lambda: write_output(window, err, base_dir), 0)


def write_output(window, text, base_dir):
    "Write text to Sublime's output panel."
    output_view = window.get_output_panel(OUTPUT_PANEL_NAME)
    output_view.set_read_only(False)
    # Configure Sublime's error message parsing:
    output_view.settings().set("result_base_dir", base_dir)
    # Write to the output buffer:
    output_view.run_command('sublime_haskell_output_text', {
        'text': text })
    # Set the selection to the beginning of the view so that "next result" works:
    output_view.sel().clear()
    output_view.sel().add(sublime.Region(0))
    output_view.set_read_only(True)
    # Show the results panel:
    window.run_command('show_panel', {'panel': 'output.' + OUTPUT_PANEL_NAME})


def hide_output(window):
    window.run_command('hide_panel', {'panel': 'output.' + OUTPUT_PANEL_NAME})

def run_build_commands_with(msg, cmds):
    """Run general build commands"""
    window, view, file_shown_in_view = get_haskell_command_window_view_file_project()
    if not file_shown_in_view:
        return
    syntax_file_for_view = view.settings().get('syntax').lower()
    if 'haskell' not in syntax_file_for_view:
        return
    cabal_project_dir, cabal_project_name = get_cabal_project_dir_and_name_of_view(view)
    if not cabal_project_dir:
        return

    run_chain_build_thread(view, cabal_project_dir, msg(cabal_project_name), cmds)

def run_build_command_with(msg, cmd):
    """Run one command"""
    run_build_commands_with(msg, [cmd])

########NEW FILE########
__FILENAME__ = cache
import json
import os
import sublime

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    import symbols
else:
    from SublimeHaskell.sublime_haskell_common import *
    import SublimeHaskell.symbols as symbols

CACHE_PATH = None
CABAL_CACHE_PATH = None
PROJECTS_CACHE_PATH = None

def swap_dict(d):
    """
    {key => (item, value)} => {item => (key, value)}
    """
    return dict((v[0], (k, v[1])) for k, v in d.items())

def as_object(serializers, dct):
    """
    Parse JSON as object
    Serializers is dictionary name => serializer, where
    serializer is tuple (type, list of field in order of appearance in constructor)
    """
    sers = swap_dict(serializers)
    if '__type__' in dct:
        if dct['__type__'] in sers:
            (load_type, fields) = sers[dct['__type__']]
            return load_type(*[dct.get(f) for f in fields])
        else:
            raise RuntimeError("Unknown type '{0}'".format(dct['__type__']))
    else:
        return dct

class SymbolsEncoder(json.JSONEncoder):
    def __init__(self, serializers = None, **kwargs):
        super(SymbolsEncoder, self).__init__(**kwargs)
        self.serializers = serializers

    def default(self, obj):
        if type(obj) in self.serializers:
            (name, args) = self.serializers[type(obj)]
            result = dict((k, v) for k, v in obj.__dict__.items() if k in args)
            result.update({'__type__': name})
            return result
        return json.JSONEncoder.default(self, obj)

def symbol_serializers():
    return {
        symbols.Location: ('location', ['filename', 'line', 'column', 'project']),
        symbols.Symbol: ('symbol', ['what', 'name', 'docs', 'location']),
        symbols.Import: ('import', ['module', 'is_qualified', 'import_as']),
        symbols.Module: ('module', ['name', 'exports', 'imports', 'declarations', 'location', 'cabal', 'last_inspection_time']),
        symbols.Declaration: ('declaration', ['name', 'what', 'docs', 'location']),
        symbols.Function: ('function', ['name', 'type', 'docs', 'location']),
        symbols.TypeBase: ('typebase', ['name', 'what', 'context', 'args', 'definition', 'docs', 'location']),
        symbols.Type: ('type', ['name', 'context', 'args', 'definition', 'docs', 'location']),
        symbols.Newtype: ('newtype', ['name', 'context', 'args', 'definition', 'docs', 'location']),
        symbols.Data: ('data', ['name', 'context', 'args', 'definition', 'docs', 'location']),
        symbols.Class: ('class', ['name', 'context', 'args', 'docs', 'location']) }

def encode_json(obj, **kwargs):
    return json.dumps(obj, cls = SymbolsEncoder, serializers = symbol_serializers(), **kwargs)

def decode_json(s):
    return json.loads(s, object_hook = lambda v: as_object(symbol_serializers(), v))

def escape_path(path):
    path = os.path.abspath(os.path.normcase(path))
    folders = []
    (base, name) = os.path.split(path)
    while name:
        folders.append(name)
        (base, name) = os.path.split(base)
    if base:
        folders.append(''.join(filter(lambda c: c.isalpha() or c.isdigit(), base)))
    folders.reverse()
    return '.'.join(folders)

def dump_cabal_cache(database, cabal_name = None):
    if not cabal_name:
        cabal_name = current_cabal()
    formatted_json = None
    with database.get_cabal_modules(cabal_name) as cabal_modules:
        cabal_path = escape_path(cabal_name) if cabal_name != 'cabal' else 'cabal'
        cabal_json = os.path.join(CABAL_CACHE_PATH, cabal_path + '.json')
        formatted_json = encode_json(cabal_modules, indent = 2)
    with open(cabal_json, 'w') as f:
        f.write(formatted_json)

def dump_project_cache(database, project_path):
    formatted_json = None
    project_modules = database.get_project_modules(project_path)
    with database.files:
        project_json = os.path.join(PROJECTS_CACHE_PATH, escape_path(project_path) + '.json')
        formatted_json = encode_json(project_modules, indent = 2)
    with open(project_json, 'w') as f:
        f.write(formatted_json)

def load_cabal_cache(database, cabal_name = None):
    if not cabal_name:
        cabal_name = current_cabal()
    formatted_json = None
    cabal_path = escape_path(cabal_name) if cabal_name != 'cabal' else 'cabal'
    cabal_json = os.path.join(CABAL_CACHE_PATH, cabal_path + '.json')
    if os.path.exists(cabal_json):
        with open(cabal_json, 'r') as f:
            formatted_json = f.read()
    if formatted_json:
        cabal_modules = decode_json(formatted_json)
        for m in cabal_modules.values():
            database.add_module(m, cabal_name)

def load_project_cache(database, project_path):
    formatted_json = None
    project_json = os.path.join(PROJECTS_CACHE_PATH, escape_path(project_path) + '.json')
    if os.path.exists(project_json):
        with open(project_json, 'r') as f:
            formatted_json = f.read()
    if formatted_json:
        project_modules = decode_json(formatted_json)
        for m in project_modules.values():
            database.add_file(m.location.filename, m)

def plugin_loaded():
    global CACHE_PATH
    global CABAL_CACHE_PATH
    global PROJECTS_CACHE_PATH

    package_path = sublime_haskell_package_path()
    cache_path = sublime_haskell_cache_path()

    CACHE_PATH = os.path.join(cache_path, 'cache')
    CABAL_CACHE_PATH = os.path.join(CACHE_PATH, 'cabal')
    PROJECTS_CACHE_PATH = os.path.join(CACHE_PATH, 'projects')

    if not os.path.exists(CACHE_PATH):
        os.mkdir(CACHE_PATH)

    if not os.path.exists(CABAL_CACHE_PATH):
        os.mkdir(CABAL_CACHE_PATH)

    if not os.path.exists(PROJECTS_CACHE_PATH):
        os.mkdir(PROJECTS_CACHE_PATH)

if int(sublime.version()) < 3000:
    plugin_loaded()

########NEW FILE########
__FILENAME__ = fix_syntax
# Sublime's built-in Haskell lexer (Packages/Haskell/Haskell.tmLanguage)
# is slightly broken.
#
# This sets the syntax of all Haskell files to our
# SublimeHaskell/Syntaxes/Haskell-SublimeHaskell.tmLanguage instead.
#
# Forked from https://gist.github.com/2940866.
import sublime_plugin
import os


class DetectFileTypeCommand(sublime_plugin.EventListener):

    def on_load(self, view):
        filename = view.file_name()
        if not filename:  # buffer has never been saved
            return

        name = os.path.basename(filename.lower())
        if name.endswith(".hs") or name.endswith(".hsc"):
            set_our_syntax(view, filename)
        # TODO Do we also have to fix Literate Haskell?


def set_our_syntax(view, filename):
    view.settings().set('syntax', 'Packages/SublimeHaskell/Syntaxes/Haskell-SublimeHaskell.tmLanguage')
    print("Switched syntax to SublimeHaskell's fixed Haskell syntax: " + filename)

########NEW FILE########
__FILENAME__ = ghci
import re
import os
import sublime
import sublime_plugin

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    import symbols
else:
    from SublimeHaskell.sublime_haskell_common import *
    import SublimeHaskell.symbols as symbols

def parse_info(name, contents):
    """
    Parses result of :i <name> command of ghci and returns derived symbols.Declaration
    """
    functionRegex = '{0}\s+::\s+(?P<type>.*?)(\s+--(.*))?$'.format(name)
    dataRegex = '(?P<what>(newtype|type|data))\s+((?P<ctx>(.*))=>\s+)?(?P<name>\S+)\s+(?P<args>(\w+\s+)*)=(\s*(?P<def>.*)\s+-- Defined)?'
    classRegex = '(?P<what>class)\s+((?P<ctx>(.*))=>\s+)?(?P<name>\S+)\s+(?P<args>(\w+\s+)*)(.*)where$'

    if name[0].isupper():
        # data, class, type or newtype
        matched = re.search(dataRegex, contents, re.MULTILINE) or re.search(classRegex, contents, re.MULTILINE)
        if matched:
            what = matched.group('what')
            args = matched.group('args').strip().split(' ') if matched.group('args') else []
            ctx = matched.group('ctx')
            definition = matched.group('def')
            if definition:
                definition.strip()

            if what == 'class':
                return symbols.Class(name, ctx, args)
            elif what == 'data':
                return symbols.Data(name, ctx, args, definition)
            elif what == 'type':
                return symbols.Type(name, ctx, args, definition)
            elif what == 'newtype':
                return symbols.Newtype(name, ctx, args, definition)
            else:
                raise RuntimeError('Unknown type of symbol: {0}'.format(what))

    else:
        # function
        matched = re.search(functionRegex, contents, re.MULTILINE)
        if matched:
            return symbols.Function(name, matched.group('type'))

    return None

def ghci_info(module, name, cabal = None):
    """
    Returns info for name as symbol
    """
    ghci_cmd = [
        ":m + " + module,
        ":i " + module + "." + name,
        ":q"]
    ghc_opts = get_setting_async('ghc_opts')

    (exit_code, stdout, stderr) = call_and_wait_with_input(ghci_append_package_db(['ghci'] + ghc_opts, cabal = cabal), "\n".join(ghci_cmd))
    stdout = crlf2lf(stdout)
    if exit_code == 0:
        return parse_info(name, stdout)

    return None

########NEW FILE########
__FILENAME__ = ghcmod
import os
import re
import sublime
import sublime_plugin
from threading import Thread

if int(sublime.version()) < 3000:
    from sublime_haskell_common import log, is_haskell_source, get_haskell_command_window_view_file_project, call_ghcmod_and_wait, get_setting_async
    from parseoutput import parse_output_messages, show_output_result_text, format_output_messages, mark_messages_in_views, hide_output, set_global_error_messages
    from ghci import parse_info
    import symbols
else:
    from SublimeHaskell.sublime_haskell_common import log, is_haskell_source, get_haskell_command_window_view_file_project, call_ghcmod_and_wait, get_setting_async
    from SublimeHaskell.parseoutput import parse_output_messages, show_output_result_text, format_output_messages, mark_messages_in_views, hide_output, set_global_error_messages
    from SublimeHaskell.ghci import parse_info
    import SublimeHaskell.symbols as symbols


def lint_as_hints(msgs):
    for m in msgs:
        if m[0] == 'lint':
            m[1].level = 'hint'


class SublimeHaskellGhcModCheck(sublime_plugin.WindowCommand):
    def run(self):
        run_ghcmod(['check'], 'Checking')

    def is_enabled(self):
        return is_haskell_source(None)


class SublimeHaskellGhcModLint(sublime_plugin.WindowCommand):
    def run(self):
        run_ghcmod(['lint', '-h', '-u'], 'Linting', lint_as_hints)

    def is_enabled(self):
        return is_haskell_source(None)


class SublimeHaskellGhcModCheckAndLint(sublime_plugin.WindowCommand):
    def run(self):
        run_ghcmods([['check'], ['lint', '-h', '-u']], 'Checking and Linting', lint_as_hints)

    def is_enabled(self):
        return is_haskell_source(None)


def run_ghcmods(cmds, msg, alter_messages_cb=None):
    """
    Run several ghcmod commands, concats result messages with callback
    and show output.
    alter_messages_cb accepts dictionary (cmd => list of output messages)
    """
    window, view, file_shown_in_view = get_haskell_command_window_view_file_project()
    if not file_shown_in_view:
        return

    file_dir, file_name = os.path.split(file_shown_in_view)

    ghc_mod_args = []
    for cmd in cmds:
        ghc_mod_args.append((cmd, cmd + [file_shown_in_view]))

    def show_current_file_first_and_alter(msgs):
        if alter_messages_cb:
            alter_messages_cb(msgs)

        def compare(l, r):
            # sort by file equality to file_name
            res = cmp(l[1].filename != file_shown_in_view, r[1].filename != file_shown_in_view)
            if res == 0:
                # then by file
                res = cmp(l[1].filename, r[1].filename)
                if res == 0:
                    # then by line
                    res = cmp(l[1].line, r[1].line)
                    if res == 0:
                        # then by column
                        res = cmp(l[1].column, r[1].column)
            return res

        def sort_key(a):
            return (
                a[1].filename != file_shown_in_view,
                a[1].filename,
                a[1].line,
                a[1].column
            )

        msgs.sort(key=sort_key)

    run_ghcmods_thread(view, file_shown_in_view, 'Ghc-Mod: ' + msg + ' ' + file_name, ghc_mod_args, show_current_file_first_and_alter)


def run_ghcmod(cmd, msg, alter_messages_cb=None):
    run_ghcmods([cmd], msg, alter_messages_cb)


def run_ghcmods_thread(view, filename, msg, cmds_with_args, alter_messages_cb):
    sublime.status_message(msg + '...')
    thread = Thread(
        target=wait_ghcmod_and_parse,
        args=(view, filename, msg, cmds_with_args, alter_messages_cb))
    thread.start()


def wait_ghcmod_and_parse(view, filename, msg, cmds_with_args, alter_messages_cb):
    sublime.set_timeout(lambda: hide_output(view), 0)

    parsed_messages = []

    file_dir = os.path.dirname(filename)

    all_cmds_successful = True
    all_cmds_outputs = []

    for (cmd, args) in cmds_with_args:
        stdout = call_ghcmod_and_wait(args, filename)

        # stdout contains NULL as line endings within one message
        # error_output_regex using indents to determine one message scope
        # Replace NULLs to indents
        out = stdout.replace('\0', '\n  ')

        success = len(out.strip()) == 0

        if not success:
            all_cmds_outputs.append(out)
            log(u"ghc-mod %s didn't exit with success on '%s'" % (u' '.join(cmd), filename))

        all_cmds_successful &= success

        parsed = parse_output_messages(file_dir, out)
        for p in parsed:
            parsed_messages.append((cmd, p))

    if alter_messages_cb:
        alter_messages_cb(parsed_messages)

    concated_messages = [m[1] for m in parsed_messages]

    # Set global error list
    set_global_error_messages(concated_messages)

    sublime.set_timeout(lambda: mark_messages_in_views(concated_messages), 0)

    output_text = (format_output_messages(concated_messages) if parsed_messages
                   else '\n'.join(all_cmds_outputs))

    exit_code = 0 if all_cmds_successful else 1

    show_output_result_text(view, msg, output_text, exit_code, file_dir)

def ghcmod_browse_module(module_name, cabal = None):
    """
    Returns symbols.Module with all declarations
    """
    contents = call_ghcmod_and_wait(['browse', '-d', module_name], cabal = cabal).splitlines()

    if not contents:
        return None

    m = symbols.Module(module_name, cabal = cabal)

    functionRegex = r'(?P<name>\w+)\s+::\s+(?P<type>.*)'
    typeRegex = r'(?P<what>(class|type|data|newtype))\s+(?P<name>\w+)(\s+(?P<args>\w+(\s+\w+)*))?'

    def toDecl(line):
        matched = re.search(functionRegex, line)
        if matched:
            return symbols.Function(matched.group('name'), matched.group('type'))
        else:
            matched = re.search(typeRegex, line)
            if matched:
                decl_type = matched.group('what')
                decl_name = matched.group('name')
                decl_args = matched.group('args')
                decl_args = decl_args.split() if decl_args else []

                if decl_type == 'class':
                    return symbols.Class(decl_name, None, decl_args)
                elif decl_type == 'data':
                    return symbols.Data(decl_name, None, decl_args)
                elif decl_type == 'type':
                    return symbols.Type(decl_name, None, decl_args)
                elif decl_type == 'newtype':
                    return symbols.Newtype(decl_name, None, decl_args)
            else:
                return symbols.Declaration(line)

    decls = map(toDecl, contents)
    for decl in decls:
        m.add_declaration(decl)

    return m

def ghcmod_info(filename, module_name, symbol_name, cabal = None):
    """
    Uses ghc-mod info filename module_name symbol_name to get symbol info
    """
    contents = call_ghcmod_and_wait(['info', filename, module_name, symbol_name], filename = filename, cabal = cabal)
    # TODO: Returned symbol doesn't contain location
    # But in fact we use ghcmod_info only to retrieve type of symbol
    return parse_info(symbol_name, contents)

def ghcmod_type(filename, module_name, line, column, cabal = None):
    """
    Uses ghc-mod type to infer type
    """
    return call_ghcmod_and_wait(['type', filename, module_name, str(line), str(column)], filename = filename, cabal = cabal)

def ghcmod_enabled():
    return get_setting_async('enable_ghc_mod') == True

########NEW FILE########
__FILENAME__ = haskell_docs
import re
import os
import sublime
import sublime_plugin

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
else:
    from SublimeHaskell.sublime_haskell_common import *

def haskell_docs(module, name):
    """
    Returns info for name as multiline string
    """
    try:
        (exit_code, stdout, stderr) = call_and_wait(["haskell-docs", module, name])
        stdout = crlf2lf(stdout)
        if exit_code == 0:
            ambigousRe = '^Ambiguous module, belongs to more than one package: (.*)$'
            continueRe = '^Continuing anyway... $'
            cantFindRe = '^Couldn\'t find name ``{0}\'\' in Haddock interface: (.*)$'.format(name)
            packageRe = '^Package: (.*)$'
            ignoreRe = '({0})|({1})|({2})|({3})'.format(ambigousRe, continueRe, cantFindRe, packageRe)

            # Remove debug messages
            result = list(filter(lambda l: not re.match(ignoreRe, l), stdout.splitlines()))
            return '\n'.join(result)
    except OSError as e:
        if e.errno == errno.ENOENT:
            log("haskell-docs not found, no docs available, try 'cabal install haskell-docs'")
    return None

########NEW FILE########
__FILENAME__ = haskell_type
import sublime
import sublime_plugin
import re

if int(sublime.version()) < 3000:
    from sublime_haskell_common import is_enabled_haskell_command, get_setting_async, show_status_message
    from autocomplete import autocompletion
    from hdevtools import hdevtools_type, hdevtools_enabled
    from ghcmod import ghcmod_type, ghcmod_enabled
else:
    from SublimeHaskell.sublime_haskell_common import is_enabled_haskell_command, get_setting_async, show_status_message
    from SublimeHaskell.autocomplete import autocompletion
    from SublimeHaskell.hdevtools import hdevtools_type, hdevtools_enabled
    from SublimeHaskell.ghcmod import ghcmod_type, ghcmod_enabled
    from functools import reduce

# Used to find out the module name.
MODULE_RE_STR = r'module\s+([^\s\(]*)'  # "module" followed by everything that is neither " " nor "("
MODULE_RE = re.compile(MODULE_RE_STR)

# Parses the output of `ghc-mod type`.
# Example: 39 1 40 17 "[Char]"
GHCMOD_TYPE_LINE_RE = re.compile(r'(?P<startrow>\d+) (?P<startcol>\d+) (?P<endrow>\d+) (?P<endcol>\d+) "(?P<type>.*)"')

# Name of the sublime panel in which type information is shown.
TYPE_PANEL_NAME = 'haskell_type_panel'

def parse_ghc_mod_type_line(l):
    """
    Returns the `groupdict()` of GHCMOD_TYPE_LINE_RE matching the given line,
    of `None` if it doesn't match.
    """
    match = GHCMOD_TYPE_LINE_RE.match(l)
    return match and match.groupdict()

def tabs_offset(view, point):
    """
    Returns count of '\t' before point in line multiplied by 7
    8 is size of type as supposed by ghc-mod, to every '\t' will add 7 to column
    Subtract this value to get sublime column by ghc-mod column, add to get ghc-mod column by sublime column
    """
    cur_line = view.substr(view.line(point))
    return len(list(filter(lambda ch: ch == '\t', cur_line))) * 7

def sublime_column_to_type_column(view, line, column):
    cur_line = view.substr(view.line(view.text_point(line, column)))
    return column + len(list(filter(lambda ch: ch == '\t', cur_line))) * 7 + 1

def type_column_to_sublime_column(view, line, column):
    cur_line = view.substr(view.line(view.text_point(line - 1, 0)))
    col = 1
    real_col = 0
    for c in cur_line:
        if col >= column:
            return real_col
        col += (8 if c == '\t' else 1)
        real_col += 1
    return real_col

class FilePosition(object):
    def __init__(self, line, column):
        self.line = line
        self.column = column

    def point(self, view):
        # Note, that sublime suppose that '\t' is 'tab_size' length
        # But '\t' is one character
        return view.text_point(self.line - 1, type_column_to_sublime_column(view, self.line, self.column))

def position_by_point(view, point):
    tabs = tabs_offset(view, point)
    (r, c) = view.rowcol(point)
    return FilePosition(r + 1, c + 1 + tabs)

class RegionType(object):
    def __init__(self, typename, start, end = None):
        self.typename = typename
        self.start = start
        self.end = end if end else start

    def region(self, view):
        return sublime.Region(self.start.point(view), self.end.point(view))

    def substr(self, view):
        return view.substr(self.region(view))

    def show(self, view):
        return '{0} :: {1}'.format(self.substr(view), self.typename)

    def precise_in_region(self, view, other):
        this_region = self.region(view)
        other_region = other.region(view)
        if other_region.contains(this_region):
            return (0, other_region.size() - this_region.size())
        elif other_region.intersects(this_region):
            return (1, -other_region.intersection(this_region).size())
        return (2, 0)

def region_by_region(view, region, typename):
    return RegionType(typename, position_by_point(view, region.a), position_by_point(view, region.b))

TYPE_RE = re.compile(r'(?P<line1>\d+)\s+(?P<col1>\d+)\s+(?P<line2>\d+)\s+(?P<col2>\d+)\s+"(?P<type>.*)"$')

def parse_type_output(s):
    result = []
    for l in s.splitlines():
        matched = TYPE_RE.match(l)
        if matched:
            result.append(RegionType(
                matched.group('type'),
                FilePosition(int(matched.group('line1')), int(matched.group('col1'))),
                FilePosition(int(matched.group('line2')), int(matched.group('col2')))))

    return result

def haskell_type(filename, module_name, line, column, cabal = None):
    result = None

    if hdevtools_enabled():
        result = hdevtools_type(filename, line, column, cabal = cabal)
    if not result and module_name and ghcmod_enabled():
        result = ghcmod_type(filename, module_name, line, column, cabal = cabal)
    return parse_type_output(result) if result else None

class SublimeHaskellShowType(sublime_plugin.TextCommand):
    def run(self, edit, filename = None, line = None, column = None):
        result = self.get_types(filename, int(line) if line else None, int(column) if column else None)
        self.show_types(result)

    def get_types(self, filename = None, line = None, column = None):
        if not filename:
            filename = self.view.file_name()

        if (not line) or (not column):
            (r, c) = self.view.rowcol(self.view.sel()[0].b)
            line = r + 1
            column = c + 1

        column = sublime_column_to_type_column(self.view, r, c)

        module_name = None
        with autocompletion.database.files as files:
            if filename in files:
                module_name = files[filename].name

        return haskell_type(filename, module_name, line, column)

    def get_best_type(self, types):
        if not types:
            return None

        region = self.view.sel()[0]
        file_region = region_by_region(self.view, region, '')
        if region.a != region.b:
            return sorted(types, key = lambda r: file_region.precise_in_region(self.view, r))[0]
        else:
            return types[0]

    def show_types(self, types):
        if not types:
            show_status_message("Can't infer type", False)
            return

        best_result = self.get_best_type(types)

        type_text = [best_result.show(self.view), '']
        type_text.extend([r.show(self.view) for r in types if r.start.line == r.end.line])

        output_view = self.view.window().get_output_panel('sublime_haskell_hdevtools_type')
        output_view.set_read_only(False)

        output_view.run_command('sublime_haskell_output_text', {
            'text': '\n'.join(type_text) })

        output_view.sel().clear()
        output_view.set_read_only(True)

        self.view.window().run_command('show_panel', {
            'panel': 'output.sublime_haskell_hdevtools_type' })

    def is_enabled(self):
        return is_enabled_haskell_command(self.view, False)


# Works only with the cursor being in the name of a toplevel function so far.
class SublimeHaskellInsertType(SublimeHaskellShowType):
    def run(self, edit):
        result = self.get_best_type(self.get_types())
        if result:
            r = result.region(self.view)
            name = self.view.substr(self.view.word(r.begin()))
            line_begin = self.view.line(r).begin()
            prefix = self.view.substr(sublime.Region(line_begin, r.begin()))
            indent = re.search('(?P<indent>\s*)', prefix).group('indent')
            signature = '{0}{1} :: {2}\n'.format(indent, name, result.typename)
            self.view.insert(edit, line_begin, signature)

########NEW FILE########
__FILENAME__ = hdevtools
import os
import re
import sublime
import sublime_plugin
import subprocess
import threading

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    from ghci import parse_info
    import symbols
else:
    from SublimeHaskell.sublime_haskell_common import *
    from SublimeHaskell.ghci import parse_info
    import SublimeHaskell.symbols as symbols


def show_hdevtools_error_and_disable():
    # Looks like we can't always get an active window here,
    # we use sublime.error_message() instead of
    # output_error(sublime.active_window().
    sublime.set_timeout(lambda: sublime.error_message(
        "SublimeHaskell: hdevtools was not found!\n"
        + "It's used for 'symbol info' and type inference\n"
        + "Install it with 'cabal install hdevtools',\n"
        + "or adjust the 'add_to_PATH' setting for a custom location.\n"
        + "'enable_hdevtools' automatically set to False in the User settings."), 0)

    set_setting_async('enable_hdevtools', False)


def call_hdevtools_and_wait(arg_list, filename = None, cabal = None):
    """
    Calls hdevtools with the given arguments.
    Shows a sublime error message if hdevtools is not available.
    """
    if not hdevtools_enabled():
        return None

    ghc_opts_args = get_ghc_opts_args(filename, cabal = cabal)
    hdevtools_socket = get_setting_async('hdevtools_socket')
    source_dir = get_source_dir(filename)

    if hdevtools_socket:
        arg_list.append('--socket={0}'.format(hdevtools_socket))

    try:
        exit_code, out, err = call_and_wait(['hdevtools'] + arg_list + ghc_opts_args, cwd = source_dir)

        if exit_code != 0:
            raise Exception("hdevtools exited with status %d and stderr: %s" % (exit_code, err))

        return crlf2lf(out)

    except OSError as e:
        if e.errno == errno.ENOENT:
            show_hdevtools_error_and_disable()

        return None

    except Exception as e:
        log('calling to hdevtools fails with {0}'.format(e))
        return None

def admin(cmds, wait = False, **popen_kwargs):
    if not hdevtools_enabled():
        return None

    hdevtools_socket = get_setting_async('hdevtools_socket')

    if hdevtools_socket:
        cmds.append('--socket={0}'.format(hdevtools_socket))

    command = ["hdevtools", "admin"] + cmds

    try:
        if wait:
            (exit_code, stdout, stderr) = call_and_wait(command, **popen_kwargs)
            if exit_code == 0:
                return stdout
            return ''
        else:
            call_no_wait(command, **popen_kwargs)
            return ''

    except OSError as e:
        if e.errno == errno.ENOENT:
            show_hdevtools_error_and_disable()

        set_setting_async('enable_hdevtools', False)

        return None
    except Exception as e:
        log('calling to hdevtools fails with {0}'.format(e))
        return None

def is_running():
    r = admin(['--status'], wait = True)
    if r and re.search(r'running', r):
        return True
    else:
        return False

def start_server():
    if not is_running():
        admin(["--start-server"])

def hdevtools_info(filename, symbol_name, cabal = None):
    """
    Uses hdevtools info filename symbol_name to get symbol info
    """
    contents = call_hdevtools_and_wait(['info', filename, symbol_name], filename = filename, cabal = cabal)
    return parse_info(symbol_name, contents) if contents else None

def hdevtools_check(filename, cabal = None):
    """
    Uses hdevtools to check file
    """
    return call_hdevtools_and_wait(['check', filename], filename = filename, cabal = cabal)

def hdevtools_type(filename, line, column, cabal = None):
    """
    Uses hdevtools to infer type
    """
    return call_hdevtools_and_wait(['type', filename, str(line), str(column)], filename = filename, cabal = cabal)

def start_hdevtools():
    thread = threading.Thread(
        target=start_server)
    thread.start()

def stop_hdevtools():
    admin(["--stop-server"])

def hdevtools_enabled():
    return get_setting_async('enable_hdevtools') == True

########NEW FILE########
__FILENAME__ = hdocs
import sublime
import json
import time

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
else:
    from SublimeHaskell.sublime_haskell_common import *

def call_hdocs_and_wait(args, filename = None, cabal = None):
    if not hdocs_enabled():
        return None

    ghc_opts_args = get_ghc_opts_args(filename, cabal = cabal)
    source_dir = get_source_dir(filename)
    
    try:
        command = ['hdocs'] + args + ghc_opts_args
        log(command)

        exit_code, out, err = call_and_wait(command, cwd = source_dir)

        if exit_code != 0:
            raise Exception("hdocs exited with status %d and stderr: %s" % (exit_code, err))

        return crlf2lf(out)

    except OSError as e:
        if e.errno == errno.ENOENT:
            sublime.set_timeout(lambda: output_error(sublime.active_window(), "SublimeHaskell: hdocs was not found!\n'enable_hdocs' is set to False"), 0)
            set_setting_async('enable_hdocs', False)

        return None

    except Exception as e:
        log('hdocs fails with {0}'.format(e))
        return None

def module_docs(module_name, cabal = None):
    if not hdocs_enabled():
        return None

    try:
        contents = call_hdocs_and_wait(['docs', module_name], cabal = cabal)
        if contents:
            return json.loads(contents)
        else:
            return None
    except Exception as e:
        log('hdocs fails with {0}'.format(e))
        return None

def symbol_docs(module_name, symbol_name, cabal = None):
    if not hdocs_enabled():
        return None

    return call_hdocs_and_wait(['docs', module_name, symbol_name], cabal = cabal)

def load_module_docs(module):
    if not hdocs_enabled():
        return False

    if module.location:
        return False
    if 'hdocs' in module.tags:
        return False

    docs = module_docs(module.name, module.cabal)
    if docs:
        module.tags['hdocs'] = time.clock()
        for decl in module.declarations.values():
            if decl.name in docs:
                decl.docs = docs[decl.name]
        return True

    return False

def hdocs_enabled():
    return get_setting_async('enable_hdocs') == True

########NEW FILE########
__FILENAME__ = hsdev
import os
import os.path
import sys
import socket
import sublime
import sublime_plugin
import subprocess
import threading
import json
import time
from functools import reduce

if int(sublime.version()) < 3000:
    import symbols
    from sublime_haskell_common import *
else:
    import SublimeHaskell.symbols as symbols
    from SublimeHaskell.sublime_haskell_common import *

def call_hsdev_and_wait(arg_list, filename = None, cabal = None, callback = None, **popen_kwargs):
    cmd = ['hsdev'] + arg_list

    result = None

    def on_line(l):
        if l:
            if 'status' in l:
                callback(l)
            else:
                result = l

    def parse_response(s):
        try:
            return {} if s.isspace() else json.loads(s)
        except Exception as e:
            return {'response' : s}

    log(' '.join(cmd))
    ret = call_and_wait_tool(cmd, 'hsdev', parse_response, filename, on_line if callback else None, **popen_kwargs)
    if ret is not None:
        result = ret

    return result

def hsdev(arg_list, on_response = None):
    if get_setting_async('enable_hsdev') != True:
        return None

    r = call_hsdev_and_wait(arg_list, callback = on_response)
    if r is None:
        return None
    if r and 'error' in r:
        log('hsdev returns error: {0} with details: {1}'.format(r['error'], r['details']))
        return None
    return r

def if_some(x, lst):
    return lst if x is not None else []

def cabal_path(cabal):
    if not cabal:
        return []
    args = ['--sandbox']
    if cabal != 'cabal':
        args.append(cabal)
    return args

def hsinspect(module = None, file = None, cabal = None, ghc_opts = []):
    cmd = ['hsinspect']
    on_result = lambda s: s
    if module:
        cmd.extend(['module', module])
        on_result = parse_module
    elif file:
        cmd.extend(['file', file])
        on_result = parse_module
    elif cabal:
        cmd.extend(['cabal', cabal])
    else:
        log('hsinspect must specify module, file or cabal')
        return None

    for opt in ghc_opts:
        cmd.extend(['-g', opt])

    r = call_and_wait_tool(cmd, 'hsinspect', lambda s: json.loads(s), file, None)
    if r:
        if 'error' in r:
            log('hsinspect returns error: {0}'.format(r['error']))
        else:
            return on_result(r)
    return None

def print_status(s):
    print(s['status'])

class StatusToMessage(object):
    def __init__(messager):
        self.messager = messager

    def on_status(self, s):
        (task_name, info) = s['task'].values()[0]
        cur = s['progress']['current']
        total = s['progress']['total']
        s.change_message('{0} {1}: {2}'.format(task_name, info, s['status']))
        s.percentage_message(cur, total)

def start(port = None, cache = None, log = None):
    return hsdev(['server', 'start'] + if_some(port, ['--port', str(port)]) + if_some(cache, ['--cache', cache]) + if_some(log, ['--log', log])) is not None

def link(port = None, parent = None):
    return hsdev(['link'] + if_some(port, ['--port', str(port)]) + if_some(parent, ['--parent', parent])) is not None

def stop(port = None):
    return hsdev(['server', 'stop'] + if_some(port, ['--port', str(port)])) is not None

def scan(cabal = None, projects = [], files = [], paths = [], modules = [], wait = False, on_status=None):
    opts = ['scan']
    if modules:
        opts.extend(['module'] + modules)
        if cabal:
            opts.extend(['--sandbox', cabal])
    elif cabal:
        opts.extend(['cabal'] + cabal_path(cabal))
    else:
        args = [['--project', p] for p in projects] + [['-f', f] for f in files] + [['-p', p] for p in paths]
        opts.extend(list(reduce(lambda x, y: x + y, args)))

    if wait or on_status:
        opts.extend(['-w', '-s'])

    opts.extend(get_ghc_opts_args(cabal = cabal))

    def onResponse(s):
        if on_status:
            on_status(s)

    return hsdev(opts, on_response = onResponse if wait else None)

def rescan(projects = [], files = [], paths = [], wait = False, on_status = None):
    opts = ['rescan']
    args = [['--project', p] for p in projects] + [['-f', f] for f in files] + [['-p', p] for p in paths]

    if not args:
        log('hsdev.rescan: must specify at least one param')
        return None

    opts.extend(list(reduce(lambda x, y: x + y, args)))

    if wait or on_status:
        opts.extend(['-w', '-s'])

    opts.extend(get_ghc_opts_args(filename = file))

    def onResponse(s):
        if on_status:
            on_status(s)

    return hsdev(opts, on_response = onResponse if wait else None)

def remove(cabal = None, project = None, file = None, module = None):
    return hsdev(
        ['remove'] +
        cabal_path(cabal) +
        if_some(project, ['--project', project]) +
        if_some(file, ['-f', file]) +
        if_some(module, ['-m', module]))

def remove_all():
    return hsdev(['remove', '-a'])

def list_modules(cabal = None, project = None, source = False, standalone = False):
    return parse_modules(
        hsdev(
            ['list', 'modules'] +
            cabal_path(cabal) +
            if_some(project, ['--project', project]) +
            (['--src'] if source else []) +
            (['--stand'] if standalone else [])))

def list_projects():
    return hsdev(['list', 'projects'])

def symbol(name = None, project = None, file = None, module = None, package = None, cabal = None, source = False, standalone = False, prefix = None, find = None):
    return parse_decls(
        hsdev(
            (['symbol', name] if name else ['symbol']) +
            if_some(project, ['--project', project]) +
            if_some(file, ['-f', file]) +
            if_some(module, ['-m', module]) +
            if_some(package, ['--package', package]) +
            cabal_path(cabal) +
            (['--src'] if source else []) +
            (['--stand'] if standalone else []) +
            if_some(prefix, ['--prefix', prefix]) +
            if_some(find, ['--find', find])))

def module(name = None, package = None, project = None, file = None, cabal = None, source = False):
    return parse_module(
        hsdev(
            ['module'] +
            if_some(name, ['-m', name]) +
            if_some(package, ['--package', package]) +
            if_some(project, ['--project', project]) +
            cabal_path(cabal) +
            if_some(file, ['-f', file]) +
            (['--src'] if source else [])))

def project(projects):
    return hsdev(['project'] + projects)

def lookup(name, file, cabal = None):
    return parse_decls(
        hsdev(
            ['lookup', name, '-f', file] + cabal_path(cabal)))

def whois(name, file, cabal = None):
    return parse_decls(
        hsdev(
            ['whois', name, '-f', file] + cabal_path(cabal)))

def scope_modules(file, cabal = None):
    return parse_modules(
        hsdev(
            ['scope', 'modules', '-f', file] + cabal_path(cabal)))

def scope(file, cabal = None, global_scope = False, prefix = None, find = None):
    return parse_decls(
        hsdev(
            ['scope', '-f', file] +
            cabal_path(cabal) +
            (['--global'] if global_scope else []) +
            if_some(prefix, ['--prefix', prefix]) +
            if_some(find, ['--find', find])))

def complete(input, file, cabal = None):
    return parse_decls(
        hsdev(
            ['complete', input, '-f', file] + cabal_path(cabal)))

def dump(cabal = None, projects = [], files = [], path = None, file = None):
    opts = ['dump']
    if cabal:
        opts.extend(['cabal'] + cabal_path(cabal))
    elif projects:
        opts.extend(['project'] + projects)
    elif files:
        opts.extend(['standalone'] + files)
    
    if path:
        opts.extend(['-p', path])
    if file:
        opts.extend(['-f', file])

    r = hsdev(opts)
    if r:
        return parse_database(r)
    else:
        return r

def load(path = None, file = None, data = None):
    return hsdev(
        ['load'] +
        if_some(path, ['-p', path]) +
        if_some(file, ['-f', file]) +
        if_some(data, ['--data', data]))

def exit():
    return hsdev(['exit'])

def parse_database(s):
    if not s:
        return None
    if s and 'projects' in s and 'modules' in s:
        return (s['projects'], [parse_module(m) for m in s['modules']])
    return None

def parse_decls(s):
    if s is None:
        return None
    return [parse_module_declaration(decl) for decl in s]

def parse_modules(s):
    if s is None:
        return None
    return [parse_module_id(m) for m in s]

def get_value(dc, ks, defval = None):
    if dc is None:
        return defval
    if type(ks) == list:
        cur = dc
        for k in ks:
            cur = cur.get(k)
            if cur is None:
                return defval
        return cur
    else:
        return dc.get(ks, defval)

def parse_location(d, p = None):
    loc = symbols.Location(
        get_value(d, 'file'),
        get_value(p, 'line', 0),
        get_value(p, 'column', 0),
        get_value(d, 'project'))
    if not loc.is_null():
        return loc
    loc = symbols.InstalledLocation(
        symbols.parse_package(get_value(d, 'package')),
        get_value(d, 'cabal'))
    if not loc.is_null():
        return loc
    return None

def parse_cabal(d):
    c = get_value(d, 'cabal')
    if c == '<cabal>':
        return 'cabal'
    else:
        return c

def parse_import(d):
    if not d:
        return None
    return symbols.Import(d['name'], d['qualified'], d.get('as'), parse_location(None, d.get('pos')))

def parse_module_id(d):
    if d is None:
        return None
    return symbols.Module(
        d['name'],
        [], {}, {},
        parse_location(d.get('location')),
        parse_cabal(d.get('location')))

def parse_declaration(decl):
    try:
        what = decl['decl']['what']
        loc = parse_location(None, decl.get('pos'))
        docs = decl.get('docs')
        name = decl['name']

        if what == 'function':
            return symbols.Function(name, decl['decl'].get('type'), docs, loc)
        elif what == 'type':
            return symbols.Type(name, decl['decl']['info'].get('ctx'), decl['decl']['info'].get('args'), decl['decl']['info'].get('def'), docs, loc)
        elif what == 'newtype':
            return symbols.Newtype(name, decl['decl']['info'].get('ctx'), decl['decl']['info'].get('args'), decl['decl']['info'].get('def'), docs, loc)
        elif what == 'data':
            return symbols.Data(name, decl['decl']['info'].get('ctx'), decl['decl']['info'].get('args'), decl['decl']['info'].get('def'), docs, loc)
        elif what == 'class':
            return symbols.Class(name, decl['decl']['info'].get('ctx'), decl['decl']['info'].get('args'), decl['decl']['info'].get('def'), docs, loc)
        else:
            return None
    except Exception as e:
        log('Error pasring declaration: {0}'.format(e))
        return None

def parse_module_declaration(d, parse_module_info = True):
    try:
        m = None
        if 'module-id' in d and parse_module_info:
            m = parse_module_id(d['module-id'])

        loc = parse_location(d['module-id'].get('location'))
        decl = parse_declaration(d['declaration'])

        if not decl:
            return None

        decl.update_location(loc)

        decl.module = m

        return decl
    except:
        return None

def parse_module(d):
    if d is None:
        return None
    return symbols.Module(
        d['name'],
        d.get('exports'),
        [parse_import(i) for i in d['imports']] if 'imports' in d else [],
        dict((decl['name'],parse_declaration(decl)) for decl in d['declarations']) if 'declarations' in d else {},
        parse_location(d.get('location')),
        parse_cabal(d.get('location')))

def test():
    p = HsDev()
    # time.sleep(10)
    p.load_cache(path = "e:")
    l = p.list()
    log(l)

class HsDevHolder(object):
    def __init__(self, port = 4567, cache = None):
        super(HsDevHolder, self).__init__()
        self.port = port
        self.cache = cache
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.started_event = threading.Event()

    def run_hsdev(self, tries = 10):
        self.start_hsdev()
        self.link_hsdev(tries = tries)

    def start_hsdev(self):
        start(port = self.port, cache = self.cache)

    def link_hsdev(self, tries = 10):
        for n in range(0, tries):
            try:
                log('connecting to hsdev server...')
                self.socket.connect(('127.0.0.1', self.port))
                log('connected to hsdev server')
                self.socket.sendall(b'["link"]\n')
                self.started_event.set()
                log('hsdev server started')
                return
            except:
                log('failed to connect to hsdev server, wait for a while')
                time.sleep(0.1)

    # Wait until linked
    def wait_hsdev(self, timeout = 60):
        return self.started_event.wait(timeout)

hsdev_holder = None

def start_server(port = None, cache = None):
    global hsdev_holder
    hsdev_holder = HsDevHolder(port, cache)
    hsdev_holder.run_hsdev()

########NEW FILE########
__FILENAME__ = parseoutput
import os
import re
import sublime
import sublime_plugin
import time
from sys import version
from threading import Thread
from collections import defaultdict

PyV3 = version[0] == "3"

if int(sublime.version()) < 3000:
    from sublime_haskell_common import log, are_paths_equal, call_and_wait, get_setting_async, show_status_message_process, show_status_message
else:
    from SublimeHaskell.sublime_haskell_common import log, are_paths_equal, call_and_wait, get_setting_async, show_status_message_process, show_status_message

ERROR_PANEL_NAME = 'haskell_error_checker'

# This regex matches an unindented line, followed by zero or more
# indented, non-empty lines.
# It also eats whitespace before the first line.
# The first line is divided into a filename, a line number, and a column.
output_regex = re.compile(
    r'\s*^(\S*):(\d+):(\d+):(.*$(?:\n^[ \t].*$)*)',
    re.MULTILINE)

# Extract the filename, line, column, and description from an error message:
result_file_regex = r'^(\S*?): line (\d+), column (\d+):$'


# Global list of errors. Used e.g. for jumping to the next one.
# Properly assigned being a defaultdict in clear_error_marks().
# Structure: ERRORS[filename][m.line] = OutputMessage()
ERRORS = {}


def filename_of_path(p):
    """Returns everything after the last slash or backslash."""
    # Not using os.path here because we don't know/care here if
    # we have forward or backslashes on Windows.
    return re.match(r'(.*[/\\])?(.*)', p).groups()[1]


class OutputMessage(object):
    "Describe an error or warning message produced by GHC."
    def __init__(self, filename, line, column, message, level):
        self.filename = filename
        self.line = int(line)
        self.column = int(column)
        self.message = message
        self.level = level

    def __unicode__(self):
        # must match result_file_regex
        return u'{0}: line {1}, column {2}:\n  {3}'.format(
            self.filename,
            self.line,
            self.column,
            self.message)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return '<OutputMessage {0}:{1}:{2}: {3}>'.format(
            filename_of_path(self.filename),
            self.line,
            self.column,
            self.message[:10] + '..')

    def find_region_in_view(self, view):
        "Return the Region referred to by this error message."
        # Convert line and column count to zero-based indices:
        point = view.text_point(self.line - 1, 0)
        # Return the whole line:
        region = view.line(point)
        region = trim_region(view, region)
        return region


def clear_error_marks():
    global ERRORS

    listdict = lambda: defaultdict(list)
    ERRORS = defaultdict(listdict)


def set_global_error_messages(messages):
    global ERRORS

    clear_error_marks()

    for m in messages:
        ERRORS[m.filename][m.line].append(m)


def run_build_thread(view, cabal_project_dir, msg, cmd, on_done):
    run_chain_build_thread(view, cabal_project_dir, msg, [cmd], on_done)


def run_chain_build_thread(view, cabal_project_dir, msg, cmds, on_done):
    show_status_message_process(msg, priority = 3)
    thread = Thread(
        target=wait_for_chain_to_complete,
        args=(view, cabal_project_dir, msg, cmds, on_done))
    thread.start()


def wait_for_build_to_complete(view, cabal_project_dir, msg, cmd, on_done):
    """Run a command, wait for it to complete, then parse and display
    the resulting errors."""

    wait_for_chain_to_complete(view, cabal_project_dir, msg, [cmd], on_done)


def wait_for_chain_to_complete(view, cabal_project_dir, msg, cmds, on_done):
    """Chains several commands, wait for them to complete, then parse and display
    the resulting errors."""

    # First hide error panel to show that something is going on
    sublime.set_timeout(lambda: hide_output(view), 0)

    # run and wait commands, fail on first fail
    for cmd in cmds:
        exit_code, stdout, stderr = call_and_wait(
            cmd,
            cwd=cabal_project_dir)
        if exit_code != 0:
            break

    errmsg = stderr if stderr else stdout

    # Notify UI thread that commands are done
    sublime.set_timeout(on_done, 0)

    parse_output_messages_and_show(view, msg, cabal_project_dir, exit_code, errmsg)


def format_output_messages(messages):
    """Formats list of messages"""
    if PyV3:
        return '\n'.join(str(x) for x in messages)
    else:
        return u'\n'.join(unicode(x) for x in messages)

def show_output_result_text(view, msg, text, exit_code, base_dir):
    """Shows text (formatted messages) in output with build result"""

    success = exit_code == 0

    success_message = 'SUCCEEDED' if success else 'FAILED'
    output = u'Build {0}\n\n{1}'.format(success_message, text.strip())

    show_status_message_process(msg, success)
    # Show panel if there is any text to show (without the part that we add)
    if text:
        if get_setting_async('show_output_window'):
            sublime.set_timeout(lambda: write_output(view, output, base_dir), 0)


def parse_output_messages_and_show(view, msg, base_dir, exit_code, stderr):
    """Parse errors and display resulting errors"""

    # stderr/stdout can contain unicode characters
    # already done in call_and_wait
    # stderr = stderr.decode('utf-8')

    # The process has terminated; parse and display the output:
    parsed_messages = parse_output_messages(base_dir, stderr)
    # The unparseable part (for other errors)
    unparsable = output_regex.sub('', stderr).strip()

    # Set global error list
    set_global_error_messages(parsed_messages)

    # If we couldn't parse any messages, just show the stderr
    # Otherwise the parsed errors and the unparsable stderr remainder
    outputs = []

    if parsed_messages:
        outputs += [format_output_messages(parsed_messages)]
    if unparsable:
        outputs += ["\nREMAINING STDERR:\n", unparsable]

    output_text = '\n'.join(outputs)

    show_output_result_text(view, msg, output_text, exit_code, base_dir)

    sublime.set_timeout(lambda: mark_messages_in_views(parsed_messages), 0)


def mark_messages_in_views(errors):
    "Mark the regions in open views where errors were found."
    begin_time = time.clock()
    # Mark each diagnostic in each open view in all windows:
    for w in sublime.windows():
        for v in w.views():
            view_filename = v.file_name()
            # Unsaved files have no file name
            if view_filename is None:
                continue
            errors_in_view = list(filter(
                lambda x: are_paths_equal(view_filename, x.filename),
                errors))
            mark_messages_in_view(errors_in_view, v)
    end_time = time.clock()
    log('total time to mark {0} diagnostics: {1} seconds'.format(
        len(errors), end_time - begin_time))

message_levels = {
    'hint': {
        'style': 'comment.warning',
        'icon': 'light_x_bright'
    },
    'warning': {
        'style': 'comment.warning',
        'icon': 'grey_x_light_shadow'
    },
    'error': {
        'style': 'invalid',
        'icon': 'grey_x'
    }
}


# These next and previous commands were shamelessly copied
# from the great SublimeClang plugin.

class SublimeHaskellNextError(sublime_plugin.TextCommand):
    def run(self, edit):
        log("SublimeHaskellNextError")
        v = self.view
        fn = v.file_name().encode("utf-8")
        line, column = v.rowcol(v.sel()[0].a)
        line += 1
        gotoline = -1
        if fn in ERRORS:
            for errLine in sorted(ERRORS[fn].keys()):
                if errLine > line:
                    gotoline = errLine
                    break
            # No next line: Wrap around if possible
            if gotoline == -1 and len(ERRORS[fn]) > 0:
                gotoline = sorted(ERRORS[fn].keys())[0]
        if gotoline != -1:
            v.window().open_file("%s:%d" % (fn, gotoline), sublime.ENCODED_POSITION)
        else:
            sublime.status_message("No more errors or warnings!")


class SublimeHaskellPreviousError(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        fn = v.file_name().encode("utf-8")
        line, column = v.rowcol(v.sel()[0].a)
        line += 1
        gotoline = -1
        if fn in ERRORS:
            for errLine in sorted(ERRORS[fn].keys(), key = lambda x: -x):
                if errLine < line:
                    gotoline = errLine
                    break
            # No previous line: Wrap around if possible
            if gotoline == -1 and len(ERRORS[fn]) > 0:
                gotoline = sorted(ERRORS[fn].keys())[-1]
        if gotoline != -1:
            v.window().open_file("%s:%d" % (fn, gotoline), sublime.ENCODED_POSITION)
        else:
            sublime.status_message("No more errors or warnings!")



def region_key(name):
    return 'subhs-{0}s'.format(name)


def mark_messages_in_view(messages, view):
    # Regions by level
    regions = {}
    for k in message_levels.keys():
        regions[k] = []

    for m in messages:
        regions[m.level].append(m.find_region_in_view(view))

    for nm, lev in message_levels.items():
        view.erase_regions(region_key(nm))
        view.add_regions(
            region_key(nm),
            regions[nm],
            lev['style'],
            lev['icon'],
            sublime.DRAW_OUTLINED)


def write_output(view, text, cabal_project_dir):
    "Write text to Sublime's output panel."
    output_view = view.window().get_output_panel(ERROR_PANEL_NAME)
    output_view.set_read_only(False)
    # Configure Sublime's error message parsing:
    output_view.settings().set("result_file_regex", result_file_regex)
    output_view.settings().set("result_base_dir", cabal_project_dir)
    # Write to the output buffer:
    output_view.run_command('sublime_haskell_output_text', {
        'text': text })
    # Set the selection to the beginning of the view so that "next result" works:
    output_view.sel().clear()
    output_view.sel().add(sublime.Region(0))
    output_view.set_read_only(True)
    # Show the results panel:
    view.window().run_command('show_panel', {'panel': 'output.' + ERROR_PANEL_NAME})


def hide_output(view):
    view.window().run_command('hide_panel', {'panel': 'output.' + ERROR_PANEL_NAME})


def parse_output_messages(base_dir, text):
    "Parse text into a list of OutputMessage objects."
    matches = output_regex.finditer(text)

    def to_error(m):
        filename, line, column, messy_details = m.groups()
        return OutputMessage(
            # Record the absolute, normalized path.
            os.path.normpath(os.path.join(base_dir, filename)),
            line,
            column,
            messy_details.strip(),
            'warning' if 'warning' in messy_details.lower() else 'error')

    return list(map(to_error, matches))


def trim_region(view, region):
    "Return the specified Region, but without leading or trailing whitespace."
    text = view.substr(region)
    # Regions may be selected backwards, so b could be less than a.
    a = min(region.a, region.b)
    b = max(region.a, region.b)
    # Figure out how much to move the endpoints to lose the space.
    # If the region is entirely whitespace, give up and return it unchanged.
    if text.isspace():
        return region
    else:
        text_trimmed_on_left = text.lstrip()
        text_trimmed = text_trimmed_on_left.rstrip()
        a += len(text) - len(text_trimmed_on_left)
        b -= len(text_trimmed_on_left) - len(text_trimmed)
        return sublime.Region(a, b)

########NEW FILE########
__FILENAME__ = stylishhaskell
import errno
import sublime
import sublime_plugin

if int(sublime.version()) < 3000:
    from sublime_haskell_common import is_enabled_haskell_command, call_and_wait_with_input
else:
    from SublimeHaskell.sublime_haskell_common import is_enabled_haskell_command, call_and_wait_with_input


class SublimeHaskellStylish(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            regions = []
            for region in self.view.sel():
                regions.append(sublime.Region(region.a, region.b))
                if region.empty():
                    selection = sublime.Region(0, self.view.size())
                else:
                    selection = region
                sel_str = self.view.substr(selection).replace('\r\n', '\n')
                exit_code, out, err = call_and_wait_with_input(['stylish-haskell'], sel_str)
                out_str = out.replace('\r\n', '\n')
                if exit_code == 0 and out_str != sel_str:
                    self.view.replace(edit, selection, out_str)

            self.view.sel().clear()
            for region in regions:
                self.view.sel().add(region)

        except OSError as e:
            if e.errno == errno.ENOENT:
                sublime.error_message("SublimeHaskell: stylish-haskell was not found!")

    def is_enabled(self):
        return is_enabled_haskell_command(self.view, False)

########NEW FILE########
__FILENAME__ = sublime_haskell_common
import errno
import fnmatch
import os
import re
import json
import sublime
import sublime_plugin
import subprocess
import threading
import time
from sys import version

PyV3 = version[0] == "3"

# Maximum seconds to wait for window to appear
# This dirty hack is used in wait_for_window function
MAX_WAIT_FOR_WINDOW = 10

# Panel for SublimeHaskell errors
SUBLIME_ERROR_PANEL_NAME = 'haskell_sublime_load'

# Used to detect hs-source-dirs for project
CABAL_INSPECTOR_EXE_PATH = None

# unicode function
def to_unicode(s):
    return s if PyV3 else unicode(s)

# Object with lock attacjed
class LockedObject(object):
    """
    Object with lock
    x = LockedObject(some_value)
    with x as v:
        v...
    """

    def __init__(self, obj, lock = None):
        self.object_lock = lock if lock else threading.Lock()
        self.object = obj

    def __enter__(self):
        self.object_lock.__enter__()
        return self.object

    def __exit__(self, type, value, traceback):
        self.object_lock.__exit__()

# Setting can't be get from not main threads
# So we using a trick:
# Once setting loaded from main thread, it also stored in sublime_haskell_settings dictionary
# and callback attached to update its value
# And then setting can be get from any thread with get_setting_async
# But setting must be loaded at least once from main thread
# Some settings are loaded only from secondary threads, so we loading them here for first time
def preload_settings():
    # Now we can use get_setting_async for 'add_to_PATH' safely
    get_setting('add_to_PATH')
    get_setting('use_cabal_dev')
    get_setting('cabal_dev_sandbox')
    get_setting('cabal_dev_sandbox_list')
    get_setting('enable_auto_build')
    get_setting('show_output_window')
    get_setting('enable_ghc_mod')
    get_setting('enable_hdevtools')
    get_setting('enable_hdocs')
    get_setting('snippet_replace')
    get_setting('ghc_opts')

# SublimeHaskell settings dictionary
# used to retrieve it async from any thread
sublime_haskell_settings = LockedObject({})


def is_enabled_haskell_command(view = None, must_be_project=True, must_be_main=False, must_be_file = False):
    """Returns True if command for .hs can be invoked"""
    window, view, file_shown_in_view = get_haskell_command_window_view_file_project(view)

    if not window or not view:
        return False

    if must_be_file and not file_shown_in_view:
        return False

    syntax_file_for_view = view.settings().get('syntax').lower()
    if 'haskell' not in syntax_file_for_view:
        return False

    if not must_be_project:
        return True

    cabal_project_dir = get_cabal_project_dir_of_view(view)
    if not cabal_project_dir:
        return False
    return True


def get_haskell_command_window_view_file_project(view = None):
    """Returns window, view and file"""
    if view:
        return view.window(), view, view.file_name()

    window = sublime.active_window()
    view = None
    if window:
        view = window.active_view()
    file_name = None
    if view:
        file_name = view.file_name()
    return window, view, file_name


def decode_bytes(s):
    if s is None:
        return None
    return s.decode('utf-8')

def encode_bytes(s):
    if s is None:
        return None
    return s.encode('utf-8')

# Get extended environment from settings for Popen
def get_extended_env():
    ext_env = dict(os.environ)
    PATH = os.getenv('PATH') or ""
    add_to_PATH = get_setting_async('add_to_PATH', [])
    if not PyV3:
        # convert unicode strings to strings (for Python < 3) as env can contain only strings
        add_to_PATH = map(str, add_to_PATH)
    ext_env['PATH'] = os.pathsep.join(add_to_PATH + [PATH])
    return ext_env

def call_and_wait(command, **popen_kwargs):
    return call_and_wait_with_input(command, None, **popen_kwargs)

def call_no_wait(command, **popen_kwargs):
    """Run the specified command with no block"""
    if subprocess.mswindows:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        popen_kwargs['startupinfo'] = startupinfo

    extended_env = get_extended_env()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        env=extended_env,
        **popen_kwargs)

def call_and_wait_with_input(command, input_string, **popen_kwargs):
    """Run the specified command, block until it completes, and return
    the exit code, stdout, and stderr.
    Extends os.environment['PATH'] with the 'add_to_PATH' setting.
    Additional parameters to Popen can be specified as keyword parameters."""
    if subprocess.mswindows:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        popen_kwargs['startupinfo'] = startupinfo

    # For the subprocess, extend the env PATH to include the 'add_to_PATH' setting.
    extended_env = get_extended_env()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        env=extended_env,
        **popen_kwargs)
    stdout, stderr = process.communicate(encode_bytes(input_string))
    exit_code = process.wait()
    return (exit_code, decode_bytes(stdout), decode_bytes(stderr))


def log(message):
    print(u'Sublime Haskell: {0}'.format(message))


def get_cabal_project_dir_and_name_of_view(view):
    """Return the path to the .cabal file project for the source file in the
    specified view. The view must show a saved file, the file must be Haskell
    source code, and the file must be under a directory containing a .cabal file.
    Otherwise, return None.
    """
    # Check that the view is showing a saved file:
    file_shown_in_view = view.file_name()
    if file_shown_in_view is None:
        return None, None
    # Check that the file is Haskell source code:
    syntax_file_for_view = view.settings().get('syntax').lower()
    if 'haskell' not in syntax_file_for_view:
        return None, None
    return get_cabal_project_dir_and_name_of_file(file_shown_in_view)


def get_cabal_project_dir_of_view(view):
    return get_cabal_project_dir_and_name_of_view(view)[0]


def get_cabal_project_dir_and_name_of_file(filename):
    """Return the path to the .cabal file and name of project for the specified file."""
    # Check that a .cabal file is present:
    directory_of_file = os.path.dirname(filename)
    cabal_file_path = find_file_in_parent_dir(directory_of_file, '*.cabal')
    if cabal_file_path is None:
        return None, None
    # Return the directory containing the .cabal file:
    project_path, cabal_file = os.path.split(cabal_file_path)
    project_name = os.path.splitext(cabal_file)[0]
    return project_path, project_name


def get_cabal_project_dir_of_file(filename):
    """Return the path to the .cabal file project for the specified file."""
    return get_cabal_project_dir_and_name_of_file(filename)[0]


def get_cabal_in_dir(cabal_dir):
    """Return .cabal file for cabal directory"""
    for entry in os.listdir(cabal_dir):
        if entry.endswith(".cabal"):
            project_name = os.path.splitext(entry)[0]
            return (project_name, os.path.join(cabal_dir, entry))
    return (None, None)


def find_file_in_parent_dir(subdirectory, filename_pattern):
    """Look for a file with the specified name in a parent directory of the
    specified directory. If found, return the file's full path. Otherwise,
    return None."""
    current_dir = subdirectory
    while True:
        # See if the current directory contains the desired file:
        for name in os.listdir(current_dir):
            full_path = os.path.join(current_dir, name)
            matches_pattern = fnmatch.fnmatch(name, filename_pattern)
            if matches_pattern and os.path.isfile(full_path):
                return full_path
        # Get the next directory up:
        last_dir = current_dir
        current_dir = os.path.dirname(current_dir)
        # Check to see if we have reached the root directory:
        if last_dir == current_dir:
            return None


def are_paths_equal(path, other_path):
    "Test whether filesystem paths are equal."
    path = os.path.abspath(path)
    other_path = os.path.abspath(other_path)
    return path == other_path


def current_cabal():
    """
    Returns current cabal-dev sandbox or 'cabal'
    """
    if get_setting_async('use_cabal_dev'):
        return get_setting_async('cabal_dev_sandbox')
    else:
        return 'cabal'

def current_sandbox():
    """
    Returns current cabal-def sandbox or None
    """
    if get_setting_async('use_cabal_dev'):
        return get_setting_async('cabal_dev_sandbox')
    else:
        return None

def cabal_name_by_sandbox(sandbox):
    if not sandbox:
        return current_cabal()
    return sandbox

def sandbox_by_cabal_name(cabal):
    if cabal == 'cabal':
        return None
    return cabal

def attach_sandbox(cmd, sandbox = None):
    """Attach sandbox arguments to command"""
    if not sandbox:
        sandbox = get_setting_async('cabal_dev_sandbox')
    if len(sandbox) > 0:
        return cmd + ['-s', sandbox]
    return cmd


def try_attach_sandbox(cmd, sandbox = None):
    """Attach sandbox if use_cabal_dev enabled"""
    if not get_setting_async('use_cabal_dev'):
        return cmd
    return attach_sandbox(cmd, sandbox)


def attach_cabal_sandbox(cmd, cabal = None):
    """
    Attach sandbox if cabal is sandbox path, attach nothing on 'cabal',
    and attach sandbox by settings on None
    """
    if not cabal:
        cabal = current_cabal()
    if cabal == 'cabal':
        return cmd
    return cmd + ['-s', cabal]


def get_settings():
    return sublime.load_settings("SublimeHaskell.sublime-settings")


def save_settings():
    sublime.save_settings("SublimeHaskell.sublime-settings")


def get_setting(key, default=None):
    "This should be used only from main thread"
    # Get setting
    result = get_settings().get(key, default)
    # Key was not retrieved, save its value and add callback to auto-update
    with sublime_haskell_settings as settings:
        if key not in settings:
            get_settings().add_on_change(key, lambda: update_setting(key))
        settings[key] = result
    return result


def update_setting(key):
    "Updates setting as it was changed"
    get_setting(key)


def get_setting_async(key, default=None):
    """
    Get setting from any thread
    Note, that setting must be loaded before by get_setting from main thread
    """
    # Reload it in main thread for future calls of get_setting_async
    sublime.set_timeout(lambda: update_setting(key), 0)
    with sublime_haskell_settings as settings:
        if key not in settings:
            # Load it in main thread, but for now all we can do is result default
            return default
        return settings[key]


def set_setting(key, value):
    """Set setting and update dictionary"""
    with sublime_haskell_settings as settings:
        settings[key] = value
    get_settings().set(key, value)
    save_settings()

def set_setting_async(key, value):
    sublime.set_timeout(lambda: set_setting(key, value), 0)

def ghci_package_db(cabal = None):
    if cabal == 'cabal':
        return None
    dev = True if cabal else get_setting_async('use_cabal_dev')
    box = cabal if cabal else get_setting_async('cabal_dev_sandbox')
    if dev and box:
        package_conf = (filter(lambda x: re.match('packages-(.*)\.conf', x), os.listdir(box)) + [None])[0]
        if package_conf:
            return os.path.join(box, package_conf)
    return None

def ghci_append_package_db(cmd, cabal = None):
    package_conf = ghci_package_db(cabal)
    if package_conf:
        cmd.extend(['-package-db', package_conf])
    return cmd

def get_source_dir(filename):
    """
    Get root of hs-source-dirs for filename in project
    """
    if not filename:
        return os.path.expanduser('~')
        # return os.getcwd()

    (cabal_dir, project_name) = get_cabal_project_dir_and_name_of_file(filename)
    if not cabal_dir:
        return os.path.dirname(filename)

    _project_name, cabal_file = get_cabal_in_dir(cabal_dir)
    exit_code, out, err = call_and_wait([CABAL_INSPECTOR_EXE_PATH, cabal_file])

    if exit_code == 0:
        info = json.loads(out)

        dirs = ["."]

        if 'error' not in info:
            # collect all hs-source-dirs
            if info['library']:
                dirs.extend(info['library']['info']['source-dirs'])
            for i in info['executables']:
                dirs.extend(i['info']['source-dirs'])
            for t in info['tests']:
                dirs.extend(t['info']['source-dirs'])

        paths = [os.path.abspath(os.path.join(cabal_dir, d)) for d in dirs]
        paths.sort(key = lambda p: -len(p))

        for p in paths:
            if filename.startswith(p):
                return p

    return os.path.dirname(filename)

def get_cwd(filename = None):
    """
    Get cwd for filename: cabal project path, file path or os.getcwd()
    """
    cwd = (get_cabal_project_dir_of_file(filename) or os.path.dirname(filename)) if filename else os.getcwd()
    return cwd

def get_ghc_opts(filename = None, add_package_db = True, cabal = None):
    """
    Gets ghc_opts, used in several tools, as list with extra '-package-db' option and '-i' option if filename passed
    """
    ghc_opts = get_setting_async('ghc_opts')
    if not ghc_opts:
        ghc_opts = []
    if add_package_db:
        package_db = ghci_package_db(cabal = cabal)
        if package_db:
            ghc_opts.append('-package-db {0}'.format(package_db))

    if filename:
        ghc_opts.append('-i {0}'.format(get_source_dir(filename)))

    return ghc_opts

def get_ghc_opts_args(filename = None, add_package_db = True, cabal = None):
    """
    Same as ghc_opts, but uses '-g' option for each option
    """
    opts = get_ghc_opts(filename, add_package_db, cabal)
    args = []
    for opt in opts:
        args.extend(["-g", opt])
    return args

def call_ghcmod_and_wait(arg_list, filename=None, cabal = None):
    """
    Calls ghc-mod with the given arguments.
    Shows a sublime error message if ghc-mod is not available.
    """

    ghc_opts_args = get_ghc_opts_args(filename, add_package_db = False, cabal = cabal)

    try:
        command = attach_cabal_sandbox(['ghc-mod'] + arg_list + ghc_opts_args, cabal)

        # log('running ghc-mod: {0}'.format(command))

        # Set cwd to user directory
        # Otherwise ghc-mod will fail with 'cannot satisfy package...'
        # Seems, that user directory works well
        # Current source directory is set with -i argument in get_ghc_opts_args
        exit_code, out, err = call_and_wait(command, cwd=get_source_dir(filename))

        if exit_code != 0:
            raise Exception("%s exited with status %d and stderr: %s" % (' '.join(command), exit_code, err))

        return crlf2lf(out)

    except OSError as e:
        if e.errno == errno.ENOENT:
            output_error(sublime.active_window(),
                "SublimeHaskell: ghc-mod was not found!\n"
                + "It is used for LANGUAGE and import autocompletions and type inference.\n"
                + "Try adjusting the 'add_to_PATH' setting.\n"
                + "You can also turn this off using the 'enable_ghc_mod' setting.")
        # Re-raise so that calling code doesn't try to work on the `None` return value
        raise e

def wait_for_window_callback(on_appear, seconds_to_wait):
    window = sublime.active_window()
    if window:
        on_appear(window)
        return
    if seconds_to_wait == 0:
        return
    sublime.set_timeout(lambda: wait_for_window_callback(on_appear, seconds_to_wait - 1), 1000)


def wait_for_window(on_appear, seconds_to_wait=MAX_WAIT_FOR_WINDOW):
    """
    Wait for window to appear on startup
    It's dirty hack, but I have no idea how to make it better
    """
    sublime.set_timeout(lambda: wait_for_window_callback(on_appear, seconds_to_wait), 0)



class SublimeHaskellOutputText(sublime_plugin.TextCommand):
    """
    Helper command to output text to any view
    TODO: Is there any default command for this purpose?
    """
    def run(self, edit, text = None):
        if not text:
            return
        self.view.insert(edit, self.view.size(), text)



def output_error(window, text):
    "Write text to Sublime's output panel with important information about SublimeHaskell error during load"
    output_view = window.get_output_panel(SUBLIME_ERROR_PANEL_NAME)
    output_view.set_read_only(False)

    output_view.run_command('sublime_haskell_output_text', {
        'text': text})

    output_view.set_read_only(True)

    window.run_command('show_panel', {'panel': 'output.' + SUBLIME_ERROR_PANEL_NAME})

class SublimeHaskellError(RuntimeError):
    def __init__(self, what):
        self.reason = what

def sublime_status_message(msg):
    """
    Pure msg with 'SublimeHaskell' prefix and set_timeout
    """
    sublime.set_timeout(lambda: sublime.status_message(u'SublimeHaskell: {0}'.format(msg)), 0)

def show_status_message(msg, isok = None):
    """
    Show status message with check mark (isok = true), ballot x (isok = false) or ... (isok = None)
    """
    mark = u'...'
    if isok is not None:
        mark = u' \u2714' if isok else u' \u2718'
    sublime_status_message(u'{0}{1}'.format(msg, mark))

def with_status_message(msg, action):
    """
    Show status message for action with check mark or with ballot x
    Returns whether action exited properly
    """
    try:
        show_status_message(msg)
        action()
        show_status_message(msg, True)
        return True
    except SublimeHaskellError as e:
        show_status_message(msg, False)
        log(e.reason)
        return False

def crlf2lf(s):
    " CRLF -> LF "
    if not s:
        return ''
    return s.replace('\r\n', '\n')

class StatusMessage(threading.Thread):
    messages = {}
    # List of ((priority, time), StatusMessage)
    # At start, messages adds itself to list, at cancel - removes
    # First element of list is message with highest priority
    priorities_lock = threading.Lock()
    priorities = []

    def __init__(self, msg, timeout, priority):
        super(StatusMessage, self).__init__()
        self.interval = 0.5
        self.start_timeout = timeout
        self.timeout = timeout
        self.priority = priority
        self.msg = msg
        self.times = 0
        self.event = threading.Event()
        self.event.set()
        self.timer = None

    def run(self):
        self.add_to_priorities()
        try:
            self.update_message()
            while self.event.is_set():
                self.timer = threading.Timer(self.interval, self.update_message)
                self.timer.start()
                self.timer.join()
        finally:
            self.remove_from_priorities()

    def cancel(self):
        self.event.clear()
        if self.timer:
            self.timer.cancel()

    def update_message(self):
        dots = self.times % 4
        self.times += 1
        self.timeout -= self.interval

        if self.is_highest_priority():
            sublime_status_message(u'{0}{1}'.format(self.msg, '.' * dots))

        if self.timeout <= 0:
            self.cancel()

    def add_to_priorities(self):
        with StatusMessage.priorities_lock:
            StatusMessage.priorities.append(((self.priority, time.clock()), self))
            StatusMessage.priorities.sort(key = lambda x: (-x[0][0], x[0][1], x[1]))

    def remove_from_priorities(self):
        with StatusMessage.priorities_lock:
            StatusMessage.priorities = [(i, msg) for i, msg in StatusMessage.priorities if msg != self]

    def is_highest_priority(self):
        with StatusMessage.priorities_lock:
            if StatusMessage.priorities:
                return StatusMessage.priorities[0][1] == self
            else:
                return False

    def change_message(self, new_msg):
        # There's progress, don't timeout
        self.timeout = self.start_timeout
        self.msg = new_msg

def show_status_message_process(msg, isok = None, timeout = 300, priority = 0):
    """
    Same as show_status_message, but shows permanently until called with isok not None
    There can be only one message process in time, message with highest priority is shown
    For example, when building project, there must be only message about building
    """
    if isok is not None:
        if msg in StatusMessage.messages:
            StatusMessage.messages[msg].cancel()
            del StatusMessage.messages[msg]
        show_status_message(msg, isok)
    else:
        if msg in StatusMessage.messages:
            StatusMessage.messages[msg].cancel()

        StatusMessage.messages[msg] = StatusMessage(msg, timeout, priority)
        StatusMessage.messages[msg].start()

def is_haskell_source(view = None):
    window, view, file_shown_in_view = get_haskell_command_window_view_file_project(view)

    if not window or not view:
        return False

    syntax_file_for_view = view.settings().get('syntax').lower()
    if not syntax_file_for_view.endswith("Haskell.tmLanguage".lower()):
        return False

    return True

class with_status_message(object):
    def __init__(self, msg, isok, show_message):
        self.msg = msg
        self.isok = isok
        self.show_message = show_message

    def __enter__(self):
        self.show_message(self.msg)
        return self

    def __exit__(self, type, value, traceback):
        if type:
            self.show_message(self.msg, False)
        else:
            self.show_message(self.msg, self.isok)

    def ok(self):
        self.isok = True

    def fail(self):
        self.isok = False

    def change_message(self, new_msg):
        if self.msg in StatusMessage.messages:
            StatusMessage.messages[self.msg].change_message(new_msg)

    def percentage_message(self, current, total = 100):
        self.change_message('{0} ({1}%)'.format(self.msg, int(current * 100 / total)))

def status_message(msg, isok = True):
    return with_status_message(msg, isok, show_status_message)

def status_message_process(msg, isok = True, timeout = 300, priority = 0):
    return with_status_message(msg, isok, lambda m, ok = None: show_status_message_process(m, ok, timeout, priority))

def sublime_haskell_package_path():
    """Get the path to where this package is installed"""
    return os.path.dirname(os.path.realpath(__file__))

def sublime_haskell_cache_path():
    """Get the path where compiled tools and caches are stored"""
    return os.path.join(sublime_haskell_package_path(), os.path.expandvars(get_setting('cache_path', '.')))

def plugin_loaded():
    global CABAL_INSPECTOR_EXE_PATH

    package_path = sublime_haskell_package_path()
    cache_path = sublime_haskell_cache_path()

    log("store compiled tools and caches to {0}".format(cache_path))
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    CABAL_INSPECTOR_EXE_PATH = os.path.join(cache_path, 'CabalInspector')
    preload_settings()

if int(sublime.version()) < 3000:
    plugin_loaded()

########NEW FILE########
__FILENAME__ = symbols
import threading
import sublime

if int(sublime.version()) < 3000:
    from sublime_haskell_common import *
    from haskell_docs import haskell_docs
else:
    from SublimeHaskell.sublime_haskell_common import *
    from SublimeHaskell.haskell_docs import haskell_docs
    from functools import reduce

class Location(object):
    """
    Location in file at line
    """
    def __init__(self, filename, line, column, project = None):
        if not project:
            project = get_cabal_project_dir_of_file(filename)
        self.project = project
        self.filename = filename
        self.line = line
        self.column = column

    def position(self):
        """ Returns filename:line:column """
        return ':'.join([self.filename, str(self.line), str(self.column)])

class Symbol(object):
    """
    Haskell symbol: module, function, data, class etc.
    """
    def __init__(self, symbol_type, name, docs = None, location = None, module = None):
        self.what = symbol_type
        self.name = name
        self.module = module
        self.docs = docs
        self.location = location

        self.tags = {}

    def update_location(self, module_loc):
        """
        JSON contains only line + column
        This function used to merge module location, which contains all other info with line + column
        """
        if self.location and self.by_source():
            self.location.set_file(module_loc)
        else:
            self.location = module_loc

    def full_name(self):
        return self.module.name + '.' + self.name

class Import(object):
    """
    Haskell import of module
    """
    def __init__(self, module_name, is_qualified = False, import_as = None):
        self.module = module_name
        self.is_qualified = is_qualified
        self.import_as = import_as

    def dump(self):
        return self.__dict__

def module_location(filename):
    return Location(filename, 1, 1)

class Module(Symbol):
    """
    Haskell module symbol
    """
    def __init__(self, module_name, exports = [], imports = {}, declarations = {}, location = None, cabal = None, last_inspection_time = 0):
        super(Module, self).__init__('module', module_name, None, location)
        # List of strings
        self.exports = exports
        # Dictionary from module name to Import object
        self.imports = imports.copy()
        # Dictionary from name to Symbol
        self.declarations = declarations.copy()
        for d in self.declarations.values():
            d.update_location(self.location)

        for decl in self.declarations.values():
            decl.module = self

        # Cabal path or 'cabal'
        self.cabal = cabal

        # Time as from time.time()
        self.last_inspection_time = last_inspection_time

    def add_declaration(self, new_declaration):
        if not new_declaration.module:
            new_declaration.module = self
        new_declaration.update_location(self.location)
        if new_declaration.module != self:
            raise RuntimeError("Adding declaration to other module")
        self.declarations[new_declaration.name] = new_declaration

    def unalias(self, module_alias):
        """
        Unalias module import if any
        Returns list of unaliased modules
        """
        return [i.module for i in self.imports.items() if i.import_as == module_alias]

class Declaration(Symbol):
    def __init__(self, name, decl_type = 'declaration', docs = None, location = None, module = None):
        super(Declaration, self).__init__(decl_type, name, docs, location, module)

    def suggest(self):
        """ Returns suggestion for this declaration """
        return (self.name, self.name)

    def brief(self):
        return self.name

    def qualified_name(self):
        return '.'.join([self.module.name, self.name])

    def detailed(self):
        """ Detailed info for use in Symbol Info command """
        info = [
            self.brief(),
            '',
            self.module.name]

        if self.docs:
            info.extend(['', self.docs])

        if self.by_source():
            info.append('')
            if self.location.project:
                info.append('Defined in {0} at {1}'.format(self.location.project, self.location.position()))
            else:
                info.append('Defined at {0}'.format(self.location.position()))
        if self.by_cabal():
            info.append('')
            info.append('Installed in {0} in package {1}'.format(self.location.cabal, self.location.package.package_id()))

        return '\n'.join(info)

class Function(Declaration):
    """
    Haskell function declaration
    """
    def __init__(self, name, function_type, docs = None, location = None, module = None):
        super(Function, self).__init__(name, 'function', docs, location, module)
        self.type = function_type

    def suggest(self):
        return (u'{0}\t{1}'.format(self.name, self.type), self.name)

    def brief(self):
        return u'{0} :: {1}'.format(self.name, self.type if self.type else u'?')

class TypeBase(Declaration):
    """
    Haskell type, data or class
    """
    def __init__(self, name, decl_type, context, args, definition = None, docs = None, location = None, module = None):
        super(TypeBase, self).__init__(name, decl_type, docs, location, module)
        self.context = context
        self.args = args
        self.definition = definition

    def suggest(self):
        return (u'{0}\t{1}'.format(self.name, ' '.join(self.args)), self.name)

    def brief(self):
        brief_parts = [self.what]
        if self.context:
            if len(self.context) == 1:
                brief_parts.append(u'{0} =>'.format(self.context[0]))
            else:
                brief_parts.append(u'({0}) =>'.format(', '.join(self.context)))
        brief_parts.append(self.name)
        if self.args:
            brief_parts.append(u' '.join(self.args))
        if self.definition:
            brief_parts.append(u' = {0}'.format(self.definition))
        return u' '.join(brief_parts)

class Type(TypeBase):
    """
    Haskell type synonym
    """
    def __init__(self, name, context, args, definition = None, docs = None, location = None, module = None):
        super(Type, self).__init__(name, 'type', context, args, definition, docs, location, module)

class Newtype(TypeBase):
    """
    Haskell newtype synonym
    """
    def __init__(self, name, context, args, definition = None, docs = None, location = None, module = None):
        super(Newtype, self).__init__(name, 'newtype', context, args, definition, docs, location, module)

class Data(TypeBase):
    """
    Haskell data declaration
    """
    def __init__(self, name, context, args, definition = None, docs = None, location = None, module = None):
        super(Data, self).__init__(name, 'data', context, args, definition, docs, location, module)

class Class(TypeBase):
    """
    Haskell class declaration
    """
    def __init__(self, name, context, args, docs = None, location = None, module = None):
        super(Class, self).__init__(name, 'class', context, args, None, docs, location, module)

def update_with(l, r, default_value, f):
    """
    unionWith for Python, but modifying first dictionary instead of returning result
    """
    for k, v in r.items():
        if k not in l:
            l[k] = default_value[:]
        l[k] = f(l[k], v)
    return l

def same_module(l, r):
    """
    Returns true if l is same module as r, which is when module name is equal
    and modules defined in one file, in same cabal-dev sandbox or in cabal
    """
    same_cabal = l.cabal and r.cabal and (l.cabal == r.cabal)
    same_filename = l.by_source() and r.by_source() and (l.location.filename == r.location.filename)
    nowhere = (not l.cabal) and (not l.location) and (not r.cabal) and (not r.location)
    return l.name == r.name and (same_cabal or same_filename or nowhere)

def same_declaration(l, r):
    """
    Returns true if l is same declaration as r
    """
    same_mod = l.module and r.module and same_module(l.module, r.module)
    nowhere = (not l.module) and (not r.module)
    return l.name == r.name and (same_mod or nowhere)

class Database(object):
    """
    Database contains storages and indexes to allow fast access to module and symbol info in several storages
    Every info must be added to storages through methods of this class
    """
    def __init__(self):
        # Info is stored in several ways:

        # Dictionary from 'cabal' or cabal-dev path to modules dictionary, where
        # modules dictionary is dictionary from module name to Module
        # Every module is unique in such dictionary
        self.cabal_modules = LockedObject({})

        # Dictionary from filename to Module defined in this file
        self.files = LockedObject({})

        # Indexes: dictionary from module name to list of Modules
        self.modules = LockedObject({})

        # Indexes: dictionary from symbol name to list of Symbols to support Go To Definition
        self.symbols = LockedObject({})

    def get_cabal_modules(self, cabal = None):
        if not cabal:
            cabal = current_cabal()
        with self.cabal_modules as cabal_modules:
            if cabal not in cabal_modules:
                cabal_modules[cabal] = {}
        return LockedObject(self.cabal_modules.object[cabal], self.cabal_modules.object_lock)

    def get_project_modules(self, project_name):
        with self.files as files:
            return dict((f, m) for f, m in files.items() if m.location.project == project_name)

    def add_indexes_for_module(self, new_module):
        def append_return(l, r):
            l.append(r)
            return l

        with self.modules as modules:
            if new_module.name not in modules:
                modules[new_module.name] = []
            modules[new_module.name].append(new_module)

        with self.symbols as decl_symbols:
            update_with(decl_symbols, new_module.declarations, [], append_return)

    def remove_indexes_for_module(self, old_module):
        def remove_return(l, r):
            return [x for x in l if not same_declaration(x, r)]

        with self.modules as modules:
            if old_module.name in modules:
                modules[old_module.name] = [m for m in modules[old_module.name] if not same_module(old_module, m)]

        with self.symbols as decl_symbols:
            update_with(decl_symbols, old_module.declarations, [], remove_return)

    def add_indexes_for_declaration(self, new_declaration):
        with self.symbols as decl_symbols:
            if new_declaration.name not in decl_symbols:
                decl_symbols[new_declaration.name] = []
            decl_symbols[new_declaration.name].append(new_declaration)

    def remove_indexes_for_declaration(self, old_declaration):
        with self.symbols as decl_symbols:
            if old_declaration.name in decl_symbols:
                decl_symbols[old_declaration.name] = [d for d in decl_symbols[old_declaration.name] if not same_declaration(d, old_declaration)]

    def add_module(self, new_module, cabal = None):
        """
        Adds module and updates indexes
        """
        if not cabal:
            if new_module.cabal:
                cabal = new_module.cabal
            else:
                cabal = current_cabal()
                new_module.cabal = cabal

        with self.cabal_modules as cabal_modules:
            if cabal not in cabal_modules:
                cabal_modules[cabal] = {}
            if new_module.name in cabal_modules[cabal]:
                old_module = cabal_modules[cabal][new_module.name]
                self.remove_indexes_for_module(old_module)
                del cabal_modules[cabal][new_module.name]
            if new_module.name not in cabal_modules[cabal]:
                cabal_modules[cabal][new_module.name] = new_module
                self.add_indexes_for_module(new_module)

    def add_file(self, filename, file_module):
        """
        Adds module defined in file and updates indexes
        """
        with self.files as files:
            if filename in files:
                old_module = files[filename]
                self.remove_indexes_for_module(old_module)
                del files[filename]
            if filename not in files:
                files[filename] = file_module
                self.add_indexes_for_module(file_module)

    def add_declaration(self, new_declaration, module):
        """
        Adds declaration to module
        """
        def add_decl_to_module():
            if new_declaration.name in module.declarations:
                self.remove_indexes_for_declaration(module.declarations[new_declaration.name])
            module.add_declaration(new_declaration)
            self.add_indexes_for_declaration(new_declaration)

        if module.location:
            with self.files as files:
                if module.location.filename not in files:
                    raise RuntimeError("Can't add declaration: no file {0}".format(module.location.filename))
                add_decl_to_module()
        elif module.cabal:
            if module.name not in self.cabal_modules.object[module.cabal]:
                raise RuntimeError("Can't add declaration: no module {0}".format(module.name))
            add_decl_to_module()
        else:
            raise RuntimeError("Can't add declaration: no module {0}".format(module.name))



def is_within_project(module, project):
    """
    Returns whether module defined within project specified
    """
    if module.location:
        return module.location.project == project
    return False

def is_within_cabal(module, cabal = None):
    """
    Returns whether module loaded from cabal specified
    If cabal is None, used current cabal
    """
    if not cabal:
        cabal = current_cabal()
    return module.cabal == cabal

def is_by_sources(module):
    """
    Returns whether module defined by sources
    """
    return module.location is not None

def flatten(lsts):
    return reduce(lambda l, r: list(l) + list(r), lsts)

def get_source_modules(modules, filename = None):
    """
    For list of modules with same name returns modules, which is defined by sources
    Prefer module in same project as filename if specified
    """
    project = get_cabal_project_dir_of_file(filename) if filename else None

    candidates = flatten([
        filter(lambda m: is_within_project(m, project), modules),
        filter(is_by_sources, modules)])

    if candidates:
        return candidates[0]
    return None

def get_visible_module(modules, filename = None, cabal = None):
    """
    For list of modules with same name returns module, which is
    1. Defined in same project as filename
    2. Defined in cabal
    3. None
    """
    project = get_cabal_project_dir_of_file(filename) if filename else None

    candidates = flatten([
        filter(lambda m: is_within_project(m, project), modules),
        filter(lambda m: is_within_cabal(m, cabal), modules)])

    if candidates:
        return candidates[0]
    return None

def get_preferred_module(modules, filename = None, cabal = None):
    """
    For list of modules with same name returns module, which is
    1. Defined in same project as filename
    2. Defined in cabal
    3. Defined by sources
    4. Other modules
    Returns None if modules is empty
    """
    if filename:
        project = get_cabal_project_dir_of_file(filename)

    candidates = flatten([
        filter(lambda m: is_within_project(m, project), modules),
        filter(lambda m: is_within_cabal(m, cabal), modules),
        filter(is_by_sources, modules),
        modules])

    if candidates:
        return candidates[0]
    return None

def declarations_modules(decls, select_module = None):
    """
    Reduce list of declarations to dictionary (module_name => select_module(list of modules))
    """
    def add_module_to_dict(d, decl):
        if decl.module.name not in d:
            d[decl.module.name] = []
        d[decl.module.name].append(decl.module)
        return d

    if not select_module:
        select_module = lambda l: l

    result = reduce(add_module_to_dict, decls, {})
    return dict((k, select_module(ms)) for k, ms in result.items() if select_module(ms) is not None)

def is_imported_module(in_module, m, qualified_name = None):
    """
    Returns whether 'm' is imported from 'in_module'
    If 'qualified_name' specified, 'm' must be 'qualified_name' or imported as 'qualified_name'
    """
    if qualified_name:
        if m.name in in_module.imports:
            cur_import = in_module.imports[m.name]
            return cur_import.module == qualified_name or cur_import.import_as == qualified_name
        return False
    else:
        if m.name in in_module.imports:
            return (not in_module.imports[m.name].is_qualified)
        # Return True also on Prelude
        return m.name == 'Prelude'

def is_this_module(this_module, m):
    """
    Returns whether 'm' is the same as 'this_module'
    """
    # Same source
    if this_module.location and m.location and this_module.location.filename == m.location.filename:
        return True
    # Same name and cabal
    if this_module.cabal and m.cabal and this_module.cabal == m.cabal and this_module.name == m.name:
        return True
    return False

########NEW FILE########
__FILENAME__ = util
import sublime

if int(sublime.version()) < 3000:
    import ghci
    import ghcmod
    import haskell_docs
    import hdevtools
    import sublime_haskell_common as common
    import symbols
else:
    import SublimeHaskell.ghci as ghci
    import SublimeHaskell.ghcmod as ghcmod
    import SublimeHaskell.haskell_docs as haskell_docs
    import SublimeHaskell.hdevtools as hdevtools
    import SublimeHaskell.sublime_haskell_common as common
    import SublimeHaskell.symbols as symbols

def symbol_info(filename, module_name, symbol_name, cabal = None, no_ghci = False):
    result = None
    if hdevtools.hdevtools_enabled():
        result = hdevtools.hdevtools_info(filename, symbol_name, cabal = cabal)
    if not result and ghcmod.ghcmod_enabled():
        result = ghcmod.ghcmod_info(filename, module_name, symbol_name, cabal = cabal)
    if not result and not filename and not no_ghci:
        result = ghci.ghci_info(module_name, symbol_name, cabal = cabal)
    return result

def load_docs(decl):
    """
    Tries to load docs for decl
    """
    if decl.docs is None:
        decl.docs = haskell_docs.haskell_docs(decl.module.name, decl.name)

def refine_type(decl, no_ghci = True):
    """
    Refine type for sources decl
    """
    if decl.location:
        if decl.what == 'function' and not decl.type:
            info = symbol_info(decl.location.filename, decl.module.name, decl.name, None, no_ghci = no_ghci)
            if info:
                decl.type = info.type

def refine_decl(decl):
    """
    Refine decl information.
    """
    # Symbol from cabal, try to load detailed info with ghci
    if not decl.location:
        load_docs(decl)

        if decl.what == 'declaration':
            decl_detailed = ghci.ghci_info(decl.module.name, decl.name)
            if decl_detailed:
                decl.__dict__.update(decl_detailed.__dict__)

    # Symbol from sources, concrete type if it's not specified
    else:
        refine_type(decl, False)

def browse_module(module_name, cabal = None):
    """
    Returns symbols.Module with all declarations
    """
    return ghcmod.ghcmod_browse_module(module_name, cabal = cabal)

########NEW FILE########
