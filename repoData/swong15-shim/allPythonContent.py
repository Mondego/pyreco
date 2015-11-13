__FILENAME__ = command_parser
# logic for parsing command buffer string and determining commands
# interfaces with shim through the in the parse_buffer function
# TODO: currently parser does a greedy scan of possible tokens
# per iteration and selects longest token, this might not actually work.
# TODO: RENAME THIS FILE COMMAND PARSER IS FULLY OBSOLETE
import re
from copy import deepcopy
from backend import command_list
from backend.commandparser.default_cmds import DEFAULT_COMMAND_TOKENS, DEFAULT_COMMAND_MAP
from backend.commandparser.ex_cmds import EX_COMMAND_TOKENS, EX_COMMAND_MAP

# BEGIN YANKED FUNCTIONS, TODO: CLEAN THIS UP
def goto_line_num(s):
    ind = s.find('gg')
    if ind == 0:
        return ['move_cursor_begin_file']
    else:
        count = 'n' + s[:ind]
        return [count, 'move_cursor_line_num']


def go_file_begin(s):
    return ['move_cursor_begin_file']


def seek_char(s):
    # assumption is that the regex will only return a string of length 2,
    # seems kind of reasonable
    return ['c' + s[1], 'move_cursor_seek_char']


def repeat_default_movement(s):
    n_arg = re.search('[0-9]*', s).group()
    return ['r' + n_arg, command_list.DEFAULT_MOVEMENTS[s[len(n_arg):]][0]]


def delete_text_movement(s):
    return ['s' + command_list.DEFAULT_MOVEMENTS[s[1:]][0],
            'delete_text_movement']


def delete_curr_line(s):
    n_arg = re.search('[0-9]*', s).group()
    if bool(n_arg):
        return ['r' + n_arg, 'delete_curr_line']
    else:
        return ['delete_curr_line']


def yank_curr_line(s):
    return ['yank_curr_line']


def quit(s):
    return ['quit']


def write(s):
    return ['write']

def write_and_quit(s):
    return ['write_and_quit']
# END YANKED FUNCTIONS, TODO: CLEAN THIS UP

def mark_position(s):
    buf = s[-1]
    return ['c' + buf, 'mark_location']


def jump_mark(s):
    buf = s[-1]
    return ['c' + buf, 'jump_location']


COMMAND_MAP = {
    'WRITE': write,
    'QUIT': quit,
    'JUMP_MARK': jump_mark,
    'FIND_CHARACTER': seek_char,
    'YANK_LINE': yank_curr_line,
    'JUMP_LINE_NUM': goto_line_num,
    'MARK_POSITION': mark_position,
    'GO_FILE_BEGIN': go_file_begin,
    'DELETE_LINE': delete_curr_line,
    'WRITE_AND_QUIT': write_and_quit,
    'DELETE_MOVEMENT': delete_text_movement,
    'REPEAT_MOVEMENT': repeat_default_movement,
}


class token():

    def __init__(self, t, r):
        self.type = t
        self.raw = r

    def __repr__(self):
        return 'type: %s | raw: %s' % (self.type, self.raw)

    def get_token(self):
        return self.type, self.val

    def get_type(self):
        return self.type


class parser():

    def __init__(self, mode):
        mode_dct ={
            'default': {
                'tokens': DEFAULT_COMMAND_TOKENS,
                'cmds': DEFAULT_COMMAND_MAP,
            },
            'ex': {
                'tokens': EX_COMMAND_TOKENS,
                'cmds': EX_COMMAND_MAP,
            },
        }
        self._tokens = mode_dct[mode]['tokens']
        self._cmds = mode_dct[mode]['cmds']

    def try_tok_str(self, s):
        matches = []
        for regex, res in self._tokens.items():
            result = regex.match(s)
            if bool(result):
                matches.append((result.group(), res))

        if not len(matches):
            return False
        return max(matches, key=lambda t: t[0])

    def try_cmd_match(self, res):
        res = [tok.get_type() for tok in res]
        for pattern, cmd in self._cmds.items():
            if res == pattern.split('|'):
                return cmd
        return None

    def parse_string(self, s):
        result = []
        has_match = True
        cs = deepcopy(s)

        while has_match:
            match = self.try_tok_str(cs)
            if match:
                result.append(
                    token(match[1]['type'], match[0])
                )
                cs = cs[len(match[0]):]
                has_match = self.try_tok_str(cs)
            else:
                break

        cmd = self.try_cmd_match(result)
        if cmd != None:
            return COMMAND_MAP[cmd](s)
        else:
            return ''

########NEW FILE########
__FILENAME__ = default_cmds
import re


DEFAULT_COMMAND_TOKENS = {
    re.compile('[0-9]+'): {
        'type':'NUMBER',
    },
    re.compile('f.'): {
        'type':'FIND_CHARACTER',
    },
    re.compile('d'): {
        'type': 'DELETE_INIT',
    },
    re.compile('dd'): {
        'type': 'DELETE_LINE',
    },
    re.compile('[h|j|k|l|w|b|\{|\}]'): {
        'type': 'MOVEMENT',
    },
    re.compile('yy'): {
        'type': 'YANK_LINE',
    },
    re.compile('gg'): {
        'type': 'GO_TO_LINE_NUM',
    },
    re.compile('m[a-z]'): {
        'type': 'MARK_POSITION',
    },
    re.compile('\'[a-z]'): {
        'type': 'JUMP_MARK',
    }
}


DEFAULT_COMMAND_MAP = {
    'YANK_LINE': 'YANK_LINE',
    'FIND_CHARACTER': 'FIND_CHARACTER',
    'NUMBER|GO_TO_LINE_NUM': 'JUMP_LINE_NUM',
    'GO_TO_LINE_NUM': 'GO_FILE_BEGIN',
    'DELETE_INIT|MOVEMENT': 'DELETE_MOVEMENT',
    'DELETE_LINE': 'DELETE_LINE',
    'NUMBER|DELETE_LINE': 'DELETE_LINE_REPEAT',
    'NUMBER|MOVEMENT': 'REPEAT_MOVEMENT',
    'MARK_POSITION': 'MARK_POSITION',
    'JUMP_MARK': 'JUMP_MARK',
}

########NEW FILE########
__FILENAME__ = ex_cmds
import re

EX_COMMAND_TOKENS = {
    re.compile('w'): {
        'type':'WRITE',
    },
    re.compile('q'): {
        'type':'QUIT',
    },
}


EX_COMMAND_MAP = {
    'WRITE': 'WRITE',
    'QUIT': 'QUIT',
    'WRITE|QUIT': 'WRITE_AND_QUIT',
}

########NEW FILE########
__FILENAME__ = command_list
# Python variables containing useful mapping translations
# i.e Tkinter keysym event mapping to useful character mapping
# like 'comma': ','
# This should be able to be manipulated by the user in some fashion
# to enable custom key mappings and potentially more(design required)
# TODO: fix hard coded tab width

COMMAND_MAP = {
    'dollar': '$',
    'braceright': '}',
    'braceleft': '{',
    'bracketright': ']',
    'bracketleft': '[',
    'parenright': ')',
    'parenleft': '(',
    'colon': ':',
    'semicolon': ';',
    'bar': '|',
    'greater': '>',
    'less': '<',
    'comma': ',',
    'period': '.',
    'slash': '/',
    'question': '?',
    'plus': '+',
    'equal': '=',
    'minus': '-',
    'underscore': '_',
    'exclam': '!',
    'at': '@',
    'percent': '%',
    'asciicircum': '^',
    'ampersand': '&',
    'asterisk': '*',
    'quoteright': "'",
    'quotedbl': '"',
    'BackSpace': 'BackSpace',
    'Return': 'Return',
    'space': ' ',
    'Up': '<Up>',
    'Down': '<Down>',
    'Left': '<Left>',
    'Right': '<Right>',
    'Tab': '    ',
    '<Control-braceright>': '<Control-bracketright>',
    '<Control-braceleft>': '<Control-bracketleft>',
}


DEFAULT_MOVEMENTS = {
    'p': ['paste'],
    # 'u': ['undo_command'],
    'k': ['move_cursor_up'],
    'h': ['move_cursor_left'],
    'j': ['move_cursor_down'],
    'l': ['move_cursor_right'],
    '<Up>': ['move_cursor_up'],
    '<Left>': ['move_cursor_left'],
    '<Down>': ['move_cursor_down'],
    '<Right>': ['move_cursor_right'],
    'A': ['insert_end_of_line'],
    'G': ['move_cursor_end_file'],
    '$': ['move_cursor_end_line'],
    'O': ['insert_new_line_above'],
    'o': ['insert_new_line_below'],
    'x': ['delete_text_highlight'],
    # '<Control-r>': ['redo_command'],
    'gg': ['move_cursor_begin_file'],
    'e': ['move_cursor_next_word_end'],
    '}': ['move_cursor_next_paragraph'],
    '{': ['move_cursor_prev_paragraph'],
    '0': ['move_cursor_beginning_line'],
    'w': ['move_cursor_next_word_front'],
    'b': ['move_cursor_prev_word_front'],
    '<Control-braceright>': ['move_next_instance_buffer'],
    '<Control-braceleft>': ['move_prev_instance_buffer'],
}


DEFAULT_COMMAND_LEADERS = set(['g', 'f', 'd', 'y', 'm', "'"])


VISUAL_MOVEMENTS = {
    'k': ['move_cursor_up'],
    'h': ['move_cursor_left'],
    'j': ['move_cursor_down'],
    'l': ['move_cursor_right'],
    '<Up>': ['move_cursor_up'],
    '<Left>': ['move_cursor_left'],
    '<Down>': ['move_cursor_down'],
    '<Right>': ['move_cursor_right'],
    '<': ['shift_selection_left'],
    'G': ['move_cursor_end_file'],
    '$': ['move_cursor_end_line'],
    '>': ['shift_selection_right'],
    'x': ['delete_text_highlight'],
    'gg': ['move_cursor_begin_file'],
    'e': ['move_cursor_next_word_end'],
    '}': ['move_cursor_next_paragraph'],
    '{': ['move_cursor_prev_paragraph'],
    '0': ['move_cursor_beginning_line'],
    'w': ['move_cursor_next_word_front'],
    'b': ['move_cursor_prev_word_front'],
}


DEFAULT_BREAK_MOVEMENTS = {
    'k': ['move_cursor_up'],
    'h': ['move_cursor_left'],
    'j': ['move_cursor_down'],
    'l': ['move_cursor_right'],
    '<Up>': ['move_cursor_up'],
    '<Left>': ['move_cursor_left'],
    '<Down>': ['move_cursor_down'],
    '<Right>': ['move_cursor_right'],
    'w': ['move_cursor_next_word_front'],
    'b': ['move_cursor_prev_word_front'],
    'x': ['delete_text_highlight'],
}


VISUAL_BREAK_MOVEMENTS = {
    'y': ['visual_yank']
}

########NEW FILE########
__FILENAME__ = interaction_manager
# Routes keyboard input to appropriate interaction manager
# to mutate instance state page is then re-rendered given new state
# Events are fed directly from user_input
# Interaction manager should not have to parse user input keys directly
import sys
from backend.interaction_managers import (
    cursor_logic, text_logic, graphics_logic)


def render_default_graphics(graphics_state, local_state, global_state):
    """
    Render 'default' graphics i.e line numbers, cursor, text lines etc.
    """
    lines = local_state.get_line_tokens()
    x, y, curr_top = local_state.get_page_state()
    buff_line_count = graphics_state.get_line_height()

    graphics_state.draw_cursor(x, y)
    graphics_state.draw_line_numbers(curr_top + 1)
    for i in range(buff_line_count + 1):
        try:
            graphics_state.write_line_grid(i, lines[curr_top + i])
        except IndexError:
            break
    x, y, t = local_state.get_page_state()
    status_line = 'file: %s  |  mode: %s  |  %d, %d | command buffer: %s' % \
        (local_state.get_filename(), global_state.get_curr_state(), x, y + t,
            global_state.get_command_buffer())
    graphics_state.write_status_line(status_line)


def render_page(graphics_state, local_state, global_state, pre=[], post=[]):
    """
    Clear buffer and and run pre and post graphics mutating functions
    Pre and post should contain a list of lambdas like so:
    [lambda: graphics_logic.highlight_visual_mode(graphics_state, local_state)]
    That way graphics can be rendered both before and after the default
    rendering routine is called so as to allow for flexibility with plugins and
    default rendering functions
    """
    graphics_state.clear_all()
    for func in pre:
        func()
    render_default_graphics(graphics_state, local_state, global_state)
    for func in post:
        func()


def move_left(graphics_state, local_state, global_state):
    """
    Functionality corresponding to h in vim
    """
    cursor_logic.move_cursor_left(local_state)
    render_page(graphics_state, local_state, global_state)


def move_right(graphics_state, local_state, global_state):
    """
    Functionality corresponding to l in vim
    """
    cursor_logic.move_cursor_right(local_state)
    render_page(graphics_state, local_state, global_state)


def move_down(graphics_state, local_state, global_state):
    """
    Functionality corresponding to j in vim
    """
    cursor_logic.move_cursor_down(local_state)
    render_page(graphics_state, local_state, global_state)


def move_up(graphics_state, local_state, global_state):
    """
    Functionality corresponding to k in vim
    """
    cursor_logic.move_cursor_up(local_state)
    render_page(graphics_state, local_state, global_state)


def move_beginning_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to 0 in vim
    """
    cursor_logic.move_cursor_beginning_line(local_state)
    render_page(graphics_state, local_state, global_state)


def move_end_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to $ in vim
    """
    cursor_logic.move_cursor_end_line(local_state)
    render_page(graphics_state, local_state, global_state)


def move_next_word_front(graphics_state, local_state, global_state):
    """
    Functionality corresponding to w in vim
    """
    cursor_logic.move_cursor_next_word_front(local_state)
    render_page(graphics_state, local_state, global_state)


def move_next_word_end(graphics_state, local_state, global_state):
    """
    Functionality corresponding to e in vim
    """
    cursor_logic.move_cursor_next_word_end(local_state)
    render_page(graphics_state, local_state, global_state)


def move_prev_word_front(graphics_state, local_state, global_state):
    """
    Functionality corresponding to b in vim
    """
    cursor_logic.move_cursor_move_prev_word_front(local_state)
    render_page(graphics_state, local_state, global_state)


def move_end_file(graphics_state, local_state, global_state):
    """
    Functionality corresponding to G in vim
    """
    cursor_logic.move_cursor_end_file(local_state)
    render_page(graphics_state, local_state, global_state)


def move_begin_file(graphics_state, local_state, global_state):
    """
    Functionality corresponding to gg in vim
    """
    cursor_logic.move_cursor_begin_file(local_state)
    render_page(graphics_state, local_state, global_state)


def move_next_paragraph(graphics_state, local_state, global_state):
    """
    Functionality corresponding to } in vim
    """
    cursor_logic.move_cursor_next_paragraph(local_state)
    render_page(graphics_state, local_state, global_state)


def move_prev_paragraph(graphics_state, local_state, global_state):
    """
    Functionality corresponding to { in vim
    """
    cursor_logic.move_cursor_prev_paragraph(local_state)
    render_page(graphics_state, local_state, global_state)


def move_line_num(n_arg, graphics_state, local_state, global_state):
    """
    Functionality corresponding to line number jumps in vim
    i.e 123gg jumps to line 123
    """
    cursor_logic.move_cursor_line_num(n_arg, local_state)
    render_page(graphics_state, local_state, global_state)


def move_seek_char(c_arg, graphics_state, local_state, global_state):
    """
    Functionality corresponding to f[character] in vim
    """
    cursor_logic.move_cursor_seek_char(c_arg, local_state)
    render_page(graphics_state, local_state, global_state)


def insert_text(s_arg, graphics_state, local_state, global_state):
    text_logic.insert_text_str(s_arg, local_state)
    render_page(graphics_state, local_state, global_state)


def delete_char(graphics_state, local_state, global_state):
    """
    Functionality corresponding to x in vim
    """
    text_logic.delete_text_char(local_state)
    render_page(graphics_state, local_state, global_state)


def add_new_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to <Return> in vim
    """
    text_logic.add_new_line_char(local_state)
    render_page(graphics_state, local_state, global_state)


def delete_text_movement(movement, graphics_state, local_state, global_state):
    """
    Delete a text in a given range. I.e 'dw' or 'd}'
    Performs this operation by:
        1. Getting current location
        2. Mutating page state with movement argument
        3. Getting location after page manipulation
        4. Mutating local line buffer to remove desired range

    TODO: This is not optimal,
    Calling COMMAND_MAP[movement](graphics_state, local_state, global_state)
    messes with graphics state unnecessarily
    """
    px, py, pt = local_state.get_page_state()
    COMMAND_MAP[movement](graphics_state, local_state, global_state)
    nx, ny, nt = local_state.get_page_state()

    text_logic.delete_text_range(px, py, pt, nx, ny, nt, local_state)
    render_page(graphics_state, local_state, global_state)


def delete_text_highlight(graphics_state, local_state, global_state):
    """
    Delete text under highlight.
    Cursor corresponds to a highlight over a single character
    i.e Calling delete_text_highlight without visual mode on corresponds to
    deleting a single character or x in vim
    TODO: In the visual mode case this adds the deleted text to the copy buffer
    This should be mirrored in the non visual mode case
    """
    if global_state.get_curr_state() == 'Visual':
        px, py, pt = local_state.get_visual_anchors()
        nx, ny, nt = local_state.get_page_state()
        txt = text_logic.get_text_range(px, py, pt, nx, ny, nt, local_state)
        global_state.add_copy_buffer(txt)
        text_logic.delete_text_range(px, py, pt, nx, ny, nt, local_state)
        global_state.set_curr_state('Default')
    else:
        text_logic.delete_text_highlight(local_state)

    render_page(graphics_state, local_state, global_state)


def delete_curr_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to dd in vim
    """
    text_logic.delete_current_line(local_state, global_state)
    render_page(graphics_state, local_state, global_state)


def insert_new_line_above(graphics_state, local_state, global_state):
    """
    Functionality corresponding to O in vim
    """
    global_state.set_curr_state('Insert')
    text_logic.insert_new_line_above(local_state)
    render_page(graphics_state, local_state, global_state)


def insert_new_line_below(graphics_state, local_state, global_state):
    """
    Functionality corresponding to o in vim
    """
    global_state.set_curr_state('Insert')
    text_logic.insert_new_line_below(local_state)
    render_page(graphics_state, local_state, global_state)


def insert_end_of_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to A in vim
    """
    global_state.set_curr_state('Insert')
    cursor_logic.move_cursor_past_end_line(local_state)
    render_page(graphics_state, local_state, global_state)


def mouse_scroll(delta, graphics_state, local_state, global_state):
    """
    Moves cursor upward to downward depending on scroll direction
    TODO: Similarly, a mouse click should move the cursor to the x, y location
    of the mouse
    """
    x, y, curr_top = local_state.get_page_state()
    if y + int(delta) + curr_top <= local_state.get_line_num() - 2:
        local_state.set_cursor(x, y + int(delta))
        render_page(graphics_state, local_state, global_state)
    else:
        move_end_file(graphics_state, local_state, global_state)


def visual_movement(motion, graphics_state, local_state, global_state):
    """
    Movement in visual mode, render line highlight code in prior to
    'Default' graphics rendering routine
    """
    COMMAND_MAP[motion](graphics_state, local_state, global_state)
    # some commands break out of visual mode
    if global_state.get_curr_state() == 'Visual':
        f = lambda: graphics_logic.highlight_visual_mode(
            graphics_state, local_state
        )
        render_page(graphics_state, local_state, global_state, post=[f])


def paste(graphics_state, local_state, global_state):
    """
    Functionality corresponding to p in vim
    """
    text_logic.insert_copy_buffer(local_state, global_state)
    render_page(graphics_state, local_state, global_state)


def yank_curr_line(graphics_state, local_state, global_state):
    """
    Functionality corresponding to yy in vim
    """
    x, y, curr_top = local_state.get_page_state()
    global_state.add_copy_buffer([local_state.get_line(curr_top + y)])


def shift_selection_right(graphics_state, local_state, global_state):
    """
    Functionality that closely mirrors > in vim
    Does not exist visual mode on shift completion
    TODO: Discuss whether or not it should remain that way
    """
    text_logic.shift_selection_right(local_state)
    render_page(graphics_state, local_state, global_state)


def shift_selection_left(graphics_state, local_state, global_state):
    """
    Functionality that closely mirrors < in vim
    Does not exist visual mode on shift completion
    TODO: Discuss whether or not it should remain that way
    """
    text_logic.shift_selection_left(local_state)
    render_page(graphics_state, local_state, global_state)


def quit(graphics_state, local_state, global_state):
    """
    Quit shim.
    Add shutdown routines here if need be
    """
    sys.exit(1)


def write(graphics_state, local_state, global_state):
    lines = ''.join(local_state.get_lines())
    with open(local_state.get_filename(), 'w') as f:
        f.write(lines)


def write_and_quit(graphics_state, local_state, global_state):
    write(graphics_state, local_state, global_state)
    quit(graphics_state, local_state, global_state)


def undo_command(graphics_state, local_state, global_state):
    """
    Functionality corresponding to u in vim
    """
    local_state.undo_state()
    render_page(graphics_state, local_state, global_state)


def redo_command(graphics_state, local_state, global_state):
    """
    Functionality corresponding to <Control-r> in vim
    """
    local_state.redo_state()
    render_page(graphics_state, local_state, global_state)


def move_next_instance_buffer(graphics_state, local_state, global_state):
    """
    Functionality corresponding to :bn in vim
    Currently bound to <Control-}>
    """
    global_state.go_next_instance()


def move_prev_instance_buffer(graphics_state, local_state, global_state):
    """
    Functionality corresponding to :bp in vim
    Currently bound to <Control-{>
    """
    global_state.go_prev_instance()


def visual_yank(graphics_state, local_state, global_state):
    """
    Place in copy buffer the text
    currently selected under visual mode
    """
    px, py, pt = local_state.get_visual_anchors()
    nx, ny, nt = local_state.get_page_state()
    txt = text_logic.get_text_range(px, py, pt, nx, ny, nt, local_state)
    global_state.add_copy_buffer(txt)
    global_state.set_curr_state('Default')
    render_page(graphics_state, local_state, global_state)


def mark_location(buf, graphics_state, local_state, global_state):
    x, y, curr_top = local_state.get_page_state()
    loc = (x, y, curr_top)
    local_state.set_mark(buf, loc)


def jump_location(buf, graphics_state, local_state, global_state):
    loc = local_state.get_mark(buf)
    if loc:
        (x, y, top) = loc
        local_state.set_cursor(x, y)
        local_state.set_curr_top(top)
        render_page(graphics_state, local_state, global_state)


COMMAND_MAP = {
    'quit': quit,
    'write': write,
    'paste': paste,
    'move_cursor_up': move_up,
    'insert_text': insert_text,
    'delete_char': delete_char,
    'visual_yank': visual_yank,
    'undo_command': undo_command,
    'redo_command': redo_command,
    'mouse_scroll': mouse_scroll,
    'add_new_line': add_new_line,
    'move_cursor_left': move_left,
    'move_cursor_down': move_down,
    'mark_location': mark_location,
    'jump_location': jump_location,
    'move_cursor_right': move_right,
    'write_and_quit': write_and_quit,
    'yank_curr_line': yank_curr_line,
    'visual_movement': visual_movement,
    'delete_curr_line': delete_curr_line,
    'move_cursor_end_line': move_end_line,
    'move_cursor_end_file': move_end_file,
    'move_cursor_line_num': move_line_num,
    'move_cursor_seek_char': move_seek_char,
    'insert_end_of_line': insert_end_of_line,
    'move_cursor_begin_file': move_begin_file,
    'shift_selection_left': shift_selection_left,
    'delete_text_movement': delete_text_movement,
    'insert_new_line_above': insert_new_line_above,
    'insert_new_line_below': insert_new_line_below,
    'delete_text_highlight': delete_text_highlight,
    'shift_selection_right': shift_selection_right,
    'move_cursor_next_word_end': move_next_word_end,
    'move_cursor_next_paragraph': move_next_paragraph,
    'move_cursor_prev_paragraph': move_prev_paragraph,
    'move_cursor_beginning_line': move_beginning_line,
    'move_cursor_next_word_front': move_next_word_front,
    'move_cursor_prev_word_front': move_prev_word_front,
    'move_next_instance_buffer': move_next_instance_buffer,
    'move_prev_instance_buffer': move_prev_instance_buffer,
}


def input_command(command, graphics_state, local_state, global_state):
    """
    Look up mapping for appropriate function to call
    if multiple commands are passed in, separate parsing logic is required
    """
    if len(command) == 1:
        COMMAND_MAP[command[0]](graphics_state, local_state, global_state)
    else:
        input_command_arg(command, graphics_state, local_state, global_state)


def input_command_arg(commands, graphics_state, local_state, global_state):
    """
    Logic to handle commands that are not singular i.e f[char] or d}

    TODO: These mapping schemes might not be valid anymore once a proper
    parser is implemented
    c denotes character arguments i.e fa maps to find a
    n denotes numerical arguments i.e 123gg maps to jump to line 123
    r denotes repeat arguments i.e 3j means run the 'j' command 3 times
    s denotes character arguments i.e text insert
    """
    opt_arg = commands[0][1:]
    in_arg = commands[1]
    if commands[0].startswith('n'):
        COMMAND_MAP[in_arg](
            int(opt_arg), graphics_state, local_state, global_state)
    elif commands[0].startswith('r'):
        for i in range(int(opt_arg)):
            COMMAND_MAP[in_arg](graphics_state, local_state, global_state)
    elif commands[0].startswith('c'):
        # This should be a single character argument anyway
        COMMAND_MAP[in_arg](opt_arg, graphics_state, local_state, global_state)
    elif commands[0].startswith('s'):
        COMMAND_MAP[in_arg](opt_arg, graphics_state, local_state, global_state)

########NEW FILE########
__FILENAME__ = cursor_logic
def move_cursor_beginning_line(local_state):
    """
    Functionality corresponding to 0
    """
    x, y = local_state.get_cursor()
    local_state.set_cursor(0, y)


def move_cursor_end_line(local_state):
    """
    Functionality corresponding to $
    """
    x, y = local_state.get_cursor()
    curr_top = local_state.get_curr_top()
    curr_line = local_state.get_line(y + curr_top)
    local_state.set_cursor(len(curr_line) - 2, y)


def move_cursor_past_end_line(local_state):
    """
    Sometimes you want to move past the 'boundary'
    i.e for the A command in vim
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()
    curr_line = local_state.get_line(y + curr_top)
    local_state.set_cursor(len(curr_line) - 1, y)


def move_cursor_end_file(local_state):
    """
    Functionality corresponding to G
    """
    x, y = local_state.get_cursor()
    local_state.set_curr_top(
        max(0, local_state.get_line_num() - local_state.get_line_height() - 1)
    )
    local_state.set_cursor(
        0, min(local_state.get_line_num() - 1, local_state.get_line_height())
    )


def move_cursor_begin_file(local_state):
    """
    Functionality corresponding to gg
    """
    local_state.set_curr_top(0)
    x, y = local_state.get_cursor()
    local_state.set_cursor(0, 0)


def move_cursor_left(local_state):
    """
    Functionality corresponding to h
    """
    x, y = local_state.get_cursor()
    x = (0, x - 1)[x - 1 > 0]
    local_state.set_cursor(x, y)


def move_cursor_line_num(n, local_state):
    """
    Functionality corresponding to line number jumps
    i.e 123gg
    """
    total = local_state.get_line_num()
    per_page = local_state.get_line_height()
    if n > (total - per_page):
        if total < per_page:
            local_state.set_cursor(
                0, min(local_state.get_line_num() - 1, n - 1)
            )
        else:
            local_state.set_cursor(
                0, min(
                    local_state.get_line_num() - 1, per_page - (total - n - 1)
                )
            )
            local_state.set_curr_top(
                max(0, total - per_page - 2)
            )
    else:
        local_state.set_curr_top(
            max(
                0,
                min(n - 1, local_state.get_line_num() - 1))
        )
        local_state.set_cursor(0, 0)


def move_cursor_seek_char(c, local_state):
    """
    Functionality corresponding to f[char]
    i.e f{ seeks the first occurence of '{' in the
    current string
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()

    curr_line = local_state.get_line(y + curr_top)
    for offset, char, in enumerate(curr_line[x + 1:]):
        if char == c:
            local_state.set_cursor(x + offset + 1, y)
            break


def move_cursor_right(local_state):
    """
    Functionality corresponding to l in vim
    """
    x, y = local_state.get_cursor()
    curr_top = local_state.get_curr_top()
    lines = local_state.get_lines()
    try:
        nxt_char = lines[curr_top + y][x + 1]
    except:
        nxt_char = '\n'
    x = (x, x + 1)[nxt_char != '\n']
    local_state.set_cursor(x, y)


def move_cursor_up(local_state):
    """
    Functionality corresponding to k in vim
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()

    try:
        previous_line = local_state.get_line(y + curr_top - 1)
        # last character is a new line
        x = min(x, len(previous_line) - 2)
    except IndexError:
        pass

    local_state.set_cursor(x, y - 1)


def move_cursor_next_paragraph(local_state):
    """
    Functionality corresponding to } in vim
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()
    accept_all = False

    for offset, line_num in enumerate(
        range(y + curr_top + 1, local_state.get_line_num() - 1)
    ):
        l = local_state.get_line(line_num).strip()
        if (l == '') and accept_all:
            return local_state.set_cursor(0, y + offset + 1)
        elif l != '':
            accept_all = True

    local_state.set_curr_top(
        max(0, local_state.get_line_num() - local_state.get_line_height() - 1))
    local_state.set_cursor(
        0,  min(local_state.get_line_num() - 1, local_state.get_line_height()))


def move_cursor_prev_paragraph(local_state):
    """
    Functionality corresponding to { in vim
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()
    accept_all = False

    for offset, line_num in enumerate(range(y + curr_top - 1, -1, -1)):
        l = local_state.get_line(line_num).strip()
        if (l == '') and accept_all:
            return local_state.set_cursor(0, y - offset - 1)
        elif l != '':
            accept_all = True

    local_state.set_curr_top(0)
    local_state.set_cursor(0, 0)


def move_cursor_down(local_state):
    """
    Functionality corresponding to j in vim
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()

    try:
        next_line = local_state.get_line(y + curr_top + 1)
        # last character is a new line
        x = min(x, len(next_line) - 2)
    except IndexError:
        pass
    # if curr line + 1 is < total line numbers then move cursor down
    if (curr_top + y + 1) < local_state.get_line_num():
        local_state.set_cursor(x, y + 1)


def move_cursor_next_word_front(local_state):
    """
    Functionality corresponding to w in vim
    TODO: there might be a smarter way to do this.
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()
    accept_all = False

    for index, char in enumerate(
        (local_state.get_line(y + curr_top)[x + 1:])
    ):
        if (accept_all and char != ' ') or (
            char in ["'", '[', ']', '(', ')', '-', '+', '{', '}']
        ):
            return local_state.set_cursor(x + index + 1, y)
        elif char == ' ':
            accept_all = True

    for offset, line_num in enumerate(
        range(y + curr_top + 1, local_state.get_line_num())
    ):
        l = local_state.get_line(line_num)
        for index, char in enumerate(l):
            if char != ' ':
                return local_state.set_cursor(index, y + offset + 1)


def move_cursor_move_prev_word_front(local_state):
    """
    Functionality corresponding to b in vim
    TODO: there might be a smarter way to do this.
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()

    # Same as above, I'm pretty sure this can be cleaner.
    curr_str = local_state.get_line(y + curr_top)
    for dx in range(x - 1, -1, -1):
        if (curr_str[dx] != ' ' and curr_str[dx - 1] == ' ') or (
            curr_str[dx] in ["'", '[', ']', '(', ')', '-', '+', '{', '}']
        ):
            return local_state.set_cursor(dx, y)
        elif (curr_str[dx] != ' ') and dx == 0:
            return local_state.set_cursor(dx, y)

    for dy, line_num in enumerate(range(y + curr_top - 1, -1, -1)):
        curr_str = local_state.get_line(line_num)
        for dx in range(len(curr_str) - 1, 0, -1):
            if (curr_str[dx] != ' ' and curr_str[dx - 1] == ' ') or (
                curr_str[dx] in ["'", '[', ']', '(', ')', '-', '+', '{', '}']
            ):
                return local_state.set_cursor(dx, y - dy - 1)


def move_cursor_next_word_end(local_state):
    """
    Functionality corresponding to e in vim
    TODO: there might be a smarter way to do this.
    """
    curr_top = local_state.get_curr_top()
    x, y = local_state.get_cursor()
    curr_str = local_state.get_line(curr_top + y)

    for dx in range(x + 2, len(curr_str) - 1):
        if (curr_str[dx] == ' ' and curr_str[dx - 1] != ' ') or (
            curr_str[dx] in ["'", '[', ']', '(', ')', '-', '+', '{', '}']
        ):
            return local_state.set_cursor(dx - 1, y)

    for dy, line_num in enumerate(
        range(y + curr_top + 1, local_state.get_line_num())
    ):
        curr_str = local_state.get_line(line_num)
        for dx in range(len(curr_str)):
            if (curr_str[dx] == ' ' and curr_str[dx - 1] != ' ') or (
                curr_str[dx] in ["'", '[', ']', '(', ')', '-', '+', '{', '}']
            ):
                return local_state.set_cursor(dx - 1, y + dy + 1)

########NEW FILE########
__FILENAME__ = graphics_logic
from backend.state.syntaxtokens.color_config import options


def highlight_visual_mode(graphics_state, local_state):
    """
    TODO: remove magic numbers from code here
    """
    nx, ny, nt = local_state.get_page_state()
    px, py, pt = local_state.get_visual_anchors()
    color = options['line_num_text_color']

    if py + pt == ny + nt:
        line = local_state.get_line(py + pt)
        graphics_state.draw_highlight_grid(py, px, nx)
        graphics_state.write_text_grid(0, py, line, color)
    else:
        lp = local_state.get_line(py + pt)
        ln = local_state.get_line(ny + nt)

        if py + pt > ny + nt:
            graphics_state.draw_highlight_grid(py + pt - nt, px, 0)
            graphics_state.write_text_grid(0, py + pt - nt, lp, color)
            graphics_state.draw_highlight_grid(ny, nx, len(ln))
            graphics_state.write_text_grid(0, ny, ln, color)
        else:
            graphics_state.draw_highlight_grid(py + pt - nt, px, len(lp))
            graphics_state.write_text_grid(0, py + pt - nt, lp, color)
            graphics_state.draw_highlight_grid(ny, 0, nx)
            graphics_state.write_text_grid(0, ny, ln, color)

        start, end = (
            (py + pt, ny + nt), (ny + nt, py + pt))[(ny + nt) < (py + pt)]
        for n in range(start - nt + 1, end - nt):
            l = local_state.get_line(n + nt)
            graphics_state.draw_highlight_grid(n, 0, len(l) - 1)
            graphics_state.write_text_grid(0, n, l, color)

########NEW FILE########
__FILENAME__ = text_logic
from backend.interaction_managers import cursor_logic
from backend.command_list import COMMAND_MAP as c_map


def insert_text_str(s, local_state):
    """
    Insert string into line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(curr_top + y)
    local_state.set_line(curr_top + y, curr_line[:x] + s + curr_line[x:])
    local_state.set_cursor(x + len(s), y)


def insert_copy_buffer(local_state, global_state):
    """
    Insert multiple strings into line start at
    curr_top + y
    """
    x, y, curr_top = local_state.get_page_state()
    paste_txt = global_state.get_copy_buffer()

    if len(paste_txt):
        curr_line = local_state.get_line(curr_top + y)
        local_state.set_line(
            curr_top + y,
            curr_line[:x] + paste_txt[0].strip('\n') + curr_line[x:]
        )
        for i in range(len(paste_txt) - 1):
            local_state.add_line(curr_top + y + i + 1, paste_txt[i + 1])


def delete_text_highlight(local_state):
    """
    Splice out a single character from a line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(curr_top + y)
    local_state.set_line(curr_top + y, curr_line[:x] + curr_line[x + 1:])


def delete_current_line(local_state, global_state):
    """
    Functionality corresponding to dd in vim
    """
    x, y, curr_top = local_state.get_page_state()
    global_state.add_copy_buffer(
        [local_state.get_line(curr_top + y)]
    )
    local_state.remove_line(curr_top + y)
    local_state.set_cursor(0, y)


def insert_new_line_below(local_state):
    """
    Functionality corresponding to o in vim
    adds whitespace as well as newline character to
    match indent level of 'source' line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(curr_top + y)

    new_line = (' ' * (len(curr_line) - len(curr_line.lstrip()))) + '\n'
    local_state.add_line(y + curr_top + 1, new_line)
    local_state.set_cursor(len(curr_line) - len(curr_line.lstrip()), y + 1)


def insert_new_line_above(local_state):
    """
    Functionality corresponding to O in vim
    adds whitespace as well as newline character to
    match indent level of 'source' line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(curr_top + y)

    new_line = (' ' * (len(curr_line) - len(curr_line.lstrip()))) + '\n'
    local_state.add_line(y + curr_top, new_line)
    local_state.set_cursor(len(curr_line) - len(curr_line.lstrip()), y)


def shift_selection_right(local_state):
    """
    Implements functionality of > in vim
    by adding whitespace to beginning of each line
    TODO: Magic number whitespace, number of white space should
    be variable
    """
    px, py, pt = local_state.get_visual_anchors()
    nx, ny, nt = local_state.get_page_state()
    td = len(c_map['Tab'])

    start, end = (
        (py + pt, ny + nt), (ny + nt, py + pt))[(ny + nt) < (py + pt)]
    for n in range(start, end + 1):
        l = local_state.get_line(n)
        local_state.set_line(n, ' ' * td + l)


def shift_selection_left(local_state):
    """
    Implements functionality of < in vim
    by adding whitespace to beginning of each line
    TODO: Magic number whitespace, number of white space should
    be variable
    """
    px, py, pt = local_state.get_visual_anchors()
    nx, ny, nt = local_state.get_page_state()
    td = len(c_map['Tab'])

    start, end = (
        (py + pt, ny + nt), (ny + nt, py + pt))[(ny + nt) < (py + pt)]
    for n in range(start, end + 1):
        l = local_state.get_line(n)
        local_state.set_line(n, l[:td].strip() + l[td:])


def delete_text_char(local_state):
    """
    Delete single character in line
    Have to watch out for deleteing a
    character at the beginning of a line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(y + curr_top)

    if x > 0:
        local_state.set_line(curr_top + y, curr_line[:x - 1] + curr_line[x:])
        local_state.set_cursor(x - 1, y)
    elif y > 0 or curr_top > 0:
        if curr_line == '\n':
            local_state.remove_line(curr_top + y)
            local_state.set_cursor(0, y - 1)
            cursor_logic.move_cursor_end_line(local_state)
        else:
            prev_line = local_state.get_line(y + curr_top - 1)
            local_state.remove_line(curr_top + y)
            local_state.set_line(
                curr_top + y - 1,
                prev_line[:-1] + curr_line
            )  # slice off new line + last character
            local_state.set_cursor(len(prev_line) - 1, y - 1)


def delete_text_range(px, py, pt, nx, ny, nt, local_state):
    """
    Delete characters within given range by first finding the
    'final' x and y location of cursor and performing delete
    in that direction.
    final cursor location should be at fx, fy
    on which of ny + nt or py + pt comes first
    """
    fx, fy = ((px, py), (nx, ny))[(ny + nt) < (py + pt)]

    if py + pt == ny + nt:
        start, end = ((px, nx), (nx, px))[nx < px]
        curr_line = local_state.get_line(py + pt)
        local_state.set_line(py + pt, curr_line[:start] + curr_line[end:])
        local_state.set_cursor(start, py)
    else:
        start, end = (
            (py + pt, ny + nt), (ny + nt, py + pt))[(ny + nt) < (py + pt)]
        count = 0
        for n in range(start, end + 1):
            if (n == py + pt) and (px, py) == (fx, fy):
                local_state.set_line(n, local_state.get_line(n)[:px] + '\n')
            elif (n == py + pt) and (px, py) != (fx, fy):
                local_state.set_line(n, local_state.get_line(n)[px:])
            elif (n == ny + nt) and (nx, ny) == (fx, fy):
                local_state.set_line(n, local_state.get_line(n)[:nx] + '\n')
            elif (n == ny + nt) and (nx, ny) != (fx, fy):
                local_state.set_line(n, local_state.get_line(n)[nx:])
            else:
                count += 1

        for i in range(count):
            local_state.remove_line(start + 1)

        local_state.set_cursor(fx, fy)


def get_text_range(px, py, pt, nx, ny, nt, local_state):
    """
    Get text in given range arguments.
    Similar to delete text in range except strings
    are appended to a list and returned
    """
    txt = []
    fx, fy = ((nx, ny), (px, py))[(ny + nt) < (py + pt)]

    if py + pt == ny + nt:
        start, end = ((px, nx), (nx, px))[nx < px]
        curr_line = local_state.get_line(py + pt)
        txt.append(curr_line[start:end + 1])
    else:
        start, end = (
            (py + pt, ny + nt), (ny + nt, py + pt))[(ny + nt) < (py + pt)]
        for n in range(start, end + 1):
            if (n == py + pt) and (px, py) == (fx, fy):
                txt.append(local_state.get_line(n)[:px])
            elif (n == py + pt) and (px, py) != (fx, fy):
                txt.append(local_state.get_line(n)[px:])
            elif (n == ny + nt) and (nx, ny) == (fx, fy):
                txt.append(local_state.get_line(n)[:nx])
            elif (n == ny + nt) and (nx, ny) != (fx, fy):
                txt.append(local_state.get_line(n)[nx:])
            else:
                txt.append(local_state.get_line(n))
    return txt


def add_new_line_char(local_state):
    """
    Split line from x based on x coordinate of cursor,
    add a new line delimiter and append the rest of the
    string to the following line
    """
    x, y, curr_top = local_state.get_page_state()
    curr_line = local_state.get_line(y + curr_top)

    local_state.set_line(
        y + curr_top,
        curr_line[:x] + '\n'  # python string splicing doesn't index exceptions
    )
    local_state.add_line(y + curr_top + 1, curr_line[x:])

    local_state.set_cursor(0, y + 1)

########NEW FILE########
__FILENAME__ = instance
# All local file state is saved in an instance class
# Multiple files being open at the same time would correspond to
# multiple instance classes being open at the same time

import os
from copy import deepcopy
from backend.state.syntaxtokens import syntax_parser

class instance():

    def __init__(self, filename):
        self._filename = filename
        self._parser = syntax_parser.syntax_parser(filename)
        if os.path.exists(filename):
            self._lines = [
                line for line in open(filename, 'r')
            ]
            self._line_tokens = [
                self._parser.parse_string(line) for line in open(filename, 'r')
            ]
        else:
            self._lines = ['']
            self._line_tokens = ['']

        self._cursor_x, self._cursor_y, self._curr_top = 0, 0, 0
        self._visual_x, self._visual_y, self._visual_curr_top = 0, 0, 0
        self._undo_buffer, self._undo_index = [], -1
        self._marks = {}

    def dump_state_variables(self):
        return {
            'cx': self._cursor_x,
            'cy': self._cursor_y,
            'ct': self._curr_top,
            'vx': self._visual_x,
            'vy': self._visual_y,
            'vt': self._visual_curr_top
        }

    def check_repeat_additions(self, diff, last_state):
        return (
            diff[0] == '+' and last_state[0] == '+'
            and diff[1] == last_state[2]['last_addition'] + 1
        )

    def check_repeat_deletions(self, diff, last_state):
        return (
            diff[0] == '-' and last_state[0] == '-'
            and diff[1] == last_state[1]
        )

    def check_repeat_modifications(self, diff, last_state):
        return (
            diff[0] == 'm' and last_state[0] == 'm'
            and diff[1] == last_state[1]
        )

    def add_to_undo_buffer(self, diff):
        """
        Only add to undo buffer is move is not to be coalesced into
        previous undo block
        """
        if self._undo_index == len(self._undo_buffer) - 1:
            try:
                last_state = self._undo_buffer[self._undo_index]
            except IndexError:
                self._undo_buffer.append(diff)
                self._undo_index += 1
                return

            # repeat addtions to the same line
            if self.check_repeat_additions(diff, last_state):
                last_state[2]['count'] += 1
                last_state[2]['last_addition'] += 1
            # repeat deletions from the same line
            elif self.check_repeat_deletions(diff, last_state):
                last_state[2]['lines'].append(diff[2]['lines'][0])
                last_state[2]['line_tokens'].append(diff[2]['line_tokens'][0])
            # repeat modifications to the same line
            elif self.check_repeat_modifications(diff, last_state):
                last_state[2]['new']['line'] = \
                    diff[2]['new']['line']
                last_state[2]['new']['line_token'] = \
                    diff[2]['new']['line_token']
            else:
                self._undo_buffer.append(diff)
                self._undo_index += 1
                if len(self._undo_buffer) > 100:
                    self._undo_buffer.pop(0)
        else:
            self._undo_buffer = (
                self._undo_buffer[:self._undo_index] + [diff], [diff]
            )[self._undo_index == -1]
            self._undo_index += 1

    def undo_line_modification(self, diff):
        self._lines[diff[1]] = diff[2]['old']['line'][0]
        self._line_tokens[diff[1]] = diff[2]['old']['line_token'][0]

    def undo_line_addition(self, diff):
        for i in range(diff[2]['count']):
            self._lines.pop(diff[1])
            self._line_tokens.pop(diff[1])

    def undo_line_removal(self, diff):
        for i in range(len(diff[2]['lines'])):
            self._lines.insert(i + diff[1], diff[2]['lines'][i])
            self._line_tokens.insert(i + diff[1], diff[2]['line_tokens'][i])

    def undo_state(self):
        """
        Only undo if there is an action to undo
        set cursor and curr_top coordinates to saved coordinates
        """
        if self._undo_index != -1:
            # diff = self._undo_buffer.pop(-1)
            diff = self._undo_buffer[self._undo_index]
            self._undo_index -= 1
            if diff[0] == 'm':
                self.undo_line_modification(diff)
            elif diff[0] == '+':
                self.undo_line_addition(diff)
            elif diff[0] == '-':
                self.undo_line_removal(diff)

            (x, y, z) = diff[2]['state']
            self.set_curr_top(z)
            self.set_cursor(x, y)

    def redo_line_modification(self, diff):
        self._lines[diff[1]] = diff[2]['new']['line'][0]
        self._line_tokens[diff[1]] = diff[2]['new']['line_token'][0]

    def redo_line_addition(self, diff):
        for i in range(diff[2]['count']):
            self._lines.insert(diff[1] + i, diff[2]['data']['lines'][i])
            self._line_tokens.insert(
                diff[1] + i, diff[2]['data']['line_tokens'][i]
            )

    def redo_line_removal(self, diff):
        for i in range(len(diff[2]['lines'])):
            self._lines.pop(diff[1])
            self._line_tokens.pop(diff[1])

    def redo_state(self):
        """
        Only redo if there is an action to redo
        """
        if self._undo_index < len(self._undo_buffer) - 1:
            self._undo_index += 1
            diff = self._undo_buffer[self._undo_index]
            if diff[0] == 'm':
                self.redo_line_modification(diff)
            if diff[0] == '+':
                self.redo_line_addition(diff)
            if diff[0] == '-':
                self.redo_line_removal(diff)

    def get_line(self, index):
        return self._lines[index]

    # line numbers are 0 indexed
    def get_lines(self):
        return self._lines

    def get_line_tokens(self):
        return self._line_tokens

    def get_cursor(self):
        return self._cursor_x, self._cursor_y

    def get_curr_top(self):
        return self._curr_top

    def get_line_height(self):
        return self._line_height

    def get_line_num(self):
        return len(self._lines)

    def get_filename(self):
        return self._filename

    def get_page_state(self):
        return self._cursor_x, self._cursor_y, self._curr_top

    def get_visual_anchors(self):
        return self._visual_x, self._visual_y, self._visual_curr_top

    def get_mark(self, buf):
        if buf in self._marks:
            return self._marks[buf]
        else:
            return None

    def set_mark(self, buf, loc):
        self._marks[buf] = loc

    def add_line(self, index, line):
        """
        Save lines added in memory so undo and
        redo can be performed
        """
        try:
            li = self._lines[index]
            lt = self._line_tokens[index]
        except IndexError:
            li = ''
            lt = self._parser.parse_string('')

        d = {
            'count': 1,
            'data': {
                'lines': [li],
                'line_tokens': [lt],
            },
            'state': self.get_page_state(),
            'last_addition': index,
        }

        # self.add_to_undo_buffer(('+', index, d))
        self._lines.insert(index, line)
        self._line_tokens.insert(index, self._parser.parse_string(line))

    def remove_line(self, index):
        """
        Save lines removed in memory so undo and
        redo can be performed
        """
        d = {
            'lines': [self._lines[index]],
            'line_tokens': [self._line_tokens[index]],
            'state': self.get_page_state(),
        }
        # self.add_to_undo_buffer(('-', index, d))
        self._lines.pop(index)
        self._line_tokens.pop(index)

    def set_curr_top(self, num):
        self._curr_top = num

    def set_line_height(self, num):
        self._line_height = num

    def set_line(self, ind, s):
        """
        Create dict of diff data and add it to
        undo buffer. Pick string depending upon
        undo or redo action
        """
        parsed = self._parser.parse_string(s)
        d = {
            'old': {
                'line': [self._lines[ind]],
                'line_token': [self._line_tokens[ind]]
            },
            'new': {
                'line': [s],
                'line_token': [parsed],
            },
            'state': self.get_page_state()
        }

        # self.add_to_undo_buffer(('m', ind, d))
        self._lines[ind] = s
        self._line_tokens[ind] = parsed

    def set_visual_anchor(self, x=None, y=None, curr_top=None):
        """
        Set anchors to cursor and curr_top values if no
        arguments ar passed in
        """
        self._visual_x = x if x is not None else self._cursor_x
        self._visual_y = y if y is not None else self._cursor_y
        self._visual_curr_top = \
            curr_top if curr_top is not None else self._curr_top

    def set_cursor(self, x, y):
        """
        Set cursor while making sure cursor x and cursor y
        never get invalid values
        """
        self._cursor_x = max(x, 0)
        if y > self._line_height:
            self._curr_top += (y - self._line_height)
            self._cursor_y = self._line_height
        elif y < 0:
            self._curr_top = max(self._curr_top + y, 0)
            self._cursor_y = 0
        else:
            self._cursor_y = y

########NEW FILE########
__FILENAME__ = color_config
options = {
    'background_color': '#002B36',
    'text_color': '#839496',
    'status_text_color': '#002B36',
    'status_background_color': '#657b83',
    'text_highlight_color': '#657b83',
    'line_num_highlight_color': '#073642',
    'line_num_text_color': '#839496',
    'cursor_highlight_color': '#073642',
    'cursor_color': '#7C6B69',
    'function_name_color': '#268bd2',
    'namespace_color': '#dc322f',
    'keyword_color': '#859900',
    'string_color': '#2aa198',
    'comment_color': '#586e75'
}

########NEW FILE########
__FILENAME__ = syntax_parser
# Syntax parsing module using pygments
# This module needs a lot of work
# Potentially this can be sped up even more
# if we roll our own syntax parser since
# there would be no need for parsing each line over and over
# TODO: Discuss alternatives to this module. (maybe this might need to be scrapped entirely and rewritten
# TODO: Make syntax highlighter work for things that aren't python

from pygments import lex
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token
from backend.state.syntaxtokens.color_config import options


class syntax_parser():

    def __init__(self, filename):
        """
        init by getting a lexer for file name
        If none exist set lexer to dummy which will be
        caught in parse
        """
        try:
            self.lexer = get_lexer_for_filename(filename)
        except:
            self.lexer = None

    def parse_string(self, s):
        """
        Parse string using lexer, if none exists
        return string with default text color
        """
        start = 0
        ret_list = []
        if self.lexer is None:
            return ([(0, s, options['text_color'])])

        for token in lex(s, self.lexer):
            color = self.determine_color(token[0])
            ret_list.append((start, token[1], color))
            start += len(token[1])
        return ret_list

    def determine_color(self, t):
        """
        This can be sped up by putting it into a preloaded dict
        """
        if t is Token.Name.Class or t is Token.Name.Function:
            return options['function_name_color']
        elif t is Token.Keyword or t is Token.Keyword.Declaration:
            return options['keyword_color']
        elif t is Token.String or t is Token.Literal.String.Interpol or t is Token.Literal.String.Single:
            return options['string_color']
        elif t is Token.Comment or t is Token.Literal.String.Doc:
            return options['comment_color']
        elif t is Token.Keyword.Namespace:
            return options['namespace_color']
        else:
            return options['text_color']

########NEW FILE########
__FILENAME__ = syntax_test
# an attempt to approximate of pygments parser runtime
from pygments import lex
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token
from color_config import options


def determine_color(t):
    print(t)
    if t is Token.Name.Class or t is Token.Name.Function:
        return options['function_name_color']
    elif t is Token.Keyword:
        return options['keyword_color']
    elif t is Token.String or t is Token.Literal.String.Interpol:
        return options['string_color']
    elif t is Token.Comment:
        return options['comment_color']
    elif t is Token.Keyword.Namespace:
        return options['namespace_color']
    else:
        return options['text_color']


l = get_lexer_for_filename('test.c')


def parse(s, l):
    ret_list = []
    start = 0
    for token in lex(s, l):
        color = determine_color(token[0])
        ret_list.append((start, token[1], color))
        start += len(token[1])
    print(ret_list)


# time1 = time.time()
# parse('i', l)
# parse('im', l)
# parse('imp', l)
# parse('impo', l)
# parse('impor', l)
# parse('import', l)
# parse('import test from lol', l)
# parse('def wat(lolblah):', l)
# parse('for line in gg:', l)
# parse('for lin in gg:', l)
# parse('for li in gg:', l)
# parse('for l in gg:', l)
# time2 = time.time()
# print 'function took %0.3f ms' % ((time2-time1)*1000.0)


parse('static int A_is_a(int cur_c)', l)

########NEW FILE########
__FILENAME__ = token_dump
# dump all pygments tokens into a text file to determine
# how pygments assigns tokens to various files

from pygments import lex
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token

from argparse import ArgumentParser


def opt_init():
    """To parse option command line"""
    parser = ArgumentParser(description='token dump test')
    parser.add_argument(dest='filename', action='store',
                        metavar='FILE', nargs='?')
    parser.add_argument(
        '-out', dest='out', nargs='?',
        default=None
    )
    return parser

if __name__ == '__main__':
    parser = opt_init()
    args = parser.parse_args()
    if args.filename:
        filename = args.filename
        lexer = get_lexer_for_filename(filename)
        out = ''

        txt = open(filename, 'r').read()
        for token in lex(txt, lexer):
            out += str(token) + '\n'

        if args.out:
            with open(args.out, 'w') as f:
                f.write(out)
                print('token dump located at %s' % (args.out))
        else:
            print(out)
    else:
        print('missing filename argument')

########NEW FILE########
__FILENAME__ = user_input
# Entry point for user input
# Events are bound in graphics intialization to user_input instance
# Events are coerced into a usable form and passed into
# user_input.user_key_pressed
#
# parsed commands are passed in list form over to interaction_manager.py
# the interaction_manager should not have to handle raw user input

import re
from copy import deepcopy
from backend.state import instance
from backend import command_list
from backend import interaction_manager
from backend.commandparser import command_parser

DEFAULT_MOVEMENTS = command_list.DEFAULT_MOVEMENTS
DEFAULT_COMMAND_LEADERS = command_list.DEFAULT_COMMAND_LEADERS
VISUAL_MOVEMENTS = command_list.VISUAL_MOVEMENTS
DEFAULT_BREAK_MOVEMENTS = command_list.DEFAULT_BREAK_MOVEMENTS
VISUAL_BREAK_MOVEMENTS = command_list.VISUAL_BREAK_MOVEMENTS
COMMAND_MAP = command_list.COMMAND_MAP


class user_input():

    def __init__(self):
        self._graphics = None
        self._curr_state, self._command_buffer = 'Default', ''
        self._instances, self._copy_buffer, self._curr_instance = [], [], 0
        self._default_parser = command_parser.parser('default')
        self._ex_parser = command_parser.parser('ex')

    def start_instance(self, filename):
        self._instances.append(instance.instance(filename))

    def set_GUI_reference(self, canvas):
        """
        Set graphics reference for particular instance and render page
        This should really only be done once per instace
        """
        self._graphics = canvas
        self._instances[self._curr_instance].set_line_height(
            self._graphics.get_line_height())
        interaction_manager.render_page(
            self._graphics,
            self.get_curr_instance(), self)

    def add_copy_buffer(self, l):
        self._copy_buffer = l

    def dump_state_variables(self):
        """
        Dump state variables for unit testing
        """
        return {
            'curr_st': self._curr_state,
            'local_st_ref': self._instances[self._curr_instance],
            'cmd_buffer': self._command_buffer,
            'cpy_buffer': self._copy_buffer,
            'local_states': self._instances,
        }

    def set_curr_state(self, s):
        self._curr_state = s

    def get_curr_instance(self):
        return self._instances[self._curr_instance]

    def get_copy_buffer(self):
        return self._copy_buffer

    def get_curr_state(self):
        return self._curr_state

    def get_command_buffer(self):
        return self._command_buffer

    def go_next_instance(self):
        """
        Go to next instance if there is one available
        """
        if self._curr_instance < len(self._instances) - 1:
            self._curr_instance += 1
            self.set_GUI_reference(self._graphics)

    def go_prev_instance(self):
        """
        Go to previous instance if there is one available
        """
        if self._curr_instance > 0:
            self._curr_instance -= 1
            self.set_GUI_reference(self._graphics)

    def is_digit(self, k):
        """
        checks if key input an integer greater than 0 and less than 10
        """
        return (len(k) == 1) and (ord(k) >= 49 and ord(k) <= 57)

    def key(self, event):
        key = event.keysym
        if key != '??':
            if len(key) > 1:  # length > 1 if not alphanumeric
                try:
                    k = COMMAND_MAP[key]
                    self.user_key_pressed(k)
                except KeyError:
                    pass
            else:
                self.user_key_pressed(key)

    def control_a(self, event):
        self.user_key_pressed('<Control-a>')

    def control_b(self, event):
        self.user_key_pressed('<Control-b>')

    def control_c(self, event):
        self.user_key_pressed('<Control-c>')

    def control_d(self, event):
        self.user_key_pressed('<Control-d>')

    def control_e(self, event):
        self.user_key_pressed('<Control-e>')

    def control_f(self, event):
        self.user_key_pressed('<Control-f>')

    def control_g(self, event):
        self.user_key_pressed('<Control-g>')

    def control_h(self, event):
        self.user_key_pressed('<Control-h>')

    def control_i(self, event):
        self.user_key_pressed('<Control-i>')

    def control_j(self, event):
        self.user_key_pressed('<Control-j>')

    def control_k(self, event):
        self.user_key_pressed('<Control-k>')

    def control_l(self, event):
        self.user_key_pressed('<Control-l>')

    def control_m(self, event):
        self.user_key_pressed('<Control-m>')

    def control_n(self, event):
        self.user_key_pressed('<Control-n>')

    def control_o(self, event):
        self.user_key_pressed('<Control-o>')

    def control_p(self, event):
        self.user_key_pressed('<Control-p>')

    def control_q(self, event):
        self.user_key_pressed('<Control-q>')

    def control_r(self, event):
        self.user_key_pressed('<Control-r>')

    def control_s(self, event):
        self.user_key_pressed('<Control-s>')

    def control_t(self, event):
        self.user_key_pressed('<Control-t>')

    def control_u(self, event):
        self.user_key_pressed('<Control-u>')

    def control_v(self, event):
        self.user_key_pressed('<Control-v>')

    def control_w(self, event):
        self.user_key_pressed('<Control-w>')

    def control_x(self, event):
        self.user_key_pressed('<Control-x>')

    def control_y(self, event):
        self.user_key_pressed('<Control-y>')

    def control_z(self, event):
        self.user_key_pressed('<Control-z>')

    def control_braceright(self, event):
        self.user_key_pressed('<Control-braceright>')

    def control_braceleft(self, event):
        self.user_key_pressed('<Control-braceleft>')

    def escape(self, event):
        self._curr_state = 'Default'
        self._command_buffer = ''
        interaction_manager.render_page(
            self._graphics, self._instances[self._curr_instance], self)

    def mouse_scroll(self, event):
        """
        Scroll mouse depending on direction moved by
        calling cursor up or cursor down repeatedly.
        TODO: This is clearly not optimal. The calling
        move_cursor_up or down re-renders the page repeatedly and
        is inefficient
        """
        delta = event.delta * -1
        self._curr_state = 'Default'
        self._command_buffer = ''
        cmd = ['n' + str(delta), 'mouse_scroll']
        interaction_manager.input_command(
            cmd, self._graphics, self.get_curr_instance(), None)

    def user_key_pressed(self, key):
        """
        Main input router. Routes key input to appropriate
        key handlers dependent upon global state
        """
        if self._curr_state == 'Default':
            self.user_key_default(key)
        elif self._curr_state == 'Insert':
            self.user_key_insert(key)
        elif self._curr_state == 'Visual':
            self.user_key_visual(key)
        elif self._curr_state == 'Ex':
            self.user_key_ex(key)
        elif self._curr_state == 'fuzzy_file_selection':
            self.user_key_fuzzy_file_select(key)

    def init_insert_mode(self):
        self._curr_state = 'Insert'

    def init_ex_mode(self):
        self._curr_state = 'Ex'

    def init_visual_mode(self):
        # set once and then never mutate this ever again per visual selection
        self.get_curr_instance().set_visual_anchor()
        self._curr_state = 'Visual'

    def user_key_default(self, key):
        """
        Handle keys in default mode
        """
        mode_dict = {
            'i': self.init_insert_mode,
            'v': self.init_visual_mode,
            ':': self.init_ex_mode,
        }

        if key in DEFAULT_COMMAND_LEADERS \
            or self.is_digit(key) \
                or len(self._command_buffer):
            self._command_buffer += key
            s_par = self._default_parser.parse_string(
                self._command_buffer
            )

            if s_par != '' or key in DEFAULT_BREAK_MOVEMENTS:
                cmd = s_par if s_par != '' else DEFAULT_BREAK_MOVEMENTS[key]
                interaction_manager.input_command(
                    cmd, self._graphics, self.get_curr_instance(), self)
                self._command_buffer = ''

        elif key in DEFAULT_MOVEMENTS:  # default movement requested
            interaction_manager.input_command(
                DEFAULT_MOVEMENTS[key], self._graphics,
                self.get_curr_instance(), self
            )
            self._command_buffer = ''
        elif key in mode_dict:  # mode change requested
            mode_dict[key]()

    def user_key_insert(self, key):
        """
        Handle keys in insert mode

        This should be the only state that should contain
        at least these mappings no matter the configuration
        """
        if key not in ['BackSpace', 'Return']:
            cmd = ['s' + key, 'insert_text']
            interaction_manager.input_command(
                cmd, self._graphics,
                self.get_curr_instance(), self
            )
        elif key == 'BackSpace':
            interaction_manager.input_command(
                ['delete_char'], self._graphics,
                self.get_curr_instance(), self
            )
        # similar to above
        elif key == 'Return':
            interaction_manager.input_command(
                ['add_new_line'], self._graphics,
                self.get_curr_instance(), self
            )

    def user_key_visual(self, key):
        """
        Handle keys in visual mode
        TODO: expand this section to handle multi command
        arguments
        i.e finds should work in visual mode
        Dependent upon a proper command parser however
        """
        if key in VISUAL_MOVEMENTS:
            motion = VISUAL_MOVEMENTS[key]
            cmd = ['s' + motion[0], 'visual_movement']
            interaction_manager.input_command(
                cmd, self._graphics,
                self.get_curr_instance(), self
            )
            self._command_buffer = ''
        elif key in VISUAL_BREAK_MOVEMENTS:
            cmd = VISUAL_BREAK_MOVEMENTS[key]
            interaction_manager.input_command(
                cmd, self._graphics,
                self.get_curr_instance(), self
            )
            self._command_buffer = ''

    def user_key_ex(self, key):
        """
        Handle keys in ex mode
        TODO: expand this section to handle multi command
        arguments
        i.e finds should work in visual mode
        Dependent upon a proper command parser however

        This mode is kind of limited for now since we don't
        have a proper command parser yet
        """
        if key == 'Return':
            cmd = self._ex_parser.parse_string(self._command_buffer)
            interaction_manager.input_command(
                cmd, self._graphics,
                self.get_curr_instance(), self
            )
            self._curr_state = 'Default'
            self._command_buffer = ''
        else:
            self._command_buffer = (
                self._command_buffer + key,
                self._command_buffer[:-1]
            )[key == 'BackSpace']

            interaction_manager.render_page(
                self._graphics,
                self.get_curr_instance(), self
            )

########NEW FILE########
__FILENAME__ = server
# Server logic for shim backend
# Simple TCP server to handling get and post requests
# Current Shim backend should be able to hook into this

import cgi
import json
import http.server
import socketserver
from http.server import BaseHTTPRequestHandler

PORT = 10003
KEEP_RUNNING = True

class request_handler(BaseHTTPRequestHandler):
    def _respond(self, s):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-length", len(s))
        self.end_headers()
        self.wfile.write(bytes(s, "utf-8"))

    def _parse_post(self):
        ctype, pdict = cgi.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            postvars = {}
        return postvars

    def do_GET(self):
        self._respond('wat')

    def do_POST(self):
        print(self._parse_post())
        self._respond('wat')


class server(socketserver.TCPServer):
    def server_bind(self):
        self.allow_reuse_address = True
        super(server, self).server_bind()


if __name__ == '__main__':
    Handler = request_handler
    httpd = server(('localhost', PORT), Handler)

    print("serving at port", PORT)

    while KEEP_RUNNING:
        httpd.handle_request()

########NEW FILE########
__FILENAME__ = build
import os

os.system('zip -r app.nw *')

########NEW FILE########
__FILENAME__ = text_canvas
# Main class for handling graphics
# all api's related to graphics should be called
# from this class
# TODO: Discuss what kind of functions this class
# should provide

from tkinter import Canvas, BOTH
from tkinter.ttk import Frame
import tkinter.font as tkFont
from backend.state.syntaxtokens.color_config import options


class text_canvas(Frame):

    def __init__(self, parent, font_size, input_handler, filename):
        Frame.__init__(self, parent)
        self._parent = parent
        self._text_font = tkFont.Font(
            family='Monaco', size=font_size, weight='bold'
        )
        self._filename = filename
        self._cheight, self._cwidth = font_size, self._text_font.measure('c')
        self._line_num_spacing = (self.get_num_spacing() * self._cwidth) + 20
        self._line_height = (
            (self.winfo_screenheight() - self._cheight)//(self._cheight + 2) - 4
        )
        self.init_UI(input_handler)

    def init_UI(self, input_handler):
        self._parent.title('')
        self.pack(fill=BOTH, expand=1)
        self.init_canvas(input_handler)

    def dump_state_variables(self):
        return {
            'filename': self._filename,
            'cheight': self._cheight,
            'cwidth': self._cwidth,
            'line_num_spacing': self._line_num_spacing,
            'line_height': self._line_height,
            'screen_width': self.winfo_screenwidth(),
            'screen_height': self.winfo_screenheight()
        }

    def get_dimensions(self):
        """
        Getting the dimensions might be helpful
        for plugin writers
        """
        return {
            'cheight': self._cheight,
            'cwidth': self._cwidth,
            'line_num_spacing': self._line_num_spacing,
            'line_height': self._line_height,
            'screen_width': self.winfo_screenwidth(),
            'screen_height': self.winfo_screenheight()
        }

    def get_num_spacing(self):
        n = sum(1 for line in open(self._filename))
        return len(str(n))

    def get_line_height(self):
        return self._line_height

    def init_canvas(self, input_handler):
        self._canvas = Canvas(
            self, highlightthickness=0, width=self.winfo_screenwidth(),
            height=self.winfo_screenheight(), bg=options['background_color']
        )
        self._canvas.pack()
        self._canvas.focus_set()
        self.bind_events(input_handler)

    def clear_all(self):
        self._canvas.delete('all')

    def get_line_height(self):
        """
        return number of lines per page
        """
        return self._line_height

    def get_grid_y(self, y):
        """
        return character height * y
        in addition distane of the spaces inbetwen
        """
        return self._cheight * y + (y * 2)

    def write_line_grid(self, y, line):
        """
        Write to line of text on grid using tokens passed in
        """
        for token in line:
            self.write_text_grid(token[0], y, token[1], token[2])

    def write_text_grid(self, x, y, text, color=options['text_color']):
        """
        Write text to x, y location on grid
        """
        x_val = self._cwidth * x + self._line_num_spacing
        y_val = self._cheight * y + (y * 2)  # 2 pixel spacing between each line
        self._canvas.create_text(
            x_val, y_val, anchor='nw', text=text,
            font=self._text_font, fill=color
        )

    def write_status_line(
        self, text, textcolor=options['status_text_color'],
        backgroundcolor=options['status_background_color']
    ):
        """
        Writen a line of text to status line
        this function could take in different data if desired
        """
        y = self._line_height + 1
        self._canvas.create_rectangle(
            0, self._cheight * y + (y * 2), self.winfo_screenwidth(),
            self._cheight * y + (y * 2) + self._cheight + 4,
            fill=backgroundcolor, outline=backgroundcolor
        )
        self.write_text_grid(0, self._line_height + 1, text, textcolor)

    def draw_highlight_grid(
        self, y, x1, x2,
        highlightcolor=options['text_highlight_color']
    ):
        """
        Draw highlights onto text canvas
        i.e selections during visual mode
        """
        y_val = self._cheight * y + (y * 2)
        x1_val = self._cwidth * x1 + self._line_num_spacing
        x2_val = self._cwidth * x2 + self._line_num_spacing
        self._canvas.create_rectangle(
            x1_val, y_val, x2_val, y_val + self._cheight + 4,
            fill=highlightcolor, outline=highlightcolor
        )

    def draw_line_numbers(
        self, start,
        highlightcolor=options['line_num_highlight_color'],
        textcolor=options['line_num_text_color']
    ):
        self._canvas.create_rectangle(
            0, 0, self._line_num_spacing - 20,
            self.winfo_screenheight(),
            fill=highlightcolor, outline=highlightcolor
        )
        for i in range(self._line_height + 1):
            self._canvas.create_text(
                0, self._cheight * i + (i * 2), anchor='nw',
                text=str(start + i), font=self._text_font,
                fill=textcolor
            )

    def draw_cursor(
        self, x, y,
        highlightcolor=options['cursor_highlight_color'],
        cursorcolor=options['cursor_color']
    ):
        """
        draw cursor as well as line and column highlights
        TODO: users should have the option to disable line
        and column highlights
        """
        x_val = self._cwidth * x + self._line_num_spacing
        y_val = self._cheight * y + (y * 2)

        self._canvas.create_rectangle(
            0, y_val, self.winfo_screenwidth(),
            y_val + self._cheight + 4,
            fill=highlightcolor, outline=highlightcolor
        )
        self._canvas.create_rectangle(
            x_val, 0, x_val + self._cwidth,
            self.winfo_screenheight(), fill=highlightcolor,
            outline=highlightcolor
        )
        self._canvas.create_rectangle(
            x_val, y_val, x_val + self._cwidth,
            y_val + self._cheight + 4,
            fill=cursorcolor, outline=cursorcolor
        )

    def draw_rectangle_absolute(
        self, x1, y1, x2, y2, color
    ):
        """
        draw rectangle onto screen
        TODO: flesh out what this function should actually
        look like
        """
        self._canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color, outline=color
        )

    def bind_events(self, input_handler):
        """
        bind events for use in input_handler
        TODO: this should be cleaned up ideally into a separate handler list
        TODO: control commands also emit their corresponding key events. I.E
        the '<Control-f>' also emits the 'f' key event. That'll cause conflicts
        between move half page and find character. 
        """
        input_handler.set_GUI_reference(self)
        self._canvas.bind('<Key>', input_handler.key)
        self._canvas.bind_all('<Escape>', input_handler.escape)
        self._canvas.bind_all('<Control-a>', input_handler.control_a)
        self._canvas.bind_all('<Control-b>', input_handler.control_b)
        self._canvas.bind_all('<Control-c>', input_handler.control_c)
        self._canvas.bind_all('<Control-d>', input_handler.control_d)
        self._canvas.bind_all('<Control-e>', input_handler.control_e)
        self._canvas.bind_all('<Control-f>', input_handler.control_f)
        self._canvas.bind_all('<Control-g>', input_handler.control_g)
        self._canvas.bind_all('<Control-h>', input_handler.control_h)
        self._canvas.bind_all('<Control-i>', input_handler.control_i)
        self._canvas.bind_all('<Control-j>', input_handler.control_j)
        self._canvas.bind_all('<Control-k>', input_handler.control_k)
        self._canvas.bind_all('<Control-l>', input_handler.control_l)
        self._canvas.bind_all('<Control-m>', input_handler.control_m)
        self._canvas.bind_all('<Control-n>', input_handler.control_n)
        self._canvas.bind_all('<Control-o>', input_handler.control_o)
        self._canvas.bind_all('<Control-p>', input_handler.control_p)
        self._canvas.bind_all('<Control-q>', input_handler.control_q)
        self._canvas.bind_all('<Control-r>', input_handler.control_r)
        self._canvas.bind_all('<Control-s>', input_handler.control_s)
        self._canvas.bind_all('<Control-t>', input_handler.control_t)
        self._canvas.bind_all('<Control-u>', input_handler.control_u)
        self._canvas.bind_all('<Control-v>', input_handler.control_v)
        self._canvas.bind_all('<Control-w>', input_handler.control_w)
        self._canvas.bind_all('<Control-x>', input_handler.control_x)
        self._canvas.bind_all('<Control-y>', input_handler.control_y)
        self._canvas.bind_all('<Control-z>', input_handler.control_z)
        self._canvas.bind_all("<MouseWheel>", input_handler.mouse_scroll)
        self._canvas.bind_all(
            '<Control-braceright>', input_handler.control_braceright
        )
        self._canvas.bind_all(
            '<Control-braceleft>', input_handler.control_braceleft
        )

########NEW FILE########
__FILENAME__ = interaction
# yanked from: http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
def calculate_edit_distance(s1, s2):
    oneago = None
    thisrow = list(range(1, len(s2) + 1)) + [0]
    for x in range(len(s1)):
        twoago, oneago, thisrow = oneago, thisrow, [0] * len(s2) + [x + 1]
        for y in range(len(s2)):
            delcost = oneago[y] + 1
            addcost = thisrow[y - 1] + 1
            subcost = oneago[y - 1] + (s1[x] != s2[y])
            thisrow[y] = min(delcost, addcost, subcost)
    return thisrow[len(s2) - 1]


def sort_files(s, files):
    files = [(k, v, calculate_edit_distance(k, s)) for k, v in files]
    files = sorted(files, key=lambda x: x[2])
    return files


# plugins have access to all state variables in the text editor
def draw_matching_file_names(graphics_state, local_state, global_state):
    dims = graphics_state.get_dimensions()
    graphics_state.draw_rectangle_absolute(0, 0, dims['screen_width'],
                                           graphics_state.get_grid_y(21),
                                           '#657b83')

    _, vy, _ = local_state.get_visual_anchors()
    graphics_state.draw_rectangle_absolute(
        0, graphics_state.get_grid_y(vy - 1),
        dims['screen_width'], graphics_state.get_grid_y(vy), '#dc322f')

    files = sort_files(
        global_state.command_buffer, list(
            local_state.get_meta_data()['fuzzy_file_select'].items()))

    graphics_state.write_text_grid(0, 0,
                                   global_state.command_buffer,
                                   color='#002B36')

    for i in range(20):
        graphics_state.write_text_grid(0, i + 1, files[i][0], color='#002B36')


# router calls this logic
def fuzzy_file_select(s, graphics_state, local_state, global_state):
    post = [lambda:draw_matching_file_names(
        graphics_state, local_state, global_state)]
    render_page([], post, graphics_state, local_state, global_state)


# router calls this logic
def fuzzy_file_enter(graphics_state, local_state, global_state):
    _, vy, _ = local_state.get_visual_anchors()
    filename = sort_files(global_state.command_buffer, list(
        local_state.get_meta_data()['fuzzy_file_select'].items()))[vy - 2][0]

    global_state.start_instance(filename)
    global_state.curr_instance += 1
    global_state.set_GUI_reference(graphics_state)

########NEW FILE########
__FILENAME__ = interaction_routes
    'fuzzy_file_select': fuzzy_file_select,
    'fuzzy_file_enter': fuzzy_file_enter,

########NEW FILE########
__FILENAME__ = metadata
import os


def write_data(dirname, file_data, dir_info):
    paths = []

    for dname, _, filenames in dir_info:
        for filename in filenames:
            if filename not in ['.shimdata']:
                paths.append(os.path.join(dname, filename))

    for path in paths:
        try:
            file_data['fuzzy_file_select'][os.path.relpath(path,
                                                           dirname)] = path
        except KeyError:
            file_data['fuzzy_file_select'] = {
                os.path.relpath(path, dirname): path}

########NEW FILE########
__FILENAME__ = user_input
def init_fuzzy_matching(self):
    if self.curr_state != 'fuzzy_file_selection':
        self.curr_state = 'fuzzy_file_selection'
        self.command_buffer = ''
        self.get_curr_instance().set_visual_anchor(y=2)
        cmd = ['s' + self.command_buffer, 'fuzzy_file_select']
        interaction_manager.input_command(cmd, self.graphics,
                                          self.get_curr_instance(), self)


def user_key_fuzzy_file_select(self, key):
    if key == 'Return':
        self.command_buffer = ''
        self.curr_state = 'Default'
        cmd = ['fuzzy_file_enter']
    elif key == 'BackSpace':
        self.command_buffer = self.command_buffer[:-1]
        cmd = ['s' + self.command_buffer, 'fuzzy_file_select']
    elif key == '<Up>' or key == '<Down>':
        inst = self.get_curr_instance()
        _, vy, _ = inst.get_visual_anchors()
        vy = vy + 1 if key == '<Down>' else vy - 1
        vy = min(21, max(vy, 2))
        inst.set_visual_anchor(y=vy)
        cmd = ['s' + self.command_buffer, 'fuzzy_file_select']
    else:
        self.command_buffer += key
        cmd = ['s' + self.command_buffer, 'fuzzy_file_select']

    interaction_manager.input_command(cmd, self.graphics,
                                      self.get_curr_instance(), self)

########NEW FILE########
__FILENAME__ = user_input_routes
'<Control-p>': self.init_fuzzy_matching

########NEW FILE########
__FILENAME__ = loader_prototype
"""
Prototype code for the plugin loader
More design on how plugin code should be handled in shim needs to be done
"""

from optparse import OptionParser
import os

parser = OptionParser()


# option parsing logic, adds options for names and group information
def opt_init():
    parser.add_option('-d', '--dir_name', dest='dir_name',
                      type='string', help='Name of plugin folder to process')


def load_content_data(dir_name):
    lines = [line for line in open(os.path.join(dir_name, 'package'), 'r')]
    for line in lines:
        # this is hardcoded for now, this can change in the future.
        # Right now there isn't much to save in the package file
        if line.startswith('package_name'):
            return line.split(':')[-1].strip()


def remove_plugin_code(lines, start_dlist, end_dlist):
    dall = False
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] in end_dlist:
            dall = False
        elif lines[i] in start_dlist:
            dall = True
        elif dall:
            lines.pop(i)


def add_plugin_code(lines, add_map, stop_list):
    add_s = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] in add_map:
            add_s = add_map[lines[i]]
        elif lines[i] in stop_list:
            add_s = None
        if add_s is not None:
            lines.insert(i, add_s)


# this is not how it should look like in the end
# But for demonstration purposes I think it works just fine
def fill_metadata_loader(dir_name, package_name):
    fn = package_name + '_meta.py'

    with open(os.path.join(dir_name, 'metadata.py'), 'r') as c:
        contents = c.read()
        with open(os.path.join('plugins', fn), 'w') as f:
            f.write(contents)

    lines = [line for line in open('metadata.py', 'r')]
    start_dlist = set([
        '# END code-generated list of module imports\n',
        '        # END code-generated list of modules to call write_data\n'])
    end_dlist = set([
        '# BEGIN code-generated list of module imports\n',
        '        # BEGIN code-generated list of modules to call write_data\n'])

    remove_plugin_code(lines, start_dlist, end_dlist)
    ipn = package_name + '_meta'

    add_map = {
        '# END code-generated list of module imports\n': 'from plugins import %s\n' % (ipn),
        '        # END code-generated list of modules to call write_data\n': '        MODULES = [%s]\n' % (ipn),
    }
    stop_list = set(['# BEGIN code-generated list of module imports\n', '        # BEGIN code-generated list of modules to call write_data\n'])

    add_plugin_code(lines, add_map, stop_list)

    with open('metadata.py', 'w') as f:
        f.write(''.join(lines))


def fill_interaction_manager(dir_name, package_name):
    lines = [line for line in open('Backend/interaction_manager.py', 'r')]
    start_dlist = set([
        '# END PLUGIN DEFINED FUNCTIONS HERE\n',
        '    # END PLUGIN DEFINED REFERENCES HERE\n'])
    end_dlist = set([
        '# BEGIN PLUGIN DEFINED FUNCTIONS HERE\n',
        '    # BEGIN PLUGIN DEFINED REFERENCES HERE\n'])

    remove_plugin_code(lines, start_dlist, end_dlist)

    add_map = {
        '# END PLUGIN DEFINED FUNCTIONS HERE\n': open(os.path.join(dir_name, 'interaction.py'), 'r').read(),
        '    # END PLUGIN DEFINED REFERENCES HERE\n': open(os.path.join(dir_name, 'interaction_routes.py'), 'r').read(),
    }

    stop_list = set(['# BEGIN PLUGIN DEFINED FUNCTIONS HERE\n', '    # BEGIN PLUGIN DEFINED REFERENCES HERE\n'])

    add_plugin_code(lines, add_map, stop_list)

    with open('Backend/interaction_manager.py', 'w') as f:
        f.write(''.join(lines))


def fill_user_input(dir_name, package_name):
    lines = [line for line in open('Backend/user_input.py', 'r')]
    start_dlist = set([
        '    # END BEGIN PLUGIN DEFINED ROUTING FUNCITONS HERE\n',
        '        # END MODE CHANGE MAPPINGS HERE\n'])
    end_dlist = set([
        '    # BEGIN PLUGIN DEFINED ROUTING FUNCITONS HERE\n',
        '        # BEGIN MODE CHANGE MAPPINGS HERE\n'])

    remove_plugin_code(lines, start_dlist, end_dlist)

    dictstr =  "        mode_dict = { 'i': self.init_insert_mode, 'v': self.init_visual_mode, ':': self.init_ex_mode, %s }\n" % \
        (open(os.path.join(dir_name, 'user_input_routes.py')).read().strip())
    add_map = {
        '    # END BEGIN PLUGIN DEFINED ROUTING FUNCITONS HERE\n': open(os.path.join(dir_name, 'user_input.py'), 'r').read(),
        '        # END MODE CHANGE MAPPINGS HERE\n': dictstr
    }

    stop_list = set([
        '    # BEGIN PLUGIN DEFINED ROUTING FUNCITONS HERE\n',
        '        # BEGIN MODE CHANGE MAPPINGS HERE\n'])

    add_plugin_code(lines, add_map, stop_list)

    with open('Backend/user_input.py', 'w') as f:
        f.write(''.join(lines))


def load_plugin(dir_name):
    package_name = load_content_data(dir_name)
    fill_metadata_loader(dir_name, package_name)
    fill_interaction_manager(dir_name, package_name)
    fill_user_input(dir_name, package_name)

########NEW FILE########
__FILENAME__ = metadata_prototype
"""
Prototype code for metadata creation
More design on how metadata should be handled (if it should at all) in shim
needs to be done
"""
import os
import json
# BEGIN code-generated list of module imports
from plugins import fuzzy_file_select_meta
# END code-generated list of module imports


def create_metadata_files():
    for dirname, dirnames, filenames in os.walk(os.getcwd()):
        file_data = {}
        # BEGIN code-generated list of modules to call write_data
        MODULES = [fuzzy_file_select_meta]
        # END code-generated list of modules to call write_data
        for module in MODULES:
            module.write_data(dirname, file_data, os.walk(os.getcwd()))

        with open(os.path.join(dirname, '.shimdata'), 'w') as f:
            f.write(json.dumps(file_data))

########NEW FILE########
__FILENAME__ = shim
#!/usr/bin/env python3
from tkinter import Tk
from argparse import ArgumentParser
from frontend import text_canvas
from backend import user_input


def opt_init():
    """To parse option command line"""
    parser = ArgumentParser(description='A vim inspired text editor')
    parser.add_argument(dest='filename', action='store',
                        metavar='FILE', nargs='?')
    parser.add_argument('-v', '--version',
                        action='version', version='/dev/null')
    return parser


def run_text_editor(filename):
    """To run text editor"""
    root = Tk()
    input_handler = user_input.user_input()

    input_handler.start_instance(filename)
    text_canvas.text_canvas(root, 12, input_handler, filename)

    root.wm_attributes('-fullscreen', 1)
    root.call("::tk::unsupported::MacWindowStyle", "style", root._w, "plain", "none")


    root.title('shim')
    root.overrideredirect()

    root.mainloop()


if __name__ == '__main__':
    parser = opt_init()
    args = parser.parse_args()

    if args.filename:
        run_text_editor(args.filename)
    else:
        parser.print_usage()

########NEW FILE########
__FILENAME__ = start_test
#!/usr/bin/env python3
from tkinter import Tk
from frontend import text_canvas
from backend import user_input


def run_text_editor(filename):
    """To run text editor"""
    root = Tk()
    input_handler = user_input.user_input()

    input_handler.start_instance(filename)
    graphics_state = text_canvas.text_canvas(root, 12, input_handler, filename)

    root.wm_attributes('-fullscreen', 1)
    root.title('shim')
    root.overrideredirect()

    return input_handler, graphics_state, root


def bootstrap(filename):
    return run_text_editor(filename)

########NEW FILE########
__FILENAME__ = test
# main entry point for testing.
# spawns a regular instance of shim and gets references
# to state variables graphics, global state.
# global state contains references to local state instances
# calling statevariable.dump_state_variables() should spew current
# state of variable. I.E calling global_state.dump_state_variables()
# should return global buffer etc in JSON form

from argparse import ArgumentParser
from test import start_test

if __name__ == '__main__':
    global_state, graphics_state, root = start_test.bootstrap('shim.py')
    root.mainloop()

########NEW FILE########
