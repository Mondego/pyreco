__FILENAME__ = conque
# FILE:     autoload/conque_term/conque.py 
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Vim terminal emulator.

This class is the main interface between Vim and the terminal application. It 
handles both updating the Vim buffer with new output and accepting new keyboard
input from the Vim user.

Although this class was originally designed for a Unix terminal environment, it
has been extended by the ConqueSole class for Windows.

Usage:
    term = Conque()
    term.open('/bin/bash', {'TERM': 'vt100'})
    term.write("ls -lha\r")
    term.read()
    term.close()
"""

import vim
import re
import math


class Conque:

    # screen object
    screen = None

    # subprocess object
    proc = None

    # terminal dimensions and scrolling region
    columns = 80 # same as $COLUMNS
    lines = 24 # same as $LINES
    working_columns = 80 # can be changed by CSI ? 3 l/h
    working_lines = 24 # can be changed by CSI r

    # top/bottom of the scroll region
    top = 1 # relative to top of screen
    bottom = 24 # relative to top of screen

    # cursor position
    l = 1 # current cursor line
    c = 1 # current cursor column

    # autowrap mode
    autowrap = True

    # absolute coordinate mode
    absolute_coords = True

    # tabstop positions
    tabstops = []

    # enable colors
    enable_colors = True

    # color changes
    color_changes = {}

    # color history
    color_history = {}

    # color highlight cache
    highlight_groups = {}

    # prune terminal colors
    color_pruning = True

    # don't wrap table output
    unwrap_tables = True

    # wrap CUF/CUB around line breaks
    wrap_cursor = False

    # do we need to move the cursor?
    cursor_set = False

    # current character set, ascii or graphics
    character_set = 'ascii'

    # used for auto_read actions
    read_count = 0

    # input buffer, array of ordinals
    input_buffer = []

    def open(self):
        """ Start program and initialize this instance. 

        Arguments:
        command -- Command string to execute, e.g. '/bin/bash --login'
        options -- Dictionary of environment vars to set and other options.

        """
        # get arguments
        command = vim.eval('command')
        options = vim.eval('options')

        # create terminal screen instance
        self.screen = ConqueScreen()

        # int vars
        self.columns = vim.current.window.width
        self.lines = vim.current.window.height
        self.working_columns = vim.current.window.width
        self.working_lines = vim.current.window.height
        self.bottom = vim.current.window.height

        # offset first line to make room for startup messages
        if int(options['offset']) > 0:
            self.l = int(options['offset'])

        # init color
        self.enable_colors = options['color'] and not CONQUE_FAST_MODE

        # init tabstops
        self.init_tabstops()

        # open command
        self.proc = ConqueSubprocess()
        self.proc.open(command, {'TERM': options['TERM'], 'CONQUE': '1', 'LINES': str(self.lines), 'COLUMNS': str(self.columns)})

        # send window size signal, in case LINES/COLUMNS is ignored
        self.update_window_size(True)


    def write(self, input, set_cursor=True, read=True):
        """ Write a unicode string to the subprocess. 

        set_cursor -- Position the cursor in the current buffer when finished
        read -- Check program for new output when finished

        """
        # write and read
        self.proc.write(input)

        # read output immediately
        if read:
            self.read(1, set_cursor)



    def write_ord(self, input, set_cursor=True, read=True):
        """ Write a single character to the subprocess, using an unicode ordinal. """

        if CONQUE_PYTHON_VERSION == 2:
            self.write(unichr(input), set_cursor, read)
        else:
            self.write(chr(input), set_cursor, read)
        


    def write_expr(self, expr, set_cursor=True, read=True):
        """ Write the value of a Vim expression to the subprocess. """

        if CONQUE_PYTHON_VERSION == 2:
            try:
                val = vim.eval(expr)
                self.write(unicode(val, CONQUE_VIM_ENCODING, 'ignore'), set_cursor, read)
            except:

                pass
        else:
            try:
                # XXX - Depending on Vim to deal with encoding, sadly
                self.write(vim.eval(expr), set_cursor, read)
            except:

                pass


    def write_latin1(self, input, set_cursor=True, read=True):
        """ Write latin-1 string to conque. Very ugly, shood be removed. """
        # XXX - this whole method is a hack, to be removed soon

        if CONQUE_PYTHON_VERSION == 2:
            try:
                input_unicode = input.decode('latin-1', 'ignore')
                self.write(input_unicode.encode('utf-8', 'ignore'), set_cursor, read)
            except:
                return
        else:
            self.write(input, set_cursor, read)


    def write_buffered_ord(self, chr):
        """ Add character ordinal to input buffer. In case we're not allowed to modify buffer a time of input. """
        self.input_buffer.append(chr)


    def read(self, timeout=1, set_cursor=True, return_output=False, update_buffer=True):
        """ Read new output from the subprocess and update the Vim buffer.

        Arguments:
        timeout -- Milliseconds to wait before reading input
        set_cursor -- Set the cursor position in the current buffer when finished
        return_output -- Return new subprocess STDOUT + STDERR as a string
        update_buffer -- Update the current Vim buffer with the new output

        This method goes through the following rough steps:
            1. Get new output from subprocess
            2. Split output string into control codes, escape sequences, or plain text
            3. Loop over and process each chunk, updating the Vim buffer as we go

        """
        output = ''

        # this may not actually work
        try:

            # read from subprocess and strip null characters
            output = self.proc.read(timeout)

            if output == '':
                return

            # for bufferless terminals
            if not update_buffer:
                return output



            # strip null characters. I'm still not sure why they appear
            output = output.replace(chr(0), '')

            # split input into individual escape sequences, control codes, and text output
            chunks = CONQUE_SEQ_REGEX.split(output)



            # if there were no escape sequences, skip processing and treat entire string as plain text
            if len(chunks) == 1:
                self.plain_text(chunks[0])

            # loop through and process escape sequences
            else:
                for s in chunks:
                    if s == '':
                        continue




                    # Check for control character match 
                    if CONQUE_SEQ_REGEX_CTL.match(s[0]):

                        nr = ord(s[0])
                        if nr in CONQUE_CTL:
                            getattr(self, 'ctl_' + CONQUE_CTL[nr])()
                        else:

                            pass

                    # check for escape sequence match 
                    elif CONQUE_SEQ_REGEX_CSI.match(s):

                        if s[-1] in CONQUE_ESCAPE:
                            csi = self.parse_csi(s[2:])

                            getattr(self, 'csi_' + CONQUE_ESCAPE[s[-1]])(csi)
                        else:

                            pass

                    # check for title match 
                    elif CONQUE_SEQ_REGEX_TITLE.match(s):

                        self.change_title(s[2], s[4:-1])

                    # check for hash match 
                    elif CONQUE_SEQ_REGEX_HASH.match(s):

                        if s[-1] in CONQUE_ESCAPE_HASH:
                            getattr(self, 'hash_' + CONQUE_ESCAPE_HASH[s[-1]])()
                        else:

                            pass

                    # check for charset match 
                    elif CONQUE_SEQ_REGEX_CHAR.match(s):

                        if s[-1] in CONQUE_ESCAPE_CHARSET:
                            getattr(self, 'charset_' + CONQUE_ESCAPE_CHARSET[s[-1]])()
                        else:

                            pass

                    # check for other escape match 
                    elif CONQUE_SEQ_REGEX_ESC.match(s):

                        if s[-1] in CONQUE_ESCAPE_PLAIN:
                            getattr(self, 'esc_' + CONQUE_ESCAPE_PLAIN[s[-1]])()
                        else:

                            pass

                    # else process plain text 
                    else:
                        self.plain_text(s)

            # set cusor position
            if set_cursor:
                self.screen.set_cursor(self.l, self.c)

            # we need to set the cursor position
            self.cursor_set = False

        except:


            pass

        if return_output:
            if CONQUE_PYTHON_VERSION == 3:
                return output
            else:
                return output.encode(CONQUE_VIM_ENCODING, 'replace')


    def auto_read(self):
        """ Poll program for more output. 

        Since Vim doesn't have a reliable event system that can be triggered when new
        output is available, we have to continually poll the subprocess instead. This
        method is called many times a second when the terminal buffer is active, so it
        needs to be very fast and efficient.

        The feedkeys portion is required to reset Vim's timer system. The timer is used
        to execute this command, typically set to go off after 50 ms of inactivity.

        """
        # process buffered input if any
        if len(self.input_buffer):
            for chr in self.input_buffer:
                self.write_ord(chr, set_cursor=False, read=False)
            self.input_buffer = []
            self.read(1)

        # check subprocess status, but not every time since it's CPU expensive
        if self.read_count % 32 == 0:
            if not self.proc.is_alive():
                vim.command('call conque_term#get_instance().close()')
                return

            if self.read_count > 512:
                self.read_count = 0

                # trim color history occasionally if desired
                if self.enable_colors and self.color_pruning:
                    self.prune_colors()

        # ++
        self.read_count += 1

        # read output
        self.read(1)

        # reset timer
        if self.c == 1:
            vim.command('call feedkeys("\<right>\<left>", "n")')
        else:
            vim.command('call feedkeys("\<left>\<right>", "n")')

        # stop here if cursor doesn't need to be moved
        if self.cursor_set:
            return

        # check if window size has changed
        if not CONQUE_FAST_MODE:
            self.update_window_size()


        # otherwise set cursor position
        try:
            self.set_cursor(self.l, self.c)
        except:


            pass

        self.cursor_set = True


    def plain_text(self, input):
        """ Write text output to Vim buffer.

  
        This method writes a string of characters without any control characters or escape sequences
        to the Vim buffer. In simple terms, it writes the input string to the buffer starting at the
        current cursor position, wrapping the text to a new line if needed. It also triggers the 
        terminal coloring methods if needed.


        """
        # translate input into graphics character set if needed
        if self.character_set == 'graphics':
            old_input = input
            input = u('')
            for i in range(0, len(old_input)):
                chrd = ord(old_input[i])


                try:
                    if chrd > 255:

                        input = input + old_input[i]
                    else:
                        input = input + uchr(CONQUE_GRAPHICS_SET[chrd])
                except:

                    pass



        # get current line from Vim buffer
        current_line = self.screen[self.l]

        # pad current line with spaces, if it's shorter than cursor position
        if len(current_line) < self.c:
            current_line = current_line + ' ' * (self.c - len(current_line))

        # if line is wider than screen
        if self.c + len(input) - 1 > self.working_columns:

            # Table formatting hack
            if self.unwrap_tables and CONQUE_TABLE_OUTPUT.match(input):
                self.screen[self.l] = current_line[:self.c - 1] + input + current_line[self.c + len(input) - 1:]
                self.apply_color(self.c, self.c + len(input))
                self.c += len(input)
                return


            diff = self.c + len(input) - self.working_columns - 1

            # if autowrap is enabled
            if self.autowrap:
                self.screen[self.l] = current_line[:self.c - 1] + input[:-1 * diff]
                self.apply_color(self.c, self.working_columns)
                self.ctl_nl()
                self.ctl_cr()
                remaining = input[-1 * diff:]

                self.plain_text(remaining)
            else:
                self.screen[self.l] = current_line[:self.c - 1] + input[:-1 * diff - 1] + input[-1]
                self.apply_color(self.c, self.working_columns)
                self.c = self.working_columns

        # no autowrap
        else:
            self.screen[self.l] = current_line[:self.c - 1] + input + current_line[self.c + len(input) - 1:]
            self.apply_color(self.c, self.c + len(input))
            self.c += len(input)



    def apply_color(self, start, end, line=0):
        """ Apply terminal colors to buffer for a range of characters in a single line. 

        When a text attribute escape sequence is encountered during input processing, the
        attributes are recorded in the dictionary self.color_changes. After those attributes
        have been applied, the changes are recorded in a second dictionary self.color_history.

  
        This method inspects both dictionaries to calculate any syntax highlighting 
        that needs to be executed to render the text attributes in the Vim buffer.


        """


        # stop here if coloration is disabled
        if not self.enable_colors:
            return

        # allow custom line nr to be passed
        if line:
            buffer_line = line
        else:
            buffer_line = self.get_buffer_line(self.l)

        # check for previous overlapping coloration

        to_del = []
        if buffer_line in self.color_history:
            for i in range(len(self.color_history[buffer_line])):
                syn = self.color_history[buffer_line][i]

                if syn['start'] >= start and syn['start'] < end:

                    vim.command('syn clear ' + syn['name'])
                    to_del.append(i)
                    # outside
                    if syn['end'] > end:

                        self.exec_highlight(buffer_line, end, syn['end'], syn['highlight'])
                elif syn['end'] > start and syn['end'] <= end:

                    vim.command('syn clear ' + syn['name'])
                    to_del.append(i)
                    # outside
                    if syn['start'] < start:

                        self.exec_highlight(buffer_line, syn['start'], start, syn['highlight'])

        # remove overlapped colors
        if len(to_del) > 0:
            to_del.reverse()
            for di in to_del:
                del self.color_history[buffer_line][di]

        # if there are no new colors
        if len(self.color_changes) == 0:
            return

        # build the color attribute string
        highlight = ''
        for attr in self.color_changes.keys():
            highlight = highlight + ' ' + attr + '=' + self.color_changes[attr]

        # execute the highlight
        self.exec_highlight(buffer_line, start, end, highlight)


    def exec_highlight(self, buffer_line, start, end, highlight):
        """ Execute the Vim commands for a single syntax highlight """

        syntax_name = 'ConqueHighLightAt_%d_%d_%d_%d' % (self.proc.pid, self.l, start, len(self.color_history) + 1)
        syntax_options = 'contains=ALLBUT,ConqueString,MySQLString,MySQLKeyword oneline'
        syntax_region = 'syntax match %s /\%%%dl\%%>%dc.\{%d}\%%<%dc/ %s' % (syntax_name, buffer_line, start - 1, end - start, end + 1, syntax_options)

        # check for cached highlight group
        hgroup = 'ConqueHL_%d' % (abs(hash(highlight)))
        if hgroup not in self.highlight_groups:
            syntax_group = 'highlight %s %s' % (hgroup, highlight)
            self.highlight_groups[hgroup] = hgroup
            vim.command(syntax_group)

        # link this syntax match to existing highlight group
        syntax_highlight = 'highlight link %s %s' % (syntax_name, self.highlight_groups[hgroup])



        vim.command(syntax_region)
        vim.command(syntax_highlight)

        # add syntax name to history
        if not buffer_line in self.color_history:
            self.color_history[buffer_line] = []

        self.color_history[buffer_line].append({'name': syntax_name, 'start': start, 'end': end, 'highlight': highlight})


    def prune_colors(self):
        """ Remove old syntax highlighting from the Vim buffer

        The kind of syntax highlighting required for terminal colors can make
        Conque run slowly. The prune_colors() method will remove old highlight definitions
        to keep the maximum number of highlight rules within a reasonable range.

        """


        buffer_line = self.get_buffer_line(self.l)
        ks = list(self.color_history.keys())

        for line in ks:
            if line < buffer_line - CONQUE_MAX_SYNTAX_LINES:
                for syn in self.color_history[line]:
                    vim.command('syn clear ' + syn['name'])
                del self.color_history[line]




    ###############################################################################################
    # Control functions 

    def ctl_nl(self):
        """ Process the newline control character. """
        # if we're in a scrolling region, scroll instead of moving cursor down
        if self.lines != self.working_lines and self.l == self.bottom:
            del self.screen[self.top]
            self.screen.insert(self.bottom, '')
        elif self.l == self.bottom:
            self.screen.append('')
        else:
            self.l += 1

        self.color_changes = {}

    def ctl_cr(self):
        """ Process the carriage return control character. """
        self.c = 1

        self.color_changes = {}

    def ctl_bs(self):
        """ Process the backspace control character. """
        if self.c > 1:
            self.c += -1

    def ctl_soh(self):
        """ Process the start of heading control character. """
        pass

    def ctl_stx(self):
        pass

    def ctl_bel(self):
        """ Process the bell control character. """
        vim.command('call conque_term#bell()')

    def ctl_tab(self):
        """ Process the tab control character. """
        # default tabstop location
        ts = self.working_columns

        # check set tabstops
        for i in range(self.c, len(self.tabstops)):
            if self.tabstops[i]:
                ts = i + 1
                break



        self.c = ts

    def ctl_so(self):
        """ Process the shift out control character. """
        self.character_set = 'graphics'

    def ctl_si(self):
        """ Process the shift in control character. """
        self.character_set = 'ascii'



    ###############################################################################################
    # CSI functions 

    def csi_font(self, csi):
        """ Process the text attribute escape sequence. """
        if not self.enable_colors:
            return

        # defaults to 0
        if len(csi['vals']) == 0:
            csi['vals'] = [0]

        # 256 xterm color foreground
        if len(csi['vals']) == 3 and csi['vals'][0] == 38 and csi['vals'][1] == 5:
            self.color_changes['ctermfg'] = str(csi['vals'][2])
            self.color_changes['guifg'] = '#' + self.xterm_to_rgb(csi['vals'][2])

        # 256 xterm color background
        elif len(csi['vals']) == 3 and csi['vals'][0] == 48 and csi['vals'][1] == 5:
            self.color_changes['ctermbg'] = str(csi['vals'][2])
            self.color_changes['guibg'] = '#' + self.xterm_to_rgb(csi['vals'][2])

        # 16 colors
        else:
            for val in csi['vals']:
                if val in CONQUE_FONT:

                    # ignore starting normal colors
                    if CONQUE_FONT[val]['normal'] and len(self.color_changes) == 0:

                        continue
                    # clear color changes
                    elif CONQUE_FONT[val]['normal']:

                        self.color_changes = {}
                    # save these color attributes for next plain_text() call
                    else:

                        for attr in CONQUE_FONT[val]['attributes'].keys():
                            if attr in self.color_changes and (attr == 'cterm' or attr == 'gui'):
                                self.color_changes[attr] += ',' + CONQUE_FONT[val]['attributes'][attr]
                            else:
                                self.color_changes[attr] = CONQUE_FONT[val]['attributes'][attr]


    def csi_clear_line(self, csi):
        """ Process the line clear escape sequence. """


        # this escape defaults to 0
        if len(csi['vals']) == 0:
            csi['val'] = 0




        # 0 means cursor right
        if csi['val'] == 0:
            self.screen[self.l] = self.screen[self.l][0:self.c - 1]

        # 1 means cursor left
        elif csi['val'] == 1:
            self.screen[self.l] = ' ' * (self.c) + self.screen[self.l][self.c:]

        # clear entire line
        elif csi['val'] == 2:
            self.screen[self.l] = ''

        # clear colors
        if csi['val'] == 2 or (csi['val'] == 0 and self.c == 1):
            buffer_line = self.get_buffer_line(self.l)
            if buffer_line in self.color_history:
                for syn in self.color_history[buffer_line]:
                    vim.command('syn clear ' + syn['name'])





    def csi_cursor_right(self, csi):
        """ Process the move cursor right escape sequence. """
        # we use 1 even if escape explicitly specifies 0
        if csi['val'] == 0:
            csi['val'] = 1




        if self.wrap_cursor and self.c + csi['val'] > self.working_columns:
            self.l += int(math.floor((self.c + csi['val']) / self.working_columns))
            self.c = (self.c + csi['val']) % self.working_columns
            return

        self.c = self.bound(self.c + csi['val'], 1, self.working_columns)


    def csi_cursor_left(self, csi):
        """ Process the move cursor left escape sequence. """
        # we use 1 even if escape explicitly specifies 0
        if csi['val'] == 0:
            csi['val'] = 1

        if self.wrap_cursor and csi['val'] >= self.c:
            self.l += int(math.floor((self.c - csi['val']) / self.working_columns))
            self.c = self.working_columns - (csi['val'] - self.c) % self.working_columns
            return

        self.c = self.bound(self.c - csi['val'], 1, self.working_columns)


    def csi_cursor_to_column(self, csi):
        """ Process the move cursor to column escape sequence. """
        self.c = self.bound(csi['val'], 1, self.working_columns)


    def csi_cursor_up(self, csi):
        """ Process the move cursor up escape sequence. """
        self.l = self.bound(self.l - csi['val'], self.top, self.bottom)

        self.color_changes = {}


    def csi_cursor_down(self, csi):
        """ Process the move cursor down escape sequence. """
        self.l = self.bound(self.l + csi['val'], self.top, self.bottom)

        self.color_changes = {}


    def csi_clear_screen(self, csi):
        """ Process the clear screen escape sequence. """
        # default to 0
        if len(csi['vals']) == 0:
            csi['val'] = 0

        # 2 == clear entire screen
        if csi['val'] == 2:
            self.l = 1
            self.c = 1
            self.screen.clear()

        # 0 == clear down
        elif csi['val'] == 0:
            for l in range(self.bound(self.l + 1, 1, self.lines), self.lines + 1):
                self.screen[l] = ''

            # clear end of current line
            self.csi_clear_line(self.parse_csi('K'))

        # 1 == clear up
        elif csi['val'] == 1:
            for l in range(1, self.bound(self.l, 1, self.lines + 1)):
                self.screen[l] = ''

            # clear beginning of current line
            self.csi_clear_line(self.parse_csi('1K'))

        # clear coloration
        if csi['val'] == 2 or csi['val'] == 0:
            buffer_line = self.get_buffer_line(self.l)
            for line in self.color_history.keys():
                if line >= buffer_line:
                    for syn in self.color_history[line]:
                        vim.command('syn clear ' + syn['name'])

        self.color_changes = {}


    def csi_delete_chars(self, csi):
        self.screen[self.l] = self.screen[self.l][:self.c] + self.screen[self.l][self.c + csi['val']:]


    def csi_add_spaces(self, csi):
        self.screen[self.l] = self.screen[self.l][: self.c - 1] + ' ' * csi['val'] + self.screen[self.l][self.c:]


    def csi_cursor(self, csi):
        if len(csi['vals']) == 2:
            new_line = csi['vals'][0]
            new_col = csi['vals'][1]
        else:
            new_line = 1
            new_col = 1

        if self.absolute_coords:
            self.l = self.bound(new_line, 1, self.lines)
        else:
            self.l = self.bound(self.top + new_line - 1, self.top, self.bottom)

        self.c = self.bound(new_col, 1, self.working_columns)
        if self.c > len(self.screen[self.l]):
            self.screen[self.l] = self.screen[self.l] + ' ' * (self.c - len(self.screen[self.l]))



    def csi_set_coords(self, csi):
        if len(csi['vals']) == 2:
            new_start = csi['vals'][0]
            new_end = csi['vals'][1]
        else:
            new_start = 1
            new_end = vim.current.window.height

        self.top = new_start
        self.bottom = new_end
        self.working_lines = new_end - new_start + 1

        # if cursor is outside scrolling region, reset it
        if self.l < self.top:
            self.l = self.top
        elif self.l > self.bottom:
            self.l = self.bottom

        self.color_changes = {}


    def csi_tab_clear(self, csi):
        # this escape defaults to 0
        if len(csi['vals']) == 0:
            csi['val'] = 0



        if csi['val'] == 0:
            self.tabstops[self.c - 1] = False
        elif csi['val'] == 3:
            for i in range(0, self.columns + 1):
                self.tabstops[i] = False


    def csi_set(self, csi):
        # 132 cols
        if csi['val'] == 3:
            self.csi_clear_screen(self.parse_csi('2J'))
            self.working_columns = 132

        # relative_origin
        elif csi['val'] == 6:
            self.absolute_coords = False

        # set auto wrap
        elif csi['val'] == 7:
            self.autowrap = True


        self.color_changes = {}


    def csi_reset(self, csi):
        # 80 cols
        if csi['val'] == 3:
            self.csi_clear_screen(self.parse_csi('2J'))
            self.working_columns = 80

        # absolute origin
        elif csi['val'] == 6:
            self.absolute_coords = True

        # reset auto wrap
        elif csi['val'] == 7:
            self.autowrap = False


        self.color_changes = {}




    ###############################################################################################
    # ESC functions 

    def esc_scroll_up(self):
        self.ctl_nl()

        self.color_changes = {}


    def esc_next_line(self):
        self.ctl_nl()
        self.c = 1


    def esc_set_tab(self):

        if self.c <= len(self.tabstops):
            self.tabstops[self.c - 1] = True


    def esc_scroll_down(self):
        if self.l == self.top:
            del self.screen[self.bottom]
            self.screen.insert(self.top, '')
        else:
            self.l += -1

        self.color_changes = {}




    ###############################################################################################
    # HASH functions 

    def hash_screen_alignment_test(self):
        self.csi_clear_screen(self.parse_csi('2J'))
        self.working_lines = self.lines
        for l in range(1, self.lines + 1):
            self.screen[l] = 'E' * self.working_columns



    ###############################################################################################
    # CHARSET functions 

    def charset_us(self):
        self.character_set = 'ascii'

    def charset_uk(self):
        self.character_set = 'ascii'

    def charset_graphics(self):
        self.character_set = 'graphics'



    ###############################################################################################
    # Random stuff 

    def set_cursor(self, line, col):
        """ Set cursor position in the Vim buffer.

        Note: the line and column numbers are relative to the top left corner of the 
        visible screen. Not the line number in the Vim buffer.

        """
        self.screen.set_cursor(line, col)

    def change_title(self, key, val):
        """ Change the Vim window title. """


        if key == '0' or key == '2':

            vim.command('setlocal statusline=' + re.escape(val))
            try:
                vim.command('set titlestring=' + re.escape(val))
            except:
                pass

    def update_window_size(self, force=False):
        """ Check and save the current buffer dimensions.

        If the buffer size has changed, the update_window_size() method both updates
        the Conque buffer size attributes as well as sending the new dimensions to the
        subprocess pty.

        """
        # resize if needed
        if force or vim.current.window.width != self.columns or vim.current.window.height != self.lines:

            # reset all window size attributes to default
            self.columns = vim.current.window.width
            self.lines = vim.current.window.height
            self.working_columns = vim.current.window.width
            self.working_lines = vim.current.window.height
            self.bottom = vim.current.window.height

            # reset screen object attributes
            self.l = self.screen.reset_size(self.l)

            # reset tabstops
            self.init_tabstops()



            # signal process that screen size has changed
            self.proc.window_resize(self.lines, self.columns)

    def insert_enter(self):
        """ Run commands when user enters insert mode. """

        # check window size
        self.update_window_size()

        # we need to set the cursor position
        self.cursor_set = False

    def init_tabstops(self):
        """ Intitialize terminal tabstop positions. """
        for i in range(0, self.columns + 1):
            if i % 8 == 0:
                self.tabstops.append(True)
            else:
                self.tabstops.append(False)

    def idle(self):
        """ Called when this terminal becomes idle. """
        pass

    def resume(self):
        """ Called when this terminal is no longer idle. """
        pass
        pass

    def close(self):
        """ End the process running in the terminal. """
        self.proc.close()

    def abort(self):
        """ Forcefully end the process running in the terminal. """
        self.proc.signal(1)



    ###############################################################################################
    # Utility 

    def parse_csi(self, s):
        """ Parse an escape sequence into it's meaningful values. """

        attr = {'key': s[-1], 'flag': '', 'val': 1, 'vals': []}

        if len(s) == 1:
            return attr

        full = s[0:-1]

        if full[0] == '?':
            full = full[1:]
            attr['flag'] = '?'

        if full != '':
            vals = full.split(';')
            for val in vals:

                val = re.sub("\D", "", val)

                if val != '':
                    attr['vals'].append(int(val))

        if len(attr['vals']) == 1:
            attr['val'] = int(attr['vals'][0])

        return attr


    def bound(self, val, min, max):
        """ TODO: This probably exists as a builtin function. """
        if val > max:
            return max

        if val < min:
            return min

        return val


    def xterm_to_rgb(self, color_code):
        """ Translate a terminal color number into a RGB string. """
        if color_code < 16:
            ascii_colors = ['000000', 'CD0000', '00CD00', 'CDCD00', '0000EE', 'CD00CD', '00CDCD', 'E5E5E5',
                   '7F7F7F', 'FF0000', '00FF00', 'FFFF00', '5C5CFF', 'FF00FF', '00FFFF', 'FFFFFF']
            return ascii_colors[color_code]

        elif color_code < 232:
            cc = int(color_code) - 16

            p1 = "%02x" % (math.floor(cc / 36) * (255 / 5))
            p2 = "%02x" % (math.floor((cc % 36) / 6) * (255 / 5))
            p3 = "%02x" % (math.floor(cc % 6) * (255 / 5))

            return p1 + p2 + p3
        else:
            grey_tone = "%02x" % math.floor((255 / 24) * (color_code - 232))
            return grey_tone + grey_tone + grey_tone




    def get_buffer_line(self, line):
        """ Get the buffer line number corresponding to the supplied screen line number. """
        return self.screen.get_buffer_line(line)



########NEW FILE########
__FILENAME__ = conque_globals
# FILE:     autoload/conque_term/conque_globals.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Common global constants and functions for Conque."""

import sys
import re




# PYTHON VERSION
CONQUE_PYTHON_VERSION = sys.version_info[0]

# Encoding

try:
    # Vim's character encoding
    import vim
    CONQUE_VIM_ENCODING = vim.eval('&encoding')

except:
    CONQUE_VIM_ENCODING = 'utf-8'


def u(str_val, str_encoding='utf-8', errors='strict'):
    """ Foolhardy attempt to make unicode string syntax compatible with both python 2 and 3. """

    if not str_val:
        str_val = ''

    if CONQUE_PYTHON_VERSION == 3:
        return str_val

    else:
        return unicode(str_val, str_encoding, errors)

def uchr(str):
    """ Foolhardy attempt to make unicode string syntax compatible with both python 2 and 3. """

    if CONQUE_PYTHON_VERSION == 3:
        return chr(str)

    else:
        return unichr(str)


# Logging
















# Unix escape sequence settings

CONQUE_CTL = {
     1: 'soh', # start of heading
     2: 'stx', # start of text
     7: 'bel', # bell
     8: 'bs',  # backspace
     9: 'tab', # tab
    10: 'nl',  # new line
    13: 'cr',  # carriage return
    14: 'so',  # shift out
    15: 'si'   # shift in
}
#    11 : 'vt',  # vertical tab
#    12 : 'ff',  # form feed

# Escape sequences
CONQUE_ESCAPE = {
    'm': 'font',
    'J': 'clear_screen',
    'K': 'clear_line',
    '@': 'add_spaces',
    'A': 'cursor_up',
    'B': 'cursor_down',
    'C': 'cursor_right',
    'D': 'cursor_left',
    'G': 'cursor_to_column',
    'H': 'cursor',
    'P': 'delete_chars',
    'f': 'cursor',
    'g': 'tab_clear',
    'r': 'set_coords',
    'h': 'set',
    'l': 'reset'
}
#    'L': 'insert_lines',
#    'M': 'delete_lines',
#    'd': 'cusor_vpos',

# Alternate escape sequences, no [
CONQUE_ESCAPE_PLAIN = {
    'D': 'scroll_up',
    'E': 'next_line',
    'H': 'set_tab',
    'M': 'scroll_down'
}
#    'N': 'single_shift_2',
#    'O': 'single_shift_3',
#    '=': 'alternate_keypad',
#    '>': 'numeric_keypad',
#    '7': 'save_cursor',
#    '8': 'restore_cursor',

# Character set escape sequences, with "("
CONQUE_ESCAPE_CHARSET = {
    'A': 'uk',
    'B': 'us',
    '0': 'graphics'
}

# Uber alternate escape sequences, with # or ?
CONQUE_ESCAPE_QUESTION = {
    '1h': 'new_line_mode',
    '3h': '132_cols',
    '4h': 'smooth_scrolling',
    '5h': 'reverse_video',
    '6h': 'relative_origin',
    '7h': 'set_auto_wrap',
    '8h': 'set_auto_repeat',
    '9h': 'set_interlacing_mode',
    '1l': 'set_cursor_key',
    '2l': 'set_vt52',
    '3l': '80_cols',
    '4l': 'set_jump_scrolling',
    '5l': 'normal_video',
    '6l': 'absolute_origin',
    '7l': 'reset_auto_wrap',
    '8l': 'reset_auto_repeat',
    '9l': 'reset_interlacing_mode'
}

CONQUE_ESCAPE_HASH = {
    '8': 'screen_alignment_test'
}
#    '3': 'double_height_top',
#    '4': 'double_height_bottom',
#    '5': 'single_height_single_width',
#    '6': 'single_height_double_width',

CONQUE_GRAPHICS_SET = [
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007,
    0x0008, 0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x000E, 0x000F,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017,
    0x0018, 0x0019, 0x001A, 0x001B, 0x001C, 0x001D, 0x001E, 0x001F,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002A, 0x2192, 0x2190, 0x2191, 0x2193, 0x002F,
    0x2588, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003A, 0x003B, 0x003C, 0x003D, 0x003E, 0x003F,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004A, 0x004B, 0x004C, 0x004D, 0x004E, 0x004F,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005A, 0x005B, 0x005C, 0x005D, 0x005E, 0x00A0,
    0x25C6, 0x2592, 0x2409, 0x240C, 0x240D, 0x240A, 0x00B0, 0x00B1,
    0x2591, 0x240B, 0x2518, 0x2510, 0x250C, 0x2514, 0x253C, 0xF800,
    0xF801, 0x2500, 0xF803, 0xF804, 0x251C, 0x2524, 0x2534, 0x252C,
    0x2502, 0x2264, 0x2265, 0x03C0, 0x2260, 0x00A3, 0x00B7, 0x007F,
    0x0080, 0x0081, 0x0082, 0x0083, 0x0084, 0x0085, 0x0086, 0x0087,
    0x0088, 0x0089, 0x008A, 0x008B, 0x008C, 0x008D, 0x008E, 0x008F,
    0x0090, 0x0091, 0x0092, 0x0093, 0x0094, 0x0095, 0x0096, 0x0097,
    0x0098, 0x0099, 0x009A, 0x009B, 0x009C, 0x009D, 0x009E, 0x009F,
    0x00A0, 0x00A1, 0x00A2, 0x00A3, 0x00A4, 0x00A5, 0x00A6, 0x00A7,
    0x00A8, 0x00A9, 0x00AA, 0x00AB, 0x00AC, 0x00AD, 0x00AE, 0x00AF,
    0x00B0, 0x00B1, 0x00B2, 0x00B3, 0x00B4, 0x00B5, 0x00B6, 0x00B7,
    0x00B8, 0x00B9, 0x00BA, 0x00BB, 0x00BC, 0x00BD, 0x00BE, 0x00BF,
    0x00C0, 0x00C1, 0x00C2, 0x00C3, 0x00C4, 0x00C5, 0x00C6, 0x00C7,
    0x00C8, 0x00C9, 0x00CA, 0x00CB, 0x00CC, 0x00CD, 0x00CE, 0x00CF,
    0x00D0, 0x00D1, 0x00D2, 0x00D3, 0x00D4, 0x00D5, 0x00D6, 0x00D7,
    0x00D8, 0x00D9, 0x00DA, 0x00DB, 0x00DC, 0x00DD, 0x00DE, 0x00DF,
    0x00E0, 0x00E1, 0x00E2, 0x00E3, 0x00E4, 0x00E5, 0x00E6, 0x00E7,
    0x00E8, 0x00E9, 0x00EA, 0x00EB, 0x00EC, 0x00ED, 0x00EE, 0x00EF,
    0x00F0, 0x00F1, 0x00F2, 0x00F3, 0x00F4, 0x00F5, 0x00F6, 0x00F7,
    0x00F8, 0x00F9, 0x00FA, 0x00FB, 0x00FC, 0x00FD, 0x00FE, 0x00FF
]

# Font codes
CONQUE_FONT = {
    0: {'description': 'Normal (default)', 'attributes': {'cterm': 'NONE', 'ctermfg': 'NONE', 'ctermbg': 'NONE', 'gui': 'NONE', 'guifg': 'NONE', 'guibg': 'NONE'}, 'normal': True},
    1: {'description': 'Bold', 'attributes': {'cterm': 'BOLD', 'gui': 'BOLD'}, 'normal': False},
    4: {'description': 'Underlined', 'attributes': {'cterm': 'UNDERLINE', 'gui': 'UNDERLINE'}, 'normal': False},
    5: {'description': 'Blink (appears as Bold)', 'attributes': {'cterm': 'BOLD', 'gui': 'BOLD'}, 'normal': False},
    7: {'description': 'Inverse', 'attributes': {'cterm': 'REVERSE', 'gui': 'REVERSE'}, 'normal': False},
    8: {'description': 'Invisible (hidden)', 'attributes': {'ctermfg': '0', 'ctermbg': '0', 'guifg': '#000000', 'guibg': '#000000'}, 'normal': False},
    22: {'description': 'Normal (neither bold nor faint)', 'attributes': {'cterm': 'NONE', 'gui': 'NONE'}, 'normal': True},
    24: {'description': 'Not underlined', 'attributes': {'cterm': 'NONE', 'gui': 'NONE'}, 'normal': True},
    25: {'description': 'Steady (not blinking)', 'attributes': {'cterm': 'NONE', 'gui': 'NONE'}, 'normal': True},
    27: {'description': 'Positive (not inverse)', 'attributes': {'cterm': 'NONE', 'gui': 'NONE'}, 'normal': True},
    28: {'description': 'Visible (not hidden)', 'attributes': {'ctermfg': 'NONE', 'ctermbg': 'NONE', 'guifg': 'NONE', 'guibg': 'NONE'}, 'normal': True},
    30: {'description': 'Set foreground color to Black', 'attributes': {'ctermfg': '16', 'guifg': '#000000'}, 'normal': False},
    31: {'description': 'Set foreground color to Red', 'attributes': {'ctermfg': '1', 'guifg': '#ff0000'}, 'normal': False},
    32: {'description': 'Set foreground color to Green', 'attributes': {'ctermfg': '2', 'guifg': '#00ff00'}, 'normal': False},
    33: {'description': 'Set foreground color to Yellow', 'attributes': {'ctermfg': '3', 'guifg': '#ffff00'}, 'normal': False},
    34: {'description': 'Set foreground color to Blue', 'attributes': {'ctermfg': '4', 'guifg': '#0000ff'}, 'normal': False},
    35: {'description': 'Set foreground color to Magenta', 'attributes': {'ctermfg': '5', 'guifg': '#990099'}, 'normal': False},
    36: {'description': 'Set foreground color to Cyan', 'attributes': {'ctermfg': '6', 'guifg': '#009999'}, 'normal': False},
    37: {'description': 'Set foreground color to White', 'attributes': {'ctermfg': '7', 'guifg': '#ffffff'}, 'normal': False},
    39: {'description': 'Set foreground color to default (original)', 'attributes': {'ctermfg': 'NONE', 'guifg': 'NONE'}, 'normal': True},
    40: {'description': 'Set background color to Black', 'attributes': {'ctermbg': '16', 'guibg': '#000000'}, 'normal': False},
    41: {'description': 'Set background color to Red', 'attributes': {'ctermbg': '1', 'guibg': '#ff0000'}, 'normal': False},
    42: {'description': 'Set background color to Green', 'attributes': {'ctermbg': '2', 'guibg': '#00ff00'}, 'normal': False},
    43: {'description': 'Set background color to Yellow', 'attributes': {'ctermbg': '3', 'guibg': '#ffff00'}, 'normal': False},
    44: {'description': 'Set background color to Blue', 'attributes': {'ctermbg': '4', 'guibg': '#0000ff'}, 'normal': False},
    45: {'description': 'Set background color to Magenta', 'attributes': {'ctermbg': '5', 'guibg': '#990099'}, 'normal': False},
    46: {'description': 'Set background color to Cyan', 'attributes': {'ctermbg': '6', 'guibg': '#009999'}, 'normal': False},
    47: {'description': 'Set background color to White', 'attributes': {'ctermbg': '7', 'guibg': '#ffffff'}, 'normal': False},
    49: {'description': 'Set background color to default (original).', 'attributes': {'ctermbg': 'NONE', 'guibg': 'NONE'}, 'normal': True},
    90: {'description': 'Set foreground color to Black', 'attributes': {'ctermfg': '8', 'guifg': '#000000'}, 'normal': False},
    91: {'description': 'Set foreground color to Red', 'attributes': {'ctermfg': '9', 'guifg': '#ff0000'}, 'normal': False},
    92: {'description': 'Set foreground color to Green', 'attributes': {'ctermfg': '10', 'guifg': '#00ff00'}, 'normal': False},
    93: {'description': 'Set foreground color to Yellow', 'attributes': {'ctermfg': '11', 'guifg': '#ffff00'}, 'normal': False},
    94: {'description': 'Set foreground color to Blue', 'attributes': {'ctermfg': '12', 'guifg': '#0000ff'}, 'normal': False},
    95: {'description': 'Set foreground color to Magenta', 'attributes': {'ctermfg': '13', 'guifg': '#990099'}, 'normal': False},
    96: {'description': 'Set foreground color to Cyan', 'attributes': {'ctermfg': '14', 'guifg': '#009999'}, 'normal': False},
    97: {'description': 'Set foreground color to White', 'attributes': {'ctermfg': '15', 'guifg': '#ffffff'}, 'normal': False},
    100: {'description': 'Set background color to Black', 'attributes': {'ctermbg': '8', 'guibg': '#000000'}, 'normal': False},
    101: {'description': 'Set background color to Red', 'attributes': {'ctermbg': '9', 'guibg': '#ff0000'}, 'normal': False},
    102: {'description': 'Set background color to Green', 'attributes': {'ctermbg': '10', 'guibg': '#00ff00'}, 'normal': False},
    103: {'description': 'Set background color to Yellow', 'attributes': {'ctermbg': '11', 'guibg': '#ffff00'}, 'normal': False},
    104: {'description': 'Set background color to Blue', 'attributes': {'ctermbg': '12', 'guibg': '#0000ff'}, 'normal': False},
    105: {'description': 'Set background color to Magenta', 'attributes': {'ctermbg': '13', 'guibg': '#990099'}, 'normal': False},
    106: {'description': 'Set background color to Cyan', 'attributes': {'ctermbg': '14', 'guibg': '#009999'}, 'normal': False},
    107: {'description': 'Set background color to White', 'attributes': {'ctermbg': '15', 'guibg': '#ffffff'}, 'normal': False}
}


# regular expression matching (almost) all control sequences
CONQUE_SEQ_REGEX = re.compile("(\x1b\[?\??#?[0-9;]*[a-zA-Z0-9@=>]|\x1b\][0-9];.*?\x07|[\x01-\x0f]|\x1b\([AB0])")
CONQUE_SEQ_REGEX_CTL = re.compile("^[\x01-\x0f]$")
CONQUE_SEQ_REGEX_CSI = re.compile("^\x1b\[")
CONQUE_SEQ_REGEX_TITLE = re.compile("^\x1b\]")
CONQUE_SEQ_REGEX_HASH = re.compile("^\x1b#")
CONQUE_SEQ_REGEX_ESC = re.compile("^\x1b.$")
CONQUE_SEQ_REGEX_CHAR = re.compile("^\x1b[()]")

# match table output
CONQUE_TABLE_OUTPUT = re.compile("^\s*\|\s.*\s\|\s*$|^\s*\+[=+-]+\+\s*$")

# basic terminal colors
CONQUE_COLOR_SEQUENCE = (
    '000', '009', '090', '099', '900', '909', '990', '999',
    '000', '00f', '0f0', '0ff', 'f00', 'f0f', 'ff0', 'fff'
)


# Windows subprocess constants

# shared memory size
CONQUE_SOLE_BUFFER_LENGTH = 1000
CONQUE_SOLE_INPUT_SIZE = 1000
CONQUE_SOLE_STATS_SIZE = 1000
CONQUE_SOLE_COMMANDS_SIZE = 255
CONQUE_SOLE_RESCROLL_SIZE = 255
CONQUE_SOLE_RESIZE_SIZE = 255

# interval of screen redraw
# larger number means less frequent
CONQUE_SOLE_SCREEN_REDRAW = 50

# interval of full buffer redraw
# larger number means less frequent
CONQUE_SOLE_BUFFER_REDRAW = 500

# interval of full output bucket replacement
# larger number means less frequent, 1 = every time
CONQUE_SOLE_MEM_REDRAW = 1000

# maximum number of lines with terminal colors
# ignored if g:ConqueTerm_Color = 2
CONQUE_MAX_SYNTAX_LINES = 200

# windows input splitting on special keys
CONQUE_WIN32_REGEX_VK = re.compile("(\x1b\[[0-9;]+VK)")

# windows attribute string splitting
CONQUE_WIN32_REGEX_ATTR = re.compile("((.)\\2*)", re.DOTALL)

# special key attributes
CONQUE_VK_ATTR_CTRL_PRESSED = u('1024')



########NEW FILE########
__FILENAME__ = conque_screen
# FILE:     autoload/conque_term/conque_screen.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
ConqueScreen is an extention of the vim.current.buffer object

Unix terminal escape sequences usually reference line numbers relative to the 
top of the visible screen. However the visible portion of the Vim buffer
representing the terminal probably doesn't start at the first line of the 
buffer.

The ConqueScreen class allows access to the Vim buffer with screen-relative
line numbering. And handles a few other related tasks, such as setting the
correct cursor position.

  E.g.:
    s = ConqueScreen()
    ...
    s[5] = 'Set 5th line in terminal to this line'
    s.append('Add new line to terminal')
    s[5] = 'Since previous append() command scrolled the terminal down, this is a different line than first cb[5] call'

"""

import vim


class ConqueScreen(object):

    # the buffer
    buffer = None

    # screen and scrolling regions
    screen_top = 1

    # screen width
    screen_width = 80
    screen_height = 80

    # char encoding for vim buffer
    screen_encoding = 'utf-8'


    def __init__(self):
        """ Initialize screen size and character encoding. """

        self.buffer = vim.current.buffer

        # initialize screen size
        self.screen_top = 1
        self.screen_width = vim.current.window.width
        self.screen_height = vim.current.window.height

        # save screen character encoding type
        self.screen_encoding = vim.eval('&fileencoding')


    def __len__(self):
        """ Define the len() function for ConqueScreen objects. """
        return len(self.buffer)


    def __getitem__(self, key):
        """ Define value access for ConqueScreen objects. """
        buffer_line = self.get_real_idx(key)

        # if line is past buffer end, add lines to buffer
        if buffer_line >= len(self.buffer):
            for i in range(len(self.buffer), buffer_line + 1):
                self.append(' ')

        return u(self.buffer[buffer_line], 'utf-8')


    def __setitem__(self, key, value):
        """ Define value assignments for ConqueScreen objects. """
        buffer_line = self.get_real_idx(key)

        if CONQUE_PYTHON_VERSION == 2:
            val = value.encode(self.screen_encoding)
        else:
            # XXX / Vim's python3 interface doesn't accept bytes object
            val = str(value)

        # if line is past end of screen, append
        if buffer_line == len(self.buffer):
            self.buffer.append(val)
        else:
            self.buffer[buffer_line] = val


    def __delitem__(self, key):
        """ Define value deletion for ConqueScreen objects. """
        del self.buffer[self.screen_top + key - 2]


    def append(self, value):
        """ Define value appending for ConqueScreen objects. """

        if len(self.buffer) > self.screen_top + self.screen_height - 1:
            self.buffer[len(self.buffer) - 1] = value
        else:
            self.buffer.append(value)

        if len(self.buffer) > self.screen_top + self.screen_height - 1:
            self.screen_top += 1

        if vim.current.buffer.number == self.buffer.number:
            vim.command('normal! G')


    def insert(self, line, value):
        """ Define value insertion for ConqueScreen objects. """

        l = self.screen_top + line - 2
        try:
            self.buffer.append(value, l)
        except:
            self.buffer[l:l] = [value]


    def get_top(self):
        """ Get the Vim line number representing the top of the visible terminal. """
        return self.screen_top


    def get_real_idx(self, line):
        """ Get the zero index Vim line number corresponding to the provided screen line. """
        return (self.screen_top + line - 2)


    def get_buffer_line(self, line):
        """ Get the Vim line number corresponding to the provided screen line. """
        return (self.screen_top + line - 1)


    def set_screen_width(self, width):
        """ Set the screen width. """
        self.screen_width = width


    def clear(self):
        """ Clear the screen. Does not clear the buffer, just scrolls down past all text. """

        self.screen_width = width
        self.buffer.append(' ')
        vim.command('normal! Gzt')
        self.screen_top = len(self.buffer)


    def set_cursor(self, line, column):
        """ Set cursor position. """

        # figure out line
        buffer_line = self.screen_top + line - 1
        if buffer_line > len(self.buffer):
            for l in range(len(self.buffer) - 1, buffer_line):
                self.buffer.append('')

        # figure out column
        real_column = column
        if len(self.buffer[buffer_line - 1]) < real_column:
            self.buffer[buffer_line - 1] = self.buffer[buffer_line - 1] + ' ' * (real_column - len(self.buffer[buffer_line - 1]))

        if not CONQUE_FAST_MODE:
            # set cursor at byte index of real_column'th character
            vim.command('call cursor(' + str(buffer_line) + ', byteidx(getline(' + str(buffer_line) + '), ' + str(real_column) + '))')

        else:
            # old version
            # python version is occasionally grumpy
            try:
                vim.current.window.cursor = (buffer_line, real_column - 1)
            except:
                vim.command('call cursor(' + str(buffer_line) + ', ' + str(real_column) + ')')


    def reset_size(self, line):
        """ Change screen size """





        # save cursor line number
        buffer_line = self.screen_top + line

        # reset screen size
        self.screen_width = vim.current.window.width
        self.screen_height = vim.current.window.height
        self.screen_top = len(self.buffer) - vim.current.window.height + 1
        if self.screen_top < 1:
            self.screen_top = 1


        # align bottom of buffer to bottom of screen
        vim.command('normal! ' + str(self.screen_height) + 'kG')

        # return new relative line number
        return (buffer_line - self.screen_top)


    def align(self):
        """ align bottom of buffer to bottom of screen """
        vim.command('normal! ' + str(self.screen_height) + 'kG')



########NEW FILE########
__FILENAME__ = conque_sole
# FILE:     autoload/conque_term/conque_sole.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Windows Console Emulator

This is the main interface to the Windows emulator. It reads new output from the background console
and updates the Vim buffer.
"""

import vim


class ConqueSole(Conque):

    window_top = None
    window_bottom = None

    color_cache = {}
    attribute_cache = {}
    color_mode = None
    color_conceals = {}

    buffer = None
    encoding = None

    # counters for periodic rendering
    buffer_redraw_ct = 1
    screen_redraw_ct = 1

    # line offset, shifts output down
    offset = 0


    def open(self):
        """ Start command and initialize this instance

        Arguments:
        command - Command string, e.g. "Powershell.exe"
        options - Dictionary of config options
        python_exe - Path to the python.exe executable. Usually C:\PythonXX\python.exe
        communicator_py - Path to subprocess controller script in user's vimfiles directory
      
        """
        # get arguments
        command = vim.eval('command')
        options = vim.eval('options')
        python_exe = vim.eval('py_exe')
        communicator_py = vim.eval('py_vim')

        # init size
        self.columns = vim.current.window.width
        self.lines = vim.current.window.height
        self.window_top = 0
        self.window_bottom = vim.current.window.height - 1

        # color mode
        self.color_mode = vim.eval('g:ConqueTerm_ColorMode')

        # line offset
        self.offset = int(options['offset'])

        # init color
        self.enable_colors = options['color'] and not CONQUE_FAST_MODE

        # open command
        self.proc = ConqueSoleWrapper()
        self.proc.open(command, self.lines, self.columns, python_exe, communicator_py, options)

        self.buffer = vim.current.buffer
        self.screen_encoding = vim.eval('&fileencoding')


    def read(self, timeout=1, set_cursor=True, return_output=False, update_buffer=True):
        """ Read from console and update Vim buffer. """

        try:
            stats = self.proc.get_stats()

            if not stats:
                return

            # disable screen and buffer redraws in fast mode
            if not CONQUE_FAST_MODE:
                self.buffer_redraw_ct += 1
                self.screen_redraw_ct += 1

            update_top = 0
            update_bottom = 0
            lines = []

            # full buffer redraw, our favorite!
            #if self.buffer_redraw_ct == CONQUE_SOLE_BUFFER_REDRAW:
            #    self.buffer_redraw_ct = 0
            #    update_top = 0
            #    update_bottom = stats['top_offset'] + self.lines
            #    (lines, attributes) = self.proc.read(update_top, update_bottom)
            #    if return_output:
            #        output = self.get_new_output(lines, update_top, stats)
            #    if update_buffer:
            #        for i in range(update_top, update_bottom + 1):
            #            if CONQUE_FAST_MODE:
            #                self.plain_text(i, lines[i], None, stats)
            #            else:
            #                self.plain_text(i, lines[i], attributes[i], stats)

            # full screen redraw
            if stats['cursor_y'] + 1 != self.l or stats['top_offset'] != self.window_top or self.screen_redraw_ct >= CONQUE_SOLE_SCREEN_REDRAW:

                self.screen_redraw_ct = 0
                update_top = self.window_top
                update_bottom = max([stats['top_offset'] + self.lines + 1, stats['cursor_y']])
                (lines, attributes) = self.proc.read(update_top, update_bottom - update_top + 1)
                if return_output:
                    output = self.get_new_output(lines, update_top, stats)
                if update_buffer:
                    for i in range(update_top, update_bottom + 1):
                        if CONQUE_FAST_MODE:
                            self.plain_text(i, lines[i - update_top], None, stats)
                        else:
                            self.plain_text(i, lines[i - update_top], attributes[i - update_top], stats)


            # single line redraw
            else:
                update_top = stats['cursor_y']
                (lines, attributes) = self.proc.read(update_top, 1)
                if return_output:
                    output = self.get_new_output(lines, update_top, stats)
                if update_buffer:
                    if lines[0].rstrip() != u(self.buffer[update_top].rstrip()):
                        if CONQUE_FAST_MODE:
                            self.plain_text(update_top, lines[0], None, stats)
                        else:
                            self.plain_text(update_top, lines[0], attributes[0], stats)


            # reset current position
            self.window_top = stats['top_offset']
            self.l = stats['cursor_y'] + 1
            self.c = stats['cursor_x'] + 1

            # reposition cursor if this seems plausible
            if set_cursor:
                self.set_cursor(self.l, self.c)

            if return_output:
                return output

        except:

            pass


    def get_new_output(self, lines, update_top, stats):
        """ Calculate the "new" output from this read. Fake but useful """

        if not (stats['cursor_y'] + 1 > self.l or (stats['cursor_y'] + 1 == self.l and stats['cursor_x'] + 1 > self.c)):
            return ""






        try:
            num_to_return = stats['cursor_y'] - self.l + 2

            lines = lines[self.l - update_top - 1:]


            new_output = []

            # first line
            new_output.append(lines[0][self.c - 1:].rstrip())

            # the rest
            for i in range(1, num_to_return):
                new_output.append(lines[i].rstrip())

        except:

            pass



        return "\n".join(new_output)


    def plain_text(self, line_nr, text, attributes, stats):
        """ Write plain text to Vim buffer. """





        # handle line offset
        line_nr += self.offset

        self.l = line_nr + 1 

        # remove trailing whitespace
        text = text.rstrip()

        # if we're using concealed text for color, then s- is weird
        if self.color_mode == 'conceal':

            text = self.add_conceal_color(text, attributes, stats, line_nr)


        # deal with character encoding
        if CONQUE_PYTHON_VERSION == 2:
            val = text.encode(self.screen_encoding)
        else:
            # XXX / Vim's python3 interface doesn't accept bytes object
            val = str(text)

        # update vim buffer
        if len(self.buffer) <= line_nr:
            self.buffer.append(val)
        else:
            self.buffer[line_nr] = val

        if self.enable_colors and not self.color_mode == 'conceal' and line_nr > self.l - CONQUE_MAX_SYNTAX_LINES:
            relevant = attributes[0:len(text)]
            if line_nr not in self.attribute_cache or self.attribute_cache[line_nr] != relevant:
                self.do_color(attributes=relevant, stats=stats)
                self.attribute_cache[line_nr] = relevant


    def add_conceal_color(self, text, attributes, stats, line_nr):
        """ Add 'conceal' color strings to output text """

        # stop here if coloration is disabled
        if not self.enable_colors:
            return text

        # if no colors for this line, clear everything out
        if len(attributes) == 0 or attributes == u(chr(stats['default_attribute'])) * len(attributes):
            return text

        new_text = ''
        self.color_conceals[line_nr] = []

        attribute_chunks = CONQUE_WIN32_REGEX_ATTR.findall(attributes)
        offset = 0
        ends = []
        for attr in attribute_chunks:
            attr_num = ord(attr[1])
            ends = []
            if attr_num != stats['default_attribute']:

                color = self.translate_color(attr_num)

                new_text += chr(27) + 'sf' + color['fg_code'] + ';'
                ends.append(chr(27) + 'ef' + color['fg_code'] + ';')
                self.color_conceals[line_nr].append(offset)

                if attr_num > 15:
                    new_text += chr(27) + 'sb' + color['bg_code'] + ';'
                    ends.append(chr(27) + 'eb' + color['bg_code'] + ';')
                    self.color_conceals[line_nr].append(offset)

            new_text += text[offset:offset + len(attr[0])]

            # close color regions
            ends.reverse()
            for i in range(0, len(ends)):
                self.color_conceals[line_nr].append(len(new_text))
                new_text += ends[i]

            offset += len(attr[0])

        return new_text


    def do_color(self, start=0, end=0, attributes='', stats=None):
        """ Convert Windows console attributes into Vim syntax highlighting """

        # if no colors for this line, clear everything out
        if len(attributes) == 0 or attributes == u(chr(stats['default_attribute'])) * len(attributes):
            self.color_changes = {}
            self.apply_color(1, len(attributes), self.l)
            return

        attribute_chunks = CONQUE_WIN32_REGEX_ATTR.findall(attributes)
        offset = 0
        for attr in attribute_chunks:
            attr_num = ord(attr[1])
            if attr_num != stats['default_attribute']:
                self.color_changes = self.translate_color(attr_num)
                self.apply_color(offset + 1, offset + len(attr[0]) + 1, self.l)
            offset += len(attr[0])


    def translate_color(self, attr):
        """ Convert Windows console attributes into RGB colors """

        # check for cached color
        if attr in self.color_cache:
            return self.color_cache[attr]






        # convert attribute integer to bit string
        bit_str = bin(attr)
        bit_str = bit_str.replace('0b', '')

        # slice foreground and background portions of bit string
        fg = bit_str[-4:].rjust(4, '0')
        bg = bit_str[-8:-4].rjust(4, '0')

        # ok, first create foreground #rbg
        red = int(fg[1]) * 204 + int(fg[0]) * int(fg[1]) * 51
        green = int(fg[2]) * 204 + int(fg[0]) * int(fg[2]) * 51
        blue = int(fg[3]) * 204 + int(fg[0]) * int(fg[3]) * 51
        fg_str = "#%02x%02x%02x" % (red, green, blue)
        fg_code = "%02x%02x%02x" % (red, green, blue)
        fg_code = fg_code[0] + fg_code[2] + fg_code[4]

        # ok, first create foreground #rbg
        red = int(bg[1]) * 204 + int(bg[0]) * int(bg[1]) * 51
        green = int(bg[2]) * 204 + int(bg[0]) * int(bg[2]) * 51
        blue = int(bg[3]) * 204 + int(bg[0]) * int(bg[3]) * 51
        bg_str = "#%02x%02x%02x" % (red, green, blue)
        bg_code = "%02x%02x%02x" % (red, green, blue)
        bg_code = bg_code[0] + bg_code[2] + bg_code[4]

        # build value for color_changes

        color = {'guifg': fg_str, 'guibg': bg_str}

        if self.color_mode == 'conceal':
            color['fg_code'] = fg_code
            color['bg_code'] = bg_code

        self.color_cache[attr] = color

        return color


    def write_vk(self, vk_code):
        """ write virtual key code to shared memory using proprietary escape seq """

        self.proc.write_vk(vk_code)


    def update_window_size(self):
        """ Resize underlying console if Vim buffer size has changed """

        if vim.current.window.width != self.columns or vim.current.window.height != self.lines:



            # reset all window size attributes to default
            self.columns = vim.current.window.width
            self.lines = vim.current.window.height
            self.working_columns = vim.current.window.width
            self.working_lines = vim.current.window.height
            self.bottom = vim.current.window.height

            self.proc.window_resize(vim.current.window.height, vim.current.window.width)


    def set_cursor(self, line, column):
        """ Update cursor position in Vim buffer """



        # handle offset
        line += self.offset

        # shift cursor position to handle concealed text
        if self.enable_colors and self.color_mode == 'conceal':
            if line - 1 in self.color_conceals:
                for c in self.color_conceals[line - 1]:
                    if c < column:
                        column += 7
                    else:
                        break



        # figure out line
        buffer_line = line
        if buffer_line > len(self.buffer):
            for l in range(len(self.buffer) - 1, buffer_line):
                self.buffer.append('')

        # figure out column
        real_column = column
        if len(self.buffer[buffer_line - 1]) < real_column:
            self.buffer[buffer_line - 1] = self.buffer[buffer_line - 1] + ' ' * (real_column - len(self.buffer[buffer_line - 1]))

        # python version is occasionally grumpy
        try:
            vim.current.window.cursor = (buffer_line, real_column - 1)
        except:
            vim.command('call cursor(' + str(buffer_line) + ', ' + str(real_column) + ')')


    def idle(self):
        """ go into idle mode """

        self.proc.idle()


    def resume(self):
        """ resume from idle mode """

        self.proc.resume()


    def close(self):
        """ end console subprocess """
        self.proc.close()


    def abort(self):
        """ end subprocess forcefully """
        self.proc.close()


    def get_buffer_line(self, line):
        """ get buffer line """
        return line


# vim:foldmethod=marker

########NEW FILE########
__FILENAME__ = conque_sole_communicator
# FILE:     autoload/conque_term/conque_sole_communicator.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""

ConqueSoleCommunicator

This script will create a new Windows console and start the requested program 
inside of it. This process is launched independently from the parent Vim
program, so it has no access to the vim module.

The main loop in this script reads data from the console and syncs it onto 
blocks of memory shared with the Vim process. In this way the Vim process
and this script can communicate with each other.

"""

import time
import sys

from conque_globals import *
from conque_win32_util import *
from conque_sole_subprocess import *
from conque_sole_shared_memory import *

##############################################################
# only run if this file was run directly

if __name__ == '__main__':

    # attempt to catch ALL exceptions to fend of zombies
    try:

        # simple arg validation

        if len(sys.argv) < 5:

            exit()

        # maximum time this thing reads. 0 means no limit. Only for testing.
        max_loops = 0

        # read interval, in seconds
        sleep_time = 0.01

        # idle read interval, in seconds
        idle_sleep_time = 0.10

        # are we idled?
        is_idle = False

        # mem key
        mem_key = sys.argv[1]

        # console width
        console_width = int(sys.argv[2])

        # console height
        console_height = int(sys.argv[3])

        # code page
        code_page = int(sys.argv[4])

        # code page
        fast_mode = int(sys.argv[5])

        # the actual subprocess to run
        cmd_line = " ".join(sys.argv[6:])


        # width and height
        options = {'LINES': console_height, 'COLUMNS': console_width, 'CODE_PAGE': code_page, 'FAST_MODE': fast_mode}



        # set initial idle status
        shm_command = ConqueSoleSharedMemory(CONQUE_SOLE_COMMANDS_SIZE, 'command', mem_key, serialize=True)
        shm_command.create('write')

        cmd = shm_command.read()
        if cmd:

            if cmd['cmd'] == 'idle':
                is_idle = True
                shm_command.clear()


        ##############################################################
        # Create the subprocess

        proc = ConqueSoleSubprocess()
        res = proc.open(cmd_line, mem_key, options)

        if not res:

            exit()

        ##############################################################
        # main loop!

        loops = 0

        while True:

            # check for idle/resume
            if is_idle or loops % 25 == 0:

                # check process health
                if not proc.is_alive():

                    proc.close()
                    break

                # check for change in buffer focus
                cmd = shm_command.read()
                if cmd:

                    if cmd['cmd'] == 'idle':
                        is_idle = True
                        shm_command.clear()

                    elif cmd['cmd'] == 'resume':
                        is_idle = False
                        shm_command.clear()


            # sleep between loops if moderation is requested
            if sleep_time > 0:
                if is_idle:
                    time.sleep(idle_sleep_time)
                else:
                    time.sleep(sleep_time)

            # write, read, etc
            proc.write()
            proc.read()

            # increment loops, and exit if max has been reached
            loops += 1
            if max_loops and loops >= max_loops:

                break

        ##############################################################
        # all done!



        proc.close()

    # if an exception was thrown, croak
    except:

        proc.close()


# vim:foldmethod=marker

########NEW FILE########
__FILENAME__ = conque_sole_shared_memory
# FILE:     autoload/conque_term/conque_sole_shared_memory.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Wrapper class for shared memory between Windows python processes

Adds a small amount of functionality to the standard mmap module.

"""

import mmap
import sys

# PYTHON VERSION
CONQUE_PYTHON_VERSION = sys.version_info[0]

if CONQUE_PYTHON_VERSION == 2:
    import cPickle as pickle
else:
    import pickle


class ConqueSoleSharedMemory():

    # is the data being stored not fixed length
    fixed_length = False

    # maximum number of bytes per character, for fixed width blocks
    char_width = 1

    # fill memory with this character when clearing and fixed_length is true
    FILL_CHAR = None

    # serialize and unserialize data automatically
    serialize = False

    # size of shared memory, in bytes / chars
    mem_size = None

    # size of shared memory, in bytes / chars
    mem_type = None

    # unique key, so multiple console instances are possible
    mem_key = None

    # mmap instance
    shm = None

    # character encoding, dammit
    encoding = 'utf-8'

    # pickle terminator
    TERMINATOR = None


    def __init__(self, mem_size, mem_type, mem_key, fixed_length=False, fill_char=' ', serialize=False, encoding='utf-8'):
        """ Initialize new shared memory block instance

        Arguments:
        mem_size -- Memory size in characters, depends on encoding argument to calcuate byte size
        mem_type -- Label to identify what will be stored
        mem_key -- Unique, probably random key to identify this block
        fixed_length -- If set to true, assume the data stored will always fill the memory size
        fill_char -- Initialize memory block with this character, only really helpful with fixed_length blocks
        serialize -- Automatically serialize data passed to write. Allows storing non-byte data
        encoding -- Character encoding to use when storing character data

        """
        self.mem_size = mem_size
        self.mem_type = mem_type
        self.mem_key = mem_key
        self.fixed_length = fixed_length
        self.fill_char = fill_char
        self.serialize = serialize
        self.encoding = encoding
        self.TERMINATOR = str(chr(0)).encode(self.encoding)

        if CONQUE_PYTHON_VERSION == 3:
            self.FILL_CHAR = fill_char
        else:
            self.FILL_CHAR = unicode(fill_char)

        if fixed_length and encoding == 'utf-8':
            self.char_width = 4


    def create(self, access='write'):
        """ Create a new block of shared memory using the mmap module. """

        if access == 'write':
            mmap_access = mmap.ACCESS_WRITE
        else:
            mmap_access = mmap.ACCESS_READ

        name = "conque_%s_%s" % (self.mem_type, self.mem_key)

        self.shm = mmap.mmap(0, self.mem_size * self.char_width, name, mmap_access)

        if not self.shm:
            return False
        else:
            return True


    def read(self, chars=1, start=0):
        """ Read data from shared memory.

        If this is a fixed length block, read 'chars' characters from memory. 
        Otherwise read up until the TERMINATOR character (null byte).
        If this memory is serialized, unserialize it automatically.

        """
        # go to start position
        self.shm.seek(start * self.char_width)

        if self.fixed_length:
            chars = chars * self.char_width
        else:
            chars = self.shm.find(self.TERMINATOR)

        if chars == 0:
            return ''

        shm_str = self.shm.read(chars)

        # return unpickled byte object
        if self.serialize:
            return pickle.loads(shm_str)

        # decode byes in python 3
        if CONQUE_PYTHON_VERSION == 3:
            return str(shm_str, self.encoding)

        # encoding
        if self.encoding != 'ascii':
            shm_str = unicode(shm_str, self.encoding)

        return shm_str


    def write(self, text, start=0):
        """ Write data to memory.

        If memory is fixed length, simply write the 'text' characters at 'start' position.
        Otherwise write 'text' characters and append a null character.
        If memory is serializable, do so first.

        """
        # simple scenario, let pickle create bytes
        if self.serialize:
            if CONQUE_PYTHON_VERSION == 3:
                tb = pickle.dumps(text, 0)
            else:
                tb = pickle.dumps(text, 0).encode(self.encoding)

        else:
            tb = text.encode(self.encoding, 'replace')

        # write to memory
        self.shm.seek(start * self.char_width)

        if self.fixed_length:
            self.shm.write(tb)
        else:
            self.shm.write(tb + self.TERMINATOR)


    def clear(self, start=0):
        """ Clear memory block using self.fill_char. """

        self.shm.seek(start)

        if self.fixed_length:
            self.shm.write(str(self.fill_char * self.mem_size * self.char_width).encode(self.encoding))
        else:
            self.shm.write(self.TERMINATOR)


    def close(self):
        """ Close/destroy memory block. """

        self.shm.close()



########NEW FILE########
__FILENAME__ = conque_sole_subprocess
# FILE:     autoload/conque_term/conque_sole_subprocess.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" ConqueSoleSubprocess

Creates a new subprocess with it's own (hidden) console window.

Mirrors console window text onto a block of shared memory (mmap), along with
text attribute data. Also handles translation of text input into the format
Windows console expects.

Sample Usage:

    sh = ConqueSoleSubprocess()
    sh.open("cmd.exe", "unique_str")

    shm_in = ConqueSoleSharedMemory(mem_key = "unique_str", mem_type = "input", ...)
    shm_out = ConqueSoleSharedMemory(mem_key = "unique_str", mem_type = "output", ...)

    output = shm_out.read(...)
    shm_in.write("dir\r")
    output = shm_out.read(...)

"""

import time
import re
import os
import ctypes

from conque_globals import *
from conque_win32_util import *
from conque_sole_shared_memory import *


class ConqueSoleSubprocess():

    # subprocess handle and pid
    handle = None
    pid = None

    # input / output handles
    stdin = None
    stdout = None

    # size of console window
    window_width = 160
    window_height = 40

    # max lines for the console buffer
    buffer_width = 160
    buffer_height = 100

    # keep track of the buffer number at the top of the window
    top = 0
    line_offset = 0

    # buffer height is CONQUE_SOLE_BUFFER_LENGTH * output_blocks
    output_blocks = 1

    # cursor position
    cursor_line = 0
    cursor_col = 0

    # console data, array of lines
    data = []

    # console attribute data, array of array of int
    attributes = []
    attribute_cache = {}

    # default attribute
    default_attribute = 7

    # shared memory objects
    shm_input = None
    shm_output = None
    shm_attributes = None
    shm_stats = None
    shm_command = None
    shm_rescroll = None
    shm_resize = None

    # are we still a valid process?
    is_alive = True

    # running in fast mode
    fast_mode = 0

    # used for periodic execution of screen and memory redrawing
    screen_redraw_ct = 0
    mem_redraw_ct = 0


    def open(self, cmd, mem_key, options={}):
        """ Create subproccess running in hidden console window. """



        self.reset = True

        try:
            # if we're already attached to a console, then unattach
            try:
                ctypes.windll.kernel32.FreeConsole()
            except:
                pass

            # set buffer height
            self.buffer_height = CONQUE_SOLE_BUFFER_LENGTH

            if 'LINES' in options and 'COLUMNS' in options:
                self.window_width = options['COLUMNS']
                self.window_height = options['LINES']
                self.buffer_width = options['COLUMNS']

            # fast mode
            self.fast_mode = options['FAST_MODE']

            # console window options
            si = STARTUPINFO()

            # hide window
            si.dwFlags |= STARTF_USESHOWWINDOW
            si.wShowWindow = SW_HIDE
            #si.wShowWindow = SW_MINIMIZE

            # process options
            flags = NORMAL_PRIORITY_CLASS | CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE

            # created process info
            pi = PROCESS_INFORMATION()



            # create the process!
            res = ctypes.windll.kernel32.CreateProcessW(None, u(cmd), None, None, 0, flags, None, u('.'), ctypes.byref(si), ctypes.byref(pi))





            # process info
            self.pid = pi.dwProcessId
            self.handle = pi.hProcess




            # attach ourselves to the new console
            # console is not immediately available
            for i in range(10):
                time.sleep(0.25)
                try:

                    res = ctypes.windll.kernel32.AttachConsole(self.pid)






                    break
                except:

                    pass

            # get input / output handles
            self.stdout = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            self.stdin = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)

            # set buffer size
            size = COORD(self.buffer_width, self.buffer_height)
            res = ctypes.windll.kernel32.SetConsoleScreenBufferSize(self.stdout, size)







            # prev set size call needs to process
            time.sleep(0.2)

            # set window size
            self.set_window_size(self.window_width, self.window_height)

            # set utf-8 code page
            if 'CODE_PAGE' in options and options['CODE_PAGE'] > 0:
                if ctypes.windll.kernel32.IsValidCodePage(ctypes.c_uint(options['CODE_PAGE'])):

                    ctypes.windll.kernel32.SetConsoleCP(ctypes.c_uint(options['CODE_PAGE']))
                    ctypes.windll.kernel32.SetConsoleOutputCP(ctypes.c_uint(options['CODE_PAGE']))

            # init shared memory
            self.init_shared_memory(mem_key)

            # init read buffers
            self.tc = ctypes.create_unicode_buffer(self.buffer_width)
            self.ac = ctypes.create_unicode_buffer(self.buffer_width)

            return True

        except:

            return False


    def init_shared_memory(self, mem_key):
        """ Create shared memory objects. """

        self.shm_input = ConqueSoleSharedMemory(CONQUE_SOLE_INPUT_SIZE, 'input', mem_key)
        self.shm_input.create('write')
        self.shm_input.clear()

        self.shm_output = ConqueSoleSharedMemory(self.buffer_height * self.buffer_width, 'output', mem_key, True)
        self.shm_output.create('write')
        self.shm_output.clear()

        if not self.fast_mode:
            buf_info = self.get_buffer_info()
            self.shm_attributes = ConqueSoleSharedMemory(self.buffer_height * self.buffer_width, 'attributes', mem_key, True, chr(buf_info.wAttributes), encoding='latin-1')
            self.shm_attributes.create('write')
            self.shm_attributes.clear()

        self.shm_stats = ConqueSoleSharedMemory(CONQUE_SOLE_STATS_SIZE, 'stats', mem_key, serialize=True)
        self.shm_stats.create('write')
        self.shm_stats.clear()

        self.shm_command = ConqueSoleSharedMemory(CONQUE_SOLE_COMMANDS_SIZE, 'command', mem_key, serialize=True)
        self.shm_command.create('write')
        self.shm_command.clear()

        self.shm_resize = ConqueSoleSharedMemory(CONQUE_SOLE_RESIZE_SIZE, 'resize', mem_key, serialize=True)
        self.shm_resize.create('write')
        self.shm_resize.clear()

        self.shm_rescroll = ConqueSoleSharedMemory(CONQUE_SOLE_RESCROLL_SIZE, 'rescroll', mem_key, serialize=True)
        self.shm_rescroll.create('write')
        self.shm_rescroll.clear()

        return True


    def check_commands(self):
        """ Check for and process commands from Vim. """

        cmd = self.shm_command.read()

        if cmd:

            # shut it all down
            if cmd['cmd'] == 'close':

                # clear command
                self.shm_command.clear()

                self.close()
                return

        cmd = self.shm_resize.read()

        if cmd:

            # clear command
            self.shm_resize.clear()

            # resize console
            if cmd['cmd'] == 'resize':



                # only change buffer width if it's larger
                if cmd['data']['width'] > self.buffer_width:
                    self.buffer_width = cmd['data']['width']

                # always change console width and height
                self.window_width = cmd['data']['width']
                self.window_height = cmd['data']['height']

                # reset the console
                buf_info = self.get_buffer_info()
                self.reset_console(buf_info, add_block=False)


    def read(self):
        """ Read from windows console and update shared memory blocks. """

        # no point really
        if self.screen_redraw_ct == 0 and not self.is_alive():
            stats = {'top_offset': 0, 'default_attribute': 0, 'cursor_x': 0, 'cursor_y': self.cursor_line, 'is_alive': 0}

            self.shm_stats.write(stats)
            return

        # check for commands
        self.check_commands()

        # get cursor position
        buf_info = self.get_buffer_info()
        curs_line = buf_info.dwCursorPosition.Y
        curs_col = buf_info.dwCursorPosition.X

        # set update range
        if curs_line != self.cursor_line or self.top != buf_info.srWindow.Top or self.screen_redraw_ct == CONQUE_SOLE_SCREEN_REDRAW:
            self.screen_redraw_ct = 0

            read_start = self.top
            read_end = max([buf_info.srWindow.Bottom + 1, curs_line + 1])
        else:

            read_start = curs_line
            read_end = curs_line + 1




        # vars used in for loop
        coord = COORD(0, 0)
        chars_read = ctypes.c_int(0)

        # read new data
        for i in range(read_start, read_end):

            coord.Y = i

            res = ctypes.windll.kernel32.ReadConsoleOutputCharacterW(self.stdout, ctypes.byref(self.tc), self.buffer_width, coord, ctypes.byref(chars_read))
            if not self.fast_mode:
                ctypes.windll.kernel32.ReadConsoleOutputAttribute(self.stdout, ctypes.byref(self.ac), self.buffer_width, coord, ctypes.byref(chars_read))

            t = self.tc.value
            if not self.fast_mode:
                a = self.ac.value

            # add data
            if i >= len(self.data):
                for j in range(len(self.data), i + 1):
                    self.data.append('')
                    if not self.fast_mode:
                        self.attributes.append('')

            self.data[i] = t
            if not self.fast_mode:
                self.attributes[i] = a




            #for i in range(0, len(t)):




        # write new output to shared memory
        try:
            if self.mem_redraw_ct == CONQUE_SOLE_MEM_REDRAW:
                self.mem_redraw_ct = 0

                for i in range(0, len(self.data)):
                    self.shm_output.write(text=self.data[i], start=self.buffer_width * i)
                    if not self.fast_mode:
                        self.shm_attributes.write(text=self.attributes[i], start=self.buffer_width * i)
            else:

                for i in range(read_start, read_end):
                    self.shm_output.write(text=self.data[i], start=self.buffer_width * i)
                    if not self.fast_mode:
                        self.shm_attributes.write(text=self.attributes[i], start=self.buffer_width * i)
                    #self.shm_output.write(text=''.join(self.data[read_start:read_end]), start=read_start * self.buffer_width)
                    #self.shm_attributes.write(text=''.join(self.attributes[read_start:read_end]), start=read_start * self.buffer_width)

            # write cursor position to shared memory
            stats = {'top_offset': buf_info.srWindow.Top, 'default_attribute': buf_info.wAttributes, 'cursor_x': curs_col, 'cursor_y': curs_line, 'is_alive': 1}
            self.shm_stats.write(stats)

            # adjust screen position
            self.top = buf_info.srWindow.Top
            self.cursor_line = curs_line

            # check for reset
            if curs_line > buf_info.dwSize.Y - 200:
                self.reset_console(buf_info)

        except:




            pass

        # increment redraw counters
        self.screen_redraw_ct += 1
        self.mem_redraw_ct += 1

        return None


    def reset_console(self, buf_info, add_block=True):
        """ Extend the height of the current console if the cursor postion gets within 200 lines of the current size. """

        # sometimes we just want to change the buffer width,
        # in which case no need to add another block
        if add_block:
            self.output_blocks += 1

        # close down old memory
        self.shm_output.close()
        self.shm_output = None

        if not self.fast_mode:
            self.shm_attributes.close()
            self.shm_attributes = None

        # new shared memory key
        mem_key = 'mk' + str(time.time())

        # reallocate memory
        self.shm_output = ConqueSoleSharedMemory(self.buffer_height * self.buffer_width * self.output_blocks, 'output', mem_key, True)
        self.shm_output.create('write')
        self.shm_output.clear()

        # backfill data
        if len(self.data[0]) < self.buffer_width:
            for i in range(0, len(self.data)):
                self.data[i] = self.data[i] + ' ' * (self.buffer_width - len(self.data[i]))
        self.shm_output.write(''.join(self.data))

        if not self.fast_mode:
            self.shm_attributes = ConqueSoleSharedMemory(self.buffer_height * self.buffer_width * self.output_blocks, 'attributes', mem_key, True, chr(buf_info.wAttributes), encoding='latin-1')
            self.shm_attributes.create('write')
            self.shm_attributes.clear()

        # backfill attributes
        if len(self.attributes[0]) < self.buffer_width:
            for i in range(0, len(self.attributes)):
                self.attributes[i] = self.attributes[i] + chr(buf_info.wAttributes) * (self.buffer_width - len(self.attributes[i]))
        if not self.fast_mode:
            self.shm_attributes.write(''.join(self.attributes))

        # notify wrapper of new output block
        self.shm_rescroll.write({'cmd': 'new_output', 'data': {'blocks': self.output_blocks, 'mem_key': mem_key}})

        # set buffer size
        size = COORD(X=self.buffer_width, Y=self.buffer_height * self.output_blocks)

        res = ctypes.windll.kernel32.SetConsoleScreenBufferSize(self.stdout, size)






        # prev set size call needs to process
        time.sleep(0.2)

        # set window size
        self.set_window_size(self.window_width, self.window_height)

        # init read buffers
        self.tc = ctypes.create_unicode_buffer(self.buffer_width)
        self.ac = ctypes.create_unicode_buffer(self.buffer_width)



    def write(self):
        """ Write text to console. 

        This function just parses out special sequences for special key events 
        and passes on the text to the plain or virtual key functions.

        """
        # get input from shared mem
        text = self.shm_input.read()

        # nothing to do here
        if text == u(''):
            return



        # clear input queue
        self.shm_input.clear()

        # split on VK codes
        chunks = CONQUE_WIN32_REGEX_VK.split(text)

        # if len() is one then no vks
        if len(chunks) == 1:
            self.write_plain(text)
            return



        # loop over chunks and delegate
        for t in chunks:

            if t == '':
                continue

            if CONQUE_WIN32_REGEX_VK.match(t):

                self.write_vk(t[2:-2])
            else:
                self.write_plain(t)


    def write_plain(self, text):
        """ Write simple text to subprocess. """

        li = INPUT_RECORD * len(text)
        list_input = li()

        for i in range(0, len(text)):

            # create keyboard input
            ke = KEY_EVENT_RECORD()
            ke.bKeyDown = ctypes.c_byte(1)
            ke.wRepeatCount = ctypes.c_short(1)

            cnum = ord(text[i])

            ke.wVirtualKeyCode = ctypes.windll.user32.VkKeyScanW(cnum)
            ke.wVirtualScanCode = ctypes.c_short(ctypes.windll.user32.MapVirtualKeyW(int(cnum), 0))

            if cnum > 31:
                ke.uChar.UnicodeChar = uchr(cnum)
            elif cnum == 3:
                ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, self.pid)
                ke.uChar.UnicodeChar = uchr(cnum)
                ke.wVirtualKeyCode = ctypes.windll.user32.VkKeyScanW(cnum + 96)
                ke.dwControlKeyState |= LEFT_CTRL_PRESSED
            else:
                ke.uChar.UnicodeChar = uchr(cnum)
                if cnum in CONQUE_WINDOWS_VK_INV:
                    ke.wVirtualKeyCode = cnum
                else:
                    ke.wVirtualKeyCode = ctypes.windll.user32.VkKeyScanW(cnum + 96)
                    ke.dwControlKeyState |= LEFT_CTRL_PRESSED




            kc = INPUT_RECORD(KEY_EVENT)
            kc.Event.KeyEvent = ke
            list_input[i] = kc



        # write input array
        events_written = ctypes.c_int()
        res = ctypes.windll.kernel32.WriteConsoleInputW(self.stdin, list_input, len(text), ctypes.byref(events_written))








    def write_vk(self, vk_code):
        """ Write special characters to console subprocess. """



        code = None
        ctrl_pressed = False

        # this could be made more generic when more attributes
        # other than ctrl_pressed are available
        vk_attributes = vk_code.split(';')

        for attr in vk_attributes:
            if attr == CONQUE_VK_ATTR_CTRL_PRESSED:
                ctrl_pressed = True
            else:
                code = attr

        li = INPUT_RECORD * 1

        # create keyboard input
        ke = KEY_EVENT_RECORD()
        ke.uChar.UnicodeChar = uchr(0)
        ke.wVirtualKeyCode = ctypes.c_short(int(code))
        ke.wVirtualScanCode = ctypes.c_short(ctypes.windll.user32.MapVirtualKeyW(int(code), 0))
        ke.bKeyDown = ctypes.c_byte(1)
        ke.wRepeatCount = ctypes.c_short(1)

        # set enhanced key mode for arrow keys
        if code in CONQUE_WINDOWS_VK_ENHANCED:

            ke.dwControlKeyState |= ENHANCED_KEY

        if ctrl_pressed:
            ke.dwControlKeyState |= LEFT_CTRL_PRESSED

        kc = INPUT_RECORD(KEY_EVENT)
        kc.Event.KeyEvent = ke
        list_input = li(kc)

        # write input array
        events_written = ctypes.c_int()
        res = ctypes.windll.kernel32.WriteConsoleInputW(self.stdin, list_input, 1, ctypes.byref(events_written))







    def close(self):
        """ Close all running subproccesses """

        # record status
        self.is_alive = False
        try:
            stats = {'top_offset': 0, 'default_attribute': 0, 'cursor_x': 0, 'cursor_y': self.cursor_line, 'is_alive': 0}
            self.shm_stats.write(stats)
        except:
            pass

        pid_list = (ctypes.c_int * 10)()
        num = ctypes.windll.kernel32.GetConsoleProcessList(pid_list, 10)



        current_pid = os.getpid()





        # kill subprocess pids
        for pid in pid_list[0:num]:
            if not pid:
                break

            # kill current pid last
            if pid == current_pid:
                continue
            try:
                self.close_pid(pid)
            except:

                pass

        # kill this process
        try:
            self.close_pid(current_pid)
        except:

            pass


    def close_pid(self, pid):
        """ Terminate a single process. """


        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, 0, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)


    def is_alive(self):
        """ Check process health. """

        status = ctypes.windll.kernel32.WaitForSingleObject(self.handle, 1)

        if status == 0:

            self.is_alive = False

        return self.is_alive


    def get_screen_text(self):
        """ Return screen data as string. """

        return "\n".join(self.data)


    def set_window_size(self, width, height):
        """ Change Windows console size. """



        # get current window size object
        window_size = SMALL_RECT(0, 0, 0, 0)

        # buffer info has maximum window size data
        buf_info = self.get_buffer_info()


        # set top left corner
        window_size.Top = 0
        window_size.Left = 0

        # set bottom right corner
        if buf_info.dwMaximumWindowSize.X < width:

            window_size.Right = buf_info.dwMaximumWindowSize.X - 1
        else:
            window_size.Right = width - 1

        if buf_info.dwMaximumWindowSize.Y < height:

            window_size.Bottom = buf_info.dwMaximumWindowSize.Y - 1
        else:
            window_size.Bottom = height - 1



        # set the window size!
        res = ctypes.windll.kernel32.SetConsoleWindowInfo(self.stdout, ctypes.c_bool(True), ctypes.byref(window_size))






        # reread buffer info to get final console max lines
        buf_info = self.get_buffer_info()

        self.window_width = buf_info.srWindow.Right + 1
        self.window_height = buf_info.srWindow.Bottom + 1


    def get_buffer_info(self):
        """ Retrieve commonly-used buffer information. """

        buf_info = CONSOLE_SCREEN_BUFFER_INFO()
        ctypes.windll.kernel32.GetConsoleScreenBufferInfo(self.stdout, ctypes.byref(buf_info))

        return buf_info




########NEW FILE########
__FILENAME__ = conque_sole_wrapper
# FILE:     autoload/conque_term/conque_sole_wrapper.py 
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" 

ConqueSoleSubprocessWrapper

Subprocess wrapper to deal with Windows insanity. Launches console based python,
which in turn launches originally requested command. Communicates with cosole
python through shared memory objects.

"""

import ctypes
import time


class ConqueSoleWrapper():

    # unique key used for shared memory block names
    shm_key = ''

    # process info
    handle = None
    pid = None

    # queue input in this bucket
    bucket = None

    # console size
    lines = 24
    columns = 80

    # shared memory objects
    shm_input = None
    shm_output = None
    shm_attributes = None
    shm_stats = None
    shm_command = None
    shm_rescroll = None
    shm_resize = None

    # console python process
    proc = None


    def open(self, cmd, lines, columns, python_exe='python.exe', communicator_py='conque_sole_communicator.py', options={}):
        """ Launch python.exe subprocess which will in turn launch the user's program.

        Arguments:
        cmd -- The user's command to run. E.g. "Powershell.exe" or "C:\Python27\Scripts\ipython.bat"
        lines, columns -- The size of the console, also the size of the Vim buffer
        python.exe -- The path to the python executable, typically C:\PythonXX\python.exe
        communicator_py -- The path to the subprocess controller script in the user's vimfiles directory
        options -- optional configuration

        """
        self.lines = lines
        self.columns = columns
        self.bucket = u('')

        # create a shm key
        self.shm_key = 'mk' + str(time.time())

        # python command
        cmd_line = '%s "%s" %s %d %d %d %d %s' % (python_exe, communicator_py, self.shm_key, int(self.columns), int(self.lines), int(options['CODE_PAGE']), int(CONQUE_FAST_MODE), cmd)


        # console window attributes
        flags = NORMAL_PRIORITY_CLASS | DETACHED_PROCESS | CREATE_UNICODE_ENVIRONMENT
        si = STARTUPINFO()
        pi = PROCESS_INFORMATION()

        # start the stupid process already
        try:
            res = ctypes.windll.kernel32.CreateProcessW(None, u(cmd_line), None, None, 0, flags, None, u('.'), ctypes.byref(si), ctypes.byref(pi))
        except:

            raise

        # handle
        self.pid = pi.dwProcessId



        # init shared memory objects
        self.init_shared_memory(self.shm_key)


    def read(self, start_line, num_lines, timeout=0):
        """ Read a range of console lines from shared memory. 

        Returns a pair of lists containing the console text and console text attributes.

        """
        # emulate timeout by sleeping timeout time
        if timeout > 0:
            read_timeout = float(timeout) / 1000

            time.sleep(read_timeout)

        output = []
        attributes = []

        # get output
        for i in range(start_line, start_line + num_lines + 1):
            output.append(self.shm_output.read(self.columns, i * self.columns))
            if not CONQUE_FAST_MODE:
                attributes.append(self.shm_attributes.read(self.columns, i * self.columns))

        return (output, attributes)


    def get_stats(self):
        """ Return a dictionary with current console cursor and scrolling information. """

        try:
            rescroll = self.shm_rescroll.read()
            if rescroll != '' and rescroll != None:



                self.shm_rescroll.clear()

                # close down old memory
                self.shm_output.close()
                self.shm_output = None

                if not CONQUE_FAST_MODE:
                    self.shm_attributes.close()
                    self.shm_attributes = None

                # reallocate memory

                self.shm_output = ConqueSoleSharedMemory(CONQUE_SOLE_BUFFER_LENGTH * self.columns * rescroll['data']['blocks'], 'output', rescroll['data']['mem_key'], True)
                self.shm_output.create('read')

                if not CONQUE_FAST_MODE:
                    self.shm_attributes = ConqueSoleSharedMemory(CONQUE_SOLE_BUFFER_LENGTH * self.columns * rescroll['data']['blocks'], 'attributes', rescroll['data']['mem_key'], True, encoding='latin-1')
                    self.shm_attributes.create('read')

            stats_str = self.shm_stats.read()
            if stats_str != '':
                self.stats = stats_str
            else:
                return False
        except:

            return False

        return self.stats


    def is_alive(self):
        """ Get process status. """

        if not self.shm_stats:
            return True

        stats_str = self.shm_stats.read()
        if stats_str:
            return (stats_str['is_alive'])
        else:
            return True


    def write(self, text):
        """ Write input to shared memory. """

        self.bucket += text

        istr = self.shm_input.read()

        if istr == '':

            self.shm_input.write(self.bucket[:500])
            self.bucket = self.bucket[500:]


    def write_vk(self, vk_code):
        """ Write virtual key code to shared memory using proprietary escape sequences. """

        seq = u("\x1b[") + u(str(vk_code)) + u("VK")
        self.write(seq)


    def idle(self):
        """ Write idle command to shared memory block, so subprocess controller can hibernate. """


        self.shm_command.write({'cmd': 'idle', 'data': {}})


    def resume(self):
        """ Write resume command to shared memory block, so subprocess controller can wake up. """

        self.shm_command.write({'cmd': 'resume', 'data': {}})


    def close(self):
        """ Shut it all down. """

        self.shm_command.write({'cmd': 'close', 'data': {}})
        time.sleep(0.2)


    def window_resize(self, lines, columns):
        """ Resize console window. """

        self.lines = lines

        # we don't shrink buffer width
        if columns > self.columns:
            self.columns = columns

        self.shm_resize.write({'cmd': 'resize', 'data': {'width': columns, 'height': lines}})


    def init_shared_memory(self, mem_key):
        """ Create shared memory objects. """

        self.shm_input = ConqueSoleSharedMemory(CONQUE_SOLE_INPUT_SIZE, 'input', mem_key)
        self.shm_input.create('write')
        self.shm_input.clear()

        self.shm_output = ConqueSoleSharedMemory(CONQUE_SOLE_BUFFER_LENGTH * self.columns, 'output', mem_key, True)
        self.shm_output.create('write')

        if not CONQUE_FAST_MODE:
            self.shm_attributes = ConqueSoleSharedMemory(CONQUE_SOLE_BUFFER_LENGTH * self.columns, 'attributes', mem_key, True, encoding='latin-1')
            self.shm_attributes.create('write')

        self.shm_stats = ConqueSoleSharedMemory(CONQUE_SOLE_STATS_SIZE, 'stats', mem_key, serialize=True)
        self.shm_stats.create('write')
        self.shm_stats.clear()

        self.shm_command = ConqueSoleSharedMemory(CONQUE_SOLE_COMMANDS_SIZE, 'command', mem_key, serialize=True)
        self.shm_command.create('write')
        self.shm_command.clear()

        self.shm_resize = ConqueSoleSharedMemory(CONQUE_SOLE_RESIZE_SIZE, 'resize', mem_key, serialize=True)
        self.shm_resize.create('write')
        self.shm_resize.clear()

        self.shm_rescroll = ConqueSoleSharedMemory(CONQUE_SOLE_RESCROLL_SIZE, 'rescroll', mem_key, serialize=True)
        self.shm_rescroll.create('write')
        self.shm_rescroll.clear()

        return True


# vim:foldmethod=marker

########NEW FILE########
__FILENAME__ = conque_subprocess
# FILE:     autoload/conque_term/conque_subprocess.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
ConqueSubprocess

Create and interact with a subprocess through a pty.

Usage:

    p = ConqueSubprocess()
    p.open('bash', {'TERM':'vt100'})
    output = p.read()
    p.write('cd ~/vim' + "\r")
    p.write('ls -lha' + "\r")
    output += p.read(timeout = 500)
    p.close()
"""

import os
import signal
import pty
import tty
import select
import fcntl
import termios
import struct
import shlex


class ConqueSubprocess:

    # process id
    pid = 0

    # stdout+stderr file descriptor
    fd = None


    def open(self, command, env={}):
        """ Create subprocess using forkpty() """

        # parse command
        command_arr = shlex.split(command)
        executable = command_arr[0]
        args = command_arr

        # try to fork a new pty
        try:
            self.pid, self.fd = pty.fork()

        except:

            return False

        # child proc, replace with command after altering terminal attributes
        if self.pid == 0:

            # set requested environment variables
            for k in env.keys():
                os.environ[k] = env[k]

            # set tty attributes
            try:
                attrs = tty.tcgetattr(1)
                attrs[0] = attrs[0] ^ tty.IGNBRK
                attrs[0] = attrs[0] | tty.BRKINT | tty.IXANY | tty.IMAXBEL
                attrs[2] = attrs[2] | tty.HUPCL
                attrs[3] = attrs[3] | tty.ICANON | tty.ECHO | tty.ISIG | tty.ECHOKE
                attrs[6][tty.VMIN] = 1
                attrs[6][tty.VTIME] = 0
                tty.tcsetattr(1, tty.TCSANOW, attrs)
            except:

                pass

            # replace this process with the subprocess
            os.execvp(executable, args)

        # else master, do nothing
        else:
            pass


    def read(self, timeout=1):
        """ Read from subprocess and return new output """

        output = ''
        read_timeout = float(timeout) / 1000
        read_ct = 0

        try:
            # read from fd until no more output
            while 1:
                s_read, s_write, s_error = select.select([self.fd], [], [], read_timeout)

                lines = ''
                for s_fd in s_read:
                    try:
                        # increase read buffer so huge reads don't slow down
                        if read_ct < 10:
                            lines = os.read(self.fd, 32)
                        elif read_ct < 50:
                            lines = os.read(self.fd, 512)
                        else:
                            lines = os.read(self.fd, 2048)
                        read_ct += 1
                    except:
                        pass
                    output = output + lines.decode('utf-8')

                if lines == '' or read_ct > 100:
                    break
        except:

            pass

        return output


    def write(self, input):
        """ Write new input to subprocess """

        try:
            if CONQUE_PYTHON_VERSION == 2:
                os.write(self.fd, input.encode('utf-8', 'ignore'))
            else:
                os.write(self.fd, bytes(input, 'utf-8'))
        except:

            pass


    def signal(self, signum):
        """ signal process """

        try:
            os.kill(self.pid, signum)
        except:
            pass


    def close(self):
        """ close process with sigterm signal """

        self.signal(15)


    def is_alive(self):
        """ get process status """

        p_status = True
        try:
            if os.waitpid(self.pid, os.WNOHANG)[0]:
                p_status = False
        except:
            p_status = False

        return p_status


    def window_resize(self, lines, columns):
        """ update window size in kernel, then send SIGWINCH to fg process """

        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
            os.kill(self.pid, signal.SIGWINCH)
        except:
            pass


# vim:foldmethod=marker

########NEW FILE########
__FILENAME__ = conque_win32_util
# FILE:     autoload/conque_term/conque_win32_util.py
# AUTHOR:   Nico Raffo <nicoraffo@gmail.com>
# WEBSITE:  http://conque.googlecode.com
# MODIFIED: 2011-09-02
# VERSION:  2.3, for Vim 7.0
# LICENSE:
# Conque - Vim terminal/console emulator
# Copyright (C) 2009-2011 Nico Raffo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" Python constants and structures used for ctypes interaction. """

from ctypes import *

# Constants

# create process flag constants

CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_DEFAULT_ERROR_MODE = 0x04000000
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
CREATE_PROTECTED_PROCESS = 0x00040000
CREATE_PRESERVE_CODE_AUTHZ_LEVEL = 0x02000000
CREATE_SEPARATE_WOW_VDM = 0x00000800
CREATE_SHARED_WOW_VDM = 0x00001000
CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400


DETACHED_PROCESS = 0x00000008
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
INHERIT_PARENT_AFFINITY = 0x00010000


# process priority constants 

ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
HIGH_PRIORITY_CLASS = 0x00000080
IDLE_PRIORITY_CLASS = 0x00000040
NORMAL_PRIORITY_CLASS = 0x00000020
REALTIME_PRIORITY_CLASS = 0x00000100


# startup info constants 

STARTF_FORCEONFEEDBACK = 0x00000040
STARTF_FORCEOFFFEEDBACK = 0x00000080
STARTF_PREVENTPINNING = 0x00002000
STARTF_RUNFULLSCREEN = 0x00000020
STARTF_TITLEISAPPID = 0x00001000
STARTF_TITLEISLINKNAME = 0x00000800
STARTF_USECOUNTCHARS = 0x00000008
STARTF_USEFILLATTRIBUTE = 0x00000010
STARTF_USEHOTKEY = 0x00000200
STARTF_USEPOSITION = 0x00000004
STARTF_USESHOWWINDOW = 0x00000001
STARTF_USESIZE = 0x00000002
STARTF_USESTDHANDLES = 0x00000100


# show window constants 

SW_FORCEMINIMIZE = 11
SW_HIDE = 0
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_RESTORE = 9
SW_SHOW = 5
SW_SHOWDEFAULT = 10
SW_SHOWMAXIMIZED = 3
SW_SHOWMINIMIZED = 2
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_SHOWNOACTIVATE = 4
SW_SHOWNORMAL = 1


# input event types 

FOCUS_EVENT = 0x0010
KEY_EVENT = 0x0001
MENU_EVENT = 0x0008
MOUSE_EVENT = 0x0002
WINDOW_BUFFER_SIZE_EVENT = 0x0004


# key event modifiers 

CAPSLOCK_ON = 0x0080
ENHANCED_KEY = 0x0100
LEFT_ALT_PRESSED = 0x0002
LEFT_CTRL_PRESSED = 0x0008
NUMLOCK_ON = 0x0020
RIGHT_ALT_PRESSED = 0x0001
RIGHT_CTRL_PRESSED = 0x0004
SCROLLLOCK_ON = 0x0040
SHIFT_PRESSED = 0x0010


# process access 

PROCESS_CREATE_PROCESS = 0x0080
PROCESS_CREATE_THREAD = 0x0002
PROCESS_DUP_HANDLE = 0x0040
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_INFORMATION = 0x0200
PROCESS_SET_QUOTA = 0x0100
PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_TERMINATE = 0x0001
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020


# input / output handles 

STD_INPUT_HANDLE = c_ulong(-10)
STD_OUTPUT_HANDLE = c_ulong(-11)
STD_ERROR_HANDLE = c_ulong(-12)


CONQUE_WINDOWS_VK = {
    'VK_LBUTTON': 0x0001,
    'VK_RBUTTON': 0x0002,
    'VK_CANCEL': 0x0003,
    'VK_BACK': 0x0008,
    'VK_TAB': 0x0009,
    'VK_CLEAR': 0x000C,
    'VK_RETURN': 0x0D,
    'VK_SHIFT': 0x10,
    'VK_CONTROL': 0x11,
    'VK_MENU': 0x12,
    'VK_PAUSE': 0x0013,
    'VK_CAPITAL': 0x0014,
    'VK_ESCAPE': 0x001B,
    'VK_SPACE': 0x0020,
    'VK_PRIOR': 0x0021,
    'VK_NEXT': 0x0022,
    'VK_END': 0x0023,
    'VK_HOME': 0x0024,
    'VK_LEFT': 0x0025,
    'VK_UP': 0x0026,
    'VK_RIGHT': 0x0027,
    'VK_DOWN': 0x0028,
    'VK_SELECT': 0x0029,
    'VK_PRINT': 0x002A,
    'VK_EXECUTE': 0x002B,
    'VK_SNAPSHOT': 0x002C,
    'VK_INSERT': 0x002D,
    'VK_DELETE': 0x002E,
    'VK_HELP': 0x002F,
    'VK_0': 0x0030,
    'VK_1': 0x0031,
    'VK_2': 0x0032,
    'VK_3': 0x0033,
    'VK_4': 0x0034,
    'VK_5': 0x0035,
    'VK_6': 0x0036,
    'VK_7': 0x0037,
    'VK_8': 0x0038,
    'VK_9': 0x0039,
    'VK_A': 0x0041,
    'VK_B': 0x0042,
    'VK_C': 0x0043,
    'VK_D': 0x0044,
    'VK_E': 0x0045,
    'VK_F': 0x0046,
    'VK_G': 0x0047,
    'VK_H': 0x0048,
    'VK_I': 0x0049,
    'VK_J': 0x004A,
    'VK_K': 0x004B,
    'VK_L': 0x004C,
    'VK_M': 0x004D,
    'VK_N': 0x004E,
    'VK_O': 0x004F,
    'VK_P': 0x0050,
    'VK_Q': 0x0051,
    'VK_R': 0x0052,
    'VK_S': 0x0053,
    'VK_T': 0x0054,
    'VK_U': 0x0055,
    'VK_V': 0x0056,
    'VK_W': 0x0057,
    'VK_X': 0x0058,
    'VK_Y': 0x0059,
    'VK_Z': 0x005A,
    'VK_LWIN': 0x005B,
    'VK_RWIN': 0x005C,
    'VK_APPS': 0x005D,
    'VK_SLEEP': 0x005F,
    'VK_NUMPAD0': 0x0060,
    'VK_NUMPAD1': 0x0061,
    'VK_NUMPAD2': 0x0062,
    'VK_NUMPAD3': 0x0063,
    'VK_NUMPAD4': 0x0064,
    'VK_NUMPAD5': 0x0065,
    'VK_NUMPAD6': 0x0066,
    'VK_NUMPAD7': 0x0067,
    'VK_NUMPAD8': 0x0068,
    'VK_MULTIPLY': 0x006A,
    'VK_ADD': 0x006B,
    'VK_SEPARATOR': 0x006C,
    'VK_SUBTRACT': 0x006D,
    'VK_DECIMAL': 0x006E,
    'VK_DIVIDE': 0x006F,
    'VK_F1': 0x0070,
    'VK_F2': 0x0071,
    'VK_F3': 0x0072,
    'VK_F4': 0x0073,
    'VK_F5': 0x0074,
    'VK_F6': 0x0075,
    'VK_F7': 0x0076,
    'VK_F8': 0x0077,
    'VK_F9': 0x0078,
    'VK_F10': 0x0079,
    'VK_F11': 0x007A,
    'VK_F12': 0x007B,
    'VK_F13': 0x007C,
    'VK_F14': 0x007D,
    'VK_F15': 0x007E,
    'VK_F16': 0x007F,
    'VK_F17': 0x0080,
    'VK_F18': 0x0081,
    'VK_F19': 0x0082,
    'VK_F20': 0x0083,
    'VK_F21': 0x0084,
    'VK_F22': 0x0085,
    'VK_F23': 0x0086,
    'VK_F24': 0x0087,
    'VK_NUMLOCK': 0x0090,
    'VK_SCROLL': 0x0091,
    'VK_LSHIFT': 0x00A0,
    'VK_RSHIFT': 0x00A1,
    'VK_LCONTROL': 0x00A2,
    'VK_RCONTROL': 0x00A3,
    'VK_LMENU': 0x00A4,
    'VK_RMENU': 0x00A5
}

CONQUE_WINDOWS_VK_INV = dict([v, k] for k, v in CONQUE_WINDOWS_VK.items())

CONQUE_WINDOWS_VK_ENHANCED = {
    str(int(CONQUE_WINDOWS_VK['VK_UP'])): 1,
    str(int(CONQUE_WINDOWS_VK['VK_DOWN'])): 1,
    str(int(CONQUE_WINDOWS_VK['VK_LEFT'])): 1,
    str(int(CONQUE_WINDOWS_VK['VK_RIGHT'])): 1,
    str(int(CONQUE_WINDOWS_VK['VK_HOME'])): 1,
    str(int(CONQUE_WINDOWS_VK['VK_END'])): 1
}


# structures used for CreateProcess

# Odd types 

LPBYTE = POINTER(c_ubyte)
LPTSTR = POINTER(c_char)


class STARTUPINFO(Structure):
    _fields_ = [("cb",            c_ulong),
                ("lpReserved",    LPTSTR),
                ("lpDesktop",     LPTSTR),
                ("lpTitle",       LPTSTR),
                ("dwX",           c_ulong),
                ("dwY",           c_ulong),
                ("dwXSize",       c_ulong),
                ("dwYSize",       c_ulong),
                ("dwXCountChars", c_ulong),
                ("dwYCountChars", c_ulong),
                ("dwFillAttribute", c_ulong),
                ("dwFlags",       c_ulong),
                ("wShowWindow",   c_short),
                ("cbReserved2",   c_short),
                ("lpReserved2",   LPBYTE),
                ("hStdInput",     c_void_p),
                ("hStdOutput",    c_void_p),
                ("hStdError",     c_void_p),]

    def to_str(self):
        return ''


class PROCESS_INFORMATION(Structure):
    _fields_ = [("hProcess",    c_void_p),
                ("hThread",     c_void_p),
                ("dwProcessId", c_ulong),
                ("dwThreadId",  c_ulong),]

    def to_str(self):
        return ''


class MEMORY_BASIC_INFORMATION(Structure):
    _fields_ = [("BaseAddress",       c_void_p),
                ("AllocationBase",    c_void_p),
                ("AllocationProtect", c_ulong),
                ("RegionSize",        c_ulong),
                ("State",             c_ulong),
                ("Protect",           c_ulong),
                ("Type",              c_ulong),]

    def to_str(self):
        return ''


class SECURITY_ATTRIBUTES(Structure):
    _fields_ = [("Length", c_ulong),
                ("SecDescriptor", c_void_p),
                ("InheritHandle", c_bool)]

    def to_str(self):
        return ''


class COORD(Structure):
    _fields_ = [("X", c_short),
                ("Y", c_short)]

    def to_str(self):
        return ''


class SMALL_RECT(Structure):
    _fields_ = [("Left", c_short),
                ("Top", c_short),
                ("Right", c_short),
                ("Bottom", c_short)]

    def to_str(self):
        return ''


class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", c_short),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]

    def to_str(self):
        return ''


class CHAR_UNION(Union):
    _fields_ = [("UnicodeChar", c_wchar),
                ("AsciiChar", c_char)]

    def to_str(self):
        return ''


class CHAR_INFO(Structure):
    _fields_ = [("Char", CHAR_UNION),
                ("Attributes", c_short)]

    def to_str(self):
        return ''


class KEY_EVENT_RECORD(Structure):
    _fields_ = [("bKeyDown", c_byte),
                ("pad2", c_byte),
                ('pad1', c_short),
                ("wRepeatCount", c_short),
                ("wVirtualKeyCode", c_short),
                ("wVirtualScanCode", c_short),
                ("uChar", CHAR_UNION),
                ("dwControlKeyState", c_int)]

    def to_str(self):
        return ''


class MOUSE_EVENT_RECORD(Structure):
    _fields_ = [("dwMousePosition", COORD),
                ("dwButtonState", c_int),
                ("dwControlKeyState", c_int),
                ("dwEventFlags", c_int)]

    def to_str(self):
        return ''


class WINDOW_BUFFER_SIZE_RECORD(Structure):
    _fields_ = [("dwSize", COORD)]

    def to_str(self):
        return ''


class MENU_EVENT_RECORD(Structure):
    _fields_ = [("dwCommandId", c_uint)]

    def to_str(self):
        return ''


class FOCUS_EVENT_RECORD(Structure):
    _fields_ = [("bSetFocus", c_byte)]

    def to_str(self):
        return ''


class INPUT_UNION(Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD),
                ("MouseEvent", MOUSE_EVENT_RECORD),
                ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
                ("MenuEvent", MENU_EVENT_RECORD),
                ("FocusEvent", FOCUS_EVENT_RECORD)]

    def to_str(self):
        return ''


class INPUT_RECORD(Structure):
    _fields_ = [("EventType", c_short),
                ("Event", INPUT_UNION)]

    def to_str(self):
        return ''



########NEW FILE########
__FILENAME__ = sparkup
#!/usr/bin/env python
# -*- coding: utf-8 -*-
version = "0.1.3"

import os
import fileinput
import getopt
import sys
import re

# =============================================================================== 

class Dialect:
    shortcuts = {}
    synonyms = {}
    required = {}
    short_tags = ()

class HtmlDialect(Dialect):
    shortcuts = {
        'cc:ie': {
            'opening_tag': '<!--[if IE]>',
            'closing_tag': '<![endif]-->'},
        'cc:ie6': {
            'opening_tag': '<!--[if lte IE 6]>',
            'closing_tag': '<![endif]-->'},
        'cc:ie7': {
            'opening_tag': '<!--[if lte IE 7]>',
            'closing_tag': '<![endif]-->'},
        'cc:noie': {
            'opening_tag': '<!--[if !IE]><!-->',
            'closing_tag': '<!--<![endif]-->'},
        'html:4t': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n' +
                '<html lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'html:4s': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n' +
                '<html lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'html:xt': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n' +
                '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'html:xs': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n' +
                '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'html:xxs': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' +
                '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'html:5': {
            'expand': True,
            'opening_tag':
                '<!DOCTYPE html>\n' +
                '<html lang="en">\n' +
                '<head>\n' +
                '    ' + '<meta charset="UTF-8" />\n' +
                '    ' + '<title></title>\n' + 
                '</head>\n' +
                '<body>',
            'closing_tag':
                '</body>\n' +
                '</html>'},
        'input:button': {
            'name': 'input',
            'attributes': { 'class': 'button', 'type': 'button', 'name': '', 'value': '' }
            },
        'input:password': {
            'name': 'input',
            'attributes': { 'class': 'text password', 'type': 'password', 'name': '', 'value': '' }
            },
        'input:radio': {
            'name': 'input',
            'attributes': { 'class': 'radio', 'type': 'radio', 'name': '', 'value': '' }
            },
        'input:checkbox': {
            'name': 'input',
            'attributes': { 'class': 'checkbox', 'type': 'checkbox', 'name': '', 'value': '' }
            },
        'input:file': {
            'name': 'input',
            'attributes': { 'class': 'file', 'type': 'file', 'name': '', 'value': '' }
            },
        'input:text': {
            'name': 'input',
            'attributes': { 'class': 'text', 'type': 'text', 'name': '', 'value': '' }
            },
        'input:submit': {
            'name': 'input',
            'attributes': { 'class': 'submit', 'type': 'submit', 'value': '' }
            },
        'input:hidden': {
            'name': 'input',
            'attributes': { 'type': 'hidden', 'name': '', 'value': '' }
            },
        'script:src': {
            'name': 'script',
            'attributes': { 'src': '' }
            },
        'script:jquery': {
            'name': 'script',
            'attributes': { 'src': 'http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js' }
            },
        'script:jsapi': {
            'name': 'script',
            'attributes': { 'src': 'http://www.google.com/jsapi' }
            },
        'script:jsapix': {
            'name': 'script',
            'text': '\n    google.load("jquery", "1.3.2");\n    google.setOnLoadCallback(function() {\n        \n    });\n'
            },
        'link:css': {
            'name': 'link',
            'attributes': { 'rel': 'stylesheet', 'type': 'text/css', 'href': '', 'media': 'all' },
            },
        'link:print': {
            'name': 'link',
            'attributes': { 'rel': 'stylesheet', 'type': 'text/css', 'href': '', 'media': 'print' },
            },
        'link:favicon': {
            'name': 'link',
            'attributes': { 'rel': 'shortcut icon', 'type': 'image/x-icon', 'href': '' },
            },
        'link:touch': {
            'name': 'link',
            'attributes': { 'rel': 'apple-touch-icon', 'href': '' },
            },
        'link:rss': {
            'name': 'link',
            'attributes': { 'rel': 'alternate', 'type': 'application/rss+xml', 'title': 'RSS', 'href': '' },
            },
        'link:atom': {
            'name': 'link',
            'attributes': { 'rel': 'alternate', 'type': 'application/atom+xml', 'title': 'Atom', 'href': '' },
            },
        'meta:ie7': {
            'name': 'meta',
            'attributes': { 'http-equiv': 'X-UA-Compatible', 'content': 'IE=7' },
            },
        'meta:ie8': {
            'name': 'meta',
            'attributes': { 'http-equiv': 'X-UA-Compatible', 'content': 'IE=8' },
            },
        'form:get': {
            'name': 'form',
            'attributes': { 'method': 'get' },
            },
        'form:g': {
            'name': 'form',
            'attributes': { 'method': 'get' },
            },
        'form:post': {
            'name': 'form',
            'attributes': { 'method': 'post' },
            },
        'form:p': {
            'name': 'form',
            'attributes': { 'method': 'post' },
            },
        }
    synonyms = {
        'checkbox': 'input:checkbox',
        'check': 'input:checkbox',
        'input:c': 'input:checkbox',
        'button': 'input:button',
        'input:b': 'input:button',
        'input:h': 'input:hidden',
        'hidden': 'input:hidden',
        'submit': 'input:submit',
        'input:s': 'input:submit',
        'radio': 'input:radio',
        'input:r': 'input:radio',
        'text': 'input:text',
        'passwd': 'input:password',
        'password': 'input:password',
        'pw': 'input:password',
        'input:t': 'input:text',
        'linkcss': 'link:css',
        'scriptsrc': 'script:src',
        'jquery': 'script:jquery',
        'jsapi': 'script:jsapi',
        'html5': 'html:5',
        'html4': 'html:4s',
        'html4s': 'html:4s',
        'html4t': 'html:4t',
        'xhtml': 'html:xxs',
        'xhtmlt': 'html:xt',
        'xhtmls': 'html:xs',
        'xhtml11': 'html:xxs',
        'opt': 'option',
        'st': 'strong',
        'css': 'style',
        'csss': 'link:css',
        'css:src': 'link:css',
        'csssrc': 'link:css',
        'js': 'script',
        'jss': 'script:src',
        'js:src': 'script:src',
        'jssrc': 'script:src',
        }
    short_tags = (
        'area', 'base', 'basefont', 'br', 'embed', 'hr', \
        'input', 'img', 'link', 'param', 'meta')
    required = {
        'a':      {'href':''},
        'base':   {'href':''},
        'abbr':   {'title': ''},
        'acronym':{'title': ''},
        'bdo':    {'dir': ''},
        'link':   {'rel': 'stylesheet', 'href': ''},
        'style':  {'type': 'text/css'},
        'script': {'type': 'text/javascript'},
        'img':    {'src':'', 'alt':''},
        'iframe': {'src': '', 'frameborder': '0'},
        'embed':  {'src': '', 'type': ''},
        'object': {'data': '', 'type': ''},
        'param':  {'name': '', 'value': ''},
        'form':   {'action': '', 'method': 'post'},
        'table':  {'cellspacing': '0'},
        'input':  {'type': '', 'name': '', 'value': ''},
        'base':   {'href': ''},
        'area':   {'shape': '', 'coords': '', 'href': '', 'alt': ''},
        'select': {'name': ''},
        'option': {'value': ''},
        'textarea':{'name': ''},
        'meta':   {'content': ''},
    }

class Parser:
    """The parser.
    """

    # Constructor
    # --------------------------------------------------------------------------- 

    def __init__(self, options=None, str='', dialect=HtmlDialect()):
        """Constructor.
        """

        self.tokens = []
        self.str = str
        self.options = options
        self.dialect = dialect
        self.root = Element(parser=self)
        self.caret = []
        self.caret.append(self.root)
        self._last = []

    # Methods 
    # --------------------------------------------------------------------------- 

    def load_string(self, str):
        """Loads a string to parse.
        """

        self.str = str
        self._tokenize()
        self._parse()

    def render(self):
        """Renders.
        Called by [[Router]].
        """

        # Get the initial render of the root node
        output = self.root.render()

        # Indent by whatever the input is indented with
        indent = re.findall("^[\r\n]*(\s*)", self.str)[0]
        output = indent + output.replace("\n", "\n" + indent)

        # Strip newline if not needed
        if self.options.has("no-last-newline") \
            or self.prefix or self.suffix:
            output = re.sub(r'\n\s*$', '', output)

        # TextMate mode
        if self.options.has("textmate"):
            output = self._textmatify(output)

        return output

    # Protected methods 
    # --------------------------------------------------------------------------- 

    def _textmatify(self, output):
        """Returns a version of the output with TextMate placeholders in it.
        """

        matches = re.findall(r'(></)|("")|(\n\s+)\n|(.|\s)', output)
        output = ''
        n = 1
        for i in matches:
            if i[0]:
                output += '>$%i</' % n
                n += 1
            elif i[1]:
                output += '"$%i"' % n
                n += 1
            elif i[2]:
                output += i[2] + '$%i\n' % n
                n += 1
            elif i[3]:
                output += i[3]
        output += "$0"
        return output

    def _tokenize(self):
        """Tokenizes.
        Initializes [[self.tokens]].
        """

        str = self.str.strip()

        # Find prefix/suffix
        while True:
            match = re.match(r"^(\s*<[^>]+>\s*)", str)
            if match is None: break
            if self.prefix is None: self.prefix = ''
            self.prefix += match.group(0)
            str = str[len(match.group(0)):]

        while True:
            match = re.findall(r"(\s*<[^>]+>[\s\n\r]*)$", str)
            if not match: break
            if self.suffix is None: self.suffix = ''
            self.suffix = match[0] + self.suffix
            str = str[:-len(match[0])]

        # Split by the element separators
        for token in re.split('(<|>|\+(?!\\s*\+|$))', str):
            if token.strip() != '':
                self.tokens.append(Token(token, parser=self))

    def _parse(self):
        """Takes the tokens and does its thing.
        Populates [[self.root]].
        """

        # Carry it over to the root node.
        if self.prefix or self.suffix:
            self.root.prefix = self.prefix
            self.root.suffix = self.suffix
            self.root.depth += 1

        for token in self.tokens:
            if token.type == Token.ELEMENT:
                # Reset the "last elements added" list. We will
                # repopulate this with the new elements added now.
                self._last[:] = []

                # Create [[Element]]s from a [[Token]].
                # They will be created as many as the multiplier specifies,
                # multiplied by how many carets we have
                count = 0
                for caret in self.caret:
                    local_count = 0
                    for i in range(token.multiplier):
                        count += 1
                        local_count += 1
                        new = Element(token, caret,
                                count = count,
                                local_count = local_count,
                                parser = self)
                        self._last.append(new)
                        caret.append(new)

            # For >
            elif token.type == Token.CHILD:
                # The last children added.
                self.caret[:] = self._last

            # For <
            elif token.type == Token.PARENT:
                # If we're the root node, don't do anything
                parent = self.caret[0].parent
                if parent is not None:
                    self.caret[:] = [parent]
        return

    # Properties
    # --------------------------------------------------------------------------- 

    # Property: dialect
    # The dialect of XML
    dialect = None

    # Property: str
    # The string
    str = ''

    # Property: tokens
    # The list of tokens
    tokens = []

    # Property: options
    # Reference to the [[Options]] instance
    options = None

    # Property: root
    # The root [[Element]] node.
    root = None 

    # Property: caret
    # The current insertion point.
    caret = None

    # Property: _last
    # List of the last appended stuff
    _last = None

    # Property: indent
    # Yeah
    indent = ''

    # Property: prefix
    # (String) The trailing tag in the beginning.
    #
    # Description:
    # For instance, in `<div>ul>li</div>`, the `prefix` is `<div>`.
    prefix = ''

    # Property: suffix
    # (string) The trailing tag at the end.
    suffix = ''
    pass

# =============================================================================== 

class Element:
    """An element.
    """

    def __init__(self, token=None, parent=None, count=None, local_count=None, \
                 parser=None, opening_tag=None, closing_tag=None, \
                 attributes=None, name=None, text=None):
        """Constructor.

        This is called by ???.

        Description:
        All parameters are optional.

        token       - (Token) The token (required)
        parent      - (Element) Parent element; `None` if root
        count       - (Int) The number to substitute for `&` (e.g., in `li.item-$`)
        local_count - (Int) The number to substitute for `$` (e.g., in `li.item-&`)
        parser      - (Parser) The parser

        attributes  - ...
        name        - ...
        text        - ...
        """

        self.children = []
        self.attributes = {}
        self.parser = parser

        if token is not None:
            # Assumption is that token is of type [[Token]] and is
            # a [[Token.ELEMENT]].
            self.name        = token.name
            self.attributes  = token.attributes.copy()
            self.text        = token.text
            self.populate    = token.populate
            self.expand      = token.expand
            self.opening_tag = token.opening_tag
            self.closing_tag = token.closing_tag

        # `count` can be given. This will substitude & in classname and ID
        if count is not None:
            for key in self.attributes:
                attrib = self.attributes[key]
                attrib = attrib.replace('&', ("%i" % count))
                if local_count is not None:
                    attrib = attrib.replace('$', ("%i" % local_count))
                self.attributes[key] = attrib

        # Copy over from parameters
        if attributes: self.attributes = attribues
        if name:       self.name       = name
        if text:       self.text       = text

        self._fill_attributes()

        self.parent = parent
        if parent is not None:
            self.depth = parent.depth + 1

        if self.populate: self._populate()

    def render(self):
        """Renders the element, along with it's subelements, into HTML code.

        [Grouped under "Rendering methods"]
        """

        output = ""
        try:    spaces_count = int(self.parser.options.options['indent-spaces'])
        except: spaces_count = 4
        spaces = ' ' * spaces_count
        indent = self.depth * spaces
        
        prefix, suffix = ('', '')
        if self.prefix: prefix = self.prefix + "\n"
        if self.suffix: suffix = self.suffix

        # Make the guide from the ID (/#header), or the class if there's no ID (/.item)
        # This is for the start-guide, end-guide and post-tag-guides
        guide_str = ''
        if 'id' in self.attributes:
            guide_str += "#%s" % self.attributes['id']
        elif 'class' in self.attributes:
            guide_str += ".%s" % self.attributes['class'].replace(' ', '.')

        # Build the post-tag guide (e.g., </div><!-- /#header -->),
        # the start guide, and the end guide.
        guide = ''
        start_guide = ''
        end_guide = ''
        if ((self.name == 'div') and \
            (('id' in self.attributes) or ('class' in self.attributes))):

            if (self.parser.options.has('post-tag-guides')):
                guide = "<!-- /%s -->" % guide_str

            if (self.parser.options.has('start-guide-format')):
                format = self.parser.options.get('start-guide-format')
                try: start_guide = format % guide_str
                except: start_guide = (format + " " + guide_str).strip()
                start_guide = "%s<!-- %s -->\n" % (indent, start_guide)

            if (self.parser.options.has('end-guide-format')):
                format = self.parser.options.get('end-guide-format')
                try: end_guide = format % guide_str
                except: end_guide = (format + " " + guide_str).strip()
                end_guide = "\n%s<!-- %s -->" % (indent, end_guide)

        # Short, self-closing tags (<br />)
        short_tags = self.parser.dialect.short_tags

        # When it should be expanded..
        # (That is, <div>\n...\n</div> or similar -- wherein something must go
        # inside the opening/closing tags)
        if  len(self.children) > 0 \
            or self.expand \
            or prefix or suffix \
            or (self.parser.options.has('expand-divs') and self.name == 'div'):

            for child in self.children:
                output += child.render()

            # For expand divs: if there are no children (that is, `output`
            # is still blank despite above), fill it with a blank line.
            if (output == ''): output = indent + spaces + "\n"

            # If we're a root node and we have a prefix or suffix...
            # (Only the root node can have a prefix or suffix.)
            if prefix or suffix:
                output = "%s%s%s%s%s\n" % \
                    (indent, prefix, output, suffix, guide)

            # Uh..
            elif self.name != '' or \
                 self.opening_tag is not None or \
                 self.closing_tag is not None:
                output = start_guide + \
                         indent + self.get_opening_tag() + "\n" + \
                         output + \
                         indent + self.get_closing_tag() + \
                         guide + end_guide + "\n"
            

        # Short, self-closing tags (<br />)
        elif self.name in short_tags: 
            output = "%s<%s />\n" % (indent, self.get_default_tag())

        # Tags with text, possibly
        elif self.name != '' or \
             self.opening_tag is not None or \
             self.closing_tag is not None:
            output = "%s%s%s%s%s%s%s%s" % \
                (start_guide, indent, self.get_opening_tag(), \
                 self.text, \
                 self.get_closing_tag(), \
                 guide, end_guide, "\n")

        # Else, it's an empty-named element (like the root). Pass.
        else: pass


        return output

    def get_default_tag(self):
        """Returns the opening tag (without brackets).

        Usage:
            element.get_default_tag()

        [Grouped under "Rendering methods"]
        """

        output = '%s' % (self.name)
        for key, value in self.attributes.iteritems():
            output += ' %s="%s"' % (key, value)
        return output

    def get_opening_tag(self):
        if self.opening_tag is None:
            return "<%s>" % self.get_default_tag()
        else:
            return self.opening_tag

    def get_closing_tag(self):
        if self.closing_tag is None:
            return "</%s>" % self.name
        else:
            return self.closing_tag

    def append(self, object):
        """Registers an element as a child of this element.

        Usage:
            element.append(child)

        Description:
        Adds a given element `child` to the children list of this element. It
        will be rendered when [[render()]] is called on the element.

        See also:
        - [[get_last_child()]]

        [Grouped under "Traversion methods"]
        """

        self.children.append(object)

    def get_last_child(self):
        """Returns the last child element which was [[append()]]ed to this element.

        Usage:
            element.get_last_child()

        Description:
        This is the same as using `element.children[-1]`.

        [Grouped under "Traversion methods"]
        """

        return self.children[-1]

    def _populate(self):
        """Expands with default items.

        This is called when the [[populate]] flag is turned on.
        """

        if self.name == 'ul':
            elements = [Element(name='li', parent=self, parser=self.parser)]

        elif self.name == 'dl':
            elements = [
                Element(name='dt', parent=self, parser=self.parser),
                Element(name='dd', parent=self, parser=self.parser)]

        elif self.name == 'table':
            tr = Element(name='tr', parent=self, parser=self.parser)
            td = Element(name='td', parent=tr, parser=self.parser)
            tr.children.append(td)
            elements = [tr]

        else:
            elements = []

        for el in elements:
            self.children.append(el)

    def _fill_attributes(self):
        """Fills default attributes for certain elements.

        Description:
        This is called by the constructor.

        [Protected, grouped under "Protected methods"]
        """

        # Make sure <a>'s have a href, <img>'s have an src, etc.
        required = self.parser.dialect.required

        for element, attribs in required.iteritems():
            if self.name == element:
                for attrib in attribs:
                    if attrib not in self.attributes:
                        self.attributes[attrib] = attribs[attrib]

    # ---------------------------------------------------------------------------

    # Property: last_child
    # [Read-only]
    last_child = property(get_last_child)

    # ---------------------------------------------------------------------------

    # Property: parent
    # (Element) The parent element.
    parent = None

    # Property: name
    # (String) The name of the element (e.g., `div`)
    name = ''

    # Property: attributes
    # (Dict) The dictionary of attributes (e.g., `{'src': 'image.jpg'}`)
    attributes = None

    # Property: children
    # (List of Elements) The children
    children = None

    # Property: opening_tag
    # (String or None) The opening tag. Optional; will use `name` and
    # `attributes` if this is not given.
    opening_tag = None

    # Property: closing_tag
    # (String or None) The closing tag
    closing_tag = None

    text = ''
    depth = -1
    expand = False
    populate = False
    parser = None

    # Property: prefix
    # Only the root note can have this.
    prefix = None
    suffix = None

# =============================================================================== 

class Token:
    def __init__(self, str, parser=None):
        """Token.

        Description:
        str   - The string to parse

        In the string `div > ul`, there are 3 tokens. (`div`, `>`, and `ul`)

        For `>`, it will be a `Token` with `type` set to `Token.CHILD`
        """

        self.str = str.strip()
        self.attributes = {}
        self.parser = parser

        # Set the type.
        if self.str == '<':
            self.type = Token.PARENT
        elif self.str == '>':
            self.type = Token.CHILD
        elif self.str == '+':
            self.type = Token.SIBLING
        else:
            self.type = Token.ELEMENT
            self._init_element()
        
    def _init_element(self):
        """Initializes. Only called if the token is an element token.
        [Private]
        """

        # Get the tag name. Default to DIV if none given.
        name = re.findall('^([\w\-:]*)', self.str)[0]
        name = name.lower().replace('-', ':')

        # Find synonyms through this thesaurus
        synonyms = self.parser.dialect.synonyms
        if name in synonyms.keys():
            name = synonyms[name]

        if ':' in name:
            try:    spaces_count = int(self.parser.options.get('indent-spaces'))
            except: spaces_count = 4
            indent = ' ' * spaces_count

            shortcuts = self.parser.dialect.shortcuts
            if name in shortcuts.keys():
                for key, value in shortcuts[name].iteritems():
                    setattr(self, key, value)
                if 'html' in name:
                    return
            else:
                self.name = name

        elif (name == ''): self.name = 'div'
        else: self.name = name

        # Look for attributes
        attribs = []
        for attrib in re.findall('\[([^\]]*)\]', self.str):
            attribs.append(attrib)
            self.str = self.str.replace("[" + attrib + "]", "")
        if len(attribs) > 0:
            for attrib in attribs:
                try:    key, value = attrib.split('=', 1)
                except: key, value = attrib, ''
                self.attributes[key] = value

        # Try looking for text
        text = None
        for text in re.findall('\{([^\}]*)\}', self.str):
            self.str = self.str.replace("{" + text + "}", "")
        if text is not None:
            self.text = text

        # Get the class names
        classes = []
        for classname in re.findall('\.([\$a-zA-Z0-9_\-\&]+)', self.str):
            classes.append(classname)
        if len(classes) > 0:
            try:    self.attributes['class']
            except: self.attributes['class'] = ''
            self.attributes['class'] += ' ' + ' '.join(classes)
            self.attributes['class'] = self.attributes['class'].strip()

        # Get the ID
        id = None
        for id in re.findall('#([\$a-zA-Z0-9_\-\&]+)', self.str): pass
        if id is not None:
            self.attributes['id'] = id

        # See if there's a multiplier (e.g., "li*3")
        multiplier = None
        for multiplier in re.findall('\*\s*([0-9]+)', self.str): pass
        if multiplier is not None:
            self.multiplier = int(multiplier)

        # Populate flag (e.g., ul+)
        flags = None
        for flags in re.findall('[\+\!]+$', self.str): pass
        if flags is not None:
            if '+' in flags: self.populate = True
            if '!' in flags: self.expand = True

    def __str__(self):
        return self.str 

    str = ''
    parser = None

    # For elements
    # See the properties of `Element` for description on these.
    name = ''
    attributes = None
    multiplier = 1
    expand = False
    populate = False
    text = ''
    opening_tag = None
    closing_tag = None

    # Type
    type = 0
    ELEMENT = 2 
    CHILD = 4
    PARENT = 8
    SIBLING = 16

# =============================================================================== 

class Router:
    """The router.
    """

    # Constructor 
    # --------------------------------------------------------------------------- 

    def __init__(self):
        pass

    # Methods 
    # --------------------------------------------------------------------------- 

    def start(self, options=None, str=None, ret=None):
        if (options):
            self.options = Options(router=self, options=options, argv=None)
        else:
            self.options = Options(router=self, argv=sys.argv[1:], options=None)

        if (self.options.has('help')):
            return self.help()

        elif (self.options.has('version')):
            return self.version()

        else:
            return self.parse(str=str, ret=ret)
    
    def help(self):
        print "Usage: %s [OPTIONS]" % sys.argv[0]
        print "Expands input into HTML."
        print ""
        for short, long, info in self.options.cmdline_keys:
            if "Deprecated" in info: continue 
            if not short == '': short = '-%s,' % short
            if not long  == '': long  = '--%s' % long.replace("=", "=XXX")

            print "%6s %-25s %s" % (short, long, info)
        print ""
        print "\n".join(self.help_content)

    def version(self):
        print "Uhm, yeah."

    def parse(self, str=None, ret=None):
        self.parser = Parser(self.options)

        try:
            # Read the files
            # for line in fileinput.input(): lines.append(line.rstrip(os.linesep))
            if str is not None:
                lines = str
            else:
                lines = [sys.stdin.read()]
                lines = " ".join(lines)

        except KeyboardInterrupt:
            pass

        except:
            sys.stderr.write("Reading failed.\n")
            return
            
        try:
            self.parser.load_string(lines)
            output = self.parser.render()
            if ret: return output
            sys.stdout.write(output)

        except:
            sys.stderr.write("Parse error. Check your input.\n")
            print sys.exc_info()[0]
            print sys.exc_info()[1]

    def exit(self):
        sys.exit()

    help_content = [
        "Please refer to the manual for more information.",
    ]

# =============================================================================== 

class Options:
    def __init__(self, router, argv, options=None):
        # Init self
        self.router = router

        # `options` can be given as a dict of stuff to preload
        if options:
            for k, v in options.iteritems():
                self.options[k] = v
            return

        # Prepare for getopt()
        short_keys, long_keys = "", []
        for short, long, info in self.cmdline_keys: # 'v', 'version'
            short_keys += short
            long_keys.append(long)

        try:
            getoptions, arguments = getopt.getopt(argv, short_keys, long_keys)

        except getopt.GetoptError:
            err = sys.exc_info()[1]
            sys.stderr.write("Options error: %s\n" % err)
            sys.stderr.write("Try --help for a list of arguments.\n")
            return router.exit()

        # Sort them out into options
        options = {}
        i = 0
        for option in getoptions:
            key, value = option # '--version', ''
            if (value == ''): value = True

            # If the key is long, write it
            if key[0:2] == '--':
                clean_key = key[2:]
                options[clean_key] = value

            # If the key is short, look for the long version of it
            elif key[0:1] == '-':
                for short, long, info in self.cmdline_keys:
                    if short == key[1:]:
                        print long
                        options[long] = True

        # Done
        for k, v in options.iteritems():
            self.options[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def get(self, attr):
        try:    return self.options[attr]
        except: return None

    def has(self, attr):
        try:    return self.options.has_key(attr)
        except: return False

    options = {
        'indent-spaces': 4
    }
    cmdline_keys = [
        ('h', 'help', 'Shows help'),
        ('v', 'version', 'Shows the version'),
        ('', 'no-guides', 'Deprecated'),
        ('', 'post-tag-guides', 'Adds comments at the end of DIV tags'),
        ('', 'textmate', 'Adds snippet info (textmate mode)'),
        ('', 'indent-spaces=', 'Indent spaces'),
        ('', 'expand-divs', 'Automatically expand divs'),
        ('', 'no-last-newline', 'Skip the trailing newline'),
        ('', 'start-guide-format=', 'To be documented'),
        ('', 'end-guide-format=', 'To be documented'),
    ]
    
    # Property: router
    # Router
    router = 1

# =============================================================================== 

if __name__ == "__main__":
    z = Router()
    z.start()

########NEW FILE########
