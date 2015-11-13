__FILENAME__ = cli
#!/usr/bin/env python

"""
Pure Python alternative to readline and cmm.Cmd.

Author: Jonathan Slenders
"""

import logging
import os
import termcolor
import termios
import time
import traceback

from twisted.internet import fdesc
from deployer.pseudo_terminal import select
from deployer.std import raw_mode
from deployer.console import Console

from pygments import highlight
from pygments.lexers import PythonTracebackLexer
from pygments.formatters import TerminalFormatter


def commonprefix(*strings):
    # Similar to os.path.commonprefix
    if not strings:
        return ''

    else:
        s1 = min(strings)
        s2 = max(strings)

        for i, c in enumerate(s1):
            if c != s2[i]:
                return s1[:i]

        return s1


class ExitCLILoop(Exception):
    def __init__(self, result=None):
        self.result = result


class CLInterface(object):
    """
    A pure-python implementation of a command line completion interface.
    It does not rely on readline or raw_input, which don't offer
    autocompletion in Python 2.6/2.7 when different ptys are used in different
    threads.
    """
    not_found_message = 'Command not found...'
    not_a_leaf_message = 'Incomplete command...'

    @property
    def prompt(self):
        return [ ('>', 'cyan') ]

    def __init__(self, pty, rootHandler):
        self.pty = pty
        self.stdin = pty.stdin
        self.stdout = pty.stdout
        self.root = rootHandler
        self.lines_history = []
        self.history_position = 0 # 0 is behind the history, -1 is browsing one backwards

        self.tcattr = termios.tcgetattr(self.stdin.fileno())
        self.line = [] # Character array
        self.insert_pos = 0
        self.scroll_pos = 0 # Horizontal scrolling
        self.vi_navigation = False # In vi-navigation mode (instead of insert mode.)

        # Additional pipe through which this shell can receive messages while
        # waiting for IO.
        r, w = os.pipe()
        self._extra_stdout = os.fdopen(w, 'w', 0)
        self._extra_stdin = os.fdopen(r, 'r', 0)
        fdesc.setNonBlocking(self._extra_stdin)

        self.currently_running = None

    def __del__(self):
        self._extra_stdout.close()
        self._extra_stdin.close()

    def write(self, data):
        self._extra_stdout.write(data)

    def completer(self, parts, lastPart):
        """
        Return a list of (name, handler)
        matching the last completion part.
        """
        h = self.root
        parts = parts[:]

        while h and parts:# and not h.is_leaf:
            try:
                h = h.get_subhandler(parts[0])
                parts = parts[1:]
            except NoSubHandler, e:
                return []

        if h and not parts:
            return list(h.complete_subhandlers(lastPart))
        else:
            return []

    def handle(self, parts):
        original_parts = parts
        h = self.root
        parts = parts[:]

        logging.info('Handle command line action "%s"' % ' '.join(parts))

        while h and parts:# and not h.is_leaf:
            try:
                h = h.get_subhandler(parts[0])
            except (NotImplementedError, NoSubHandler):
                print 'Not implemented...'
                return

            parts = parts[1:]

        if h and not parts:
            if h.is_leaf:
                self.currently_running = ' '.join(original_parts)
                try:
                    h()
                except ExitCLILoop:
                    raise
                except Exception as e:
                    self.handle_exception(e)
                self.currently_running = None
            else:
                print self.not_a_leaf_message
        else:
            print self.not_found_message

    def handle_exception(self, e):
        """
        Default exception handler when something went wrong in the shell.
        """
        tb = traceback.format_exc()
        print highlight(tb, PythonTracebackLexer(), TerminalFormatter())
        print e

    def complete(self, return_all_completions=False):
        # Take part before cursor
        l = ''.join(self.line)[:self.insert_pos]

        # Split parts
        parts = [ p for p in l.split() if p ] or [ '' ]

        # When there's a space below the cursor, it means that we are
        # at the start of a new part.
        if self.insert_pos > 0 and self.line[self.insert_pos - 1].isspace():
            parts.append('')

        possible_completions = self.completer(parts[:-1], parts[-1])

        if return_all_completions:
            return possible_completions
        else:
            last_part_len = len(parts[-1])
            possible_completions = [ c[0] for c in possible_completions ]
            if len(possible_completions) == 1:
                # When exactly one match, append a space
                return possible_completions[0][last_part_len:] + ' '
            else:
                return commonprefix(*possible_completions)[last_part_len:]

    def print_all_completions(self, all_completions):
        self.stdout.write('\r\n')

        # Create an iterator which yields all the comments (in their color),
        # and pass it through in_columns/lesspipe
        def column_items():
            for w in all_completions:
                handler_type = w[1].handler_type
                text = '%s%s' % (
                    termcolor.colored(w[0], handler_type.color),
                    termcolor.colored(handler_type.postfix, handler_type.postfix_color))
                length = len(w[0]) + len(handler_type.postfix)
                yield text, length

        c = Console(self.pty)
        c.lesspipe(c.in_columns(column_items()))

    def ctrl_c(self):
        # Initialize new read
        self.line = []
        self.insert_pos = 0
        self.history_position = 0
        self.vi_navigation = False

        # Print promt again
        self.stdout.write('\r\n')
        self.print_command()


    def print_command(self, only_if_scrolled=False):
        """
        Print the whole command line prompt.
        """
        termwidth = self.pty.get_width()
        prompt_out, prompt_length = self._make_prompt(termwidth)

        changed = self._update_scroll(prompt_length)
        if changed or not only_if_scrolled:
            self._print_command(prompt_out, prompt_length, termwidth)

    def _make_prompt(self, termwidth):
        """
        Create a (outbuffer, promptsize) object.
        """
        out = []
        pos = 0

        # Call prompt property
        prompt = self.prompt

        # Max prompt size
        max_prompt_size = termwidth / 2

        # Loop backwards over all the parts, truncate when required.
        while prompt and pos < max_prompt_size:
            text, color = prompt.pop()

            if len(text) > max_prompt_size - pos:
                text = text[-(max_prompt_size-pos):]

            out = [ termcolor.colored(text, color) ] + out
            pos += len(text)

        return out, pos

    def _update_scroll(self, prompt_length):
        """
        Update scroll, to make sure that the cursor is always visible.
        """
        changed = False

        # Make sure that the cursor is within range.
        # (minus one, because we need to have an insert prompt available after the input text.)
        available_width = self.pty.get_width() - prompt_length - 1

        # Make sure that the insert position is visible
        if self.insert_pos > available_width + self.scroll_pos:
            self.scroll_pos = self.insert_pos - available_width
            changed = True

        if self.insert_pos < self.scroll_pos:
            self.scroll_pos = self.insert_pos
            changed = True

        # Make sure that the scrolling pos is never larger than it has to be.
        # e.g. after enlarging the window size.
        if self.scroll_pos > len(self.line) - available_width:
            self.scroll_pos = max(0, len(self.line) - available_width)

        return changed

    def _print_command(self, prompt_out, prompt_length, termwidth):
        """
        Reprint prompt.
        """
        # We have an unbufferred stdout, so it's faster to write only once.
        out = [ ]

        # Move cursor position to the left.
        out.append('\x1b[%iD' % termwidth)

        # Erace until the end of line
        out.append('\x1b[K')

        # Add prompt
        pos = prompt_length
        out += prompt_out

        # Horizontal scrolling
        scroll_pos = self.scroll_pos

        # Print interactive part of command line
        line = ''.join(self.line)
        h = self.root

        while line:
            if line[0].isspace():
                overflow = pos+1 > termwidth
                if overflow:
                    break
                else:
                    if scroll_pos:
                        scroll_pos -= 1
                    else:
                        out.append(line[0])
                        pos += 1

                line = line[1:]
            else:
                # First following part
                p = line.split()[0]
                line = line[len(p):]

                # Get color
                color = None
                if h:
                    try:
                        h = h.get_subhandler(p)
                        if h:
                            color = h.handler_type.color
                    except (NotImplementedError, NoSubHandler):
                        pass

                while scroll_pos and p:
                    scroll_pos -= 1
                    p = p[1:]

                # Trim when the line's too long.
                overflow = pos + len(p) > termwidth
                if overflow:
                    p = p[:termwidth-pos]

                # Print this slice in the correct color.
                out.append(termcolor.colored(p, color))
                pos += len(p)

                if overflow:
                    break

        # Move cursor to correct position
        out.append('\x1b[%iD' % termwidth) # Move 'x' positions backwards (to the start of the line)
        out.append('\x1b[%iC' % (prompt_length + self.insert_pos - self.scroll_pos)) # Move back to right

        # Flush buffer
        self.stdout.write(''.join(out))
        self.stdout.flush()

    def clear(self):
        # Erase screen and move cursor to 0,0
        self.stdout.write('\033[2J\033[0;0H')
        self.print_command()

    def backspace(self):
        if self.insert_pos > 0:
            self.line = self.line[:self.insert_pos-1] + self.line[self.insert_pos:]
            self.insert_pos -= 1

            self.print_command()
        else:
            self.stdout.write('\a') # Beep

    def cursor_left(self):
        if self.insert_pos > 0:
            self.insert_pos -= 1
            self.stdout.write('\x1b[D') # Move to left

            self.print_command(True)

    def cursor_right(self):
        if self.insert_pos < len(self.line):
            self.insert_pos += 1
            self.stdout.write('\x1b[C') # Move to right

            self.print_command(True)

    def word_forwards(self):
        found_space = False
        while self.insert_pos < len(self.line) - 1:
            self.insert_pos += 1
            self.stdout.write('\x1b[C') # Move to right

            if self.line[self.insert_pos].isspace():
                found_space = True
            elif found_space:
                return

        self.print_command(True)

    def word_backwards(self):
        found_non_space = False
        while self.insert_pos > 0:
            self.insert_pos -= 1
            self.stdout.write('\x1b[D') # Move to left

            if not self.line[self.insert_pos].isspace():
                found_non_space = True
            if found_non_space and self.insert_pos > 0 and self.line[self.insert_pos-1].isspace():
                return

        self.print_command(True)

    def delete(self):
        if self.insert_pos < len(self.line):
            self.line = self.line[:self.insert_pos] + self.line[self.insert_pos+1:]
            self.print_command()

    def delete_until_end(self):
        self.line = self.line[:self.insert_pos]
        self.print_command()

    def delete_word(self):
        found_space = False
        while self.insert_pos < len(self.line) - 1:
            self.line = self.line[:self.insert_pos] + self.line[self.insert_pos+1:]

            if self.line[self.insert_pos].isspace():
                found_space = True
            elif found_space:
                break

        self.print_command()

    def history_back(self):
        if self.history_position > -len(self.lines_history):
            self.history_position -= 1
            self.line = list(self.lines_history[self.history_position])

        self.insert_pos = len(self.line)
        self.print_command()

    def history_forward(self):
        if self.history_position < -1:
            self.history_position += 1
            self.line = list(self.lines_history[self.history_position])

        elif self.history_position == -1:
            # New line
            self.history_position = 0
            self.line = []

        self.insert_pos = len(self.line)
        self.print_command()

    def home(self):
        self.insert_pos = 0
        self.print_command()

    def end(self):
        self.insert_pos = len(self.line)
        self.print_command()

    def cmdloop(self):
        try:
            while True:
                # Set handler for resize terminal events.
                self.pty.set_ssh_channel_size = lambda: self.print_command()

                # Read command
                with raw_mode(self.stdin):
                    result = self.read().strip()

                self.pty.set_ssh_channel_size = None

                # Handle result
                if result:
                    self.lines_history.append(result)
                    self.history_position = 0

                    self.handle([ p for p in result.split(' ') if p ])

        except ExitCLILoop, e:
            print # Print newline
            return e.result

    def exit(self):
        """
        Exit cmd loop.
        """
        raise ExitCLILoop

    def read(self):
        """
        Blocking call which reads in command line input
        Not thread safe
        """
        # Initialize new read
        self.line = []
        self.insert_pos = 0
        self.print_command()

        # Timings
        last_up = time.time()
        last_down = time.time()

        # Interaction loop
        last_char = None
        c = ''
        while True:
            last_char = c

            r, w, e = select([self._extra_stdin, self.stdin], [], [])

            # Receive stream from monitor
            if self._extra_stdin in r:
                self.stdout.write('\r') # Move cursor to the left
                self.stdout.write('\x1b[K') # Erase until the end of line
                self.stdout.write(self._extra_stdin.read(4096))
                self.stdout.write('\r\n')

                # Clear line
                self.print_command()

            if self.stdin in r:
                c = self.stdin.read(1)

                # self.stdout.write(' %i ' % ord(c))
                # self.stdout.flush()
                # continue

                # Contrel-A
                if c == '\x01':
                    self.home()

                # Control-B
                elif c == '\x02':
                    self.cursor_left()

                # Control-C
                elif c == '\x03':
                    self.ctrl_c()

                # Control-D
                elif c == '\x04':
                    self.exit()

                # Contrel-E
                elif c == '\x05':
                    self.end()

                # Control-F
                elif c == '\x06':
                    self.cursor_right()

                # Control-K
                elif c == '\x0b':
                    self.delete_until_end()

                # Control-L
                elif c == '\x0c':
                    self.clear()

                # Control-N
                elif c == '\x0e': # 14
                    self.history_forward()

                # Control-P
                elif c == '\x10': # 16
                    self.history_back()

                # Control-R
                elif c == '\x12': # 18
                    self.stdout.write('\r\nSorry, reverse search is not supported.\r\n')
                    self.print_command()

                # Enter
                elif c in ('\r', '\n'): # Depending on the client \n or \r is sent.
                    # Restore terminal
                    self.stdout.write('\r\n')
                    self.stdout.flush()

                    # Return result
                    return ''.join(self.line)

                # Tab completion
                elif c == '\t':
                    # Double tab press: print all completions and show new prompt.
                    if last_char == '\t':
                        all_completions = self.complete(True)
                        if all_completions:
                            self.print_all_completions(all_completions)
                            self.print_command()

                    else:
                        # Call tab completion
                        append = self.complete()
                        self.line = self.line[:self.insert_pos]

                        for a in append:
                            self.line.append(a)
                            self.insert_pos += 1
                        self.print_command()

                # Backspace
                elif c == '\x7f': # (127) Backspace
                    self.backspace()

                # Escape characters for cursor movement
                elif c == '\x1b': # (27) Escape

                    # When no other characters are followed immediately after the
                    # escape character, we consider it an ESC key press
                    if not select( [self.stdin], [], [], 0)[0]:
                        self.vi_navigation = True
                        c = ''
                    else:
                        c = self.stdin.read(1)

                    if c in ('[', 'O'): # (91, 68)
                        c = self.stdin.read(1)

                        # Cursor to left
                        if c == 'D':
                            self.cursor_left()

                        # Cursor to right
                        elif c == 'C':
                            self.cursor_right()

                        # Cursor up:
                        elif c == 'A':
                            if time.time() - last_up > 0.01:
                                self.history_back()
                            last_up = time.time()

                            # NOTE: When the scrolling events occur too fast,
                            # we'll skip them, because mouse scrolling can generate
                            # multiple up or down events, and we need only
                            # one.

                        # Cursor down:
                        elif c == 'B':
                            if time.time() - last_down > 0.01:
                                self.history_forward()
                            last_down = time.time()

                        # Delete key: esc[3~
                        elif c == '3':
                            c = self.stdin.read(1)

                            if c == '~':
                                self.delete()

                        # xrvt sends esc[7~ for home
                        # some others send esc[1~ (tmux)
                        elif c in ('1', '7'):
                            c = self.stdin.read(1)

                            if c == '~':
                                self.home()

                        # xrvt sends esc[8~ for end
                        # some others send esc[4~ (tmux)
                        elif c in ('4', '8'):
                            c = self.stdin.read(1)

                            if c == '~':
                                self.end()

                        # Home (xterm)
                        if c == 'H':
                            self.home()

                        # End (xterm)
                        elif c == 'F':
                            self.end()

                # Insert character
                else:
                    if self.vi_navigation:
                        if c == 'h': # Move left
                            self.cursor_left()
                        elif c == 'l': # Move right
                            self.cursor_right()
                        elif c == 'I': # Home
                            self.vi_navigation = False
                            self.home()
                        elif c == 'x': # Delete
                            self.delete()
                        elif c == 'A': # Home
                            self.vi_navigation = False
                            self.end()
                        elif c == 'i': # Back to insert mode
                            self.vi_navigation = False
                        elif c == 'a': # Back to insert mode
                            self.vi_navigation = False
                            self.cursor_right()
                        elif c == 'w': # Move word forward
                            self.word_forwards()
                        elif c == 'b': # Move word backwards
                            self.word_backwards()
                        elif c == 'D': # Delete until end
                            self.delete_until_end()
                        elif c == 'd': # Delete
                            c = self.stdin.read(1)
                            if c == 'w': # Delete word
                                self.delete_word()

                    # Only printable characters (space to tilde, or 32..126)
                    elif c >= ' ' and c <= '~':
                        # Note: correct handling of UTF-8 input, can be done
                        # by using the codecs.getreader, but it's complex to
                        # get it working right with the ANSI terminal escape
                        # codes, and buffering, and we don't really need it
                        # anyway.
                        #   # stdin_utf8 = codecs.getreader('utf-8')(sys.stdin)

                        if self.insert_pos < len(self.line):
                            self.line = self.line[:self.insert_pos] + [c] + self.line[self.insert_pos:]
                        else:
                            self.line.append(c)
                        self.insert_pos += 1
                        self.print_command()

                self.stdout.flush()


class HandlerType(object):
    """
    Command line handlers can be given several types.
    This makes it for example possible to the prompt
    another color during execution of a dangerous command.
    """
    color = None

    # A little one character postfix to distinguish between handler types.
    postfix = ''
    postfix_color = None


class NoSubHandler(Exception):
    pass


class Handler(object):
    is_leaf = False
    handler_type = HandlerType()

    def __call__(self):
        raise NotImplementedError

    def complete_subhandlers(self, part):
        """
        Return (name, Handler) subhandler pairs.
        """
        return []

    def get_subhandler(self, name):
        raise NoSubHandler

########NEW FILE########
__FILENAME__ = client
"""Usage:
  client.py run [-s | --single-threaded | --socket SOCKET] [--path PATH]
                  [--non-interactive] [--log LOGFILE] [--scp]
                  [--] [ACTION PARAMETER...]
  client.py listen [--log LOGFILE] [--non-interactive] [--socket SOCKET]
  client.py connect (--socket SOCKET) [--path PATH] [--scp]
                  [--] [ACTION PARAMETER...]
  client.py telnet-server [--port PORT] [--log LOGFILE] [--non-interactive]
  client.py list-sessions
  client.py scp
  client.py -h | --help
  client.py --version

Options:
  -h, --help             : Display this help text.
  -s, --single-threaded  : Single threaded mode.
  --path PATH            : Start the shell at the node with this location.
  --scp                  : Open a secure copy shell.
  --non-interactive      : If possible, run script with as few interactions as
                           possible.  This will always choose the default
                           options when asked for questions.
  --log LOGFILE          : Write logging info to this file. (For debugging.)
  --socket SOCKET        : The path of the unix socket.
  --version              : Show version information.
"""

from deployer import __version__
from deployer.run.socket_client import list_sessions
from deployer.run.socket_client import start as start_client
from deployer.run.socket_server import start as start_server
from deployer.run.standalone_shell import start as start_standalone
from deployer.run.telnet_server import start as start_telnet_server

import docopt
import getpass
import os
import sys


def start(root_node, name=sys.argv[0], extra_loggers=None):
    """
    Client startup point.
    """
    a = docopt.docopt(__doc__.replace('client.py', os.path.basename(name)), version=__version__)

    # "client.py scp" is a shorthand for "client.py run -s --scp"
    if a['scp']:
        a['run'] = True
        a['--single-threaded'] = True
        a['--scp'] = True

    interactive = not a['--non-interactive']
    action = a['ACTION']
    parameters = a['PARAMETER']
    path = a['--path'].split('.') if a['--path'] else None
    extra_loggers = extra_loggers or []
    scp = a['--scp']

    # Socket name variable
    # In case of integers, they map to /tmp/deployer.sock.username.X
    socket_name = a['--socket']

    if socket_name is not None and socket_name.isdigit():
        socket_name = '/tmp/deployer.sock.%s.%s' % (getpass.getuser(), socket_name)

    # List sessions
    if a['list-sessions']:
        list_sessions()

    # Telnet server
    elif a['telnet-server']:
        port = int(a['PORT']) if a['PORT'] is not None else 23
        start_telnet_server(root_node, logfile=a['--log'], port=port,
                extra_loggers=extra_loggers)

    # Socket server
    elif a['listen']:
        socket_name = start_server(root_node, daemonized=False,
                    shutdown_on_last_disconnect=False,
                    interactive=interactive, logfile=a['--log'], socket=a['--socket'],
                    extra_loggers=extra_loggers)

    # Connect to socket
    elif a['connect']:
        start_client(socket_name, path, action_name=action, parameters=parameters,
                open_scp_shell=scp)

    # Single threaded client
    elif a['run'] and a['--single-threaded']:
        start_standalone(root_node, interactive=interactive, cd_path=path,
                action_name=action, parameters=parameters, logfile=a['--log'],
                extra_loggers=extra_loggers, open_scp_shell=scp)

    # Multithreaded
    elif a['run']:
        # If no socket has been given. Start a daemonized server in the
        # background, and use that socket instead.
        if not socket_name:
            socket_name = start_server(root_node, daemonized=True,
                    shutdown_on_last_disconnect=True, interactive=interactive,
                    logfile=a['--log'], extra_loggers=extra_loggers)

        start_client(socket_name, path, action_name=action, parameters=parameters,
                open_scp_shell=scp)

########NEW FILE########
__FILENAME__ = console
"""
The ``console`` object is an interface for user interaction from within a
``Node``. Among the input methods are choice lists, plain text input and password
input.

It has output methods that take the terminal size into account, like pagination
and multi-column display. It takes care of the pseudo terminal underneat.

Example:

::

    class MyNode(Node):
        def do_something(self):
            if self.console.confirm('Should we really do this?', default=True):
                # Do it...
                pass

.. note:: When the script runs in a shell that was started with the
    ``--non-interactive`` option, the default options will always be chosen
    automatically.

"""

from deployer import std

from termcolor import colored
from datetime import datetime

import random

__all__ = ('Console', 'NoInput', 'ProgressBarSteps', 'ProgressBar', )

class NoInput(Exception):
    pass


class Console(object):
    """
    Interface for user interaction from within a ``Node``.

    :param pty: :class:`deployer.pseudo_terminal.Pty` instance.
    """
    def __init__(self, pty):
        self._pty = pty

    @property
    def pty(self):
        """ The :class:`deployer.pseudo_terminal.Pty` of this console. """
        return self._pty

    @property
    def is_interactive(self):
        """
        When ``False`` don't ask for input and choose the default options when
        possible.
        """
        return self._pty.interactive

    def input(self, label, is_password=False, answers=None, default=None):
        """
        Ask for plain text input. (Similar to raw_input.)

        :param is_password: Show stars instead of the actual user input.
        :type is_password: bool
        :param answers: A list of the accepted answers or None.
        :param default: Default answer.
        """
        stdin = self._pty.stdin
        stdout = self._pty.stdout

        def print_question():
            answers_str = (' [%s]' % (','.join(answers)) if answers else '')
            default_str = (' (default=%s)' % default if default is not None else '')
            stdout.write(colored('  %s%s%s: ' % (label, answers_str, default_str), 'cyan'))
            stdout.flush()

        def read_answer():
            value = ''
            print_question()

            while True:
                c = stdin.read(1)

                # Enter pressed
                if c in ('\r', '\n') and (value or default):
                    stdout.write('\r\n')
                    break

                # Backspace pressed
                elif c == '\x7f' and value:
                    stdout.write('\b \b')
                    value = value[:-1]

                # Valid character
                elif ord(c) in range(32, 127):
                    stdout.write(colored('*' if is_password else c, attrs=['bold']))
                    value += c

                elif c == '\x03': # Ctrl-C
                    raise NoInput

                stdout.flush()

            # Return result
            if not value and default is not None:
                return default
            else:
                return value

        with std.raw_mode(stdin):
            while True:
                if self._pty.interactive:
                    value = read_answer()
                elif default is not None:
                    print_question()
                    stdout.write('[non interactive] %r\r\n' % default)
                    stdout.flush()
                    value = default
                else:
                    # XXX: Asking for input in non-interactive session
                    value = read_answer()

                # Return if valid anwer
                if not answers or value in answers:
                    return value

                # Otherwise, ask again.
                else:
                    stdout.write('Invalid answer.\r\n')
                    stdout.flush()

    def choice(self, question, options, allow_random=False, default=None):
        """
        :param options: List of (name, value) tuples.
        :type options: list
        :param allow_random: If ``True``, the default option becomes 'choose random'.
        :type allow_random: bool
        """
        if len(options) == 0:
            raise NoInput('No options given.')

        if allow_random and default is not None:
            raise Exception("Please don't provide allow_random and default parameter at the same time.")

        # Order options alphabetically
        options = sorted(options, key=lambda i:i[0])

        # Ask for valid input
        while True:
            self._pty.stdout.write(colored('  %s\n' % question, 'cyan'))

            # Print options
            self.lesspipe(('%10i %s' % (i+1, tuple_[0]) for i, tuple_ in enumerate(options)))

            if allow_random:
                default = 'random'
            elif default is not None:
                try:
                    default = [o[1] for o in options ].index(default) + 1
                except ValueError:
                    raise Exception('The default value does not appear in the options list.')

            result = self.input(question, default=('random' if allow_random else default))

            if allow_random and result == 'random':
                return random.choice(options)[1]
            else:
                try:
                    result = int(result)
                    if 1 <= result <= len(options):
                        return options[result - 1][1]
                except ValueError:
                    pass

                self.warning('Invalid input')

    def confirm(self, question, default=None):
        """
        Print this yes/no question, and return ``True`` when the user answers
        'Yes'.
        """
        answer = 'invalid'

        if default is not None:
            assert isinstance(default, bool)
            default = 'y' if default else 'n'

        while answer not in ('yes', 'no', 'y', 'n'):
            answer = self.input(question + ' [y/n]', default=default)

        return answer in ('yes', 'y')

    #
    # Node selector
    #

    def select_node(self, root_node, prompt='Select a node', filter=None):
        """
        Show autocompletion for node selection.
        """
        from deployer.cli import ExitCLILoop, Handler, HandlerType, CLInterface

        class NodeHandler(Handler):
            def __init__(self, node):
                self.node = node

            @property
            def is_leaf(self):
                return not filter or filter(self.node)

            @property
            def handler_type(self):
                class NodeType(HandlerType):
                    color = self.node.get_group().color
                return NodeType()

            def complete_subhandlers(self, part):
                for name, subnode in self.node.get_subnodes():
                    if name.startswith(part):
                        yield name, NodeHandler(subnode)

            def get_subhandler(self, name):
                if self.node.has_subnode(name):
                    subnode = self.node.get_subnode(name)
                    return NodeHandler(subnode)

            def __call__(self, context):
                raise ExitCLILoop(self.node)

        root_handler = NodeHandler(root_node)

        class Shell(CLInterface):
            @property
            def prompt(self):
                return colored('\n%s > ' % prompt, 'cyan')

            not_found_message = 'Node not found...'
            not_a_leaf_message = 'Not a valid node...'

        node_result = Shell(self._pty, root_handler).cmdloop()

        if not node_result:
            raise NoInput

        return self.select_node_isolation(node_result)

    def select_node_isolation(self, node):
        """
        Ask for a host, from a list of hosts.
        """
        from deployer.inspection import Inspector
        from deployer.node import IsolationIdentifierType

        # List isolations first. (This is a list of index/node tuples.)
        options = [
                (' '.join([ '%s (%s)' % (h.slug, h.address) for h in hosts ]), node) for hosts, node in
                Inspector(node).iter_isolations(identifier_type=IsolationIdentifierType.HOST_TUPLES)
                ]

        if len(options) > 1:
            return self.choice('Choose a host', options, allow_random=True)
        else:
            return options[0][1]

    def lesspipe(self, line_iterator):
        """
        Paginator for output. This will print one page at a time. When the user
        presses a key, the next page is printed. ``Ctrl-c`` or ``q`` will quit
        the paginator.

        :param line_iterator: A generator function that yields lines (without
                              trailing newline)
        """
        stdin = self._pty.stdin
        stdout = self._pty.stdout
        height = self._pty.get_size()[0] - 1

        with std.raw_mode(stdin):
            lines = 0
            for l in line_iterator:
                # Print next line
                stdout.write(l)
                stdout.write('\r\n')
                lines += 1

                # When we are at the bottom of the terminal
                if lines == height:
                    # Wait for the user to press enter.
                    stdout.write(colored('  Press enter to continue...', 'cyan'))
                    stdout.flush()

                    try:
                        c = stdin.read(1)

                        # Control-C or 'q' will quit pager.
                        if c in ('\x03', 'q'):
                            stdout.write('\r\n')
                            stdout.flush()
                            return
                    except IOError:
                        # Interupted system call.
                        pass

                    # Move backwards and erase until the end of the line.
                    stdout.write('\x1b[40D\x1b[K')
                    lines = 0
            stdout.flush()

    def in_columns(self, item_iterator, margin_left=0):
        """
        :param item_iterator: An iterable, which yields either ``basestring``
                              instances, or (colored_item, length) tuples.
        """
        # Helper functions for extracting items from the iterator
        def get_length(item):
            return len(item) if isinstance(item, basestring) else item[1]

        def get_text(item):
            return item if isinstance(item, basestring) else item[0]

        # First, fetch all items
        all_items = list(item_iterator)

        if not all_items:
            return

        # Calculate the longest.
        max_length = max(map(get_length, all_items)) + 1

        # World per line?
        term_width = self._pty.get_size()[1] - margin_left
        words_per_line = max(term_width / max_length, 1)

        # Iterate through items.
        margin = ' ' * margin_left
        line = [ margin ]
        for i, j in enumerate(all_items):
            # Print command and spaces
            line.append(get_text(j))

            # When we reached the max items on this line, yield line.
            if (i+1) % words_per_line == 0:
                yield ''.join(line)
                line = [ margin ]
            else:
                # Pad with whitespace
                line.append(' ' * (max_length - get_length(j)))

        yield ''.join(line)

    def warning(self, text):
        """
        Print a warning.
        """
        stdout = self._pty.stdout
        stdout.write(colored('*** ', 'yellow'))
        stdout.write(colored('WARNING: ' , 'red'))
        stdout.write(colored(text, 'red', attrs=['bold']))
        stdout.write(colored(' ***\n', 'yellow'))
        stdout.flush()

    def progress_bar(self, message, expected=None, clear_on_finish=False, format_str=None):
        """
        Display a progress bar. This returns a Python context manager.
        Call the next() method to increase the counter.

        ::

            with console.progress_bar('Looking for nodes') as p:
                for i in range(0, 1000):
                    p.next()
                    ...

        :returns: :class:`ProgressBar` instance.
        :param message: Text label of the progress bar.
        """
        return ProgressBar(self._pty, message, expected=expected,
                    clear_on_finish=clear_on_finish, format_str=format_str)

    def progress_bar_with_steps(self, message, steps, format_str=None):
        """
        Display a progress bar with steps.

        ::

            steps = ProgressBarSteps({
                1: "Resolving address",
                2: "Create transport",
                3: "Get remote key",
                4: "Authenticating" })

            with console.progress_bar_with_steps('Connecting to SSH server', steps=steps) as p:
                ...
                p.set_progress(1)
                ...
                p.set_progress(2)
                ...

        :param steps: :class:`ProgressBarSteps` instance.
        :param message: Text label of the progress bar.
        """
        return ProgressBar(self._pty, message, steps=steps, format_str=format_str)


class ProgressBarSteps(object): # TODO: unittest this class.
    def __init__(self, steps):
        # Validate
        for k,v in steps.items():
            assert isinstance(k, int)
            assert isinstance(v, basestring)

        self._steps = steps

    def get_step_description(self, step):
        return self._steps.get(step, '')

    def get_steps_count(self):
        return max(self._steps.keys())


class ProgressBar(object):
    interval = .1 # Refresh interval

    def __init__(self, pty, message, expected=None, steps=None, clear_on_finish=False, format_str=None):
        if expected and steps:
            raise Exception("Don't give expected and steps parameter at the same time.")

        self._pty = pty
        self.message = message
        self.counter = 0
        self.expected = expected
        self.clear_on_finish = clear_on_finish

        self.done = False
        self._last_print = datetime.now()

        # Duration
        self.start_time = datetime.now()
        self.end_time = None

        # In case of steps
        if steps is not None:
            assert isinstance(steps, ProgressBarSteps)
            self.expected = steps.get_steps_count()

        self.steps = steps

        # Formatting
        if format_str:
            self.format_str = format_str
        elif self.expected:
            self.format_str = '%(message)s: %(counter)s/%(expected)s [%(percentage)s completed]  [%(duration)s] [%(status)s]'
        else:
            self.format_str = '%(message)s: %(counter)s [%(duration)s] [%(status)s]'

    def __enter__(self):
        self._print()
        return self

    def _print(self):
        # Calculate percentage
        percentage = '??'
        if self.expected and self.expected > 0:
            percentage = '%s%%' % (self.counter * 100 / self.expected)

        # Calculate duration
        duration = (self.end_time or datetime.now()) - self.start_time
        duration = str(duration).split('.')[0] # Don't show decimals.

        status = colored((
                'DONE' if self.done else
                self.steps.get_step_description(self.counter) if self.steps
                else ''), 'green')

        format_str = '\r\x1b[K' + self.format_str + '\r' # '\x1b[K' clears the line.

        self._pty.stdout.write(format_str % {
            'message': self.message,
            'counter': self.counter,
            'duration': duration,
            'counter': self.counter,
            'expected': self.expected,
            'percentage': percentage,
            'status': status ,
        })

    def next(self):
        """
        Increment progress bar counter.
        """
        self.set_progress(self.counter + 1, rewrite=False)

    def set_progress(self, value, rewrite=True):
        """
        Set counter to this value.

        :param rewrite: Always redraw the progress bar.
        :type rewrite: bool
        """
        self.counter = value

        # Only print when the last print was .3sec ago
        delta = (datetime.now() - self._last_print).microseconds / 1000 / 1000.

        if rewrite or delta > self.interval:
            self._print()
            self._last_print = datetime.now()

    def __exit__(self, *a):
        self.done = True
        self.end_time = datetime.now()

        if self.clear_on_finish:
            # Clear the line.
            self._pty.stdout.write('\x1b[K')
        else:
            # Redraw and keep progress bar
            self._print()
            self._pty.stdout.write('\n')

########NEW FILE########
__FILENAME__ = commands
from deployer.utils import esc1

def wget(url, target=None):
    """
    Download file using wget
    """
    if target:
        return "wget '%s' --output-document '%s'" %  (esc1(url), esc1(target))
    else:
        return "wget '%s'" % esc1(url)

def bashrc_append(line):
    """
    Create a command which appends something to .bashrc if this line was not yet added before.
    """
    return "grep '%s' ~/.bashrc || echo '%s' >> ~/.bashrc" % (esc1(line), esc1(line))

########NEW FILE########
__FILENAME__ = on_host
from deployer.loggers import Logger, RunCallback, ForkCallback
from deployer.utils import esc1

class OnHostLogger(Logger):
    """
    Log all transactions on every host in:
    ~/.deployer/history
    """
    def __init__(self, username):
        from socket import gethostname
        self.from_host = gethostname()
        self.username = username

    def log_run(self, run_entry):
        if not run_entry.sandboxing:
            run_entry.host._run_silent("""
                mkdir -p ~/.deployer/;
                echo -n `date '+%%Y-%%m-%%d %%H:%%M:%%S | ' ` >> ~/.deployer/history;
                echo -n '%s | %s | %s | ' >> ~/.deployer/history;
                echo '%s' >> ~/.deployer/history;
                """
                % ('sudo' if run_entry.use_sudo else '    ',
                    esc1(self.from_host),
                    esc1(self.username),
                    esc1(run_entry.command or '')
                    ))
        return RunCallback()

    def log_fork(self, fork_entry):
        # Use the same class OnHostLogger in forks.
        class callback(ForkCallback):
            def get_fork_logger(c):
                return OnHostLogger(self.username)
        return callback()

########NEW FILE########
__FILENAME__ = apt_get
from deployer.contrib.commands import wget
from deployer.exceptions import ExecCommandFailed
from deployer.node import ParallelNode
from deployer.utils import esc1


DEFAULT_KEYSERVER = 'hkp://keyserver.ubuntu.com:80/'

class AptGet(ParallelNode):
    packages = ()
    packages_if_available = ()
                # Packages to be installed when they're available.  Don't
                # throw errors when not available.
    dpkg_packages = ()
    extra_keys = ()
    extra_key_urls = ()
    extra_sources = {}

    def setup(self):
        self.setup_extra()
        self.install()

    def install(self, skip_update=True):
        """
        Install packages.
        """
        if not skip_update:
            self.update()

        # apt-get install
        with self.host.env('DEBIAN_FRONTEND', 'noninteractive'):
            self.host.sudo('apt-get install -yq %s' % ' '.join(self.packages))

            # Optional packages
            for p in self.packages_if_available:
                try:
                    self.host.sudo('apt-get install -yq %s' % p)
                except ExecCommandFailed:
                    print 'Failed to install %s on %s, ignoring...' % (p, self.host.slug)

        # dpkg packages
        self.install_dpkg_packages()

    def update(self):
        with self.host.env('DEBIAN_FRONTEND', 'noninteractive'):
            self.host.sudo('apt-get update')

    def add_key_url(self, key_url):
        self.host.sudo("wget '%s' -O - | apt-key add -" % esc1(key_url))

    def add_key(self, fingerprint, keyserver=None):
        keyserver = keyserver if keyserver else DEFAULT_KEYSERVER
        self.host.sudo("apt-key adv --keyserver %s --recv %s" % (keyserver, fingerprint))

    def add_sources(self, slug, sources, overwrite=False):
        extra_sources_dir = '/etc/apt/sources.list.d'
        distro_codename = self.host.run('lsb_release -cs', interactive=False).strip()
        if not self.host.exists('%s/%s.list' % (extra_sources_dir, slug)) or overwrite:
            self.host.open('%s/%s.list' % (extra_sources_dir, slug), 'w', use_sudo=True) \
                    .write("\n".join(sources) % {'distro_codename': distro_codename})

    def setup_extra(self):
        self.setup_extra_keys()
        self.setup_extra_key_urls()
        self.setup_extra_sources()
        self.update()

    def setup_extra_keys(self):
        for key in self.extra_keys:
            self.add_key(key)

    def setup_extra_key_urls(self):
        for key_url in self.extra_key_urls:
            self.add_key_url(key_url)

    def setup_extra_sources(self):
        for slug, sources in self.extra_sources.items():
            self.add_sources(slug, sources)

    def install_dpkg_packages(self):
        for package in self.dpkg_packages:
            self.host.sudo(wget(package))
            self.host.sudo("dpkg -i '%s'" % esc1(package.split('/')[-1]))

    def is_package_available(self, package):
        # apt-cache will return an error message on stderr,
        # but nothing on stdout if the package could not be found
        return bool(self.host.run("apt-cache madison '%s'" % esc1(package),
            interactive=False).strip())

########NEW FILE########
__FILENAME__ = config
from pygments import highlight
from pygments.lexers import TextLexer, DiffLexer
from pygments.formatters import TerminalFormatter as Formatter

from deployer.node import ParallelNode, required_property, suppress_action_result
from deployer.utils import esc1

import difflib


class Config(ParallelNode):
    """
    Base class for all configuration files.
    """
    # Full path of the location where this config should be stored. (Start with slash)
    remote_path = required_property()

    # The textual content that should be saved in this place.
    content = required_property()

    # Pygments Lexer
    lexer = TextLexer

    use_sudo = True
    make_executable = False
    always_backup_existing_config = False

                # TODO: maybe we should make this True by default,
                #       but don't backup when the 'diff' is empty.

    def show_new_config(self):
        """
        Show the new configuration file. (What will be installed on 'setup')
        """
        print highlight(self.content, self.lexer(), Formatter())

    def show(self):
        """
        Show the currently installed configuration file.
        """
        print highlight(self.current_content, self.lexer(), Formatter())

    @property
    def current_content(self):
        """
        Return the content which currently exists in this file.
        """
        return self.host.open(self.remote_path, 'rb', use_sudo=True).read()

    @suppress_action_result
    def diff(self):
        """
        Show changes to be written to the file. (diff between the current and
        the new config.)
        """
        # Split new and existing content in lines
        current_content = self.current_content.splitlines(1)
        new_content = self.content.splitlines(1)

        # Call difflib
        diff = ''.join(difflib.unified_diff(current_content, new_content))
        print highlight(diff, DiffLexer(), Formatter())

        return diff

    @suppress_action_result
    def exists(self):
        """
        True when this config exists.
        """
        if self.host.exists(self.remote_path):
            print 'Yes, config exists already.'
            return True
        else:
            print 'Config doesn\'t exist yet'
            return False

    def changed(self):
        """
        Return True when there are configuration changes.
        (Or when the file does not yet exist)
        """
        if self.exists():
            return self.current_content != self.content
        else:
            return True

    def setup(self):
        """
        Install config on remote machines.
        """
        # Backup existing configuration
        if self.always_backup_existing_config:
            self.backup()

        self.host.open(self.remote_path, 'wb', use_sudo=self.use_sudo).write(self.content)

        if self.make_executable:
            self.host.sudo("chmod a+x '%s'" % esc1(self.host.expand_path(self.remote_path)))

    def backup(self):
        """
        Create a backup of this configuration file on the same host, in the same directory.
        """
        import datetime
        suffix = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        self.host.sudo("test -f '%s' && cp --archive '%s' '%s.%s'" % (
                        esc1(self.remote_path), esc1(self.remote_path), esc1(self.remote_path), esc1(suffix)))

    def edit_in_vim(self):
        """
        Edit this configuration manually in Vim.
        """
        self.host.sudo("vim '%s'" % esc1(self.host.expand_path(self.remote_path)))

########NEW FILE########
__FILENAME__ = connect
from deployer.node import ParallelNode, isolate_one_only


class Connect(ParallelNode):
    """
    Open SSH connection to host
    """
    @property
    def initial_input(self):
        # Override this one in order to create a connect statement
        # which does 'cd' to a certain directory, activates a virtualenv,
        # or executes any other arbitrary command in the shell before handing
        # over control to the user.
        return None

    @isolate_one_only # It does not make much sense to open interactive shells to all hosts at the same time.
    def with_host(self):
        self.host.start_interactive_shell(initial_input=self.initial_input)
        print

    @isolate_one_only
    def as_root(self):
        self.host.sudo('/bin/bash')
        print

    __call__ = with_host

########NEW FILE########
__FILENAME__ = git
from deployer.exceptions import ExecCommandFailed
from deployer.node import Node, ParallelNode, ParallelNodeBase, dont_isolate_yet, required_property
from deployer.utils import esc1

__all__ = ('Git', 'GitOverview' )


class GitBase(ParallelNodeBase):
    _default_commands = {
        'branch': 'branch',
        'describe': 'describe',
        'diff': 'diff',
        'log': 'log',
        'pull': 'pull',
        'reset': 'reset --hard',
        'show': 'show',
        'show_oneline': 'show --oneline|head -n 1',
        'stash': 'stash',
        'stash_list': 'stash list',
        'stash_pop': 'stash pop',
        'stash_clear': 'stash clear',
        'status': 'status',
        'version': 'version',
        'whatchanged': 'whatchanged',
        'head_sha': 'rev-parse HEAD',
    }

    _ignore_exit_status = [ 'show', 'whatchanged' ] # These are displayed through lesspipe, and would return 141 when 'q' was pressed.

    def __new__(cls, name, bases, attrs):
        # Extra git commands
        commands = attrs.get('commands', { })

        for cmd_name, command in cls._default_commands.items() + commands.items():
            attrs[cmd_name] = cls._create_git_command(command,
                                        ignore_exit_status=command in cls._ignore_exit_status)

        return ParallelNodeBase.__new__(cls, name, bases, attrs)

    @staticmethod
    def _create_git_command(command, ignore_exit_status=False):
        def run(self):
            with self.host.cd(self.repository_location):
                return self.host.run('git %s' % command, ignore_exit_status=ignore_exit_status)
        return run


class Git(ParallelNode):
    """
    Manage the git checkout of a project
    """
    __metaclass__ = GitBase

    repository = required_property()
    repository_location = required_property()
    default_revision = 'master'

    commands = { } # Extra git commands. Map function name to git command.

    @dont_isolate_yet
    def checkout(self, commit=None):
        # NOTE: this public 'checkout'-method uses @dont_isolate_yet, so that
        # in case of a parrallel checkout, we only ask once for the commit
        # name, and fork only to several threads after calling '_checkout'.

        # If no commit was given, ask for commit.
        if not commit:
            commit = self.console.input('Git commit', default=self.default_revision)
            if not commit: raise Exception('No commit given')

        self._checkout(commit)

    def _before_checkout_hook(self, commit):
        """ To be overridden. This function can throw an exception for
        instance, in a case when it's not allowed to continue with the
        checkout. (e.g. when git-grep matches a certain pattern that is not
        allowed on the machine.) """
        pass

    def _checkout(self, commit):
        """
        This will either clone or checkout the given commit. Changes in the
        repository are always stashed before checking out, and stash-popped
        afterwards.
        """
        # Checkout on every host.
        host = self.host
        existed = host.exists(self.repository_location)

        if not existed:
            # Do a new checkout
            host.run('git clone --recursive %s %s' % (self.repository, self.repository_location))

        with host.cd(self.repository_location):
            host.run('git fetch --all --prune')

            self._before_checkout_hook(commit)

            # Stash
            if existed:
                host.run('git stash')

            # Checkout
            try:
                host.run("git checkout '%s'" % esc1(commit))
                host.run("git submodule update --init") # Also load submodules.
            finally:
                # Pop stash
                try:
                    if existed:
                        host.run('git stash pop 2>&1', interactive=False) # will fail when checkout had no local changes
                except ExecCommandFailed, e:
                    result = e.result
                    if result.strip() not in ('Nothing to apply', 'No stash found.'):
                        print result
                        if not self.console.confirm('Should we continue?', default=True):
                            raise Exception('Problem with popping your stash, please check logs and try again.')


class GitOverview(Node):
    """
    Show a nice readable overview of all the git checkouts of all the services in the tree.
    """
    def show(self):
        from deployer.inspection import filters, Inspector

        def iterate():
            iterator = Inspector(Inspector(self).get_root()).walk(filters.IsInstance(Git) & filters.PublicOnly)
            for node in iterator:
                full_path = '.'.join(Inspector(node).get_path())
                checkout = str(node.show_oneline()).strip()
                yield ' %-40s %s' % (full_path, checkout)

        self.console.lesspipe(iterate())

    __call__ = show

########NEW FILE########
__FILENAME__ = hg
from deployer.node import ParallelNode, required_property, dont_isolate_yet, ParallelNodeBase
from deployer.utils import esc1


class HgBase(ParallelNodeBase):
    _default_commands = {
        'id': 'id',
        'log': 'log',
        'status': 'status',
        'summary': 'summary',
        'version': 'version',
    }

    def __new__(cls, name, bases, attrs):
        # Extra hg commands
        commands = attrs.get('commands', { })

        for cmd_name, command in cls._default_commands.items() + commands.items():
            attrs[cmd_name] = cls._create_hg_command(command)

        return ParallelNodeBase.__new__(cls, name, bases, attrs)

    @staticmethod
    def _create_hg_command(command):
        def run(self):
            with self.host.cd(self.repository_location):
                return self.host.run('hg %s' % command)
        return run


class Hg(ParallelNode):
    """
    Mercurial repository.
    """
    __metaclass__ = HgBase

    repository = required_property()
    repository_location = required_property()
    default_changeset = 'default'

    commands = { } # Extra hg commands. Map function name to hg command.

    @dont_isolate_yet
    def checkout(self, changeset=None):
        if not changeset:
            commit = self.console.input('Hg changeset', default=self.default_changeset)
            if not commit: raise Exception('No changeset given')

        self._checkout(changeset)

    def _checkout(self, changeset):
        # Clone the fist time
        existed = self.host.exists(self.repository_location)
        if not existed:
            self.host.run("hg clone '%s' '%s'" % (esc1(self.repository), esc1(self.repository_location)))

        # Checkout
        with self.host.cd(self.repository_location):
            self.host.run("hg checkout '%s'" % esc1(changeset))

########NEW FILE########
__FILENAME__ = inspection
from deployer.inspection.inspector import Inspector
from deployer.node import ParallelNode, Node

import termcolor


class AnalyseHost(ParallelNode):
    """
    Analyze a host and find out what it's used for.
    """
    def analyise(self):
        """
        Discover what a host is used for, which role mappings it has for every
        node.
        """
        with self.console.progress_bar('Looking for nodes') as progress_bar:
            print termcolor.colored('Showing node::role for every match of %s' % self.host.slug, 'cyan')

            def process_node(node):
                # Gather roles which contain this host in the current node.
                roles = []
                for role in node.hosts.roles:
                    progress_bar.next()
                    for h in node.hosts.filter(role):
                        if h._host.__class__ == self.host._host.__class__:
                            roles.append(role)

                # If roles were found, print result
                if roles:
                    print '.'.join(Inspector(node).get_path()), termcolor.colored(' :: ', 'cyan'), termcolor.colored(', '.join(roles), 'yellow')

                for childnode in Inspector(node).get_childnodes(verify_parent=True):
                    process_node(childnode)

            process_node(Inspector(self).get_root())
    __call__ = analyise


class Inspection(Node):
    """
    Inspection of all services
    """
    except_peer_services = [ ]

    def print_everything(self):
        """
        Example command which prints all nodes with their actions
        """
        def print_node(node):
            print
            print '====[ %s ]==== ' % node.__repr__(path_only=True)
            print

            print 'Actions:'
            for name, action in node.get_actions():
                print ' - ', name, action
            print

            for child in node.get_childnodes():
                print_node(child)

        print_node(Inspector(self).get_root())


    def global_status(self):
        """
        Sanity check.
        This will browse all nodes for a 'status' method and run it.
        """
        def process_node(node):
            print node.__repr__()

            for name, action in node.get_actions():
                if name == 'status':
                    try:
                        action()
                    except Exception as e:
                        print 'Failed: ', e.message

            for name, subnode in node.get_subnodes():
                process_node(subnode)

        process_node(Inspector(self).get_root())

########NEW FILE########
__FILENAME__ = daemonize
"""
Double fork-trick. For starting a posix daemon.
http://code.activestate.com/recipes/66012-fork-a-daemon-process-on-unix/
"""

import os
import sys


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    '''This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.
    Note that stderr is opened unbuffered, so
    if it shares a file with stdout then interleaved output
    may not appear in the order that you expect.
    '''
    # Do first fork.
    try:
        pid = os.fork()
        if pid > 0:
            return 0 # Return 0 from first parent.
            #sys.exit(0) # Exit first parent.
    except OSError, e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)    )
        sys.exit(1)

    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid()

    # Do second fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0) # Exit second parent.
    except OSError, e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)    )
        sys.exit(1)

    # Now I am a daemon!

    # Redirect standard file descriptors.

        # NOTE: For debugging, you meight want to take these instead of /dev/null.
    #so = file('/tmp/log', 'a+')
    #se = file('/tmp/log', 'a+', 0)

    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    # Return 1 from daemon.
    return 1

########NEW FILE########
__FILENAME__ = exceptions

class DeployerException(Exception):
    """
    Base exception class.
    """
    pass


class ExecCommandFailed(DeployerException):
    """
    Execution of a run() or sudo() call on a host failed.
    """
    def __init__(self, command, host, use_sudo, status_code, result=None):
        self.command = command
        self.use_sudo = use_sudo
        self.host = host
        self.status_code = status_code
        self.result = result

        DeployerException.__init__(self, 'Executing "%s" on "%s" failed with status code: %s' %
                    (command, host.slug, status_code))


class QueryException(DeployerException):
    """
    Resolving of a Q object in a deployer Node failed.
    """
    def __init__(self, node, attr_name, query, inner_exception):
        self.node = node
        self.attr_name = attr_name
        self.query = query
        self.inner_exception = inner_exception

        DeployerException.__init__(self, 'Running query %s:=%r on "%s" failed' %
                            (self.attr_name, self.query, repr(self.node)))

class ActionException(DeployerException):
    """
    When an action fails.
    """
    def __init__(self, inner_exception, traceback):
        self.inner_exception = inner_exception
        self.traceback = traceback

    def __repr__(self):
        return 'ActionException(%r)' % repr(self.inner_exception)

class ConnectionFailedException(DeployerException):
    """
    When connecting to an SSH host fails.
    """

########NEW FILE########
__FILENAME__ = groups

"""
A ``Group`` can be attached to every Node, in order to put them in categories.

Typically, you have group names like ``alpha``, ``beta`` and ``production``.
The interactive shell will show the nodes in other colours, depending on the
group they're in.

For instance.

::

    from deployer.groups import production, staging

    class N(Node):
        @production
        class Child(Node):
            pass
"""

__all__ = (
        'Group',
        'set_group'
)

class Group(object):
    """
    Group to which a node belongs.
    """
    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            # Give the group a 'name'-property, based on
            # its own class name
            dct['name'] = name
            return type.__new__(cls, name, bases, dct)

    color = None
    """
    Colour for this service/action in the shell. Right now, only the colours
    from the ``termcolor`` library are supported:

    grey, red, green, yellow, blue, magenta, cyan, white
    """


def set_group(group):
    """
    Set the group for this node.

    ::

        @set_group(Staging)
        class MyNode(Node):
            pass
    """
    def group_setter(node):
        return type(node.__name__, (node,), { 'node_group': group })
    return group_setter

#
# Built-in groups
#

class Production(Group):
    color = 'red'

class Staging(Group):
    color = 'yellow'

class Beta(Group):
    color = 'green'

class Local(Group):
    color = 'green'

class Other(Group):
    color = 'white'

class Utility(Group):
    color = 'magenta'

#
# Decorators for built-in groups
#

production = set_group(Production)
staging = set_group(Staging)
beta = set_group(Beta)
local = set_group(Local)
other = set_group(Other)
utility = set_group(Utility)

########NEW FILE########
__FILENAME__ = base

import contextlib
import logging
import os
import paramiko
import random
import socket
import termcolor
import time
from stat import S_ISDIR, S_ISREG

from deployer.console import Console
from deployer.exceptions import ExecCommandFailed
from deployer.loggers import DummyLoggerInterface
from deployer.pseudo_terminal import DummyPty, select
from deployer.std import raw_mode
from deployer.utils import esc1

from StringIO import StringIO
from twisted.internet import fdesc

__all__ = (
    'Host',
    'HostContext',
    'Stat',
)

class HostContext(object):
    """
    A push/pop stack which keeps track of the context on which commands
    at a host are executed.

    (This is mainly used internally by the library.)
    """
        # TODO: Guarantee thread safety!! When doing parallel deployments, and
        #       several threads act on the same host, things will probably go
        #       wrong...
    def __init__(self):
        self._command_prefixes = []
        self._path = []
        self._env = []

    def copy(self):
        """ Create a deep copy. """
        c = HostContext()
        c._command_prefixes = list(self._command_prefixes)
        c._path = list(self._path)
        c._env = list(self._env)
        return c

    def __repr__(self):
        return 'HostContext(prefixes=%r, path=%r, env=%r)' % (
                        self._command_prefixes, self._path, self._env)

    def prefix(self, command):
        """
        Prefix all commands with given command plus ``&&``.

        ::

            with host.prefix('workon environment'):
                host.run('./manage.py migrate')
        """
        class Prefix(object):
            def __enter__(context):
                self._command_prefixes.append(command)

            def __exit__(context, *args):
                self._command_prefixes.pop()
        return Prefix()

    def cd(self, path, expand=False):
        """
        Execute commands in this directory. Nesting of cd-statements is
        allowed.

        ::

            with host.cd('directory'):
                host.run('ls')

        :param expand: Expand tildes.
        :type expand: bool
        """
        class CD(object):
            def __enter__(context):
                self._path.append((path, expand))

            def __exit__(context, *args):
                self._path.pop()
        return CD()

    def _chdir(self, path):
        """ Move to this directory. Not to be used together with the `cd` context manager. """
        # NOTE: This is used by the sftp shell.
        self._path = [ (os.path.join(* self._path + [path]), False) ]

    def env(self, variable, value, escape=True):
        """
        Set this environment variable

        ::

            with host.cd('VAR', 'my-value'):
                host.run('echo $VAR')
        """
        if value is None:
            value = ''

        if escape:
            value = "'%s'" % esc1(value)

        class ENV(object):
            def __enter__(context):
                self._env.append( (variable, value) )

            def __exit__(context, *args):
                self._env.pop()
        return ENV()


class Stat(object):
    """ Base `Stat` class """
    def __init__(self, stat_result, filename):
        self._stat_result = stat_result
        self.filename = filename

    @property
    def st_size(self):
        """ File size in bytes. """
        return self._stat_result.st_size

    @property
    def st_uid(self):
        """ User ID """
        return self._stat_result.st_uid

    @property
    def st_gid(self):
        """ Group ID """
        return self._stat_result.st_gid

    @property
    def st_mode(self):
        return self._stat_result.st_mode

    @property
    def is_dir(self):
        """ True when this is a directory. """
        return S_ISDIR(self.st_mode)

    @property
    def is_file(self):
        """ True when this is a regular file. """
        return S_ISREG(self.st_mode)


class Host(object):
    """
    Abstract base class for SSHHost and LocalHost.

    :param pty: The pseudo terminal wrapper which handles the stdin/stdout.
    :type pty: :class:`deployer.pseudo_terminal.Pty`
    :param logger: The logger interface.
    :type logger: LoggerInterface

    ::

            class MyHost(SSHHost):
                ...
            my_host = MyHost()
            my_host.run('pwd', interactive=False)
    """
    #class __metaclass__(type):
    #    @property
    #    def slug(self):
    #        return self.__name__

    slug = '' # TODO: maybe deprecate 'slug' and use __class__.__name__ instead.
    """
    The slug should be a unique identifier for the host.
    """

    username = ''
    """
    Username for connecting to the Host
    """

    password = ''
    """
    Password for connecting to the host. (for sudo)
    """

    # Magic prompt. We expect this string to not appear in the stdout of
    # random programs. This makes it possible to automatically send the
    # correct password when sudo asks us.
    magic_sudo_prompt = termcolor.colored('[:__enter-sudo-password__:]', 'grey') #, attrs=['concealed'])

    def __init__(self, pty=None, logger=None):
        self.host_context = HostContext()
        self.pty = pty or DummyPty()
        self.logger = logger or DummyLoggerInterface()

    def copy(self, pty=None):
        """
        Create a deep copy of this Host class.
        (the pty-parameter allows to bind it to anothor pty)
        """
        h = self.__class__(pty=(pty or self.pty), logger=self.logger)
        h.host_context = self.host_context.copy()
        return h

    def __repr__(self):
        return 'Host(slug=%r, context=%r)' % (self.slug, self.host_context)

    def get_start_path(self):
        """
        The path in which commands at the server will be executed.
        by default. (if no cd-statements are used.)
        Usually, this is the home directory.
        It should always return an absolute path, starting with '/'
        """
        raise NotImplementedError
#        return self.get_home_directory(self.username)
#        if self.username:
#            return '~%s' % self.username
#        else:
#            return '~'

    def getcwd(self):
        """
        Return current working directory as absolute path.
        """
        # Get path from host context (expand expandable parts)
        host_context_path = [ (self._expand_tilde(path) if expand else path) for path, expand in self.host_context._path ]

        # Join with start path.
        path = os.path.normpath(os.path.join(*[ self.get_start_path() ] + host_context_path))
        assert path[0] == '/' # Returns absolute directory (get_start_path() should be absolute)
        return path

    def get_home_directory(self, username=None): # TODO: or use getcwd() on the sftp object??
        # TODO: maybe: return self.expand_path('~%s' % username if username else '~')
        if username:
            return self._run_silent('cd /; echo -n ~%s' % username, sandbox=False)
        else:
            return self._run_silent('cd /; echo -n ~', sandbox=False)

    def exists(self, filename, use_sudo=True, **kw):
        """
        Returns ``True`` when a file named ``filename`` exists on this hosts.
        """
        # Note: the **kw is required for passing in a HostContext.
        try:
            self._run_silent("test -f '%s' || test -d '%s'" % (esc1(filename), esc1(filename)),
                        use_sudo=use_sudo, **kw)
            return True
        except ExecCommandFailed:
            return False

    def get_ip_address(self, interface='eth0'):
        """
        Return internal IP address of this interface.
        """
        # We add "cd /", to be sure that at least no error get thrown because
        # we're in a non existing directory right now.

        return self._run_silent(
                """cd /; /sbin/ifconfig "%s" | grep 'inet ad' | """
                """ cut -d: -f2 | awk '{ print $1}' """ % interface).strip()

    def ifconfig(self):
        """
        Return the network information for this host.

        :returns: An :class:`IfConfig <deployer.utils.network.IfConfig>` instance.
        """
        # We add "cd /", to be sure that at least no error get thrown because
        # we're in a non existing directory right now.
        from deployer.utils import parse_ifconfig_output
        return parse_ifconfig_output(self._run_silent('cd /; /sbin/ifconfig'))

    def _wrap_command(self, command, sandbox):
        """
        Prefix command with cd-statements and variable assignments
        """
        result = []

        # Ensure that the start-path exists (only if one was given. Not for the ~)
#        if self.start_path:
#            result.append("(mkdir -p '%s' 2> /dev/null || true) && " %
#                            esc1(self.expand_path(self.start_path)))

        # Prefix with all cd-statements
        cwd = self.getcwd()
        # TODO: We can't have double quotes around paths,
        #       or shell expansion of '*' does not work.
        #       Make this an option for with cd(path):...
        if sandbox:
            # In sandbox mode, it may be possible that this directory
            # is not yet created, only 'cd' to it when the directory
            # really exists.
            result.append('if [ -d %s ]; then cd %s; fi && ' % (cwd,cwd))
        else:
            result.append('cd %s && ' % cwd)

        # Set TERM variable.
        result.append("export TERM=%s && " % self.pty.get_term_var())

        # Prefix with variable assignments
        for var, value in self.host_context._env:
            #result.append('%s=%s ' % (var, value))
            result.append("export %s=%s && " % (var, value))

            # We use the export-syntax instead of just the key=value prefix
            # for a command. This is necessary, because in the case of pipes,
            # like, e.g.:     " key=value  yes | command "
            # the variable 'key' will not be passed to the second command.
            #
            # Also, note that the value is not escaped, this allow inclusion
            # of other variables.

        # Add the command itself. Put in between braces to make sure that we
        # get the operator priority right. (if the command itself has an ||
        # operator, it won't otherwise work in combination with cd-statements.)
        result.append('(%s)' % command)

        return ''.join(result)

    def run(self, command, use_sudo=False, sandbox=False, interactive=True,
                    user=None, ignore_exit_status=False, initial_input=None, silent=False):
        """
        Execute this shell command on the host.

        :param command: The shell command.
        :type command: basestring
        :param use_sudo: Run as superuser.
        :type use_sudo: bool
        :param sandbox: Validate syntax instead of really executing. (Wrap the command in ``bash -n``.)
        :type sandbox: bool
        :param interactive: Start an interactive event loop which allows
                            interaction with the remote command. Otherwise, just return the output.
        :type interactive: bool
        :param initial_input: When ``interactive``, send this input first to the host.
        """
        assert isinstance(command, basestring)
        assert not initial_input or interactive # initial_input can only in case of interactive.

        logger = DummyLoggerInterface() if silent else self.logger
        pty = DummyPty() if silent else self.pty

        # Create new channel for this command
        chan = self._get_session()

        # Run in PTY (Sudo usually needs to be run into a pty)
        if interactive:
            height, width = pty.get_size()
            chan.get_pty(term=self.pty.get_term_var(), width=width, height=height)

            # Keep size of local pty and remote pty in sync
            def set_size():
                height, width = pty.get_size()
                try:
                    chan.resize_pty(width=width, height=height)
                except paramiko.SSHException as e:
                    # Channel closed. Ignore when channel was already closed.
                    pass
            pty.set_ssh_channel_size = set_size
        else:
            pty.set_ssh_channel_size = lambda:None

        command = " && ".join(self.host_context._command_prefixes + [command])

        # Start logger
        with logger.log_run(self, command=command, use_sudo=use_sudo,
                                sandboxing=sandbox, interactive=interactive) as log_entry:
            # Are we sandboxing? Wrap command in "bash -n"
            if sandbox:
                command = "bash -n -c '%s' " % esc1(command)
                command = "%s;echo '%s'" % (command, esc1(command))

            logging.info('Running "%s" on host "%s" sudo=%r, interactive=%r' %
                            (command, self.slug, use_sudo, interactive))

            # Execute
            if use_sudo:
                # We use 'sudo su' instead of 'sudo -u', because shell expension
                # of ~ is threated differently. e.g.
                #
                # 1. This will still show the home directory of the original user
                # sudo -u 'postgres' bash -c ' echo $HOME '
                #
                # 2. This shows the home directory of the user postgres:
                # sudo su postgres -c 'echo $HOME '
                if interactive:
                    wrapped_command = self._wrap_command((
                                "sudo -p '%s' su '%s' -c '%s'" % (esc1(self.magic_sudo_prompt), esc1(user), esc1(command))
                                #"sudo -u '%s' bash -c '%s'" % (user, esc1(command))
                                if user else
                                "sudo -p '%s' bash -c '%s' " % (esc1(self.magic_sudo_prompt), esc1(command))),
                                sandbox
                                )

                    logging.debug('Running wrapped command "%s"' % wrapped_command)
                    chan.exec_command(wrapped_command)

                # Some commands, like certain /etc/init.d scripts cannot be
                # run interactively. They won't work in a ssh pty.
                else:
                    wrapped_command = self._wrap_command((
                        "echo '%s' | sudo -p '(passwd)' -u '%s' -P %s " % (esc1(self.password), esc1(user), command)
                        if user else
                        "echo '%s' | sudo -p '(passwd)' -S %s " % (esc1(self.password), command)),
                        sandbox
                        )

                    logging.debug('Running wrapped command "%s" interactive' % wrapped_command)
                    chan.exec_command(wrapped_command)
            else:
                chan.exec_command(self._wrap_command(command, sandbox))

            if interactive:
                # Pty receive/send loop
                result = self._posix_shell(chan, initial_input=initial_input)
            else:
                # Read loop.
                result = self._read_non_interactive(chan)

                #print result # I don't think we need to print the result of non-interactive runs
                              # In any case self._run_silent_sudo should not print anything.

            # Retrieve status code
            status_code = chan.recv_exit_status()
            log_entry.set_status_code(status_code)

            pty.set_ssh_channel_size = None

            if status_code and not ignore_exit_status:
                raise ExecCommandFailed(command, self, use_sudo=use_sudo, status_code=status_code, result=result)

        # Return result
        if sandbox:
            return '<Not sure in sandbox>'
        else:
            return result

    def _get_session(self):
        raise NotImplementedError

    def _read_non_interactive(self, channel):
        """ Read data from channel and return output. """
        raise NotImplementedError

    def start_interactive_shell(self, command=None, initial_input=None):
        """
        Start an interactive bash shell.
        """
        raise NotImplementedError

    def _posix_shell(self, chan, raw=True, initial_input=None):
        """
        Create a loop which redirects sys.stdin/stdout into this channel.
        The loop ends when channel.recv() returns 0.

        Code inspired by the Paramiko interactive demo.
        """
        result = []
        password_sent = False

        # Set terminal in raw mode
        if raw:
            context = raw_mode(self.pty.stdin)
        else:
            context = contextlib.nested()

        assert self.pty.set_ssh_channel_size
        with context:
            # Make channel non blocking.
            chan.settimeout(0.0)

            # When initial input has been given, send this first
            if initial_input:
                time.sleep(0.2) # Wait a very short while for the channel to be initialized, before sending.
                chan.send(initial_input)

            reading_from_stdin = True

            # Read/write loop
            while True:
                # Don't wait for any input when an exit status code has been
                # set already. (But still wait for the output to finish.)
                if chan.status_event.isSet():
                    reading_from_stdin = False

                channels = [self.pty.stdin, chan] if reading_from_stdin else [chan]
                r, w, e = select(channels, [], [])

                # Receive stream
                if chan in r:
                    try:
                        x = chan.recv(1024)

                        # Received length 0 -> end of stream
                        if len(x) == 0:
                            break

                        # Write received characters to stdout and flush
                        while True:
                            try:
                                self.pty.stdout.write(x)
                                break
                            except IOError as e:
                                # Sometimes, when we have a lot of output, we get here:
                                # IOError: [Errno 11] Resource temporarily unavailable
                                # Just waiting a little, and retrying seems to work.
                                # See also: deployer.run.socket_client for a similar issue.
                                time.sleep(0.2)

                        self.pty.stdout.flush()

                        # Also remember received output.
                        # We want to return what's written to stdout.
                        result.append(x)

                        # Do we need to send the sudo password? (It's when the
                        # magic prompt has been detected in the stream) Note
                        # that we only monitor the last part of 'result', it's
                        # a bit fuzzy, but works.
                        if not password_sent and self.magic_sudo_prompt in ''.join(result[-32:]):
                            chan.send(self.password)
                            chan.send('\n')
                            password_sent = True
                    except socket.timeout:
                        pass

                # Send stream (one by one character)
                # (use 'elif', read stdin only when there is no more output to be received.)
                elif self.pty.stdin in r:
                    try:
                        # Make stdin non-blocking. (The select call already
                        # blocked for us, we want sys.stdin.read() to read
                        # as many bytes as possible without blocking.)
                        try:
                            fdesc.setNonBlocking(self.pty.stdin)
                            x = self.pty.stdin.read(1024)
                        finally:
                            # Set stdin blocking again
                            # (Writing works better in blocking mode.
                            # Especially OS X seems to be very sensitive if we
                            # write lange amounts [>1000 bytes] nonblocking to
                            # stdout. That causes a lot of IOErrors.)
                            fdesc.setBlocking(self.pty.stdin)

                        # We receive \n from stdin, but \r is required to
                        # send. (Until now, the only place where the
                        # difference became clear is in redis-cli, which
                        # only accepts \r as confirmation.)
                        x = x.replace('\n', '\r')
                    except IOError as e:
                        # What to do with IOError exceptions?
                        # (we see what happens in the next select-call.)
                        continue

                    # Received length 0
                    # There's no more at stdin to read.
                    if len(x) == 0:
                        # However, we should go on processing the input
                        # from the remote end, until the process finishes
                        # there (because it was done or processed Ctrl-C or
                        # Ctrl-D/EOF.)
                        #
                        # The end of the input stream happens when we are
                        # using StringIO at the client side, and we're not
                        # attached to a real pseudo terminal. (For
                        # unit-testing, or background commands.)
                        reading_from_stdin = False
                        continue

                    # Write to channel
                    chan.send(x)

                    # Not sure about this. Sometimes, when pasting large data
                    # in the command line, the many concecutive read or write
                    # commands will make Paramiko hang somehow...  (This was
                    # the case, when still using a blocking pty.stdin.read(1)
                    # instead of a non-blocking readmany.
                    time.sleep(0.01)

            return ''.join(result)

    # =====[ SFTP operations ]====

    def _expand_local_path(self, path):
        # Only tilde expansion
        return os.path.expanduser(path)

    def _expand_tilde(self, relative_path):
        raise NotImplementedError

    def expand_path(self, path):
        raise NotImplementedError

    def _tempfile(self):
        """ Return temporary filename """
        return self.expand_path('~/deployer-tempfile-%s-%s' % (time.time(), random.randint(0, 1000000)))

    def get_file(self, remote_path, local_path, use_sudo=False, sandbox=False):
        """
        Download this remote_file.
        """
        with self.open(remote_path, 'rb', use_sudo=use_sudo, sandbox=sandbox) as f:
            # Expand paths
            local_path = self._expand_local_path(local_path)

            with open(local_path, 'wb') as f2:
                f2.write(f.read()) # TODO: read/write in chunks and print progress bar.

    def put_file(self, local_path, remote_path, use_sudo=False, sandbox=False):
        """
        Upload this local_file to the remote location.
        """
        with self.open(remote_path, 'wb', use_sudo=use_sudo, sandbox=sandbox) as f:
            # Expand paths
            local_path = self._expand_local_path(local_path)

            with open(local_path, 'rb') as f2:
                f.write(f2.read())

    def stat(self, remote_path):
        raise NotImplementedError

    def listdir(self, path='.'):
        raise NotImplementedError

    def listdir_stat(self, path='.'):
        """
        Return a list of :class:`.Stat` instances for each file in this directory.
        """
        raise NotImplementedError

    def _open(self, remote_path, mode):
        raise NotImplementedError

    def open(self, remote_path, mode="rb", use_sudo=False, sandbox=False):
        """
        Open file handler to remote file. Can be used both as:

        ::

            with host.open('/path/to/somefile', 'wb') as f:
                f.write('some content')

        or:

        ::

            host.open('/path/to/somefile', 'wb').write('some content')
        """
        # Expand path
        remote_path = os.path.normpath(os.path.join(self.getcwd(), self.expand_path(remote_path)))

        class RemoteFile(object):
            def __init__(rf):
                rf._is_open = False

                # Log entry
                self._log_entry = self.logger.log_file(self, mode=mode, remote_path=remote_path,
                                                use_sudo=use_sudo, sandboxing=sandbox)
                self._log_entry.__enter__()

                if sandbox:
                    # Use dummy file in sandbox mode.
                    rf._file = open('/dev/null', mode)
                else:
                    if use_sudo:
                        rf._temppath = self._tempfile()

                        if self.exists(remote_path):
                            # Copy existing file to available location
                            self._run_silent_sudo("cp '%s' '%s' " % (esc1(remote_path), esc1(rf._temppath)))
                            self._run_silent_sudo("chown '%s' '%s' " % (esc1(self.username), esc1(rf._temppath)))
                            self._run_silent_sudo("chmod u+r,u+w '%s' " % esc1(rf._temppath))

                        elif mode.startswith('w'):
                            # Create empty tempfile for writing (without sudo,
                            # using current username)
                            self._run_silent("touch '%s' " % esc1(rf._temppath))
                        else:
                            raise IOError('Remote file: "%s" does not exist' % remote_path)

                        # Open stream to this temp file
                        rf._file = self._open(rf._temppath, mode)
                    else:
                        rf._file = self._open(remote_path, mode)

                rf._is_open = True

            def __enter__(rf):
                return rf

            def __exit__(rf, *a, **kw):
                # Close file at the end of the with-statement
                rf.close()

            def __del__(rf):
                # Close file when this instance is gargage collected.
                # (When open(...).write(...) is used.)
                rf.close()

            def read(rf, size=-1):
                if rf._is_open:
                    # Always read in chunks of 1024 bytes and show a progress bar.

                    # Create progress bar.
                    p = Console(self.pty).progress_bar('Downloading data',
                            expected=(size if size >= 0 else None))
                    result = StringIO()

                    with p:
                        while True:
                            if size == 0:
                                break
                            elif size < 0:
                                # If we have to read until EOF, keep reaeding
                                # in chunks of 1024
                                chunk = rf._file.read(1024)
                            else:
                                # If we have to read for a certain size, read
                                # until we reached that size.
                                read_size = min(1024, size)
                                chunk = rf._file.read(read_size)
                                size -= len(chunk)

                            if not chunk: break # EOF
                            result.write(chunk)
                            p.set_progress(result.len)

                    return result.getvalue()
                else:
                    raise IOError('Cannot read from closed remote file')

            def readline(rf):
                if rf._is_open:
                    return rf._file.readline()
                else:
                    raise IOError('Cannot read from closed remote file')

            def write(rf, data):
                if rf._is_open:
                    # On some hosts, Paramiko blocks when writing more than
                    # 1180 bytes at once. Not sure about the reason or the
                    # exact limit, but using chunks of 1024 seems to work
                    # well. (and that way we can visualise our progress bar.)

                    # Create progress bar.
                    size=len(data)
                    p = Console(self.pty).progress_bar('Uploading data', expected=size)

                    with p:
                        if len(data) > 1024:
                            while data:
                                p.set_progress(size - len(data), rewrite=False) # Auto rewrite
                                rf._file.write(data[:1024])
                                data = data[1024:]
                        else:
                            rf._file.write(data)
                        p.set_progress(size, rewrite=True)
                else:
                    raise IOError('Cannot write to closed remote file')

            def close(rf):
                if rf._is_open:
                    try:
                        rf._file.close()

                        if not sandbox:
                            if use_sudo:
                                # Restore permissions (when this file already existed.)
                                if self.exists(remote_path):
                                    self._run_silent_sudo("chown --reference='%s' '%s' " % (esc1(remote_path), esc1(rf._temppath)))
                                    self._run_silent_sudo("chmod --reference='%s' '%s' " % (esc1(remote_path), esc1(rf._temppath)))

                                # Move tempfile back in place
                                self._run_silent_sudo("mv '%s' '%s' " % (esc1(rf._temppath), esc1(remote_path)))

                            # chmod?
                            # TODO
                    except Exception as e:
                        self._log_entry.complete(False)
                        raise e
                    else:
                        self._log_entry.complete(True)

                self._log_entry.__exit__()
                rf._is_open=False

        return RemoteFile()


    # Some simple wrappers for the commands

    def sudo(self, *args, **kwargs):
        """sudo(command, use_sudo=False, sandbox=False, interactive=True, user=None, ignore_exit_status=False, initial_input=None, silent=False)

        Wrapper around :func:`~deployer.host.base.Host.run` which uses ``sudo``.
        """
        kwargs['use_sudo'] = True
        return self.run(*args, **kwargs)

    def _run_silent(self, command, **kw):
        kw['interactive'] = False
        kw['silent'] = True
        return self.run(command, **kw)

    def _run_silent_sudo(self, command, **kw):
        kw['interactive'] = False
        kw['use_sudo'] = True
        kw['silent'] = True
        return self.run(command, **kw)

########NEW FILE########
__FILENAME__ = local
import getpass
import os
import pexpect
from functools import wraps

from deployer.console import Console
from deployer.exceptions import ExecCommandFailed

from .base import Host, Stat

__all__ = (
    'LocalHost',
)

class LocalStat(Stat):
    """
    Stat info for local files.
    """
    pass


# Global variable for localhost sudo password cache.
_localhost_password = None
_localhost_start_path = os.getcwd()


class LocalHost(Host):
    """
    ``LocalHost`` can be used instead of :class:`SSHHost` for local execution.
    It uses ``pexpect`` underneat.
    """
    slug = 'localhost'
    address = 'localhost'
    start_path = os.getcwd()

    def run(self, *a, **kw):
        if kw.get('use_sudo', False):
            self._ensure_password_is_known()
        return Host.run(self, *a, **kw)

    def _expand_tilde(self, relative_path):
        return os.path.expanduser(relative_path)

    def expand_path(self, path):
        return os.path.expanduser(path) # TODO: expansion like with SSHHost!!!!

    def _ensure_password_is_known(self):
        # Make sure that we know the localhost password, before running sudo.
        global _localhost_password
        tries = 0

        while _localhost_password is None:
            _localhost_password = Console(self.pty).input('[sudo] password for %s at %s' %
                        (self.username, self.slug), is_password=True)

            # Check password
            try:
                Host._run_silent_sudo(self, 'ls > /dev/null')
            except ExecCommandFailed:
                print 'Incorrect password'
                self._backend.password = None

                tries += 1
                if tries >= 3:
                    raise Exception('Incorrect password')

    @property
    def password(self):
        return _localhost_password

    @property
    def username(self):
        return getpass.getuser()

    def get_start_path(self):
        return _localhost_start_path

    def get_ip_address(self, interface='eth0'):
        # Just return '127.0.0.1'. Laptops are often only connected
        # on wlan0, and looking for eth0 would return an empty string.
        return '127.0.0.1'

    def _get_session(self): # TODO: choose a better API, then paramiko's.
        """
        Return a channel through which we can execute commands.
        It will reserve a pseudo terminal and attach the process
        during exec_command.
        NOTE: The Channel class is actually just made API-compatible
        with the result of Paramiko's transport.open_session()
        """
        # See:
        # http://mail.python.org/pipermail/baypiggies/2010-October/007027.html
        # http://cr.yp.to/docs/selfpipe.html
        class channel(object):
            def __init__(self):
                self._spawn = None
                self._height, self._width = None, None

                # pexpect.spawn sets by default a winsize of 24x80,
                # we want to get the right size immediately.
                class spawn_override(pexpect.spawn):
                    def setwinsize(s, rows=None, cols=None):
                        # Note: This could throw an obscure "close failed in
                        # file object destructor: IOERROR" if we called this
                        # with None values. (We shouldn't do that, but not sure
                        # why it happens.)
                        w = self._width or cols
                        h = self._height or rows
                        if w and h:
                            pexpect.spawn.setwinsize(s, h, w)
                self.spawn_override = spawn_override

            def get_pty(self, term=None, width=None, height=None):
                self.resize_pty(width=width, height=height)

            def recv(self, count=1024):
                try:
                    return self._spawn.read_nonblocking(count)
                except pexpect.EOF:
                    return ''

            def read(self):
                """ Read all blocking. """
                return self._spawn.read()

            def send(self, data):
                return self._spawn.write(data)

            def fileno(self):
                return self._spawn.child_fd

            def resize_pty(self, width=None, height=None):
                self._width, self._height = width, height

                if self._spawn and self._height and self._width:
                    self._spawn.setwinsize(self._height, self._width)

            def exec_command(self, command):
                self._spawn = self.spawn_override('/bin/bash', ['-c', command])#, cwd='/')

                if self._spawn and self._height and self._width:
                    self._spawn.setwinsize(self._height, self._width)

            def recv_exit_status(self):
                # We need to call close() before retreiving the exitstatus of
                # a pexpect spawn.
                self._spawn.close()
                return self._spawn.exitstatus

            # Just for Paramiko's SSH channel compatibility

            def settimeout(self, *a, **kw):
                pass

            @property
            def status_event(self):
                class event(object):
                    def isSet(self):
                        return False
                return event()

        return channel()

    def _open(self, remote_path, mode):
        # Use the builtin 'open'
        return open(remote_path, mode)

    @wraps(Host.stat)
    def stat(self, path):
        try:
            full_path = os.path.join(self.getcwd(), path)
            filename = os.path.split(full_path)[1]
            return LocalStat(os.stat(full_path), filename)
        except OSError as e:
            # Turn OSError in IOError.
            # Paramiko also throws IOError when doing stat calls on remote files.
            # (OSError is only for local system calls and cannot be generalized.)
            raise IOError(e.message)

    @wraps(Host.listdir)
    def listdir(self, path='.'):
        return os.listdir(os.path.join(* [self.getcwd(), path]))

    @wraps(Host.listdir_stat)
    def listdir_stat(self, path='.'):
        return [ self.stat(f) for f in self.listdir() ]

    def _read_non_interactive(self, chan):
        return chan.read()

        # XXX: this was the old way of reading non interactive from a local command.
        #      probably, we can delete this, if the current way has been proven to work
        #      reliable.

        #result = []
        #while True:
        #    # Before calling recv, call select to make sure
        #    # the channel is ready to be read. (Trick for
        #    # getting the SIGCHLD pipe of Localhost to work.)
        #    while True:
        #        r, w, e = select([chan], [], [], 5)
        #        if r:
        #            break
        #        else:
        #            print 'XXX: Select timed out, retrying...', r, w, e

        #    if chan in r:
        #        # Blocking call. Returns when data has been received or at
        #        # the end of the channel stream.
        #        try:
        #            data = chan.recv(1024)
        #        except IOError:
        #            # In case of localhost: application terminated,
        #            # caught in SIGCHLD, and closed slave PTY
        #            break

        #        if data:
        #            result += [data]
        #        else:
        #            break

        #return ''.join(result)


    def start_interactive_shell(self, command=None, initial_input=None):
        """
        Start an interactive bash shell.
        """
        self.run(command='/bin/bash', initial_input=initial_input)

########NEW FILE########
__FILENAME__ = paramiko_connect_patch
"""
Patch for the paramiko SSHClient.connect function.
The only difference is that it calls a progress bar callback.
"""

from paramiko.config import SSH_PORT
from paramiko.util import retry_on_signal
import socket
import getpass

from paramiko.transport import Transport
from paramiko.resource import ResourceManager
from paramiko.ssh_exception import BadHostKeyException


def connect(self, hostname, port=SSH_PORT, username=None, password=None, pkey=None,
            key_filename=None, timeout=None, allow_agent=True, look_for_keys=True,
            compress=False, sock=None, progress_bar_callback=None):
    if not sock:
        progress_bar_callback(1) # Resolving DNS

        for (family, socktype, proto, canonname, sockaddr) in socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            if socktype == socket.SOCK_STREAM:
                af = family
                addr = sockaddr
                break
        else:
            # some OS like AIX don't indicate SOCK_STREAM support, so just guess. :(
            af, _, _, _, addr = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)

        progress_bar_callback(2) # Creating socket
        sock = socket.socket(af, socket.SOCK_STREAM)

        if timeout is not None:
            try:
                sock.settimeout(timeout)
            except:
                pass
        retry_on_signal(lambda: sock.connect(addr))

    progress_bar_callback(3) # Creating transport
    t = self._transport = Transport(sock)
    t.use_compression(compress=compress)
    if self._log_channel is not None:
        t.set_log_channel(self._log_channel)
    t.start_client()
    ResourceManager.register(self, t)

    progress_bar_callback(4) # Exchange keys
    server_key = t.get_remote_server_key()
    keytype = server_key.get_name()

    if port == SSH_PORT:
        server_hostkey_name = hostname
    else:
        server_hostkey_name = "[%s]:%d" % (hostname, port)
    our_server_key = self._system_host_keys.get(server_hostkey_name, {}).get(keytype, None)
    if our_server_key is None:
        our_server_key = self._host_keys.get(server_hostkey_name, {}).get(keytype, None)
    if our_server_key is None:
        # will raise exception if the key is rejected; let that fall out
        self._policy.missing_host_key(self, server_hostkey_name, server_key)
        # if the callback returns, assume the key is ok
        our_server_key = server_key

    if server_key != our_server_key:
        raise BadHostKeyException(hostname, server_key, our_server_key)

    if username is None:
        username = getpass.getuser()

    if key_filename is None:
        key_filenames = []
    elif isinstance(key_filename, (str, unicode)):
        key_filenames = [ key_filename ]
    else:
        key_filenames = key_filename

    progress_bar_callback(5) # Authenticate
    self._auth(username, password, pkey, key_filenames, allow_agent, look_for_keys)

########NEW FILE########
__FILENAME__ = ssh

import StringIO
import os
import paramiko
import threading

from deployer.console import Console
from deployer.exceptions import ConnectionFailedException
from functools import wraps

from .base import Host, Stat

__all__ = (
    'SSHHost',
)


_ssh_backends = { } # Maps Host class to SSHBackend instances.


class SSHBackend(object):
    """
    Manage Paramiko's SSH connection for a Host.

    When multiple instances of the same SSHHost are created, they will all
    share the same backend (this class). Only one ssh connection per host
    will be created, and shared between all threads.
    """
    def __init__(cls, host_cls):
        pass # Leave __init__ empty, use __new__ for this singleton.

    def __new__(cls, host_cls):
        """
        Create singleton SSHBackend
        """
        if host_cls not in _ssh_backends:
            self = object.__new__(cls, host_cls)

            # Initialize
            self._ssh_cache = None
            self._lock = threading.Lock()

            _ssh_backends[host_cls] = self
        return _ssh_backends[host_cls]

    def __del__(self):
        # Terminate Paramiko's SSH thread
        if self._ssh_cache:
            self._ssh_cache.close()
            self._ssh_cache = None

    def get_ssh(self, host):
        """
        Ssh connection. The actual connection to the host is established
        only after the first call of this function.
        """
        # Lock: be sure not to create this connection from several threads at
        # the same time.
        with self._lock:
            if not (self._ssh_cache and self._ssh_cache._transport and self._ssh_cache._transport.is_active()):
                # Create progress bar.
                progress_bar = self._create_connect_progress_bar(host)

                with progress_bar:
                    h = host

                    # Connect
                    self._ssh_cache = paramiko.SSHClient()

                    if not h.reject_unknown_hosts:
                        self._ssh_cache.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                    try:
                        kw = {}

                        if h.config_filename:
                            try:
                                config_file = file(os.path.expanduser(h.config_filename))
                            except IOError:
                                pass
                            else:
                                ssh_config = paramiko.config.SSHConfig()
                                ssh_config.parse(config_file)
                                host_config = ssh_config.lookup(h.address)

                                # Map ssh_config to paramiko config
                                config_map = {
                                        'identityfile': 'key_filename',
                                        'user': 'username',
                                        'port': 'port',
                                        'connecttimeout': 'timeout',
                                        }
                                for ck, pk in config_map.items():
                                    if ck in host_config:
                                        kw[pk] = host_config[ck]

                        if h.port:
                            kw['port'] = h.port
                        if h.username:
                            kw['username'] = h.username
                        if h.timeout:
                            kw['timeout'] = h.timeout

                        # Paramiko's authentication method can be either a public key, public key file, or password.
                        if h.rsa_key:
                            # RSA key
                            rsa_key_file_obj = StringIO.StringIO(h.rsa_key)
                            kw["pkey"] = paramiko.RSAKey.from_private_key(rsa_key_file_obj, h.rsa_key_password)
                        elif h.key_filename:
                            kw["key_filename"] = h.key_filename
                        elif h.password:
                            kw["password"] = h.password

                        # Connect to the SSH server.
                        # We use a patched connect function instead of the connect of paramiko's library,
                        # In order to add the progress bar.
                        from .paramiko_connect_patch import connect as connect_patch
                        kw['progress_bar_callback'] = progress_bar.set_progress

                        #self._ssh_cache.connect = connect_patch
                        connect_patch(self._ssh_cache, h.address, **kw)

                    except (paramiko.SSHException, Exception) as e:
                        self._ssh_cache = None
                        raise ConnectionFailedException('Could not connect to host %s:%s (%s) username=%s\n%s' %
                                        (h.address, h.port, h.slug, h.username, unicode(e)))

            return self._ssh_cache

    def get_sftp(self, host):
        """ Return the paramiko SFTPClient for this connection. """
        transport = self.get_ssh(host).get_transport()
        transport.set_keepalive(host.keepalive_interval)
        sftp = paramiko.SFTPClient.from_transport(transport)

#        # Sometimes, Paramiko his sftp.getcwd() returns an empty path.
#        # Probably, because he doesn't know it yet. By calling chdir('.')
#        # we make sure that we have a path.
#        sftp.chdir('.')

        return sftp

    def _create_connect_progress_bar(self, host):
        from deployer.console import ProgressBarSteps
        console = Console(host.pty)
        return console.progress_bar_with_steps('Connecting %s (%s)' % (host.address, host.slug),
                steps=ProgressBarSteps({
                    1: "Resolving DNS",
                    2: "Creating socket",
                    3: "Creating transport",
                    4: "Exchanging keys",
                    5: "Authenticating" }),
                format_str="%(message)s: %(counter)s/%(expected)s %(status)s")


class SSHStat(Stat):
    """
    Stat info for SSH files.
    """
    pass


class SSHHost(Host):
    """
    SSH Host.

    For the authentication, it's required to provide either a ``password``, a
    ``key_filename`` or ``rsa_key``. e.g.

    ::

        class WebServer(SSHHost):
            slug = 'webserver'
            password = '...'
            address = 'example.com'
            username = 'jonathan'

    """
    # Base host configuration
    reject_unknown_hosts = False

    config_filename = '~/.ssh/config'
    """ SSH config file (optional) """

    key_filename = None
    """ RSA key filename (optional) """

    rsa_key = None
    """ RSA key. (optional) """

    rsa_key_password = None
    """ RSA key password. (optional) """

    address = 'example.com'
    """ SSH Address """

    username = ''
    """ SSH Username """

    port = 22
    """ SSH Port """

    timeout = 10
    """ Connection timeout in seconds.  """

    keepalive_interval  = 30
    """ SSH keep alive in seconds  """

    def __init__(self, *a, **kw):
        self._backend = SSHBackend(self.__class__)
        self._cached_start_path = None
        Host.__init__(self, *a, **kw)

    def _get_session(self):
        transport = self._backend.get_ssh(self).get_transport()
        transport.set_keepalive(self.keepalive_interval)
        chan = transport.open_session()
        return chan

    @wraps(Host.get_start_path)
    def get_start_path(self):
        if self._cached_start_path is None:
            sftp = self._backend.get_sftp(self)
            sftp.chdir('.')
            self._cached_start_path = sftp.getcwd()
        return self._cached_start_path

    def _expand_tilde(self, p):
        """ Do tilde expansion of this (relative) path """
        if p.startswith('~/') or p == '~':
            home = self._backend.get_sftp(self).normalize('.')
            return p.replace('~', home, 1)
        else:
            return p

    def expand_path(self, path):
        # Expand remote path, using the current working directory.
        return os.path.join(self.getcwd(), self._expand_tilde(path))

    @wraps(Host.stat)
    def stat(self, remote_path):
        sftp = self._backend.get_sftp(self)
        sftp.chdir(self.getcwd())

        s = sftp.lstat(remote_path)

        filename = os.path.split(remote_path)[-1]
        return SSHStat(s, filename=filename)

    @wraps(Host.listdir)
    def listdir(self, path='.'):
        sftp = self._backend.get_sftp(self)
        sftp.chdir(self.getcwd())
        return sftp.listdir(path)

    @wraps(Host.listdir_stat)
    def listdir_stat(self, path='.'):
        sftp = self._backend.get_sftp(self)
        sftp.chdir(self.getcwd())
        return [ SSHStat(a, filename=a.filename) for a in sftp.listdir_attr(path) ]

    def _open(self, remote_path, mode):
        return self._backend.get_sftp(self).open(remote_path, mode)

    def _read_non_interactive(self, channel):
        stdout = channel.makefile('rb', -1)
        return stdout.read()

    def start_interactive_shell(self, command=None, initial_input=None, sandbox=False):
        """
        Start /bin/bash and redirect all SSH I/O from stdin and to stdout.
        """
        # Start a new shell using the same dimentions as the current terminal
        height, width = self.pty.get_size()
        chan = self._backend.get_ssh(self).invoke_shell(term=self.pty.get_term_var(), height=height, width=width)

        # Keep size of local pty and remote pty in sync
        def set_size():
            height, width = self.pty.get_size()
            chan.resize_pty(width=width, height=height)
        self.pty.set_ssh_channel_size = set_size

        # Start logger
        with self.logger.log_run(self, command=command, shell=True, sandboxing=sandbox) as log_entry:
            # When a command has been passed, use 'exec' to replace the current
            # shell process by this command
            if command:
                chan.send('exec %s\n' % command)

            # PTY receive/send loop
            self._posix_shell(chan, initial_input=initial_input)

            # Retrieve status code
            status_code = chan.recv_exit_status()
            log_entry.set_status_code(status_code)

            self.pty.set_ssh_channel_size = None

            # Return status code
            return status_code


########NEW FILE########
__FILENAME__ = vagrant
from deployer.host import SSHHost, LocalHost

import os.path


class VagrantHost(SSHHost):
    """
    Virtual machine, created by the Vagrant wrappers.
    http://www.vagrantup.com/

    TOOD:
    - not yet for multiple-vm environments
    - Probably only works when host_machine is Localhost (no ssh proxy.)
    """
    # Directory which contains the Vagrantfile.
    vagrant_environment = '~'

    # Host machine on which the VirtualBox instance in running.
    host_machine = LocalHost


    @property
    def slug(self):
        return 'vagrant-%s' % os.path.split(self.vagrant_environment)[1]

    @property
    def address(self):
        return self._get_ssh_property('HostName')

    @property
    def port(self):
        return int(self._get_ssh_property('Port'))

    @property
    def username(self):
        return self._get_ssh_property('User')

    @property
    def key_filename(self):
        return self._get_ssh_property('IdentityFile')

    def _get_ssh_property(self, key):
        """
        Run "vagrant ssh-config", and retrieve property.
        """
        if not hasattr(self, '_ssh_config'):
            host = self.host_machine()

            with host.cd(self.vagrant_environment):
                self._ssh_config = host._run_silent('vagrant ssh-config')

        for line in self._ssh_config.splitlines():
            k, v = line.strip().split(None, 1)

            if k == key:
                return v

########NEW FILE########
__FILENAME__ = host_container
from contextlib import nested
from deployer.host import Host
from deployer.exceptions import ExecCommandFailed
from deployer.utils import isclass, esc1
from functools import wraps

__all__ = ('HostContainer', 'HostsContainer', )


class HostsContainer(object):
    """
    Proxy to a group of :class:`~deployer.host.base.Host` instances.

    For instance, if you have a role, name 'www' inside the container, you
    could do:

    ::

        host_container.run(...)
        host_container[0].run(...)
        host_container.filter('www')[0].run(...)

    Typically, you get a :class:`~deployer.host_container.HostsContainer` class
    by accessing the :attr:`~deployer.node.base.Env.hosts` property of an
    :class:`~deployer.node.base.Env` (:class:`~deployer.node.base.Node`
    wrapper.)
    """
    def __init__(self, hosts, pty=None, logger=None, is_sandbox=False):
        # the hosts parameter is a dictionary, mapping roles to <Host> instances, or lists
        # of <Host>-instances.
        # e.g. hosts = { 'www': [ <host1>, <host2> ], 'queue': <host3> }
        self._logger = logger
        self._pty = pty
        self._sandbox = is_sandbox

        # Create
        self._hosts = { }

        def get(h):
            # Create host instance if class was given. Otherwise return
            # instance.
            if isclass(h):
                assert issubclass(h, Host)
                return h(pty=pty, logger=logger)
            else:
                assert isinstance(h, Host)
                return h

        for k, v in hosts.items():
            # A value should be a list of Host classes.
            assert isinstance(v, set)
            self._hosts[k] = { get(h) for h in v }

        # Validate hosts. No two host with the same slug can occur in a
        # same role within a container.
        for k, v in hosts.items():
            slugs = { } # Slug -> Host class
            for h in v:
                if h.slug in slugs and h != slugs[h.slug]:
                    raise Exception('Duplicate host slug %s found in HostsContainer.' % h.slug)
                else:
                    slugs[h.slug] = h

    @property
    def _all(self):
        return [ h for v in self._hosts.values() for h in v ]

    @classmethod
    def from_definition(cls, hosts_class, **kw):
        """
        Create a :class:`HostsContainer` from a Hosts class.
        """
        hosts = { }
        for k in dir(hosts_class):
            v = getattr(hosts_class, k)

            if isinstance(v, HostsContainer):
                # This happens when we define Hosts inline in an action, to be
                # initialized, e.g. by initialize_node.
                hosts[k] = v.get_hosts()
            elif isclass(v) and issubclass(v, Host):
                hosts[k] = { v }
            elif isinstance(v, (set, tuple)):
                for h in v:
                    assert issubclass(h, Host)
                hosts[k] = { h for h in v }
            elif not k.startswith('_'):
                raise TypeError('Invalid attribute in host definition %s: %r=%r' % (hosts_class, k, v))

        return cls(hosts, **kw)

    def get_hosts(self):
        """
        Return a set of :class:`deployer.host.Host` classes that appear in this
        container.  Each :class:`deployer.host.Host` class will abviously
        appear only once in the set, even when it appears in several roles.
        """
        return { h.__class__ for l in self._hosts.values() for h in l }

    def get_hosts_as_dict(self):
        """
        Return a dictionary which maps all the roles to the set of
        :class:`deployer.host.Host` classes for each role.
        """
        return { k: { h.__class__ for h in l } for k, l in self._hosts.items() }

    def __repr__(self):
        return ('<%s\n' % self.__class__.__name__ +
                ''.join('   %s: [%s]\n' % (r, ','.join(h.slug for h in self.filter(r))) for r in self.roles) +
                '>')

    def __eq__(self, other):
        """
        Return ``True`` when the roles/hosts are the same.
        """
        # We can't do this: host instances are created during initialisation.
        raise NotImplementedError('There is no valid definition for HostsContainer equality.')

    def _new(self, hosts):
        return HostsContainer(hosts, self._pty, self._logger, self._sandbox)

    def _new_1(self, host):
        return HostContainer({ 'host': {host} }, self._pty, self._logger, self._sandbox)

    def __len__(self):
        """
        Returns the amount of :class:`deployer.host.Host` instances in this
        container. If a host appears in several roles, each appearance will be
        taken in account.
        """
        return sum(len(v) for v in self._hosts.values())

    def __nonzero__(self):
        return len(self) > 0

    @property
    def roles(self):
        return sorted(self._hosts.keys())

    def __contains__(self, host):
        """
        Return ``True`` when this host appears in this host container.
        """
        raise Exception('No valid implementation for this...') # XXX

#        assert isinstance(host, (Host, HostContainer))
#
#        if isinstance(host, HostContainer):
#            host = host._host
#        return host.__class__ in self.get_hosts()

    def filter(self, *roles):
        """
        Returns a new HostsContainer instance, containing only the hosts
        matching this filter. The hosts are passed by reference, so if you'd
        call `cd()` on the returned container, it will also effect the hosts in
        this object.

        Examples:

        ::

            hosts.filter('role1', 'role2')
        """
        assert all(isinstance(r, basestring) for r in roles), TypeError('Unknown host filter %r' % roles)

        return self._new({ r: self._hosts.get(r, set()) for r in roles })

    def __getitem__(self, index):
        """
        Mostly for backwards-compatibility.

        You can use the [0] index operation, but as a HostContainer contains a
        set of hosts, there is no definition of the 'first' host in a set, so
        you shouldn't trust the order, and you shouldn't rely on the fact that it'll
        be always the same host that will be returned.
        This can be useful if you want to retrieve a value from one node in an
        array, but when it's not important which one.


        :returns: :class:`HostContainer`;
        """
        if index != 0:
            raise Exception('Only [0] index operation is allowed on HostsContainer instance.')

        hosts = list(self._all)

        if len(hosts) == 0:
            raise IndexError

        return self._new_1(hosts[index])

    def __iter__(self):
        for h in self._all:
            yield self._new_1(h)

    def expand_path(self, path):
        return [ h.expand_path(path) for h in self._all ]

    def run(self, *a, **kw):
        """run(command, sandbox=False, interactive=True, user=None, ignore_exit_status=False, initial_input=None)

        Call :func:`~deployer.host.base.Host.run` with this parameters on every
        :class:`~deployer.host.base.Host` in this container. It can be executed
        in parallel when we have multiple hosts.

        :returns: An array of all the results.
        """
        # First create a list of callables
        def closure(host):
            def call(pty):
                assert pty

                kw2 = dict(**kw)
                kw2.setdefault('sandbox', self._sandbox)

                new_host = host.copy(pty=pty)
                return new_host.run(*a, **kw2)
            return call

        callables = map(closure, self._all)

        # When addressing multiple hosts and auxiliary ptys are available,
        # do a parallel run.
        if len(callables) > 1 and self._pty.auxiliary_ptys_are_available:
            # Run in auxiliary ptys, wait for them all to finish,
            # and return result.
            print 'Forking to %i pseudo terminals...' % len(callables)

            # Wait for the forks to finish
            fork_result = self._pty.run_in_auxiliary_ptys(callables)
            fork_result.join()
            result = fork_result.result

            # Return result.
            print ''.join(result) # (Print it once more in the main terminal, not really sure whether we should do that.)
            return result

        # Otherwise, run all serially.
        else:
            return [ c(self._pty) for c in callables ]

    def sudo(self, *args, **kwargs):
        """sudo(command, sandbox=False, interactive=True, user=None, ignore_exit_status=False, initial_input=None)

        Call :func:`~deployer.host.base.Host.sudo` with this parameters on every
        :class:`~deployer.host.base.Host` in this container. It can be executed
        in parallel when we have multiple hosts.

        :returns: An array of all the results.
        """
        kwargs['use_sudo'] = True
        return HostsContainer.run(self, *args, **kwargs)
                    # NOTE: here we use HostsContainer instead of self, to be
                    #       sure that we don't call te overriden method in
                    #       HostContainer.

    def prefix(self, command):
        """
        Call :func:`~deployer.host.base.HostContext.prefix` on the
        :class:`~deployer.host.base.HostContext` of every host.

        ::

            with host.prefix('workon environment'):
                host.run('./manage.py migrate')
        """
        return nested(* [ h.host_context.prefix(command) for h in self._all ])

    def cd(self, path, expand=False):
        """
        Execute commands in this directory. Nesting of cd-statements is
        allowed.

        Call :func:`~deployer.host.base.HostContext.cd` on the
        :class:`~deployer.host.base.HostContext` of every host.

        ::

            with host_container.cd('directory'):
                host_container.run('ls')
        """
        return nested(* [ h.host_context.cd(path, expand=expand) for h in self._all ])

    def env(self, variable, value, escape=True):
        """
        Sets an environment variable.

        This calls :func:`~deployer.host.base.HostContext.env` on the
        :class:`~deployer.host.base.HostContext` of every host.

        ::

            with host_container.cd('VAR', 'my-value'):
                host_container.run('echo $VAR')
        """
        return nested(* [ h.host_context.env(variable, value, escape=escape) for h in self._all ])

    def getcwd(self):
        """ Calls :func:`~deployer.host.base.Host.getcwd` for every host and return the result as an array. """
        return [ h._host.getcwd() for h in self ]

    #
    # Commands
    # (these don't need sandboxing.)
    #
    def exists(self, filename, use_sudo=True):
        """
        Returns an array of boolean values that represent whether this a file
        with this name exist for each host.
        """
        def on_host(container):
            return container._host.exists(filename, use_sudo=use_sudo)

        return map(on_host, self)

    def has_command(self, command, use_sudo=False):
        """
        Test whether this command can be found in the bash shell, by executing a 'which'
        """
        def on_host(container):
            try:
                container.run("which '%s'" % esc1(command), use_sudo=use_sudo,
                                interactive=False, sandbox=False)
                return True
            except ExecCommandFailed:
                return False

        return map(on_host, self)

    @property
    def hostname(self): # TODO: Deprecate!!!
        with self.cd('/'):
            return self.run('hostname', sandbox=False).strip()

    @property
    def is_64_bit(self): # TODO: deprecate!!!
        with self.cd('/'):
            return 'x86_64' in self._run_silent('uname -m', sandbox=False)


class HostContainer(HostsContainer):
    """
    Similar to :class:`~deployer.host_container.HostsContainer`, but wraps only
    around exactly one :class:`~deployer.host.base.Host`.
    """
    @property
    def _host(self):
        """
        This host container has only one host.
        """
        assert len(self) == 1, AssertionError('Found multiple hosts in HostContainer')
        return self._all[0]

    @property
    def slug(self):
        return self._host.slug

    @wraps(Host.get_file)
    def get_file(self, *args, **kwargs):
        kwargs['sandbox'] = self._sandbox
        return self._host.get_file(*args, **kwargs)

    @wraps(Host.put_file)
    def put_file(self, *args, **kwargs):
        kwargs['sandbox'] = self._sandbox
        return self._host.put_file(*args, **kwargs)

    @wraps(Host.open)
    def open(self, *args, **kwargs):
        kwargs['sandbox'] = self._sandbox
        return self._host.open(*args, **kwargs)

    @wraps(HostsContainer.run)
    def run(self, *a, **kw):
        return HostsContainer.run(self, *a, **kw)[0]

    @wraps(HostsContainer.sudo)
    def sudo(self, *a, **kw):
        return HostsContainer.sudo(self, *a, **kw)[0]

    @wraps(HostsContainer.getcwd)
    def getcwd(self):
        return HostsContainer.getcwd(self)[0]

    def start_interactive_shell(self, command=None, initial_input=None):
        if not self._sandbox:
            return self._host.start_interactive_shell(command=command, initial_input=initial_input)
        else:
            print 'Interactive shell is not available in sandbox mode.'

    def __getattr__(self, name):
        """
        Proxy to the Host object. Following commands can be
        accessed when this hostcontainer contains exactly one host.
        """
        return getattr(self._host, name)

    @wraps(HostsContainer.expand_path)
    def expand_path(self, *a, **kw):
        return HostsContainer.expand_path(self, *a, **kw)[0]

    def exists(self, filename, use_sudo=True):
        """
        Returns ``True`` when this file exists on the hosts.
        """
        return HostsContainer.exists(self, filename, use_sudo=use_sudo)[0]

    def has_command(self, command, use_sudo=False):
        """
        Test whether this command can be found in the bash shell, by executing
        a ``which`` Returns ``True`` when the command exists.
        """
        return HostsContainer.has_command(self, command, use_sudo=use_sudo)[0]

########NEW FILE########
__FILENAME__ = filters
"""
Filters for NodeIterator
------------------------

``NodeIterator`` is the iterator that ``Inspector.walk()`` returns. It supports
filtering to limit the yielded nodes according to certain conditions.

A filter is a ``Filter`` instance or an AND or OR operation of several
filters. For instance:

::

    from deployer.inspection.filters import HasAction, PublicOnly
    Inspector(node).walk(HasAction('my_action') & PublicOnly & ~ InGroup(Staging))
"""

__all__ = (
        'Filter',
        'PublicOnly',
        'PrivateOnly',
        'IsInstance',
        'HasAction',
        'InGroup',
)

from deployer.groups import Group


class Filter(object):
    """
    Base class for ``Inspector.walk`` filters.
    """
    def _filter(self, node):
        raise NotImplementedError

    def __and__(self, other_filter):
        return AndFilter(self, other_filter)

    def __or__(self, other_filter):
        return OrFilter(self, other_filter)

    def __invert__(self):
        return NotFilter(self)


class AndFilter(Filter):
    def __init__(self, filter1, filter2):
        self.filter1 = filter1
        self.filter2 = filter2

    def _filter(self, node):
        return self.filter1._filter(node) and self.filter2._filter(node)

    def __repr__(self):
        return '%r & %r' % (self.filter1, self.filter2)


class OrFilter(Filter):
    def __init__(self, filter1, filter2):
        self.filter1 = filter1
        self.filter2 = filter2

    def _filter(self, node):
        return self.filter1._filter(node) or self.filter2._filter(node)

    def __repr__(self):
        return '%r | %r' % (self.filter1, self.filter2)


class NotFilter(Filter):
    def __init__(self, filter1):
        self.filter1 = filter1

    def _filter(self, node):
        return not self.filter1._filter(node)

    def __repr__(self):
        return '~ %r' % self.filter1


class _PublicOnly(Filter):
    def _filter(self, node):
        return not (node._node_name and node._node_name.startswith('_'))

    def __repr__(self):
        return 'PublicOnly'

PublicOnly = _PublicOnly()
"""
Filter on public nodes.
"""


class _PrivateOnly(Filter):
    def _filter(self, node):
        return node._node_name and node._node_name.startswith('_')

    def __repr__(self):
        return 'PrivateOnly'

PrivateOnly = _PrivateOnly()
"""
Filter on private nodes.
"""


class IsInstance(Filter):
    """
    Filter on the nodes which are an instance of this ``Node`` class.

    :param node_class: A :class:`deployer.node.Node` subclass.
    """
    def __init__(self, node_class):
        self.node_class = node_class

    def _filter(self, node):
        return isinstance(node, self.node_class)

    def __repr__(self):
        return 'IsInstance(%r)' % self.node_class


class HasAction(Filter):
    """
    Filter on the nodes which implement this action.
    """
    def __init__(self, action_name):
        self.action_name = action_name

    def _filter(self, node):
        from deployer.inspection.inspector import Inspector
        return Inspector(node).has_action(self.action_name)

    def __repr__(self):
        return 'HasAction(%r)' % self.action_name


class InGroup(Filter):
    """
    Filter nodes that are in this group.

    :param group: A :class:`deployer.groups.Group` subclass.
    """
    def __init__(self, group):
        assert issubclass(group, Group)
        self.group = group

    def _filter(self, node):
        from deployer.inspection.inspector import Inspector
        return Inspector(node).get_group() == self.group

    def __repr__(self):
        return 'InGroup(%r)' % self.group

########NEW FILE########
__FILENAME__ = inspector
"""
Inspector
---------

Reflexion/introspection on a `deployer.node.Node`
"""

from deployer.node import Node, Env, IsolationIdentifierType, iter_isolations, Action
from deployer.groups import Group
from deployer.inspection import filters
from functools import wraps

__all__ = (
        'PathType',
        'Inspector',
)


class PathType:
    """
    Types for displaying the ``Node`` address in a tree.
    It's an options for Inspector.get_path()
    """

    NAME_ONLY = 'NAME_ONLY'
    """
    A list of names.
    """

    NODE_AND_NAME = 'NODE_AND_NAME'
    """
    A list of ``(Node, name)`` tuples.
    """

    NODE_ONLY = 'NODE_ONLY'
    """
    A list of nodes.
    """


class Inspector(object):
    """
    Introspection of a ``Node`` instance.
    """
    def __init__(self, node):
        if isinstance(node, Env):
            self.env = node
            self.node = node._node
            self.__class__ = _EnvInspector
        elif isinstance(node, Node):
            self.env = None
            self.node = node
        else:
            raise Exception('Expecting a Node or Env instance')

    def __repr__(self):
        return 'Inspector(node=%s)' % self.node.__class__.__name__

    @property
    def is_isolated(self):
        return self.node._node_is_isolated

    def iter_isolations(self, identifier_type=IsolationIdentifierType.INT_TUPLES):
        return iter_isolations(self.node, identifier_type=identifier_type)

    def get_isolation(self, identifier, identifier_type=IsolationIdentifierType.INT_TUPLES):
        for i, node in self.iter_isolations(identifier_type):
            if i == identifier:
                return node
        raise AttributeError('Isolation not found')

    def _filter(self, include_private, filter):
        childnodes = { }
        for name in dir(self.node.__class__):
            if not name.startswith('__') and name != 'parent':
                if include_private or not name.startswith('_'):
                    attr = getattr(self.node, name)
                    if filter(attr):
                        childnodes[name] = attr
        return childnodes

    def get_childnodes(self, include_private=True, verify_parent=True):
        """
        Return a list of childnodes.

        :param include_private: ignore names starting with underscore.
        :type include_private: bool
        :param verify_parent: check that the parent matches the current node.
        :type verify_parent: bool
        """
        # Retrieve all nodes.
        def f(i):
            return isinstance(i, Node) and (not verify_parent or i.parent == self.node)
        nodes = self._filter(include_private, f).values()

        # Order by _node_creation_counter
        return sorted(nodes, key=lambda n: n._node_creation_counter)

    def has_childnode(self, name):
        """
        Returns ``True`` when this node has a childnode called ``name``.
        """
        try:
            self.get_childnode(name)
            return True
        except AttributeError:
            return False

    def get_childnode(self, name):
        """
        Return the childnode with this name or raise ``AttributeError``.
        """
        for c in self.get_childnodes():
            if Inspector(c).get_name() == name:
                return c
        raise AttributeError('Childnode not found.')

    def get_actions(self, include_private=True):
        """
        Return a list of ``Action`` instances for the actions in this node.

        :param include_private: Include actions starting with an underscore.
        :type include_private: bool
        """
        actions = self._filter(include_private, lambda i: isinstance(i, Action) and
                    not i.is_property and not i.is_query)

        # Order alphabetically.
        return sorted(actions.values(), key=lambda a:a.name)

    def has_action(self, name):
        """
        Returns ``True`` when this node has an action called ``name``.
        """
        try:
            self.get_action(name)
            return True
        except AttributeError:
            return False

    def get_action(self, name):
        """
        Return the ``Action`` with this name or raise ``AttributeError``.
        """
        for a in self.get_actions():
            if a.name == name:
                return a
        raise AttributeError('Action not found.')

    def get_properties(self, include_private=True):
        """
        Return the attributes that are properties.

        This are the members of this node that were wrapped in ``@property``
        :returns: A list of ``Action`` instances.
        """
        # The @property descriptor is in a Node replaced by the
        # node.PropertyDescriptor. This returns an Action object instead of
        # executing it directly.
        actions = self._filter(include_private, lambda i:
                        isinstance(i, Action) and i.is_property)

        # Order alphabetically
        return sorted(actions.values(), key=lambda a:a.name)

    def get_property(self, name):
        """
        Returns the property with this name or raise AttributeError.
        :returns: ``Action`` instance.
        """
        for p in self.get_properties():
            if p.name == name:
                return p
        raise AttributeError('Property not found.')

    def has_property(self, name):
        """
        Returns ``True`` when the attribute ``name`` is a @property.
        """
        try:
            self.get_property(name)
            return True
        except AttributeError:
            return False

    def get_queries(self, include_private=True):
        """
        Return the attributes that are :class:`deployer.query.Query` instances.
        """
        # Internal only. For the shell.
        actions = self._filter(include_private, lambda i:
                    isinstance(i, Action) and i.is_query)

        # Order alphabetically
        return sorted(actions.values(), key=lambda a:a.name)

    def get_query(self, name):
        """
        Returns the Action object that wraps the Query with this name or raise
        AttributeError.

        :returns: An ``Action`` instance.
        """
        for q in self.get_queries():
            if q.name == name:
                return q
        raise AttributeError('Query not found.')

    def has_query(self, name):
        """
        Returns ``True`` when the attribute ``name`` of this node is a Query.
        """
        try:
            self.get_query(name)
            return True
        except AttributeError:
            return False

    def suppress_result_for_action(self, name):
        """
        ``True`` when :func:`deployer.node.suppress_action_result` has been applied to this action.
        """
        return self.get_action(name).suppress_result

    def get_path(self, path_type=PathType.NAME_ONLY):
        """
        Return a (name1, name2, ...) tuple, defining the path from the root until here.

        :param path_type: Path formatting.
        :type path_type: :class:`.PathType`
        """
        result = []
        n = self.node
        while n:
            if path_type == PathType.NAME_ONLY:
                result.append(Inspector(n).get_name())

            elif path_type == PathType.NODE_AND_NAME:
                result.append((n, Inspector(n).get_name()))

            elif path_type == PathType.NODE_ONLY:
                result.append(n)
            else:
                raise Exception('Invalid path_type')

            n = n.parent

        return tuple(result[::-1])

    def get_root(self): # TODO: unittest!!
        """
        Return the root ``Node`` of the tree.
        """
        node = self.node
        while node.parent:
            node = node.parent
        return node

    def get_parent(self): # TODO: unittest!!
        """
        Return the parent ``Node`` or raise ``AttributeError``.
        """
        if self.parent:
            return self.parent
        else:
            raise AttributeError('No parent found. Is this the root node?')

    def get_group(self):
        """
        Return the :class:`deployer.groups.Group` to which this node belongs.
        """
        return self.node.node_group or (
                Inspector(self.node.parent).get_group() if self.node.parent else Group())

    def get_name(self):
        """
        Return the name of this node.

        Note: when a node is nested in a parent node, the name becomes the
        attribute name of this node in the parent.
        """
        return self.node._node_name or self.node.__class__.__name__

    def get_full_name(self): #XXX deprecate!!!
        return self.node.__class__.__name__

    def get_isolation_identifier(self):
        return self.node._node_isolation_identifier

    def is_callable(self):
        """
        Return ``True`` when this node implements ``__call__``.
        """
        return hasattr(self.node, '__call__')

    def _walk(self):
        visited = set()
        todo = [ self.node ]

        def key(n):
            # Unique identifier for every node.
            # (The childnode descriptor will return another instance every time.)
            i = Inspector(n)
            return (i.get_root(), i.get_path())

        while todo:
            n = todo.pop(0)
            yield n
            visited.add(key(n))

            for c in Inspector(n).get_childnodes(verify_parent=False):
                if key(c) not in visited:
                    todo.append(c)

    def walk(self, filter=None):
        """
        Recursively walk (topdown) through the nodes and yield them.

        It does not split ``SimpleNodes`` nodes in several isolations.

        :param filter: A :class:`.filters.Filter` instance.
        :returns: A :class:`NodeIterator` instance.
        """
        return NodeIterator(self._walk).filter(filter)


class _EnvInspector(Inspector):
    """
    When doing the introspection on an Env object, this acts like a proxy and
    makes sure that the result is compatible for in an Env environment.
    """
    def get_childnodes(self, *a, **kw):
        nodes = Inspector.get_childnodes(self, *a, **kw)
        return map(self.env._Env__wrap_node, nodes)

    @wraps(Inspector.get_actions)
    def get_actions(self, *a, **kw):
        return map(self.env._Env__wrap_action, Inspector.get_actions(self, *a, **kw))

    @wraps(Inspector.get_properties)
    def get_properties(self, *a, **kw):
        actions = []
        for a in Inspector.get_properties(self, *a, **kw):
            actions.append(self.env._Env__wrap_action(a, auto_evaluate=False))
        return actions

    @wraps(Inspector.get_queries)
    def get_queries(self, *a, **kw):
        actions = []
        for a in Inspector.get_queries(self, *a, **kw):
            actions.append(self.env._Env__wrap_action(a, auto_evaluate=False))
        return actions

    @wraps(Inspector.get_root)
    def get_root(self): # TODO: unittest
        node = Inspector.get_root(self)
        return self.env._Env__wrap_node(node)

    def iter_isolations(self, *a, **kw):
        for index, node in Inspector.iter_isolations(self, *a, **kw):
            yield index, self.env._Env__wrap_node(node)

    def _walk(self):
        for node in Inspector._walk(self):
            yield self.env._Env__wrap_node(node)

    def trace_query(self, name):
        """
        Execute this query, but return the ``QueryResult`` wrapper instead of
        the actual result. This wrapper contains trace information for
        debugging.
        """
        env_action = self.get_query(name)
        query_result = env_action(return_query_result=True)
        return query_result


class NodeIterator(object):
    """
    Generator object which yields the nodes in a collection.
    """
    def __init__(self, node_iterator_func):
        self._iterator_func = node_iterator_func

    def __iter__(self):
        return self._iterator_func()

    def __len__(self):
        return sum(1 for _ in self)

    def filter(self, filter):
        """
        Apply filter on this node iterator, and return a new iterator instead.
        `filter` should be a Filter instance.
        """
        if filter is not None:
            assert isinstance(filter, filters.Filter)

            def new_iterator():
                for n in self:
                    if filter._filter(n):
                        yield n
            return NodeIterator(new_iterator)
        else:
            return self

    def prefer_isolation(self, index):
        """
        For nodes that are not yet isoleted. (SimpleNodes, or normal Nodes
        nested in there.) yield the isolations with this index.  Otherwise,
        nodes are yielded unmodified.
        """
        def new_iterator():
            for n in self:
                # When this is a SimpleNode, yield only this isolation if it
                # exists.
                if not n._node_is_isolated:
                    try:
                        yield n[index]
                    except KeyError:
                        # TODO: maybe: yield n here. Not 100% sure, whether this is the best.
                        pass
                # Otherwise, just yield the node.
                else:
                    yield n
        return NodeIterator(new_iterator)

    def call_action(self, name, *a, **kw):
        """
        Call a certain action on all the nodes.
        """
        # Note: This will split the SimpleNode Arrays into their isolations.
        for n in self:
            for index, node in Inspector(n).iter_isolations():
                action = getattr(node, name)
                yield action(*a, **kw)

########NEW FILE########
__FILENAME__ = default
from deployer.exceptions import ExecCommandFailed, QueryException
from deployer.loggers import Logger, RunCallback, FileCallback, ForkCallback, Actions
from deployer.exceptions import ActionException
from pygments import highlight
from pygments.formatters import TerminalFormatter as Formatter
from pygments.lexers import PythonTracebackLexer
import sys
import termcolor


class DefaultLogger(Logger):
    """
    The default logger.
    Does only print nice colored logging information in the stdout.
    """
    def __init__(self, stdout=None, print_group=True):
        self._stdout = stdout
                # TODO: wrap this logger into a proxy object which handles the case that the logger socket is closed.
                #       we have that problem sometimes when we write to a named pipe.
                #       (and the other end terminates `cat logfile`.)
        self._group = []
        self.print_group = print_group

    @property
    def stdout(self):
        if self._stdout:
            return self._stdout
        else:
            # If no stdout was given, take what is currently given in
            # sys.stdout. (may be differrent, every time, depending on the
            # thread in which we are logging.)
            return sys.stdout

    def enter_group(self, func_name, *args, **kwargs):
        name = '%s(%s)' % (func_name,
                ', '.join(map(repr, args) + [ '%s=%s' % (k, repr(v)) for k,v in kwargs.items() ]))
        self._group.append(name)

    def leave_group(self):
        self._group.pop()

    def _print(self, *args):
        for a in args:
            self.stdout.write(a)
        self.stdout.flush()

    def _print_start(self, host, command, use_sudo, sandboxing):
        y = lambda msg: termcolor.colored(msg, 'yellow')
        h = lambda msg: termcolor.colored(msg, 'red', attrs=['bold'])

        group = ' >  '.join([ termcolor.colored(g, 'green') for g in self._group ])
        host_str = host.slug

        if use_sudo:
            command = '(sudo) %s' % command

        if sandboxing:
            command = '(sandbox) %s' % command

        if group and self.print_group:
            self.stdout.write('%s\n' % y(group))

        self.stdout.write('%20s ' % h(host_str))
        self.stdout.write('%s\n' % y(command))
        self.stdout.flush()

    def _print_end(self, success):
        self.stdout.write('\033[10000C\033[10D') # Move 1000 columns forward, 10 columns backwards
        self.stdout.write('\x1b[A') # Move cursor one up
        if success:
            self.stdout.write(termcolor.colored('SUCCESS\n', 'green'))
        else:
            self.stdout.write(termcolor.colored('FAILED\n', 'red', 'on_white'))
        self.stdout.flush()

    def log_fork(self, fork_entry):
        self._print(
                termcolor.colored('Forking ', 'green'),
                termcolor.colored('<%s>' % fork_entry.fork_name, 'yellow'),
                termcolor.colored(' in other terminal...\n', 'green'))

        class callback(ForkCallback):
            def __init__(c):
                # For the fork, create a new logger, starting from
                # the same state.
                c.logger = self._get_fork_class()
                c.logger._group = self._group[:]

            def get_fork_logger(c):
                return c.logger
        return callback()

    def _get_fork_class(self):
        return DefaultLogger()

    def log_run(self, run_entry):
        self._print_start(run_entry.host, run_entry.command, run_entry.use_sudo, run_entry.sandboxing)
        return RunCallback(completed=lambda:
            self._print_end(run_entry.status_code == 0))

    def log_file_opened(self, file_entry):
        self._print_start(file_entry.host, {
            Actions.Open: 'Opening file',
            #Actions.Put: 'Uploading file',
            #Actions.Get: 'Downloading file'
            }[ file_entry.entry_type], file_entry.use_sudo, file_entry.sandboxing)

        if file_entry.entry_type == Actions.Open:
            self.stdout.write('  Mode: %s\n' % file_entry.mode)

        if file_entry.local_path:
            self.stdout.write('  Local path: %s\n' % file_entry.local_path)

        if file_entry.remote_path:
            self.stdout.write('  Remote path: %s\n' % file_entry.remote_path)

        self.stdout.flush()

        return FileCallback(file_closed=lambda:
            self._print_end(file_entry.succeeded))

    def log_exception(self, e):
        print_exception(e, self._stdout)

    def log_msg(self, msg):
        self.stdout.write('%s\n' % msg)


class IndentedDefaultLogger(DefaultLogger):
    """
    Another logger which prints only to the given stdout,
    It will indent the output according to the node/action hierarchy.
    """
    tree_color = 'red'
    hostname_color = 'yellow'
    command_color = 'green'

    def __init__(self, stdout=None):
        DefaultLogger.__init__(self, stdout=stdout)
        self._indent = 0

    def enter_group(self, func_name, *args, **kwargs):
        self._print(termcolor.colored('%s(%s)\n' % (func_name,
                ', '.join(map(repr, args) + [ '%s=%s' % (k, repr(v)) for k,v in kwargs.items() ])), self.tree_color))
        self._indent += 1

    def leave_group(self):
        self._indent -= 1

    def _print(self, *args):
        o = []

        o.append(termcolor.colored(u'\u2502 ' * self._indent + u'\u251c ', self.tree_color).encode('utf-8'))
        for a in args:
            o.append(a)

        self.stdout.write(''.join(o))
        self.stdout.flush()

    def _print_start(self, host, command, use_sudo, sandboxing):
        # Remove newlines
        command = command.replace('\n', '\\n')[0:100]
        if len(command) > 80:
            command = command[:80] + '...'

        self._print(
                termcolor.colored(host.slug, self.hostname_color, attrs=['bold']).ljust(40),
                ' ',
                termcolor.colored(' (sandbox) ' if sandboxing else '        '),
                termcolor.colored(' (sudo) ' if use_sudo else '        ',  attrs=['bold']),
                termcolor.colored(command, self.command_color, attrs=['bold']))

    def _print_end(self, success):
        o = []
        o.append('\033[10000C\033[10D') # Move 1000 columns forward, 10 columns backwards
        o.append(
                termcolor.colored('SUCCESS', 'green') if success else
                termcolor.colored('FAILED', 'red'))
        o.append('\n')
        self.stdout.write(''.join(o))
        self.stdout.flush()

    def _get_fork_class(self):
        # Return dummy logger instance.
        return Logger()


def print_exception(exception, stdout):
    """
    Print a nice exception, and inner exceptions.
    """
    e = exception

    def print_exec_failed_exception(e):
        print
        print termcolor.colored('FAILED !!', 'red', attrs=['bold'])
        print termcolor.colored('Command:     ', 'yellow'),
        print termcolor.colored(e.command, 'red', attrs=['bold'])
        print termcolor.colored('Host:        ', 'yellow'),
        print termcolor.colored(e.host.slug, 'red', attrs=['bold'])
        print termcolor.colored('Status code: ', 'yellow'),
        print termcolor.colored(str(e.status_code), 'red', attrs=['bold'])
        print

    def print_query_exception(e):
        print
        print termcolor.colored('FAILED TO EXECUTE QUERY', 'red', attrs=['bold'])
        print termcolor.colored('Node:        ', 'yellow'),
        print termcolor.colored(repr(e.node), 'red', attrs=['bold'])
        print termcolor.colored('Attribute:   ', 'yellow'),
        print termcolor.colored(e.attr_name, 'red', attrs=['bold'])
        print termcolor.colored('Query:       ', 'yellow'),
        print termcolor.colored(repr(e.query), 'red', attrs=['bold'])
        print termcolor.colored('Filename:     ', 'yellow'),
        print termcolor.colored(e.query._filename, 'red', attrs=['bold'])
        print termcolor.colored('Line:        ', 'yellow'),
        print termcolor.colored(e.query._line, 'red', attrs=['bold'])
        print

        if e.inner_exception:
            print_exception(e.inner_exception)

    def print_action_exception(e):
        if isinstance(e.inner_exception, (ExecCommandFailed, QueryException)):
            print_exception(e.inner_exception)
        else:
            print '-'*79
            print highlight(e.traceback, PythonTracebackLexer(), Formatter())
            print '-'*79

    def print_other_exception(e):
        print
        print e
        print

    def print_exception(e):
        if isinstance(e, ActionException):
            print_action_exception(e)
        elif isinstance(e, ExecCommandFailed):
            print_exec_failed_exception(e)
        elif isinstance(e, QueryException):
            print_query_exception(e)
        else:
            print_other_exception(e)

    print_exception(e)

########NEW FILE########
__FILENAME__ = trace
from deployer.loggers import Logger, RunCallback, FileCallback, ForkCallback, Actions
from deployer.utils import indent
import termcolor


class TraceLogger(Logger):
    """
    Log traces inside this class
    For reflextion code.

    After execution, we can retrieve a list of Actions/Groups.
    (where every group can consist of other Actions/Groups.
    """
    def __init__(self):
        self.trace = TraceGroup('root')
        self._group_stack = [ self.trace ]

    @property
    def traces(self):
        return self.trace.items

    @property
    def first_trace(self):
        return self.trace.items[0]

    def enter_group(self, func_name, *args, **kwargs):
        # Nest new group
        new_group = TraceGroup(func_name, *args, **kwargs)

        self._group_stack[-1].items.append(new_group)
        self._group_stack.append(new_group) # Become the new list head.

    def leave_group(self):
        self._group_stack.pop()

    def log_fork(self, fork_entry):
        new_group = TraceFork(fork_entry)
        self._group_stack[-1].items.append(new_group)

        class callback(ForkCallback):
            def get_fork_logger(c):
                logger = TraceLogger()
                logger._group_stack = [ new_group ]
                return logger

            def completed(self):
                new_group.completed = True

        return callback()

    def log_run(self, run_entry):
        self._group_stack[-1].items.append(run_entry)
        return RunCallback()

    def log_file_opened(self, file_entry):
        self._group_stack[-1].items.append(file_entry)
        return FileCallback()


class TraceGroup(object):
    """
    Data structure where a trace log is stored.
    """
    def __init__(self, func_name, *args, **kwargs):
        self.items = []
        self.func_name = func_name
        self.args = args
        self.kwargs = kwargs

    @property
    def all_io(self):
        for item in self.items:
            if isinstance(item, TraceGroup):
                for io in item.all_io:
                    yield io
            elif item.entry_type == Actions.Run:
                yield item.io

class TraceFork(object):
    def __init__(self, fork_entry):
        self.fork_entry = fork_entry
        self.items = []
        self.completed = False

class TracePrinter(object):
    """
    Printer for outputting the trace structure as string.
    (optionally colored)
    """
    property_color = 'green'
    property_color_attrs = ['dark']
    func_color = 'green'
    func_color_attrs = ['bold']
    call_color = 'red'
    call_color_attrs = []
    key_color = 'yellow'
    key_color_attrs = []
    param_color = 'blue'
    param_color_attrs = []

    def __init__(self, trace):
        self.trace = trace

    def _wrap(self, string, outputtype):
        color = getattr(self, outputtype + '_color', 'default')
        attrs = getattr(self, outputtype + '_color_attrs', [])
        return termcolor.colored(string, color, attrs=attrs)

    def print_color(self):
        if '.property' in self.trace.func_name:
            f = lambda string: self._wrap(string, 'property')
        else:
            f = lambda string: self._wrap(string, 'func')

        params = ', '.join(map(repr, self.trace.args) +
                            [ '%s=%s' % (k, repr(v)) for k,v in self.trace.kwargs.items() ])
        if self.trace.items:
            return (f('%s(%s)\n[\n' % (self.trace.func_name, params)) +
                    ''.join([ indent(self._print_item_color(i), prefix='  ') for i in self.trace.items ]) +
                    f(']'))
        else:
            return f('%s(%s)' % (self.trace.func_name, params))

    def _print_item_color(self, item):
        c = lambda string: self._wrap(string, 'call')
        k = lambda string: self._wrap(string, 'key')
        p = lambda string: self._wrap(string, 'param')


        if isinstance(item, TraceGroup):
            return TracePrinter(item).print_color()

        elif isinstance(item, TraceFork):
            return (
                    c(u'fork') +
                    k(u'(') + p(item.fork_name) + k(u') {\n') +
                    TracePrinter(item).print_color() +
                    k(u'\n}'))
        elif item.entry_type == Actions.Run:
            return (
                    c(u'sandbox' if item.sandboxing else u'run') +
                    k(u'{\n host: ') + p(item.host.slug) +
                    k(u',\n sudo: ') + p(str(item.use_sudo)) +
                    k(u',\n command: ') + p(item.command) +
                    k(u',\n status_code: ') + p(item.status_code) +
                    k(u'\n}'))

        elif item.entry_type == Actions.Open:
            return (
                    c('open') +
                    k(u'{\n host: ') + p(item.host.slug) +
                    k(u',\n sudo: ') + p(item.use_sudo) +
                    k(u',\n mode: ') + p(item.mode) +
                    k(u',\n remote: ') + p(item.remote_path) +
                    k(u',\n succeeded: ') + p(item.succeeded) +
                    k(u'\n}'))

########NEW FILE########
__FILENAME__ = base
from deployer.console import Console
from deployer.exceptions import ExecCommandFailed, ActionException
from deployer.groups import Group
from deployer.host import Host
from deployer.host_container import HostsContainer, HostContainer
from deployer.loggers import DummyLoggerInterface
from deployer.node.role_mapping import RoleMapping, ALL_HOSTS, DefaultRoleMapping
from deployer.pseudo_terminal import DummyPty
from deployer.query import Query
from deployer.utils import isclass

from inspect import isfunction

import logging
import traceback
import sys
import os

__all__ = (
    'Action',
    'Env',
    'EnvAction',
    'IsolationIdentifierType',
    'Node',
    'NodeBase',
    'ParallelActionResult',
    'ParallelNode',
    'ParallelNodeBase',
    'SimpleNode',
    'SimpleNodeBase',
    'iter_isolations',
    'required_property',
)


class required_property(property):
    """
    Placeholder for properties which are required when a service is inherit.

    ::

        class MyNode(Node):
            name = required_property()

            def method(self):
                # This will raise an exception, unless this class was
                # inherited, and `name` was filled in.
                print (self.name)
    """
    def __init__(self, description=''):
        self.description = description
        self.name = ''
        self.owner = ''

        def fget(obj):
            raise NotImplementedError('Required property %s of %s is not defined: %s' %
                            (self.name, self.owner, self.description))

        property.__init__(self, fget)


class ChildNodeDescriptor(object):
    """
    Every nested Node class definition in a Node will be wrapped by this
    descriptor. For instance:

    ::

    class ParentNode(Node):
        class ChildNode(Node):
            pass
    """
    def __init__(self, attr_name, node_class):
        self.attr_name = attr_name
        self._node_class = node_class

    def __get__(self, parent_instance, owner):
        """
        When the child node is retrieved from an instance of the parent node, an instance of the child node
        will be returned (and the hosts from the parent are mapped to the child.)
        """
        if parent_instance:
            new_name = '%s.%s' % (owner.__name__, self.attr_name)

            # When The parent is isolated, return an isolated childnode, except if we have an Array.
            isolated = (parent_instance._node_is_isolated and self._node_class._node_type != NodeTypes.SIMPLE_ARRAY)

            # We inherit the class in order to override the name and isolated
            # attributes. However, the creation counter should stay the same,
            # because it's used to track the order of childnodes in the parent.
            class_ = type(new_name, (self._node_class, ), {
                            '_node_is_isolated': isolated,
                            '_node_name': self.attr_name
                            })
            class_._node_creation_counter = self._node_class._node_creation_counter

            return class_(parent=parent_instance)
        else:
            return self._node_class


class QueryDescriptor(object):
    def __init__(self, node_name, attr_name, query):
        self.node_name = node_name
        self.attr_name = attr_name
        self.query = query

    def __get__(self, instance, owner):
        if instance:
            return Action.from_query(self.attr_name, instance, self.query)
        else:
            return self.query


class ActionDescriptor(object):
    """
    Every instancemethod in a Service will be wrapped by this descriptor.
    """
    def __init__(self, attr_name, func):
        self.attr_name = attr_name
        self._func = func

    def __get__(self, node_instance, owner):
        if node_instance:
            return Action(self.attr_name, node_instance, self._func)
        else:
            # Unbound action access. We need this for calling the method of a
            # super class. e.g. Config.action(env, *a...)
            return Action(self.attr_name, None, self._func)


class PropertyDescriptor(object):
    def __init__(self, attr_name, attribute):
        self.attr_name = attr_name
        self.attribute = attribute

    def __get__(self, instance, owner):
        if instance:
            return Action.from_property(self.attr_name, instance, self.attribute.fget)
        else:
            return self.attribute


class Env(object):
    """
    Wraps a :class:`deployer.node.Node` into an executable context.

    ::

        n = Node()
        e = Env(n)
        e.do_action()

    Instead of ``self``, the first parameter of a ``Node``-action will be this
    ``Env`` instance. It acts like a proxy to the ``Node``, but in the meantime
    it takes care of logging, sandboxing, the terminal and context.

    .. note:: Node actions can never be executed directly on the node instance,
              without wrapping it in an Env object first. But if you use the
              :ref:`interactive shell <interactive-shell>`, the shell will do this
              for you.

    :param node: The node that this ``Env`` should wrap.
    :type node: :class:`deployer.node.Node`
    :param pty: The terminal object that wraps the input and output streams.
    :type pty: :class:`deployer.pseudo_terminal.Pty`
    :param logger: (optional) The logger interface.
    :type logger: :class:`deployer.logger.LoggerInterface`
    :param is_sandbox: Run all commands in here in sandbox mode.
    :type is_sandbox: bool
    """
    def __init__(self, node, pty=None, logger=None, is_sandbox=False):
        assert isinstance(node, Node)

        self._node = node
        self._pty = pty or DummyPty()
        self._logger = logger or DummyLoggerInterface()
        self._is_sandbox = is_sandbox

        # When the node is callable (when it has a default action),
        # make sure that this env becomes collable as well.
        if callable(self._node):
            # Per instance overriding
            def call(self, *a, **kw):
                return self.__getattr__('__call__')(*a, **kw)

            self.__class__ = type(self.__class__.__name__, (self.__class__,), { '__call__': call })

        # Create a new HostsContainer object which is identical to the one of
        # the Node object, but add pty/logger/sandbox settings. (So, this
        # doesn't create new Host instances, only a new container.)
        # (do this in this constructor. Each call to Env.hosts should return
        # the same host container instance.)
        self._hosts = HostsContainer(self._node.hosts.get_hosts_as_dict(), pty=self._pty,
                                logger=self._logger, is_sandbox=is_sandbox)

        # Lock Env
        self._lock_env = True

    def __repr__(self):
        return 'Env(%s)' % get_node_path(self._node)

    @classmethod
    def default_from_node(cls, node):
        """
        Create a default environment for this node to run.

        It will be attached to stdin/stdout and commands will be logged to
        stdout. The is the most obvious default to create an ``Env`` instance.

        :param node: :class:`~deployer.node.base.Node` instance
        """
        from deployer.pseudo_terminal import Pty
        from deployer.loggers import LoggerInterface
        from deployer.loggers.default import DefaultLogger

        pty = Pty(stdin=sys.stdin, stdout=sys.stdout, interactive=False,
                term_var=os.environ.get('TERM', ''))

        logger_interface = LoggerInterface()
        logger_interface.attach(DefaultLogger())

        return cls(node, pty=pty, logger=logger_interface, is_sandbox=False)

    def __wrap_action(self, action, auto_evaluate=True):
        """
        Wrap the action in an EnvAction object when it's called from the Env.
        This will make sure that __call__ will run it in this Env environment.

        :param auto_evaluate: Call properties and queries immediately upon retrieval.
                              This is the default behaviour.
        :type auto_evaluate: bool
        """
        assert isinstance(action, Action)
        env_action = EnvAction(self, action)

        if (action.is_property or action.is_query) and auto_evaluate:
            # Properties are automatically called upon retrieval
            return env_action()
        else:
            return env_action

    def initialize_node(self, node_class):
        """
        Dynamically initialize a node from within another node.
        This will make sure that the node class is initialized with the
        correct logger, sandbox and pty settings. e.g:

        :param node_class: A ``Node`` subclass.

        ::

            class SomeNode(Node):
                def action(self):
                    pass

            class RootNode(Node):
                def action(self):
                    # Wrap SomeNode into an Env object
                    node = self.initialize_node(SomeNode)

                    # Use the node.
                    node.action2()
        """
        return self.__wrap_node(node_class())

    def __wrap_node(self, node):
        assert isinstance(node, Node)
        return Env(node, self._pty, self._logger, self._is_sandbox)

    @property
    def hosts(self):
        """
        :class:`deployer.host_container.HostsContainer` instance. This is the
        proxy to the actual hosts.
        """
        return self._hosts

    @property
    def console(self):
        """
        Interface for user input. Returns a :class:`deployer.console.Console`
        instance.
        """
        if not self._pty:
            raise AttributeError('Console is not available in Env when no pty was given.')
        return Console(self._pty)

    def __getattr__(self, name):
        """
        Retrieve attributes from the Node class, but in case of actions and
        childnodes, wrap it in this environment.
        """
        attr = getattr(self._node, name)

        if isinstance(attr, Action):
            return self.__wrap_action(attr)

        elif isinstance(attr, Node):
            return self.__wrap_node(attr)

        else:
            return attr

    def __setattr__(self, name, value):
        # Only allow setting of attributes when the _lock_env flag has not yet been set.
        try:
            locked = object.__getattribute__(self, '_lock_env')
        except AttributeError as e:
            locked = False

        if locked:
            raise AttributeError('Not allowed to change attributes of the node environment. (%s=%r)' % (name, value))
        else:
            super(Env, self).__setattr__(name, value)

    def __iter__(self):
        for node in self._node:
            yield self.__wrap_node(node)

    def __getitem__(self, item):
        return self.__wrap_node(self._node[item])


class NodeTypes:
    NORMAL = 'NORMAL_NODE'
    SIMPLE = 'SIMPLE_NODE'
    SIMPLE_ARRAY = 'SIMPLE_NODE.ARRAY'
    SIMPLE_ONE = 'SIMPLE_NODE.ONE'

class MappingOptions:
    REQUIRED = 'MAPPING_REQUIRED'
    OPTIONAL = 'MAPPING_OPTIONAL'
    NOT_ALLOWED = 'MAPPING_NOT_ALLOWED'


class NodeNestingRules:
    RULES = {
            # Parent - Child
            (NodeTypes.NORMAL, NodeTypes.NORMAL): MappingOptions.OPTIONAL,
            (NodeTypes.NORMAL, NodeTypes.SIMPLE_ARRAY): MappingOptions.REQUIRED,
            (NodeTypes.NORMAL, NodeTypes.SIMPLE_ONE): MappingOptions.REQUIRED,

            (NodeTypes.SIMPLE_ARRAY, NodeTypes.SIMPLE): MappingOptions.OPTIONAL,
            (NodeTypes.SIMPLE_ONE, NodeTypes.SIMPLE): MappingOptions.OPTIONAL,
            (NodeTypes.SIMPLE, NodeTypes.SIMPLE): MappingOptions.OPTIONAL,

            (NodeTypes.SIMPLE, NodeTypes.NORMAL): MappingOptions.OPTIONAL,
            (NodeTypes.SIMPLE_ARRAY, NodeTypes.NORMAL): MappingOptions.OPTIONAL,
            (NodeTypes.SIMPLE_ONE, NodeTypes.NORMAL): MappingOptions.OPTIONAL,
    }
    @classmethod
    def check(cls, parent, child):
        return (parent, child) in cls.RULES

    @classmethod
    def check_mapping(cls, parent, child, has_mapping):
        mapping_option = cls.RULES[(parent, child)]

        if has_mapping:
            return mapping_option in (MappingOptions.OPTIONAL, MappingOptions.REQUIRED)
        else:
            return mapping_option in (MappingOptions.OPTIONAL, MappingOptions.NOT_ALLOWED)


def _internal(func):
    """ Mark this function as internal. """
    func.internal = True
    return func


class NodeBase(type):
    """
    Metaclass for Node. This takes mostly care of wrapping Node members
    into the correct descriptor, but it does some metaclass magic.
    """
    # Keep track of the order in which nodes are created, so that we can
    # retain the order of nested sub nodes. This global variable is
    # increased after every definition of a Node class.
    creation_counter = 0

    @classmethod
    def _preprocess_attributes(cls, attrs, base):
        """
        Do double-underscore preprocessing of attributes.
        e.g.
        `server__ssl_is_enabled = True` will override the `ssl_is_enabled`
        value of the server object in attrs.
        """
        new_attrs = { }
        override = { } # { attr_to_override: { k->v } }

        # Separate real attributes from "nested overrides".
        for k, v in attrs.items():
            if '__' in k and not k.startswith('__'): # Allow name mangling.
                # Split at __ (only split at the first __, type(...) below
                # does it recursively.)
                attr_to_override, key = k.split('__', 1)

                if attr_to_override in override:
                    override[attr_to_override][key] = v
                else:
                    override[attr_to_override] = { key : v }
            else:
                new_attrs[k] = v

        # Now apply overrides.
        for attr, overrides in override.items():
            first_override = overrides.keys()[0]

            if attr in new_attrs:
                raise Exception("Don't override %s__%s property in the same scope." %
                                (attr, first_override))
            elif hasattr(base, attr):
                original_node = getattr(base, attr)

                if not issubclass(original_node, Node):
                    raise Exception('Node override %s__%s is not applied on a Node class.' %
                                    (attr, first_override))
                else:
                    new_attrs[attr] = type(attr, (original_node,), overrides)
            else:
                raise Exception("Couldn't find %s__%s to override." % (attr, first_override))

        return new_attrs

    def __new__(cls, name, bases, attrs):
        # No multiple inheritance allowed.
        if len(bases) > 1:
            # Not sure whether this is a good idea or not, it might be not that bad...
            raise Exception('No multiple inheritance allowed for Nodes')

        # Preprocess __ in attributes
        attrs = cls._preprocess_attributes(attrs, bases[0])

        # Get node type.
        if '_node_type' in attrs:
            node_type = attrs['_node_type']
        else:
            node_type = bases[0]._node_type

        # Do not allow __init__ to be overriden
        if '__init__' in attrs and not getattr(attrs['__init__'], 'internal', False):
            raise TypeError('A Node should not have its own __init__ function.')

        # Verify that nobody is overriding the 'host' property.
        if 'host' in attrs and (
                not isinstance(attrs['host'], property) or
                not getattr(attrs['host'].fget, '_internal', False)):
            raise TypeError("Please don't override the reserved name 'host' in a Node.")

        if name != 'Node': # TODO: this "!='Node'" may not be completely safe...
            # Replace actions/childnodes/properties by descriptors
            for attr_name, attr in attrs.items():
                wrapped_attribute = cls._wrap_attribute(attr_name, attr, name, node_type)
                attrs[attr_name] = wrapped_attribute

                if isfunction(attr):
                    # Create aliases
                    if hasattr(attr, 'action_alias'):
                        for a in attr.action_alias:
                            attrs[a] = cls._wrap_attribute(a, attr, name, node_type)

        # Set creation order
        attrs['_node_creation_counter'] = cls.creation_counter
        cls.creation_counter += 1

        # Create class
        return type.__new__(cls, name, bases, attrs)

    @classmethod
    def _wrap_attribute(cls, attr_name, attribute, node_name, node_type):
        """
        Wrap a Node attribute into the correct descriptor class.
        """
        # The Hosts definition (should be a Hosts class ore RoleMapping)
        if attr_name == 'Hosts':
            # Validate 'Hosts' value
            if not isinstance(attribute, RoleMapping):
                if isclass(attribute):
                    # Try to initialize a HostContainer. If that fails, something is wrong.
                    HostsContainer.from_definition(attribute)
                else:
                    raise Exception('Node.Hosts should be a class definition or a RoleMapping instance.')
            return attribute

        # Wrap functions into an ActionDescriptor
        elif isfunction(attribute) and attr_name not in ('__getitem__', '__iter__', '__new__', '__init__'):
            return ActionDescriptor(attr_name, attribute)

        # Wrap Nodes into a ChildNodeDescriptor
        elif isclass(attribute) and issubclass(attribute, Node):
            # Check the node nesting rules.
            if not NodeNestingRules.check(node_type, attribute._node_type):
                raise Exception('Invalid nesting of %s in %s (%r in %r).' % (
                            attribute._node_type, node_type, attribute, node_name))

            if not NodeNestingRules.check_mapping(node_type, attribute._node_type, bool(attribute.Hosts)):
                raise Exception('The Node-attribute %s of type %s does not have a valid role_mapping.' %
                                            (attr_name, attribute._node_type))


            return ChildNodeDescriptor(attr_name, attribute)

        # Properties should be wrapped again in an Action
        # descriptor
        elif isinstance(attribute, property):
            if isinstance(attribute, required_property):
                attribute.name = attr_name
                attribute.owner = node_name
            return PropertyDescriptor(attr_name, attribute)

        # Query objects are like properties and should also be
        # wrapped into a descriptor
        elif isinstance(attribute, Query):
            return QueryDescriptor(node_name, attr_name, attribute)

        else:
            return attribute

    def __setattr__(self, name, value):
        """
        When dynamically, a new function/property/class is assigned to a
        Node class definition, wrap it into the correct descriptor, before
        assigning it to the actual class.
        Note that `self` is a Node class here, not a Node instance.
        """
        wrapped_attribute = self._wrap_attribute(name, value, self.__name__, self._node_type)
        type.__setattr__(self, name, wrapped_attribute)

    def __instancecheck__(self, instance):
        """
        Override isinstance operator.
        We consider an Env object in instance of this class as well if
        env._node is an instance.
        """
        return type.__instancecheck__(self, instance) or (
                    isinstance(instance, Env) and isinstance(instance._node, self))


class ParallelNodeBase(NodeBase):
    @property
    def Array(self):
        """
        'Arrayify' a ParallelNode. This is an explicit step
        to be taken before nesting ParallelNode into a normal Node.
        """
        if self._node_type != NodeTypes.SIMPLE:
            raise Exception('Second .Array operation is not allowed.')

        # When this class doesn't have a Hosts, create default mapper.
        hosts = RoleMapping(host=ALL_HOSTS) if self.Hosts is None else self.Hosts

        class ParallelNodeArray(self):
            _node_type = NodeTypes.SIMPLE_ARRAY
            Hosts = hosts

        ParallelNodeArray.__name__ = '%s.Array' % self.__name__
        return ParallelNodeArray

    @property
    def JustOne(self):
        """
        When nesting ParallelNode inside a normal Node,
        say that we expect exactly one host for the mapped
        role, so don't act like an array.
        """
        if self._node_type != NodeTypes.SIMPLE:
            raise Exception('Second .JustOne operation is not allowed.')

        # When this class doesn't have a Hosts, create default mapper.
        hosts = RoleMapping(host=ALL_HOSTS) if self.Hosts is None else self.Hosts

        class ParallelNode_One(self):
            _node_type = NodeTypes.SIMPLE_ONE
            Hosts = hosts

            @_internal
            def __init__(self, parent=None):
                Node.__init__(self, parent)
                if len(self.hosts.filter('host')) != 1:
                    raise Exception('Invalid initialisation of ParallelNode .JustOne. %i hosts given to %r.' %
                            (len(self.hosts.filter('host')), self))


        ParallelNode_One.__name__ = '%s.JustOne' % self.__name__
        return ParallelNode_One


SimpleNodeBase = ParallelNodeBase
"""
Deprecated alias for ParallelNodeBase
"""


def get_node_path(node): # TODO: maybe replace this by using the inspection module.
    """
    Return a string which represents this node's path in the tree.
    """
    path = []
    while node:
        if node._node_isolation_identifier is not None:
            path.append('%s[%s]' % (node._node_name, node._node_isolation_identifier))
        else:
            path.append(node._node_name or node.__class__.__name__)
        node = node.parent
    return '.'.join(path[::-1])


class Node(object):
    """
    This is the base class for any deployment node.

    For the attributes, also have a look at the proxy class
    :class:`deployer.node.Env`. The ``parent`` parameter is used internally to
    pass the parent ``Node`` instance into here.
    """
    __metaclass__ = NodeBase
    __slots__ = ('hosts', 'parent')
    _node_type = NodeTypes.NORMAL
    _node_is_isolated = False
    _node_isolation_identifier = None
    _node_name = None # NodeBase will set this to the attribute name as soon as we nest this node inside another one.

    node_group = None # TODO: rename to _node_group??

    Hosts = None
    """
    Hosts can be ``None`` or a definition of the hosts that should be used for this node.
    e.g.::

        class MyNode(Node):
            class Hosts:
                role1 = [ LocalHost ]
                role2 = [ SSHHost1, SSHHost2]
    """

    def __repr__(self):
        return '<Node %s>' % get_node_path(self)

    def __new__(cls, parent=None):
        """
        When this is the root node, of type NORMAL, mark is isolated right away.
        """
        if not parent and cls._node_type == NodeTypes.NORMAL:
            new_cls = type(cls.__name__, (cls,), { '_node_is_isolated': True })
            return object.__new__(new_cls, parent)
        else:
            return object.__new__(cls, parent)

    @_internal
    def __init__(self, parent=None):
        #: Reference to the parent :class:`~deployer.node.base.Node`.
        #: (This is always assigned in the constructor. You should never override it.)
        self.parent = parent

        if self._node_type in (NodeTypes.SIMPLE_ARRAY, NodeTypes.SIMPLE_ONE) and not parent:
            raise Exception('Cannot initialize a node of type %s without a parent' % self._node_type)

        # Create host container (from hosts definition, or mapping from parent hosts.)
        Hosts = self.Hosts or DefaultRoleMapping()

        if isinstance(Hosts, RoleMapping):
            self.hosts = Hosts.apply(parent) if parent else HostsContainer({ })
        else:
            self.hosts = HostsContainer.from_definition(Hosts)

        # TODO: when this is a ParallelNode and a parent was given, do we have to make sure that the
        #       the 'host' is the same, when a mapping was given? I don't think it's necessary.

    def __getitem__(self, index):
        """
        When this is a not-yet-isolated ParallelNode,
        __getitem__ retrieves the instance for this host.

        This returns a specific isolation. In case of multiple dimensions
        (multiple Node-ParallelNode.Array transitions, a tuple should be provided.)
        """
        if self._node_is_isolated:
            # TypeError, would also be a good, idea, but we choose to be compatible
            # with the error class for when an item is not found.
            raise KeyError('__getitem__ on isolated node is not allowed.')

        if isinstance(index, HostContainer):
            index = (index._host.__class__, )

        if not isinstance(index, tuple):
            index = (index, )

        for identifier_type in [
                        IsolationIdentifierType.INT_TUPLES,
                        IsolationIdentifierType.HOST_TUPLES,
                        IsolationIdentifierType.HOSTS_SLUG ]:

            for key, node in iter_isolations(self, identifier_type):
                if key == index:
                    return node
        raise KeyError

    def __iter__(self):
        for key, node in iter_isolations(self):
            yield node


class IsolationIdentifierType:
    """
    Manners of identifing a node in an array of nodes.
    """
    INT_TUPLES = 'INT_TUPLES'
    """ Use a tuple of integers """

    HOST_TUPLES = 'HOST_TUPLES'
    """ Use a tuple of :class:`Host` classes """

    HOSTS_SLUG = 'HOSTS_SLUG'
    """ Use a tuple of :class:`Host` slugs """


def iter_isolations(node, identifier_type=IsolationIdentifierType.INT_TUPLES):
    """
    Yield (index, Node) for each isolation of this node.
    """
    assert isinstance(node, Node) and not isinstance(node, Env)

    if node._node_is_isolated:
        yield (), node
        return

    def get_simple_node_cell(parent, host, identifier):
        """
        For a ParallelNode (or array cell), create a ParallelNode instance
        which matches a single cell, that is one Host for the 'host'-role.
        """
        assert isinstance(host, Host)
        hosts2 = node.hosts.get_hosts_as_dict()
        hosts2['host'] = host.__class__

        class ParallelNodeItem(node.__class__):
            _node_is_isolated = True
            _node_isolation_identifier = identifier
            Hosts = type('Hosts', (object,), hosts2)

        # If everything goes well, parent can only be an isolated instance.
        # (It's coming from ChildNodeDescriptor through getattr which isolates
        # well, or through a recursive iter_isolations call which should only
        # return isolated instances.)
        assert not parent or parent._node_is_isolated

        return ParallelNodeItem(parent=parent)

    def get_identifiers(node, parent_identifier):
        # The `node` parameter here is one for which the parent is
        # already isolated. This means that the roles are correct
        # and we can iterate through it.
        for i, host in enumerate(node.hosts.filter('host')._all):
            assert isinstance(host, Host)
            if identifier_type == IsolationIdentifierType.INT_TUPLES:
                identifier = (i,)
            elif identifier_type == IsolationIdentifierType.HOST_TUPLES:
                identifier = (host.__class__,)
            elif identifier_type == IsolationIdentifierType.HOSTS_SLUG:
                identifier = (host.slug, )

            yield (parent_identifier + identifier, host)

    # For a normal node, the isolation consists of the parent isolations.
    if node._node_type == NodeTypes.NORMAL:
        if node.parent:
            for index, n in iter_isolations(node.parent, identifier_type):
                yield (index, getattr(n, node._node_name))
        else:
            # A normal node without parent should always be isolated.
            # This is handled by Node.__new__
            assert node._node_is_isolated

            yield ((), node)

    elif node._node_type == NodeTypes.SIMPLE_ARRAY:
        assert node.parent

        for parent_identifier, parent_node in iter_isolations(node.parent, identifier_type):
            new_node = getattr(parent_node, node._node_name)
            for identifier, host in get_identifiers(new_node, parent_identifier):
                yield (identifier, get_simple_node_cell(parent_node, host, identifier[-1]))

    elif node._node_type == NodeTypes.SIMPLE_ONE:
        assert node.parent
        assert len(node.hosts.filter('host')) == 1

        for parent_identifier, parent_node in iter_isolations(node.parent, identifier_type):
            new_node = getattr(parent_node, node._node_name)
            for identifier, host in get_identifiers(new_node, parent_identifier):
                yield (identifier, get_simple_node_cell(parent_node, host, identifier[-1]))

    elif node._node_type == NodeTypes.SIMPLE:
        if node.parent:
            for index, n in iter_isolations(node.parent, identifier_type):
                yield (index, getattr(n, node._node_name))
        else:
            for identifier, host in get_identifiers(node, ()):
                yield (identifier, get_simple_node_cell(None, host, identifier[-1]))


class ParallelNode(Node):
    """
    A ``ParallelNode`` is a ``Node`` which has only one role, named ``host``.
    Multiple hosts can be given for this role, but all of them will be isolated,
    during execution. This allows parallel executing of functions on each 'cell'.

    If you call a method on a ``ParallelNode``, it will be called one for every
    host, which can be accessed through the ``host`` property.

    :note: This was called `SimpleNode` before.
    """
    __metaclass__ = ParallelNodeBase
    _node_type = NodeTypes.SIMPLE

    def host(self):
        """
        This is the proxy to the active host.

        :returns: :class:`~deployer.host_container.HostContainer` instance.
        """
        if self._node_is_isolated:
            host = self.hosts.filter('host')
            if len(host) != 1:
                raise AttributeError
            return host[0]
        else:
            raise AttributeError
    host._internal = True
    host = property(host)


SimpleNode = ParallelNode
"""
Deprecated alias for ParallelNode
"""


class Action(object):
    """
    Node actions, which are defined as just functions, will be wrapped into
    this Action class. When one such action is called, this class will make
    sure that a correct ``env`` object is passed into the function as its first
    argument.
    :param node_instance: The Node Env to which this Action is bound.
    :type node_instance: None or :class:`deployer.node.Env`
    """
    def __init__(self, attr_name, node_instance, func, is_property=False, is_query=False, query=None):
        self._attr_name = attr_name
        self._node_instance = node_instance
        self._func = func # TODO: wrap _func in something that checks whether the first argument is an Env instance.
        self.is_property = is_property
        self.is_query = is_query
        self.query = query

    @classmethod
    def from_query(cls, attr_name, node_instance, query):
        # Make a callable from this query.
        def run_query(i, return_query_result=False):
            """
            Handles exceptions properly. -> wrap anything that goes wrong in
            QueryException.
            """
            try:
                if return_query_result:
                    # Return the QueryResult wrapper instead.
                    return query._execute_query(i)
                else:
                    return query._execute_query(i).result

            except Exception as e:
                from deployer.exceptions import QueryException
                raise QueryException(i._node, attr_name, query, e)

        # Make sure that a nice name is passed to Action
        run_query.__name__ = str('query:%s' % query.__str__())

        return cls(attr_name, node_instance, run_query, is_query=True, query=query)

    @classmethod
    def from_property(cls, attr_name, node_instance, func):
        return cls(attr_name, node_instance, func, is_property=True)

    def __repr__(self):
        # Mostly useful for debugging.
        if self._node_instance:
            return '<Action %s.%s>' % (get_node_path(self._node_instance), self._attr_name)
        else:
            return "<Unbound Action %s>" % self._attr_name


    def __call__(self, env, *a, **kw):
        """
        Call this action using the unbound method.
        """
        # Calling an action is normally only possible when it's wrapped by an
        # Env object, then it becomes an EnvAction. When, on the other hand,
        # this Action object is called unbound, with an Env object as the first
        # parameter, we wrap it ourself in an EnvAction object.
        if self._node_instance is None and isinstance(env, Env):
            return env._Env__wrap_action(self)(*a, **kw)
        else:
            raise TypeError('Action is not callable. '
                'Please wrap the Node instance in an Env object first.')

    @property
    def name(self):
        return self._attr_name

    @property
    def node(self):
        return self._node_instance

    @property
    def node_group(self):
        return self._node_instance.node_group or Group()

    @property
    def suppress_result(self):
        return getattr(self._func, 'suppress_result', False)


class EnvAction(object):
    """
    Action wrapped by an Env object.
    Calling this will execute the action in the environment.
    """
    def __init__(self, env, action):
        assert isinstance(env, Env)
        assert isinstance(action, Action)

        self._env = env
        self._action = action

    def __repr__(self):
        return '<Env.Action %s.%s>' % (get_node_path(self._env._node), self._action.name)

    @property
    def name(self):
        return self._action.name

    @property
    def node(self):
        # In an Env, the node is the Env.
        return self._env

    @property
    def suppress_result(self):
        return self._action.suppress_result

    @property
    def is_property(self):
        return self._action.is_property

    @property
    def is_query(self):
        return self._action.is_query

    def _run_on_node(self, isolation, *a, **kw):
        """
        Run the action on one isolation. (On a normal Node, or on a ParallelNode cell.)
        """
        with isolation._logger.group(self._action._func.__name__, *a, **kw):
            while True:
                try:
                    return self._action._func(isolation, *a, **kw)
                except ActionException as e:
                    raise
                except ExecCommandFailed as e:
                    isolation._logger.log_exception(e)

                    if self._env._pty.interactive:
                        # If the console is interactive, ask what to do, otherwise, just abort
                        # without showing this question.
                        choice = Console(self._env._pty).choice('Continue?',
                                [ ('Retry', 'retry'),
                                ('Skip (This will not always work.)', 'skip'),
                                ('Abort', 'abort') ], default='abort')
                    else:
                        choice = 'abort'

                    if choice == 'retry':
                        continue
                    elif choice == 'skip':
                        class SkippedTaskResult(object):
                            def __init__(self, node, action):
                                self._node = node
                                self._action = action

                            def __getattribute__(self, name):
                                raise Exception('SkippedTask(%r.%r) does not have an attribute %r' % (
                                        object.__getattr__(self, '_node'),
                                        object.__getattr__(self, '_action'),
                                        name))


                        return SkippedTaskResult(self._env._node, self._action)
                    elif choice == 'abort':
                        # TODO: send exception to logger -> and print it
                        raise ActionException(e, traceback.format_exc())
                except Exception as e:
                    e2 = ActionException(e, traceback.format_exc())
                    isolation._logger.log_exception(e2)
                    raise e2

    def __call__(self, *a, **kw):
        # In case of a not_isolated ParallelNode, return a
        # ParallelActionResult, otherwise, just return the actual result.
        if isinstance(self._env, ParallelNode) and not self._env._node_is_isolated and \
                            not getattr(self._action._func, 'dont_isolate_yet', False):

            # Get isolations of the env.
            isolations = list(self._env)

            # No hosts in ParallelNode. Nothing to do.
            if len(isolations) == 0:
                self._env._logger.log_msg('Nothing to do. No hosts in %r' % self._action)
                return ParallelActionResult([ ])

            # Exactly one host.
            elif len(isolations) == 1:
                return ParallelActionResult([ (isolations[0], self._run_on_node(isolations[0], *a, **kw)) ])

            # Multiple hosts, but isolate_one_only flag set.
            elif getattr(self._action._func, 'isolate_one_only', False):
                # Ask the end-user which one to use.
                        # TODO: this is not necessarily okay. we can have several levels of isolation.
                options = [ ('%s    [%s]' % (i.host.slug, i.host.address), i) for i in isolations ]
                i = Console(self._env._pty).choice('Choose a host', options, allow_random=True)
                return self._run_on_node(i, *a, **kw)

            # Multiple hosts. Fork for each isolation.
            else:
                errors = []

                # Create a callable for each host.
                def closure(isolation):
                    def call(pty):
                        # Isolation should be an env, but
                        i2 = Env(isolation._node, pty, isolation._logger, isolation._is_sandbox)

                        # Fork logger
                        logger_fork = self._env._logger.log_fork('On: %r' % i2._node)
                                # TODO: maybe we shouldn't log fork(). Consider it an abstraction.

                        try:
                            # Run this action on the new service.
                            result = self._run_on_node(i2, *a, **kw)

                            # Succeed
                            logger_fork.set_succeeded()
                            return (isolation, result)
                        except Exception as e:
                            # TODO: handle exception in thread
                            logger_fork.set_failed(e)
                            errors.append(e)
                    return call

                # For every isolation, create a callable.
                callables = [ closure(i) for i in isolations ]
                logging.info('Forking %r (%i pseudo terminals)' % (self._action, len(callables)))

                fork_result = self._env._pty.run_in_auxiliary_ptys(callables)
                fork_result.join()

                if errors:
                    # When an error occcured in one fork, raise this error
                    # again in current thread.
                    raise errors[0]
                else:
                    # This returns a list of results.
                    return ParallelActionResult(fork_result.result)
        else:
            return self._run_on_node(self._env, *a, **kw)


class ParallelActionResult(dict):
    """
    When an action of a ParallelNode was called from outside the parallel node
    itself, a `ParallelActionResult` instance is returned. This contains the
    result for each isolation.

    (Unconventional, but) Iterating through the `ParallelActionResult` class
    will yield the values (the results) instead of the keys, because of
    backwards compatibility and this is typically what people are interested in
    if they run:
    ``for result in node.action(...)``.

    The `keys`, `items` and `values` functions work as usual.
    """
    def __init__(self, isolations_and_results):
        # This is a list of (isolation, result) tuples.
        super(ParallelActionResult, self).__init__(isolations_and_results)

    def __repr__(self):
        return '{ %s }' % ', '.join('<%s>: %r' % (i.host._host.slug, v) for i, v in self.items())

    def __iter__(self):
        for v in self.values():
            yield v

########NEW FILE########
__FILENAME__ = decorators

__all__ = (
    'suppress_action_result',
    'dont_isolate_yet',
    'isolate_one_only',
    'alias',
)

def suppress_action_result(action):
    """
    When using a deployment shell, don't print the returned result to stdout.
    For example, when the result is superfluous to be printed, because the
    action itself contains already print statements, while the result
    can be useful for the caller.
    """
    action.suppress_result = True
    return action

def dont_isolate_yet(func):
    """
    If the node has not yet been separated in serveral parallel, isolated
    nodes per host. Don't do it yet for this function.
    When anothor action of the same host without this decorator is called,
    the node will be split.

    It's for instance useful for reading input, which is similar for all
    isolated executions, (like asking which Git Checkout has to be taken),
    before forking all the threads.

    Note that this will not guarantee that a node will not be split into
    its isolations, it does only say, that it does not have to. It is was
    already been split before, and this is called from a certain isolation,
    we'll keep it like that.
    """
    func.dont_isolate_yet = True
    return func

def isolate_one_only(func):
    """
    When using role isolation, and several hosts are available, run on only
    one role.  Useful for instance, for a database client. it does not make
    sense to run the interactive client on every host which has database
    access.
    """
    func.isolate_one_only = True
    return func

def alias(name):
    """
    Give this node action an alias. It will also be accessable using that
    name in the deployment shell. This is useful, when you want to have special
    characters which are not allowed in Python function names, like dots, in
    the name of an action.
    """
    def decorator(func):
       if hasattr(func, 'action_alias'):
           func.action_alias.append(name)
       else:
           func.action_alias = [ name ]
       return func
    return decorator


########NEW FILE########
__FILENAME__ = role_mapping
from deployer.utils import isclass
from deployer.host_container import HostsContainer

__all__ = ('ALL_HOSTS', 'map_roles', 'DefaultRoleMapping', )


class _MappingFilter(object):
    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name


ALL_HOSTS = _MappingFilter('ALL_HOSTS')
"""
Constant to indicate in a role mapping that all hosts of the parent should be
mapped to this role.
"""


class RoleMapping(object):
    """
    A role mapping defines which hosts from a parent Node will used in the childnode,
    and for which roles.
    Some examples:

    ::

        @map_roles(role='parent_role', role2=('parent_role2', 'parent_role3'))
        @map_roles(role='parent_role', role2=ALL_HOSTS)

        # If you don't define any role names, they'll map to the name 'host'.
        @map_roles('parent_role', 'another_parent_role')

        # This will map all the hosts in all the roles of the parent node, to the
        # role named 'host' in this node.
        @map_roles(ALL_HOSTS)
    """
    def __init__(self, *host_mapping, **mappings):
        # Validate first
        for v in host_mapping:
            assert isinstance(v, (basestring, _MappingFilter)), TypeError('Invalid parameter: %s' % v)

        for k, v in mappings.items():
            assert isinstance(v, (basestring, tuple, _MappingFilter)), TypeError('Invalid parameter: %s' % v)

            # Make sure that all values are tuples.
            if isinstance(v, basestring):
                mappings[k] = (v,)

        if host_mapping:
            mappings = dict(host=host_mapping, **mappings)

        self._mappings = mappings # Maps role -> tuple of role names.

    def __call__(self, node_class):
        from deployer.node import Node
        if not isclass(node_class) or not issubclass(node_class, Node):
            raise TypeError('Role mapping decorator incorrectly applied. '
                            '%r is not a Node class' % node_class)

        # Apply role mapping on a copy of the node class.
        return type(node_class.__name__, (node_class, ), {
                    'Hosts': self,
                    # Keep the module, to make sure that inspect.getsourcelines still works.
                    '__module__': node_class.__module__,
                    })

    def apply(self, parent_node_instance):
        """
        Map roles from the parent to the child node and create a new
        :class:`HostsContainer` instance by applying it.
        """
        parent_container = parent_node_instance.hosts
        def get(f):
            if f == ALL_HOSTS:
                return parent_container.get_hosts()
            else:
                assert isinstance(f, tuple), TypeError('Invalid value found in mapping: %r' % f)
                return parent_container.filter(*f).get_hosts()

        return HostsContainer({ role: get(f) for role, f in self._mappings.items() },
                    pty=parent_container._pty,
                    logger=parent_container._logger,
                    is_sandbox=parent_container._sandbox)


map_roles = RoleMapping


class DefaultRoleMapping(RoleMapping):
    """
    Default mapping: take the host container from the parent.
    """
    def apply(self, parent_node_instance):
        return parent_node_instance.hosts


########NEW FILE########
__FILENAME__ = options

"""
Runtime options.
"""


class Option(object):
    """
    Shell option.
    """
    def __init__(self, values, current_value):
        self.values = values
        self._value = current_value
        self._callbacks = []

    def on_change(self, callback):
        self._callbacks.append(callback)

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for c in self._callbacks:
            c()

class BooleanOption(Option):
    def __init__(self, current_value):
        assert isinstance(current_value, bool)
        Option.__init__(self, ['on', 'off'], 'on' if current_value else 'off')

    def get_value_as_bool(self):
        return self._value == 'on'


class Options(object):
    def __init__(self):
        self._options = {
            'keep-panes-open': BooleanOption(False),

            # Other options to implement:
            #    'colorscheme': Option(['dark_background', 'light_background'], 'dark_background'),
            #    'interactive': BooleanOption(True),
            #    'interactive': BooleanOption(True),
        }

    def __getitem__(self, name):
        return self._options[name]

    def items(self):
        return self._options.items()


########NEW FILE########
__FILENAME__ = pseudo_terminal
"""
.. note:: This module is mainly for internal use.

Pty implements a terminal abstraction. This can be around the default stdin/out
pair, but also around a pseudo terminal that was created through the
``openpty`` system call.
"""

import StringIO
import array
import fcntl
import os
import select as _select
import sys
import termios
import logging


class Pty(object):
    """
    Terminal abstraction around a stdin/stdout pair.

    Contains helper function, for opening an additional Pty,
    if parallel deployments are supported.

    :stdin: The input stream. (``sys.__stdin__`` by default)
    :stdout: The output stream. (``sys.__stdout__`` by default)
    :interactive: When ``False``, we should never ask for input during
                         the deployment. Choose default options when possible.
    """
    def __init__(self, stdin=None, stdout=None, interactive=True, term_var=''):
        self._stdin = stdin or sys.__stdin__
        self._stdout = stdout or sys.__stdout__
        self._term_var = term_var
        self.interactive = interactive
        self.set_ssh_channel_size = None

    @property
    def stdin(self):
        """ Return the input file object. """
        return self._stdin

    @property
    def stdout(self):
        """ Return the output file object. """
        return self._stdout

    def get_size(self):
        # Thanks to fabric (fabfile.org), and
        # http://sqizit.bartletts.id.au/2011/02/14/pseudo-terminals-in-python/
        """
        Get the size of this pseudo terminal.

        :returns: A (rows, cols) tuple.
        """
        if self.stdout.isatty():
            # Buffer for the C call
            buf = array.array('h', [0, 0, 0, 0 ])

            # Do TIOCGWINSZ (Get)
            fcntl.ioctl(self.stdout.fileno(), termios.TIOCGWINSZ, buf, True)

            # Return rows, cols
            return buf[0], buf[1]
        else:
            # Default value
            return 24, 80

    def get_width(self):
        """
        Return the width.
        """
        return self.get_size()[1]

    def get_height(self):
        """
        Return the height.
        """
        return self.get_size()[0]

    def set_term_var(self, value):
        self._term_var = value

    def get_term_var(self):
        return self._term_var

    def set_size(self, rows, cols):
        """
        Set terminal size.

        (This is also mainly for internal use. Setting the terminal size
        automatically happens when the window resizes. However, sometimes the process
        that created a pseudo terminal, and the process that's attached to the output window
        are not the same, e.g. in case of a telnet connection, or unix domain socket, and then
        we have to sync the sizes by hand.)
        """
        if self.stdout.isatty():
            # Buffer for the C call
            buf = array.array('h', [rows, cols, 0, 0 ])

            # Do: TIOCSWINSZ (Set)
            fcntl.ioctl(self.stdout.fileno(), termios.TIOCSWINSZ, buf)

            self.trigger_resize()

    def trigger_resize(self):
        # Call size setter for SSH channel
        if self.set_ssh_channel_size:
            self.set_ssh_channel_size()

    @property
    def auxiliary_ptys_are_available(self):
        # Override this when secondary pty's are available.
        return False

    def run_in_auxiliary_ptys(self, callbacks):
        """
        For each callback, open an additional terminal, and call it with the
        new 'pty' as parameter. The callback can potentially run in another
        thread.

        The default behaviour is not in parallel, but sequential.
        Socket_server however, inherits this pty, and overrides this function
        for parrallel execution.

        :param callbacks: A list of callables.
        """
        logging.info('Could not open auxiliary pty. Running sequential.')

        # This should be overriden by other PTY objects, for environments
        # which support parallellism.

        class ForkResult(object):
            def __init__(s):
                # The callbacks parameter can be either a single callable, or a list
                if callable(callbacks):
                    s.result = callbacks(self)
                else:
                    s.result = [ c(self) for c in callbacks ]

            def join(s):
                pass # Wait for the thread to finish. No thread here.

        return ForkResult()


class DummyPty(Pty):
    """
    Pty compatible object which insn't attached to an interactive terminal, but
    to dummy StringIO instead.

    This is mainly for unit testing, normally you want to see the execution in
    your terminal.
    """
    def __init__(self, input_data=''):
        # StringIO for stdout
        self._output = StringIO.StringIO()
        self._input_data = input_data
        self._size = (40, 80)
        self._pipe = None

        Pty.__init__(self, None, self._output, interactive=False)

    @property
    def stdin(self):
        # Lazy pipe creation.
        if not self._pipe:
            self._pipe = self._make_pipe()
        return self._pipe

    def _make_pipe(self):
        """
        Create a pipe on which the input data is written. Return the output
        data. (Select will be used on this -- so StringIO won't work.)
        """
        r, w = os.pipe()

        with os.fdopen(w, 'w') as w:
            w.write(self._input_data)

        return os.fdopen(r, 'r')

    def __del__(self):
        if self._pipe:
            self._pipe.close()
            self._pipe = None

    def get_size(self):
        return self._size

    def set_size(self, rows, cols):
        self._size = (rows, cols)

    def get_output(self):
        return self._output.getvalue()

# Alternative pty_size implementation. (Will spawn a child process, so less
# efficient.)
def _pty_size(self):
    """
    Returns (height, width)
    """
    height, width = os.popen('stty size', 'r').read().split()
    return int(height), int(width)


def select(*args, **kwargs):
    """
    Wrapper around select.select.

    When the SIGWINCH signal is handled, other system calls, like select
    are aborted in Python. This wrapper will retry the system call.
    """
    import errno

    while True:
        try:
            return _select.select(*args, **kwargs)
        except Exception as e:
            # Retry select call when EINTR
            if e.args and e.args[0] == errno.EINTR:
                continue
            else:
                raise

########NEW FILE########
__FILENAME__ = query
"""
Queries provide syntactic sugar for expressions inside nodes.

::

    class MyNode(Node):
        do_something = True

        class MyChildNode(Node):
            do_something = Q.parent.do_something

            def setup(self):
                if self.do_something:
                    ...
                    pass
"""

import inspect


__all__ = ('Q', )


class Query(object):
    """
    Node Query object.
    """
    def __init__(self):
        c = inspect.currentframe()

        # Track the file and line number where this expression was created.
        self._filename = self._line = None
        for f in inspect.getouterframes(inspect.currentframe()):
            self._filename = f[1]
            self._line = f[2]

            if not 'deployer/query.py' in self._filename:
                break

    def _execute_query(self, instance):
        return NotImplementedError

    def __getattr__(self, attrname):
        """
        Attribute lookup.
        """
        return AttrGetter(self, attrname)

    def __call__(self, *args, **kwargs):
        """
        Handle .method(param)
        """
        return Call(self, args, kwargs)

    def __getitem__(self, key):
        """
        Handle self[key]
        """
        return ItemGetter(self, key)

    @property
    def parent(self):
        """
        Go to the current parent of this node.
        """
        return Parent(self)

    # Operator overloads
    def __mod__(self, other):
        return Operator(self, other, lambda a, b: a % b, '%')

    def __add__(self, other):
        return Operator(self, other, lambda a, b: a + b, '+')

    def __sub__(self, other):
        return Operator(self, other, lambda a, b: a - b, '-')

    def __mul__(self, other):
        return Operator(self, other, lambda a, b: a * b, '*')

    def __div__(self, other):
        return Operator(self, other, lambda a, b: a / b, '/')

    # Reverse operator overloads
    def __radd__(self, other):
        return Operator(other, self, lambda a, b: a + b, '+')

    def __rsub__(self, other):
        return Operator(other, self, lambda a, b: a - b, '-')

    def __rmul__(self, other):
        return Operator(other, self, lambda a, b: a * b, '*')

    def __rdiv__(self, other):
        return Operator(other, self, lambda a, b: a / b, '/')

    def __repr__(self):
        return 'Query(...)'

    # You cannot override and, or and not:
    # Instead, we override the bitwise operators
    # http://stackoverflow.com/questions/471546/any-way-to-override-the-and-operator-in-python

    def __and__(self, other):
        return Operator(self, other, lambda a, b: a and b, '&')

    def __or__(self, other):
        return Operator(self, other, lambda a, b: a or b, '|')

    def __invert__(self):
        return Invert(self)


class QueryResult(object):
    """
    Wrap the output of a query along with all the subqueries
    that were done during it's evaluation.
    (Mainly for reflexion on queries, and its understanding for te end-user.)
    """
    def __init__(self, query, result, subqueries=None):
        self.query = query
        self.result = result
        self.subqueries = subqueries or [] # List of subquery results

    def __repr__(self):
        return 'QueryResult(query=%r, result=%r)' % (self.query, self.result)

    def walk_through_subqueries(self):
        """
        Yield all queries, and their result
        """
        for s in self.subqueries:
            for r in s.walk_through_subqueries():
                yield r
        yield self.query, self.result


def _resolve(o):
    """
    Make sure that this object becomes a Query object.
    In case of a tuple/list, create a QueryTuple/List,
    otherwise, return a Static
    """
    if isinstance(o, Query):
        return o

    elif isinstance(o, tuple):
        return Tuple(o)

    elif isinstance(o, list):
        return List(o)

    elif isinstance(o, dict):
        return Dict(o)

    else:
        return Static(o)


class Tuple(Query):
    # Resolving tuples is very useful for:
    #     Q("%s/%s") % (Q.var1, Q.var2)
    cls = tuple

    def __init__(self, items):
        self.items = [ _resolve(i) for i in items ]

    def _execute_query(self, instance):
        parts = [ i._execute_query(instance) for i in self.items ]
        return QueryResult(self,
                self.cls(i.result for i in parts),
                parts)

class List(Tuple):
    cls = list

class Dict(Query):
    # Both the keys and the values will be resolved
    #     Q("%(magic)s") % {Q.key: Q.value} is possible
    cls = dict

    def __init__(self, items):
        self.items = { _resolve(k): _resolve(v) for k, v in items.iteritems() }

    def _execute_query(self, instance):
        parts = { k._execute_query(instance): v._execute_query(instance) for k, v in self.items.iteritems() }
        return QueryResult(self,
                self.cls([(k.result, v.result) for k, v in parts.iteritems()]),
                parts)


class Invert(Query):
    """
    Implementation of the invert operator
    """
    def __init__(self, subquery):
        self.subquery = subquery

    def _execute_query(self, instance):
        part = self.subquery._execute_query(instance)
        return QueryResult(self, not part.result, [ part ] )

    def __repr__(self):
        return u'~ %r' % self.subquery


class Operator(Query):
    """
    Query which wraps two other query objects and an operator in between.
    """
    def __init__(self, part1, part2, operator, operator_str):
        Query.__init__(self)
        self.part1 = _resolve(part1)
        self.part2 = _resolve(part2)
        self.operator = operator
        self.operator_str = operator_str

    def _execute_query(self, instance):
        part1 = self.part1._execute_query(instance)
        part2 = self.part2._execute_query(instance)

        return QueryResult(self,
                self.operator(part1.result, part2.result),
                [ part1, part2 ])

    def __repr__(self):
        return u'%r %s %r' % (self.part1, self.operator_str, self.part2)


class ItemGetter(Query):
    """
    Query which takes an item of the result from another query.
    """
    def __init__(self, subquery, key):
        Query.__init__(self)
        self.subquery = subquery
        self.key = _resolve(key)

    def _execute_query(self, instance):
        # The index object can be a query itself. e.g. Q.var[Q.var2]
        part = self.subquery._execute_query(instance)
        key = self.key._execute_query(instance)
        return QueryResult(self,
            part.result[key.result], [part, key])

    def __repr__(self):
        return '%r[%r]' % (self.subquery, self.key)


class Static(Query):
    """
    Query which represents just a static value.
    """
    def __init__(self, value):
        Query.__init__(self)
        self.value = value

    def _execute_query(self, instance):
        return QueryResult(self, self.value, [])

    def __repr__(self):
        # NOTE: we just return `value` instead of `Q(value)`.
        # otherwise, most of the repr calls return too much garbage,
        # most of the time, not what the user entered.
        # e.g: Q.a['value'] is automatically transformed in Q.a[Q('value')]
        return repr(self.value)


class AttrGetter(Query):
    """
    Query which takes an attribute of the result from another query.
    """
    def __init__(self, subquery, attrname):
        Query.__init__(self)
        self.subquery = subquery
        self.attrname = attrname

    def _execute_query(self, instance):
        part = self.subquery._execute_query(instance)
        return QueryResult(self,
            getattr(part.result, self.attrname), [ part ])

    def __repr__(self):
        return '%r.%s' % (self.subquery, self.attrname)


class Call(Query):
    """
    Any callable in a query.
    The parameters can be queris itself.
    """
    def __init__(self, subquery, args, kwargs):
        Query.__init__(self)
        self.subquery = subquery
        self.args = [ _resolve(a) for a in args ]
        self.kwargs = { k:_resolve(v) for k,v in kwargs.items() }

    def _execute_query(self, instance):
        part = self.subquery._execute_query(instance)
        args_results = [ a._execute_query(instance) for a in self.args ]
        kwargs_results = { k:v._execute_query(instance) for k,v in self.kwargs }

        return QueryResult(self,
                        part.result(
                                * [a.result for a in args_results],
                                **{ k:v.result for k,v in kwargs_results.items() }),
                        [ part ] + args_results + kwargs_results.values())

    def __repr__(self):
        return '%r(%s)' % (self.subquery,
                    ', '.join(map(repr, self.args) + ['%s=%r' % (k,v) for k,v in self.kwargs.items()] ))


class Parent(Query):
    """
    Query which would go to the parent of the result of another query.
    `parent('parent_name')` would go up through all the parents looking for that name.
    """
    def __init__(self, subquery):
        Query.__init__(self)
        self.subquery = subquery

    def __call__(self, parent_name):
        """
        Handle .parent(parent_name)
        """
        return FindParentByName(self.subquery, parent_name)

    def _execute_query(self, instance):
        part = self.subquery._execute_query(instance)
        return QueryResult(self, part.result.parent, [part])

    def __repr__(self):
        return '%r.parent' % self.subquery


class FindParentByName(Query):
    """
    Query which traverses the nodes in the tree, and searches for a parent having the given name.

    e.g.:

    class node(Node):
        some_property = Q('NameOfParent').property_of_that_parent
    """
    def __init__(self, subquery, parent_name):
        Query.__init__(self)
        self.subquery = subquery
        self.parent_name = parent_name

    def _execute_query(self, instance):
        part = self.subquery._execute_query(instance)

        def p(i):
            if self.parent_name in [ b.__name__ for b in inspect.getmro(i._node.__class__) ]:
                return i
            else:
                if not i.parent:
                    raise Exception('Class %s has no parent (while accessing %s from %s)' %
                                (i, self.parent_name, instance))

                return p(i.parent)

        return QueryResult(self, p(part.result), [part])

    def __repr__(self):
        return '%r.parent(%r)' % (self.subquery, self.parent_name)


class Identity(Query):
    """
    Helper for the Q object below.
    """
    def _execute_query(self, instance):
        # Return idenity func
        return QueryResult(self, instance, [])


class q(Identity):
    """
    Node Query object.
    """
    def __call__(self, string):
        """
        Allow static values, but also lists etc. to resolve further.

        Q('str') -> 'str'
        Q((Q('abc-%s') % Q.foo)) -> 'abc-bar'
        """
        return _resolve(string)

    def __repr__(self):
        return 'Q'

Q = q()

########NEW FILE########
__FILENAME__ = ipython_shell
#!/usr/bin/env python

def start(settings):
    from IPython import embed
    root = settings()
    embed()

if __name__ == '__main__':
    from deployer.contrib.default_config import example_settings
    start(settings=example_settings)

########NEW FILE########
__FILENAME__ = socket_client
"""
Start a deployment shell client.
"""

from StringIO import StringIO
from twisted.internet import fdesc

from deployer.utils import esc1
from setproctitle import setproctitle

import array
import errno
import fcntl
import getpass
import glob
import os
import pickle
import select
import signal
import socket
import subprocess
import sys
import termcolor
import termios
import time
import tty

__all__ = ('start',)

def get_size():
    # Buffer for the C call
    buf = array.array('h', [0, 0, 0, 0 ])

    # Do TIOCGWINSZ (Get)
    fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, buf, True)

    # Return rows, cols
    return buf[0], buf[1]

def make_stdin_unbuffered():
    # Make stdin/stdout unbufferd
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

class DeploymentClient(object):
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self._buffer = []
        self.wait_for_closing = False
        self.exit_status = 0

        # Currently running command
        self.update_process_title()

        # Connect to unix socket
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._connect_socket()

        # Send size to server at startup and when SIGWINCH has been caught.
        def sigwinch_handler(n, frame):
            self._send_size()

        signal.signal(signal.SIGWINCH, sigwinch_handler)

    def _connect_socket(self):
        # Can throw socket.error
        self.socket.connect(self.socket_path)

        # Wait for server to become ready
        time.sleep(0.1)

    def _send_size(self):
        self.socket.sendall(pickle.dumps(('_resize', get_size())))

    def update_process_title(self):
        """
        Set process name
        """
        setproctitle('deploy connect --socket "%s"' % self.socket_path)

    @property
    def new_window_command(self):
        """
        When a new window is opened, run this command.
        """
        return "python -c 'from deployer.run.socket_client import start; import sys; start(sys.argv[1])' '%s' " % esc1(self.socket_path)

    def _open_new_window(self, focus=False):
        """
        Open another client in a new window.
        """
        try:
            tmux_env = os.environ.get('TMUX', '')
            xterm_env = os.environ.get('XTERM', '')
            display_env = os.environ.get('DISPLAY', '')
            colorterm_env = os.environ.get('COLORTERM', '')

            if tmux_env:
                # Construct tmux split command
                swap = (' && (tmux last-pane || true)' if not focus else '')
                tiled = ' && (tmux select-layout tiled || true)'

                    # We run the new client in the current PATH variable, this
                    # makes sure that if a virtualenv was activated in a tmux
                    # pane, that we use the same virtualenv for this command.
                path_env = os.environ.get('PATH', '')

                subprocess.call(r'TMUX=%s tmux split-window "PATH=\"%s\" %s" %s %s' %
                        (tmux_env, path_env, self.new_window_command, swap, tiled),
                        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # When in a gnome-terminal:
            elif display_env and colorterm_env == 'gnome-terminal':
                subprocess.call('gnome-terminal -e "%s" &' % self.new_window_command, shell=True)
            # Fallback to xterm
            elif display_env and xterm_env:
                subprocess.call('xterm -e %s &' % self.new_window_command, shell=True)
            else:
                # Failed, print err.
                sys.stdout.write(
                        'ERROR: Doesn\'t know how to open new terminal. '
                        'TMUX and XTERM environment variables are empty.\r\n')
                sys.stdout.flush()

        except Exception as e:
            # TODO: Somehow, the subprocess.call raised an IOError Invalid argument,
            # we don't know why, but need to debug when it happens again.
            import pdb; pdb.set_trace()

    def _receive(self, data):
        """
        Process incoming data
        """
        try:
            io = StringIO(''.join(self._buffer + [data]))
            action, data = pickle.load(io)

            # Unmarshalling succeeded, call callback
            if action == '_print':
                while True:
                    try:
                        sys.stdout.write(data)
                        break
                    except IOError as e:
                        # Sometimes, when we have a lot of output, we get here:
                        # IOError: [Errno 11] Resource temporarily unavailable
                        # Just waiting a little, and retrying seems to work.
                        # See also: deployer.host.__init__ for a similar issue.
                        time.sleep(0.2)
                sys.stdout.flush()

            elif action == 'open-new-window':
                focus = data['focus']
                self._open_new_window(focus)

            elif action == '_info':
                print termcolor.colored(self.socket_path, 'cyan')
                print '     Created:             %s' % data['created']
                print '     Root node name:      %s' % data['root_node_name']
                print '     Root node module:    %s' % data['root_node_module']
                print '     Processes: (%i)' % len(data['processes'])

                for i, process in enumerate(data['processes']):
                    print '     %i' % i
                    print '     - Node name    %s' % process['node_name']
                    print '     - Node module  %s' % process['node_module']
                    print '     - Running      %s' % process['running']

            elif action == 'finish':
                self.exit_status = data['exit_status']

                if data['close_on_keypress']:
                    sys.stdout.write('\r\n\r\n[DONE] Press ENTER to close window.\r\n')
                    sys.stdout.flush()
                    self.wait_for_closing = True

            # Keep the remainder for the next time
            remainder = io.read()
            self._buffer = [ remainder ]

            if len(remainder):
                self._receive('')
        except (EOFError, ValueError) as e:
            # Not enough data, wait for the next part to arrive
            if data:
                self._buffer.append(data)

    def ask_info(self):
        self.socket.sendall(pickle.dumps(('_get_info', '')))
        self._read_loop()

    def run(self, cd_path=None, action_name=None, parameters=None, open_scp_shell=False):
        """
        Run main event loop.
        """
        if action_name and open_scp_shell:
            raise Exception("Don't provide 'action_name' and 'open_scp_shell' at the same time")

        # Set stdin non blocking and raw
        tcattr = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())

        # Report size
        self._send_size()

        self.socket.sendall(pickle.dumps(('_start-interaction', {
                'cd_path': cd_path,
                'action_name': action_name,
                'parameters': parameters,
                'open_scp_shell': open_scp_shell,
                'term_var': os.environ.get('TERM', 'xterm'), # xterm, vt100, xterm-256color
            })))

        self._read_loop()

        # Reset terminal state
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, tcattr)

        # Put the cursor again at the left margin.
        sys.stdout.write('\r\n')

        # Set exit status
        sys.exit(self.exit_status)

    def _read_loop(self):
        while True:
            try:
                # I/O routing
                r, w, e = select.select([ self.socket, sys.stdin ], [], [])

                if self.socket in r:
                    data = self.socket.recv(1024)
                    if data:
                        self._receive(data)
                    else:
                        # Nothing received? End of stream.
                        break

                if sys.stdin in r:
                    # Non blocking read. (Write works better in blocking mode.
                    # Especially on OS X.)
                    fdesc.setNonBlocking(sys.stdin)
                    data = sys.stdin.read(1)
                    fdesc.setBlocking(sys.stdin)

                    # If we're finish and 'wait_for_closing' was set. Any key
                    # press will terminate the client.
                    if self.wait_for_closing:
                        break

                    if ord(data) == 14: # Ctrl-N
                        # Tell the server to open a new window.
                        self.socket.sendall(pickle.dumps(('open-new-window', '')))
                    else:
                        self.socket.sendall(pickle.dumps(('_input', data)))

            except socket.error:
                print '\nConnection closed...'
                break
            except Exception as e:
                # SIGWINCH will abort select() call. Just ignore this error
                if e.args and e.args[0] == errno.EINTR:
                    continue
                else:
                    raise


def list_sessions():
    """
    List all the servers that are running.
    """
    for path in glob.glob('/tmp/deployer.sock.%s.*' % getpass.getuser()):
        try:
            DeploymentClient(path).ask_info()
        except socket.error as e:
            pass


def start(socket_name, cd_path=None, action_name=None, parameters=None, open_scp_shell=False):
    """
    Start a socket client.
    """
    make_stdin_unbuffered()

    DeploymentClient(socket_name).run(cd_path=cd_path,
                    action_name=action_name, parameters=parameters, open_scp_shell=open_scp_shell)

########NEW FILE########
__FILENAME__ = socket_server
#!/usr/bin/env python

from deployer import std
from deployer.cli import HandlerType
from deployer.daemonize import daemonize
from deployer.exceptions import ActionException
from deployer.loggers import LoggerInterface
from deployer.loggers.default import DefaultLogger, IndentedDefaultLogger
from deployer.options import Options
from deployer.pseudo_terminal import Pty
from deployer.shell import Shell, ShellHandler, BuiltinType

from twisted.internet import reactor, defer, abstract, fdesc
from twisted.internet import threads
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.error import CannotListenError

from contextlib import nested
from setproctitle import setproctitle
from tempfile import NamedTemporaryFile

import StringIO
import datetime
import getpass
import logging
import os
import pickle
import sys

__all__ = ('start',)


"""
IMPORTANT: This file contains a good mix of event driven (Twisted Matrix) and
           threaded, blocking code. Before changing anything in this file,
           please be aware which code runs in the Twisted reactor and which
           code is forked to threads.
"""


# Consts
OPEN_TERMINAL_TIMEOUT = 2

#
# Shell extensions
#


class SocketHandlerType(HandlerType):
    color = 'cyan'
    postfix = '~'


class NewShell(ShellHandler):
    """
    List the HTTP clients.
    """
    is_leaf = True
    handler_type = SocketHandlerType()

    def __call__(self):
        print 'Opening new window...'
        self.shell.session.openNewShellFromThread()

class Jobs(ShellHandler):
    is_leaf = True
    handler_type = SocketHandlerType()

    def __call__(self):
        print ' TODO: show running jobs...' # TODO

class Monitor(ShellHandler):
    is_leaf = True
    handler_type = SocketHandlerType()

    def __call__(self):
        # Open monitor in new pane.
        def monitor(pty):
            logger = IndentedDefaultLogger(pty.stdout)
            self.shell.logger_interface.attach(logger)
            pty.stdout.write('Press to close logging pane...\n')
            pty.stdin.read(1)
            self.shell.logger_interface.detach(logger)

        self.shell.session.connection.runInNewPtys(monitor, focus=False)

class CloseDeadPanes(ShellHandler):
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        for c in set(self.shell.connection.connectionPool):
            if c.process_done:
                c.send_close()

#
# Shell instance.
#

class SocketShell(Shell):
    """
    """
    def __init__(self, *a, **kw):
        self.connection = kw.pop('connection')
        Shell.__init__(self, *a, **kw)

    @property
    def extensions(self):
        return {
                'new': NewShell,
                #'jobs': Jobs,
                'open_monitor': Monitor,

                'close-dead-panes': CloseDeadPanes,
                }


class SocketPty(Pty):
    """
    The Pty object that we pass to every shell.
    """
    def __init__(self, stdin, stdout, run_in_new_pty, interactive):
        Pty.__init__(self, stdin, stdout, interactive)
        self._run_in_new_ptys = run_in_new_pty

    def run_in_auxiliary_ptys(self, callbacks):
        return self._run_in_new_ptys(callbacks)

    @property
    def auxiliary_ptys_are_available(self):
        return True


#
# Connection Utils.
#

class SelectableFile(abstract.FileDescriptor):
    """
    Monitor a file descriptor, and call the callback
    when something is ready to read from this file.
    """
    def __init__(self, fp, callback):
        self.fp = fp
        fdesc.setNonBlocking(fp)
        self.callback = callback
        self.fileno = self.fp.fileno

        abstract.FileDescriptor.__init__(self, reactor)

    def doRead(self):
        buf = self.fp.read(4096)

        if buf:
            self.callback(buf)


class Connection(object):
    """
    Unix socket connection.
    Contains a pseudo terminal which can be used
    for either an interactive session, for logging,
    or for a second parallel deployment.
    """
    def __init__(self, protocol):
        self.root_node = protocol.factory.root_node
        self.extra_loggers = protocol.factory.extra_loggers
        self.runtime_options = protocol.factory.runtime_options
        self.transportHandle = protocol._handle
        self.doneCallback = protocol.transport.loseConnection
        self.connectionPool = protocol.factory.connectionPool
        self.connection_shell = None
        self.exit_status = 0
        self.process_done = False # Done, but waiting for the user to close the pane.

        # Create PTY
        master, self.slave = os.openpty()

        # File descriptors for the shell
        self.shell_in = os.fdopen(master, 'w', 0)
        self.shell_out = os.fdopen(master, 'r', 0)

        # File descriptors for slave pty.
        stdin = os.fdopen(self.slave, 'r', 0)
        stdout = os.fdopen(self.slave, 'w', 0)

        # Create pty object, for passing to deployment enviroment.
        self.pty = SocketPty(stdin, stdout, self.runInNewPtys,
                    interactive=protocol.factory.interactive)

        # Start read loop
        self._startReading()

    def _startReading(self):
        """
        Monitor output of the PTY's master, and send it to the client when
        available.
        """
        # Start IO reader
        def writeCallback(data):
            self.transportHandle('_print', data)
        self.reader = SelectableFile(self.shell_out, writeCallback)
        self.reader.startReading()

    def set_term_var(self, value):
        self.pty.set_term_var(value)

    def finish(self, exit_status=0, always_close=False):
        """
        Called when the process in this connection is finished.
        """
        self.exit_status = exit_status
        self.process_done = True

        close = (always_close or not self.runtime_options['keep-panes-open'].get_value_as_bool())

        # Send status code
        self.transportHandle('finish', {
            'exit_status': self.exit_status,
            'close_on_keypress': not close
        })

        # If panes are closed automatically, close the pane and terminate
        # connection. (otherwise, wait for close-dead-panes)
        if close:
            self.send_close()

    def send_close(self):
        # Stop IO reader
        self.reader.stopReading()

        # Callback
        self.doneCallback()

    def __del__(self):
        try:
            self.shell_in.close()
            self.shell_out.close()
        except:
            # Catch the following error. No idea how to solve it right now.
            # .. close failed in file object destructor:
            # .. IOError: [Errno 9] Bad file descriptor
            pass

    def startShell(self, clone_shell=None, cd_path=None, action_name=None,
                    parameters=None, open_scp_shell=False):
        """
        Start an interactive shell in this connection.
        """
        self.connection_shell = ConnectionShell(self, clone_shell=clone_shell, cd_path=cd_path)
        self.connection_shell.startThread(action_name=action_name, parameters=parameters,
                    open_scp_shell=open_scp_shell)

    def openNewConnection(self, focus=False):
        """
        Tell the client that it should open a new window.
        """
        def _open():
            self.transportHandle('open-new-window', { 'focus': focus })
        reactor.callFromThread(_open)

    def runInNewPtys(self, funcs, focus=False):
        """
        Tell the client to open a new window. When the pty has been received,
        call this function into a new thread.

        To be called from this connection's thread.
        """
        # `funcs` can be a list of callables or a single callable.
        if callable(funcs):
            funcs = [funcs]
        else:
            funcs = funcs[:] # Clone, because we pop.

        def getConnection():
            self.openNewConnection(focus=focus)

            # Blocking call to wait for a new connection
            return PtyManager.getNewConnectionFromThread()

        # Be sure to have all the necessairy connections available for every
        # function. If that's not the case, we should keep this thread
        # blocking, and eventually decide to run this function in our own
        # thread if we can't offload it in a fork.
        connections = []
        for f in funcs:
            try:
                connections.append(getConnection())
            except PtyManager.NoPtyConnection as e:
                # getNewConnection can timeout, when opening a new teminal
                # fails. (In that case we should run functions in our own
                # thread.)
                print 'ERROR: Could not open new terminal window...\n'
                break

        # Result
        results = [] # Final result.
        done_d = defer.Deferred() # Fired when all functions are called.

        # Finish execution countdown
        todo = [len(funcs)]
        def countDown():
            todo[0] -= 1
            if todo[0] == 0:
                done_d.callback(results)

        def thread(f, index, connection):
            """
            In the new spawned thread.
            """
            # Set stdout/in for this thread.
            sys.stdout.set_handler(connection.pty.stdout)
            sys.stdin.set_handler(connection.pty.stdin)

            # Call function
            try:
                result = f(connection.pty)
            except Exception as e:
                # Just print the exception, it's actually the tasks of the
                # runInNewPtys caller to make sure that all the passed
                # functions don't raise errors, or to implement a global
                # try/catch around in each function.
                # We cannot allow exceptions to propagate any more, as it
                # would leave connections open, and break ForkResult.
                print str(e)
                result = ''

            # Remove std handlers for this thread.
            sys.stdout.del_handler()
            sys.stdin.del_handler()

            # Close connection
            reactor.callFromThread(connection.finish)
            return result

        def startAllThreads():
            """
            In the Twisted reactor's thread.
            """
            def startThread(f, conn):
                # Add placeholder in results list (ordered output)
                index = len(results)
                results.append(None)

                # Spawn thread
                d = threads.deferToThread(thread, f, index, conn)

                # Attach thread-done callbacks
                @d.addCallback
                def done(result):
                    # Save result in correct slot.
                    results[index] = result
                    countDown()

                @d.addErrback
                def err(failure):
                    results[index] = str(failure)
                    countDown()

            while connections:
                conn = connections.pop()
                f = funcs.pop()
                startThread(f, conn)

        # This is blocking, given that `startAllThreads` will be run in the
        # reactor. Not that we wait for all the spawned threads to finish.
        threads.blockingCallFromThread(reactor, startAllThreads)

        # Call remaining functions in current thread/pty. This is the case when
        # opening new terminals failed.
        def handleRemainingInCurrentPty():
            while funcs:
                f = funcs.pop()
                try:
                    result = f(self.pty)
                    results.append(result)
                except Exception as e:
                    results.append(str(e))
                countDown()
        handleRemainingInCurrentPty()

        class ForkResult(object):
            """
            This ForkResult, containing the state of the thread, will be
            returned from the Twisted's reactor thread, to this connection's
            thread.
            Note that this member methods are probably not run from the reactor.
            """
            def join(self):
                """
                Wait for the thread to finish.
                """
                if todo[0] == 0:
                    return results
                else:
                    return threads.blockingCallFromThread(reactor, lambda: done_d)

            @property
            def result(self):
                if todo[0] == 0:
                    return results
                else:
                    raise AttributeError('Result not yet known. Not all threads have been finished.')

        return ForkResult()


class ConnectionShell(object):
    """
    Start an interactive shell for a connection.
    (using a separate thread.)
    """
    def __init__(self, connection, clone_shell=None, cd_path=None):
        self.connection = connection

        # Create loggers
        self.logger_interface = LoggerInterface()

        # Run shell
        self.shell = SocketShell(connection.root_node, connection.pty, connection.runtime_options,
                                self.logger_interface, clone_shell=clone_shell, connection=connection)
        self.cd_path = cd_path

    def openNewShellFromThread(self):
        """
        Open new interactive shell in a new window.
        (Clone location of current shell.)
        """
        # Ask the client to open a new connection
        self.connection.openNewConnection(focus=True)

        try:
            # Blocking call to wait for a new incoming connection
            new_connection = PtyManager.getNewConnectionFromThread()

            # Start a new shell-thread into this connection.
            ConnectionShell(new_connection, clone_shell=self.shell).startThread()
        except PtyManager.NoPtyConnection as e:
            print 'ERROR: could not open new terminal window...'

    def openNewShellFromReactor(self):
        self.connection.openNewConnection(focus=True)
        d = PtyManager.getNewConnection()

        @d.addCallback
        def openShell(new_connection):
            new_connection.startShell(clone_shell=self.shell)

        @d.addErrback
        def failed(failure):
            # Opening a new shell failed.
            pass

    def startThread(self, *a, **kw):
        threads.deferToThread(lambda: self.thread(*a, **kw))

    def thread(self, action_name=None, parameters=None, open_scp_shell=False):
        parameters = parameters or []

        # Set stdin/out pair for this thread.
        sys.stdout.set_handler(self.connection.pty.stdout)
        sys.stdin.set_handler(self.connection.pty.stdin)

        self.shell.session = self # Assign session to shell

        # in_shell_logger: Displaying of events in shell
        with self.logger_interface.attach_in_block(DefaultLogger(print_group=False)):
            # Attach the extra loggers.
            with nested(* [ self.logger_interface.attach_in_block(l) for l in self.connection.extra_loggers]):
                # Start at correct location
                if self.cd_path:
                    self.shell.cd(self.cd_path)

                if action_name and open_scp_shell:
                    print "Don't provide 'action_name' and 'open_scp_shell' at the same time"
                    exit_status = 1

                elif open_scp_shell:
                    self.shell.open_scp_shell()
                    exit_status = 0

                # When an action_name is given, call this action immediately,
                # otherwise, run the interactive cmdloop.
                elif action_name:
                    try:
                        self.shell.run_action(action_name, *parameters)
                        exit_status = 0
                    except ActionException:
                        exit_status = 1
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        exit_status = 1
                else:
                    self.shell.cmdloop()
                    exit_status = 0

        # Remove references (shell and session have circular reference)
        self.shell.session = None
        self.shell = None

        # Remove std handlers for this thread.
        sys.stdout.del_handler()
        sys.stdin.del_handler()

        # Close connection
        reactor.callFromThread(lambda: self.connection.finish(
                    exit_status=exit_status, always_close=True))


class PtyManager(object):
    need_pty_callback = None

    class NoPtyConnection(Exception):
        pass

    @classmethod
    def getNewConnectionFromThread(cls):
        """
        Block the caller's thread, until a new pty has been received.
        It will ask the current shell to open a new terminal,
        and wait for a new socket connection which will initialize
        the new pseudo terminal.
        """
        return threads.blockingCallFromThread(reactor, cls.getNewConnection)

    @classmethod
    def getNewConnection(cls):
        d = defer.Deferred()

        def callback(connection):
            cls.need_pty_callback = None
            timeout.cancel()
            d.callback(connection)

        def timeout():
            cls.need_pty_callback = None
            d.errback(cls.NoPtyConnection())

        timeout = reactor.callLater(OPEN_TERMINAL_TIMEOUT, timeout)

        cls.need_pty_callback = staticmethod(callback)
        return d


class CliClientProtocol(Protocol):
    def __init__(self):
        self._buffer = []
        self.connection = None
        self.created = datetime.datetime.now()

    def dataReceived(self, data):
        try:
            # Try to parse what we have received until now
            io = StringIO.StringIO(''.join(self._buffer + [data]))

            action, data = pickle.load(io)

            # Unmarshalling succeeded, call callback
            if action == '_input':
                self.connection.shell_in.write(data)

            elif action == '_resize':
                self.connection.pty.set_size(*data)

            elif action == '_get_info':
                # Return information about the current server state
                processes = [ {
                            'node_name': c.connection_shell.shell.state._node.__class__.__name__,
                            'node_module': c.connection_shell.shell.state._node.__module__,
                            'running': c.connection_shell.shell.currently_running or '(Idle)'
                    } for c in self.factory.connectionPool if c.connection_shell and c.connection_shell.shell ]

                self._handle('_info', {
                            'created': self.created.isoformat(),
                            'root_node_name': self.connection.root_node.__class__.__name__,
                            'root_node_module': self.connection.root_node.__module__,
                            'processes': processes,
                    })
                self.transport.loseConnection()

            elif action == 'open-new-window':
                logging.info('Opening new window')
                # When the client wants to open a new shell (Ctrl-N press for
                # instance), check whether we are in an interactive session,
                # and if so, copy this shell.
                if self.connection.connection_shell:
                    self.connection.connection_shell.openNewShellFromReactor()
                else:
                    self._handle('open-new-window', { 'focus': True })

            elif action == '_start-interaction':
                logging.info('Starting session')

                cd_path = data.get('cd_path', None)
                action_name = data.get('action_name', None)
                parameters = data.get('parameters', None)
                open_scp_shell = data.get('open_scp_shell', False)
                term_var = data.get('term_var', False)

                self.connection.set_term_var(term_var)

                # NOTE: The defer to thread method, which will be called back
                # immeditiately, can hang (wait) if the thread pool has been
                # saturated.

                # When a new Pty was needed by an existing shell. (For instance, for
                # a parallel session. Report this connection; otherwise start a new
                # ConnectionShell.
                if PtyManager.need_pty_callback and not action_name:
                    PtyManager.need_pty_callback(self.connection)
                else:
                    self.connection.startShell(cd_path=cd_path,
                            action_name=action_name, parameters=parameters,
                            open_scp_shell=open_scp_shell)

            # Keep the remainder for the next time.
            remainder = io.read()
            self._buffer = [ remainder ]

            # In case we did receive multiple calls
            # one chunk, immediately parse again.
            if len(remainder):
                self.dataReceived('')
        except (EOFError, ValueError) as e:
            # Not enough data, wait for the next part to arrive
            if data:
                self._buffer.append(data)

    def connectionLost(self, reason):
        """
        Disconnected from client.
        """
        logging.info('Client connection lost')

        # Remove current connection from the factory's connection pool.
        self.factory.connectionPool.remove(self.connection)
        self.connection = None

        # When no more connections are left, close the reactor.
        if len(self.factory.connectionPool) == 0 and self.factory.shutdownOnLastDisconnect:
            logging.info('Stopping server.')
            reactor.stop()

    def _handle(self, action, data):
        self.transport.write(pickle.dumps((action, data)) )

    def connectionMade(self):
        self.connection = Connection(self)
        self.factory.connectionPool.add(self.connection)


def startSocketServer(root_node, shutdownOnLastDisconnect, interactive, socket=None, extra_loggers=None):
    """
    Bind the first available unix socket.
    Return the socket file.
    """
    # Create protocol factory.
    factory = Factory()
    factory.connectionPool = set() # List of currently, active connections
    factory.protocol = CliClientProtocol
    factory.shutdownOnLastDisconnect = shutdownOnLastDisconnect
    factory.root_node = root_node
    factory.interactive = interactive
    factory.extra_loggers = extra_loggers or []
    factory.runtime_options = Options()

    # Listen on socket.
    if socket:
        reactor.listenUNIX(socket, factory)
    else:
        # Find a socket to listen on. (if no socket was given.)
        i = 0
        while True:
            try:
                socket = '/tmp/deployer.sock.%s.%i' % (getpass.getuser(), i)
                reactor.listenUNIX(socket, factory)
                break
            except CannotListenError:
                i += 1

                # When 100 times failed, cancel server
                if i == 100:
                    logging.warning('100 times failed to listen on posix socket. Please clean up old sockets.')
                    raise

    return socket


# =================[ Startup]=================

def start(root_node, daemonized=False, shutdown_on_last_disconnect=False, thread_pool_size=50,
                interactive=True, logfile=None, socket=None, extra_loggers=None):
    """
    Start web server
    If daemonized, this will start the server in the background,
    and return the socket path.
    """
    # Create node instance
    root_node = root_node()

    # Start server
    socket2 = startSocketServer(root_node, shutdownOnLastDisconnect=shutdown_on_last_disconnect,
                        interactive=interactive, socket=socket, extra_loggers=extra_loggers)

    def set_title(stream_name):
        suffix = (' --log "%s"' % stream_name if stream_name else '')
        setproctitle('deploy:%s listen --socket "%s"%s' %
                        (root_node.__class__.__name__, socket2, suffix))

    def run_server():
        # Set logging
        stream = None
        if logfile:
            logging.basicConfig(filename=logfile, level=logging.DEBUG)
        elif not daemonized:
            logging.basicConfig(filename='/dev/stdout', level=logging.DEBUG)
        else:
            # If no logging file was given, and we're daemonized, create a temp
            # logfile for monitoring.
            stream = NamedTemporaryFile(delete=True, suffix=socket2.replace('/', '-'))
            logging.basicConfig(stream=stream, level=logging.DEBUG)

        logging.info('Socket server started at %s' % socket2)

        # Thread sensitive interface for stdout/stdin
        std.setup()

        # Set thread pool size (max parrallel interactive processes.)
        if thread_pool_size:
            reactor.suggestThreadPoolSize(thread_pool_size)

        # Set process name
        set_title(stream.name if stream else logfile)

        # Run Twisted reactor
        reactor.run()

        # Remove logging file (this will automatically delete the NamedTemporaryFile)
        if stream:
            stream.close()

    if daemonized:
        if daemonize():
            # In daemon
            run_server()
            sys.exit()
        else:
            # In parent.
            return socket2
    else:
        run_server()

########NEW FILE########
__FILENAME__ = standalone_shell
#!/usr/bin/env python

from deployer.exceptions import ActionException
from deployer.loggers import LoggerInterface
from deployer.loggers.default import DefaultLogger
from deployer.options import Options
from deployer.pseudo_terminal import Pty
from deployer.shell import Shell

from contextlib import nested
from setproctitle import setproctitle

import logging
import os
import signal
import sys


__all__ = ('start',)


class StandaloneShell(Shell):
    """
    You can inherit this shell, add your extension, and pass that class
    to the start method below.
    """
    @property
    def extensions(self):
        return { }


def start(root_node, interactive=True, cd_path=None, logfile=None,
                action_name=None, parameters=None, shell=StandaloneShell,
                extra_loggers=None, open_scp_shell=False):
    """
    Start the deployment shell in standalone modus. (No parrallel execution,
    no server/client. Just one interface, and everything sequential.)
    """
    parameters = parameters or []

    # Enable logging
    if logfile:
        logging.basicConfig(filename=logfile, level=logging.DEBUG)

    # Make sure that stdin and stdout are unbuffered
    # The alternative is to start Python with the -u option
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    # Create Pty object
    pty = Pty(sys.stdin, sys.stdout, interactive=interactive,
                term_var=os.environ.get('TERM', ''))

    def sigwinch_handler(n, frame):
        pty.trigger_resize()
    signal.signal(signal.SIGWINCH, sigwinch_handler)

    # Create runtime options
    options = Options()

    # Initialize root node
    root_node = root_node()

    # Set process title
    setproctitle('deploy:%s run -s' % root_node.__class__.__name__)

    # Loggers
    in_shell_logger = DefaultLogger(print_group=False)

    logger_interface = LoggerInterface()
    extra_loggers = extra_loggers or []

    with logger_interface.attach_in_block(in_shell_logger):
        with nested(* [logger_interface.attach_in_block(l) for l in extra_loggers]):
            # Create shell
            print 'Running single threaded shell...'
            shell = shell(root_node, pty, options, logger_interface)
            if cd_path is not None:
                shell.cd(cd_path)

            if action_name and open_scp_shell:
                raise Exception("Don't provide 'action_name' and 'open_scp_shell' at the same time")

            if open_scp_shell:
                shell.open_scp_shell()

            elif action_name:
                try:
                    return shell.run_action(action_name, *parameters)
                except ActionException as e:
                    sys.exit(1)
                except:
                    import traceback
                    traceback.print_exc()
                    sys.exit(1)

            else:
                shell.cmdloop()

########NEW FILE########
__FILENAME__ = telnet_server
"""
Web and telnet server for the deployment scripts.
Note that this module is using global variables, it should
never be initialized more than once.
"""

from twisted.conch import telnet
from twisted.conch.telnet import StatefulTelnetProtocol, TelnetTransport
from twisted.internet import reactor, abstract, fdesc
from twisted.internet.protocol import ServerFactory
from twisted.internet.threads import deferToThread

from deployer import std
from deployer.cli import HandlerType
from deployer.console import NoInput, Console
from deployer.loggers import LoggerInterface
from deployer.loggers.default import DefaultLogger
from deployer.options import Options
from deployer.pseudo_terminal import Pty
from deployer.shell import Shell, ShellHandler

from contextlib import nested
from termcolor import colored
from setproctitle import setproctitle

import logging
import os
import signal
import struct
import sys


__all__ = ('start',)


# =================[ Authentication backend ]=================

class Backend(object):
    def authenticate(self, username, password):
        # Return True when this username/password combination is correct.
        raise NotImplementedError

# =================[ Shell extensions ]=================

class WebHandlerType(HandlerType):
    color = 'cyan'
    postfix = '~'

class ActiveSessionsHandler(ShellHandler):
    """
    List active deployment sessions. (Telnet + HTTP)
    """
    is_leaf = True
    handler_type = WebHandlerType()

    def __call__(self):
        print colored('%-12s %s' % ('Username', 'What'), 'cyan')

        for session in self.shell.session.protocol.factory.connectionPool:
            print '%-12s' % (session.username or 'somebody'),
            print '%s' % ((session.shell.currently_running if session.shell else None) or '(Idle)')


class WebShell(Shell):
    """
    The shell that we provide via telnet exposes some additional commands for
    session and user management and logging.
    """
    @property
    def extensions(self):
        return { 'w': ActiveSessionsHandler, }

    def __init__(self, *a, **kw):
        username = kw.pop('username')
        Shell.__init__(self, *a, **kw)
        self.username = username

    @property
    def prompt(self):
        """
        Return a list of [ (text, color) ] tuples representing the prompt.
        """
        if self.username:
            return [ (self.username, 'cyan'), ('@', None) ] + super(WebShell, self).prompt
        else:
            return super(WebShell, self).prompt

# =================[ Text based authentication ]=================

class NotAuthenticated(Exception):
    pass


def pty_based_auth(auth_backend, pty):
    """
    Show a username/password login prompt.
    Return username when authentication succeeded.
    """
    tries = 0
    while True:
        # Password authentication required for this session?
        sys.stdout.write('\033[2J\033[0;0H') # Clear screen
        sys.stdout.write(colored('Please authenticate\r\n\r\n', 'cyan'))

        if tries:
            sys.stdout.write(colored('  Authentication failed, try again\r\n', 'red'))

        try:
            console = Console(pty)
            username = console.input('Username', False)
            password = console.input('Password', True)
        except NoInput:
            raise NotAuthenticated

        if auth_backend.authenticate(username, password):
            sys.stdout.write(colored(' ' * 40 + 'Authentication successful\r\n\r\n', 'green'))
            return username
        else:
            tries += 1
            if tries == 3:
                raise NotAuthenticated


# =================[ Session handling ]=================

class Session(object):
    """
    Create a pseudo terminal and run a deployment session in it.
    (using a separate thread.)
    """
    def __init__(self, protocol, writeCallback=None, doneCallback=None):
        self.protocol = protocol
        self.root_node = protocol.transport.factory.root_node
        self.auth_backend = protocol.transport.factory.auth_backend
        self.extra_loggers = protocol.transport.factory.extra_loggers

        self.doneCallback = doneCallback
        self.writeCallback = writeCallback
        self.username = None

        # Create PTY
        self.master, self.slave = os.openpty()

        # File descriptors for the shell
        self.shell_in = self.shell_out = os.fdopen(self.master, 'r+w', 0)

        # File descriptors for slave pty.
        stdin = stdout = os.fdopen(self.slave, 'r+w', 0)

        # Create pty object, for passing to deployment enviroment.
        self.pty = Pty(stdin, stdout)

    def start(self):
        def thread():
            """
            Run the shell in a normal synchronous thread.
            """
            # Set stdin/out pair for this thread.
            sys.stdout.set_handler(self.pty.stdout)
            sys.stdin.set_handler(self.pty.stdin)

            # Authentication
            try:
                self.username = pty_based_auth(self.auth_backend, self.pty) if self.auth_backend else ''
                authenticated = True
            except NotAuthenticated:
                authenticated = False

            if authenticated:
                # Create loggers
                logger_interface = LoggerInterface()
                in_shell_logger = DefaultLogger(self.pty.stdout, print_group=False)

                # Create options.
                options = Options()

                # Run shell
                shell = WebShell(self.root_node, self.pty, options, logger_interface, username=self.username)

                shell.session = self # Assign session to shell
                self.shell = shell

                with logger_interface.attach_in_block(in_shell_logger):
                    with nested(* [logger_interface.attach_in_block(l) for l in self.extra_loggers]):
                        shell.cmdloop()

                # Remove references (shell and session had circular reference)
                self.shell = None
                shell.session = None

            # Write last dummy character to trigger the session_closed.
            # (telnet session will otherwise wait for enter keypress.)
            sys.stdout.write(' ')

            # Remove std handlers for this thread.
            sys.stdout.del_handler()
            sys.stdin.del_handler()

            if self.doneCallback:
                self.doneCallback()

            # Stop IO reader
            reactor.callFromThread(self.reader.stopReading)

        deferToThread(thread)

        # Start IO reader
        self.reader = SelectableFile(self.shell_out, self.writeCallback)
        self.reader.startReading()


class SelectableFile(abstract.FileDescriptor):
    """
    Monitor a file descriptor, and call the callback
    when something is ready to read from this file.
    """
    def __init__(self, fp, callback):
        self.fp = fp
        fdesc.setNonBlocking(fp)
        self.callback = callback
        self.fileno = self.fp.fileno

        abstract.FileDescriptor.__init__(self, reactor)

    def doRead(self):
        buf = self.fp.read(4096)

        if buf:
            self.callback(buf)

# =================[ Telnet interface ]=================

class TelnetDeployer(StatefulTelnetProtocol):
    """
    Telnet interface
    """
    def connectionMade(self):
        logging.info('Connection made, starting new session')

        # Start raw (for the line receiver)
        self.setRawMode()

        # Handle window size answers
        self.transport.negotiationMap[telnet.NAWS] = self.telnet_NAWS

        # Use a raw connection for ANSI terminals, more info:
        # http://tools.ietf.org/html/rfc111/6
        # http://s344.codeinspot.com/q/1492309

        # 255, 253, 34,  /* IAC DO LINEMODE */
        self.transport.do(telnet.LINEMODE)

        # 255, 250, 34, 1, 0, 255, 240 /* IAC SB LINEMODE MODE 0 IAC SE */
        self.transport.requestNegotiation(telnet.LINEMODE, '\0')

        # 255, 251, 1    /* IAC WILL ECHO */
        self.transport.will(telnet.ECHO)

        # Negotiate about window size
        self.transport.do(telnet.NAWS)

        # Start session
        self.session = Session(self,
                    writeCallback=lambda data: self.transport.write(data),
                    doneCallback=lambda: self.transport.loseConnection())
        self.factory.connectionPool.add(self.session)
        self.session.start()

    def connectionLost(self, reason):
        self.factory.connectionPool.remove(self.session)
        logging.info('Connection lost. Session ended')

    def enableRemote(self, option):
        #self.transport.write("You tried to enable %r (I rejected it)\r\n" % (option,))
        return True # TODO:only return True for the values that we accept

    def disableRemote(self, option):
        #self.transport.write("You disabled %r\r\n" % (option,))
        pass
        #return True

    def enableLocal(self, option):
        #self.transport.write("You tried to make me enable %r (I rejected it)\r\n" % (option,))
        return True

    def disableLocal(self, option):
        #self.transport.write("You asked me to disable %r\r\n" % (option,))
        pass
        #return True

    def rawDataReceived(self, data):
        self.session.shell_in.write(data)
        self.session.shell_in.flush()

    def telnet_NAWS(self, bytes):
        # When terminal size is received from telnet client,
        # set terminal size on pty object.
        if len(bytes) == 4:
            width, height = struct.unpack('!HH', ''.join(bytes))
            self.session.pty.set_size(height, width)
        else:
            print "Wrong number of NAWS bytes"


# =================[ Startup]=================

def start(root_node, auth_backend=None, port=8023, logfile=None, extra_loggers=None):
    """
    Start telnet server
    """
    # Set logging
    if logfile:
        logging.basicConfig(filename=logfile, level=logging.DEBUG)
    else:
        logging.basicConfig(filename='/dev/stdout', level=logging.DEBUG)

    # Thread sensitive interface for stdout/stdin
    std.setup()

    # Telnet
    factory = ServerFactory()
    factory.connectionPool = set() # List of currently, active connections
    factory.protocol = lambda: TelnetTransport(TelnetDeployer)
    factory.root_node = root_node()
    factory.auth_backend = auth_backend
    factory.extra_loggers = extra_loggers or []

    # Handle signals
    def handle_sigint(signal, frame):
        if factory.connectionPool:
            logging.info('Running, %i active session(s).' % len(factory.connectionPool))
        else:
            logging.info('No active sessions, exiting')
            reactor.stop()

    signal.signal(signal.SIGINT, handle_sigint)

    # Run the reactor!
    logging.info('Listening for incoming telnet connections on localhost:%s...' % port)

    # Set process name
    suffix = (' --log "%s"' % logfile if logfile else '')
    setproctitle('deploy:%s telnet-server --port %i%s' %
            (root_node.__class__.__name__, port, suffix))

    # Run server
    reactor.listenTCP(port, factory)
    reactor.run()

########NEW FILE########
__FILENAME__ = scp_shell
from deployer.cli import CLInterface, Handler, HandlerType
from deployer.console import Console
from deployer.host import Host
from deployer.host import LocalHost
from deployer.utils import esc1
from termcolor import colored

import sys
import os
import stat
import os.path

# Types

class BuiltinType(HandlerType):
    color = 'cyan'

class LocalType(HandlerType):
    color = 'green'

class RemoteType(HandlerType):
    color = 'yellow'

class ModifyType(HandlerType):
    color = 'red'

class DirectoryType(HandlerType):
    color = 'blue'

class FileType(HandlerType):
    color = None


class CacheMixin(object):
    """
    Mixin for Host, which adds caching to listdir and stat.
    (This makes autocompletion much faster.
    """
    def __init__(self, *a, **kw):
        super(CacheMixin, self).__init__(*a, **kw)
        self._listdir_cache = {}
        self._stat_cache = {}

    def listdir(self):
        cwd = self.getcwd()
        if cwd not in self._listdir_cache:
            self._listdir_cache[cwd] = super(CacheMixin, self).listdir()
        return self._listdir_cache[cwd]

    def stat(self, path):
        cwd = self.getcwd()
        if (cwd, path) not in self._stat_cache:
            self._stat_cache[(cwd, path)] = super(CacheMixin, self).stat(path)
        return self._stat_cache[(cwd, path)]

    def fill_cache(self, pty):
        """ Fill cache for current directory. """
        console = Console(pty)
        with console.progress_bar('Reading directory...', clear_on_finish=True):
            cwd = self.getcwd()
            for s in self.listdir_stat():
                self._stat_cache[(cwd, s.filename)] = s

# Handlers

class SCPHandler(Handler):
    def __init__(self, shell):
        self.shell = shell

def remote_handler(files_only=False, directories_only=False):
    """ Create a node system that does autocompletion on the remote path. """
    return _create_autocompleter_system(files_only, directories_only, RemoteType,
            lambda shell: shell.host)


def local_handler(files_only=False, directories_only=False):
    """ Create a node system that does autocompletion on the local path. """
    return _create_autocompleter_system(files_only, directories_only, LocalType,
            lambda shell: shell.localhost)


def _create_autocompleter_system(files_only, directories_only, handler_type_cls, get_host_func):
    def local_handler(func):
        class ChildHandler(SCPHandler):
            is_leaf = True

            def __init__(self, shell, path):
                self.path = path
                SCPHandler.__init__(self, shell)

            @property
            def handler_type(self):
                host = get_host_func(self.shell)
                if self.path in ('..', '.', '/') or host.stat(self.path).is_dir:
                    return DirectoryType()
                else:
                    return FileType()

            def __call__(self):
                func(self.shell, self.path)

        class MainHandler(SCPHandler):
            handler_type = handler_type_cls()

            def complete_subhandlers(self, part):
                host = get_host_func(self.shell)
                # Progress bar.
                for f in host.listdir():
                    if f.startswith(part):
                        if files_only and not host.stat(f).is_file:
                            continue
                        if directories_only and not host.stat(f).is_dir:
                            continue

                        yield f, ChildHandler(self.shell, f)

                # Root directory.
                if '/'.startswith(part) and not files_only:
                    yield f, ChildHandler(self.shell, '/')

            def get_subhandler(self, name):
                host = get_host_func(self.shell)

                # First check whether this name appears in the current directory.
                # (avoids stat calls on unknown files.)
                if name in host.listdir():
                    # When this file does not exist, return
                    try:
                        s = host.stat(name)
                        if (files_only and not s.is_file):
                            return
                        if (directories_only and not s.is_dir):
                            return
                    except IOError: # stat on non-existing file.
                        return
                    finally:
                        return ChildHandler(self.shell, name)

                # Root, current and parent directory.
                if name in ('/', '..', '.') and not files_only:
                    return ChildHandler(self.shell, name)

        return MainHandler
    return local_handler


class Clear(SCPHandler):
    """ Clear window.  """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        sys.stdout.write('\033[2J\033[0;0H')
        sys.stdout.flush()

class Exit(SCPHandler):
    """ Quit the SFTP shell. """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        self.shell.exit()


class Connect(SCPHandler):
    is_leaf = True
    handler_type = RemoteType()

    def __call__(self): # XXX: code duplication of deployer/shell.py
        initial_input = "cd '%s'\n" % esc1(self.shell.host.getcwd())
        self.shell.host.start_interactive_shell(initial_input=initial_input)


class Lconnect(SCPHandler):
    is_leaf = True
    handler_type = LocalType()

    def __call__(self): # XXX: code duplication of deployer/shell.py
        initial_input = "cd '%s'\n" % esc1(self.shell.localhost.getcwd())
        self.shell.localhost.start_interactive_shell(initial_input=initial_input)


@remote_handler(files_only=True)
def view(shell, path):
    """ View remote file. """
    console = Console(shell.pty)

    with shell.host.open(path, 'r') as f:
        def reader():
            while True:
                line = f.readline()
                if line:
                    yield line.rstrip('\n')
                else:
                    return # EOF

        console.lesspipe(reader())

@remote_handler(files_only=True)
def edit(shell, path):
    """ Edit file in editor. """
    shell.host.run("vim '%s'" % esc1(path))

class Pwd(SCPHandler):
    """ Display remote working directory. """
    is_leaf = True
    handler_type = RemoteType()

    def __call__(self):
        print self.shell.host.getcwd()

def make_ls_handler(handler_type_, get_host_func):
    """ Make a function that does a directory listing """
    class Ls(SCPHandler):
        is_leaf = True
        handler_type = handler_type_()

        def __call__(self):
            host = get_host_func(self.shell)
            files = host.listdir()

            def iterator():
                for f in files:
                    if host.stat(f).is_dir:
                        yield colored(f, DirectoryType.color), len(f)
                    else:
                        yield f, len(f)

            console = Console(self.shell.pty)
            console.lesspipe(console.in_columns(iterator()))
    return Ls

ls = make_ls_handler(RemoteType, lambda shell: shell.host)
lls = make_ls_handler(LocalType, lambda shell: shell.localhost)


@remote_handler(directories_only=True)
def cd(shell, path):
    shell.host.host_context._chdir(path)
    print shell.host.getcwd()
    shell.host.fill_cache(shell.pty)


@local_handler(directories_only=True)
def lcd(shell, path):
    shell.localhost.host_context._chdir(path)
    print shell.localhost.getcwd()


class Lls(SCPHandler):
    """ Display local directory listing  """
    handler_type = LocalType()
    is_leaf = True

    def __call__(self):
        files = self.shell.localhost.listdir()
        console = Console(self.shell.pty)
        console.lesspipe(console.in_columns(files))


class Lpwd(SCPHandler):
    """ Print local working directory. """
    handler_type = LocalType()
    is_leaf = True

    def __call__(self):
        print self.shell.localhost.getcwd()


@local_handler(files_only=True)
def lview(shell, path):
    """ View local file. """
    console = Console(shell.pty)

    with shell.localhost.open(path, 'r') as f:
        def reader():
            while True:
                line = f.readline()
                if line:
                    yield line.rstrip('\n')
                else:
                    return # EOF

        console.lesspipe(reader())

@local_handler(files_only=True)
def put(shell, filename):
    """ Upload local-path and store it on the remote machine. """
    print 'Uploading %s...', filename
    h = shell.host
    h.put_file(os.path.join(shell.localhost.getcwd(), filename), filename)


@remote_handler(files_only=True)
def get(shell, filename):
    """ Retrieve the remote-path and store it on the local machine """
    target = os.path.join(shell.localhost.getcwd(), filename)
    print 'Downloading %s to %s...' % (filename, target)
    h = shell.host
    h.get_file(filename, target)


@remote_handler()
def stat_handler(shell, filename):
    """ Print stat information of this file. """
    s = shell.host.stat(filename)

    print ' Is file:      %r' % s.is_file
    print ' Is directory: %r' % s.is_dir
    print
    print ' Size:         %r bytes' % s.st_size
    print
    print ' st_uid:       %r' % s.st_uid
    print ' st_gid:       %r' % s.st_gid
    print ' st_mode:      %r' % s.st_mode


@local_handler()
def lstat(shell, filename):
    """ Print stat information for this local file. """
    s =  shell.localhost.stat(filename)

    print ' Is file:      %r' % stat.S_ISREG(s.st_mode)
    print ' Is directory: %r' % stat.S_ISDIR(s.st_mode)
    print
    print ' Size:         %r bytes' % int(s.st_size)
    print
    print ' st_uid:       %r' % s.st_uid
    print ' st_gid:       %r' % s.st_gid
    print ' st_mode:      %r' % s.st_mode


@local_handler(files_only=True)
def ledit(shell, path):
    """ Edit file in editor. """
    shell.localhost.run("vim '%s'" % esc1(path))


class RootHandler(SCPHandler):
    subhandlers = {
            'clear': Clear,
            'exit': Exit,

            'ls': ls,
            'cd': cd,
            'pwd': Pwd,
            'stat': stat_handler,
            'view': view,
            'edit': edit,
            'connect': Connect,

            'lls': lls,
            'lcd': lcd,
            'lpwd': Lpwd,
            'lstat': lstat,
            'lview': lview,
            'ledit': ledit,
            'lconnect': Lconnect,

            'put': put,
            'get': get,
    }

    def complete_subhandlers(self, part):
        # Built-ins
        for name, h in self.subhandlers.items():
            if name.startswith(part):
                yield name, h(self.shell)

    def get_subhandler(self, name):
        if name in self.subhandlers:
            return self.subhandlers[name](self.shell)



class Shell(CLInterface):
    """
    Interactive secure copy shell.
    """
    def __init__(self, pty, host, logger_interface, clone_shell=None): # XXX: import clone_shell
        assert issubclass(host, Host)
        assert pty

        self.host = type('RemoteSCPHost', (CacheMixin, host), { })(pty=pty, logger=logger_interface)
        self.host.fill_cache(pty)
        self.localhost = LocalHost(pty=pty, logger=logger_interface)
        self.localhost.host_context._chdir(os.getcwd())
        self.pty = pty
        self.root_handler = RootHandler(self)

        CLInterface.__init__(self, self.pty, RootHandler(self))

        # Caching for autocompletion (directory -> list of content.)
        self._cd_cache = { }

    @property
    def prompt(self):
        get_name = lambda p: os.path.split(p)[-1]

        return [
                    ('local:%s' % get_name(self.localhost.getcwd() or ''), 'yellow'),
                    (' ~ ', 'cyan'),
                    ('%s:' % self.host.slug, 'yellow'),
                    (get_name(self.host.getcwd() or ''), 'yellow'),
                    (' > ', 'cyan'),
                ]

########NEW FILE########
__FILENAME__ = shell
from deployer.cli import CLInterface, Handler, HandlerType
from deployer.console import Console
from deployer.console import NoInput
from deployer.exceptions import ActionException
from deployer.inspection import Inspector, PathType
from deployer.node import Env, IsolationIdentifierType

from inspect import getfile
from itertools import groupby

from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

import deployer
import inspect
import socket
import sys
import termcolor


__all__ = ('Shell', )


# Handler types

class ActionType(HandlerType):
    def __init__(self, color):
        self.color = color
        self.postfix = '*'

def type_of_node(node):
    group = Inspector(node).get_group()
    return NodeType(group.color)

def type_of_action(action):
    group = action.node_group
    return ActionType(group.color)

class NodeType(HandlerType):
    def __init__(self, color):
        self.color = color

class BuiltinType(HandlerType):
    color = 'cyan'


# Utils for navigation


class ShellHandler(Handler):
    def __init__(self, shell):
        self.shell = shell


class AUTOCOMPLETE_TYPE:
    NODE = 'NODE'
    ACTION = 'ACTION'
    ACTION_AND_ARGS = 'ACTION_AND_ARGS'

    QUERY_ATTRIBUTE = 'QUERY_ATTRIBUTE'
    PROPERTY_ATTRIBUTE = 'PROPERTY'
    CONSTANT_ATTRIBUTE = 'CONNSTANT' # TODO: inspection on this type.


class NodeACHandler(ShellHandler):
    """
    ShellHandler which implements node path completion.  Depending on the
    ``autocomplete_types`` attribute, it can complete on nodes, actions, or any
    other attribute value.
    """
    autocomplete_types = [AUTOCOMPLETE_TYPE.NODE]

    def __init__(self, shell, node=None, attr_name=None, args=None):
        ShellHandler.__init__(self, shell)
        self._root = node is None
        self.node = node or shell.state._node
        self.attr_name = attr_name
        self.args = args or []

    @property
    def is_leaf(self):
        return self.get_type() is not None

    def get_type(self):
        """
        Return the ``AUTOCOMPLETE_TYPE`` for this node.
        """
        insp = Inspector(self.node)
        atypes = self.autocomplete_types

        if AUTOCOMPLETE_TYPE.NODE in atypes and not self.attr_name:
            return AUTOCOMPLETE_TYPE.NODE

        if AUTOCOMPLETE_TYPE.ACTION in atypes and not self.attr_name and insp.is_callable():
            return AUTOCOMPLETE_TYPE.ACTION

        if AUTOCOMPLETE_TYPE.ACTION in atypes and insp.has_action(self.attr_name):
            return AUTOCOMPLETE_TYPE.ACTION

        if AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE in atypes and insp.has_query(self.attr_name):
            return AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE

        if AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE in atypes and insp.has_property(self.attr_name):
            return AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE

    @property
    def handler_type(self):
        if self._root:
            return BuiltinType()
        else:
            node_color = Inspector(self.node).get_group().color

            def get_postfix():
                type_ = self.get_type()
                if type_ == AUTOCOMPLETE_TYPE.ACTION:
                    return '*'

                if type_ == AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE:
                    return '?'

                if type_ == AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE:
                    return '@'

                return ''

            class Type(HandlerType):
                color = node_color
                postfix = get_postfix()
            return Type()

    def get_subhandler(self, name):
        parent = self.node.parent
        cls = self.__class__

        # Current node
        if name == '.':
            return self

        # Previous location
        if name == '-' and self.shell.state.can_cdback:
            return cls(self.shell, self.shell.state.previous_node)

        # Root node
        if parent and name == '/':
            root = Inspector(parent).get_root()
            return cls(self.shell, root)

        # Parent node
        if parent and name == '..':
            return cls(self.shell, parent)

        # TODO: ~ --> home.

        # Isolation
        elif name.startswith(':'):
            ids = tuple(name[1:].split(':'))
            try:
                node = Inspector(self.node).get_isolation(ids, IsolationIdentifierType.HOSTS_SLUG)
                return cls(self.shell, node)
            except AttributeError: pass

        # Childnodes
        try:
            node = Inspector(self.node).get_childnode(name)
            return cls(self.shell, node)
        except AttributeError: pass

        # Actions
        if AUTOCOMPLETE_TYPE.ACTION in self.autocomplete_types:
            try:
                action = Inspector(self.node).get_action(name)
                return cls(self.shell, self.node, name)
            except AttributeError: pass

        if AUTOCOMPLETE_TYPE.ACTION_AND_ARGS in self.autocomplete_types and self.attr_name:
            return cls(self.shell, self.node, self.attr_name, self.args + [name])

        # Queries
        if AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE in self.autocomplete_types:
            try:
                action = Inspector(self.node).get_query(name)
                return cls(self.shell, self.node, action.name)
            except AttributeError:
                pass

        # Properties
        if AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE in self.autocomplete_types:
            try:
                action = Inspector(self.node).get_property(name)
                return cls(self.shell, self.node, action.name)
            except AttributeError:
                pass

    def complete_subhandlers(self, part):
        parent = self.node.parent
        include_private = part.startswith('_')
        cls = self.__class__

        # No autocompletion anymore after an action has been typed.
        if self.attr_name:
            return

        # Current node
        if '.'.startswith(part):
            yield '.', self

        # Previous location
        if '-'.startswith(part) and self.shell.state.can_cdback:
            yield '-', cls(self.shell, self.shell.state.previous_node)

        # Root node
        if parent and '/'.startswith(part):
            root = Inspector(parent).get_root()
            yield '/', cls(self.shell, root)

        # Parent node
        if parent and '..'.startswith(part):
            yield ('..', cls(self.shell, parent))

        # TODO: ~ -->> Home

        # Isolation
        for i, n in Inspector(self.node).iter_isolations(IsolationIdentifierType.HOSTS_SLUG):
            if i:
                # Prefix all isolations with colons.
                name = ':%s' % ':'.join(i)
                if name.startswith(part):
                    yield name, cls(self.shell, n)

        # Childnodes:
        # Note: when an underscore has been typed, include private too.
        for c in Inspector(self.node).get_childnodes(include_private=include_private):
            name = Inspector(c).get_name()
            if name.startswith(part):
                yield name, cls(self.shell, c)

        # Actions
        if AUTOCOMPLETE_TYPE.ACTION in self.autocomplete_types:
            for action in Inspector(self.node).get_actions(include_private=include_private):
                if action.name.startswith(part):
                    yield action.name, cls(self.shell, self.node, action.name)

        # Queries
        if AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE in self.autocomplete_types:
            for action in Inspector(self.node).get_queries(include_private=include_private):
                if action.name.startswith(part):
                    yield action.name, cls(self.shell, self.node, action.name)

        # Properties
        if AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE in self.autocomplete_types:
            for action in Inspector(self.node).get_properties(include_private=include_private):
                if action.name.startswith(part):
                    yield action.name, cls(self.shell, self.node, action.name)


    def __call__(self):
        raise NotImplementedError


# Handlers


class Version(ShellHandler):
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        print termcolor.colored('  deployer library, version: ', 'cyan'),
        print termcolor.colored(deployer.__version__, 'red')
        print termcolor.colored('  Host:                      ', 'cyan'),
        print termcolor.colored(socket.gethostname(), 'red')
        print termcolor.colored('  Root node class:           ', 'cyan'),
        print termcolor.colored(self.shell.root_node.__module__, 'red'),
        print termcolor.colored('  <%s>' % self.shell.root_node.__class__.__name__, 'red')


class Connect(NodeACHandler):
    """
    Open interactive SSH connection with this host.
    """
    def __call__(self):
        from deployer.contrib.nodes import connect

        class Connect(connect.Connect):
            class Hosts:
                host = self.node.hosts.get_hosts()

        env = Env(Connect(), self.shell.pty, self.shell.logger_interface)

        # Run as any other action. (Nice exception handling, e.g. in case of NoInput on host selection.)
        try:
            env.with_host()
        except ActionException as e:
            pass
        except Exception as e:
            self.shell.logger_interface.log_exception(e)


class Run(NodeACHandler):
    """
    Run a shell command on all hosts in the current node.
    """
    use_sudo = False

    def get_command(self):
        try:
            text = '[SUDO] Enter command' if self.use_sudo else 'Enter command'
            return Console(self.shell.pty).input(text)
        except NoInput:
            return

    def __call__(self):
        from deployer.node import Node

        # Print info
        host_count = len(self.node.hosts)

        if host_count == 0:
            print 'No hosts found at this node. Nothing to execute.'
            return

        print 'Command will be executed on %i hosts:' % host_count
        for h in self.node.hosts:
            print '   - %s (%s)' % (h.slug, h.address)

        command = self.get_command()
        if not command:
            return

        # Run
        use_sudo = self.use_sudo

        class RunNode(Node):
            class Hosts:
                host = self.node.hosts.get_hosts()

            def run(self):
                if use_sudo:
                    self.hosts.sudo(command)
                else:
                    self.hosts.run(command)

        env = Env(RunNode(), self.shell.pty, self.shell.logger_interface)

        # Run as any other action. (Nice exception handling, e.g. in case of
        # NoInput on host selection.)
        try:
            env.run()
        except ActionException as e:
            pass
        except Exception as e:
            self.shell.logger_interface.log_exception(e)


class RunWithSudo(Run):
    use_sudo = True


class Find(NodeACHandler):
    def __call__(self):
        def _list_nested_nodes(node, prefix):
            for a in Inspector(node).get_actions():
                yield '%s %s' % (prefix, termcolor.colored(a.name, Inspector(a.node).get_group().color))

            for c in Inspector(node).get_childnodes():
                # Check the parent, to avoid loops.
                if c.parent == node:
                    name = Inspector(c).get_name()
                    for i in _list_nested_nodes(c, '%s %s' % (prefix, termcolor.colored(name, Inspector(c).get_group().color))):
                        yield i

        Console(self.shell.pty).lesspipe(_list_nested_nodes(self.node, ''))


class Inspect(NodeACHandler):
    """
    Inspection of the current node. Show host mappings and other information.
    """
    autocomplete_types = [
            AUTOCOMPLETE_TYPE.NODE,
            AUTOCOMPLETE_TYPE.ACTION,
            AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE,
            AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE ]

    def __call__(self):
        type_ = self.get_type()

        if type_ == AUTOCOMPLETE_TYPE.NODE:
            self._inspect_node()

        if type_ == AUTOCOMPLETE_TYPE.ACTION:
            self._inspect_action()

        if type_ == AUTOCOMPLETE_TYPE.QUERY_ATTRIBUTE:
            self._inspect_query_attribute()

        if type_ == AUTOCOMPLETE_TYPE.PROPERTY_ATTRIBUTE:
            self._inspect_property_attribute()

    def _inspect_node(self):
        console = Console(self.shell.pty)

        def inspect():
            # Print full name
            yield termcolor.colored('  Node:    ', 'cyan') + \
                  termcolor.colored(Inspector(self.node).get_full_name(), 'yellow')

            # Print mro
            yield termcolor.colored('  Mro:', 'cyan')
            i = 1
            for m in self.node.__class__.__mro__:
                if m.__module__ != 'deployer.node' and m != object:
                    yield termcolor.colored('              %i ' % i, 'cyan') + \
                          termcolor.colored('%s.' % m.__module__, 'red') + \
                          termcolor.colored('%s' % m.__name__, 'yellow')
                    i += 1

            # File names
            yield termcolor.colored('  Files:', 'cyan')
            i = 1
            for m in self.node.__class__.__mro__:
                if m.__module__ != 'deployer.node' and m != object:
                    yield termcolor.colored('              %i ' % i, 'cyan') + \
                          termcolor.colored(getfile(m), 'red')
                    i += 1

            # Print host mappings
            yield termcolor.colored('  Hosts:', 'cyan')

            for role in sorted(self.node.hosts._hosts.keys()):
                items = self.node.hosts._hosts[role]
                yield termcolor.colored('         "%s"' % role, 'yellow')
                i = 1
                for host in sorted(items, key=lambda h:h.slug):
                    yield termcolor.colored('            %3i ' % i, 'cyan') + \
                          termcolor.colored('%-25s (%s)' % (host.slug, getattr(host, 'address', '')), 'red')
                    i += 1

            # Print the first docstring (look to the parents)
            for m in self.node.__class__.__mro__:
                if m.__module__ != 'deployer.node' and m != object and m.__doc__:
                    yield termcolor.colored('  Docstring:\n', 'cyan') + \
                          termcolor.colored(m.__doc__ or '<None>', 'red')
                    break

            # Actions
            yield termcolor.colored('  Actions:', 'cyan')

            def item_iterator():
                for a in Inspector(self.node).get_actions():
                    yield termcolor.colored(a.name, 'red'), len(a.name)

            for line in console.in_columns(item_iterator(), margin_left=13):
                yield line

            # Nodes
            yield termcolor.colored('  Sub nodes:', 'cyan')

                # Group by node group
            grouper = lambda c:Inspector(c).get_group()
            for group, nodes in groupby(sorted(Inspector(self.node).get_childnodes(), key=grouper), grouper):
                yield termcolor.colored('         "%s"' % group.name, 'yellow')

                # Create iterator for all the items in this group
                def item_iterator():
                    for n in nodes:
                        name = Inspector(n).get_name()

                        if n.parent == self.node:
                            text = termcolor.colored(name, type_of_node(n).color)
                            length = len(name)
                        else:
                            full_name = Inspector(n).get_full_name()
                            text = termcolor.colored('%s -> %s' % (name, full_name), type_of_node(n).color)
                            length = len('%s -> %s' % (name, full_name))
                        yield text, length

                # Show in columns
                for line in console.in_columns(item_iterator(), margin_left=13):
                    yield line

        console.lesspipe(inspect())

    def _inspect_action(self):
        console = Console(self.shell.pty)
        action = Inspector(self.node).get_action(self.attr_name)

        def run():
            yield termcolor.colored('  Action name:   ', 'cyan') + \
                  termcolor.colored(self.attr_name, 'yellow')
            yield termcolor.colored('  __repr__:      ', 'cyan') + \
                  termcolor.colored(repr(action._func), 'yellow')
            yield termcolor.colored('  Node:          ', 'cyan') + \
                  termcolor.colored(repr(self.node), 'yellow')
        console.lesspipe(run())

    def _get_env(self):
        """
        Created a sandboxed environment for evaluation of attributes.
        (attributes shouldn't have side effects on servers, so sandboxing is fine.)
        Returns an ``Env`` object.
        """
        env = Env(self.node, self.shell.pty, self.shell.logger_interface, is_sandbox=True)
        return Console(self.shell.pty).select_node_isolation(env)

    def _inspect_query_attribute(self):
        console = Console(self.shell.pty)
        query = Inspector(self.node).get_query(self.attr_name).query

        def run():
            yield termcolor.colored('  Node:       ', 'cyan') + \
                  termcolor.colored(Inspector(self.node).get_full_name(), 'yellow')
            yield termcolor.colored('  Filename:   ', 'cyan') + \
                  termcolor.colored(query._filename, 'yellow')
            yield termcolor.colored('  Line:       ', 'cyan') + \
                  termcolor.colored(query._line, 'yellow')
            yield termcolor.colored('  Expression: ', 'cyan') + \
                  termcolor.colored(repr(query.query), 'yellow')
            yield ''

            # Execute query in sandboxed environment.
            yield 'Trace query:'
            try:
                insp = Inspector(self._get_env())
                result = insp.trace_query(self.attr_name)
            except Exception as e:
                yield 'Failed to execute query: %r' % e
                return

            # Print query and all subqueries with their results.
            for subquery in result.walk_through_subqueries():
                yield termcolor.colored(repr(subquery[0]), 'cyan')
                yield '    %s' % subquery[1]

        console.lesspipe(run())

    def _inspect_property_attribute(self):
        console = Console(self.shell.pty)
        action = Inspector(self.node).get_property(self.attr_name)

        def run():
            yield termcolor.colored('  Property name:   ', 'cyan') + \
                  termcolor.colored(self.attr_name, 'yellow')
            yield termcolor.colored('  __repr__:      ', 'cyan') + \
                  termcolor.colored(repr(action._func), 'yellow')
            yield termcolor.colored('  Node:          ', 'cyan') + \
                  termcolor.colored(repr(self.node), 'yellow')

            # Value
            try:
                value = getattr(self._get_env(), self.attr_name)

                yield termcolor.colored('  Value:          ', 'cyan') + \
                      termcolor.colored(repr(value), 'yellow')
            except Exception as e:
                yield termcolor.colored('  Value:          ', 'cyan') + \
                      termcolor.colored('Failed to evaluate value...', 'yellow')
        console.lesspipe(run())


class Cd(NodeACHandler):
    def __call__(self):
        self.shell.state.cd(self.node)


class Ls(NodeACHandler):
    """
    List subnodes and actions in the current node.
    """
    def __call__(self):
        w = self.shell.stdout.write
        console = Console(self.shell.pty)

        def run():
            # Print nodes
            if Inspector(self.node).get_childnodes():
                yield 'Child nodes:'

                def column_iterator():
                    for c in Inspector(self.node).get_childnodes():
                        name = Inspector(c).get_name()
                        yield termcolor.colored(name, type_of_node(c).color), len(name)
                for line in console.in_columns(column_iterator()):
                    yield line

            # Print actions
            if Inspector(self.node).get_actions():
                yield 'Actions:'

                def column_iterator():
                    for a in Inspector(self.node).get_actions():
                        yield termcolor.colored(a.name, type_of_action(a).color), len(a.name)
                for line in console.in_columns(column_iterator()):
                    yield line

        console.lesspipe(run())

class Pwd(NodeACHandler):
    """
    Print current node path.
    ``pwd``, like "Print working Directory" in the Bash shell.
    """
    def __call__(self):
        result = [ ]

        for node, name in Inspector(self.node).get_path(PathType.NODE_AND_NAME):
            color = Inspector(node).get_group().color
            result.append(termcolor.colored(name, color))

        sys.stdout.write(termcolor.colored('/', 'cyan'))
        sys.stdout.write(termcolor.colored('.', 'cyan').join(result) + '\n')
        sys.stdout.flush()


class SourceCode(NodeACHandler):
    """
    Print the source code of a node.
    """
    def __call__(self):
        options = []

        for m in self.node.__class__.__mro__:
            if m.__module__ != 'deployer.node' and m != object:
                options.append( ('%s.%s' % (
                      termcolor.colored(m.__module__, 'red'),
                      termcolor.colored(m.__name__, 'yellow')), m) )

        if len(options) > 1:
            try:
                node_class = Console(self.shell.pty).choice('Choose node definition', options)
            except NoInput:
                return
        else:
            node_class = options[0][1]

        def run():
            try:
                # Retrieve source
                source = inspect.getsource(node_class)

                # Highlight code
                source = highlight(source, PythonLexer(), TerminalFormatter())

                for l in source.split('\n'):
                    yield l.rstrip('\n')
            except IOError:
                yield 'Could not retrieve source code.'

        Console(self.shell.pty).lesspipe(run())


class Scp(NodeACHandler):
    """
    Open a secure copy shell at this node.
    """
    def __call__(self):
        # Choose host.
        hosts = self.node.hosts.get_hosts()
        if len(hosts) == 0:
            print 'No hosts found'
            return
        elif len(hosts) == 1:
            host = hosts.copy().pop()
        else:
            # Choose a host.
            options = [ (h.slug, h) for h in hosts ]
            try:
                host = Console(self.shell.pty).choice('Choose a host', options, allow_random=True)
            except NoInput:
                return

        # Start scp shell
        from deployer.scp_shell import Shell
        Shell(self.shell.pty, host, self.shell.logger_interface).cmdloop()


class SetOption(ShellHandler):
    """
    Change shell options.
    """
    handler_type = BuiltinType()

    def complete_subhandlers(self, part):
        for option_name, option in self.shell.options.items():
            if option_name.startswith(part):
                yield option_name, SetOptionName(self.shell, option)

    def get_subhandler(self, name):
        for option_name, option in self.shell.options.items():
            if option_name == name:
                return SetOptionName(self.shell, option)


class SetOptionName(ShellHandler):
    handler_type = BuiltinType()

    def __init__(self, shell, option):
        ShellHandler.__init__(self, shell)
        self.option = option

    def complete_subhandlers(self, part):
        for value in self.option.values:
            if value.startswith(part):
                yield value, SetOptionNameValue(self.shell, self.option, value)

    def get_subhandler(self, name):
        if name in self.option.values:
            return SetOptionNameValue(self.shell, self.option, name)


class SetOptionNameValue(ShellHandler):
    is_leaf = True
    handler_type = BuiltinType()

    def __init__(self, shell, option, value):
        ShellHandler.__init__(self, shell)
        self.option = option
        self.value = value

    def __call__(self):
        self.option.set(self.value)


class ShowOptions(ShellHandler):
    """
    Show the current shell settings.
    """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        for name, option in self.shell.options.items():
            print '%-20s %s' % (name, option.get())


class Exit(ShellHandler):
    """
    Quit the deployment shell.
    """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        self.shell.exit()


class Return(ShellHandler):
    """
    Return from a subshell (which was spawned by a previous node.)
    """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        self.shell.state = self.shell.state.return_state


class Clear(ShellHandler):
    """
    Clear window.
    """
    is_leaf = True
    handler_type = BuiltinType()

    def __call__(self):
        sys.stdout.write('\033[2J\033[0;0H')
        sys.stdout.flush()


class Node(NodeACHandler):
    """
    Node node.
    """
    sandbox = False
    autocomplete_types = [
            AUTOCOMPLETE_TYPE.ACTION,
            AUTOCOMPLETE_TYPE.ACTION_AND_ARGS,
            ]

    def __call__(self):
        # Execute
        logger_interface = self.shell.logger_interface

        try:
            # Create env
            env = Env(self.node, self.shell.pty, logger_interface, is_sandbox=self.sandbox)

            # Call action
            if self.attr_name is not None:
                result = getattr(env, self.attr_name)(*self.args)
                suppress_result = Inspector(self.node).suppress_result_for_action(self.attr_name)
            else:
                result = env(*self.args)
                suppress_result = False

            # When the result is a subnode, start a subshell.
            def handle_result(result):
                if isinstance(result, deployer.node.Env):
                    print ''
                    print 'Starting subshell ...'
                    self.shell.state = ShellState(result._node, return_state=self.shell.state)

                # Otherwise, print result
                elif result is not None and not suppress_result:
                    print result

            if isinstance(result, list):
                for r in result:
                    handle_result(r)
            else:
                handle_result(result)

        except ActionException as e:
            # Already sent to logger_interface in the Action itself.
            pass

        except Exception as e:
            logger_interface.log_exception(e)


class Sandbox(Node):
    sandbox = True


class RootHandler(ShellHandler):
    subhandlers = {
            'cd': Cd,
            'clear': Clear,
            'exit': Exit,
            'find': Find,
            'ls': Ls,
            'sandbox': Sandbox,
            'pwd': Pwd,
            'set-option': SetOption,
            'show-options': ShowOptions,
            '--connect': Connect,
            '--inspect': Inspect,
            '--run': Run,
            '--run-with-sudo': RunWithSudo,
            '--version': Version,
            '--source-code': SourceCode,
            '--scp': Scp,
    }

    @property
    def sandboxed_current_node(self):
        return Sandbox(self.shell.state._node, self.shell)

    def complete_subhandlers(self, part):
        """
        Return (name, Handler) subhandler pairs.
        """
        # Default built-ins
        for name, h in self.subhandlers.items():
            if name.startswith(part):
                yield name, h(self.shell)

        # Return when the shell supports it
        if self.shell.state.can_return and 'return'.startswith(part):
            yield 'return', Return(self.shell)

        # Extensions
        for name, h in self.shell.extensions.items():
            if name.startswith(part):
                yield name, h(self.shell)

        # Nodes.
        for name, h in Node(self.shell).complete_subhandlers(part):
            yield name, h

    def get_subhandler(self, name):
        # Current node
        if name == '.':
            return Node(self.shell)

        # Default built-ins
        if name in self.subhandlers:
            return self.subhandlers[name](self.shell)

        if self.shell.state.can_return and name == 'return':
            return Return(self.shell)

        # Extensions
        if name in self.shell.extensions:
            return self.shell.extensions[name](self.shell)

        # Nodes.
        return Node(self.shell).get_subhandler(name)


class ShellState(object):
    """
    When we are moving to a certain position in the node tree.
    """
    def __init__(self, subnode, return_state=None):
        self._return_state = return_state
        self._node = subnode
        self._prev_node = None

    def clone(self):
        s = ShellState(self._node, self._return_state)
        s._prev_node = self._prev_node
        return s

    def __repr__(self):
        return 'ShellState(node=%r)' % self._node

    @property
    def prompt(self):
        # Returns a list of (text,color) tuples for the prompt.
        result = []
        for node in Inspector(self._node).get_path(path_type=PathType.NODE_ONLY):
            if result:
                result.append( ('.', None) )

            name = Inspector(node).get_name()
            ii = Inspector(node).get_isolation_identifier()
            color = Inspector(node).get_group().color

            result.append( (name, color) )
            if ii:
                result.append( ('[%s]' % ii, color) )
        return result

    def cd(self, target_node):
        self._prev_node = self._node
        self._node = target_node

    @property
    def can_return(self):
        return bool(self._return_state)

    @property
    def return_state(self):
        return self._return_state

    @property
    def can_cdback(self):
        return bool(self._prev_node)

    @property
    def previous_node(self):
         return self._prev_node

    @property
    def node(self):
        return self._node



class Shell(CLInterface):
    """
    Deployment shell.
    """
    def __init__(self, root_node, pty, options, logger_interface, clone_shell=None):
        self.root_node = root_node
        self.pty = pty
        self.options = options
        self.logger_interface = logger_interface

        if clone_shell:
            self.state = clone_shell.state.clone()
        else:
            self._reset_navigation()

        # CLI interface
        self.root_handler = RootHandler(self)
        CLInterface.__init__(self, self.pty, self.root_handler)

    def cd(self, cd_path):
        for p in cd_path:
            try:
                self.state.cd(Inspector(self.state._node).get_childnode(p))
            except AttributeError:
                print 'Unknown path given.'
                return

    def open_scp_shell(self):
        self.root_handler.get_subhandler('--scp')()

    def run_action(self, action_name, *a, **kw):
        """
        Run a deployment command at the current shell state.
        """
        env = Env(self.state._node, self.pty, self.logger_interface, is_sandbox=False)
        return getattr(env, action_name)(*a, **kw)

    @property
    def extensions(self):
        # Dictionary with extensions to the root handler
        return { }

    def _reset_navigation(self):
        self.state = ShellState(self.root_node)

    def exit(self):
        """
        Exit cmd loop.
        """
        if self.state.can_return:
            self.state = self.state.return_state
            self.ctrl_c()
        else:
            super(Shell, self).exit()

    @property
    def prompt(self):
        """
        Return a list of [ (text, color) ] tuples representing the prompt.
        """
        return self.state.prompt + [ (' > ', 'cyan') ]

########NEW FILE########
__FILENAME__ = std
import sys
import threading
import termios
import tty


class TeeStd(object):
    """
    Like the unix 'tee' command.
    Wrapper around an std object, which allows other handlers to listen
    along.
    """
    _names = ('_std', '_read_listeners', 'add_read_listener', 'remove_read_listener', 'read')

    def __init__(self, std):
        self._std = std
        self._read_listeners = []

    def add_read_listener(self, handler):
        self._read_listeners.append(handler)

    def remove_read_listener(self, handler):
        self._read_listeners.remove(handler)

    def read(self, *a):
        data = self._std.read(*a)

        for l in self._read_listeners:
            l(data)

        return data

    def __getattribute__(self, name):
        if name in TeeStd._names:
            return object.__getattribute__(self, name)
        else:
            return getattr(self._std, name)

    def __setattr__(self, name, value):
        if name in TeeStd._names:
            object.__setattr__(self, name, value)
        else:
            setattr(self._std, name, value)


class Std(object):
    """
    Threading aware proxy for sys.stdin/sys.stdout
    This will make sure that print statements are automatically routed to the
    correct pseudo terminal.
    This is the only one that should be used in the whole deployer framework.
    """
    def __init__(self, fallback, mode):
        # `fallback` is the default fallback, in case none has been set for
        # the current thread.
        self._f = { }
        self._fallback = fallback

    def get_handler(self):
        t = threading.currentThread()
        return self._f.get(t, self._fallback)

    def set_handler(self, value):
        t = threading.currentThread()
        self._f[t] = value

    def del_handler(self):
        t = threading.currentThread()
        del self._f[t]

    def __getattribute__(self, name):
        """
        Route all attribute lookups to the stdin/out object
        that belongs to the current thread.
        """
        if name in ('__init__', 'get_handler', 'set_handler', 'del_handler',
                '__getattribute__', '__eq__', '__setattr__', '_f', '_fallback'):
            return object.__getattribute__(self, name)
        else:
            return getattr(self.get_handler(), name)

    def __eq__(self, value):
        return self.get_handler() == value

    def __setattr__(self, name, value):
        """
        Redirect setting of attribute to the thread's std.
        """
        if name in ('_f', '_fallback'):
            object.__setattr__(self, name, value)
        else:
            setattr(self.get_handler(), name, value)


has_been_setup = False

def setup():
    """
    Make sure that sys.stdin and sys.stdout are replaced by an Std object.
    """
    global has_been_setup
    if not has_been_setup:
        has_been_setup = True
        sys.stdin = Std(sys.__stdin__, 'r')
        sys.stdout = Std(sys.__stdout__, 'w')


class raw_mode(object):
    """
    with raw_mode(stdin):
        ''' the pseudo-terminal stdin is now used in raw mode '''
    """
    def __init__(self, stdin):
        self.stdin = stdin

        if self.stdin.isatty():
            self.attrs_before = termios.tcgetattr(self.stdin)

    def __enter__(self):
        if self.stdin.isatty():
            # NOTE: On os X systems, using pty.setraw() fails. Therefor we are using this:
            newattr = termios.tcgetattr(self.stdin.fileno())
            newattr[tty.LFLAG] = newattr[tty.LFLAG] & ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
            termios.tcsetattr(self.stdin.fileno(), termios.TCSANOW, newattr)

    def __exit__(self, *a, **kw):
        if self.stdin.isatty():
            termios.tcsetattr(self.stdin.fileno(), termios.TCSANOW, self.attrs_before)

########NEW FILE########
__FILENAME__ = network
import re

__all__ = ('parse_ifconfig_output', 'IfConfig', 'NetworkInterface')


class NetworkInterface(object):
    """
    Information about a single network interface.
    """
    def __init__(self, name='eth0'):
        self._name = name
        self._ip = None

    @property
    def name(self):
        """
        Name of the network interface. e.g. "eth0".
        """
        return self._name

    @property
    def ip(self):
        """
        IP address of the network interface. e.g. "127.0.0.1"
        """
        return self._ip

    def __repr__(self):
        return 'NetworkInterface(name=%r, ip=%r)' % (self.name, self.ip)


class IfConfig(object):
    """
    Container for the network settings, found by `ifconfig`.
    This contains a list of :class:`NetworkInterface`.
    """
    def __init__(self):
        self._interfaces = []

    @property
    def interfaces(self):
        """
        List of all :class:`NetworkInterface` objects.
        """
        return self._interfaces

    def __repr__(self):
        return 'IfConfig(interfaces=%r)' % self.interfaces

    def get_interface(self, name):
        """
        Return the :class:`NetworkInterface` object, given an interface name
        (e.g. "eth0") or raise `AttributeError`.
        """
        for i in self.interfaces:
            if i.name == name:
                return i
        raise AttributeError

    def get_address(self, ip):
        """
        Return the :class:`NetworkInterface` object, given an IP addres
        (e.g. "127.0.0.1") or raise `AttributeError`.
        """
        for i in self.interfaces:
            if i.ip == ip:
                return i
        raise AttributeError


def parse_ifconfig_output(output, only_active_interfaces=True):
    """
    Parse the output of an `ifconfig` command.

    :returns: A list of :class:`IfConfig` objects.

    Example usage:
    ::
        ifconfig = parse_ifconfig_output(host.run('ifconfig'))
        interface = ifconfig.get_interface('eth0')
        print interface.ip
    """
    ifconfig = IfConfig()
    current_interface = None

    for l in output.split('\n'):
        if l:
            # At any line starting with eth0, lo, tap7, etc..
            # Start a new interface.
            if not l[0].isspace():
                current_interface = NetworkInterface(l.split()[0].rstrip(':'))
                ifconfig.interfaces.append(current_interface)
                l = ' '.join(l.split()[1:])

            if current_interface:
                # If this line contains 'inet'
                for inet_addr in re.findall(r'inet (addr:)?(([0-9]*\.){3}[0-9]*)', l):
                    current_interface._ip = inet_addr[1]

    # Return only the interfaces that have an IP address.
    if only_active_interfaces:
        ifconfig._interfaces = filter(lambda i: i.ip, ifconfig._interfaces)

    return ifconfig

########NEW FILE########
__FILENAME__ = string_utils

__all__ = (
        'esc1',
        'esc2',
        'indent',
)

def esc2(string):
    """
    Escape double quotes
    """
    return string.replace('"', r'\"')


def esc1(string):
    """
    Escape single quotes, mainly for use in shell commands. Single quotes
    are usually preferred above double quotes, because they never do shell
    expension inside. e.g.

    ::

        class HelloWorld(Node):
            def run(self):
                self.hosts.run("echo '%s'" % esc1("Here's some text"))
    """
    return string.replace("'", r"'\''")


def indent(string, prefix='    '):
    """
    Indent every line of this string.
    """
    return ''.join('%s%s\n' % (prefix, s) for s in string.split('\n'))


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# python-deploy-framework documentation build configuration file, created by
# sphinx-quickstart on Thu Jun 20 22:12:13 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.graphviz' ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'python-deploy-framework'
copyright = u'2013, Jonathan Slenders'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.12'
# The full version, including alpha/beta/rc tags.
release = '0.1.12'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if on_rtd:
    html_theme = 'default'
else:
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except ImportError:
        html_theme = 'pyramid'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'python-deploy-frameworkdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'python-deploy-framework.tex', u'python-deploy-framework Documentation',
   u'Jonathan Slenders', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'python-deploy-framework', u'python-deploy-framework Documentation',
     [u'Jonathan Slenders'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'python-deploy-framework', u'python-deploy-framework Documentation',
   u'Jonathan Slenders', 'python-deploy-framework', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = simple_deployment
#!/usr/bin/env python
"""
Start this file as "./simple_deployment run"

Then you can for instance do this:
    > cd examples
    > say_hello
    > --connect
    > exit
"""

from deployer.host import LocalHost
from deployer.node import Node


class example_settings(Node):
    # Run everything on the local machine
    class Hosts:
        host = { LocalHost }

    # A nested node with some examples.
    class examples(Node):
        def say_hello(self):
            self.hosts.run('echo hello world')

        def directory_listing_in_superuser_home(self):
            self.hosts.sudo('ls ~')

        def return_hello_world(self):
            return 'Hello world'

        def raise_exception(self):
            raise Exception('Custom exception')


if __name__ == '__main__':
    # Start an interactive shell.
    from deployer.client import start
    start(example_settings)

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

from tests.host_container_test import *
from tests.host_test import *
from tests.inspector_test import *
from tests.node_test import *
from tests.query_test import *
from tests.utils_test import *
from tests.pty_test import *
from tests.console_test import *

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = console_test
import unittest

from deployer.console import Console
from deployer.pseudo_terminal import DummyPty


class ConsoleTest(unittest.TestCase):
    def test_print_warning(self):
        p = DummyPty()
        c = Console(p)
        c.warning('this is a warning')
        self.assertIn('this is a warning', p.get_output())

    def test_input(self):
        # Test normal input
        p = DummyPty(input_data='my-input\n')
        result = Console(p).input('input question')
        output = p.get_output()

        self.assertEqual(result, 'my-input')
        self.assertIn('input question', output)

        # Test default input
        p = DummyPty(input_data='\n')
        result = Console(p).input('input question', default='default-value')
        self.assertEqual(result, 'default-value')

        p = DummyPty(input_data='my-input\n')
        p.interactive = True # We have to set interactive=True, otherwise
                             # Console will take the default value anyway.
        result = Console(p).input('input question', default='default-value')
        self.assertEqual(result, 'my-input')

    def test_confirm(self):
        question = 'this is my question'

        # Test various inputs
        for inp, result in [
                ('yes', True),
                ('y', True),
                ('no', False),
                ('n', False) ]:

            p = DummyPty(input_data='%s\n' % inp)
            c = Console(p)
            returnvalue = c.confirm(question)

            self.assertEqual(returnvalue, result)
            self.assertIn(question, p.get_output())

        # Test default
        p = DummyPty(input_data='\n')
        c = Console(p)
        self.assertEqual(c.confirm('', default=True), True)
        self.assertEqual(c.confirm('', default=False), False)

########NEW FILE########
__FILENAME__ = host_container_test
import os
import tempfile
import unittest

from deployer.host_container import HostsContainer, HostContainer
from deployer.pseudo_terminal import DummyPty

from .our_hosts import LocalHost1, LocalHost2, LocalHost3, LocalHost4, LocalHost5
from .our_hosts import LocalSSHHost1, LocalSSHHost2, LocalSSHHost3, LocalSSHHost4, LocalSSHHost5


class HostsContainerTest(unittest.TestCase):
    def get_hosts(self):
        """ Use local hosts. """
        class H:
            h1 =  LocalHost1
            h2 =  LocalHost2
            h3 =  LocalHost3
            h4 =  LocalHost4
            h5 =  LocalHost5
        return H

    def get_definition(self):
        hosts = self.get_hosts()
        class Hosts:
            role1 = { hosts.h1, hosts.h2}
            role2 = { hosts.h3, hosts.h4, hosts.h5 }
            role3 = { hosts.h1 }

        return HostsContainer.from_definition(Hosts, pty=DummyPty())

    def test_from_invalid_definition(self):
        class Hosts:
            invalid = 4
            class invalid2(object):
                pass

        self.assertRaises(TypeError, HostsContainer.from_definition, Hosts)

    def test_host_container(self):
        hosts = self.get_hosts()
        hosts_container = self.get_definition()

        # (fuzzy) __repr__
        self.assertIn('role1', repr(hosts_container))
        self.assertIn('role2', repr(hosts_container))
        self.assertIn('role3', repr(hosts_container))

        # __eq__ of get_hosts_as_dict
        # (__eq__ of HostsContainer itself is not supported anymore.)
        self.assertEqual(hosts_container.get_hosts_as_dict(),
                    self.get_definition().get_hosts_as_dict())

        # __len__ (One host appeared in two roles, both will be counted, so 6)
        self.assertEqual(len(hosts_container), 6)

        # __nonzero__
        self.assertEqual(bool(hosts_container), True)

        # roles
        self.assertEqual(hosts_container.roles, ['role1', 'role2', 'role3'])

     #   # __contains__
     #   self.assertIn(LocalHost3, hosts_container)

        # Filter
        self.assertEqual(len(hosts_container.filter('role1')), 2)
        self.assertEqual(len(hosts_container.filter('role2')), 3)
        self.assertEqual(len(hosts_container.filter('role3')), 1)

        # Non string filter should raise exception.
        self.assertRaises(TypeError, HostsContainer.filter, 123)

        class MyHosts1:
            role1 = { hosts.h1, hosts.h2 }
        class MyHosts2:
            role2 = { hosts.h3, hosts.h4, hosts.h5 }

        self.assertIsInstance(hosts_container.filter('role1'), HostsContainer)
        self.assertIsInstance(hosts_container.filter('role2'), HostsContainer)
        self.assertEqual(hosts_container.filter('role1').get_hosts(), set(MyHosts1.role1))
        self.assertEqual(hosts_container.filter('role2').get_hosts(), set(MyHosts2.role2))

        self.assertEqual(hosts_container.filter('role1').get_hosts_as_dict(),
                HostsContainer.from_definition(MyHosts1).get_hosts_as_dict())
        self.assertEqual(hosts_container.filter('role2').get_hosts_as_dict(),
                HostsContainer.from_definition(MyHosts2).get_hosts_as_dict())
        self.assertNotEqual(hosts_container.filter('role1').get_hosts_as_dict(),
                HostsContainer.from_definition(MyHosts2).get_hosts_as_dict())
        self.assertNotEqual(hosts_container.filter('role2').get_hosts_as_dict(),
                HostsContainer.from_definition(MyHosts1).get_hosts_as_dict())

        # Filter on two roles.

        class MyHosts1_and_2:
            role1 = { hosts.h1, hosts.h2 }
            role2 = { hosts.h3, hosts.h4, hosts.h5 }

        self.assertEqual(hosts_container.filter('role1', 'role2').get_hosts_as_dict(),
                    HostsContainer.from_definition(MyHosts1_and_2).get_hosts_as_dict())

        # __iter__ (will yield 6 items: when several roles contain the same
        # host, it are different instances.)
        count = 0
        for i in hosts_container:
            self.assertIsInstance(i, HostContainer)
            count += 1
        self.assertEqual(count, 6)

    def test_hostcontainer_run(self):
        hosts_container = self.get_definition()

        # Simple run
        result = hosts_container.run('echo test', interactive=False)
        self.assertEqual(len(result), 6)
        self.assertEqual(len(set(result)), 1) # All results should be equal
        self.assertEqual(result[0].strip(), 'test')

        # Env
        with hosts_container.env('CUSTOM_VAR', 'my-value'):
            result = hosts_container.run('echo $CUSTOM_VAR', interactive=False)
            self.assertEqual(result[0].strip(), 'my-value')

        # Env/filter combination
        with hosts_container.filter('role2').env('CUSTOM_VAR', 'my-value'):
            result = hosts_container.run('echo var=$CUSTOM_VAR', interactive=False)
            self.assertEqual(all('var=' in i for i in result), True)
            self.assertEqual(len(filter((lambda i: 'my-value' in i), result)), 3)

    def test_hostcontainer_commands(self):
        # Exists (the current directory should exist)
        hosts_container = self.get_definition()
        self.assertEqual(hosts_container.exists('.', use_sudo=False), [True, True, True, True, True, True])
        self.assertEqual(hosts_container[0].exists('.', use_sudo=False), True)

        # Has command
        self.assertEqual(hosts_container.has_command('ls'), [True, True, True, True, True, True])
        self.assertEqual(hosts_container[0].has_command('ls'), True)

        # (unknown command
        unknown_command = 'this_is_an_unknown_command'
        self.assertEqual(hosts_container.has_command(unknown_command),
                        [False, False, False, False, False, False])
        self.assertEqual(hosts_container[0].has_command(unknown_command), False)

    def test_hostcontainer_cd(self):
        hosts_container = self.get_definition()

        with hosts_container.cd('/'):
            result = hosts_container.run('pwd', interactive=False)
            self.assertEqual(len(result), 6)
            self.assertEqual(result[0].strip(), '/')
            self.assertEqual(hosts_container[0].getcwd(), '/')
            self.assertEqual(hosts_container.getcwd(), ['/'] * 6)

    def test_hostcontainer_cd2(self):
        # Test exists in cd.
        # (Exists should be aware of the cd-context.)
        hosts_container = self.get_definition()

        with hosts_container.cd('/'):
            self.assertEqual(hosts_container.exists('.', use_sudo=False), [True, True, True, True, True, True])
        with hosts_container.cd('/some-unknown-directory'):
            self.assertEqual(hosts_container.exists('.', use_sudo=False), [False, False, False, False, False, False])
        with hosts_container.cd('/'):
            self.assertEqual(hosts_container[0].exists('.', use_sudo=False), True)
        with hosts_container.cd('/some-unknown-directory'):
            self.assertEqual(hosts_container[0].exists('.', use_sudo=False), False)

    def test_hostcontainer_prefix(self):
        hosts_container = self.get_definition()

        with hosts_container.prefix('echo hello'):
            result = hosts_container.run('echo world', interactive=False)
            self.assertIn('hello', result[0])
            self.assertIn('world', result[0])

    def test_expand_path(self):
        hosts_container = self.get_definition()

        self.assertIsInstance(hosts_container.expand_path('.'), list)
        self.assertIsInstance(hosts_container.filter('role3')[0].expand_path('.'), basestring)

    def test_file_open(self):
        hosts_container = self.get_definition()

        # Open function should not exist in HostsContainer, only in HostContainer
        self.assertRaises(AttributeError, lambda: hosts_container.getattr('open'))

        # Call open function.
        _, name = tempfile.mkstemp()
        container = hosts_container.filter('role3')[0]
        with container.open(name, 'w') as f:
            f.write('my-content')

        # Verify content
        with open(name, 'r') as f:
            self.assertEqual(f.read(), 'my-content')

        os.remove(name)

    def test_put_and_get_file(self):
        hosts_container = self.get_definition()
        host_container = hosts_container.filter('role3')[0]

        # putfile/getfile functions should not exist in HostsContainer, only in HostContainer
        self.assertRaises(AttributeError, lambda: hosts_container.getattr('put_file'))
        self.assertRaises(AttributeError, lambda: hosts_container.getattr('get_file'))

        # Create temp file
        fd, name1 = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write('my-data')

        # Put operations
        _, name2 = tempfile.mkstemp()
        host_container.put_file(name1, name2)

        with open(name1) as f:
            with open(name2) as f2:
                self.assertEqual(f.read(), f2.read())

        # Get operation
        _, name3 = tempfile.mkstemp()
        host_container.get_file(name1, name3)

        with open(name1) as f:
            with open(name3) as f2:
                self.assertEqual(f.read(), f2.read())

        # clean up
        os.remove(name1)
        os.remove(name2)
        os.remove(name3)


class SSHHostsContainerTest(HostsContainerTest):
    """ Run the same tests, but using an SSH connection. """
    def get_hosts(self):
        """ Use local hosts. """
        class H:
            h1 =  LocalSSHHost1
            h2 =  LocalSSHHost2
            h3 =  LocalSSHHost3
            h4 =  LocalSSHHost4
            h5 =  LocalSSHHost5
        return H


########NEW FILE########
__FILENAME__ = host_test
from deployer.pseudo_terminal import DummyPty
from deployer.utils import IfConfig
from deployer.host.base import Stat

from our_hosts import LocalHost1, LocalSSHHost1

import os
import unittest
import tempfile
from os.path import expanduser


class HostTest(unittest.TestCase):
    def get_host(self, *a, **kw):
        return LocalHost1(*a, **kw)

    def test_simple_echo_command(self):
        host = self.get_host()
        self.assertEqual(host.run('echo test', interactive=False).strip(), 'test')

    def test_host_context(self):
        host = self.get_host()
        context = host.host_context

        # Test __repr__
        self.assertIn('HostContext(', repr(context))

        # Test env.
        with context.env('CUSTOM_VAR', 'my-value'):
            self.assertEqual(host.run('echo $CUSTOM_VAR', interactive=False).strip(), 'my-value')
        self.assertEqual(host.run('echo $CUSTOM_VAR', interactive=False).strip(), '')

        # Test prefix
        with context.prefix('echo prefix'):
            result = host.run('echo command', interactive=False)
            self.assertIn('prefix', result)
            self.assertIn('command', result)

        # Test 'cd /'
        with context.cd('/'):
            self.assertEqual(host.run('pwd', interactive=False).strip(), '/')

        # Test cd with path expansion
        with context.cd('~', expand=True):
            self.assertEqual(host.run('pwd', interactive=False).strip(), expanduser('~'))

        # Test env nesting.
        with context.env('VAR1', 'var1'):
            with context.env('VAR2', 'var2'):
                self.assertEqual(host.run('echo $VAR1-$VAR2', interactive=False).strip(), 'var1-var2')

        # Test escaping.
        with context.env('VAR1', 'var1'):
            with context.env('VAR2', '$VAR1', escape=False):
                self.assertEqual(host.run('echo $VAR2', interactive=False).strip(), 'var1')

            with context.env('VAR2', '$VAR1'): # escape=True by default
                self.assertEqual(host.run('echo $VAR2', interactive=False).strip(), '$VAR1')

    def test_repr(self):
        host = self.get_host()
        self.assertIn('Host(', repr(host))

    def test_interactive(self):
        # XXX: Not entirely sure whether this test is reliable.
        #      -> the select-loop will stop as soon as no input is available on any end.
        host = self.get_host()

        result = host.run('echo test', interactive=True).strip()
        self.assertEqual(result, 'test')

    def test_input(self):
        return
        pty = DummyPty('my-input\n')
        host = self.get_host(pty=pty)

        result = host.run('read varname; echo $varname')
        self.assertEqual(result, 'my-input\r\nmy-input\r\n')

    def test_opening_files(self):
        test_filename = '/tmp/python-deploy-framework-unittest-testfile-1'
        content = 'my-test-content'

        # Writing of file
        host = self.get_host()
        with host.open(test_filename, mode='w') as f:
            f.write(content)

        with open(test_filename, 'r') as f:
            self.assertEqual(f.read(), content)

        # Reading of file.
        with host.open(test_filename, mode='r') as f:
            self.assertEqual(f.read(), content)

        os.remove(test_filename)

    def test_put_file(self):
        host = self.get_host()

        # Create temp file
        fd, name1 = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write('my-data')

        # Put operations
        _, name2 = tempfile.mkstemp()
        host.put_file(name1, name2)

        with open(name1) as f:
            with open(name2) as f2:
                self.assertEqual(f.read(), f2.read())

        # Get operation
        _, name3 = tempfile.mkstemp()
        host.get_file(name1, name3)

        with open(name1) as f:
            with open(name3) as f2:
                self.assertEqual(f.read(), f2.read())

        # clean up
        os.remove(name1)
        os.remove(name2)
        os.remove(name3)

    def test_stat(self):
        """ Test the stat method. """
        host = self.get_host()

        # Create temp file
        fd, name = tempfile.mkstemp()

        # Call stat on temp file.
        s = host.stat(name)
        self.assertIsInstance(s, Stat)
        self.assertEqual(s.st_size, 0)
        self.assertEqual(s.is_file, True)
        self.assertEqual(s.is_dir, False)
        self.assertIsInstance(s.st_uid, int)
        self.assertIsInstance(s.st_gid, int)
        os.remove(name)

        # Call stat on directory
        s = host.stat('/tmp')
        self.assertEqual(s.is_file, False)
        self.assertEqual(s.is_dir, True)

    def test_ifconfig(self):
        # ifconfig should return an IfConfig instance.
        host = self.get_host()
        self.assertIsInstance(host.ifconfig(), IfConfig)

    def test_listdir(self):
        host = self.get_host()
        with host.host_context.cd('/'):
            self.assertIsInstance(host.listdir(), list)

    def test_listdir_stat(self):
        host = self.get_host()

        result = host.listdir_stat('/tmp')
        self.assertIsInstance(result, list)
        for r in result:
            self.assertIsInstance(r, Stat)

    def test_term_var(self):
        pty = DummyPty()
        host = self.get_host(pty=pty)

        # Changing the TERM variable of the PTY object.
        # (set_term_var is called by a client.)
        pty.set_term_var('xterm')
        self.assertEqual(host.run('echo $TERM', interactive=False).strip(), 'xterm')

        pty.set_term_var('another-term')
        self.assertEqual(host.run('echo $TERM', interactive=False).strip(), 'another-term')

        # This with statement should override the variable.
        with host.host_context.env('TERM', 'env-variable'):
            self.assertEqual(host.run('echo $TERM', interactive=False).strip(), 'env-variable')

class SSHHostTest(HostTest):
    def get_host(self, *a, **kw):
        return LocalSSHHost1(*a, **kw)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = inspector_test
import unittest

from deployer.query import Q, QueryResult
from deployer.node import Node, SimpleNode, Env, Action
from deployer.groups import Production, Staging, production, staging
from deployer.node import map_roles, suppress_action_result, EnvAction
from deployer.inspection import Inspector, PathType
from deployer.inspection.inspector import NodeIterator
from deployer.inspection import filters

from our_hosts import LocalHost1, LocalHost2, LocalHost3, LocalHost4, LocalHost5


class InspectorTest(unittest.TestCase):
    def setUp(self):
        class Root(Node):
            @production
            class A(Node):
                pass
            @staging
            class B(Node):
                class C(Node):
                    def __call__(self):
                        # __call__ is the default action
                        pass
            def a(self): pass
            def b(self): pass
            def c(self): pass
            c.__name__ = 'another-name' # Even if we override this name, Action.name should remain 'c'

            @property
            def p1(self):
                return 'p1'

            @property
            def p2(self):
                return 'p1'

            query1 = Q.something
            query2 = Q.something_else

        self.s = Root()
        self.insp = Inspector(self.s)

    def test_get_childnodes(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_childnodes()), '[<Node Root.A>, <Node Root.B>]')
        self.assertEqual(repr(insp.get_actions()), '[<Action Root.a>, <Action Root.b>, <Action Root.c>]')
        for a in insp.get_actions():
            self.assertIn(a.name, ['a', 'b', 'c'])

    def test_get_childnode(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_childnode('A')), '<Node Root.A>')
        self.assertIsInstance(insp.get_childnode('A'), Node)
        self.assertRaises(AttributeError, insp.get_childnode, 'unknown_childnode')

    def test_has_childnode(self):
        insp = self.insp
        self.assertEqual(insp.has_childnode('A'), True)
        self.assertEqual(insp.has_childnode('C'), False)

    def test_get_actions(self):
        insp = self.insp
        self.assertEqual(len(insp.get_actions()), 3)
        self.assertEqual(repr(insp.get_actions()), '[<Action Root.a>, <Action Root.b>, <Action Root.c>]')

    def test_get_action(self):
        insp = self.insp
        self.assertIsInstance(insp.get_action('a'), Action)
        self.assertEqual(repr(insp.get_action('a')), '<Action Root.a>')
        self.assertRaises(AttributeError, insp.get_action, 'unknown_action')

    def test_has_action(self):
        insp = self.insp
        self.assertEqual(insp.has_action('a'), True)
        self.assertEqual(insp.has_action('d'), False)

    def test_get_properties(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_properties()), '[<Action Root.p1>, <Action Root.p2>]')

    def test_get_property(self):
        insp = self.insp
        self.assertIsInstance(insp.get_property('p1'), Action)
        self.assertEqual(repr(insp.get_property('p1')), '<Action Root.p1>')
        self.assertRaises(AttributeError, insp.get_property, 'unknown_property')

    def has_property(self):
        insp = self.insp
        self.assertEqual(insp.has_property('p1'), True)
        self.assertEqual(insp.has_property('unknown_property'), False)

    def test_get_queries(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_queries()), '[<Action Root.query1>, <Action Root.query2>]')

    def test_get_query(self):
        insp = self.insp
        self.assertIsInstance(insp.get_query('query1'), Action)
        self.assertEqual(repr(insp.get_query('query1')), '<Action Root.query1>')
        self.assertRaises(AttributeError, insp.get_query, 'unknown_query')

    def test_has_query(self):
        insp = self.insp
        self.assertEqual(insp.has_query('query1'), True)
        self.assertEqual(insp.has_query('unknown_query'), False)

    def test_get_path(self):
        s = self.s
        self.assertEqual(repr(Inspector(s.A).get_path()), "('Root', 'A')")
        self.assertEqual(repr(Inspector(s.B.C).get_path()), "('Root', 'B', 'C')")
        self.assertEqual(repr(Inspector(s.B.C).get_path(path_type=PathType.NODE_AND_NAME)),
                        "((<Node Root>, 'Root'), (<Node Root.B>, 'B'), (<Node Root.B.C>, 'C'))")
        self.assertEqual(repr(Inspector(s.B.C).get_path(path_type=PathType.NODE_ONLY)),
                        "(<Node Root>, <Node Root.B>, <Node Root.B.C>)")

    def test_get_name(self):
        s = self.s
        self.assertEqual(Inspector(s.A).get_name(), 'A')
        self.assertEqual(Inspector(s.B.C).get_name(), 'C')

        self.assertEqual(Inspector(s.A).get_full_name(), 'Root.A')
        self.assertEqual(Inspector(s.B.C).get_full_name(), 'Root.B.C')

    def test_is_callable(self):
        s = self.s
        self.assertEqual(Inspector(s.A).is_callable(), False)
        self.assertEqual(Inspector(s.B.C).is_callable(), True)

    def test_repr(self):
        s = self.s
        self.assertEqual(repr(Inspector(s)), 'Inspector(node=Root)')
        self.assertEqual(repr(Inspector(s.B.C)), 'Inspector(node=Root.B.C)')

    def test_get_group(self):
        s = self.s
        self.assertEqual(Inspector(s.A).get_group(), Production)
        self.assertEqual(Inspector(s.B).get_group(), Staging)
        self.assertEqual(Inspector(s.B.C).get_group(), Staging)

    def test_walk(self):
        insp = self.insp
        self.assertEqual(len(list(insp.walk())), 4)
        self.assertEqual({ Inspector(i).get_name() for i in insp.walk() }, { 'Root', 'A', 'B', 'C' })
        for i in insp.walk():
            self.assertIsInstance(i, Node)

    def test_walk_from_childnode(self):
        s = self.s
        insp = Inspector(s.B)
        self.assertEqual(len(list(insp.walk())), 2)
        self.assertEqual({ Inspector(i).get_name() for i in insp.walk() }, { 'B', 'C' })


class InspectorOnEnvTest(unittest.TestCase):
    def setUp(self):
        class Root(Node):
            class A(Node):
                pass
            class B(Node):
                def action(self):
                    return 'action-b'
            def action(self):
                return 'action-root'
            def action2(self):
                return 'action-root2'

            @property
            def p1(self):
                return 'p1'

            @property
            def p2(self):
                return 'p2'

        self.env = Env(Root())
        self.insp = Inspector(self.env)

    def test_get_childnodes(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_childnodes()), '[Env(Root.A), Env(Root.B)]')
        self.assertEqual(insp.get_childnode('B').action(), 'action-b')

    def test_get_childnode(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_childnode('A')), 'Env(Root.A)')
        self.assertIsInstance(insp.get_childnode('A'), Env)
        self.assertRaises(AttributeError, insp.get_childnode, 'unknown_childnode')

    def test_get_actions(self):
        insp = self.insp
        self.assertIsInstance(insp.get_actions()[0], EnvAction)

    def test_get_action(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_action('action')), '<Env.Action Root.action>')
        self.assertIsInstance(insp.get_action('action'), EnvAction)
        self.assertEqual(insp.get_action('action')(), 'action-root')
        self.assertEqual(insp.get_action('action').name, 'action')

    def test_get_properties(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_properties()), '[<Env.Action Root.p1>, <Env.Action Root.p2>]')
        self.assertIsInstance(insp.get_properties()[0], EnvAction)

    def test_get_property(self):
        insp = self.insp
        self.assertEqual(repr(insp.get_property('p1')), '<Env.Action Root.p1>')
        self.assertIsInstance(insp.get_property('p1'), EnvAction)

    def test_walk(self):
        insp = self.insp
        self.assertEqual(len(list(insp.walk())), 3)
        self.assertEqual({ Inspector(i).get_name() for i in insp.walk() }, { 'Root', 'A', 'B' })
        for i in insp.walk():
            self.assertIsInstance(i, Env)

class InspectorChildnodesOrder(unittest.TestCase):
    def test_get_childnodes_order(self):
        """
        The inspector should return the childnodes in the order, as they were
        nested inside the node definition.
        """
        # Automatic
        class Root(Node):
            class A(Node): pass
            class B(Node): pass

        self.assertEqual(repr(Inspector(Root()).get_childnodes()), '[<Node Root.A>, <Node Root.B>]')
        self.assertEqual(repr(Inspector(Env(Root())).get_childnodes()), '[Env(Root.A), Env(Root.B)]')

        # Manually set creation order
        class Root(Node):
            class A(Node): pass
            class B(Node): pass
            A._node_creation_counter = 44
            B._node_creation_counter = 45

        self.assertEqual(repr(Inspector(Root()).get_childnodes()), '[<Node Root.A>, <Node Root.B>]')
        self.assertEqual(repr(Inspector(Env(Root())).get_childnodes()), '[Env(Root.A), Env(Root.B)]')

        # Manually revert the creation order
        class Root(Node):
            class A(Node): pass
            class B(Node): pass
            A._node_creation_counter = 45
            B._node_creation_counter = 44

        self.assertEqual(repr(Inspector(Root()).get_childnodes()), '[<Node Root.B>, <Node Root.A>]')
        self.assertEqual(repr(Inspector(Env(Root())).get_childnodes()), '[Env(Root.B), Env(Root.A)]')

class InspectorTestIterIsolations(unittest.TestCase):
    def setUp(self):
        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2, LocalHost3 }
                role2 = { LocalHost2, LocalHost4, LocalHost5 }

            @map_roles('role1', extra='role2')
            class B(SimpleNode.Array):
                class C(Node):
                    @map_roles('extra')
                    class D(SimpleNode.Array):
                        pass
        self.A = A

    def test_inspection_env_node(self):
        A = self.A
        def test(insp, type):
            self.assertEqual(len(list(insp.iter_isolations())), 9) # 3x3

            # Inspection on env should yield Env objects, Node should yield
            # node objects.
            for i, node in insp.iter_isolations():
                self.assertIsInstance(node, type)

            # Test get_isolation
            node = insp.get_isolation((0, 0))
            self.assertIsInstance(node, type)
            self.assertEqual(repr(node),
                '<Node A.B[0].C.D[0]>' if type == Node else 'Env(A.B[0].C.D[0])')

            node = insp.get_isolation((2, 2))
            self.assertIsInstance(node, type)
            self.assertEqual(repr(node),
                '<Node A.B[2].C.D[2]>' if type == Node else 'Env(A.B[2].C.D[2])')

        test(Inspector(A().B.C.D), Node)
        test(Inspector(Env(A()).B.C.D), Env)

class InspectorIteratorTest(unittest.TestCase):
    def setUp(self):
        class Base(Node):
            pass

        self.Base = Base

        # Ensure that we have a correct __repr__ for this class
        self.Base.__module__ = 'inspector_test'
        assert repr(Base) == "<class 'inspector_test.Base'>"

        class A(Node):
            def my_action(self): return 'a'

            @production
            class B(Base):
                def my_action(self): return 'b'
                def my_other_action(self): return 'b2'

                class C(SimpleNode.Array):
                    class Hosts:
                        host = { LocalHost1, LocalHost2, LocalHost3, LocalHost4 }

                    def my_action(self): return 'c'

                    @staging
                    class E(Base):
                        def my_action(self): return 'e'

            @production
            class D(Base):
                def my_action(self): return 'd'
                def my_other_action(self): return 'd2'

            @staging
            class _P(Base):
                # A private node
                def my_action(self): return '_p'

        self.env = Env(A())
        self.insp = Inspector(self.env)

    def test_walk(self):
        insp = self.insp
        Base = self.Base
        self.assertEqual(len(insp.walk()), 6)
        self.assertIsInstance(insp.walk(), NodeIterator)
        self.assertEqual(len(insp.walk().filter(filters.IsInstance(Base))), 4)

    def test_walk_public_only(self):
        insp = self.insp
        self.assertEqual(len(insp.walk(filters.PublicOnly)), 5)
        self.assertEqual(len(insp.walk().filter(filters.PublicOnly)), 5)

    def test_walk_private_only(self):
        insp = self.insp
        self.assertEqual(len(insp.walk(filters.PrivateOnly)), 1)

    def test_or_operation(self):
        insp = self.insp
        self.assertEqual(len(insp.walk(filters.PrivateOnly | filters.HasAction('my_other_action'))), 3)
        self.assertEqual({ repr(n) for n in insp.walk(filters.PrivateOnly | filters.HasAction('my_other_action')) },
                { 'Env(A.B)', 'Env(A.D)', 'Env(A._P)' })

        # Check repr
        self.assertEqual(repr(filters.PrivateOnly | filters.HasAction('my_other_action')),
                "PrivateOnly | HasAction('my_other_action')")

    def test_and_operation(self):
        insp = self.insp
        self.assertEqual(len(insp.walk(filters.PrivateOnly & filters.IsInstance(self.Base))), 1)

        # Check repr
        self.assertEqual(repr(filters.PrivateOnly & filters.IsInstance(self.Base)),
                "PrivateOnly & IsInstance(<class 'inspector_test.Base'>)")

    def test_not_operation(self):
        insp = self.insp
        self.assertEqual(len(insp.walk(~ filters.PrivateOnly)), 5)
        self.assertEqual(repr(~ filters.PrivateOnly), '~ PrivateOnly')

    def test_call_action(self):
        insp = self.insp
        Base = self.Base
        result = list(insp.walk().filter(filters.IsInstance(Base)).call_action('my_action'))
        self.assertEqual(len(result), 7)
        self.assertEqual(set(result), { 'b', 'd', '_p', 'e', 'e', 'e', 'e' })

    def test_filter_on_action(self):
        insp = self.insp
        result = insp.walk().filter(filters.HasAction('my_action'))
        self.assertEqual(len(result), 6)
        result = insp.walk().filter(filters.HasAction('my_other_action'))
        self.assertEqual(len(result), 2)
        result = insp.walk().filter(filters.HasAction('my_other_action')).call_action('my_other_action')
        self.assertEqual(set(result), { 'b2', 'd2' })

    def test_filter_on_group(self):
        insp = self.insp
        # Following are production nodes B, B.C, B.D
        self.assertEqual(len(list(insp.walk().filter(filters.InGroup(Production)))), 3)

        for node in insp.walk().filter(filters.InGroup(Production)):
            self.assertEqual(Inspector(node).get_group(), Production)

    def test_prefer_isolation(self):
        insp = self.insp
        env = self.env
        result = insp.walk().prefer_isolation(LocalHost2)
        self.assertEqual( set(repr(e) for e in result),
                    { repr(e) for e in { env, env.B, env.D, env._P, env.B.C[LocalHost2], env.B.C[LocalHost2].E }})

        # Maybe we should also implement a better Node.__eq__ and Env.__eq__, then we can do this:
        # >> self.assertEqual(set(result), { env, env.B, env.D, env.B.C[LocalHost2], env.B.C[LocalHost2].E })

    def test_multiple_iterator(self):
        insp = self.insp
        node_iterator = insp.walk()
        self.assertEqual(len(list(node_iterator)), 6)
        self.assertEqual(len(list(node_iterator)), 6)
        self.assertEqual(len(node_iterator), 6)
        self.assertEqual(len(node_iterator), 6)

    def test_unknown_action(self):
        insp = self.insp
        self.assertRaises(AttributeError, lambda: list(insp.walk().call_action('my_action2')))


class SuppressResultTest(unittest.TestCase):
    def setUp(self):
        class Root(Node):
            def a(self):
                pass

            @suppress_action_result
            def b(self):
                pass

        self.env = Env(Root())
        self.env_insp = Inspector(self.env)
        self.node_insp = Inspector(Root())

    def test_suppress_decorator(self):
        # On an node object
        self.assertEqual(self.node_insp.suppress_result_for_action('a'), False)
        self.assertEqual(self.node_insp.suppress_result_for_action('b'), True)

        # On an env object
        self.assertEqual(self.env_insp.suppress_result_for_action('a'), False)
        self.assertEqual(self.env_insp.suppress_result_for_action('b'), True)


class QueryInspectionTest(unittest.TestCase):
    def setUp(self):
        class Root(Node):
            attr = 'value'
            query = Q.attr + Q.attr
            def my_action(self): pass
        self.env = Env(Root())
        self.env_insp = Inspector(self.env)
        self.node_insp = Inspector(Root())

    def test_has_query(self):
        self.assertEqual(self.env_insp.has_query('query'), True)
        self.assertEqual(self.env_insp.has_query('not_a_query'), False)

        self.assertEqual(self.node_insp.has_query('query'), True)
        self.assertEqual(self.node_insp.has_query('not_a_query'), False)

    def test_get_query(self):
        self.assertIsInstance(self.node_insp.get_query('query'), Action)
        self.assertRaises(AttributeError, self.node_insp.get_query, 'not_a_query')

    def test_trace_query(self):
        # trace_query is private because it's for internal use. (In the
        # shell.)
        result = self.env_insp.trace_query('query')
        self.assertIsInstance(result, QueryResult)
        self.assertEqual(result.result, 'valuevalue')


########NEW FILE########
__FILENAME__ = node_test
import unittest

from deployer.console import Console
from deployer.exceptions import ActionException, ExecCommandFailed
from deployer.inspection import Inspector
from deployer.node import Node, SimpleNode, Env, ParallelActionResult
from deployer.node import map_roles, dont_isolate_yet, required_property, alias, IsolationIdentifierType
from deployer.pseudo_terminal import Pty
from deployer.query import Q

from our_hosts import LocalHost, LocalHost1, LocalHost2, LocalHost3, LocalHost4, LocalHost5


class NodeTest(unittest.TestCase):
    def test_assignments_to_node(self):
        """
        When a Node is assigned to a Node class, retrieval
        should return the same object.
        """
        class MyNode(Node):
            pass
        class S2(Node):
            pass

        MyNode.s = S2
        self.assertEqual(MyNode.s, S2) # TODO: the same for methods is not true!!!

    def test_node_initialisation(self):
        class S(Node):
            class Hosts:
                role1 = LocalHost
                role2 = LocalHost

        s = S()
        self.assertEqual(isinstance(s, Node), True)
        self.assertEqual(s.hosts.roles, ['role1', 'role2'])

    def test_nesting(self):
        class S(Node):
            class Hosts:
                role1 = LocalHost
                role2 = LocalHost

            class T(Node):
                pass

            class U(Node):
                pass

        s = S()
        self.assertEqual(isinstance(s, Node), True)
        self.assertEqual(isinstance(s.T, Node), True)
        self.assertEqual(isinstance(s.U, Node), True)

        self.assertEqual(s.hosts.roles, ['role1', 'role2'])
        self.assertEqual(s.T.hosts.roles, ['role1', 'role2'])
        self.assertEqual(s.U.hosts.roles, ['role1', 'role2'])

        self.assertEqual(s.hosts.get_hosts_as_dict(), s.T.hosts.get_hosts_as_dict())
        self.assertEqual(s.hosts.get_hosts_as_dict(), s.U.hosts.get_hosts_as_dict())

    def test_mapping(self):
        class S(Node):
            class Hosts:
                role1 = LocalHost
                role2 = LocalHost2

            @map_roles(role3='role1', role4='role2', role5='role3', role6=('role1', 'role2'))
            class T(Node):
                pass

            @map_roles(role7=('role1', 'role3'), role8='role1')
            class U(Node):
                class V(Node):
                    pass

                @map_roles(role9='role1', role10='role7')
                class W(Node):
                    pass

                class X(Node):
                    class Hosts:
                        role1 = LocalHost3
                        role2 = { LocalHost4, LocalHost5 }

                @map_roles(role11='role7')
                class Y(Node):
                    # Because of map_roles, the following will be overriden.
                    class Hosts:
                        role1 = LocalHost1

        s = S()
        self.assertIsInstance(s, Node)
        self.assertIsInstance(s.T, Node)
        self.assertIsInstance(s.U, Node)
        self.assertIsInstance(s.U.V, Node)
        self.assertIsInstance(s.U.W, Node)
        self.assertIsInstance(s.U.X, Node)
        self.assertIsInstance(s.U.Y, Node)

        self.assertEqual(s.hosts.roles, ['role1', 'role2'])
        self.assertEqual(s.T.hosts.roles, ['role3', 'role4', 'role5', 'role6'])
        self.assertEqual(s.U.hosts.roles, ['role7', 'role8'])
        self.assertEqual(s.U.V.hosts.roles, ['role7', 'role8'])
        self.assertEqual(s.U.W.hosts.roles, ['role10', 'role9']) # Lexical ordered
        self.assertEqual(s.U.X.hosts.roles, ['role1', 'role2'])
        self.assertEqual(s.U.X.hosts.roles, ['role1', 'role2'])
        self.assertEqual(s.U.Y.hosts.roles, ['role11'])

        self.assertEqual(s.T.hosts.get_hosts_as_dict(),
                { 'role3': {LocalHost}, 'role4': {LocalHost2}, 'role5': set(), 'role6': { LocalHost, LocalHost2 } })
        self.assertEqual(s.U.hosts.get_hosts_as_dict(),
                { 'role7': {LocalHost}, 'role8': {LocalHost} })
        self.assertEqual(s.U.V.hosts.get_hosts_as_dict(),
                { 'role7': {LocalHost}, 'role8': {LocalHost} })
        self.assertEqual(s.U.W.hosts.get_hosts_as_dict(),
                { 'role9': set(), 'role10': {LocalHost} })
        self.assertEqual(s.U.X.hosts.get_hosts_as_dict(),
                { 'role1': {LocalHost3}, 'role2': {LocalHost4, LocalHost5} })
        self.assertEqual(s.U.Y.hosts.get_hosts_as_dict(),
                { 'role11': {LocalHost} })

    def test_invalid_mapping(self):
        class NotANode(object): pass
        self.assertRaises(TypeError, map_roles('role'), NotANode())

    def test_env_object(self):
        class S(Node):
            class Hosts:
                role1 = LocalHost
                role2 = LocalHost2

            def my_action(self):
                return 'result'

            def return_name_of_self(self):
                return self.__class__.__name__

            def echo_on_all(self):
                return self.hosts.run('/bin/echo echo', interactive=False)

            def echo_on_role1(self):
                return self.hosts.filter('role1').run('/bin/echo echo', interactive=False)

            def echo_on_role2(self):
                return self.hosts.filter('role2')[0].run('/bin/echo echo', interactive=False)

        s = S()
        env = Env(s)

        self.assertEqual(env.my_action(), 'result')
        self.assertEqual(env.return_name_of_self(), 'Env')
        self.assertEqual(env.echo_on_all(), [ 'echo\r\n', 'echo\r\n' ])
        self.assertEqual(env.echo_on_role1(), [ 'echo\r\n' ])
        self.assertEqual(env.echo_on_role2(), 'echo\r\n')

        # Isinstance hooks
        self.assertIsInstance(s, S)
        self.assertIsInstance(env, S)

    def test_bin_false(self):
        class S(Node):
            class Hosts:
                role1 = LocalHost

            def return_false(self):
                return self.hosts.run('/bin/false', interactive=False)

        s = S()
        env = Env(s)

        # This should raise an ExecCommandFailed, wrapped in an ActionException
        self.assertRaises(ActionException, env.return_false)

        try:
            env.return_false()
        except ActionException as e:
            self.assertIsInstance(e.inner_exception, ExecCommandFailed)

    def test_action_with_params(self):
        class MyNode(Node):
            class Hosts:
                host = LocalHost

            def my_action(self, param1, *a, **kw):
                return (param1, a, kw)

        s = MyNode()
        env = Env(s)
        result = env.my_action('param1', 1, 2, k=3, v=4)
        self.assertEqual(result, ('param1', (1, 2), { 'k': 3, 'v': 4 }) )

    def test_nested_action(self):
        class MyNode(Node):
            class Node2(Node):
                class Node3(Node):
                    def my_action(self):
                        return 'result'

        env = Env(MyNode())
        result = env.Node2.Node3.my_action()
        self.assertEqual(result, 'result')

    def test_property(self):
        class MyNode(Node):
            class Hosts:
                host = LocalHost

            @property
            def p(self):
                return 'value'

            def my_action(self):
                return self.p

        s = MyNode()
        env = Env(s)
        self.assertEqual(env.my_action(), 'value')

    def test_wrapping_middle_node_in_env(self):
        class S(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }

            class T(Node):
                def action(self):
                    return len(self.hosts)

        s = S()
        env = Env(s.T)
        self.assertEqual(env.action(), 2)

    def test_attribute_overrides(self):
        # Test double underscore overrides.
        class N(Node):
            class O(Node):
                value = 'original_value'

        self.assertEqual(N.O.value, 'original_value')

        class N2(N):
            O__value = 'new_value'

            def O__func(self):
                return 'return_value'

        self.assertEqual(N2.O.value, 'new_value')

        env = Env(N2())
        self.assertEqual(env.O.value, 'new_value')
        self.assertEqual(env.O.func(), 'return_value')

    def test_multiple_level_overrides(self):
        class N(Node):
            class O(Node):
                class P(Node):
                    class Q(Node):
                        value = 'original_value'

        self.assertEqual(N.O.P.Q.value, 'original_value')

        class N2(N):
            O__P__Q__value = 'new_value'

            def O__P__func(self):
                return 'return_value'

        self.assertEqual(N2.O.P.Q.value, 'new_value')

        env = Env(N2())
        self.assertEqual(env.O.P.Q.value, 'new_value')
        self.assertEqual(env.O.P.func(), 'return_value')

    def test_unknown_attribute_override(self):
        class N(Node):
            class O(Node):
                pass
        # Using this attributes in a class inheriting from here should raise an exception3
        # TODO: correct exception.
        self.assertRaises(Exception, type, 'NewN', (N,), { 'unknown__member': True })
        self.assertRaises(Exception, type, 'NewN', (N,), { 'O__unknown__member': True })

    def test_simple_node(self):
        class N(SimpleNode):
            class Hosts:
                host = { LocalHost1, LocalHost2 }

            def func(self):
                return 'result'

        # SimpleNode executes for each host separately.
        env = Env(N())
        self.assertEqual(list(env.func()), ['result', 'result' ])

        # Test return value of SimpleNode
        result = env.func()
        self.assertIsInstance(result, ParallelActionResult)

            # (The key is the Env, containing the isolation)
        self.assertIsInstance(result.keys()[0], Env)
        self.assertIsInstance(result.keys()[1], Env)
        self.assertIn(result.keys()[0]._node.Hosts.host, { LocalHost1, LocalHost2 })
        self.assertIn(result.keys()[1]._node.Hosts.host, { LocalHost1, LocalHost2 })

        self.assertEqual(result.values()[0], 'result')
        self.assertEqual(result.values()[1], 'result')

    def test_simple_node_getitem(self):
        class N(SimpleNode):
            class Hosts:
                host = { LocalHost1, LocalHost2 }

            def func(self):
                return 'result'

        n = N()
        self.assertIsInstance(n[0], SimpleNode)
        self.assertIsInstance(n[1], SimpleNode)
        self.assertIsInstance(n[LocalHost1], SimpleNode)
        self.assertIsInstance(n[LocalHost2], SimpleNode)
        self.assertEqual(n[0]._node_is_isolated, True)
        self.assertEqual(n[1]._node_is_isolated, True)
        self.assertEqual(n[LocalHost1]._node_is_isolated, True)
        self.assertEqual(n[LocalHost2]._node_is_isolated, True)
        self.assertRaises(KeyError, lambda: n[2])
        self.assertRaises(KeyError, lambda: n[LocalHost3])

        # Calling the isolated item should not return an array
        env = Env(N())
        self.assertEqual(list(env.func()), ['result', 'result' ])
        self.assertIsInstance(env.func(), ParallelActionResult)
        self.assertEqual(env[0].func(), 'result')
        self.assertEqual(env[1].func(), 'result')
        self.assertRaises(KeyError, lambda: env[2])
        self.assertRaises(KeyError, lambda: env[LocalHost3])

    def test_getitem_on_normal_node(self):
        # __getitem__ should not be possible on a normal node.
        class N(Node):
            class Hosts:
                host = { LocalHost1, LocalHost2 }
        n = N()
        self.assertRaises(KeyError, lambda:n[0]) # TODO: regex match: KeyError: __getitem__ on isolated node is not allowed.

    def test_getitem_between_simplenodes(self):
        # We often go from one simplenode to another one by using
        # self.host as the index parameter.
        class Root(Node):
            class Hosts:
                role = { LocalHost1, LocalHost2 }

            @map_roles('role')
            class A(SimpleNode.Array):
                def action(self):
                    return self.parent.B[self.host].action()

            @map_roles('role')
            class B(SimpleNode.Array):
                def action(self):
                    return '%s in b' % self.host.slug

        env = Env(Root())
        self.assertEqual(set(env.A.action()), set(['localhost2 in b', 'localhost1 in b']))
        self.assertIn(env.A[0].action(), ['localhost1 in b', 'localhost2 in b'])

    def test_dont_isolate_yet(self):
        once = [0]
        for_each_host = [0]
        this = self

        class A(Node):
            class Hosts:
                my_role = { LocalHost1, LocalHost2 }

            @map_roles('my_role')
            class B(SimpleNode.Array):
                def for_each_host(self):
                    for_each_host[0] += 1
                    this.assertEqual(len(self.hosts), 1)

                @dont_isolate_yet
                def only_once(self):
                    once[0] += 1
                    self.for_each_host()
                    this.assertEqual(len(self.hosts), 2)
                    return 'result'

        env = Env(A())
        result = env.B.only_once()

        self.assertEqual(result, 'result')
        self.assertEqual(once, [1])
        self.assertEqual(for_each_host, [2])

    def test_nested_simple_nodes(self):
        class N(SimpleNode):
            class Hosts:
                host = { LocalHost1, LocalHost2 }

            class M(SimpleNode):
                def func(self):
                    return 'result'

        # `M` gets both hosts as well.
        env = Env(N())
        self.assertEqual(list(env.M.func()), ['result', 'result' ])

    def test_simple_nodes_in_normal_node(self):
        class N(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost }
                role2 = LocalHost3

            @map_roles('role1')
            class M(SimpleNode.Array):
                def func(self):
                    return 'func-m'

                class X(SimpleNode):
                    def func(self):
                        return 'func-x'

            def func(self):
                return 'func-n'

        # `M` should behave as an array.
        env = Env(N())
        self.assertEqual(env.func(), 'func-n')
        self.assertEqual(list(env.M.func()), ['func-m', 'func-m' ])
        self.assertIsInstance(env.M.func(), ParallelActionResult)
        self.assertEqual(env.M[0].func(), 'func-m')
        self.assertEqual(list(env.M.X.func()), ['func-x', 'func-x'])
        self.assertIsInstance(env.M.X.func(), ParallelActionResult)
        self.assertEqual(env.M[0].X.func(), 'func-x')
        self.assertEqual(env.M.X[0].func(), 'func-x')

    def test_calling_between_simple_and_normal_nodes(self):
        class N(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost }
                role2 = LocalHost3

            def do_tests(this):
                self.assertEqual(list(this.M.func()), ['func-m', 'func-m'])
                self.assertEqual(list(this.M.X.func()), ['func-x', 'func-x'])
                self.assertEqual(this.M[0].func(), 'func-m')
                self.assertEqual(this.M.X[0].func(), 'func-x')

            def func(this):
                return 'func-n'

            @map_roles(host='role1')
            class M(SimpleNode.Array):
                def func(this):
                    return 'func-m'

                class X(SimpleNode):
                    def func(this):
                        return 'func-x'

                    def do_tests(this):
                        self.assertIn(repr(this.parent), [
                                    'Env(N.M[0])',
                                    'Env(N.M[1])'])
                        self.assertEqual(repr(this.parent.parent), 'Env(N)')

                        self.assertEqual(this.func(), 'func-x')
                        self.assertEqual(this.parent.parent.func(), 'func-n')
                        self.assertEqual(list(this.parent.parent.M.func()), ['func-m', 'func-m'])
                        self.assertEqual(this.parent.parent.M[0].func(), 'func-m')

        env = Env(N())
        env.do_tests()
        env.M.X.do_tests()

    def test_node_names(self):
        class Another(Node):
            pass

        class N(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }
                role2 = LocalHost3

            class M(Node):
                class O(Node):
                    pass

            @map_roles(host='role1')
            class P(SimpleNode.Array):
                pass

            class another_node(Another):
                pass

            another_node2 = Another

        # For the class definitions, the names certainly shoudn't change.
        self.assertEqual(N.__name__, 'N')
        self.assertEqual(N.M.__name__, 'M')
        self.assertEqual(N.M.O.__name__, 'O')
        self.assertEqual(N.P.__name__, 'P')
        self.assertEqual(N.another_node.__name__, 'another_node')
        self.assertEqual(N.another_node2.__name__, 'Another')

        # For instances (and mappings), they should be named according to the
        # full path.
        n = N()
        self.assertEqual(repr(n), '<Node N>')
        self.assertEqual(repr(n.M), '<Node N.M>')
        self.assertEqual(repr(n.M.O), '<Node N.M.O>')
        self.assertEqual(repr(n.P), '<Node N.P>')

        self.assertEqual(repr(n.P[0]), '<Node N.P[0]>')
        self.assertEqual(repr(n.P[1]), '<Node N.P[1]>')

        self.assertEqual(repr(n.another_node), '<Node N.another_node>')
        self.assertEqual(repr(n.another_node2), '<Node N.another_node2>')

        # Test Env.__repr__
        env = Env(n)
        self.assertEqual(repr(env), 'Env(N)')
        self.assertEqual(repr(env.M.O), 'Env(N.M.O)')
        self.assertEqual(repr(env.P[0]), 'Env(N.P[0])')
        self.assertEqual(repr(env.P[1]), 'Env(N.P[1])')


    def test_auto_mapping_from_node_to_simplenode_array(self):
        # When no role_mapping is defined between Node and SimpleNode.Array,
        # we will map *all* roles to 'host'
        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }
                role2 = { LocalHost3 }
                role3 = { LocalHost4 }

            class B(SimpleNode.Array):
                pass

        env = Env(A())
        self.assertEqual(len(list(env.B)), 4)

        # When we have a Hosts class, and no explicit
        # mapping between A and B, this hosts will be used.
        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }
                role2 = { LocalHost3, LocalHost4 }

            class B(SimpleNode.Array):
                class Hosts:
                    host = LocalHost1

        env = Env(A())
        self.assertEqual(len(list(env.B)), 1)

        # In case of JustOne, it should work as well.
        class A(Node):
            class Hosts:
                role1 = LocalHost1

            class B(SimpleNode.JustOne):
                pass

        env = Env(A())
        self.assertEqual(len(list(env.B)), 1)

        # Exception: Invalid initialisation of SimpleNode.JustOne. 2 hosts given to <Node A.B>.
        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }

            class B(SimpleNode.JustOne):
                pass
        env = Env(A())
        self.assertRaises(Exception, lambda: env.B)

    def test_action_names(self):
        # Test Action.__repr__
        class N(Node):
            class M(Node):
                def my_action(self):
                    pass

        n = N()
        self.assertEqual(repr(n.M.my_action), '<Action N.M.my_action>')
        self.assertEqual(repr(N.M.my_action), '<Unbound Action my_action>')
        self.assertEqual(n.M.my_action.name, 'my_action')

        # Env.Action.__repr__
        env = Env(n)
        self.assertEqual(repr(env.M.my_action), '<Env.Action N.M.my_action>')
        self.assertEqual(env.M.my_action.name, 'my_action')

    def test_nesting_normal_in_simple(self):
        # Simplenode in Node without using .Array
        def run():
            class A(Node):
                class B(SimpleNode):
                    pass

        self.assertRaises(Exception, run) # TODO: correct exception

        # .Array inside .Array
        def run():
            class A(Node.Array):
                class B(Node.Array):
                    pass

        self.assertRaises(Exception, run) # TODO: correct exception

    def test_invalid_hosts_object(self):
        # Hosts should be a role mapping or Hosts class definition
        # Anything else should raise an exception.
        def run():
            class MyNode(Node):
                Hosts = 4
        self.assertRaises(Exception, run) # TODO: correct exception

    def test_assignments_in_node(self):
        # It's not allowed to change attributes from a Node Environment.
        class MyNode(Node):
            def action(self):
                self.variable = 'value'

        # AttributeError wrapped in ActionException
        env = Env(MyNode())
        self.assertRaises(ActionException, env.action)

        try:
            env.action()
        except ActionException as e:
            self.assertIsInstance(e.inner_exception, AttributeError)

    def test_custom_node_init(self):
        # It is not allowed to provide a custom __init__ method.
        def run():
            class MyNode(Node):
                def __init__(self, *a, **kw):
                    pass
        self.assertRaises(TypeError, run)

    def test_overriding_host_property(self):
        # It should not be possible to override the host property.
        def run():
            class MyNode(Node):
                host = 'Something'
        self.assertRaises(TypeError, run)

    def test_running_actions_outside_env(self):
        # It should not be possible to run any action directly on the Node
        # without wrapping it in an Env object.
        class A(Node):
            def action(self):
                pass
        self.assertRaises(TypeError, A.action)

    def test_required_property(self):
        class A(Node):
            p = required_property()

            def action(self):
                self.p()
        env = Env(A())

        # NotImplementedError wrapped in ActionException
        self.assertRaises(ActionException, env.action)
        try:
            env.action()
        except ActionException as e:
            self.assertIsInstance(e.inner_exception, NotImplementedError)

    def test_action_aliases(self):
        # We can define multiple aliases for an action.
        class A(Node):
            @alias('my_alias2')
            @alias('my_alias')
            def action(self):
                return 'result'

        env = Env(A())
        self.assertEqual(env.action(), 'result')
        self.assertEqual(env.my_alias(), 'result')
        self.assertEqual(env.my_alias2(), 'result')

    def test_from_simple_to_parent_to_normal(self):
        # We had the issue that when moving from a SimpleNode (C) back up to A
        # (which is a normal Node), into B (which is also a normal Node). B
        # didn't took it's own Hosts, but instead received all the hosts from
        # A.
        this = self

        class A(Node):
            class Hosts:
                host = { LocalHost1, LocalHost2, LocalHost3 }

            class B(Node):
                class Hosts:
                    host = { LocalHost4 }

            @map_roles('host')
            class C(SimpleNode.Array):
                def test(self):
                    this.assertEqual(len(self.parent.B.hosts), 1)

        env = Env(A())
        env.C.test()

    def test_super_call(self):
        # Calling the superclass
        class A(Node):
            def action(self):
                return 'result'

        class B(A):
            def action(self):
                return 'The result was %s' % A.action(self)

        env = Env(B())
        self.assertEqual(env.action(), 'The result was result')

    def test_default_action(self):
        class A(Node):
            class Hosts:
                role = { LocalHost1, LocalHost2 }

            def __call__(self):
                return 'A.call'

            class B(Node):
                def __call__(self):
                    return 'B.call'

            @map_roles('role')
            class C(SimpleNode.Array):
                def __call__(self):
                    return 'C.call'

        env = Env(A())
        self.assertEqual(env(), 'A.call')
        self.assertEqual(env.B(), 'B.call')
        self.assertEqual(list(env.C()), ['C.call', 'C.call'])
        self.assertEqual(env.C[0](), 'C.call')

    def test_going_from_isolated_to_parent(self):
        # When both B and C are a SimpleNode,
        # Going doing ``A.B.C[0].parent``, that should return a SimpleNode item.
        this = self

        class A(Node):
            class Hosts:
                role = { LocalHost1, LocalHost2 }

            @map_roles('role')
            class B(SimpleNode.Array):
                def action2(self):
                    this.assertEqual(len(self.hosts), 1)
                    this.assertEqual(self._node_is_isolated, True)

                class C(SimpleNode):
                    def action(self):
                        this.assertEqual(len(self.hosts), 1)
                        self.parent.action2()

        env = Env(A())
        env.B.C.action()
        env.B.C[0].action()
        env.B.C[1].action()

    def test_isolated_siblings(self):
        """
        Going from one isolated SimpleNode through the parent to its sibling.
        """
        this = self

        class Root(Node):
            class Hosts:
                host = { LocalHost1, LocalHost2 }

            @map_roles(host='host')
            class A(SimpleNode.Array):
                class B(SimpleNode):
                    q1 = Q.parent.C
                    q2 = Q.parent.parent.A.C

                    def action(self):
                        # parent.C belongs to the same isolation.
                        this.assertEqual(repr(self.parent.C), 'Env(Root.A[0].C)')
                        this.assertEqual(repr(self.q1), 'Env(Root.A[0].C)')

                        # If we go two levels up, and end up in the root, then
                        # we get a list of isolations.
                        this.assertEqual(repr(list(self.parent.parent.A.C)), '[Env(Root.A[0].C), Env(Root.A[1].C)]')
                        this.assertEqual(len(list(self.parent.parent.A.C)), 2)
                        this.assertEqual(repr(list(self.q2)), '[Env(Root.A[0].C), Env(Root.A[1].C)]')
                        this.assertEqual(len(list(self.q2)), 2)


                class C(SimpleNode):
                    pass

        env = Env(Root())
        env.A[0].B.action()

    def test_initialize_node(self):
        class A(Node):
            class Hosts:
                role1 = { LocalHost2 }
                role2 = { LocalHost4, LocalHost5 }

            def action(self):
                # Define a new Node-tree
                class B(Node):
                    class Hosts:
                        role2 = self.hosts.filter('role2')

                    def action2(self):
                        return len(self.hosts)

                # Initialize it in the current Env, and call an action of that one.
                return self.initialize_node(B).action2()

        env = Env(A())
        self.assertEqual(env.action(), 2)

    def test_additional_roles_in_simple_node(self):
        # We should be able to pass additional roles to a SimpleNode, but
        # isolation happens at the 'host' role.
        this = self
        counter = [0]

        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2, LocalHost3 }
                role2 = { LocalHost2, LocalHost4, LocalHost5 }

            @map_roles('role1', extra='role2')
            class B(SimpleNode.Array):
                def action(self):
                    this.assertEqual(len(self.hosts.filter('host')), 1)
                    this.assertEqual(len(self.hosts.filter('extra')), 3)
                    this.assertEqual(set(self.hosts.roles), set(['host', 'extra']))
                    self.C.action2()
                    counter[0] += 1

                class C(SimpleNode):
                    def action2(self):
                        this.assertEqual(len(self.hosts.filter('host')), 1)
                        this.assertEqual(len(self.hosts.filter('extra')), 3)
                        this.assertEqual(set(self.hosts.roles), set(['host', 'extra']))
                        counter[0] += 1

        env = Env(A())
        env.B.action()
        self.assertEqual(counter[0], 6)

    def test_nesting_normal_node_in_simple_node(self):
        # It is possible to nest multiple sequences of Node-SimpleNode.Array
        # inside each other. This behaves like a multi-dimensional array.

        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2, LocalHost3 }
                role2 = { LocalHost2, LocalHost4, LocalHost5 }

            @map_roles('role1', extra='role2')
            class B(SimpleNode.Array):
                class C(SimpleNode):
                    @map_roles(role='extra')
                    class D(Node):
                        @map_roles('role')
                        class E(SimpleNode.Array):
                            # At this point, for each 'cell', there will be only
                            # one host in the role 'host'. We are mapping this one
                            # down in the following Node, and SimpleNode. But that
                            # means that for any 'isolation', the host in E and G
                            # will be the same.
                            @map_roles(role='host')
                            class F(Node):
                                @map_roles('role')
                                class G(SimpleNode.Array):
                                    def action(self):
                                        pass

        env = Env(A())
        self.assertEqual(env.B.C[0]._node_is_isolated, True)
        self.assertEqual(env.B.C[0].parent._node_is_isolated, True)

        # Test all possible kinds of indexes.
        # Any transition from a normal Node to a SimpleNode.Array
        # should add one dimension.
        nodes = [
            env.B[0].C,
            env.B[0].C.D,
            env.B[0].C.D.E[0],
            env.B.C.D.E[(0, 0)],
            env.B[0].C.D.E[0],
            env.B[0].C.D.E[0].F.G[0],
            env.B.C.D.E[(0,0)].F.G[0],
            env.B.C.D[0].E[0].F.G[0],
            env.B.C.D[(0,)].E[(0,)].F.G[(0,)],
            env.B.C.D.E.F.G[(0,0,0)],

            env.B[LocalHost1],
            env.B[LocalHost2],
            env.B[LocalHost1].C.D.E[0],
            env.B[LocalHost1].C.D.E[LocalHost2],
            env.B[LocalHost1].C.D.E[LocalHost4],
            env.B[LocalHost1].C.D.E[LocalHost4],
            env.B[LocalHost1].C.D.E[LocalHost4].F.G[LocalHost4],
            env.B[LocalHost1].C.D.E.F.G[(LocalHost4, LocalHost4)],
            env.B.C.D[LocalHost1].E.F.G[(LocalHost4, LocalHost4)],
            env.B.C.D.E.F.G[(LocalHost1, LocalHost4, LocalHost4)],

            env.B['localhost1'],
            env.B.C.D.E.F.G[('localhost1', 'localhost4', 'localhost4')],
        ]
        for n in nodes:
            self.assertIsInstance(n, Env)

        for index, node in Inspector(env.B.C.D.E.F.G).iter_isolations(IsolationIdentifierType.HOSTS_SLUG):
            # See comment above in the Nodes. For this example the nodes in the second and third
            # are the same.
            self.assertEqual(index[1], index[2])

        # Following are not possible
        self.assertRaises(KeyError, lambda: env.B[0].C.D.E[0].F[0].G)
        self.assertRaises(KeyError, lambda: env.B[0].C[0].D[0])
        self.assertRaises(KeyError, lambda: env.B[(0, 1)])
        self.assertRaises(KeyError, lambda: env.B[LocalHost4])
        self.assertRaises(KeyError, lambda: env.B.C.D.E[LocalHost1].F.G[(LocalHost4, LocalHost4)])
        self.assertRaises(KeyError, lambda: env.B['localhost5'])

    def test_simplenode_just_one(self):
        # In contrast with .Array, the .JustOne should
        # make sure that it doesn't behave as an array,
        # but instead asserts that it will only get one
        # host for this role.
        class A(Node):
            class Hosts:
                role1 = { LocalHost1, LocalHost2 }
                role2 = LocalHost3

            @map_roles('role2')
            class B(SimpleNode.JustOne):
                def action(self):
                    return 'result'

        env = Env(A())
        self.assertEqual(env.B._node_is_isolated, True)
        self.assertEqual(env.B.action(), 'result')

    def test_hostcontainer_from_node(self):
        this = self

        class A(Node):
            class Hosts:
                role1 = LocalHost1

            def action(self):
                with self.hosts.cd('/tmp'):
                    this.assertEqual(self.hosts.getcwd(), ['/tmp'])
                    this.assertEqual(self.hosts[0].getcwd(), '/tmp')
                    this.assertEqual(self.hosts[0].run('pwd').strip(), '/tmp')

                    with self.hosts.cd('/'):
                        this.assertEqual(self.hosts[0].run('pwd').strip(), '/')

                    this.assertEqual(self.hosts[0].run('pwd').strip(), '/tmp')

        env = Env(A())
        env.action()

    def test_double_array(self):
        # It's not allowed to use the .Array operation multiple times on the same class.
        # The same is true for JustOne.
        class A(SimpleNode):
            pass

        self.assertRaises(Exception, lambda:SimpleNode.Array.Array)
        self.assertRaises(Exception, lambda:SimpleNode.Array.JustOne)
        self.assertRaises(Exception, lambda:SimpleNode.JustOne.JustOne)
        self.assertRaises(Exception, lambda:SimpleNode.JustOne.Array)

    def test_action_alias(self):
        """
        By using the @alias decorator around an action, the action should be
        available through multiple names.
        """
        class Root(Node):
            @alias('b.c.d')
            @alias('b')
            def a(self):
                return 'result'
        env = Env(Root())
        self.assertEqual(env.a(), 'result')
        self.assertEqual(env.b(), 'result')
        self.assertEqual(getattr(env, 'b.c.d')(), 'result')

    def test_node_console(self):
        class Root(Node):
            def a(self):
                return 'result'

        # Test Console instance.
        p = Pty()
        env = Env(Root(), pty=p)
        self.assertIsInstance(env.console, Console)
        self.assertEqual(env.console.pty, p)
        self.assertEqual(env.console.is_interactive, p.interactive) #

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = our_hosts
from deployer.host import LocalHost
from deployer.host import SSHHost

import os
import getpass


class LocalHost1(LocalHost):
    # Act as another host then localhost
    slug = 'localhost1'

class LocalHost2(LocalHost):
    # Act as another host then localhost
    slug = 'localhost2'

class LocalHost3(LocalHost):
    # Act as another host then localhost
    slug = 'localhost3'

class LocalHost4(LocalHost):
    # Act as another host then localhost
    slug = 'localhost4'

class LocalHost5(LocalHost):
    # Act as another host then localhost
    slug = 'localhost5'


class LocalSSHHost1(SSHHost):
    """
    Passwordless SSH connection to localhost.

    To generate the certificate, do:

    $ ssh-keygen -f ~/.ssh/id_rsa_local -N ""
    $ cat id_rsa_local.pub >> authorized_keys
    """
    key_filename = os.path.expanduser('~/.ssh/id_rsa_local')
    address = 'localhost'
    username = getpass.getuser()
    slug = 'local-ssh-1'

class LocalSSHHost2(LocalSSHHost1):
    slug = 'local-ssh-2'

class LocalSSHHost3(LocalSSHHost1):
    slug = 'local-ssh-3'

class LocalSSHHost4(LocalSSHHost1):
    slug = 'local-ssh-4'

class LocalSSHHost5(LocalSSHHost1):
    slug = 'local-ssh-5'

########NEW FILE########
__FILENAME__ = pty_test
import unittest

from deployer.pseudo_terminal import Pty

class PtyTest(unittest.TestCase):
    def test_get_size(self):
        # Create pty from standard stdin/stdout
        p = Pty()

        # Test get_size -> returns height,width
        size = p.get_size()
        self.assertIsInstance(size, tuple)
        self.assertEqual(len(size), 2)
        self.assertIsInstance(size[0], int)
        self.assertIsInstance(size[1], int)

        # Test get_width
        width = p.get_width()
        self.assertIsInstance(width, int)
        self.assertEqual(width, size[1])

        # Test get_height
        height = p.get_height()
        self.assertIsInstance(height, int)
        self.assertEqual(height, size[0])

        # Test set_term_var/get_term_var
        p.set_term_var('my-custom-xterm')
        self.assertEqual('my-custom-xterm', p.get_term_var())

########NEW FILE########
__FILENAME__ = query_test
import unittest

from deployer.query import Q, Query, QueryResult
from deployer.node import Node, Env
from deployer.exceptions import QueryException, ActionException

from .our_hosts import LocalHost


def get_query_result(query, instance):
    return query._execute_query(instance).result


class ExpressionTest(unittest.TestCase):
    def test_literals(self):
        # Literals
        q = Q('string')
        self.assertEqual(get_query_result(q, None), 'string')

        q = Q(55)
        self.assertEqual(get_query_result(q, None), 55)

        q = Q(True)
        self.assertEqual(get_query_result(q, None), True)

        q = Q(False)
        self.assertEqual(get_query_result(q, None), False)

    def test_operator_overloads(self):
        # Simple operator overloads (Both Q objects)
        q = Q('a') + Q('b')
        self.assertEqual(get_query_result(q, None), 'ab')

        q = Q(1) + Q(2)
        self.assertEqual(get_query_result(q, None), 3)

        q = Q(2) - Q(1)
        self.assertEqual(get_query_result(q, None), 1)

        q = Q(3) * Q(4)
        self.assertEqual(get_query_result(q, None), 12)

        q = Q(12) / Q(4)
        self.assertEqual(get_query_result(q, None), 3)

        # Simple operator overloads (Q object on the left.)
        q = Q('a') + 'b'
        self.assertEqual(get_query_result(q, None), 'ab')

        q = Q(1) + 2
        self.assertEqual(get_query_result(q, None), 3)

        q = Q(2) - 1
        self.assertEqual(get_query_result(q, None), 1)

        q = Q(3) * 4
        self.assertEqual(get_query_result(q, None), 12)

        q = Q(12) / 4
        self.assertEqual(get_query_result(q, None), 3)

        # Simple operator overloads (Q object on the right.)
        q = 'a' + Q('b')
        self.assertEqual(get_query_result(q, None), 'ab')

        q = 1 + Q(2)
        self.assertEqual(get_query_result(q, None), 3)

        q = 2 - Q(1)
        self.assertEqual(get_query_result(q, None), 1)

        q = 3 * Q(4)
        self.assertEqual(get_query_result(q, None), 12)

        q = 12 / Q(4)
        self.assertEqual(get_query_result(q, None), 3)

    def test_string_interpolation(self):
        # String interpolation
        q = Q('before %s after') % 'value'
        self.assertEqual(get_query_result(q, None), 'before value after')

    def test_booleans(self):
        # And/or/not
        q = Q(True) & Q(True)
        self.assertEqual(get_query_result(q, None), True)

        q = Q(True) & Q(False)
        self.assertEqual(get_query_result(q, None), False)

        q = Q(True) | Q(False)
        self.assertEqual(get_query_result(q, None), True)

        q = Q(False) | Q(False)
        self.assertEqual(get_query_result(q, None), False)

        q = ~ Q(False)
        self.assertEqual(get_query_result(q, None), True)

        q = ~ Q(True)
        self.assertEqual(get_query_result(q, None), False)

        # Combinations
        q = Q(False) | ~ Q(False)
        self.assertEqual(get_query_result(q, None), True)

    def test_resolve_types(self):
        q = Q(Q('a'))
        self.assertEqual(get_query_result(q, None), 'a')

        q = Q([Q('%s') % 'a'])
        self.assertEqual(get_query_result(q, None), ['a'])

        q = Q('%s: %s') % ('a', 'b')
        self.assertEqual(get_query_result(q, None), 'a: b')

        q = Q('%s: %s') % (Q('a'), Q('b'))
        self.assertEqual(get_query_result(q, None), 'a: b')

        q = Q(['a', 'b']) + ['c', 'd']
        self.assertEqual(get_query_result(q, None), ['a', 'b', 'c', 'd'])

        q = Q(['a', 'b']) + [Q('c'), Q('d')]
        self.assertEqual(get_query_result(q, None), ['a', 'b', 'c', 'd'])

        q = Q('%(A)s: %(B)s') % {'A': 'a', 'B': 'b'}
        self.assertEqual(get_query_result(q, None), 'a: b')

        q = Q('%(A)s: %(B)s') % {Q('A'): Q('a'), Q('B'): Q('b')}
        self.assertEqual(get_query_result(q, None), 'a: b')

class ReprTest(unittest.TestCase):
    def test_reprs(self):
        # Operators
        self.assertEqual(repr(Q(4) + Q(5)), '4 + 5')
        self.assertEqual(repr(Q(4) - Q(5)), '4 - 5')
        self.assertEqual(repr(Q(4) * Q(5)), '4 * 5')
        self.assertEqual(repr(Q(4) / Q(5)), '4 / 5')

        # Booleans
        self.assertEqual(repr(Q(4) | ~ Q(5)), '4 | ~ 5')
        self.assertEqual(repr(Q(4) & ~ Q(5)), '4 & ~ 5')

        # Attributes and calls
        self.assertEqual(repr(Q.a), 'Q.a')
        self.assertEqual(repr(Q.b['lookup']), "Q.b['lookup']")
        self.assertEqual(repr(Q.a.call('param') + Q.b['lookup']), "Q.a.call('param') + Q.b['lookup']")
        self.assertEqual(repr(Q.a.call('param', 'p2', key='value')), "Q.a.call('param', 'p2', key='value')")
        self.assertEqual(repr(Q.a.call(Q.a)), "Q.a.call(Q.a)")


class InContextTest(unittest.TestCase):
    """
    Evaluation of expressions, on a context object.
    (The context is usually a Node in practise.)
    """
    def setUp(self):
        class Obj(object):
            value = 'value'

            def action(self):
                return 'action-result'

            def __getitem__(self, item):
                return 'item %s' % item

            def true(self): return True
            def false(self): return False

        obj = Obj()
        obj.nested_obj = obj
        self.obj = obj

    def test_q_attribute_selection(self):
        # Combinations of attribute lookups, __getitem__ and calling.
        q = Q.value
        self.assertEqual(get_query_result(q, self.obj), 'value')

        q = Q['attr']
        self.assertEqual(get_query_result(q, self.obj), 'item attr')

        q = Q.action()
        self.assertEqual(get_query_result(q, self.obj), 'action-result')

        q = Q.nested_obj.action()
        self.assertEqual(get_query_result(q, self.obj), 'action-result')

        q = Q.nested_obj.action()
        self.assertEqual(get_query_result(q, self.obj), 'action-result')

        q = Q.nested_obj.nested_obj['attr']
        self.assertEqual(get_query_result(q, self.obj), 'item attr')

        # Add some operators
        q = Q.nested_obj.nested_obj.value + '-' + Q.value
        self.assertEqual(get_query_result(q, self.obj), 'value-value')

        q = ~ Q.true()
        self.assertEqual(get_query_result(q, self.obj), False)

        q = Q.true() & Q.nested_obj.true()
        self.assertEqual(get_query_result(q, self.obj), True)

        q = Q.true() | Q.nested_obj.false()
        self.assertEqual(get_query_result(q, self.obj), True)

    def test_query_result(self):
        """
        Analysis of the following hierarchical query.

        # Q                               | <q_object_test.Obj object at 0x976d64c>
        # Q.true                          | <bound method Obj.true of <q_object_test.Obj object at 0x976d64c>>
        # Q.true()                        | True
        # Q                               | <q_object_test.Obj object at 0x976d64c>
        # Q.nested_obj                    | <q_object_test.Obj object at 0x976d64c>
        # Q.nested_obj.false              | <bound method Obj.false of <q_object_test.Obj object at 0x976d64c>>
        # Q.nested_obj.false()            | False
        # Q.true() | Q.nested_obj.false() | True
        """
        def count(query):
            result = query._execute_query(self.obj)
            return len(list(result.walk_through_subqueries()))

        # Check subquery count
        q = Q
        self.assertEqual(count(q), 1)

        q = Q.true
        self.assertEqual(count(q), 2)

        q = Q.true()
        self.assertEqual(count(q), 3)

        q = Q.nested_obj
        self.assertEqual(count(q), 2)

        q = Q.nested_obj.false
        self.assertEqual(count(q), 3)

        q = Q.nested_obj.false()
        self.assertEqual(count(q), 4)

        q = Q.true() | Q.nested_obj.false()
        self.assertEqual(count(q), 8)

        # Check subquery order.
        q = Q.true() | Q.nested_obj.false()
        result = q._execute_query(self.obj)
        self.assertIsInstance(result, QueryResult)

            # The first parameter contains all the subqueries that are executed.
        queries = [ r[0] for r in result.walk_through_subqueries() ]
        self.assertEqual(map(repr, queries), [
                 'Q',
                 'Q.true',
                 'Q.true()',
                 'Q',
                 'Q.nested_obj',
                 'Q.nested_obj.false',
                 'Q.nested_obj.false()',
                 'Q.true() | Q.nested_obj.false()' ])

        for q in queries:
            self.assertIsInstance(q, Query)

            # The second parameter contains the results for the respective subqueries.
        results = [ r[1] for r in result.walk_through_subqueries() ]
        self.assertEqual(results[2], True)
        self.assertEqual(results[6], False)
        self.assertEqual(results[7], True)


class InActionTest(unittest.TestCase):
    def test_q_navigation(self):
        this = self
        class DummyException(Exception):
            pass

        class MyNode(Node):
            class Hosts:
                host = LocalHost

            # 1. Normal query from node.
            attr = 'value'
            query = Q.attr
            query2 = Q.attr + Q.attr

            def my_action(self):
                return self.query

            # 2. Exception in query from node.

            @property
            def this_raises(self):
                raise DummyException

            query3 = Q.this_raises + Q.attr

            def my_action2(self):
                # Calling query3 raises a QueryException
                # The inner exception that one is the DummyException
                try:
                    return self.query3
                except Exception as e:
                    this.assertIsInstance(e, ActionException)

                    this.assertIsInstance(e.inner_exception, QueryException)
                    this.assertIsInstance(e.inner_exception.node, MyNode)
                    this.assertIsInstance(e.inner_exception.query, Query)

                    this.assertIsInstance(e.inner_exception.inner_exception, DummyException)

                    # Raising the exception again at this point, will turn it
                    # into an action exception.
                    raise

        s = MyNode()
        env = Env(s)

        # 1.
        self.assertEqual(env.my_action(), 'value')
        self.assertEqual(env.query2, 'valuevalue')

        # 2.
        self.assertRaises(ActionException, env.my_action2)
        try:
            env.my_action2()
        except Exception as e:
            self.assertIsInstance(e, ActionException)


########NEW FILE########
__FILENAME__ = utils_test
import unittest
from deployer.utils import parse_ifconfig_output

output_1 = """
eth0      Link encap:Ethernet  HWaddr 08:00:27:4c:bc:84
          inet addr:10.0.3.15  Bcast:10.0.3.255  Mask:255.255.255.0
          inet6 addr: fe80::a00:27ff:fe4c:bc83/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:3008946 errors:0 dropped:0 overruns:0 frame:0
          TX packets:2245787 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:521487561 (521.4 MB)  TX bytes:1485805583 (1.4 GB)

lo        Link encap:Local Loopback
          inet addr:127.0.0.1  Mask:255.0.0.0
          inet6 addr: ::1/128 Scope:Host
          UP LOOPBACK RUNNING  MTU:16436  Metric:1
          RX packets:448011 errors:0 dropped:0 overruns:0 frame:0
          TX packets:448011 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:0
          RX bytes:213448877 (213.4 MB)  TX bytes:213448877 (213.4 MB)

tap7      Link encap:Ethernet  HWaddr 66:72:04:b6:81:d4
          inet addr:46.29.46.232  Bcast:46.28.46.255  Mask:255.255.255.0
          inet6 addr: fe80::6472:4ff:feb6:81d3/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:981 errors:0 dropped:631 overruns:0 frame:0
          TX packets:60 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:100
          RX bytes:85606 (85.6 KB)  TX bytes:11787 (11.7 KB)"""

output_2 = """
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
    options=3<RXCSUM,TXCSUM>
    inet6 fe80::1%lo0 prefixlen 64 scopeid 0x1
    inet 127.0.0.1 netmask 0xff000000
    inet6 ::1 prefixlen 128
gif0: flags=8010<POINTOPOINT,MULTICAST> mtu 1280
stf0: flags=0<> mtu 1280
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
    ether 20:c9:d0:83:95:39
    inet6 fe80::22c9:d0ff:fe83:9539%en0 prefixlen 64 scopeid 0x4
    inet 10.126.120.72 netmask 0xffff0000 broadcast 10.126.255.255
    media: autoselect
    status: active
p2p0: flags=8843<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> mtu 2304
    ether 02:c9:d0:83:95:44
    media: autoselect
    status: inactive
en2: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
    options=b<RXCSUM,TXCSUM,VLAN_HWTAGGING>
    ether a8:20:67:2b:e0:3e
    inet6 fe80::aa20:66ff:fe2b:e03f%en2 prefixlen 64 scopeid 0x6
    inet 10.126.100.28 netmask 0xffff0000 broadcast 10.126.255.255
    media: autoselect (1000baseT <full-duplex>)
    status: active
"""

class UtilsTest(unittest.TestCase):
    def test_node_initialisation(self):
        self.assertEqual(repr(parse_ifconfig_output(output_1)),
                "IfConfig(interfaces=[" +
                "NetworkInterface(name='eth0', ip='10.0.3.15'), " +
                "NetworkInterface(name='lo', ip='127.0.0.1'), " +
                "NetworkInterface(name='tap7', ip='46.29.46.232')])")

        self.assertEqual(repr(parse_ifconfig_output(output_2)),
                "IfConfig(interfaces=[" +
                "NetworkInterface(name='lo0', ip='127.0.0.1'), " +
                "NetworkInterface(name='en0', ip='10.126.120.72'), " +
                "NetworkInterface(name='en2', ip='10.126.100.28')])")

        # get_interface
        self.assertEqual(repr(parse_ifconfig_output(output_1).get_interface('eth0')),
                "NetworkInterface(name='eth0', ip='10.0.3.15')")
        self.assertRaises(AttributeError, parse_ifconfig_output(output_1).get_interface, 'eth100')

        # get_adress
        self.assertEqual(repr(parse_ifconfig_output(output_1).get_address('10.0.3.15')),
                "NetworkInterface(name='eth0', ip='10.0.3.15')")
        self.assertRaises(AttributeError, parse_ifconfig_output(output_1).get_address, '10.100.100.100')

########NEW FILE########
