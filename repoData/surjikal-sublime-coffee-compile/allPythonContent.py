__FILENAME__ = coffee_compile
import os
import traceback

import sublime_plugin
import sublime


try:
    from .lib.compilers import CoffeeCompilerModule, CoffeeCompilerExecutableVanilla
    from .lib.exceptions import CoffeeCompilationError, CoffeeCompilationCompilerNotFoundError
    from .lib.sublime_utils import SublimeTextOutputPanel, SublimeTextEditorView
    from .lib.utils import log
except ValueError:
    from lib.compilers import CoffeeCompilerModule, CoffeeCompilerExecutableVanilla
    from lib.exceptions import CoffeeCompilationError, CoffeeCompilationCompilerNotFoundError
    from lib.sublime_utils import SublimeTextOutputPanel, SublimeTextEditorView
    from lib.utils import log


PLATFORM_IS_WINDOWS = (sublime.platform() == 'windows')
DEFAULT_COFFEE_CMD = 'coffee.cmd' if PLATFORM_IS_WINDOWS else 'coffee'
DEFAULT_COMPILER = 'vanilla-executable'


def settings_adapter(settings):

    node_path = settings.get('node_path')

    def get_executable_compiler():
        coffee_executable = settings.get('coffee_executable') or DEFAULT_COFFEE_CMD
        coffee_path = settings.get('coffee_path')
        print(coffee_path)
        return CoffeeCompilerExecutableVanilla(
            node_path
          , coffee_path
          , coffee_executable
        )

    def get_module_compiler():
        cwd = settings.get('cwd')
        return CoffeeCompilerModule(node_path, cwd)

    def get_compiler():
        compiler = settings.get('compiler') or DEFAULT_COMPILER
        if compiler == 'vanilla-executable':
            return get_executable_compiler()
        elif compiler == 'vanilla-module':
            return get_module_compiler()
        else:
            raise InvalidCompilerSettingError(compiler)

    return {
        # (compiler, options)
        'compiler': (get_compiler(), {
            'bare': settings.get('bare')
        }),
        'options': {
            'syntax_patterns': settings.get('syntax_patterns')
        }
    }


def loadSettings():
    return sublime.load_settings("CoffeeCompile.sublime-settings")


class CoffeeCompileCommand(sublime_plugin.TextCommand):

    PANEL_NAME = 'coffeecompile_output'

    def run(self, edit):
        self.settings = loadSettings()
        self.window   = self.view.window()
        self.editor   = SublimeTextEditorView(self.view)

        coffeescript = self.editor.get_text()
        coffeescript = coffeescript.encode('utf8')

        try:
            [compiler, options] = settings_adapter(self.settings)['compiler']
            javascript = self._compile(coffeescript, compiler, options)
            self._write_javascript_to_panel(javascript, edit)
        except CoffeeCompilationError as e:
            self._write_compile_error_to_panel(e, edit)
        except InvalidCompilerSettingError as e:
            e = CoffeeCompilationError(path='', message=str(e), details='')
            self._write_compile_error_to_panel(e, edit)
        except Exception as e:
            e = CoffeeCompilationError(path='', message="Unexpected Exception!", details=traceback.format_exc())
            self._write_compile_error_to_panel(e, edit)

    def is_visible(self):
        settings = loadSettings()
        syntax_patterns = settings_adapter(settings)['options']['syntax_patterns']
        current_syntax  = self.view.settings().get('syntax')
        return len(syntax_patterns) == 0 or current_syntax in syntax_patterns

    def _compile(self, coffeescript, compiler, options):
        filename = self.view.file_name()

        if filename:
            self.settings.set('cwd', os.path.dirname(filename))
        elif not self.settings.get('coffee_path', None):
            raise CoffeeCompilationCompilerNotFoundError()

        return compiler.compile(coffeescript, options)

    def _create_panel(self):
        return SublimeTextOutputPanel(self.window, self.PANEL_NAME)

    def _write_javascript_to_panel(self, javascript, edit):
        panel = self._create_panel()
        panel.set_syntax_file('Packages/JavaScript/JavaScript.tmLanguage')
        panel.display(javascript, edit)

    def _write_compile_error_to_panel(self, error, edit):
        panel = self._create_panel()
        panel.set_syntax_file('Packages/Markdown/Markdown.tmLanguage')
        panel.display(str(error), edit)


class InvalidCompilerSettingError(Exception):
    def __init__(self, compiler):
        self.compiler = compiler
        self.available_compilers = [
            'vanilla-executable',
            'vanilla-module'
        ]
    def __str__(self):
        message = "Compiler `%s` is not a valid compiler setting choice.\n\n" % self.compiler
        message+= "Available choices are:\n\n- "
        message+= "\n- ".join(self.available_compilers)
        message+= "\n"
        return message

########NEW FILE########
__FILENAME__ = compilers
import os
try:                import JSON
except ImportError: import json as JSON

try:
    from .execute import execute
    from .exceptions import CoffeeCompilationUnknownError, CoffeeCompilationOSError, CoffeeModuleNotFoundError, CoffeeExecutableNotFoundError
except ValueError:
    from execute import execute
    from exceptions import CoffeeCompilationUnknownError, CoffeeCompilationOSError, CoffeeModuleNotFoundError, CoffeeExecutableNotFoundError


class CoffeeCompiler(object):

    def __init__(self, node_path=None):
        self.node_path = node_path

    def compile(self, coffeescript, options={}):
        raise NotImplementedError()

    def _execute(self, args, coffeescript='', cwd=None):
        path = self._get_path()
        self.path = path # FIXME: Side effect... required by exceptions raised from derived classes.
        try:
            javascript, error = execute(args=args, message=coffeescript, path=path, cwd=cwd)
            if error: raise CoffeeCompilationUnknownError(path, error)
            return javascript
        except OSError as e:
            raise CoffeeCompilationOSError(self.path, e)

    def _get_path(self):
        path = os.environ.get('PATH', '').split(os.pathsep)
        if self.node_path: path.append(self.node_path)
        return path


class CoffeeCompilerModule(CoffeeCompiler):

    def __init__(self, node_path=None, cwd=None):
        CoffeeCompiler.__init__(self, node_path)
        self.cwd = cwd

    def compile(self, coffeescript, options={}):
        bootstrap  = self._get_bootstrap_script(options)
        javascript = self._execute(
            args=['node', '-e', bootstrap]
          , coffeescript=coffeescript
          , cwd=self.cwd
        )
        if javascript.startswith('module.js'):
            require_search_paths = self._get_require_search_paths()
            raise CoffeeModuleNotFoundError(self.path, javascript, require_search_paths)
        return javascript

    def _get_bootstrap_script(self, options={}):
        return """
        var coffee = require('coffee-script');
        var buffer = "";
        process.stdin.on('data', function(d) { buffer += d; });
        process.stdin.on('end',  function()  { console.log(coffee.compile(buffer, %s)); });
        process.stdin.read();
        """ % self._options_to_json(options)

    def _get_require_search_paths(self):
        return self._execute(
            args=['node', '-e', "console.log(module.paths)"]
          , cwd=self.cwd
        )

    def _options_to_json(self, options={}):
        return 'null'
        return JSON.dumps({
            'bare': options.get('bare', False)
        })


class CoffeeCompilerExecutable(CoffeeCompiler):

    def __init__(self, node_path=None, coffee_path=None, coffee_executable=None):
        CoffeeCompiler.__init__(self, node_path)
        self.coffee_path       = coffee_path
        self.coffee_executable = coffee_executable

    def compile(self, coffeescript, args):
        javascript = self._execute(
            coffeescript=coffeescript
          , args=([self.coffee_executable] + args)
        )
        if javascript == "env: node: No such file or directory":
            raise CoffeeExecutableNotFoundError(self.path, javascript)
        return javascript

    def _get_path(self):
        path = CoffeeCompiler._get_path(self)
        if self.coffee_path: path.append(self.coffee_path)
        return path


class CoffeeCompilerExecutableVanilla(CoffeeCompilerExecutable):

    def compile(self, coffeescript, options):
        return CoffeeCompilerExecutable.compile(self,
            coffeescript=coffeescript
          , args=self._options_to_args(options)
        )

    def _options_to_args(self, options):
        args = ['--stdio', '--print']
        if options.get('bare'): args.append('--bare')
        return args

########NEW FILE########
__FILENAME__ = exceptions


class CoffeeCompilationError(Exception):
    """ Raised when something went wrong with the subprocess call """
    def __init__(self, path, message, details):
        self.path = path
        self.message = message
        self.details = details

    def __str__(self):
        output = \
"""# CoffeeCompile Error :(

%(message)s

## Details
```
%(details)s
```

## Halp
If you're sure that you've configured the plugin properly,
please open up an issue and I'll try to help you out!

https://github.com/surjikal/sublime-coffee-compile/issues

## Path
```
%(path)s
```
"""
        return output % {
            'message': self.message
          , 'details': self.details
          , 'path': "\n".join(self.path)
        }


class CoffeeCompilationOSError(CoffeeCompilationError):

    def __init__(self, path, osError):
        message = "An OS Error was raised after calling your `coffee` executable\n"

        if osError.errno is 2:
            message  = "Could not find your `coffee` executable...\n"
            message += "Your `coffee_path` setting is probably not configured properly.\n\n"
            message += "To configure CoffeeCompile, go to:\n"
            message += "`Preferences > Package Settings > CoffeeCompile > Settings - User`"


        super(CoffeeCompilationOSError, self).__init__(
            path=path
          , message=message
          , details=repr(osError)
        )


class CoffeeCompilationCompilerNotFoundError(CoffeeCompilationError):

    def __init__(self):
        message = "Couldn't compile your coffee... can't find your coffee compiler!"

        details  = "CoffeeCompile can't use the nodejs/module-based compiler because you're\n"
        details += "editing an unsaved file, and therefore don't have a current working directory.\n\n"

        details += "You probably want to use the `coffee_path` setting, since it lets you\n"
        details += "explicitly set a path to your coffee script compiler.\n\n"

        details += "To configure CoffeeCompile and the `coffee_path` setting, go to:\n"
        details += "`Preferences > Package Settings > CoffeeCompile > Settings - User`"

        super(CoffeeCompilationCompilerNotFoundError, self).__init__(
            path=''
          , message=message
          , details=details
        )



class CoffeeModuleNotFoundError(CoffeeCompilationError):
    def __init__(self, path, details, require_search_paths):
        message  = "NodeJS cannot find your `coffee-script` module.\n\n\n"

        message += "## `module.paths`:\n"
        message += require_search_paths
        message += "\n"

        super(CoffeeModuleNotFoundError, self).__init__(
            path=path
          , message=message
          , details=details
        )


class CoffeeExecutableNotFoundError(CoffeeCompilationError):
    def __init__(self, path, details):
        message  = "Your `coffee` executable couldn't find NodeJS in his path.\n"
        message += "Your `node_path` setting is probably not configured properly.\n\n"
        message += "To configure CoffeeCompile, go to:\n"
        message += "`Preferences > Package Settings > CoffeeCompile > Settings - User`"

        super(CoffeeExecutableNotFoundError, self).__init__(
            path=path
          , message=message
          , details=details
        )


class CoffeeCompilationUnknownError(CoffeeCompilationError):
    def __init__(self, path, details):
        super(CoffeeCompilationUnknownError, self).__init__(
            path=path
          , message='Something went horribly wrong compiling your coffee D:'
          , details=details
        )

########NEW FILE########
__FILENAME__ = execute
import os
import subprocess
import sublime
import sys

try:
    from .utils import log
except ValueError:
    from utils import log


PLATFORM_IS_WINDOWS = (sublime.platform() == 'windows')


def execute(args, message='', path=None, cwd=None):
    # This is needed for Windows... not sure why. See:
    # https://github.com/surjikal/sublime-coffee-compile/issues/13
    if path:
        log('Path:')
        log("\n".join(path))
        path = os.pathsep.join(path)
        if PLATFORM_IS_WINDOWS:
            log('Platform is Windows!')
            os.environ['PATH'] = path
            path = None

    env = {'PATH': path} if path else None
    log('Env:')
    log(env)
    log('Args:')
    log(args)

    process = subprocess.Popen(args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=_get_startupinfo(),
        env=env,
        cwd=cwd)

    output, error = process.communicate(message)

    if output:
        output = output.decode('utf8')
        output = output.strip()

    return (output, error)


def _get_startupinfo():
    if PLATFORM_IS_WINDOWS:
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        return info
    return None


########NEW FILE########
__FILENAME__ = sublime_utils
import sublime


def get_sublime_version():
    if int(sublime.version()) < 3000: return 2
    return 3


def is_sublime_text_2():
    return get_sublime_version() == 2


class SublimeTextOutputPanel:

    def __init__(self, window, name):
        self.name = name
        self._window = window
        self._panel = self._get_or_create_panel(window, name)

    def show(self):
        self._window.run_command('show_panel', {'panel': 'output.%s' % self.name})

    def write(self, text, edit=None):
        self._panel.set_read_only(False)
        if is_sublime_text_2():
            if not edit:
                edit = self._panel.begin_edit()
            self._panel.insert(edit, 0, text)
            self._panel.end_edit(edit)
            self._panel.sel().clear()
        else:
            self._panel.run_command('append', {'characters': text})

    def display(self, text, edit=None):
        self.write(text, edit)
        self.show()

    def set_syntax_file(self, syntax_file):
        self._panel.set_syntax_file(syntax_file)

    def _get_or_create_panel(self, window, name):
        try:
            return window.get_output_panel(name)
        except AttributeError:
            log("Couldn't get output panel.")
            return window.create_output_panel(name)


class SublimeTextEditorView:
    def __init__(self, view):
        self._view = view

    def get_text(self):
        return self.get_selected_text() or self.get_all_text()

    def has_selected_text(self):
        for region in self._view.sel():
            if not region.empty(): return True
        return False

    def get_selected_text(self):
        if not self.has_selected_text():
            return None
        region = self._get_selected_region()
        return self._view.substr(region)

    def get_all_text(self):
        region = self._get_full_region()
        return self._view.substr(region)

    def _get_selected_region(self):
         return self._view.sel()[0]

    def _get_full_region(self):
        return sublime.Region(0, self._view.size())

########NEW FILE########
__FILENAME__ = utils
import sys

def log(msg):
    sys.stdout.write("[CoffeeCompile] %s\n" % msg)

########NEW FILE########
