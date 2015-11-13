__FILENAME__ = ex_commands
import sublime
import sublime_plugin

import sys
import os

# We use several commands implemented in Vintange, so make it available here.
sys.path.append(os.path.join(sublime.packages_path(), 'Vintage'))

import re
import subprocess

from vintage import g_registers

from plat.windows import get_oem_cp
from plat.windows import get_startup_info
from vex import ex_error
from vex import ex_range
from vex import shell
from vex import parsers

GLOBAL_RANGES = []

CURRENT_LINE_RANGE = {'left_ref': '.', 'left_offset': 0, 'left_search_offsets': [],
                      'right_ref': None, 'right_offset': 0, 'right_search_offsets': []}


class VintageExState(object):
    # When repeating searches, determines which search term to use: the current
    # word or the latest search term.
    # Values: find_under, search_pattern
    search_buffer_type = 'find_under'


def is_any_buffer_dirty(window):
    for v in window.views():
        if v.is_dirty():
            return True


# TODO: this code must be shared with Vintage, not reimplemented here.
def set_register(text, register):
    global g_registers
    if register == '*' or register == '+':
        sublime.set_clipboard(text)
    elif register == '%':
        pass
    else:
        reg = register.lower()
        append = (reg != register)

        if append and reg in g_registers:
            g_registers[reg] += text
        else:
            g_registers[reg] = text


def gather_buffer_info(v):
    """gathers data to be displayed by :ls or :buffers
    """
    path = v.file_name()
    if path:
        parent, leaf = os.path.split(path)
        parent = os.path.basename(parent)
        path = os.path.join(parent, leaf)
    else:
        path = v.name() or str(v.buffer_id())
        leaf = v.name() or 'untitled'

    status = []
    if not v.file_name():
        status.append("t")
    if v.is_dirty():
        status.append("*")
    if v.is_read_only():
        status.append("r")

    if status:
        leaf += ' (%s)' % ', '.join(status)
    return [leaf, path]


def get_region_by_range(view, line_range=None, as_lines=False):
    # If GLOBAL_RANGES exists, the ExGlobal command has been run right before
    # the current command, and we know we must process these lines.
    global GLOBAL_RANGES
    if GLOBAL_RANGES:
        rv = GLOBAL_RANGES[:]
        GLOBAL_RANGES = []
        return rv

    if line_range:
        vim_range = ex_range.VimRange(view, line_range)
        if as_lines:
            return vim_range.lines()
        else:
            return vim_range.blocks()


class ExGoto(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None):
        if not line_range['text_range']:
            # No-op: user issued ":".
            return
        ranges, _ = ex_range.new_calculate_range(self.view, line_range)
        a, b = ranges[0]
        self.view.run_command('vi_goto_line', {'repeat': b})
        self.view.show(self.view.sel()[0])


class ExShellOut(sublime_plugin.TextCommand):
    """Ex command(s): :!cmd, :'<,>'!cmd

    Run cmd in a system's shell or filter selected regions through external
    command.
    """
    def run(self, edit, line_range=None, shell_cmd=''):
        try:
            if line_range['text_range']:
                shell.filter_thru_shell(
                                view=self.view,
                                regions=get_region_by_range(self.view, line_range=line_range),
                                cmd=shell_cmd)
            else:
                shell.run_and_wait(self.view, shell_cmd)
        except NotImplementedError:
            ex_error.handle_not_implemented()


class ExShell(sublime_plugin.TextCommand):
    """Ex command(s): :shell

    Opens a shell at the current view's directory. Sublime Text keeps a virtual
    current directory that most of the time will be out of sync with the actual
    current directory. The virtual current directory is always set to the
    current view's directory, but it isn't accessible through the API.
    """
    def open_shell(self, command):
        view_dir = os.path.dirname(self.view.file_name())
        return subprocess.Popen(command, cwd=view_dir)

    def run(self, edit):
        if sublime.platform() == 'linux':
            term = self.view.settings().get('vintageex_linux_terminal')
            term = term or os.environ.get('COLORTERM') or os.environ.get("TERM")
            if not term:
                sublime.status_message("VintageEx: Not terminal name found.")
                return
            try:
                self.open_shell([term, '-e', 'bash']).wait()
            except Exception as e:
                print e
                sublime.status_message("VintageEx: Error while executing command through shell.")
                return
        elif sublime.platform() == 'osx':
            term = self.view.settings().get('vintageex_osx_terminal')
            term = term or os.environ.get('COLORTERM') or os.environ.get("TERM")
            if not term:
                sublime.status_message("VintageEx: Not terminal name found.")
                return
            try:
                self.open_shell([term, '-e', 'bash']).wait()
            except Exception as e:
                print e
                sublime.status_message("VintageEx: Error while executing command through shell.")
                return
        elif sublime.platform() == 'windows':
            self.open_shell(['cmd.exe', '/k']).wait()
        else:
            # XXX OSX (make check explicit)
            ex_error.handle_not_implemented()


class ExReadShellOut(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None, name='', plusplus_args='', forced=False):
        target_line = self.view.line(self.view.sel()[0].begin())
        if line_range['text_range']:
            range = max(ex_range.calculate_range(self.view, line_range=line_range)[0])
            target_line = self.view.line(self.view.text_point(range, 0))
        target_point = min(target_line.b + 1, self.view.size())

        # cheat a little bit to get the parsing right:
        #   - forced == True means we need to execute a command
        if forced:
            if sublime.platform() == 'linux':
                for s in self.view.sel():
                    # TODO: make shell command configurable.
                    the_shell = self.view.settings().get('linux_shell')
                    the_shell = the_shell or os.path.expandvars("$SHELL")
                    if not the_shell:
                        sublime.status_message("VintageEx: No shell name found.")
                        return
                    try:
                        p = subprocess.Popen([the_shell, '-c', name],
                                                            stdout=subprocess.PIPE)
                    except Exception as e:
                        print e
                        sublime.status_message("VintageEx: Error while executing command through shell.")
                        return
                    self.view.insert(edit, s.begin(), p.communicate()[0][:-1])
            elif sublime.platform() == 'windows':
                for s in self.view.sel():
                    p = subprocess.Popen(['cmd.exe', '/C', name],
                                            stdout=subprocess.PIPE,
                                            startupinfo=get_startup_info()
                                            )
                    cp = 'cp' + get_oem_cp()
                    rv = p.communicate()[0].decode(cp)[:-2].strip()
                    self.view.insert(edit, s.begin(), rv)
            else:
                ex_error.handle_not_implemented()
        # Read a file into the current view.
        else:
            # According to Vim's help, :r should read the current file's content
            # if no file name is given, but Vim doesn't do that.
            # TODO: implement reading a file into the buffer.
            ex_error.handle_not_implemented()
            return


class ExPromptSelectOpenFile(sublime_plugin.TextCommand):
    """Ex command(s): :ls, :files

    Shows a quick panel listing the open files only. Provides concise
    information about the buffers's state: 'transient', 'unsaved'.
    """
    def run(self, edit):
        self.file_names = [gather_buffer_info(v)
                                        for v in self.view.window().views()]
        self.view.window().show_quick_panel(self.file_names, self.on_done)

    def on_done(self, idx):
        if idx == -1: return
        sought_fname = self.file_names[idx]
        for v in self.view.window().views():
            if v.file_name() and v.file_name().endswith(sought_fname[1]):
                self.view.window().focus_view(v)
            # XXX Base all checks on buffer id?
            elif sought_fname[1].isdigit() and \
                                        v.buffer_id() == int(sought_fname[1]):
                self.view.window().focus_view(v)


class ExMap(sublime_plugin.TextCommand):
    # do at least something moderately useful: open the user's .sublime-keymap
    # file
    def run(self, edit):
        if sublime.platform() == 'windows':
            platf = 'Windows'
        elif sublime.platform() == 'linux':
            platf = 'Linux'
        else:
            platf = 'OSX'
        self.view.window().run_command('open_file', {'file':
                                        '${packages}/User/Default (%s).sublime-keymap' % platf})


class ExAbbreviate(sublime_plugin.TextCommand):
    # for them moment, just open a completions file.
    def run(self, edit):
        abbs_file_name = 'VintageEx Abbreviations.sublime-completions'
        abbreviations = os.path.join(sublime.packages_path(),
                                     'User/' + abbs_file_name)
        if not os.path.exists(abbreviations):
            with open(abbreviations, 'w') as f:
                f.write('{\n\t"scope": "",\n\t"completions": [\n\t\n\t]\n}\n')

        self.view.window().run_command('open_file',
                                    {'file': "${packages}/User/%s" % abbs_file_name})


class ExPrintWorkingDir(sublime_plugin.TextCommand):
    def run(self, edit):
        sublime.status_message(os.getcwd())


class ExWriteFile(sublime_plugin.TextCommand):
    def run(self, edit,
                line_range=None,
                forced=False,
                file_name='',
                plusplus_args='',
                operator='',
                target_redirect='',
                subcmd=''):

        if file_name and target_redirect:
            sublime.status_message('VintageEx: Too many arguments.')
            return

        appending = operator == '>>'
        # FIXME: reversed? -- what's going on here!!
        a_range = line_range['text_range']
        content = get_region_by_range(self.view, line_range=line_range) if a_range else \
                        [sublime.Region(0, self.view.size())]

        if target_redirect or file_name:
            target = self.view.window().new_file()
            target.set_name(target_redirect or file_name)
        else:
            target = self.view

        start = 0 if not appending else target.size()
        prefix = '\n' if appending and target.size() > 0 else ''

        if appending or target_redirect or file_name:
            for frag in reversed(content):
                target.insert(edit, start, prefix + self.view.substr(frag) + '\n')
        elif a_range:
            start_deleting = 0
            for frag in content:
                text = self.view.substr(frag) + '\n'
                self.view.insert(edit, 0, text)
                start_deleting += len(text)
            self.view.replace(edit, sublime.Region(start_deleting,
                                        self.view.size()), '')
        else:
            if self.view.is_dirty():
                self.view.run_command('save')


class ExWriteAll(sublime_plugin.TextCommand):
    def run(self, edit, forced=False):
        for v in self.view.window().views():
            if v.is_dirty():
                v.run_command('save')


class ExNewFile(sublime_plugin.TextCommand):
    def run(self, edit, forced=False):
        self.view.window().run_command('new_file')


class ExFile(sublime_plugin.TextCommand):
    def run(self, edit, forced=False):
        # XXX figure out what the right params are. vim's help seems to be
        # wrong
        if self.view.file_name():
            fname = self.view.file_name()
        else:
            fname = 'untitled'

        attrs = ''
        if self.view.is_read_only():
            attrs = 'readonly'

        if self.view.is_scratch():
            attrs = 'modified'

        lines = 'no lines in the buffer'
        if self.view.rowcol(self.view.size())[0]:
            lines = self.view.rowcol(self.view.size())[0] + 1

        # fixme: doesn't calculate the buffer's % correctly
        if not isinstance(lines, basestring):
            vr = self.view.visible_region()
            start_row, end_row = self.view.rowcol(vr.begin())[0], \
                                              self.view.rowcol(vr.end())[0]
            mid = (start_row + end_row + 2) / 2
            percent = float(mid) / lines * 100.0

        msg = fname
        if attrs:
            msg += " [%s]" % attrs
        if isinstance(lines, basestring):
            msg += " -- %s --"  % lines
        else:
            msg += " %d line(s) --%d%%--" % (lines, int(percent))

        sublime.status_message('VintageEx: %s' % msg)


class ExMove(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None, forced=False, address=''):
        # make sure we have a default range
        if not line_range['text_range']:
            line_range['text_range'] = '.'
        address_parser = parsers.cmd_line.AddressParser(address)
        parsed_address = address_parser.parse()
        address = ex_range.calculate_address(self.view, parsed_address)
        if address is None:
            ex_error.display_error(ex_error.ERR_INVALID_ADDRESS)
            return

        line_block = get_region_by_range(self.view, line_range=line_range)
        line_block = [self.view.substr(r) for r in line_block]

        text = '\n'.join(line_block) + '\n'
        if address != 0:
            dest = self.view.line(self.view.text_point(address, 0)).end() + 1
        else:
            dest = 0

        # Don't move lines onto themselves.
        for sel in self.view.sel():
            if sel.contains(dest):
                ex_error.display_error(ex_error.ERR_CANT_MOVE_LINES_ONTO_THEMSELVES)
                return

        if dest > self.view.size():
            dest = self.view.size()
            text = '\n' + text[:-1]
        self.view.insert(edit, dest, text)

        for r in reversed(get_region_by_range(self.view, line_range)):
            self.view.erase(edit, self.view.full_line(r))


class ExCopy(sublime_plugin.TextCommand):
    # todo: do null ranges always default to '.'?
    def run(self, edit, line_range=CURRENT_LINE_RANGE, forced=False, address=''):
        address_parser = parsers.cmd_line.AddressParser(address)
        parsed_address = address_parser.parse()
        address = ex_range.calculate_address(self.view, parsed_address)
        if address is None:
            ex_error.display_error(ex_error.ERR_INVALID_ADDRESS)
            return

        line_block = get_region_by_range(self.view, line_range=line_range)
        line_block = [self.view.substr(r) for r in line_block]

        text = '\n'.join(line_block) + '\n'
        if address != 0:
            dest = self.view.line(self.view.text_point(address, 0)).end() + 1
        else:
            dest = address
        if dest > self.view.size():
            dest = self.view.size()
            text = '\n' + text[:-1]
        self.view.insert(edit, dest, text)

        self.view.sel().clear()
        cursor_dest = self.view.line(dest + len(text) - 1).begin()
        self.view.sel().add(sublime.Region(cursor_dest, cursor_dest))


class ExOnly(sublime_plugin.TextCommand):
    """ Command: :only
    """
    def run(self, edit, forced=False):
        if not forced:
            if is_any_buffer_dirty(self.view.window()):
                ex_error.display_error(ex_error.ERR_OTHER_BUFFER_HAS_CHANGES)
                return

        w = self.view.window()
        current_id = self.view.id()
        for v in w.views():
            if v.id() != current_id:
                if forced and v.is_dirty():
                    v.set_scratch(True)
                w.focus_view(v)
                w.run_command('close')


class ExDoubleAmpersand(sublime_plugin.TextCommand):
    """ Command :&&
    """
    def run(self, edit, line_range=None, flags='', count=''):
        self.view.run_command('ex_substitute', {'line_range': line_range,
                                                'pattern': flags + count})


class ExSubstitute(sublime_plugin.TextCommand):
    most_recent_pat = None
    most_recent_flags = ''
    most_recent_replacement = ''

    def run(self, edit, line_range=None, pattern=''):

        # :s
        if not pattern:
            pattern = ExSubstitute.most_recent_pat
            replacement = ExSubstitute.most_recent_replacement
            flags = ''
            count = 0
        # :s g 100 | :s/ | :s// | s:/foo/bar/g 100 | etc.
        else:
            try:
                parts = parsers.s_cmd.split(pattern)
            except SyntaxError, e:
                sublime.status_message("VintageEx: (substitute) %s" % e)
                print "VintageEx: (substitute) %s" % e
                return
            else:
                if len(parts) == 4:
                    # This is a full command in the form :s/foo/bar/g 100 or a
                    # partial version of it.
                    (pattern, replacement, flags, count) = parts
                else:
                    # This is a short command in the form :s g 100 or a partial
                    # version of it.
                    (flags, count) = parts
                    pattern = ExSubstitute.most_recent_pat
                    replacement = ExSubstitute.most_recent_replacement

        if not pattern:
            pattern = ExSubstitute.most_recent_pat
        else:
            ExSubstitute.most_recent_pat = pattern
            ExSubstitute.most_recent_replacement = replacement
            ExSubstitute.most_recent_flags = flags

        computed_flags = 0
        computed_flags |= re.IGNORECASE if (flags and 'i' in flags) else 0
        try:
            pattern = re.compile(pattern, flags=computed_flags)
        except Exception, e:
            sublime.status_message("VintageEx [regex error]: %s ... in pattern '%s'" % (e.message, pattern))
            print "VintageEx [regex error]: %s ... in pattern '%s'" % (e.message, pattern)
            return

        replace_count = 0 if (flags and 'g' in flags) else 1

        target_region = get_region_by_range(self.view, line_range=line_range, as_lines=True)
        for r in reversed(target_region):
            line_text = self.view.substr(self.view.line(r))
            rv = re.sub(pattern, replacement, line_text, count=replace_count)
            self.view.replace(edit, self.view.line(r), rv)


class ExDelete(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None, register='', count=''):
        # XXX somewhat different to vim's behavior
        rs = get_region_by_range(self.view, line_range=line_range)
        self.view.sel().clear()

        to_store = []
        for r in rs:
            self.view.sel().add(r)
            if register:
                to_store.append(self.view.substr(self.view.full_line(r)))

        if register:
            text = ''.join(to_store)
            # needed for lines without a newline character
            if not text.endswith('\n'):
                text = text + '\n'
            set_register(text, register)

        self.view.run_command('split_selection_into_lines')
        self.view.run_command('run_macro_file',
                        {'file': 'Packages/Default/Delete Line.sublime-macro'})


class ExGlobal(sublime_plugin.TextCommand):
    """Ex command(s): :global

    :global filters lines where a pattern matches and then applies the supplied
    action to all those lines.

    Examples:
        :10,20g/FOO/delete

        This command deletes all lines between line 10 and line 20 where 'FOO'
        matches.

        :g:XXX:s!old!NEW!g

        This command replaces all instances of 'old' with 'NEW' in every line
        where 'XXX' matches.

    By default, :global searches all lines in the buffer.

    If you want to filter lines where a pattern does NOT match, add an
    exclamation point:

        :g!/DON'T TOUCH THIS/delete
    """
    most_recent_pat = None
    def run(self, edit, line_range=None, forced=False, pattern=''):

        if not line_range['text_range']:
            line_range['text_range'] = '%'
            line_range['left_ref'] = '%'
        try:
            global_pattern, subcmd = parsers.g_cmd.split(pattern)
        except ValueError:
            msg = "VintageEx: Bad :global pattern. (%s)" % pattern
            sublime.status_message(msg)
            print msg
            return

        if global_pattern:
            ExGlobal.most_recent_pat = global_pattern
        else:
            global_pattern = ExGlobal.most_recent_pat

        # Make sure we always have a subcommand to exectute. This is what
        # Vim does too.
        subcmd = subcmd or 'print'

        rs = get_region_by_range(self.view, line_range=line_range, as_lines=True)

        for r in rs:
            try:
                match = re.search(global_pattern, self.view.substr(r))
            except Exception, e:
                msg = "VintageEx (global): %s ... in pattern '%s'" % (str(e), global_pattern)
                sublime.status_message(msg)
                print msg
                return
            if (match and not forced) or (not match and forced):
                GLOBAL_RANGES.append(r)

        # don't do anything if we didn't found any target ranges
        if not GLOBAL_RANGES:
            return
        self.view.window().run_command('vi_colon_input',
                              {'cmd_line': ':' +
                                    str(self.view.rowcol(r.a)[0] + 1) +
                                    subcmd})


class ExPrint(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None, count='1', flags=''):
        if not count.isdigit():
            flags, count = count, ''
        rs = get_region_by_range(self.view, line_range=line_range)
        to_display = []
        for r in rs:
            for line in self.view.lines(r):
                text = self.view.substr(line)
                if '#' in flags:
                    row = self.view.rowcol(line.begin())[0] + 1
                else:
                    row = ''
                to_display.append((text, row))

        v = self.view.window().new_file()
        v.set_scratch(True)
        if 'l' in flags:
            v.settings().set('draw_white_space', 'all')
        for t, r in to_display:
            v.insert(edit, v.size(), (str(r) + ' ' + t + '\n').lstrip())


# TODO: General note for all :q variants:
#   ST has a notion of hot_exit, whereby it preserves all buffers so that they
#   can be restored next time you open ST. With this option on, all :q
#   commands should probably execute silently even if there are unsaved buffers.
#   Sticking to Vim's behavior closely here makes for a worse experience
#   because typically you don't start ST as many times.
class ExQuitCommand(sublime_plugin.WindowCommand):
    """Ex command(s): :quit
    Closes the window.

        * Don't close the window if there are dirty buffers
          TODO:
          (Doesn't make too much sense if hot_exit is on, though.)
          Although ST's window command 'exit' would take care of this, it
          displays a modal dialog, so spare ourselves that.
    """
    def run(self, forced=False, count=1, flags=''):
        v = self.window.active_view()
        if forced:
            v.set_scratch(True)
        if v.is_dirty():
            sublime.status_message("There are unsaved changes!")
            return

        self.window.run_command('close')
        if len(self.window.views()) == 0:
            self.window.run_command('close')


class ExQuitAllCommand(sublime_plugin.WindowCommand):
    """Ex command(s): :qall
    Close all windows and then exit Sublime Text.

    If there are dirty buffers, exit only if :qall!.
    """
    def run(self, forced=False):
        if forced:
            for v in self.window.views():
                if v.is_dirty():
                    v.set_scratch(True)
        elif is_any_buffer_dirty(self.window):
            sublime.status_message("There are unsaved changes!")
            return

        self.window.run_command('close_all')
        self.window.run_command('exit')


class ExWriteAndQuitCommand(sublime_plugin.TextCommand):
    """Ex command(s): :wq

    Write and then close the active buffer.
    """
    def run(self, edit, line_range=None, forced=False):
        # TODO: implement this
        if forced:
            ex_error.handle_not_implemented()
            return
        if self.view.is_read_only():
            sublime.status_message("Can't write a read-only buffer.")
            return
        if not self.view.file_name():
            sublime.status_message("Can't save a file without name.")
            return

        self.view.run_command('save')
        self.view.window().run_command('ex_quit')


class ExBrowse(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().run_command('prompt_open_file')


class ExEdit(sublime_plugin.TextCommand):
    def run_(self, args):
        self.run(args)

    def run(self, forced=False):
        # todo: restore active line_nr too
        if forced or not self.view.is_dirty():
            self.view.run_command('revert')
            return
        elif self.view.is_dirty():
            ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)
            return

        ex_error.handle_not_implemented()


class ExCquit(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().run_command('exit')


class ExExit(sublime_plugin.TextCommand):
    """Ex command(s): :x[it], :exi[t]

    Like :wq, but write only when changes have been made.

    TODO: Support ranges, like :w.
    """
    def run(self, edit, line_range=None):
        w = self.view.window()

        if w.active_view().is_dirty():
            w.run_command('save')

        w.run_command('close')

        if len(w.views()) == 0:
            w.run_command('close')


class ExListRegisters(sublime_plugin.TextCommand):
    """Lists registers in quick panel and saves selected to `"` register."""

    def run(self, edit):
        if not g_registers:
            sublime.status_message('VintageEx: no registers.')
        self.view.window().show_quick_panel(
            ['"{0}   {1}'.format(k, v) for k, v in g_registers.items()],
            self.on_done)

    def on_done(self, idx):
        """Save selected value to `"` register."""
        if idx == -1:
            return
        g_registers['"'] = g_registers.values()[idx]


class ExNew(sublime_plugin.TextCommand):
    """Ex command(s): :new

    Create a new buffer.

    TODO: Create new buffer by splitting the screen.
    """
    def run(self, edit, line_range=None):
        self.view.window().run_command('new_file')


class ExYank(sublime_plugin.TextCommand):
    """Ex command(s): :y[ank]
    """

    def run(self, edit, line_range, register=None, count=None):
        if not register:
            register = '"'
        regs = get_region_by_range(self.view, line_range)
        text = '\n'.join([self.view.substr(line) for line in regs])
        g_registers[register] = text
        if register == '"':
            g_registers['0'] = text


class TabControlCommand(sublime_plugin.WindowCommand):
    def run(self, command, file_name=None, forced=False):
        window = self.window
        selfview = window.active_view()
        max_index = len(window.views())
        (group, index) = window.get_view_index(selfview)
        if (command == "open"):
            if file_name is None:  # TODO: file completion
                window.run_command("show_overlay", {"overlay": "goto", "show_files": True, })
            else:
                cur_dir = os.path.dirname(selfview.file_name())
                window.open_file(os.path.join(cur_dir, file_name))
        elif command == "next":
            window.run_command("select_by_index", {"index": (index + 1) % max_index}, )
        elif command == "prev":
            window.run_command("select_by_index", {"index": (index + max_index - 1) % max_index, })
        elif command == "last":
            window.run_command("select_by_index", {"index": max_index - 1, })
        elif command == "first":
            window.run_command("select_by_index", {"index": 0, })
        elif command == "only":
            for view in window.views_in_group(group):
                if view.id() != selfview.id():
                    window.focus_view(view)
                    window.run_command("ex_quit", {"forced": forced})
            window.focus_view(selfview)
        else:
            sublime.status_message("Unknown TabControl Command")


class ExTabOpenCommand(sublime_plugin.WindowCommand):
    def run(self, file_name=None):
        self.window.run_command("tab_control", {"command": "open", "file_name": file_name}, )


class ExTabNextCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "next"}, )


class ExTabPrevCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "prev"}, )


class ExTabLastCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "last"}, )


class ExTabFirstCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "first"}, )


class ExTabOnlyCommand(sublime_plugin.WindowCommand):
    def run(self, forced=False):
        self.window.run_command("tab_control", {"command": "only", "forced": forced, }, )

########NEW FILE########
__FILENAME__ = ex_search_cmd
# TODO(guillermooo): All of this functionality, along with key bindings, rather
# belongs in Vintage, but we need to extract the necessary functions out of
# VintageEx first. This is a temporary solution.

import sublime
import sublime_plugin

from vex import ex_location
import ex_commands


def compute_flags(view, term):
    flags = 0 # case sensitive
    search_mode = view.settings().get('vintage_search_mode')
    if search_mode == 'smart_case':
        if term.lower() == term:
            flags = sublime.IGNORECASE
    elif search_mode == 'case_insensitive':
        flags = sublime.IGNORECASE
    return flags


class SearchImpl(object):
    last_term = ""
    def __init__(self, view, cmd, remember=True, start_sel=None):
        self.start_sel = start_sel
        self.remember = remember
        if not cmd:
            return
        self.view = view
        self.reversed = cmd.startswith("?")
        if not cmd.startswith(("?", "/")):
            cmd = "/" + cmd
        if len(cmd) == 1 and SearchImpl.last_term:
            cmd += SearchImpl.last_term
        elif not cmd:
            return
        self.cmd = cmd[1:]
        self.flags = compute_flags(self.view, self.cmd)

    def search(self):
        if not getattr(self, "cmd", None):
            return
        if self.remember:
            SearchImpl.last_term = self.cmd
        sel = self.start_sel[0]

        next_match = None
        if self.reversed:
            current_line = self.view.line(self.view.sel()[0])
            left_side = sublime.Region(current_line.begin(),
                                       self.view.sel()[0].begin())
            if ex_location.search_in_range(self.view, self.cmd,
                                           left_side.begin(),
                                           left_side.end(),
                                           self.flags):
                next_match = ex_location.find_last_match(self.view,
                                                         self.cmd,
                                                         left_side.begin(),
                                                         left_side.end(),
                                                         self.flags)
            else:
                line_nr = ex_location.reverse_search(self.view, self.cmd,
                                                end=current_line.begin() - 1,
                                                flags=self.flags)
                if line_nr:
                    pt = self.view.text_point(line_nr - 1, 0)
                    line = self.view.full_line(pt)
                    if line.begin() != current_line.begin():
                        next_match = ex_location.find_last_match(self.view,
                                                             self.cmd,
                                                             line.begin(),
                                                             line.end(),
                                                             self.flags)
        else:
            next_match = self.view.find(self.cmd, sel.end(), self.flags)
        # handle search restart
        if not next_match:
            if self.reversed:
                sublime.status_message("VintageEx: search hit TOP, continuing at BOTTOM")
                line_nr = ex_location.reverse_search(self.view, self.cmd, flags=self.flags)
                if line_nr:
                    pt = self.view.text_point(line_nr - 1, 0)
                    line = self.view.full_line(pt)
                    next_match = ex_location.find_last_match(self.view,
                                                             self.cmd,
                                                             line.begin(),
                                                             line.end(),
                                                             self.flags)
            else:
                sublime.status_message("VintageEx: search hit BOTTOM, continuing at TOP")
                next_match = self.view.find(self.cmd, 0, sel.end())
        # handle result
        if next_match:
            self.view.sel().clear()
            if not self.remember:
                self.view.add_regions("vi_search", [next_match], "search.vi",
                                      sublime.DRAW_OUTLINED)
            else:
                self.view.sel().add(next_match)
            self.view.show(next_match)
        else:
            sublime.status_message("VintageEx: Pattern not found:" + self.cmd)


class ViRepeatSearchBackward(sublime_plugin.TextCommand):
   def run(self, edit):
        if ex_commands.VintageExState.search_buffer_type == 'pattern_search':
            SearchImpl(self.view, "?" + SearchImpl.last_term,
                      start_sel=self.view.sel()).search()
        elif ex_commands.VintageExState.search_buffer_type == 'find_under':
            self.view.window().run_command("find_prev", {"select_text": False})


class ViRepeatSearchForward(sublime_plugin.TextCommand):
    def run(self, edit):
        if ex_commands.VintageExState.search_buffer_type == 'pattern_search':
            SearchImpl(self.view, SearchImpl.last_term,
                       start_sel=self.view.sel()).search()
        elif ex_commands.VintageExState.search_buffer_type == 'find_under':
            self.view.window().run_command("find_next", {"select_text": False})


class ViFindUnder(sublime_plugin.TextCommand):
    def run(self, edit, forward=True):
        ex_commands.VintageExState.search_buffer_type = 'find_under'
        if forward:
            self.view.window().run_command('find_under', {'select_text': False})
        else:
            self.view.window().run_command('find_under_prev', {'select_text': False})


class ViSearch(sublime_plugin.TextCommand):
    def run(self, edit, initial_text=""):
        self.original_sel = list(self.view.sel())
        self.view.window().show_input_panel("", initial_text,
                                            self.on_done,
                                            self.on_change,
                                            self.on_cancel)

    def on_done(self, s):
        self._restore_sel()
        try:
            SearchImpl(self.view, s, start_sel=self.original_sel).search()
            ex_commands.VintageExState.search_buffer_type = 'pattern_search'
        except RuntimeError, e:
            if 'parsing' in str(e):
                print "VintageEx: Regex parsing error. Incomplete pattern: %s" % s
            else:
                raise e
        self.original_sel = None
        self._restore_sel()

    def on_change(self, s):
        if s in ("/", "?"):
            return
        self._restore_sel()
        try:
            SearchImpl(self.view, s, remember=False,
                       start_sel=self.original_sel).search()
        except RuntimeError, e:
            if 'parsing' in str(e):
                print "VintageEx: Regex parsing error. Expected error." 
            else:
                raise e

    def on_cancel(self):
        self._restore_sel()
        self.original_sel = None

    def _restore_sel(self):
        self.view.erase_regions("vi_search")
        if not self.original_sel:
            return
        self.view.sel().clear()
        for s in self.original_sel:
            self.view.sel().add(s)
        self.view.show(self.view.sel()[0])

########NEW FILE########
__FILENAME__ = linux
import os
import subprocess


def run_and_wait(view, cmd):
    term = view.settings().get('vintageex_linux_terminal')
    term = term or os.path.expandvars("$COLORTERM") or os.path.expandvars("$TERM")
    subprocess.Popen([
            term, '-e',
            "bash -c \"%s; read -p 'Press RETURN to exit.'\"" % cmd]).wait()


def filter_region(view, text, command):
    shell = view.settings().get('vintageex_linux_shell')
    shell = shell or os.path.expandvars("$SHELL")
    p = subprocess.Popen([shell, '-c', 'echo "%s" | %s' % (text, command)],
                         stdout=subprocess.PIPE)
    return p.communicate()[0][:-1]

########NEW FILE########
__FILENAME__ = osx
import os
import subprocess


def run_and_wait(view, cmd):
    term = view.settings().get('vintageex_osx_terminal')
    term = term or os.path.expandvars("$COLORTERM") or os.path.expandvars("$TERM")
    subprocess.Popen([
            term, '-e',
            "bash -c \"%s; read -p 'Press RETURN to exit.'\"" % cmd]).wait()


def filter_region(view, text, command):
    shell = view.settings().get('vintageex_osx_shell')
    shell = shell or os.path.expandvars("$SHELL")
    p = subprocess.Popen([shell, '-c', 'echo "%s" | %s' % (text, command)],
                         stdout=subprocess.PIPE)
    return p.communicate()[0][:-1]

########NEW FILE########
__FILENAME__ = windows
import subprocess
import os
import tempfile


try:
    import ctypes
except ImportError:
    import plat
    if plat.HOST_PLATFORM == plat.WINDOWS:
        raise EnvironmentError("ctypes module missing for Windows.")
    ctypes = None


def get_startup_info():
    # Hide the child process window.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def run_and_wait(view, cmd):
    subprocess.Popen(['cmd.exe', '/c', cmd + '&& pause']).wait()


def filter_region(view, txt, command):
    try:
        contents = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        contents.write(txt.encode('utf-8'))
        contents.close()

        script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
        script.write('@echo off\ntype %s | %s' % (contents.name, command))
        script.close()

        p = subprocess.Popen([script.name],
                             stdout=subprocess.PIPE,
                             startupinfo=get_startup_info())

        rv = p.communicate()
        return rv[0].decode(get_oem_cp()).replace('\r\n', '\n')[:-1].strip()
    finally:
        os.remove(script.name)
        os.remove(contents.name)


def get_oem_cp():
    codepage = ctypes.windll.kernel32.GetOEMCP()
    return str(codepage)

########NEW FILE########
__FILENAME__ = test_commands

########NEW FILE########
__FILENAME__ = test_global
import unittest

from vex.parsers.g_cmd import GlobalLexer


class TestGlobalLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = GlobalLexer()

    def testCanMatchFullPattern(self):
        actual = self.lexer.parse(r'/foo/p#')
        self.assertEqual(actual, ['foo', 'p#'])

    def testCanMatchEmtpySearch(self):
        actual = self.lexer.parse(r'//p#')
        self.assertEqual(actual, ['', 'p#'])

    def testCanEscapeCharactersInSearchPattern(self):
        actual = self.lexer.parse(r'/\/foo\//p#')
        self.assertEqual(actual, ['/foo/', 'p#'])

    def testCanEscapeBackSlashes(self):
        actual = self.lexer.parse(r'/\\/p#')
        self.assertEqual(actual, ['\\', 'p#'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_location
import sublime

import unittest

from test_runner import g_test_view
from tests import select_line

from ex_location import get_line_nr
from ex_location import find_eol
from ex_location import find_bol
from ex_location import find_line
from ex_location import search_in_range
from ex_location import find_last_match
from ex_location import reverse_search
from ex_range import calculate_relative_ref


class TestHelpers(unittest.TestCase):
    def testGetCorrectLineNumber(self):
        self.assertEquals(get_line_nr(g_test_view, 1000), 19)
    
    def testfind_bolAndEol(self):
        values = (
            (find_eol(g_test_view, 1000), 1062),
            (find_eol(g_test_view, 2000), 2052),
            (find_bol(g_test_view, 1000), 986),
            (find_bol(g_test_view, 2000), 1981),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)


class TestSearchHelpers(unittest.TestCase):
    def testForwardSearch(self):
        values = (
            (find_line(g_test_view, target=30), sublime.Region(1668, 1679)),
            (find_line(g_test_view, target=1000), -1),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)
    
    def testSearchInRange(self):
        values = (
            (search_in_range(g_test_view, 'THIRTY', 1300, 1800), True),
            (search_in_range(g_test_view, 'THIRTY', 100, 100), None),
            (search_in_range(g_test_view, 'THIRTY', 100, 1000), None),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)
        
    def testFindLastMatch(self):
        values = (
            (find_last_match(g_test_view, 'Lorem', 0, 1200), sublime.Region(913, 918)),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)
    
    def testReverseSearch(self):
        values = (
            (reverse_search(g_test_view, 'THIRTY'), 30),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)
    
    def testReverseSearchNonMatchesReturnCurrentLine(self):
        self.assertEquals(g_test_view.rowcol(g_test_view.sel()[0].a)[0], 0)
        values = (
            (reverse_search(g_test_view, 'FOOBAR'), 1),
        )

        select_line(g_test_view, 10)
        values += (
            (reverse_search(g_test_view, 'FOOBAR'), 10),
        )
        
        select_line(g_test_view, 100)
        values += (
            (reverse_search(g_test_view, 'FOOBAR'), 100),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    def testCalculateRelativeRef(self):
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 1)
        self.assertEquals(calculate_relative_ref(g_test_view, '$'), 538)

        select_line(g_test_view, 100)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 100)

        select_line(g_test_view, 200)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 200)

    def setUp(self):
        select_line(g_test_view, 1)
    
    def tearDown(self):
        select_line(g_test_view, 1)

########NEW FILE########
__FILENAME__ = test_range
import unittest
import re

from test_runner import g_test_view
from tests import select_bof
from tests import select_eof
from tests import select_line

from vex.ex_range import EX_RANGE
from vex.ex_range import new_calculate_range
from vex.ex_range import calculate_relative_ref
from vex.ex_range import calculate_address


class TestCalculateRelativeRef(unittest.TestCase):
    def StartUp(self):
        select_bof(g_test_view)

    def tearDown(self):
        select_bof(g_test_view)

    def testCalculateRelativeRef(self):
        values = (
            (calculate_relative_ref(g_test_view, '.'), 1),
            (calculate_relative_ref(g_test_view, '.', start_line=100), 101),
            (calculate_relative_ref(g_test_view, '$'), 538),
            (calculate_relative_ref(g_test_view, '$', start_line=100), 538),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    def testCalculateRelativeRef2(self):
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 1)
        self.assertEquals(calculate_relative_ref(g_test_view, '$'), 538)

        select_line(g_test_view, 100)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 100)

        select_line(g_test_view, 200)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 200)


class TestCalculatingRanges(unittest.TestCase):
    def testCalculateCorrectRange(self):
        values = (
            (new_calculate_range(g_test_view, '0'), [(0, 0)]),
            (new_calculate_range(g_test_view, '1'), [(1, 1)]),
            (new_calculate_range(g_test_view, '1,1'), [(1, 1)]),
            (new_calculate_range(g_test_view, '%,1'), [(1, 538)]),
            (new_calculate_range(g_test_view, '1,%'), [(1, 538)]),
            (new_calculate_range(g_test_view, '1+99,160-10'), [(100, 150)]),
            (new_calculate_range(g_test_view, '/THIRTY/+10,100'), [(40, 100)]),
        )

        select_line(g_test_view, 31)
        values += (
            (new_calculate_range(g_test_view, '10,/THIRTY/'), [(10, 31)]),
            (new_calculate_range(g_test_view, '10;/THIRTY/'), [(10, 30)]),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    def tearDown(self):
        select_bof(g_test_view)


class CalculateAddress(unittest.TestCase):
    def setUp(self):
        select_eof(g_test_view)

    def tearDown(self):
        select_bof(g_test_view)

    def testCalculateAddressCorrectly(self):
        values = (
            (dict(ref='100', offset=None, search_offsets=[]), 99),
            (dict(ref='200', offset=None, search_offsets=[]), 199),
        )

        for v, expected in values:
            self.assertEquals(calculate_address(g_test_view, v), expected)

    def testOutOfBoundsAddressShouldReturnNone(self):
        address = dict(ref='1000', offset=None, search_offsets=[])
        self.assertEquals(calculate_address(g_test_view, address), None)

    def testInvalidAddressShouldReturnNone(self):
        address = dict(ref='XXX', offset=None, search_offsets=[])
        self.assertRaises(AttributeError, calculate_address, g_test_view, address)

########NEW FILE########
__FILENAME__ = test_substitute
import unittest

from vex.parsers.s_cmd import SubstituteLexer
from vex.parsers.parsing import RegexToken
from vex.parsers.parsing import Lexer
from vex.parsers.parsing import EOF


class TestRegexToken(unittest.TestCase):
    def setUp(self):
        self.token = RegexToken("f[o]+")

    def testCanTestMembership(self):
        self.assertTrue("fo" in self.token)
        self.assertTrue("foo" in self.token)

    def testCanTestEquality(self):
        self.assertTrue("fo" == self.token)


class TestLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = Lexer()

    def testEmptyInputSetsCursorToEOF(self):
        self.lexer.parse('')
        self.assertEqual(self.lexer.c, EOF)

    def testDoesReset(self):
        c, cursor, string = self.lexer.c, self.lexer.cursor, self.lexer.string
        self.lexer.parse('')
        self.lexer._reset()
        self.assertEqual(c, self.lexer.c)
        self.assertEqual(cursor, self.lexer.cursor)
        self.assertEqual(string, self.lexer.string)

    def testCursorIsPrimed(self):
        self.lexer.parse("foo")
        self.assertEqual(self.lexer.c, 'f')

    def testCanConsume(self):
        self.lexer.parse("foo")
        self.lexer.consume()
        self.assertEqual(self.lexer.c, 'o')
        self.assertEqual(self.lexer.cursor, 1)

    def testCanReachEOF(self):
        self.lexer.parse("f")
        self.lexer.consume()
        self.assertEqual(self.lexer.c, EOF)

    def testPassingInJunk(self):
        self.assertRaises(TypeError, self.lexer.parse, 100)
        self.assertRaises(TypeError, self.lexer.parse, [])


class TestSubstituteLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = SubstituteLexer()

    def testCanParseEmptyInput(self):
        actual = self.lexer.parse('')

        self.assertEqual(actual, ['', ''])

    def testCanParseShortFormWithFlagsOnly(self):
        one_flag = self.lexer.parse(r'g')
        many_flags = self.lexer.parse(r'gi')

        self.assertEqual(one_flag, ['g', ''])
        self.assertEqual(many_flags, ['gi', ''])

    def testCanParseShortFormWithCountOnly(self):
        actual = self.lexer.parse(r'100')

        self.assertEqual(actual, ['', '100'])

    def testCanParseShortFormWithFlagsAndCount(self):
        actual_1 = self.lexer.parse(r'gi100')
        actual_2 = self.lexer.parse(r'  gi  100  ')

        self.assertEqual(actual_1, ['gi', '100'])
        self.assertEqual(actual_2, ['gi', '100'])

    def testThrowErrorIfCountIsFollowedByAnything(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"100gi")

    def testThrowErrorIfShortFormIsFollowedByAnythingOtherThanFlagsOrCount(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"x")

    def testCanParseOneSeparatorOnly(self):
        actual = self.lexer.parse(r"/")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseTwoSeparatorsOnly(self):
        actual = self.lexer.parse(r"//")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseThreeSeparatorsOnly(self):
        actual = self.lexer.parse(r"///")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseOnlySearchPattern(self):
        actual = self.lexer.parse(r"/foo")

        self.assertEqual(actual, ['foo', '', '', ''])

    def testCanParseOnlyReplacementString(self):
        actual = self.lexer.parse(r"//foo")

        self.assertEqual(actual, ['', 'foo', '', ''])

    def testCanParseOnlyFlags(self):
        actual = self.lexer.parse(r"///gi")

        self.assertEqual(actual, ['', '', 'gi', ''])

    def testCanParseOnlyCount(self):
        actual = self.lexer.parse(r"///100")

        self.assertEqual(actual, ['', '', '', '100'])

    def testCanParseOnlyFlagsAndCount(self):
        actual = self.lexer.parse(r"///gi100")

        self.assertEqual(actual, ['', '', 'gi', '100'])

    def testThrowIfFlagsAndCountAreReversed(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"///100gi")

    def testThrowIfFlagsAndCountAreInvalid(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"///x")

    def testCanEscapeDelimiter(self):
        actual = self.lexer.parse(r"/foo\/")

        self.assertEqual(actual, ['foo/', '', '', ''])

    def testCanEscapeDelimiterComplex(self):
        actual = self.lexer.parse(r"/foo\//hello")

        self.assertEqual(actual, ['foo/', 'hello', '', ''])

########NEW FILE########
__FILENAME__ = test_runner
import sublime
import sublime_plugin

import os
import unittest
import StringIO


TEST_DATA_FILE_BASENAME = 'vintageex_test_data.txt'
TEST_DATA_PATH = os.path.join(sublime.packages_path(),
                              'VintageEx/tests/data/%s' % TEST_DATA_FILE_BASENAME)


g_test_view = None
g_executing_test_suite = None

test_suites = {
        'parser': ['vintage_ex_run_simple_tests', 'vex.parsers.test_cmdline'],
        'range': ['vintage_ex_run_data_file_based_tests', 'tests.test_range'],
        'location': ['vintage_ex_run_data_file_based_tests', 'tests.test_location'],
        'substitute': ['vintage_ex_run_simple_tests', 'tests.test_substitute'],
        'global': ['vintage_ex_run_simple_tests', 'tests.test_global'],
}


def print_to_view(view, obtain_content):
    edit = view.begin_edit()
    view.insert(edit, 0, obtain_content())
    view.end_edit(edit)
    view.set_scratch(True)

    return view


class ShowVintageExTestSuites(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_quick_panel(sorted(test_suites.keys()), self.run_suite)

    def run_suite(self, idx):
        global g_executing_test_suite

        suite_name = sorted(test_suites.keys())[idx]
        g_executing_test_suite = suite_name
        command_to_run, _ = test_suites[suite_name]

        self.window.run_command(command_to_run, dict(suite_name=suite_name))


class VintageExRunSimpleTestsCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return os.getcwd() == os.path.join(sublime.packages_path(), 'VintageEx')

    def run(self, suite_name):
        bucket = StringIO.StringIO()
        _, suite = test_suites[suite_name]
        suite = unittest.defaultTestLoader.loadTestsFromName(suite)
        unittest.TextTestRunner(stream=bucket, verbosity=1).run(suite)

        print_to_view(self.window.new_file(), bucket.getvalue)


class VintageExRunDataFileBasedTests(sublime_plugin.WindowCommand):
    def run(self, suite_name):
        self.window.open_file(TEST_DATA_PATH)


class TestDataDispatcher(sublime_plugin.EventListener):
    def on_load(self, view):
        if view.file_name() and os.path.basename(view.file_name()) == TEST_DATA_FILE_BASENAME:
            global g_test_view
            g_test_view = view

            _, suite_name = test_suites[g_executing_test_suite]
            suite = unittest.TestLoader().loadTestsFromName(suite_name)

            bucket = StringIO.StringIO()
            unittest.TextTestRunner(stream=bucket, verbosity=1).run(suite)

            v = print_to_view(view.window().new_file(), bucket.getvalue)
            # In this order, or Sublime Text will fail.
            v.window().focus_view(view)
            view.window().run_command('close')

########NEW FILE########
__FILENAME__ = ex_command_parser
"""a simple 'parser' for :ex commands
"""

from collections import namedtuple
import re
from itertools import takewhile

from vex import ex_error
from vex import parsers


# Data used to parse strings into ex commands and map them to an actual
# Sublime Text command.
#
#   command
#       The Sublime Text command to be executed.
#   invocations
#       Tuple of regexes representing valid calls for this command.
#   error_on
#       Tuple of error codes. The parsed command is checked for errors based
#       on this information.
#       For example: on_error=(ex_error.ERR_TRAILING_CHARS,) would make the
#       command fail if it was followed by any arguments.
ex_cmd_data = namedtuple('ex_cmd_data', 'command invocations error_on')

# Holds a parsed ex command data.
# TODO: elaborate on params info.
EX_CMD = namedtuple('ex_command', 'name command forced args parse_errors line_range can_have_range')

# Address that can only appear after a command.
POSTFIX_ADDRESS = r'[.$]|(?:/.*?(?<!\\)/|\?.*?(?<!\\)\?){1,2}|[+-]?\d+|[\'][a-zA-Z0-9<>]'
ADDRESS_OFFSET = r'[-+]\d+'
# Can only appear standalone.
OPENENDED_SEARCH_ADDRESS = r'^[/?].*'

# ** IMPORTANT **
# Vim's documentation on valid addresses is wrong. For postfixed addresses,
# as in :copy10,20, only the left end is parsed and used; the rest is discarded
# and not even errors are thrown if the right end is bogus, like in :copy10XXX.
EX_POSTFIX_ADDRESS = re.compile(
                        r'''(?x)
                            ^(?P<address>
                                (?:
                                 # A postfix address...
                                 (?:%(address)s)
                                 # optionally followed by offsets...
                                 (?:%(offset)s)*
                                )|
                                # or an openended search-based address.
                                %(openended)s
                            )
                        ''' %  {'address':      POSTFIX_ADDRESS,
                                'offset':       ADDRESS_OFFSET,
                                'openended':    OPENENDED_SEARCH_ADDRESS}
                        )


EX_COMMANDS = {
    ('write', 'w'): ex_cmd_data(
                                command='ex_write_file',
                                invocations=(
                                    re.compile(r'^\s*$'),
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *(?P<operator>>>) *(?P<target_redirect>.+)?'),
                                    # fixme: raises an error when it shouldn't
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *!(?P<subcmd>.+)'),
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *(?P<file_name>.+)?'),
                                ),
                                error_on=()
                                ),
    ('wall', 'wa'): ex_cmd_data(
                                command='ex_write_all',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('pwd', 'pw'): ex_cmd_data(
                                command='ex_print_working_dir',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS)
                                ),
    ('buffers', 'buffers'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('files', 'files'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('ls', 'ls'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('registers', 'reg'): ex_cmd_data(
                                command='ex_list_registers',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('map', 'map'): ex_cmd_data(
                                command='ex_map',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('abbreviate', 'ab'): ex_cmd_data(
                                command='ex_abbreviate',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('quit', 'q'): ex_cmd_data(
                                command='ex_quit',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('qall', 'qa'): ex_cmd_data(
                                command='ex_quit_all',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    # TODO: add invocations
    ('wq', 'wq'): ex_cmd_data(
                                command='ex_write_and_quit',
                                invocations=(),
                                error_on=()
                                ),
    ('read', 'r'): ex_cmd_data(
                                command='ex_read_shell_out',
                                invocations=(
                                    # xxx: works more or less by chance. fix the command code
                                    re.compile(r'(?P<plusplus> *\+\+[a-zA-Z0-9_]+)* *(?P<name>.+)'),
                                    re.compile(r' *!(?P<name>.+)'),
                                ),
                                # fixme: add error category for ARGS_REQUIRED
                                error_on=()
                                ),
    ('enew', 'ene'): ex_cmd_data(
                                command='ex_new_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('ascii', 'as'): ex_cmd_data(
                                # This command is implemented in Packages/Vintage.
                                command='show_ascii_info',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS)
                                ),
    # vim help doesn't say this command takes any args, but it does
    ('file', 'f'): ex_cmd_data(
                                command='ex_file',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('move', 'move'): ex_cmd_data(
                                command='ex_move',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('copy', 'co'): ex_cmd_data(
                                command='ex_copy',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('t', 't'): ex_cmd_data(
                                command='ex_copy',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('substitute', 's'): ex_cmd_data(
                                command='ex_substitute',
                                invocations=(re.compile(r'(?P<pattern>.+)'),
                                ),
                                error_on=()
                                ),
    ('&&', '&&'): ex_cmd_data(
                                command='ex_double_ampersand',
                                # We don't want to mantain flag values here, so accept anything and
                                # let :substitute handle the values.
                                invocations=(re.compile(r'(?P<flags>.+?)\s*(?P<count>[0-9]+)'),
                                             re.compile(r'\s*(?P<flags>.+?)\s*'),
                                             re.compile(r'\s*(?P<count>[0-9]+)\s*'),
                                             re.compile(r'^$'),
                                ),
                                error_on=()
                                ),
    ('shell', 'sh'): ex_cmd_data(
                                command='ex_shell',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS)
                                ),
    ('delete', 'd'): ex_cmd_data(
                                command='ex_delete',
                                invocations=(
                                    re.compile(r' *(?P<register>[a-zA-Z0-9])? *(?P<count>\d+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('global', 'g'): ex_cmd_data(
                                command='ex_global',
                                invocations=(
                                    re.compile(r'(?P<pattern>.+)'),
                                ),
                                error_on=()
                                ),
    ('print', 'p'): ex_cmd_data(
                                command='ex_print',
                                invocations=(
                                    re.compile(r'\s*(?P<count>\d+)?\s*(?P<flags>[l#p]+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('Print', 'P'): ex_cmd_data(
                                command='ex_print',
                                invocations=(
                                    re.compile(r'\s*(?P<count>\d+)?\s*(?P<flags>[l#p]+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('browse', 'bro'): ex_cmd_data(
                                command='ex_browse',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS,)
                                ),
    ('edit', 'e'): ex_cmd_data(
                                command='ex_edit',
                                invocations=(re.compile(r"^$"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('cquit', 'cq'): ex_cmd_data(
                                command='ex_cquit',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    # TODO: implement all arguments, etc.
    ('xit', 'x'): ex_cmd_data(
                                command='ex_exit',
                                invocations=(),
                                error_on=()
                                ),
    # TODO: implement all arguments, etc.
    ('exit', 'exi'): ex_cmd_data(
                                command='ex_exit',
                                invocations=(),
                                error_on=()
                                ),
    ('only', 'on'): ex_cmd_data(
                                command='ex_only',
                                invocations=(re.compile(r'^$'),),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('new', 'new'): ex_cmd_data(
                                command='ex_new',
                                invocations=(re.compile(r'^$',),
                                ),
                                error_on=(ex_error.ERR_TRAILING_CHARS,)
                                ),
    ('yank', 'y'): ex_cmd_data(
                                command='ex_yank',
                                invocations=(re.compile(r'^(?P<register>\d|[a-z])$'),
                                             re.compile(r'^(?P<register>\d|[a-z]) (?P<count>\d+)$'),
                                ),
                                error_on=(),
                                ),
    (':', ':'): ex_cmd_data(
                        command='ex_goto',
                        invocations=(),
                        error_on=(),
                        ),
    ('!', '!'): ex_cmd_data(
                        command='ex_shell_out',
                        invocations=(
                                re.compile(r'(?P<shell_cmd>.+)$'),
                        ),
                        # FIXME: :!! is a different command to :!
                        error_on=(ex_error.ERR_NO_BANG_ALLOWED,),
                        ),
    ('tabedit', 'tabe'): ex_cmd_data(
                                    command='ex_tab_open',
                                    invocations=(
                                        re.compile(r'^(?P<file_name>.+)$'),
                                    ),
                                    error_on=(ex_error.ERR_NO_RANGE_ALLOWED,),
                                    ),
    ('tabnext', 'tabn'): ex_cmd_data(command='ex_tab_next',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabprev', 'tabp'): ex_cmd_data(command='ex_tab_prev',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabfirst', 'tabf'): ex_cmd_data(command='ex_tab_first',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tablast', 'tabl'): ex_cmd_data(command='ex_tab_last',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabonly', 'tabo'): ex_cmd_data(command='ex_tab_only',
                                     invocations=(),
                                     error_on=(
                                        ex_error.ERR_NO_RANGE_ALLOWED,
                                        ex_error.ERR_TRAILING_CHARS,)
                                     )
}


def find_command(cmd_name):
    partial_matches = [name for name in EX_COMMANDS.keys()
                                            if name[0].startswith(cmd_name)]
    if not partial_matches: return None
    full_match = [(ln, sh) for (ln, sh) in partial_matches
                                                if cmd_name in (ln, sh)]
    if full_match:
        return full_match[0]
    else:
        return partial_matches[0]


def parse_command(cmd):
    cmd_name = cmd.strip()
    if len(cmd_name) > 1:
        cmd_name = cmd_name[1:]
    elif not cmd_name == ':':
        return None

    parser = parsers.cmd_line.CommandLineParser(cmd[1:])
    r_ = parser.parse_cmd_line()

    command = r_['commands'][0]['cmd']
    bang = r_['commands'][0]['forced']
    args = r_['commands'][0]['args']
    cmd_data = find_command(command)
    if not cmd_data:
        return
    cmd_data = EX_COMMANDS[cmd_data]
    can_have_range = ex_error.ERR_NO_RANGE_ALLOWED not in cmd_data.error_on

    cmd_args = {}
    for pattern in cmd_data.invocations:
        found_args = pattern.search(args)
        if found_args:
            found_args = found_args.groupdict()
            # get rid of unset arguments so they don't clobber defaults
            found_args = dict((k, v) for k, v in found_args.iteritems()
                                                        if v is not None)
            cmd_args.update(found_args)
            break

    parse_errors = []
    for err in cmd_data.error_on:
        if err == ex_error.ERR_NO_BANG_ALLOWED and bang:
            parse_errors.append(ex_error.ERR_NO_BANG_ALLOWED)
        if err == ex_error.ERR_TRAILING_CHARS and args:
            parse_errors.append(ex_error.ERR_TRAILING_CHARS)
        if err == ex_error.ERR_NO_RANGE_ALLOWED and r_['range']['text_range']:
            parse_errors.append(ex_error.ERR_NO_RANGE_ALLOWED)
        if err == ex_error.ERR_INVALID_RANGE and not cmd_args:
            parse_errors.append(ex_error.ERR_INVALID_RANGE)
        if err == ex_error.ERR_ADDRESS_REQUIRED and not cmd_args:
            parse_errors.append(ex_error.ERR_ADDRESS_REQUIRED)

    return EX_CMD(name=command,
                    command=cmd_data.command,
                    forced=bang,
                    args=cmd_args,
                    parse_errors=parse_errors,
                    line_range=r_['range'],
                    can_have_range=can_have_range,)

########NEW FILE########
__FILENAME__ = ex_error
"""
This module lists error codes and error display messages along with
utilities to handle them.
"""

import sublime


ERR_UNKNOWN_COMMAND = 492 # Command can't take arguments.
ERR_TRAILING_CHARS = 488 # Unknown command.
ERR_NO_BANG_ALLOWED = 477 # Command doesn't allow !.
ERR_INVALID_RANGE = 16 # Invalid range.
ERR_INVALID_ADDRESS = 14 # Invalid range.
ERR_NO_RANGE_ALLOWED = 481 # Command can't take a range.
ERR_UNSAVED_CHANGES = 37 # The buffer has been modified but not saved.
ERR_ADDRESS_REQUIRED = 14 # Command needs an address.
ERR_OTHER_BUFFER_HAS_CHANGES = 445 # :only, for example, may trigger this
ERR_CANT_MOVE_LINES_ONTO_THEMSELVES = 134


ERR_MESSAGES = {
    ERR_TRAILING_CHARS: 'Traling characters.',
    ERR_UNKNOWN_COMMAND: 'Not an editor command.',
    ERR_NO_BANG_ALLOWED: 'No ! allowed.',
    ERR_INVALID_RANGE: 'Invalid range.',
    ERR_INVALID_ADDRESS: 'Invalid address.',
    ERR_NO_RANGE_ALLOWED: 'No range allowed.',
    ERR_UNSAVED_CHANGES: 'There are unsaved changes.',
    ERR_ADDRESS_REQUIRED: 'Invalid address.',
    ERR_OTHER_BUFFER_HAS_CHANGES: "Other buffer contains changes.",
    ERR_CANT_MOVE_LINES_ONTO_THEMSELVES: "Move lines into themselves."
}


def get_error_message(error_code):
    return ERR_MESSAGES.get(error_code, '')


def display_error(error_code, arg='', log=False):
    err_fmt = "VintageEx: E%d %s"
    if arg:
        err_fmt += " (%s)" % arg
    msg = get_error_message(error_code)
    sublime.status_message(err_fmt % (error_code, msg))


def handle_not_implemented():
    sublime.status_message('VintageEx: Not implemented')

########NEW FILE########
__FILENAME__ = ex_location
import sublime

from ex_range import calculate_relative_ref

def get_line_nr(view, point):
    """Return 1-based line number for `point`.
    """
    return view.rowcol(point)[0] + 1


# TODO: Move this to sublime_lib; make it accept a point or a region.
def find_eol(view, point):
    return view.line(point).end()


# TODO: Move this to sublime_lib; make it accept a point or a region.
def find_bol(view, point):
    return view.line(point).begin()


# TODO: make this return None for failures.
def find_line(view, start=0, end=-1, target=0):
    """Do binary search to find :target: line number.

    Return: If `target` is found, `Region` comprising entire line no. `target`.
            If `target`is not found, `-1`.
    """

    # Don't bother if sought line is beyond buffer boundaries.
    if  target < 0 or target > view.rowcol(view.size())[0] + 1:
        return -1

    if end == -1:
        end = view.size()

    lo, hi = start, end
    while lo <= hi:
        middle = lo + (hi - lo) / 2
        if get_line_nr(view, middle) < target:
            lo = find_eol(view, middle) + 1
        elif get_line_nr(view, middle) > target:
            hi = find_bol(view, middle) - 1
        else:
            return view.full_line(middle)
    return -1


def search_in_range(view, what, start, end, flags=0):
    match = view.find(what, start, flags)
    if match and ((match.begin() >= start) and (match.end() <= end)):
        return True


def find_last_match(view, what, start, end, flags=0):
    """Find last occurrence of `what` between `start`, `end`.
    """
    match = view.find(what, start, flags)
    new_match = None
    while match:
        new_match = view.find(what, match.end(), flags)
        if new_match and new_match.end() <= end:
            match = new_match
        else:
            return match


def reverse_search(view, what, start=0, end=-1, flags=0):
    """Do binary search to find `what` walking backwards in the buffer.
    """
    if end == -1:
        end = view.size()
    end = find_eol(view, view.line(end).a)
    
    last_match = None

    lo, hi = start, end
    while True:
        middle = (lo + hi) / 2    
        line = view.line(middle)
        middle, eol = find_bol(view, line.a), find_eol(view, line.a)

        if search_in_range(view, what, middle, hi, flags):
            lo = middle
        elif search_in_range(view, what, lo, middle - 1, flags):
            hi = middle -1
        else:
            return calculate_relative_ref(view, '.')

        # Don't search forever the same line.
        if last_match and line.contains(last_match):
            match = find_last_match(view, what, lo, hi, flags=flags)
            return view.rowcol(match.begin())[0] + 1
        
        last_match = sublime.Region(line.begin(), line.end())    


def search(view, what, start_line=None, flags=0):
    # TODO: don't make start_line default to the first sel's begin(). It's
    # confusing. ???
    if start_line:
        start = view.text_point(start_line, 0)
    else:
        start = view.sel()[0].begin()
    reg = view.find(what, start, flags)
    if not reg is None:
        row = (view.rowcol(reg.begin())[0] + 1)
    else:
        row = calculate_relative_ref(view, '.', start_line=start_line)
    return row

########NEW FILE########
__FILENAME__ = ex_range
"""helpers to manage :ex mode ranges
"""

from collections import namedtuple
import sublime


class VimRange(object):
    """Encapsulates calculation of view regions based on supplied raw range info.
    """
    def __init__(self, view, range_info, default=None):
        self.view = view
        self.default = default
        self.range_info = range_info

    def blocks(self):
        """Returns a list of blocks potentially encompassing multiple lines.
        Returned blocks don't end in a newline char.
        """
        regions, visual_regions = new_calculate_range(self.view, self.range_info)
        blocks = []
        for a, b in regions:
            r = sublime.Region(self.view.text_point(a - 1, 0),
                               self.view.line(self.view.text_point(b - 1, 0)).end())
            if self.view.substr(r)[-1] == "\n":
                if r.begin() != r.end():
                    r = sublime.Region(r.begin(), r.end() - 1)
            blocks.append(r)
        return blocks

    def lines(self):
        """Return a list of lines.
        Returned lines don't end in a newline char.
        """
        lines = []
        for block in self.blocks():
            lines.extend(self.view.split_by_newlines(block))
        return lines


EX_RANGE = namedtuple('ex_range', 'left left_offset separator right right_offset')


def calculate_relative_ref(view, where, start_line=None):
    if where == '$':
        return view.rowcol(view.size())[0] + 1
    if where == '.':
        if start_line:
            return view.rowcol(view.text_point(start_line, 0))[0] + 1
        return view.rowcol(view.sel()[0].begin())[0] + 1


def new_calculate_search_offsets(view, searches, start_line):
    last_line = start_line
    for search in searches:
        if search[0] == '/':
            last_line = ex_location.search(view, search[1], start_line=last_line)
        elif search[0] == '?':
            end = view.line(view.text_point(start_line, 0)).end()
            last_line = ex_location.reverse_search(view, search[1], end=end)
        last_line += search[2]
    return last_line


def calculate_address(view, a):
    fake_range = dict(left_ref=a['ref'],
                      left_offset=a['offset'],
                      left_search_offsets=a['search_offsets'],
                      sep=None,
                      right_ref=None,
                      right_offset=None,
                      right_search_offsets=[]
                      # todo: 'text_range' key missing
                    )

    a, _ =  new_calculate_range(view, fake_range)[0][0] or -1
    # FIXME: 0 should be a valid address?
    if not (0 < a <= view.rowcol(view.size())[0] + 1):
        return None
    return a - 1


def new_calculate_range(view, r):
    """Calculates line-based ranges (begin_row, end_row) and returns
    a tuple: a list of ranges and a boolean indicating whether the ranges
    where calculated based on a visual selection.
    """

    # FIXME: make sure this works with whitespace between markers, and doublecheck
    # with Vim to see whether '<;>' is allowed.
    # '<,>' returns all selected line blocks
    if r['left_ref'] == "'<" and r['right_ref'] == "'>":
        all_line_blocks = []
        for sel in view.sel():
            start = view.rowcol(sel.begin())[0] + 1
            end = view.rowcol(sel.end())[0] + 1
            if view.substr(sel.end() - 1) == '\n':
                end -= 1
            all_line_blocks.append((start, end))
        return all_line_blocks, True
        
    # todo: '< and other marks
    if r['left_ref'] and (r['left_ref'].startswith("'") or (r['right_ref'] and r['right_ref'].startswith("'"))):
        return []

    # todo: don't mess up with the received ranged. Also, % has some strange
    # behaviors that should be easy to replicate.
    if r['left_ref'] == '%' or r['right_ref'] == '%':
        r['left_offset'] = 1
        r['right_ref'] = '$'

    current_line = None
    lr = r['left_ref']
    if lr is not None:
        current_line = calculate_relative_ref(view, lr) 
    loffset = r['left_offset']
    if loffset:
        current_line = current_line or 0
        current_line += loffset

    searches = r['left_search_offsets']
    if searches:
        current_line = new_calculate_search_offsets(view, searches, current_line or calculate_relative_ref(view, '.'))
    left = current_line

    current_line = None
    rr = r['right_ref']
    if rr is not None:
        current_line = calculate_relative_ref(view, rr) 
    roffset = r['right_offset']
    if roffset:
        current_line = current_line or 0
        current_line += roffset

    searches = r['right_search_offsets']
    if searches:
        current_line = new_calculate_search_offsets(view, searches, current_line or calculate_relative_ref(view, '.'))
    right = current_line

    if not right:
        right = left

    # todo: move this to the parsing phase? Do all vim commands default to '.' as a range?
    if not any([left, right]):
        left = right = calculate_relative_ref(view, '.')

    # todo: reverse range automatically if needed
    return [(left, right)], False

# Avoid circular import.
from vex import ex_location

########NEW FILE########
__FILENAME__ = cmd_line
import re

EOF = -1

COMMA = ','
SEMICOLON = ';'
LINE_REF_SEPARATORS = (COMMA, SEMICOLON)

default_range_info = dict(left_ref=None,
                          left_offset=None,
                          left_search_offsets=[],
                          separator=None,
                          right_ref=None,
                          right_offset=None,
                          right_search_offsets=[],
                          text_range='')


class ParserBase(object):
    def __init__(self, source):
        self.c = ''
        self.source = source
        self.result = default_range_info.copy()
        self.n = -1
        self.consume()

    def consume(self):
        if self.c == EOF:
            raise SyntaxError("End of file reached.")
        if self.n == -1 and not self.source:
            self.c = EOF
            return
        else:
            self.n += 1
            if self.n >= len(self.source):
                self.c = EOF
                return
            self.c = self.source[self.n]


class VimParser(ParserBase):
    STATE_NEUTRAL = 0
    STATE_SEARCH_OFFSET = 1

    def __init__(self, *args, **kwargs):
        self.state = VimParser.STATE_NEUTRAL
        self.current_side = 'left'
        ParserBase.__init__(self, *args, **kwargs)

    def parse_full_range(self):
        # todo: make sure that parse_range throws error for unknown tokens
        self.parse_range()
        sep = self.match_one(',;')
        if sep:
            if not self.result[self.current_side + '_offset'] and not self.result[self.current_side + '_ref']:
                self.result[self.current_side + '_ref'] = '.'
            self.consume()
            self.result['separator'] = sep
            self.current_side = 'right'
            self.parse_range()

        if self.c != EOF and not (self.c.isalpha() or self.c in '&!'):
            raise SyntaxError("E492 Not an editor command.")

        return self.result

    def parse_range(self):
        if self.c == EOF:
            return self.result
        line_ref = self.consume_if_in(list('.%$'))
        if line_ref:
            self.result[self.current_side + "_ref"] = line_ref
        while self.c != EOF:
            if self.c == "'":
                self.consume()
                if self.c != EOF and not (self.c.isalpha() or self.c in ("<", ">")):
                    raise SyntaxError("E492 Not an editor command.")
                self.result[self.current_side + "_ref"] = "'%s" % self.c
                self.consume()
            elif self.c in ".$%%'" and not self.result[self.current_side + "_ref"]:
                if (self.result[self.current_side + "_search_offsets"] or
                    self.result[self.current_side + "_offset"]):
                        raise SyntaxError("E492 Not an editor command.")
            elif self.c.startswith(tuple("01234567890+-")):
                offset = self.match_offset()
                self.result[self.current_side + '_offset'] = offset
            elif self.c.startswith(tuple('/?')):
                self.state = VimParser.STATE_SEARCH_OFFSET
                search_offests = self.match_search_based_offsets()
                self.result[self.current_side + "_search_offsets"] = search_offests
                self.state = VimParser.STATE_NEUTRAL
            elif self.c not in ':,;&!' and not self.c.isalpha():
                raise SyntaxError("E492 Not an editor command.")
            else:
                break

            if (self.result[self.current_side + "_ref"] == '%' and
                (self.result[self.current_side + "_offset"] or
                 self.result[self.current_side + "_search_offsets"])):
                    raise SyntaxError("E492 Not an editor command.")

        end = max(0, min(self.n, len(self.source)))
        self.result['text_range'] = self.source[:end]
        return self.result

    def consume_if_in(self, items):
        rv = None
        if self.c in items:
            rv = self.c
            self.consume()
        return rv

    def match_search_based_offsets(self):
        offsets = []
        while self.c != EOF and self.c.startswith(tuple('/?')):
            new_offset = []
            new_offset.append(self.c)
            search = self.match_one_search_offset()
            new_offset.append(search)
            # numeric_offset = self.consume_while_match('^[0-9+-]') or '0'
            numeric_offset = self.match_offset()
            new_offset.append(numeric_offset)
            offsets.append(new_offset)
        return offsets

    def match_one_search_offset(self):
        search_kind = self.c
        rv = ''
        self.consume()
        while self.c != EOF and self.c != search_kind:
            if self.c == '\\':
                self.consume()
                if self.c != EOF:
                    rv += self.c
                    self.consume()
            else:
                rv += self.c
                self.consume()
        if self.c == search_kind:
            self.consume()
        return rv

    def match_offset(self):
        offsets = []
        sign = 1
        is_num_or_sign = re.compile('^[0-9+-]')
        while self.c != EOF and is_num_or_sign.match(self.c):
            if self.c in '+-':
                signs = self.consume_while_match('^[+-]')
                if self.state == VimParser.STATE_NEUTRAL and len(signs) > 1 and not self.result[self.current_side + '_ref']:
                    self.result[self.current_side + '_ref'] = '.'
                if self.c != EOF and self.c.isdigit():
                    if self.state == VimParser.STATE_NEUTRAL and not self.result[self.current_side + '_ref']:
                        self.result[self.current_side + '_ref'] = '.'
                    sign = -1 if signs[-1] == '-' else 1
                    signs = signs[:-1] if signs else []
                subtotal = 0
                for item in signs:
                    subtotal += 1 if item == '+' else -1 
                offsets.append(subtotal)
            elif self.c.isdigit():
                nr = self.consume_while_match('^[0-9]')
                offsets.append(sign * int(nr))
                sign = 1
            else:
                break

        return sum(offsets)
        # self.result[self.current_side + '_offset'] = sum(offsets)

    def match_one(self, seq):
        if self.c != EOF and self.c in seq:
            return self.c


    def consume_while_match(self, regex):
        rv = ''
        r = re.compile(regex)
        while self.c != EOF and r.match(self.c):
            rv += self.c
            self.consume()
        return rv


class CommandLineParser(ParserBase):
    def __init__(self, source, *args, **kwargs):
        ParserBase.__init__(self, source, *args, **kwargs)     
        self.range_parser = VimParser(source)
        self.result = dict(range=None, commands=[], errors=[])

    def parse_cmd_line(self):
        try:
            rng = self.range_parser.parse_full_range()
        except SyntaxError, e:
            rng = None
            self.result["errors"].append(str(e))
            return self.result

        self.result['range'] = rng
        # sync up with range parser the dumb way
        self.n = self.range_parser.n
        self.c = self.range_parser.c
        while self.c != EOF and self.c == ' ':
            self.consume()
        self.parse_commands()

        if not self.result['commands'][0]['cmd']:
            self.result['commands'][0]['cmd'] = ':'
        return self.result

    def parse_commands(self):
        name = ''
        cmd = {}
        while self.c != EOF:
            if self.c.isalpha() and '&' not in name:
                name += self.c
                self.consume()
            elif self.c == '&' and (not name or name == '&'):
                name += self.c
                self.consume()
            else:
                break

        if not name and self.c  == '!':
            name = '!'
            self.consume()

        cmd['cmd'] = name
        cmd['forced'] = self.c == '!'
        if cmd['forced']:
            self.consume()

        while self.c != EOF and self.c == ' ':
            self.consume()
        cmd['args'] = ''
        if not self.c == EOF:
            cmd['args'] = self.source[self.n:]
        self.result['commands'].append(cmd)


class AddressParser(ParserBase):
    STATE_NEUTRAL = 1
    STATE_SEARCH_OFFSET = 2

    def __init__(self, source, *args, **kwargs):
        ParserBase.__init__(self, source, *args, **kwargs)
        self.result = dict(ref=None, offset=None, search_offsets=[])
        self.state = AddressParser.STATE_NEUTRAL

    def parse(self):
        if self.c == EOF:
            return self.result
        ref = self.consume_if_in(list('.$'))
        if ref:
            self.result["ref"] = ref

        while self.c != EOF:
            if self.c in '0123456789+-':
                rv = self.match_offset()
                self.result['offset'] = rv
            elif self.c in '?/':
                rv = self.match_search_based_offsets()
                self.result['search_offsets'] = rv

        return self.result

    def match_search_based_offsets(self):
        offsets = []
        while self.c != EOF and self.c.startswith(tuple('/?')):
            new_offset = []
            new_offset.append(self.c)
            search = self.match_one_search_offset()
            new_offset.append(search)
            # numeric_offset = self.consume_while_match('^[0-9+-]') or '0'
            numeric_offset = self.match_offset()
            new_offset.append(numeric_offset)
            offsets.append(new_offset)
        return offsets

    def match_one_search_offset(self):
        search_kind = self.c
        rv = ''
        self.consume()
        while self.c != EOF and self.c != search_kind:
            if self.c == '\\':
                self.consume()
                if self.c != EOF:
                    rv += self.c
                    self.consume()
            else:
                rv += self.c
                self.consume()
        if self.c == search_kind:
            self.consume()
        return rv

    def match_offset(self):
        offsets = []
        sign = 1
        is_num_or_sign = re.compile('^[0-9+-]')
        while self.c != EOF and is_num_or_sign.match(self.c):
            if self.c in '+-':
                signs = self.consume_while_match('^[+-]')
                if self.state == AddressParser.STATE_NEUTRAL and len(signs) > 0 and not self.result['ref']:
                    self.result['ref'] = '.'
                if self.c != EOF and self.c.isdigit():
                    sign = -1 if signs[-1] == '-' else 1
                    signs = signs[:-1] if signs else []
                subtotal = 0
                for item in signs:
                    subtotal += 1 if item == '+' else -1 
                offsets.append(subtotal)
            elif self.c.isdigit():
                nr = self.consume_while_match('^[0-9]')
                offsets.append(sign * int(nr))
                sign = 1
            else:
                break

        return sum(offsets)

    def match_one(self, seq):
        if self.c != EOF and self.c in seq:
            return self.c


    def consume_while_match(self, regex):
        rv = ''
        r = re.compile(regex)
        while self.c != EOF and r.match(self.c):
            rv += self.c
            self.consume()
        return rv

    def consume_if_in(self, items):
        rv = None
        if self.c in items:
            rv = self.c
            self.consume()
        return rv

########NEW FILE########
__FILENAME__ = g_cmd
from vex.parsers.parsing import RegexToken
from vex.parsers.parsing import Lexer
from vex.parsers.parsing import EOF


class GlobalLexer(Lexer):
    DELIMITER = RegexToken(r'[^a-zA-Z0-9 ]')
    WHITE_SPACE = ' \t'

    def __init__(self):
        self.delimiter = None

    def _match_white_space(self):
        while self.c != EOF and self.c in self.WHITE_SPACE:
            self.consume()

    def _match_pattern(self):
        buf = []
        while self.c != EOF and self.c != self.delimiter:
            if self.c == '\\':
                buf.append(self.c)
                self.consume()
                if self.c in '\\':
                    # Don't store anything, we're escaping \.
                    self.consume()
                elif self.c == self.delimiter:
                    # Overwrite the \ we've just stored.
                    buf[-1] = self.delimiter
                    self.consume()

                if self.c == EOF:
                    break
            else:
                buf.append(self.c)
                self.consume()

        return ''.join(buf)

    def _parse_long(self):
        buf = []

        self.delimiter = self.c
        self.consume()

        buf.append(self._match_pattern())

        self.consume()
        buf.append(self.string[self.cursor:])

        return buf

    def _do_parse(self):
        if not self.c in self.DELIMITER:
            raise SyntaxError("expected delimiter, got '%s'" % self.c)
        return self._parse_long()


def split(s):
    return GlobalLexer().parse(s)

########NEW FILE########
__FILENAME__ = parsing
import re

EOF = -1

class Lexer(object):
    def __init__(self):
        self.c = None # current character
        self.cursor = 0
        self.string = None

    def _reset(self):
        self.c = None
        self.cursor = 0
        self.string = None

    def consume(self):
        self.cursor += 1
        if self.cursor >= len(self.string):
            self.c = EOF
        else:
            self.c = self.string[self.cursor]

    def _do_parse(self):
        pass

    def parse(self, string):
        if not isinstance(string, basestring):
            raise TypeError("Can only parse strings.")
        self._reset()
        self.string = string
        if not string:
            self.c = EOF
        else:
            self.c = string[0]
        return self._do_parse()


class RegexToken(object):
    def __init__(self, value):
        self.regex = re.compile(value)

    def __contains__(self, value):
        return self.__eq__(value)

    def __eq__(self, other):
        return bool(self.regex.match(other))

########NEW FILE########
__FILENAME__ = s_cmd
from vex.parsers.parsing import RegexToken
from vex.parsers.parsing import Lexer
from vex.parsers.parsing import EOF


class SubstituteLexer(Lexer):
    DELIMITER = RegexToken(r'[^a-zA-Z0-9 ]')
    WHITE_SPACE = ' \t'
    FLAG = 'giI'

    def __init__(self):
        self.delimiter = None

    def _match_white_space(self):
        while self.c != EOF and self.c in self.WHITE_SPACE:
            self.consume()

    def _match_count(self):
        buf = []
        while self.c != EOF and self.c.isdigit():
            buf.append(self.c)
            self.consume()
        return ''.join(buf)

    def _match_flags(self):
        buf = []
        while self.c != EOF and self.c in self.FLAG:
            if self.c in self.FLAG:
                buf.append(self.c)
            self.consume()
        return ''.join(buf)

    def _match_pattern(self):
        buf = []
        while self.c != EOF and self.c != self.delimiter:
            if self.c == '\\':
                buf.append(self.c)
                self.consume()
                if self.c == self.delimiter:
                    # Overwrite the \ we've just stored.
                    buf[-1] = self.delimiter
                    self.consume()
                if self.c in '\\':
                    buf.append(self.c) # BUGFIXED: still need to escape \ in python regex!
                    self.consume()

                if self.c == EOF:
                    break
            else:
                buf.append(self.c)
                self.consume()

        return ''.join(buf)

    def _parse_short(self):
        buf = []
        if self.c == EOF:
            return ['', ''] # no flags, no count

        if self.c.isalpha():
            buf.append(self._match_flags())
            self._match_white_space()
        else:
            buf.append('')

        if self.c != EOF and self.c.isdigit():
            buf.append(self._match_count())
            self._match_white_space()
        else:
            buf.append('')

        if self.c != EOF:
            raise SyntaxError("Trailing characters.")

        return buf

    def _parse_long(self):
        buf = []

        self.delimiter = self.c
        self.consume()

        if self.c == EOF:
            return ['', '', '', '']

        buf.append(self._match_pattern())

        if self.c != EOF:
            # We're at a separator now --we MUST be.
            self.consume()
            buf.append(self._match_pattern())
        else:
            buf.append('')

        if self.c != EOF:
            self.consume()

        if self.c != EOF and self.c in self.FLAG:
            buf.append(self._match_flags())
        else:
            buf.append('')

        if self.c != EOF:
            self._match_white_space()
            buf.append(self._match_count())
        else:
            buf.append('')

        self._match_white_space()
        if self.c != EOF:
            raise SyntaxError("Trailing characters.")

        return buf

    def _do_parse(self):
        self._match_white_space()
        if self.c != EOF and self.c in self.DELIMITER:
            return self._parse_long()
        else:
            return self._parse_short()


def split(s):
    return SubstituteLexer().parse(s)

########NEW FILE########
__FILENAME__ = test_cmdline
import unittest
from vex.parsers import cmd_line


class ParserBase(unittest.TestCase):
    def setUp(self):
        self.parser = cmd_line.ParserBase("foo")

    def testIsInitCorrect(self):
        self.assertEqual(self.parser.source, "foo")
        self.assertEqual(self.parser.c, "f")

    def testCanConsume(self):
        rv = []
        while self.parser.c != cmd_line.EOF:
            rv.append(self.parser.c)
            self.parser.consume()
        self.assertEqual(rv, list("foo"))

    def testCanConsumeEmpty(self):
        parser = cmd_line.ParserBase('')
        self.assertEqual(parser.c, cmd_line.EOF)


class VimParser(unittest.TestCase):
    def testCanParseEmptyInput(self):
        parser = cmd_line.VimParser('')
        rv = parser.parse_range()
        self.assertEqual(rv, cmd_line.default_range_info)

    def testCanMatchMinusSignOffset(self):
        parser = cmd_line.VimParser('-')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = -1
        expected['text_range'] = '-'
        self.assertEqual(rv, expected)

    def testCanMatchPlusSignOffset(self):
        parser = cmd_line.VimParser('+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 1
        expected['text_range'] = '+'
        self.assertEqual(rv, expected)

    def testCanMatchMultiplePlusSignsOffset(self):
        parser = cmd_line.VimParser('++')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 2
        expected['text_range'] = '++'
        self.assertEqual(rv, expected)

    def testCanMatchMultipleMinusSignsOffset(self):
        parser = cmd_line.VimParser('--')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -2
        expected['text_range'] = '--'
        self.assertEqual(rv, expected)

    def testCanMatchPositiveIntegerOffset(self):
        parser = cmd_line.VimParser('+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.' 
        expected['left_offset'] = 100 
        expected['text_range'] = "+100"
        self.assertEqual(rv, expected)

    def testCanMatchMultipleSignsAndPositiveIntegetOffset(self):
        parser = cmd_line.VimParser('++99')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100 
        expected['text_range'] = '++99'
        self.assertEqual(rv, expected)

    def testCanMatchMultipleSignsAndNegativeIntegerOffset(self):
        parser = cmd_line.VimParser('--99')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -100 
        expected['text_range'] = '--99'
        self.assertEqual(rv, expected)

    def testCanMatchPlusSignBeforeNegativeInteger(self):
        parser = cmd_line.VimParser('+-101')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -100 
        expected['text_range'] = '+-101'
        self.assertEqual(rv, expected)

    def testCanMatchPostFixMinusSign(self):
        parser = cmd_line.VimParser('101-')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['text_range'] = '101-'
        self.assertEqual(rv, expected)

    def testCanMatchPostfixPlusSign(self):
        parser = cmd_line.VimParser('99+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['text_range'] = '99+'
        self.assertEqual(rv, expected)

    def testCanMatchCurrentLineSymbol(self):
        parser = cmd_line.VimParser('.')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['text_range'] = '.'
        self.assertEqual(rv, expected)

    def testCanMatchLastLineSymbol(self):
        parser = cmd_line.VimParser('$')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['text_range'] = '$'
        self.assertEqual(rv, expected)

    def testCanMatchWholeBufferSymbol(self):
        parser = cmd_line.VimParser('%')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['text_range'] = '%'
        self.assertEqual(rv, expected)

    def testCanMatchMarkRef(self):
        parser = cmd_line.VimParser("'a")
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = "'a"
        expected['text_range'] = "'a"
        self.assertEqual(rv, expected)

    def testCanMatchUppsercaseMarkRef(self):
        parser = cmd_line.VimParser("'A")
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = "'A"
        expected['text_range'] = "'A"
        self.assertEqual(rv, expected)

    def testMarkRefsMustBeAlpha(self):
        parser = cmd_line.VimParser("'0")
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePostfixOffsets(self):
        parser = cmd_line.VimParser('%100')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100.')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100$')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCanHavePostfixNoSignIntegerOffsets(self):
        parser = cmd_line.VimParser('$100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 100
        expected['text_range'] = '$100'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSignedIntegerOffsets(self):
        parser = cmd_line.VimParser('$+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 100
        expected['text_range'] = '$+100'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSignOffsets(self):
        parser = cmd_line.VimParser('$+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 1
        expected['text_range'] = '$+'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixNoSignIntegerOffsets(self):
        parser = cmd_line.VimParser('.100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = '.100'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixSignedIntegerOffsets(self):
        parser = cmd_line.VimParser('.+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = '.+100'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixSignOffsets(self):
        parser = cmd_line.VimParser('.+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 1
        expected['text_range'] = '.+'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 0]]
        expected['text_range'] = '/foo/'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsets(self):
        parser = cmd_line.VimParser('?foo?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', 0]]
        expected['text_range'] = '?foo?'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsetsWithPostfixOffset(self):
        parser = cmd_line.VimParser('?foo?100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', 100]]
        expected['text_range'] = '?foo?100'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsetsWithSignedIntegerOffset(self):
        parser = cmd_line.VimParser('?foo?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', -100]]
        expected['text_range'] = '?foo?-100'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsetsWithPostfixOffset(self):
        parser = cmd_line.VimParser('/foo/100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 100]]
        expected['text_range'] = '/foo/100'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsetsWithSignedIntegerOffset(self):
        parser = cmd_line.VimParser('/foo/-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', -100]]
        expected['text_range'] = '/foo/-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeForwardSlash(self):
        parser = cmd_line.VimParser('/foo\/-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo/-100', 0]]
        expected['text_range'] = '/foo\/-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeQuestionMark(self):
        parser = cmd_line.VimParser('?foo\?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo?-100', 0]]
        expected['text_range'] = '?foo\?-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeBackSlash(self):
        parser = cmd_line.VimParser('/foo\\\\?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo\\?-100', 0]]
        expected['text_range'] = '/foo\\\\?-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsEscapeAnyUnknownEscapeSequence(self):
        parser = cmd_line.VimParser('/foo\\h')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'fooh', 0]]
        expected['text_range'] = '/foo\\h'
        self.assertEqual(rv, expected)

    def testCanHaveMultipleSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo//bar/?baz?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 0],
                                           ['/', 'bar', 0],
                                           ['?', 'baz', 0],
                                          ]
        expected['text_range'] = '/foo//bar/?baz?'
        self.assertEqual(rv, expected)

    def testCanHaveMultipleSearchBasedOffsetsWithInterspersedNumericOffets(self):
        parser = cmd_line.VimParser('/foo/100/bar/+100--+++?baz?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 100],
                                           ['/', 'bar', 101],
                                           ['?', 'baz', 0],
                                          ]
        expected['text_range'] = '/foo/100/bar/+100--+++?baz?'
        self.assertEqual(rv, expected)

    def testWholeBufferSymbolCannotHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('%/foo/')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/.')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/$')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCanHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('./foo/+10')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_search_offsets'] = [['/', 'foo', 10]]
        expected['text_range'] = './foo/+10'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('$?foo?+10')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_search_offsets'] = [['?', 'foo', 10]]
        expected['text_range'] = '$?foo?+10'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHaveMultiplePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('$?foo?+10/bar/100/baz/')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_search_offsets'] = [['?', 'foo', 10],
                                           ['/', 'bar', 100],
                                           ['/', 'baz', 0],
                                          ]
        expected['text_range'] = '$?foo?+10/bar/100/baz/'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegers(self):
        parser = cmd_line.VimParser('100,100')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['separator'] = ','
        expected['right_offset'] = 100
        expected['text_range'] = '100,100'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersWithOffsets(self):
        parser = cmd_line.VimParser('+100++--+;++100-')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 101
        expected['separator'] = ';'
        expected['right_ref'] = '.'
        expected['right_offset'] = 100
        expected['text_range'] = '+100++--+;++100-'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_1(self):
        parser = cmd_line.VimParser('%,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        expected['text_range'] = '%,%'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_2(self):
        parser = cmd_line.VimParser('.,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_2(self):
        parser = cmd_line.VimParser('%,.')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '.'
        expected['text_range'] = '%,.'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_3(self):
        parser = cmd_line.VimParser('$,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        expected['text_range'] = '$,%'
        self.assertEqual(rv, expected)
        
    def testCanMatchFullRangeOfIntegersSymbols_4(self):
        parser = cmd_line.VimParser('%,$')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '$'
        expected['text_range'] = '%,$'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_5(self):
        parser = cmd_line.VimParser('$,.')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['separator'] = ','
        expected['right_ref'] = '.'
        expected['text_range'] = '$,.'
        self.assertEqual(rv, expected)
        
    def testCanMatchFullRangeOfIntegersSymbols_6(self):
        parser = cmd_line.VimParser('.,$')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['separator'] = ','
        expected['right_ref'] = '$'
        expected['text_range'] = '.,$'
        self.assertEqual(rv, expected)

    def testFullRangeCanMatchCommandOnly(self):
        parser = cmd_line.VimParser('foo')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        self.assertEqual(rv, expected)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_1(self):
        parser = cmd_line.VimParser('100.,%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_2(self):
        parser = cmd_line.VimParser('%,100$')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_3(self):
        parser = cmd_line.VimParser('%,100.')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_4(self):
        parser = cmd_line.VimParser('100%,.')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testComplexFullRange(self):
        parser = cmd_line.VimParser(".++9/foo\\bar/100?baz?--;'b-100?buzz\\\\\\??+10")
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 10
        expected['left_search_offsets'] = [['/', 'foobar', 100], ['?', 'baz', -2]]
        expected['separator'] = ';'
        expected['right_ref'] = "'b"
        expected['right_offset'] = -100
        expected['right_search_offsets'] = [['?', 'buzz\\?', 10]]
        expected['text_range'] = ".++9/foo\\bar/100?baz?--;'b-100?buzz\\\\\\??+10"
        self.assertEqual(rv, expected)

    def testFullRangeMustEndInAlpha(self):
        parser = cmd_line.VimParser('100%,.(')
        self.assertRaises(SyntaxError, parser.parse_full_range)


class TestCaseCommandLineParser(unittest.TestCase):
    def testCanParseCommandOnly(self):
        parser = cmd_line.CommandLineParser('foo')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"", "forced": False}],
                errors=[]
            )
        self.assertEqual(rv, expected)

    def testCanParseWithErrors(self):
        parser = cmd_line.CommandLineParser('10$foo')
        rv = parser.parse_cmd_line()
        expected = dict(
                range=None,
                commands=[],
                errors=['E492 Not an editor command.']
            )
        self.assertEqual(rv, expected)

    def testCanParseCommandWithArgs(self):
        parser = cmd_line.CommandLineParser('foo! bar 100')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"bar 100", "forced": True}],
                errors=[]
            )
        self.assertEqual(rv, expected)
        
    def testCanParseCommandWithArgsAndRange(self):
        parser = cmd_line.CommandLineParser('100foo! bar 100')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected_range['left_offset'] = 100
        expected_range['text_range'] = '100'
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"bar 100", "forced": True}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseDoubleAmpersandCommand(self):
        parser = cmd_line.CommandLineParser('&&')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"&&", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseAmpersandCommand(self):
        parser = cmd_line.CommandLineParser('&')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"&", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseBangCommand(self):
        parser = cmd_line.CommandLineParser('!')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"!", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseBangCommandWithRange(self):
        parser = cmd_line.CommandLineParser('.!')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected_range['text_range'] = '.'
        expected_range['left_ref'] = '.'
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"!", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)


class TestAddressParser(unittest.TestCase):
    def testCanParseSymbolAddress_1(self):
        parser = cmd_line.AddressParser('.')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': None}
        self.assertEqual(rv, expected)

    def testCanParseSymbolAddress_2(self):
        parser = cmd_line.AddressParser('$')
        rv = parser.parse()
        expected = {'ref': '$', 'search_offsets': [], 'offset': None}
        self.assertEqual(rv, expected)

    def testCanParseOffsetOnItsOwn(self):
        parser = cmd_line.AddressParser('100')
        rv = parser.parse()
        expected = {'ref': None, 'search_offsets': [], 'offset': 100}
        self.assertEqual(rv, expected)

    def testCanParseSignsOnTheirOwn(self):
        parser = cmd_line.AddressParser('++')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 2}
        self.assertEqual(rv, expected)

    def testCanParseSignAndNumber(self):
        parser = cmd_line.AddressParser('+1')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 1}
        self.assertEqual(rv, expected)

    def testCanParseSymbolAndOffset(self):
        parser = cmd_line.AddressParser('.+1')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 1}
        self.assertEqual(rv, expected)

    def testCanParseSearchOffset(self):
        parser = cmd_line.AddressParser('/foo bar')
        rv = parser.parse()
        expected = {'ref': None, 'search_offsets': [['/', 'foo bar', 0]], 'offset': None}
        self.assertEqual(rv, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = shell
import plat
import plat.linux
import plat.osx
import plat.windows


def run_and_wait(view, cmd):
    if plat.HOST_PLATFORM == plat.WINDOWS:
        plat.windows.run_and_wait(view, cmd)
    elif plat.HOST_PLATFORM == plat.LINUX:
        plat.linux.run_and_wait(view, cmd)
    elif plat.HOST_PLATFORM == plat.OSX:
        plat.osx.run_and_wait(view, cmd)
    else:
        raise NotImplementedError


def filter_thru_shell(view, regions, cmd):
    try:
        # XXX: make this a ShellFilter class instead
        edit = view.begin_edit()
        if plat.HOST_PLATFORM == plat.WINDOWS:
            filter_func = plat.windows.filter_region
        elif plat.HOST_PLATFORM == plat.LINUX:
            filter_func = plat.linux.filter_region
        elif plat.HOST_PLATFORM == plat.OSX:
            filter_func = plat.osx.filter_region
        else:
            raise NotImplementedError

        for r in reversed(regions):
            rv = filter_func(view, view.substr(r), cmd)
            view.replace(edit, r, rv)
    finally:
        view.end_edit(edit)

########NEW FILE########
__FILENAME__ = vintage_ex
import sublime
import sublime_plugin

from vex.ex_command_parser import parse_command
from vex.ex_command_parser import EX_COMMANDS
from vex import ex_error


COMPLETIONS = sorted([x[0] for x in EX_COMMANDS.keys()])

EX_HISTORY_MAX_LENGTH = 20
EX_HISTORY = {
    'cmdline': [],
    'searches': []
}


def update_command_line_history(item, slot_name):
    if len(EX_HISTORY[slot_name]) >= EX_HISTORY_MAX_LENGTH:
        EX_HISTORY[slot_name] = EX_HISTORY[slot_name][1:]
    if item in EX_HISTORY[slot_name]:
        EX_HISTORY[slot_name].pop(EX_HISTORY[slot_name].index(item))
    EX_HISTORY[slot_name].append(item)


class ViColonInput(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return len(self.window.views()) > 0

    def __init__(self, window):
        sublime_plugin.WindowCommand.__init__(self, window)

    def run(self, initial_text=':', cmd_line=''):
        # non-interactive call
        if cmd_line:
            self.non_interactive = True
            self.on_done(cmd_line)
            return
        v = self.window.show_input_panel('', initial_text,
                                                    self.on_done, None, None)
        v.set_syntax_file('Packages/VintageEx/Support/VintageEx Cmdline.tmLanguage')
        v.settings().set('gutter', False)
        v.settings().set('rulers', [])

    def on_done(self, cmd_line):
        if not getattr(self, 'non_interactive', None):
            update_command_line_history(cmd_line, 'cmdline')
        else:
            self.non_interactive = False
        ex_cmd = parse_command(cmd_line)
        print ex_cmd

        if ex_cmd and ex_cmd.parse_errors:
            ex_error.display_error(ex_cmd.parse_errors[0])
            return
        if ex_cmd and ex_cmd.name:
            if ex_cmd.can_have_range:
                ex_cmd.args["line_range"] = ex_cmd.line_range
            if ex_cmd.forced:
                ex_cmd.args['forced'] = ex_cmd.forced
            self.window.run_command(ex_cmd.command, ex_cmd.args)
        else:
            ex_error.display_error(ex_error.ERR_UNKNOWN_COMMAND, cmd_line)


class ViColonRepeatLast(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return (len(self.window.views()) > 0) and (len(EX_HISTORY['cmdline']) > 0)

    def run(self):
        self.window.run_command('vi_colon_input', {'cmd_line': EX_HISTORY['cmdline'][-1]})


class ExCompletionsProvider(sublime_plugin.EventListener):
    CACHED_COMPLETIONS = []
    CACHED_COMPLETION_PREFIXES = []

    def on_query_completions(self, view, prefix, locations):
        if view.score_selector(0, 'text.excmdline') == 0:
            return []

        if len(prefix) + 1 != view.size():
            return []

        if prefix and prefix in self.CACHED_COMPLETION_PREFIXES:
            return self.CACHED_COMPLETIONS

        compls = [x for x in COMPLETIONS if x.startswith(prefix)]
        self.CACHED_COMPLETION_PREFIXES = [prefix] + compls
        self.CACHED_COMPLETIONS = zip([prefix] + compls, compls + [prefix])
        return self.CACHED_COMPLETIONS


class CycleCmdlineHistory(sublime_plugin.TextCommand):
    HISTORY_INDEX = None
    def run(self, edit, backwards=False):
        if CycleCmdlineHistory.HISTORY_INDEX is None:
            CycleCmdlineHistory.HISTORY_INDEX = -1 if backwards else 0
        else:
            CycleCmdlineHistory.HISTORY_INDEX += -1 if backwards else 1

        if CycleCmdlineHistory.HISTORY_INDEX == len(EX_HISTORY['cmdline']) or \
            CycleCmdlineHistory.HISTORY_INDEX < -len(EX_HISTORY['cmdline']):
                CycleCmdlineHistory.HISTORY_INDEX = -1 if backwards else 0

        self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, \
                EX_HISTORY['cmdline'][CycleCmdlineHistory.HISTORY_INDEX])


class HistoryIndexRestorer(sublime_plugin.EventListener):
    def on_deactivated(self, view):
        # Because views load asynchronously, do not restore history index
        # .on_activated(), but here instead. Otherwise, the .score_selector()
        # call won't yield the desired results.
        if view.score_selector(0, 'text.excmdline') > 0:
            CycleCmdlineHistory.HISTORY_INDEX = None

########NEW FILE########
