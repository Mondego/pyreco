__FILENAME__ = errormarker
try:
    from .highlighter import CodeHighlighter
    from .util import delayed, maybe
except(ValueError):
    from highlighter import CodeHighlighter
    from util import delayed, maybe


class ErrorMarker(object):

    def __init__(self, window, error_report, settings):
        self._window = window
        self._error_report = error_report
        self.__settings = settings
        self.__highlighter = None
        settings.add_on_change(self.mark_errors)

    @delayed(0)
    def mark_errors(self):
        for view in self._window.views():
            errors = self._error_report.sorted_errors_in(view.file_name())
            self._mark_errors_in_view(view, errors)

    @delayed(0)
    def mark_errors_in(self, filename):
        errors = self._error_report.sorted_errors_in(filename)
        for view in self._file_views(filename):
            self._mark_errors_in_view(view, errors)

    @delayed(0)
    def hide_errors_in(self, filename):
        for view in self._file_views(filename):
            self._highlighter.clear(view)

    @delayed(0)
    def mark_error(self, error):
        for view in self._file_views(error.filename):
            self._highlighter.highlight(view, [error])

    @delayed(0)
    def clear(self):
        for view in self._window.views():
            self._highlighter.clear(view)

    @delayed(0)
    def update_status(self):
        self.update_status_now()

    def update_status_now(self):
        for view in maybe(self._window.active_view()):
            self._highlighter.set_status_message(view, self._status_message(view))

    def _mark_errors_in_view(self, view, errors):
        if errors and not view.is_dirty():
            self._highlighter.highlight(view, errors, replace=True)
        else:
            self._highlighter.clear(view)

    def _status_message(self, view):
        for errors in maybe(self._line_errors(view)):
            return '(%s)' % ')('.join([e.message for e in errors])

    def _file_views(self, filename):
        for view in self._window.views():
            if filename == view.file_name():
                yield view

    def _line_errors(self, view):
        row, _ = view.rowcol(view.sel()[0].begin())
        return self._error_report.errors_at(view.file_name(), row + 1)

    def _current_error_in_view(self, view):
        return self._error_report.current_error_in(view.file_name())

    @property
    def _highlighter(self):
        if self.__highlighter is None:
            self.__highlighter = CodeHighlighter(self.__settings, self._current_error_in_view)
        return self.__highlighter

########NEW FILE########
__FILENAME__ = errorreport
try:
    from .sbterror import SbtError
    from .util import maybe
except(ValueError):
    from sbterror import SbtError
    from util import maybe


class ErrorReport(object):

    def __init__(self):
        self._errors = {}
        self._old_errors = {}
        self._new_errors = {}
        self._set_current(None)

    def clear(self):
        self._errors.clear()
        self._old_errors.clear()
        self._new_errors.clear()
        self._set_current(None)

    def add_error(self, error):
        if error.filename not in self._new_errors:
            self._new_errors[error.filename] = {}
        file_errors = self._new_errors[error.filename]
        if error.line not in file_errors:
            file_errors[error.line] = []
        file_errors[error.line].append(error)
        self._merge_errors()

    def cycle(self):
        self._old_errors = self._new_errors
        self._new_errors = {}
        self._merge_errors()

    def all_errors(self):
        for filename in sorted(self._errors.keys()):
            for error in self.sorted_errors_in(filename):
                yield error

    def focus_error(self, error):
        for i, e in enumerate(self.all_errors()):
            if e == error:
                self._set_current(i)

    def next_error(self):
        sorted_errors = list(self.all_errors())
        if sorted_errors:
            if self._index is None:
                self._set_current(0)
            else:
                self._set_current((self._index + 1) % len(sorted_errors))
        else:
            self._set_current(None)
        return self.current_error

    def sorted_errors_in(self, filename):

        def sort_errors(errors):
            for line in sorted(errors.keys()):
                for error in sorted(errors[line], key=lambda e: e.error_type):
                    yield error

        for errors in maybe(self.errors_in(filename)):
            return list(sort_errors(errors))

    def errors_at(self, filename, line):
        for errors in maybe(self.errors_in(filename)):
            return errors.get(line)

    def errors_in(self, filename):
        return self._errors.get(filename)

    def current_error_in(self, filename):
        for error in maybe(self.current_error):
            if error.filename == filename:
                return error

    def clear_file(self, filename):
        for errors in [self._old_errors, self._new_errors, self._errors]:
            if filename in errors:
                del errors[filename]
        if self.current_error_in(filename):
            self._set_current(None)

    def has_errors(self):
        return len(self._errors) > 0

    def _merge_errors(self):
        self._errors = dict(list(self._old_errors.items()) + list(self._new_errors.items()))
        self._set_current(None)

    def _set_current(self, i):
        sorted_errors = list(self.all_errors())
        if i is not None and i < len(sorted_errors):
            self._index = i
            self.current_error = sorted_errors[i]
        else:
            self._index = None
            self.current_error = None

########NEW FILE########
__FILENAME__ = errorreporter
try:
    from .errormarker import ErrorMarker
    from .util import delayed
except(ValueError):
    from errormarker import ErrorMarker
    from util import delayed


class ErrorReporter(object):

    def __init__(self, window, error_report, settings):
        self._marker = ErrorMarker(window, error_report, settings)
        self._error_report = error_report

    def error(self, error):
        self._error_report.add_error(error)
        self._marker.mark_error(error)
        self._marker.update_status()

    def finish(self):
        self._error_report.cycle()
        self._marker.mark_errors()

    def clear(self):
        self._error_report.clear()
        self._marker.clear()

    def show_errors(self):
        self._marker.mark_errors()

    def show_errors_in(self, filename):
        self._marker.mark_errors_in(filename)

    def hide_errors_in(self, filename):
        self._error_report.clear_file(filename)
        self._marker.hide_errors_in(filename)

    def update_status(self):
        self._marker.update_status()

    def update_status_now(self):
        self._marker.update_status_now()

########NEW FILE########
__FILENAME__ = errorview
import sublime
import sublime_plugin

try:
    from .sbtsettings import SBTSettings
    from .util import OnePerWindow
except(ValueError):
    from sbtsettings import SBTSettings
    from util import OnePerWindow


class ErrorView(OnePerWindow):

    error_type_display = {
        'error': 'Error',
        'warning': 'Warning',
        'failure': 'Test Failure'
    }

    def __init__(self, window):
        self.window = window
        self.settings = SBTSettings(window)
        self.panel = self.window.get_output_panel('sbt_error')
        self.panel.set_read_only(True)
        self.panel.settings().set('line_numbers', False)
        self.panel.settings().set('gutter', False)
        self.panel.settings().set('scroll_past_end', False)
        self.panel.set_syntax_file("Packages/SublimeSBT/SBTError.hidden-tmLanguage")
        self._update_panel_colors()
        self.settings.add_on_change(self._update_panel_colors)

    def show(self):
        self._update_panel_colors()
        self.window.run_command('show_panel', {'panel': 'output.sbt_error'})

    def hide(self):
        self.window.run_command('hide_panel', {'panel': 'output.sbt_error'})

    def show_error(self, error):
        self.show()
        self.panel.run_command('sbt_show_error_text',
                               {'text': self._error_text(error)})
        self.panel.sel().clear()
        self.panel.show(0)

    def _error_text(self, error):
        banner = ' -- %s --' % type(self).error_type_display[error.error_type]
        return '%s\n%s' % (banner, error.text)

    def _update_panel_colors(self):
        self.panel.settings().set('color_scheme', self.settings.get('color_scheme'))


class SbtShowErrorTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, text):
        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)
        self.view.set_read_only(True)

########NEW FILE########
__FILENAME__ = highlighter
import sublime

try:
    from .util import group_by, maybe
except(ValueError):
    from util import group_by, maybe


class CodeHighlighter(object):

    error_types = ['error', 'failure', 'warning']

    def __init__(self, settings, current_error_in_view):
        self.settings = settings
        self._current_error_in_view = current_error_in_view
        self.bookmark_key = 'sublimesbt_bookmark'
        self.status_key = 'SBT'
        self._update_highlight_args()
        settings.add_on_change(self._update_highlight_args)

    def set_status_message(self, view, message):
        if message:
            view.set_status(self.status_key, message)
        else:
            view.erase_status(self.status_key)

    def clear(self, view):
        view.erase_regions(self.bookmark_key)
        for error_type in type(self).error_types:
            view.erase_regions(self.region_key(error_type))

    def highlight(self, view, errors, replace=False):
        bookmarked_line = self._bookmark_error(view)
        grouped = group_by(errors, lambda e: e.error_type)
        for error_type in type(self).error_types:
            lines = [e.line for e in grouped.get(error_type, list())]
            lines = [l for l in lines if l != bookmarked_line]
            self._highlight_lines(view, lines, error_type, replace)

    def region_key(self, error_type):
        return 'sublimesbt_%s_marking' % error_type

    def region_scope(self, error_type):
        return self._mark_settings(error_type)['scope']

    def _bookmark_error(self, view):
        for error in maybe(self._current_error_in_view(view)):
            region = self._create_region(view, error.line)
            self._clear_highlight(view, region)
            view.add_regions(self.bookmark_key,
                             [region],
                             self.region_scope(error.error_type),
                             *self._bookmark_args(error.error_type))
            return error.line

    def _highlight_lines(self, view, lines, error_type, replace):
        regions = self._all_regions(view, self._create_regions(view, lines), error_type, replace)
        self._highlight_regions(view, regions, error_type)

    def _highlight_regions(self, view, regions, error_type):
        view.add_regions(self.region_key(error_type),
                         regions,
                         self.region_scope(error_type),
                         *self._highlight_args[error_type])

    def _clear_highlight(self, view, region):
        for error_type in type(self).error_types:
            regions = view.get_regions(self.region_key(error_type))
            if region in regions:
                regions = [r for r in regions if r != region]
                self._highlight_regions(view, regions, error_type)

    def _all_regions(self, view, new_regions, error_type, replace):
        if replace:
            return new_regions
        else:
            return view.get_regions(self.region_key(error_type)) + new_regions

    def _create_regions(self, view, lines):
        return [self._create_region(view, l) for l in lines]

    def _create_region(self, view, lineno):
        line = view.line(view.text_point(lineno - 1, 0))
        r = view.find(r'\S', line.begin())
        if r is not None and line.contains(r):
            return sublime.Region(r.begin(), line.end())
        else:
            return line

    def _bookmark_args(self, error_type):
        return ['bookmark', self._highlight_args[error_type][-1]]

    def _update_highlight_args(self):
        self._highlight_args = {
            'error': self._create_highlight_args('error'),
            'failure': self._create_highlight_args('failure'),
            'warning': self._create_highlight_args('warning')
        }

    def _create_highlight_args(self, error_type):
        style = self._mark_settings(error_type)['style']
        if style == 'dot':
            return ['dot', sublime.HIDDEN]
        elif style == 'outline':
            return [sublime.DRAW_OUTLINED]
        else:
            return ['dot', sublime.DRAW_OUTLINED]

    def _mark_settings(self, error_type):
        return self.settings.get('%s_marking' % error_type)

########NEW FILE########
__FILENAME__ = outputmon
try:
    from .sbterror import SbtError
    from .util import maybe
except(ValueError):
    from sbterror import SbtError
    from util import maybe

import re


class BuildOutputMonitor(object):

    def __init__(self, project):
        self.project = project
        self._parsers = [ErrorParser, TestFailureParser, FinishedParser]
        self._parser = None
        self._buffer = ''

    def __call__(self, output):
        lines = re.split(r'(?:\r\n|\n|\r)', self._buffer + output)
        self._buffer = lines[-1]
        for line in lines[0:-1]:
            self._output_line(self._strip_terminal_codes(line))

    def _output_line(self, line):
        if self._parser:
            self._parser = self._parser.parse(line)
        else:
            self._parser = self._start_parsing(line)

    def _start_parsing(self, line):
        for parser_class in self._parsers:
            for parser in parser_class.start(self.project, line):
                return parser

    def _strip_terminal_codes(self, line):
        return re.sub(r'\033(?:M|\[[0-9;]+[mK])', '', line)


class OutputParser(object):

    def parse(self, line):
        self.finish()


class AbstractErrorParser(OutputParser):

    def __init__(self, project, line, filename, lineno, message):
        self.project = project
        self.reporter = project.error_reporter
        self.filename = filename
        self.lineno = lineno
        self.message = message
        self.extra_lines = []

    def finish(self):
        self.reporter.error(self._error())

    def _extra_line(self, line):
        self.extra_lines.append(line)

    def _error(self):
        return SbtError(project=self.project,
                        filename=self.filename,
                        line=self.lineno,
                        message=self.message,
                        error_type=self.error_type,
                        extra_lines=self.extra_lines)


class ErrorParser(AbstractErrorParser):

    @classmethod
    def start(cls, project, line):
        for m in maybe(re.match(r'\[(error|warn)\]\s+(.+):(\d+):\s+(.+)$', line)):
            yield cls(project,
                      line=line,
                      label=m.group(1),
                      filename=m.group(2),
                      lineno=int(m.group(3)),
                      message=m.group(4))

    def __init__(self, project, line, label, filename, lineno, message):
        AbstractErrorParser.__init__(self, project, line, filename, lineno, message)
        if label == 'warn':
            self.error_type = 'warning'
        else:
            self.error_type = 'error'

    def parse(self, line):
        for t in maybe(self._match_last_line(line)):
            self._extra_line(t)
            return self.finish()
        for t in maybe(self._match_line(line)):
            self._extra_line(t)
            return self
        return self.finish()

    def _match_last_line(self, line):
        for m in maybe(re.match(r'\[(?:error|warn)\] (\s*\^\s*)$', line)):
            return m.group(1)

    def _match_line(self, line):
        for m in maybe(re.match(r'\[(?:error|warn)\] (.*)$', line)):
            return m.group(1)


class TestFailureParser(AbstractErrorParser):

    @classmethod
    def start(cls, project, line):
        for m in maybe(re.match(r'\[(?:error|info)\]\s+(.+)\s+\(([^:]+):(\d+)\)$', line)):
            yield cls(project,
                      line=line,
                      filename=m.group(2),
                      lineno=int(m.group(3)),
                      message=m.group(1))

    def __init__(self, project, line, filename, lineno, message):
        AbstractErrorParser.__init__(self, project, line, filename, lineno, message)
        self.error_type = 'failure'


class FinishedParser(OutputParser):

    @classmethod
    def start(cls, project, line):
        if re.match(r'\[(?:success|error)\] Total time:', line):
            yield cls(project)

    def __init__(self, project):
        self.reporter = project.error_reporter

    def finish(self):
        self.reporter.finish()

########NEW FILE########
__FILENAME__ = project
import sublime

try:
    from .sbtsettings import SBTSettings
    from .errorreport import ErrorReport
    from .errorreporter import ErrorReporter
    from .util import maybe, OnePerWindow
except(ValueError):
    from sbtsettings import SBTSettings
    from errorreport import ErrorReport
    from errorreporter import ErrorReporter
    from util import maybe, OnePerWindow

import os
import re
from glob import glob


class Project(OnePerWindow):

    def __init__(self, window):
        self.window = window
        self.settings = SBTSettings(window)
        self.error_report = ErrorReport()
        self.error_reporter = ErrorReporter(window,
                                            self.error_report,
                                            self.settings)

    def project_root(self):
        for folder in self.window.folders():
            if self._is_sbt_folder(folder):
                return folder

    def is_sbt_project(self):
        return self.project_root() is not None

    def is_play_project(self):
        for root in maybe(self.project_root()):
            if self._play_build_files(root):
                return True

    def sbt_command(self):
        if self.is_play_project():
            return self.settings.play_command()
        else:
            return self.settings.sbt_command()

    def setting(self, name):
        return self.settings.get(name)

    def expand_filename(self, filename):
        if len(os.path.dirname(filename)) > 0:
            return filename
        else:
            return self._find_in_project(filename)

    def relative_path(self, filename):
        return os.path.relpath(filename, self.project_root())

    def open_project_file(self, filename, line):
        full_path = os.path.join(self.project_root(), filename)
        self.window.open_file('%s:%i' % (full_path, line),
                              sublime.ENCODED_POSITION)

    def _is_sbt_folder(self, folder):
        if self._sbt_build_files(folder) or self._scala_build_files(folder):
            return True

    def _sbt_build_files(self, folder):
        return glob(os.path.join(folder, '*.sbt'))

    def _scala_build_files(self, folder):
        return glob(os.path.join(folder, 'project', '*.scala'))

    def _play_build_files(self, folder):
        return list(filter(self._is_play_build, self._scala_build_files(folder)))

    def _is_play_build(self, build_path):
        try:
            with open(build_path, 'r') as build_file:
                for line in build_file.readlines():
                    if re.search(r'\b(?:play\.|Play)Project\b', line):
                        return True
        except:
            return False

    def _find_in_project(self, filename):
        for path, _, files in os.walk(self.project_root()):
            if filename in files:
                return os.path.join(path, filename)

########NEW FILE########
__FILENAME__ = sbterror
try:
    from .util import delayed
except(ValueError):
    from util import delayed

from threading import Event

import re

class SbtError(object):

    def __init__(self, project, filename, line, message, error_type, extra_lines):
        self.line = int(line)
        if len(extra_lines) > 0 and re.match(r' *^', extra_lines[-1]):
            self.column_spec = ':%i' % len(extra_lines[-1])
        else:
            self.column_spec = ''
        self.message = message
        self.error_type = error_type
        self.__finished = Event()
        self.__finish(project, filename, extra_lines)

    @property
    def filename(self):
        self.__finished.wait()
        return self.__filename

    @property
    def relative_path(self):
        self.__finished.wait()
        return self.__relative_path

    @property
    def text(self):
        self.__finished.wait()
        return self.__text

    def list_item(self):
        return [self.message, '%s:%i%s' % (self.relative_path, self.line, self.column_spec)]

    def encoded_position(self):
        return '%s:%i%s' % (self.filename, self.line, self.column_spec)

    @delayed(0)
    def __finish(self, project, filename, extra_lines):
        try:
            self.__filename = project.expand_filename(filename)
            self.__relative_path = project.relative_path(self.__filename)
            if self.error_type == 'failure':
                self.__text = '%s (%s:%i)' % (self.message, filename, self.line)
            else:
                extra_lines.insert(0, '%s:%i: %s' % (self.__relative_path, self.line, self.message))
                self.__text = '\n'.join(extra_lines)
        finally:
            self.__finished.set()

########NEW FILE########
__FILENAME__ = sbtrunner
import sublime

try:
    from .project import Project
    from .util import OnePerWindow
except(ValueError):
    from project import Project
    from util import OnePerWindow

import os
import pipes
import signal
import subprocess
import threading


class SbtRunner(OnePerWindow):

    @classmethod
    def is_sbt_running_for(cls, window):
        return cls(window).is_sbt_running()

    def __init__(self, window):
        self._project = Project(window)
        self._proc = None

    def project_root(self):
        return self._project.project_root()

    def sbt_command(self, command):
        cmdline = self._project.sbt_command()
        if command is not None:
            cmdline.append(command)
        return cmdline

    def start_sbt(self, command, on_start, on_stop, on_stdout, on_stderr):
        if self.project_root() and not self.is_sbt_running():
            self._proc = self._try_start_sbt_proc(self.sbt_command(command),
                                                  on_start,
                                                  on_stop,
                                                  on_stdout,
                                                  on_stderr)

    def stop_sbt(self):
        if self.is_sbt_running():
            self._proc.terminate()

    def kill_sbt(self):
        if self.is_sbt_running():
            self._proc.kill()

    def is_sbt_running(self):
        return (self._proc is not None) and self._proc.is_running()

    def send_to_sbt(self, input):
        if self.is_sbt_running():
            self._proc.send(input)

    def _try_start_sbt_proc(self, cmdline, *handlers):
        try:
            return SbtProcess.start(cmdline,
                                    self.project_root(),
                                    self._project.settings,
                                    *handlers)
        except OSError:
            msg = ('Unable to find "%s".\n\n'
                   'You may need to specify the full path to your sbt command.'
                   % cmdline[0])
            sublime.error_message(msg)


class SbtProcess(object):

    @staticmethod
    def start(*args, **kwargs):
        if sublime.platform() == 'windows':
            return SbtWindowsProcess._start(*args, **kwargs)
        else:
            return SbtUnixProcess._start(*args, **kwargs)

    @classmethod
    def _start(cls, cmdline, cwd, settings, *handlers):
        return cls(cls._start_proc(cmdline, cwd, settings), settings, *handlers)

    @classmethod
    def _start_proc(cls, cmdline, cwd, settings):
        return cls._popen(cmdline,
                          env=cls._sbt_env(settings),
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          cwd=cwd)

    @classmethod
    def _sbt_env(cls, settings):
        return dict(list(os.environ.items()) +
                    [cls._append_opts('SBT_OPTS', cls._sbt_opts(settings))])

    @classmethod
    def _sbt_opts(cls, settings):
        return [
            '-Dfile.encoding=%s' % (settings.get('encoding') or 'UTF-8')
        ]

    @classmethod
    def _append_opts(cls, name, opts):
        existing_opts = os.environ.get(name, None)
        if existing_opts:
            opts = [existing_opts] + opts
        return [name, ' '.join(opts)]

    def __init__(self, proc, settings, on_start, on_stop, on_stdout, on_stderr):
        self._proc = proc
        self._encoding = settings.get('encoding') or 'UTF-8'
        on_start()
        if self._proc.stdout:
            self._start_thread(self._monitor_output,
                               (self._proc.stdout, on_stdout))
        if self._proc.stderr:
            self._start_thread(self._monitor_output,
                               (self._proc.stderr, on_stderr))
        self._start_thread(self._monitor_proc, (on_stop,))

    def is_running(self):
        return self._proc.returncode is None

    def send(self, input):
        self._proc.stdin.write(input.encode())
        self._proc.stdin.flush()

    def _monitor_output(self, pipe, handle_output):
        while True:
            output = os.read(pipe.fileno(), 2 ** 15).decode(self._encoding)
            if output != "":
                handle_output(output)
            else:
                pipe.close()
                return

    def _monitor_proc(self, handle_stop):
        self._proc.wait()
        sublime.set_timeout(handle_stop, 0)

    def _start_thread(self, target, args):
        threading.Thread(target=target, args=args).start()


class SbtUnixProcess(SbtProcess):

    @classmethod
    def _popen(cls, cmdline, **kwargs):
        return subprocess.Popen(cls._shell_cmdline(cmdline),
                                preexec_fn=os.setpgrp,
                                **kwargs)

    @classmethod
    def _shell_cmdline(cls, cmdline):
        shell = os.environ.get('SHELL', '/bin/bash')
        opts = '-ic' if shell.endswith('csh') else '-lic'
        cmd = ' '.join(map(pipes.quote, cmdline))
        return [shell, opts, cmd]

    def terminate(self):
        os.killpg(self._proc.pid, signal.SIGTERM)

    def kill(self):
        os.killpg(self._proc.pid, signal.SIGKILL)


class SbtWindowsProcess(SbtProcess):

    @classmethod
    def _popen(cls, cmdline, **kwargs):
        return subprocess.Popen(cmdline, shell=True, **kwargs)

    @classmethod
    def _sbt_opts(cls, settings):
        return SbtProcess._sbt_opts(settings) + [
            '-Dfile.encoding=%s' % (settings.get('encoding') or 'UTF-8')
        ]

    def terminate(self):
        self.kill()

    def kill(self):
        cmdline = ['taskkill', '/T', '/F', '/PID', str(self._proc.pid)]
        si = subprocess.STARTUPINFO()
        si.dwFlags = subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.call(cmdline, startupinfo=si)

########NEW FILE########
__FILENAME__ = sbtsettings
import sublime

try:
    from .util import maybe
except(ValueError):
    from util import maybe


class SBTSettings(object):

    def __init__(self, window):
        self.window = window
        self._plugin_settings = sublime.load_settings('SublimeSBT.sublime-settings')
        self._migrate_user_config()

    def sbt_command(self):
        return self.get('sbt_command')

    def play_command(self):
        return self._view_settings().get('sbt_command', self._plugin_settings.get('play_command'))

    def test_command(self):
        return self.get('test_command')

    def run_command(self):
        return self.get('run_command')

    def mark_style(self, error_type='error'):
        self.mark_settings(error_type).get('style')

    def error_scope(self, error_type='error'):
        self.mark_settings(error_type).get('scope')

    def color_scheme(self):
        return self.get('color_scheme')

    def mark_settings(self, error_type='error'):
        for settings in maybe(self.get('%s_marking' % error_type)):
            return settings
        return self.global_mark_settings()

    def global_mark_settings(self):
        return {
            'style': self.get('mark_style'),
            'scope': self.get('error_scope')
        }

    def get(self, name):
        return self._view_settings().get(name, self._plugin_settings.get(name))

    def add_on_change(self, on_change):
        self._plugin_settings.add_on_change('SublimeSBT', on_change)

    def _view_settings(self):
        for view in maybe(self.window.active_view()):
            return view.settings().get('SublimeSBT', {})
        return {}

    def _migrate_user_config(self):
        style = self._plugin_settings.get('mark_style', None)
        scope = self._plugin_settings.get('error_scope', None)
        if style is not None or scope is not None:
            for key in ('%s_marking' % t for t in ('error', 'failure', 'warning')):
                mark_settings = self._plugin_settings.get(key, {})
                if style is not None:
                    mark_settings['style'] = style
                if scope is not None:
                    mark_settings['scope'] = scope
                self._plugin_settings.set(key, mark_settings)
            self._plugin_settings.erase('mark_style')
            self._plugin_settings.erase('error_scope')
            sublime.save_settings('SublimeSBT.sublime-settings')

########NEW FILE########
__FILENAME__ = sbtview
import sublime
import sublime_plugin

try:
    from .sbtsettings import SBTSettings
    from .util import maybe, OnePerWindow
except(ValueError):
    from sbtsettings import SBTSettings
    from util import maybe, OnePerWindow

import re


class SbtView(OnePerWindow):

    settings = {
        "line_numbers": False,
        "gutter": False,
        "rulers": [],
        "word_wrap": False,
        "draw_centered": False,
        "highlight_line": False
    }

    @classmethod
    def is_sbt_view(cls, view):
        if view is not None:
            for window in maybe(view.window()):
                sbt_view = cls(window)
                return sbt_view.panel.id() == view.id()

    def __init__(self, window):
        self.window = window
        self.settings = SBTSettings(window)
        self.panel = self.window.get_output_panel('sbt')
        self.panel.set_syntax_file("Packages/SublimeSBT/SBTOutput.hidden-tmLanguage")
        for name, setting in SbtView.settings.items():
            self.panel.settings().set(name, setting)
        self._update_panel_colors()
        self.settings.add_on_change(self._update_panel_colors)
        self._output_size = 0
        self._set_running(False)

    def start(self):
        self.clear_output()
        self.show()
        self._set_running(True)

    def finish(self):
        self.show_output('\n -- Finished --\n')
        self._set_running(False)

    def show(self):
        self._update_panel_colors()
        self.window.run_command('show_panel', {'panel': 'output.sbt'})

    def hide(self):
        self.window.run_command('hide_panel', {'panel': 'output.sbt'})

    def focus(self):
        self.window.focus_view(self.panel)
        self.panel.show(self.panel.size())

    def show_output(self, output):
        output = self._clean_output(output)
        self.show()
        self._append_output(output)
        self._output_size = self.panel.size()
        self.panel.show(self.panel.size())

    def clear_output(self):
        self._erase_output(sublime.Region(0, self.panel.size()))

    def take_input(self):
        input_region = sublime.Region(self._output_size, self.panel.size())
        input = self.panel.substr(input_region)
        if sublime.platform() == 'windows':
            self._append_output('\n')
        else:
            self._erase_output(input_region)
        return input

    def delete_left(self):
        if self.panel.sel()[0].begin() > self._output_size:
            self.panel.run_command('left_delete')

    def delete_bol(self):
        if self.panel.sel()[0].begin() >= self._output_size:
            p = self.panel.sel()[-1].end()
            self._erase_output(sublime.Region(self._output_size, p))

    def delete_word_left(self):
        if self.panel.sel()[0].begin() > self._output_size:
            for r in self.panel.sel():
                p = max(self.panel.word(r).begin(), self._output_size)
                self.panel.sel().add(sublime.Region(p, r.end()))
            self._erase_output(*self.panel.sel())

    def delete_word_right(self):
        if self.panel.sel()[0].begin() >= self._output_size:
            for r in self.panel.sel():
                p = self.panel.word(r).end()
                self.panel.sel().add(sublime.Region(r.begin(), p))
            self._erase_output(*self.panel.sel())

    def update_writability(self):
        self.panel.set_read_only(not self._running or
                                 self.panel.sel()[0].begin() < self._output_size)

    def _set_running(self, running):
        self._running = running
        self.update_writability()

    def _append_output(self, output):
        self._run_command('sbt_append_output', output=output)

    def _erase_output(self, *regions):
        self._run_command('sbt_erase_output',
                          regions=[[r.begin(), r.end()] for r in regions])

    def _run_command(self, name, **kwargs):
        self.panel.set_read_only(False)
        self.panel.run_command(name, kwargs)
        self.update_writability()

    def _clean_output(self, output):
        return self._strip_codes(self._normalize_lines(output))

    def _normalize_lines(self, output):
        return output.replace('\r\n', '\n').replace('\033M', '\r')

    def _strip_codes(self, output):
        return re.sub(r'\033\[[0-9;]+[mK]', '', output)

    def _update_panel_colors(self):
        self.panel.settings().set('color_scheme', self.settings.get('color_scheme'))


class SbtAppendOutputCommand(sublime_plugin.TextCommand):

    def run(self, edit, output):
        for i, s in enumerate(output.split('\r')):
            if i > 0:
                self.view.replace(edit, self.view.line(self.view.size()), s)
            else:
                self.view.insert(edit, self.view.size(), s)


class SbtEraseOutputCommand(sublime_plugin.TextCommand):

    def run(self, edit, regions):
        for a, b in reversed(regions):
            self.view.erase(edit, sublime.Region(int(a), int(b)))

########NEW FILE########
__FILENAME__ = sublimesbt
import sublime_plugin
import sublime

try:
    from .project import Project
    from .sbtrunner import SbtRunner
    from .sbtview import SbtView
    from .errorview import ErrorView
    from .outputmon import BuildOutputMonitor
    from .util import delayed, maybe
except(ValueError):
    from project import Project
    from sbtrunner import SbtRunner
    from sbtview import SbtView
    from errorview import ErrorView
    from outputmon import BuildOutputMonitor
    from util import delayed, maybe

class SbtWindowCommand(sublime_plugin.WindowCommand):

    def __init__(self, *args):
        super(SbtWindowCommand, self).__init__(*args)
        self._project = Project(self.window)
        self._runner = SbtRunner(self.window)
        self._sbt_view = SbtView(self.window)
        self._error_view = ErrorView(self.window)
        self._error_reporter = self._project.error_reporter
        self._error_report = self._project.error_report
        self._monitor_compile_output = BuildOutputMonitor(self._project)

    def is_sbt_project(self):
        return self._project.is_sbt_project()

    def is_play_project(self):
        return self._project.is_play_project()

    def is_sbt_running(self):
        return self._runner.is_sbt_running()

    def start_sbt(self, command=None):
        self._runner.start_sbt(command,
                               on_start=self._sbt_view.start,
                               on_stop=self._sbt_view.finish,
                               on_stdout=self._on_stdout,
                               on_stderr=self._on_stderr)

    def stop_sbt(self):
        self._runner.stop_sbt()

    def kill_sbt(self):
        self._runner.kill_sbt()

    def show_sbt(self):
        self._sbt_view.show()

    def hide_sbt(self):
        self._sbt_view.hide()

    def focus_sbt(self):
        self._sbt_view.focus()

    def take_input(self):
        return self._sbt_view.take_input()

    def send_to_sbt(self, cmd):
        self._runner.send_to_sbt(cmd)

    @delayed(0)
    def show_error(self, error):
        self._error_report.focus_error(error)
        self._error_reporter.show_errors()
        self._error_view.show_error(error)
        self.goto_error(error)

    @delayed(0)
    def goto_error(self, error):
        self.window.open_file(error.encoded_position(), sublime.ENCODED_POSITION)

    def show_error_output(self):
        self._error_view.show()

    def setting(self, name):
        return self._project.setting(name)

    def _on_stdout(self, output):
        self._monitor_compile_output(output)
        self._show_output(output)

    def _on_stderr(self, output):
        self._show_output(output)

    @delayed(0)
    def _show_output(self, output):
        self._sbt_view.show_output(output)


class StartSbtCommand(SbtWindowCommand):

    def run(self):
        self.start_sbt()

    def is_enabled(self):
        return self.is_sbt_project() and not self.is_sbt_running()


class StopSbtCommand(SbtWindowCommand):

    def run(self):
        self.stop_sbt()

    def is_enabled(self):
        return self.is_sbt_running()


class KillSbtCommand(SbtWindowCommand):

    def run(self):
        self.kill_sbt()

    def is_enabled(self):
        return self.is_sbt_running()


class ShowSbtCommand(SbtWindowCommand):

    def run(self):
        self.show_sbt()
        self.focus_sbt()

    def is_enabled(self):
        return self.is_sbt_project()


class SbtSubmitCommand(SbtWindowCommand):

    def run(self):
        self.send_to_sbt(self.take_input() + '\n')

    def is_enabled(self):
        return self.is_sbt_running()


class SbtCommand(SbtWindowCommand):

    def run(self, command):
        if self.is_sbt_running():
            self.send_to_sbt(command + '\n')
        else:
            self.start_sbt(command)

    def is_enabled(self):
        return self.is_sbt_project()


class SbtTestCommand(SbtCommand):

    def run(self):
        super(SbtTestCommand, self).run(self.test_command())

    def test_command(self):
        return self.setting('test_command')


class SbtContinuousTestCommand(SbtTestCommand):

    def test_command(self):
        return '~ ' + super(SbtContinuousTestCommand, self).test_command()


test_only_arg = '*'


class SbtTestOnlyCommand(SbtCommand):

    base_command = 'test-only'

    def run(self):
        self.window.show_input_panel(self.prompt(), test_only_arg,
                                     self.test_only, None, None)

    def test_only(self, arg):
        global test_only_arg
        test_only_arg = arg
        super(SbtTestOnlyCommand, self).run(self.test_command(arg))

    def prompt(self):
        return 'SBT: %s' % self.base_command

    def test_command(self, arg):
        return '%s %s' % (self.base_command, arg)


class SbtContinuousTestOnlyCommand(SbtTestOnlyCommand):

    def test_command(self, arg):
        return '~ ' + super(SbtContinuousTestOnlyCommand, self).test_command(arg)


class SbtTestQuickCommand(SbtTestOnlyCommand):

    base_command = 'test-quick'


class SbtContinuousTestQuickCommand(SbtTestQuickCommand):

    def test_command(self, arg):
        return '~ ' + super(SbtContinuousTestQuickCommand, self).test_command(arg)


class SbtRunCommand(SbtCommand):

    def run(self):
        super(SbtRunCommand, self).run(self.setting('run_command'))


class SbtReloadCommand(SbtCommand):

    def run(self):
        super(SbtReloadCommand, self).run('reload')

    def is_enabled(self):
        return self.is_sbt_running()


class SbtErrorsCommand(SbtWindowCommand):

    def is_enabled(self):
        return self.is_sbt_project() and self._error_report.has_errors()


class ClearSbtErrorsCommand(SbtErrorsCommand):

    def run(self):
        self._error_reporter.clear()


class ListSbtErrorsCommand(SbtErrorsCommand):

    def run(self):
        errors = list(self._error_report.all_errors())
        list_items = [e.list_item() for e in errors]

        def goto_error(index):
            if index >= 0:
                self.show_error(errors[index])

        self.window.show_quick_panel(list_items, goto_error)


class NextSbtErrorCommand(SbtErrorsCommand):

    def run(self):
        self.show_error(self._error_report.next_error())


class ShowSbtErrorOutputCommand(SbtErrorsCommand):

    def run(self):
        self.show_error_output()


class SbtEotCommand(SbtWindowCommand):

    def run(self):
        if sublime.platform() == 'windows':
            self.send_to_sbt('\032')
        else:
            self.send_to_sbt('\004')

    def is_enabled(self):
        return self.is_sbt_running()


class SbtDeleteLeftCommand(SbtWindowCommand):

    def run(self):
        self._sbt_view.delete_left()


class SbtDeleteBolCommand(SbtWindowCommand):

    def run(self):
        self._sbt_view.delete_bol()


class SbtDeleteWordLeftCommand(SbtWindowCommand):

    def run(self):
        self._sbt_view.delete_word_left()


class SbtDeleteWordRightCommand(SbtWindowCommand):

    def run(self):
        self._sbt_view.delete_word_right()


class SbtListener(sublime_plugin.EventListener):

    def on_clone(self, view):
        for reporter in maybe(self._reporter(view)):
            reporter.show_errors_in(view.file_name())

    def on_load(self, view):
        for reporter in maybe(self._reporter(view)):
            reporter.show_errors_in(view.file_name())

    def on_post_save(self, view):
        for reporter in maybe(self._reporter(view)):
            reporter.hide_errors_in(view.file_name())

    def on_modified(self, view):
        for reporter in maybe(self._reporter(view)):
            reporter.show_errors_in(view.file_name())

    def on_selection_modified(self, view):
        if SbtView.is_sbt_view(view):
            SbtView(view.window()).update_writability()
        else:
            for reporter in maybe(self._reporter(view)):
                reporter.update_status_now()

    def on_activated(self, view):
        for reporter in maybe(self._reporter(view)):
            reporter.show_errors_in(view.file_name())

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "in_sbt_view":
            if SbtView.is_sbt_view(view):
                return SbtRunner.is_sbt_running_for(view.window())
            else:
                return False

    def _reporter(self, view):
        for window in maybe(view.window()):
            return Project(window).error_reporter

########NEW FILE########
__FILENAME__ = util
import sublime

import functools
import itertools
import threading


def maybe(value):
    if value is not None:
        yield value


def group_by(xs, kf):
    grouped = {}
    for k, i in itertools.groupby(xs, kf):
        grouped.setdefault(k, []).extend(i)
    return grouped


class delayed(object):

    def __init__(self, timeout):
        self.timeout = timeout

    def __call__(self, f):

        def call_with_timeout(*args, **kwargs):
            sublime.set_timeout(functools.partial(f, *args, **kwargs),
                                self.timeout)

        return call_with_timeout


class SynchronizedCache(object):

    def __init__(self):
        self.__items = {}
        self.__lock = threading.RLock()

    def __call__(self, key, f):
        with self.__lock:
            if key not in self.__items:
                self.__items[key] = f()
            return self.__items[key]


class MetaOnePerWindow(type):

    def __init__(cls, name, bases, dct):
        super(MetaOnePerWindow, cls).__init__(name, bases, dct)
        cls.instance_cache = SynchronizedCache()

    def __call__(cls, window):
        return cls.instance_cache(window.id(), lambda: type.__call__(cls, window))


OnePerWindow = MetaOnePerWindow('OnePerWindow', (object,), {})

########NEW FILE########
