__FILENAME__ = command
"""
This file is part of Candela.

Candela is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Candela is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Candela.  If not, see <http://www.gnu.org/licenses/>.
"""
import constants


class Command(object):
    """
    The representation of a single command available to the user
    A command exists within one menu at a time.
    A single command object can be used in multiple menus.
    """
    def __init__(self, definition, description):
        """
        Creates a new generic command, setting the default functions for run()
        and validate().
        These two commands are called on each matched command during the main loop.
        First, validate() is called. If validate() returns True, then run() is
        called. These are the default implementations, and can be overridden.

        The default validation function simply parses the command definition and
        ensures that those arguments specified as required by that definition are
        present in a command input string.

        The default run function does nothing. It only returns the marker for
        command success and exits. Command run functions can also return the string
        name of another menu. If this happens, the shell state will switch to that
        menu, if it exists.

        The parser implements a specific syntax for required and optional arguments.
        See parse_definition() for details.

        Args:
        definition      - The definition string, following the specific syntax
                          detailed in the parse_definition() docstring
        description     - The human-readable description of what the command does
                          and how to use it
        """
        self.name = definition.split()[0]
        self.aliases = []

        self.definition = definition
        self.description = description

        self.args,self.kwargs = self.parse_definition(definition.split())

        def runner(*args, **kwargs):
            return constants.CHOICE_VALID
        self.run = runner

        def validator(*args, **kwargs):
            required_params = list(self.args)
            for kw in self.kwargs.keys():
                name,reqd = self.kwargs[kw]
                if reqd:
                    required_params.append(kw)
            if len(args) + len(kwargs) < len(required_params):
                return (False, "Usage: %s" % self.definition)
            for kw in self.kwargs.keys():
                name,reqd = self.kwargs[kw]
                if reqd and kw not in kwargs.keys():
                    return (False, "Usage: %s" % (self.definition))
            return (True, "")
        self.validate = validator
        self.default_validate = validator

        # the hooks used to tab complete each argument
        # keys are the argument names used in the definition, values are callbacks
        # returning lists of completions
        self.tabcomplete_hooks = {}

    def parse_command(self, tokens):
        """
        Parse a command input string into a series of tokens, and subsequently
        argument data.

        The syntax for a command input string is simple. It consists of the command
        name or alias followed by a sequence of space-separated tokens. A token
        can be either a single-letter flag prefixed with '-' or a word of
        abritrary length.

        Semantics of command input strings:
        command     ::= command_name ([flag] argument)*
        flag        ::= -(letter)
        argument    ::= (letter | digit | _)*
        command_name::= (letter | digit | _)*
        letter      ::= (lowercase | uppercase)*
        lowercase   ::= "a"..."z"
        uppercase   ::= "A"..."Z"
        digit       ::= "0"..."9"

        Args:
        tokens  - The list of tokens, the result of input_string.split()

        Returns the tuple of positional arguments and the dictionary of
        flag: arg_value pairs of keyword arguments
        """
        args = []
        kwargs = {}
        current_key = None
        parsing_named = False
        for token in tokens:
            if token == self.name or token in self.aliases:
                continue
            if "-" not in token:
                if not parsing_named:
                    args.append(token)
                else:
                    kwargs[current_key] = token
                    parsing_named = False
            else:
                if not parsing_named:
                    parsing_named = True
                    current_key = token.strip("-")
                else:
                    raise ParseException("Unexpected '-' in command input")
        if parsing_named:
            raise ParseException("Unexpected end of command input")
        return (args, kwargs)

    def parse_definition(self, tokens):
        """
        Parse the command definition into a listing of required commands, to
        be used for validation

        The syntax of command definitions allows the specification of positional
        and named arguments. The named arguments can be required or optional. All
        positional arguments are required.

        Command definition semantics:
        definition      ::= command_name (positional)* (named)*
        command_name    ::= (letter | digit | _)*
        positional      ::= (letter | digit | _)*
        argument        ::= (letter | digit | _)*
        named           ::= (required | optional)
        required        ::= "<"flag argument">"
        optional        ::= "["flag argument"]"
        flag            ::= -(letter)
        letter          ::= (lowercase | uppercase)*
        lowercase       ::= "a"..."z"
        uppercase       ::= "A"..."Z"
        digit           ::= "0"..."9"

        More directly, this is an example command definition:
        my_command arg1 arg2 <-f im_required> [-o im_optional]
        You can also examine shell_example.py for more examples of command definitions

        Args:
        tokens  - The list of tokens, the result of definition.split()
        """
        args = []
        kwargs = {}  # key: (value, optional)
        parsing_optional = False
        parsing_reqd = False
        current_key = None
        for token in tokens:
            if token == self.name:
                continue
            if not any((spec_char in token) for spec_char in ["<", "]", "[", ">"]):
                args.append(token)
            else:
                if token.startswith("<"):
                    if not parsing_reqd:
                        current_key = token.strip("<-")
                        parsing_reqd = True
                    else:
                        raise ParseException("Encountered unexpected '<'")
                elif token.startswith("["):
                    if not parsing_optional:
                        current_key = token.strip("[-")
                        parsing_optional = True
                    else:
                        raise ParseException("Encountered unexpected '['")
                elif token.endswith(">"):
                    if parsing_reqd:
                        kwargs[current_key] = (token.strip(">"), True)
                        parsing_reqd = False
                    else:
                        raise ParseException("Encountered unexpected '>'")
                elif token.endswith("]"):
                    if parsing_optional:
                        kwargs[current_key] = (token.strip("]"), False)
                        parsing_optional = False
                    else:
                        raise ParseException("Encountered unexpected ']'")
        if parsing_optional or parsing_reqd:
            raise ParseException("Unexpected end of command definition: %s" % (token))
        return (args, kwargs)


    def __str__(self):
        ret = "%s\n    %s" % (self.definition, self.description)
        if self.aliases:
            ret += "\n    Aliases: %s" % ",".join(self.aliases)
        return ret

    def alias(self, alias):
        """
        Create an alias for this command.
        An alias is simply an alternate name for the command.
        A command can be invoked by using any of its aliases or its name.

        Args:
        alias       - The string by which to alias this command
        """
        if alias not in self.aliases:
            self.aliases.append(alias)

    def _tabcomplete(self, buff):
        """
        Get a list of possible completions for the current buffer, called when
        the user presses Tab.

        This is called in the event that the buffer starts with a valid command name
        and contains unfinished argument input.

        Partially parses the command string, determines the name of the argument
        currently being typed, and calls the Command object's tabcomplete hook
        corresponding to that argument.

        Tabcomplete hooks are callback functions that can be defined per command
        argument. They take as an argument the current last token in the command input
        buffer, which is usually a fragment of an argument. They return a list of
        strings representing possible completions for the current argument. The
        default hook returns an empty list.

        Hooks are looked up from the self.tabcomplete_hooks dictionary by
        argument name. For example, if this command takes an argument my_arg like so:
        testcommand my_arg
        the corresponding tabcomplete hook can be found in self.tabcomplete_hooks['my_arg']

        Args:
        buff    - The string buffer representing the current unfinished command input

        Return:
        A list of completion strings for the current token in the command
        """
        def __default(frag):
            return []
        func = __default
        tokens = buff.split()
        if '-' in tokens[-1] and not buff.endswith(' '):
            return []
        if len(tokens) >= 2:
            if buff.endswith(' '):
                arg_is_named = '-' in tokens[-1]
            else:
                arg_is_named = '-' in tokens[-2]
        else:
            arg_is_named = False
        num_named = len([a for a in tokens if '-' in a])
        if arg_is_named:
            try:
                flag_index = -2
                if buff.endswith(' '):
                    flag_index = -1
                arg_name, reqd = self.kwargs[tokens[flag_index].strip('-')]
            except:
                return __default(tokens[-1])
        else:
            arg_index = len(tokens) - (2 * num_named)
            if buff.endswith(' '):
                arg_index -= 1
            else:
                arg_index -= 2
            try:
                arg_name = self.args[arg_index]
            except:
                return __default(tokens[-1])
        if arg_name in self.tabcomplete_hooks:
            func = self.tabcomplete_hooks[arg_name]
        results = func(tokens[-1])
        if buff.endswith(' '):
            return results
        return [a for a in results if a.startswith(tokens[-1])]


class BackCommand(Command):
    """
    A command that, on success, reverts the latest new menu action by resetting
    the shell to the previous menu.
    """
    def __init__(self, tomenu):
        super(BackCommand, self).__init__('back', 'Back to the %s menu' % tomenu)

        def _run(*args, **kwargs):
            return tomenu
        self.run = _run

        self.default_run = _run


class QuitCommand(Command):
    """
    A command that, on success, quits the shell and cleans up the window.
    It does this by returning CHOICE_QUIT, which is the escape sequence
    for which the shell's main loop is listening.
    """
    def __init__(self, name):
        super(QuitCommand, self).__init__('quit', 'Quit %s' % name)

        def _run(*args, **kwargs):
            return constants.CHOICE_QUIT
        self.run = _run

        self.default_run = _run


class RunScriptCommand(Command):
    """
    A command that, on success, loads and runs a candela shell script.
    """
    def __init__(self, shell):
        super(RunScriptCommand, self).__init__('run scriptfile', 'Run a script')

        self.shell = shell

        def _run(*args, **kwargs):
            self.shell.runscript(args[0])
        self.run = _run

        self.default_run = _run


class ClearCommand(Command):
    """
    Command wrapper around Shell.clear()

    Clears all scrollback text from the window
    """
    def __init__(self, shell):
        super(ClearCommand, self).__init__('clear', 'Clear the screen')

        self.shell = shell

        def _run(*args, **kwargs):
            self.shell.clear()
            return constants.CHOICE_VALID
        self.run = _run

        self.default_run = _run


class ParseException(Exception):
    pass

########NEW FILE########
__FILENAME__ = constants
"""
This file is part of Candela.

Candela is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Candela is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Candela.  If not, see <http://www.gnu.org/licenses/>.
"""

CHOICE_INVALID = 0
CHOICE_VALID = 1
CHOICE_QUIT = 2
CHOICE_BACK = 3
FAILURE = 11

########NEW FILE########
__FILENAME__ = menu
"""
This file is part of Candela.

Candela is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Candela is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Candela.  If not, see <http://www.gnu.org/licenses/>.
"""

class Menu():
    """
    Simple representation of a menu: one state of the state machine
    created by Candela.
    Consists of a series of Commands
    One Shell instance may have one or more menus.
    """
    def __init__(self, name):
        self.name = name
        self.title = ''
        self.commands = []

    def options(self):
        """
        Return the string representations of the options for this menu
        """
        ret = ""
        for command in self.commands:
            ret += "%s\n" % str(command)
        return ret

########NEW FILE########
__FILENAME__ = shell
"""
This file is part of Candela.

Candela is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Candela is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Candela.  If not, see <http://www.gnu.org/licenses/>.
"""
import curses
import sys
import signal
import threading
import textwrap
import platform

import constants


class Shell():
    """
    The main Candela class
    Controls the shell by taking control of the current terminal window.
    Performs input and output to the user
    """
    def __init__(self, scriptfile=None):
        """
        Create an instance of a Shell
        This call takes over the current terminal by calling curses.initscr()
        Sets global shell state, including size information, menus, stickers,
        the header, and the prompt.

        Kwargs:
        scriptfile - the name of the script file to run. If not None and the
                     file exists, the script will be immediately run.
        """
        self._register_sigint_handler()

        self.script_lines = self._parse_script_file(scriptfile)
        self.script_counter = 0
        self.scriptfile = ""

        self.stdscr = curses.initscr()
        self.stdscr.keypad(1)

        self.platform = self._get_platform()

        # holds the backlog of shell output
        self.backbuffer = []
        self.height,self.width = self.stdscr.getmaxyx()

        # the list of menus in the shell app
        self.menus = []
        # the currently visible stickers in the app
        self.stickers = []

        # should the command menu be shown
        self.should_show_help = True
        # for commands with only positional args, show the
        # name of the next argument as the user types
        self.should_show_hint = False

        # dictionary of functions to call on key events
        # keys are chars representing the pressed keys
        self.keyevent_hooks = {}

        # the text to stick in the upper left corner of the window
        self.header = ""
        self._header_bottom = 0
        self._header_right = 0
        self._header_right_margin = 50

        self.prompt = "> "

    def _parse_script_file(self, filename):
        """
        Open a file if it exists and return its contents as a list of lines

        Args:
        filename - the file to attempt to open
        """
        self.scriptfile = filename
        try:
            f = open(filename, 'r')
            script_lines = f.readlines()
            script_lines = [a.strip('\n') for a in script_lines]
            f.close()
        except Exception as e:
            return
        return script_lines

    def runscript(self, scriptfile):
        """
        Set up the global shell state necessary to run a script from a file

        Args:
        scriptfile - the string name of the file containing the script.
                     paths are relative to system cwd
        """
        self.script_lines = self._parse_script_file(scriptfile)
        self.script_counter = 0

    def get_helpstring(self):
        """
        Get the help string for the current menu.

        This string contains a preformatted list of commands and their
        descriptions from the current menu.
        """
        _menu = self.get_menu()
        if not _menu:
            return

        helpstring = "\n\n" + _menu.title + "\n" + "-"*20 + "\n" + _menu.options()
        return helpstring

    def sticker(self, output, new_output="", pos=None):
        """
        Place, change, or remove a sticker from the shell window.

        Candela has the concept of a sticker - a small block of text that
        is "stuck" to the window. They can be used to convey persistent
        information to the shell user.

        If only output is specified, this creates a new sticker with the string
        output. If output and new_output are specified, and there is an existing
        sticker whose text is the same as output, this will replace that
        sticker's text with new_output.

        Args:
        output      - The text of the sticker to manipulate

        Kwargs:
        new_output  - The text that will replace the text of the chosen sticker
        pos         - The (y, x) tuple indicating where to place the sticker
        """
        if len(self.stickers) > 0:
            sort = sorted(self.stickers, key=lambda x: x[1][0], reverse=True)
            ht = sort[0][1][0]+1
        else:
            ht = 3

        pos = pos or (ht, self.width - 20)

        match = None
        for text,_pos in self.stickers:
            if output == text:
                match = (text,_pos)
                break
        if match:
            self.remove_sticker(match[0])

        sticker = (new_output or output, match[1] if match else pos)
        self.stickers.append(sticker)

        self._update_screen()

    def remove_sticker(self, text):
        """
        Remove the sticker with the given text from the window

        Args:
        text    - The text of the sticker to remove
        """
        self.stickers = [a for a in self.stickers if a[0] != text]


    def _print_stickers(self):
        """
        Print all current stickers at the appropriate positions
        """
        for text,pos in self.stickers:
            _y,_x = pos
            if _x + len(text) > self.width:
                _x = self.width - len(text) - 1
            self.stdscr.addstr(_y, _x, text)

    def _print_header(self):
        """
        Print the header in the appropriate position
        """
        ht = 0
        for line in self.header.split("\n"):
            self.stdscr.addstr(ht, 0, line + (" "*self._header_right_margin))
            if len(line) > self._header_right:
                self._header_right = len(line)
            ht += 1
        self.stdscr.addstr(ht, 0, " "*(self._header_right+self._header_right_margin))
        self._header_bottom = ht
        self.mt_width = self._header_right + 49

    def clear(self):
        """
        Remove all scrollback text from the window
        """
        backbuffer = list(self.backbuffer)
        printstring = "\n"
        for i in range(self.height):
            self.put(printstring)

    def _print_backbuffer(self):
        """
        Print the previously printed output above the current command line.

        candela.shell.Shell stores previously printed commands and output
        in a backbuffer. Like a normal shell, it handles printing these lines
        in reverse order to allow the user to see their past work.
        """
        rev = list(self.backbuffer)
        rev.reverse()

        for i, tup in zip(range(len(rev)), rev):
            string, iscommand = tup
            ypos = self.height-2-i
            if ypos > 0:
                printstring = string
                if iscommand:
                    printstring = "%s%s" % (self.prompt, string)
                self.stdscr.addstr(ypos,0,printstring)

    def _print_help(self):
        """
        Print the menu help box for the current menu
        """
        _helpstring = self.get_helpstring()
        if not _helpstring:
            return
        helpstrings = [" %s" % a for a in _helpstring.split("\n")]
        ht = 0
        longest = len(max(helpstrings, key=len))
        _x = self._header_right + self._header_right_margin
        if _x + longest > self.width:
            _x = self.width - longest - 1
        for line in helpstrings:
            self.stdscr.addstr(ht, _x, line + " "*15)
            ht += 1

    def put(self, output, command=False):
        """
        Print the output string on the bottom line of the shell window
        Also pushes the backbuffer up the screen by the number of lines
        in output.

        Args:
        output  - The string to print. May contain newlines

        Kwargs:
        command - False if the string was not a user-entered command,
                  True otherwise (users of Candela should always use False)
        """
        self._update_screen()

        if not output:
            return

        output = str(output)

        _x,_y = (self.height-1, 0)

        lines = []
        for line in output.split('\n'):
            if len(line) > self.width - 3:
                for line in textwrap.wrap(line, self.width-3):
                    lines.append(line)
            else:
                lines.append(line)

        for line in lines:
            # put the line
            self.stdscr.addstr(_x, _y, line)

            # add it to backbuffer
            backbuf_string = line
            to_append = (backbuf_string, command)
            if line != self.prompt:
                index = 0
                if len(self.backbuffer) >= 200:
                    index = 1
                self.backbuffer = self.backbuffer[index:] + [to_append]

    def _input(self, prompt):
        """
        Handle user input on the shell window.
        Works similarly to python's raw_input().
        Takes a prompt and returns the raw string entered before the return key
        by the user.

        The input is returned withnewlines stripped.

        Args:
        prompt  - The text to display prompting the user to enter text
        """
        self.put(prompt)
        keyin = ''
        buff = ''
        hist_counter = 1
        while keyin != 10:
            keyin = self.stdscr.getch()
            _y,_x = self.stdscr.getyx()
            index = _x - len(self.prompt)
            #self.stdscr.addstr(20, 70, str(keyin))  # for debugging
            try:
                if chr(keyin) in self.keyevent_hooks.keys():
                    cont = self.keyevent_hooks[chr(keyin)](chr(keyin), buff)
                    if cont == False:
                        continue
            except:
                pass
            if keyin in [127, 263]:  # backspaces
                del_lo, del_hi = self._get_backspace_indices()
                buff = buff[:index+del_lo] + buff[index+del_hi:]
                self._redraw_buffer(buff)
                self.stdscr.move(_y, max(_x+del_lo, len(self.prompt)))
            elif keyin in [curses.KEY_UP, curses.KEY_DOWN]:  # up and down arrows
                hist_counter,buff = self._process_history_command(keyin, hist_counter)
            elif keyin in [curses.KEY_LEFT, curses.KEY_RIGHT]:  # left, right arrows
                if keyin == curses.KEY_LEFT:
                    newx = max(_x - 1, len(self.prompt))
                elif keyin == curses.KEY_RIGHT:
                    newx = min(_x + 1, len(buff) + len(self.prompt))
                self.stdscr.move(_y, newx)
            elif keyin == curses.KEY_F1:  # F1
                curses.endwin()
                sys.exit()
            elif keyin in [9]:  # tab
                choices = self._tabcomplete(buff)
                if len(choices) == 1:
                    if len(buff.split()) == 1 and not buff.endswith(' '):
                        buff = choices[0]
                    else:
                        if len(buff.split()) != 1 and not buff.endswith(' '):
                            buff = ' '.join(buff.split()[:-1])
                        if buff.endswith(' '):
                            buff += choices[0]
                        else:
                            buff += ' ' + choices[0]
                elif len(choices) > 1:
                    self.put("    ".join(choices))
                elif len(choices) == 0:
                    pass
                self._redraw_buffer(buff)
            elif keyin >= 32 and keyin <= 126:  # ascii input
                buff = buff[:index-1] + chr(keyin) + buff[index-1:]
                self._redraw_buffer(buff)
                self.stdscr.move(_y, min(_x, len(buff) + len(self.prompt)))
                if self.should_show_hint and keyin == 32:
                    command = self._get_command(buff)
                    if hasattr(command, 'definition') and '-' not in command.definition:
                        try:
                            nextarg = command.definition.split()[len(buff.split())]
                            self.stdscr.addstr(_y, _x+1, nextarg)
                            self.stdscr.move(_y, _x)
                        except:
                            pass
        self.put(buff, command=True)
        self.stdscr.refresh()
        return buff

    def _get_backspace_indices(self):
        if self.platform == "Linux":
            return (0, 1)
        elif self.platform == "Darwin":
            return (-len(self.prompt)-1, -len(self.prompt))

    def _tabcomplete(self, buff):
        """
        Get a list of possible completions for the current buffer

        If the current buffer doesn't contain a valid command, see if the
        buffer is a prefix of any valid commands. If so, return those as possible
        completions. Otherwise, delegate the completion finding to the command object.

        Args:
        buff    - The string buffer representing the current unfinished command input

        Return:
        A list of completion strings for the current token in the command
        """
        menu = self.get_menu()
        commands = []
        if menu:
            commands = menu.commands
        output = []
        if len(buff.split()) <= 1 and ' ' not in buff:
            for command in commands:
                if command.name.startswith(buff):
                    output.append(command.name)
                for alias in command.aliases:
                    if alias.startswith(buff):
                        output.append(alias)
        else:
            command = self._get_command(buff)
            if command:
                output = command._tabcomplete(buff)
        return output

    def _get_command(self, buff):
        """
        Get the command instance referenced by string in the current input buffer

        Args:
        buff    - The string version of the current command input buffer

        Return:
        The Command instance corresponding to the buffer command
        """
        menu = self.get_menu()
        commands = []
        if menu:
            commands = menu.commands
        if len(commands) == 0:
            self.put("No commands found. Maybe you forgot to set self.menus or self.menu?")
            self.put("Hint: use F1 to quit")
        for command in commands:
            if command.name == buff.split()[0] or buff.split()[0] in command.aliases:
                return command
        return None

    def _redraw_buffer(self, buff):
        """
        Clear the bottom line and re-print the given string on that line

        Args:
        buff    - The line to print on the cleared bottom line
        """
        self.stdscr.addstr(self.height-1, 0, " "*(self.width-3))
        self.stdscr.addstr(self.height-1, 0, "%s%s" % (self.prompt, buff))

    def _process_history_command(self, keyin, hist_counter):
        """
        Get the next command from the backbuffer and return it
        Also return the modified buffer counter.

        Args:
        keyin           - The key just pressed
        hist_counter    - The current position in the backbuffer
        """
        hist_commands = [(s,c) for s,c in self.backbuffer if c]
        if not hist_commands:
            return hist_counter, ""

        buff = hist_commands[-hist_counter][0]

        self.stdscr.addstr(self.height-1, 0, " "*(self.width-3))
        self.stdscr.addstr(self.height-1, 0, "%s%s" % (self.prompt, buff))

        if keyin == curses.KEY_UP and hist_counter < len(hist_commands):
            hist_counter += 1
        elif keyin == curses.KEY_DOWN and hist_counter > 0:
            hist_counter -= 1
        return hist_counter, buff

    def _script_in(self):
        """
        Substitute for _input used when reading from a script.
        Returns the next command from the script being read.
        """
        if not self.script_lines:
            return None

        if self.script_counter < len(self.script_lines):
            command = self.script_lines[self.script_counter]
            self.script_counter += 1
        else:
            command = None
        return command

    def main_loop(self):
        """
        The main shell IO loop.
        The sequence of events is as follows:
            get an input command
            split into tokens
            find matching command
            validate tokens for command
            run command

        This loop can be broken out of only with by a command returning
        constants.CHOICE_QUIT or by pressing F1
        """
        ret_choice = None
        while ret_choice != constants.CHOICE_QUIT:
            success = True
            ret_choice = constants.CHOICE_INVALID
            choice = self._script_in()
            if choice:
                self.put("%s%s" % (self.prompt, choice))
            else:
                choice = self._input(self.prompt)
            tokens = choice.split()
            if len(tokens) == 0:
                self.put("\n")
                continue
            command = self._get_command(choice)
            if not command:
                self.put("Invalid command - no match")
                continue
            try:
                args, kwargs = command.parse_command(tokens)
                success, message = command.validate(*args, **kwargs)
                if not success:
                    self.put(message)
                else:
                    ret_choice = command.run(*args, **kwargs)
                    if ret_choice == constants.CHOICE_INVALID:
                        self.put("Invalid command")
                    else:
                        menus = [a.name for a in self.menus]
                        if str(ret_choice).lower() in menus:
                            self.menu = ret_choice.lower()
                        else:
                            self.put("New menu '%s' not found" % ret_choice.lower())
            except Exception as e:
                self.put(e)
        return self

    def get_menu(self):
        """
        Get the current menu as a Menu
        """
        if not self.menus: return
        try:
            return [a for a in self.menus if a.name == self.menu][0]
        except:
            return

    def defer(self, func, args=(), kwargs={}, timeout_duration=10, default=None):
        """
        Create a new thread, run func in the thread for a max of
        timeout_duration seconds
        This is useful for blocking operations that must be performed
        after the next window refresh.
        For example, if a command should set a sticker when it starts executing
        and then clear that sticker when it's done, simply using the following
        will not work:

        def _run(*args, **kwargs):
            self.sticker("Hello!")
            # do things...
            self.remove_sticker("Hello!")

        This is because the sticker is both added and removed in the same
        refresh loop of the window. Put another way, the sticker is added and
        removed before the window gets redrawn.

        defer() can be used to get around this by scheduling the sticker
        to be removed shortly after the next window refresh, like so:

        def _run(*args, **kwargs):
            self.sticker("Hello!")
            # do things...
            def clear_sticker():
                time.sleep(.1)
                self.remove_sticker("Hello!")
            self.defer(clear_sticker)

        Args:
        func        - The callback function to run in the new thread

        Kwargs:
        args        - The arguments to pass to the threaded function
        kwargs      - The keyword arguments to pass to the threaded function
        timeout_duration - the amount of time in seconds to wait before
                           killing the thread
        default     - The value to return in case of a timeout
        """
        class InterruptableThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.result = default
            def run(self):
                self.result = func(*args, **kwargs)
        it = InterruptableThread()
        it.start()
        it.join(timeout_duration)
        if it.isAlive():
            return it.result
        else:
            return it.result

    def end(self):
        """
        End the current Candela shell and safely shut down the curses session
        """
        curses.endwin()

    def _register_sigint_handler(self):
        """
        Properly handle ^C and any other method of sending SIGINT.
        This avoids leaving the user with a borked up terminal.
        """
        def signal_handler(signal, frame):
            self.end()
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

    def _update_screen(self):
        """
        Refresh the screen and redraw all elements in their appropriate positions
        """
        self.height,self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()

        self._print_backbuffer()

        if self.width < self._header_right + 80 or self.height < self._header_bottom + 37:
            pass
        else:
            self._print_header()
            if self.should_show_help:
                self._print_help()
        self._print_stickers()

        self.stdscr.refresh()

    def _get_platform(self):
        """
        Return the platform name. This is fine, but it's used in a hacky way to
        get around a backspace-cooking behavior in Linux (at least Ubuntu)
        """
        return platform.uname()[0]

########NEW FILE########
__FILENAME__ = shell_example
"""
This file is part of Candela.

Candela is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Candela is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Candela.  If not, see <http://www.gnu.org/licenses/>.
"""
import getpass

from candela.shell import Shell
from candela.menu import Menu
from candela.command import Command, QuitCommand, RunScriptCommand, BackCommand, ClearCommand
from candela import constants


class MyShell(Shell):
    def __init__(self):
        Shell.__init__(self)

        self.name = "My Shell"

        # set the header that appears in the top left of the shell
        self.header = """
   ___                _      _
  / __\__ _ _ __   __| | ___| | __ _
 / /  / _` | '_ \ / _` |/ _ \ |/ _` |
/ /__| (_| | | | | (_| |  __/ | (_| |
\____/\__,_|_| |_|\__,_|\___|_|\__,_|
                                      """

        # place sticky text on the top right side of the shell
        # you can change this text by calling sticker() from a command
        self.sticker("Welcome, %s" % getpass.getuser())

        # define commands
        hello_world_com = self.build_hello_command()
        named_com = self.build_named_args_command()
        complex_com = self.build_complex_command()
        invalid_com = self.build_invalid_command()
        quit_com = self.build_quit_command()
        clear_com = self.build_clear_command()
        sticker_com = self.build_sticker_command()
        builtins_com = self.build_builtin_command()

        # define menus
        main_menu = Menu('main')
        #menu display title
        main_menu.title = "Main menu"
        # list of Command objects making up menu
        main_menu.commands = [hello_world_com, named_com, complex_com, sticker_com,
                              invalid_com, builtins_com, clear_com, quit_com, ]

        script_com = self.build_script_command()
        back_com = self.build_back_command()

        builtins_menu = Menu('builtins')
        builtins_menu.title = "Built-in commands menu"
        builtins_menu.commands = [script_com, hello_world_com, back_com, quit_com]

        # list of all menus in the app
        self.menus = [main_menu, builtins_menu]
        # name of default menu
        self.menu = 'main'

        self.put("""
Welcome to Candela, the simple python shell builder.
You can use Candela to build your own shell-based interfaces.
This is especially good for custom offline tools for games or web production.
For example, if your game requires lots of data in a custom XML format, you can
use Candela to easily set up an editor for that data.

This is an instructional shell app built in Candela that demonstrates its functionality.
Try any of the commands listed in the menu bar to continue.
        """)

        def _backslash_event(key, buff):
            self.put("""
This is a key event hook. It is called every time you press %s, and runs a
callback function that you define. This callback must take as parameters the
key character that was pressed and the current state of the command input
buffer.
            """ % key)
        self.keyevent_hooks['\\'] = _backslash_event

    def build_hello_command(self):
        com = Command('first_command', 'Intro to commands')
        def _run(*args, **kwargs):
            self.put("""
Congratulations, you just invoked your first command in Candela.
This text is being printed from inside a callback function passed to the library
via a Command object.
You can print text to your shell from anywhere in your Shell subclass by calling
self.put().
            """)
            return constants.CHOICE_VALID
        com.run = _run
        return com

    def build_named_args_command(self):
        com = Command('named my_arg <-f filename> [-g othername]', 'Demonstrate arguments')
        def _val(*args, **kwargs):
            success,message = com.default_validate(*args, **kwargs)
            if not success:
                if len(args) == 0 and len(kwargs) == 0:
                    self.put("""
Some commands accept command line arguments.
When creating a command, you specify these arguments with a special (simple) syntax.
For example, this command is called "%s". It accepts both positional and named arguments.

Positional arguments are indicated by a bare word following the command's name
in the command definition.
Named arguments are wrapped in either <> or [], and contain both the argument name
(starting with '-') and a helpful tip about the argument function.
Named arguments with <> are required, those with [] are optional.

This command also demonstrates customizable tab completion hooks. Try pressing
Tab after typing '%s s' and before typing enter. You'll see a list of possible
completions for your argument.

You can customize these commands by supplying callbacks to Command.tabcomplete_hooks.


Try passing arguments to this command!
                    """ % (com.name, com.name))
                else:
                    self.put("""
This command requires one unnamed argument followed by a named argument (-f).
Try this:
%s helloworld -f data.txt
                    """ % com.name)
                return (False, message)
            return (success, message)
        com.validate = _val

        def _run(*args, **kwargs):
            self.put("Got arguments:")
            self.put(args)
            self.put(kwargs)
            self.put("Arguments are passed around in a format quite familiar to python:")
            self.put("Positional arguments in a list, named arguments in a dictionary")
            return constants.CHOICE_VALID
        com.run = _run

        def _complete_myarg(frag):
            return ['some', 'random', 'choices']
        com.tabcomplete_hooks['my_arg'] = _complete_myarg

        def _complete_file(frag):
            from os import listdir
            from os.path import isfile, join
            onlyfiles = [f for f in listdir('.') if isfile(join('.',f))]
            return onlyfiles
        com.tabcomplete_hooks['filename'] = _complete_file

        return com

    def build_invalid_command(self):
        com = Command('broken', 'Demonstrate invalid command')
        def _run(*args, **kwargs):
            self.put("I will never print")
            return constants.CHOICE_VALID
        com.run = _run

        def _val(*args, **kwargs):
            message = """
You can write custom validation functions for your commands.
A validation function will run before execution of the command.
If the validation returns False, the command is not run.
The default validation function checks for the presence of all required
arguments, but you can override this behavior by setting the Command's validate member.

This is a command that always fails to validate.
            """
            return (False, message)
        com.validate = _val

        return com

    def build_complex_command(self):
        com = Command('cat <-f filename>', 'Demonstrate arbitrary python running')
        def _run(*args, **kwargs):
            self.put("""
Commands can run arbitrary python via a callback. Here's a callback that reads a
file from your local drive and prints it to the shell.
            """)
            try:
                with open(kwargs['f'], 'r') as f:
                    self.put(f.read())
            except IOError:
                self.put("%s : No such file!" % kwargs['f'])
            return constants.CHOICE_VALID
        com.run = _run
        return com

    def build_sticker_command(self):
        com = Command('make_sticker text', 'Make a new sticker')
        def _run(*args, **kwargs):
            self.put("""
This command places a 'sticker' on the terminal. Use these to present persistent
data to the user.
            """)
            self.sticker(" ".join(args))
            return constants.CHOICE_VALID
        com.run = _run
        return com

    def build_builtin_command(self):
        com = Command('builtins', 'Go to builtin commands menu')
        def _run(*args, **kwargs):
            self.put("""
Commands can conditionally lead the user to other menus.
This demo app has two menus defined: the main menu and the built-in commands menu.
The command you just ran has returned the string 'builtins' to point to the
builtins menu. 'builtins' is the name of the new menu.

Notice that the options menu has changed to reflect the new commands available in this menu.
            """)
            return 'builtins'
        com.run = _run
        return com

    def build_script_command(self):
        com = RunScriptCommand(self)
        def _run(*args, **kwargs):
            self.put("""
This command runs a script.
A Candela script is simply a text file containing one command per line.
            """)
            com.default_run(*args, **kwargs)
            return constants.CHOICE_VALID
        com.run = _run

        def _val(*args, **kwargs):
            success, message = com.default_validate(*args, **kwargs)
            if not success:
                self.put("""
Try running\nrun script_example.txt
                """)
                return (False, message)
            return (success, message)
        com.validate = _val
        return com

    def build_back_command(self):
        return BackCommand('main')

    def build_quit_command(self):
        quit_com = QuitCommand(self.name)
        quit_com.alias('q')
        return quit_com

    def build_clear_command(self):
        clear_com = ClearCommand(self)
        return clear_com


if __name__ == "__main__":
    MyShell().main_loop().end()

########NEW FILE########
