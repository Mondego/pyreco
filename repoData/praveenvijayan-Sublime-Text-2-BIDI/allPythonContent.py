__FILENAME__ = algorithm
# This file is part of python-bidi
#
# python-bidi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2008-2010 Yaacov Zamir <kzamir_a_walla.co.il>,
# Meir kriheli <meir@mksoft.co.il>
"bidirectional alogrithm implementation"

from unicodedata import bidirectional, mirrored
import inspect
import sys
from collections import deque

try:

    # Python 3

    from .mirror import MIRRORED
except ValueError:

    # Python 2
    from bidi.mirror import MIRRORED

# Some definitions
PARAGRAPH_LEVELS = { 'L':0, 'AL':1, 'R': 1 }
EXPLICIT_LEVEL_LIMIT = 62

_LEAST_GREATER_ODD = lambda x: (x + 1) | 1
_LEAST_GREATER_EVEN = lambda x: (x + 2) & ~1

X2_X5_MAPPINGS = {
    'RLE': (_LEAST_GREATER_ODD, 'N'),
    'LRE': (_LEAST_GREATER_EVEN, 'N'),
    'RLO': (_LEAST_GREATER_ODD, 'R'),
    'LRO': (_LEAST_GREATER_EVEN, 'L'),
}

# Added 'B' so X6 won't execute in that case and X8 will run it's course
X6_IGNORED = list(X2_X5_MAPPINGS.keys()) + ['BN', 'PDF', 'B']
X9_REMOVED = list(X2_X5_MAPPINGS.keys()) + ['BN', 'PDF']

_embedding_direction = lambda x:('L', 'R')[x % 2]

_IS_UCS2 = sys.maxunicode == 65535
_SURROGATE_MIN, _SURROGATE_MAX = 55296, 56319 # D800, DBFF

def debug_storage(storage, base_info=False, chars=True, runs=False):
    "Display debug information for the storage"

    import codecs
    import locale
    import sys

    stderr = codecs.getwriter(locale.getpreferredencoding())(sys.stderr)

    caller = inspect.stack()[1][3]
    stderr.write('in %s\n' % caller)

    if base_info:
        stderr.write(u'  base level  : %d\n' % storage['base_level'])
        stderr.write(u'  base dir    : %s\n' % storage['base_dir'])

    if runs:
        stderr.write(u'  runs        : %s\n' % list(storage['runs']))

    if chars:
        output = u'  Chars       : '
        for _ch in storage['chars']:
            if _ch != '\n':
                output += _ch['ch']
            else:
                output += 'C'
        stderr.write(output + u'\n')

        output = u'  Res. levels : %s\n' % u''.join(
            [unicode(_ch['level']) for _ch in storage['chars']])
        stderr.write(output)

        _types = [_ch['type'].ljust(3) for _ch in storage['chars']]

        for i in range(3):
            if i:
                output = u'                %s\n'
            else:
                output = u'  Res. types  : %s\n'
            stderr.write(output % u''.join([_t[i] for _t in _types]))


def get_base_level(text, upper_is_rtl=False):
    """Get the paragraph base embedding level. Returns 0 for LTR,
    1 for RTL.

    `text` a unicode object.

    Set `upper_is_rtl` to True to treat upper case chars as strong 'R'
    for debugging (default: False).

    """

    base_level = None

    prev_surrogate = False
    # P2
    for _ch in text:
        # surrogate in case of ucs2
        if _IS_UCS2 and (_SURROGATE_MIN <= ord(_ch) <= _SURROGATE_MAX):
            prev_surrogate = _ch
            continue
        elif prev_surrogate:
            _ch = prev_surrogate + _ch
            prev_surrogate = False

        # treat upper as RTL ?
        if upper_is_rtl and _ch.isupper():
            base_level = 1
            break

        bidi_type = bidirectional(_ch)

        if bidi_type in ('AL', 'R'):
            base_level = 1
            break

        elif bidi_type == 'L':
            base_level = 0
            break

    # P3
    if base_level is None:
        base_level = 0

    return base_level

def get_embedding_levels(text, storage, upper_is_rtl=False, debug=False):
    """Get the paragraph base embedding level and direction,
    set the storage to the array of chars"""

    prev_surrogate = False
    base_level = storage['base_level']

    # preset the storage's chars
    for _ch in text:
        if _IS_UCS2 and (_SURROGATE_MIN <= ord(_ch) <= _SURROGATE_MAX):
            prev_surrogate = _ch
            continue
        elif prev_surrogate:
            _ch = prev_surrogate + _ch
            prev_surrogate = False

        if upper_is_rtl and _ch.isupper():
            bidi_type = 'R'
        else:
            bidi_type = bidirectional(_ch)
        storage['chars'].append({'ch':_ch, 'level':base_level, 'type':bidi_type,
                                 'orig':bidi_type})
    if debug:
        debug_storage(storage, base_info=True)

def explicit_embed_and_overrides(storage, debug=False):
    """Apply X1 to X9 rules of the unicode algorithm.

    See http://unicode.org/reports/tr9/#Explicit_Levels_and_Directions

    """
    overflow_counter = almost_overflow_counter = 0
    directional_override = 'N'
    levels = deque()

    #X1
    embedding_level = storage['base_level']

    for _ch in storage['chars']:
        bidi_type = _ch['type']

        level_func, override = X2_X5_MAPPINGS.get(bidi_type, (None, None))

        if level_func:
            # So this is X2 to X5
            # if we've past EXPLICIT_LEVEL_LIMIT, note it and do nothing

            if overflow_counter != 0:
                overflow_counter += 1
                continue

            new_level = level_func(embedding_level)
            if new_level < EXPLICIT_LEVEL_LIMIT:
                levels.append( (embedding_level, directional_override) )
                embedding_level, directional_override = new_level, override

            elif embedding_level == EXPLICIT_LEVEL_LIMIT -2:
                # The new level is invalid, but a valid level can still be
                # achieved if this level is 60 and we encounter an RLE or
                # RLO further on.  So record that we 'almost' overflowed.
                almost_overflow_counter += 1

            else:
                overflow_counter += 1
        else:
            # X6
            if bidi_type not in X6_IGNORED:
                _ch['level'] = embedding_level
                if directional_override != 'N':
                    _ch['type'] = directional_override

            # X7
            elif bidi_type == 'PDF':
                if overflow_counter:
                    overflow_counter -= 1
                elif almost_overflow_counter and \
                        embedding_level != EXPLICIT_LEVEL_LIMIT - 1:
                    almost_overflow_counter -= 1
                elif levels:
                    embedding_level, directional_override = levels.pop()

            # X8
            elif bidi_type == 'B':
                levels.clear()
                overflow_counter = almost_overflow_counter = 0
                embedding_level = _ch['level'] = storage['base_level']
                directional_override = 'N'

    #Removes the explicit embeds and overrides of types
    #RLE, LRE, RLO, LRO, PDF, and BN. Adjusts extended chars
    #next and prev as well

    #Applies X9. See http://unicode.org/reports/tr9/#X9
    storage['chars'] = [_ch for _ch in storage['chars']\
                        if _ch['type'] not in X9_REMOVED]

    calc_level_runs(storage)

    if debug:
        debug_storage(storage, runs=True)

def calc_level_runs(storage):
    """Split the storage to run of char types at the same level.

    Applies X10. See http://unicode.org/reports/tr9/#X10
    """
    #run level depends on the higher of the two levels on either side of
    #the boundary If the higher level is odd, the type is R; otherwise,
    #it is L

    storage['runs'].clear()
    chars = storage['chars']

    #empty string ?
    if not chars:
        return

    calc_level_run = lambda b_l, b_r: ['L', 'R'][max(b_l, b_r) % 2]

    first_char = chars[0]

    sor = calc_level_run(storage['base_level'], first_char['level'])
    eor = None

    run_start = run_length = 0

    prev_level, prev_type = first_char['level'], first_char['type']

    for _ch in chars:
        curr_level, curr_type = _ch['level'], _ch['type']

        if curr_level == prev_level:
            run_length += 1
        else:
            eor = calc_level_run(prev_level, curr_level)
            storage['runs'].append({'sor':sor, 'eor':eor, 'start':run_start,
                            'type': prev_type,'length': run_length})
            sor = eor
            run_start += run_length
            run_length = 1

        prev_level, prev_type = curr_level, curr_type

    # for the last char/runlevel
    eor = calc_level_run(curr_level, storage['base_level'])
    storage['runs'].append({'sor':sor, 'eor':eor, 'start':run_start,
                            'type':curr_type, 'length': run_length})

def resolve_weak_types(storage, debug=False):
    """Reslove weak type rules W1 - W3.

    See: http://unicode.org/reports/tr9/#Resolving_Weak_Types

    """

    for run in storage['runs']:
        prev_strong = prev_type = run['sor']
        start, length = run['start'], run['length']
        chars = storage['chars'][start:start+length]
        for _ch in chars:
            # W1. Examine each nonspacing mark (NSM) in the level run, and
            # change the type of the NSM to the type of the previous character.
            # If the NSM is at the start of the level run, it will get the type
            # of sor.
            bidi_type = _ch['type']

            if bidi_type == 'NSM':
                _ch['type'] = bidi_type = prev_type

            # W2. Search backward from each instance of a European number until
            # the first strong type (R, L, AL, or sor) is found. If an AL is
            # found, change the type of the European number to Arabic number.
            if bidi_type == 'EN' and prev_strong == 'AL':
                _ch['type'] = 'AN'

            # update prev_strong if needed
            if bidi_type in ('R', 'L', 'AL'):
                prev_strong = bidi_type

            prev_type = _ch['type']

        # W3. Change all ALs to R
        for _ch in chars:
            if _ch['type'] == 'AL':
                _ch['type'] = 'R'

        # W4. A single European separator between two European numbers changes
        # to a European number. A single common separator between two numbers of
        # the same type changes to that type.
        for idx in range(1, len(chars) -1 ):
            bidi_type = chars[idx]['type']
            prev_type = chars[idx-1]['type']
            next_type = chars[idx+1]['type']

            if bidi_type == 'ES' and (prev_type == next_type == 'EN'):
                chars[idx]['type'] = 'EN'

            if bidi_type == 'CS' and prev_type == next_type and \
                       prev_type in ('AN', 'EN'):
                chars[idx]['type'] = prev_type


        # W5. A sequence of European terminators adjacent to European numbers
        # changes to all European numbers.
        for idx in range(len(chars)):
            if chars[idx]['type'] == 'EN':
                for et_idx in range(idx-1, -1, -1):
                    if chars[et_idx]['type'] == 'ET':
                        chars[et_idx]['type'] = 'EN'
                    else:
                        break
                for et_idx in range(idx+1, len(chars)):
                    if chars[et_idx]['type'] == 'ET':
                        chars[et_idx]['type'] = 'EN'
                    else:
                        break

        # W6. Otherwise, separators and terminators change to Other Neutral.
        for _ch in chars:
            if _ch['type'] in ('ET', 'ES', 'CS'):
                _ch['type'] = 'ON'

        # W7. Search backward from each instance of a European number until the
        # first strong type (R, L, or sor) is found. If an L is found, then
        # change the type of the European number to L.
        prev_strong = run['sor']
        for _ch in chars:
            if _ch['type'] == 'EN' and prev_strong == 'L':
                _ch['type'] = 'L'

            if _ch['type'] in ('L', 'R'):
                prev_strong = _ch['type']

    if debug:
        debug_storage(storage, runs=True)

def resolve_neutral_types(storage, debug):
    """Resolving neutral types. Implements N1 and N2

    See: http://unicode.org/reports/tr9/#Resolving_Neutral_Types

    """

    for run in storage['runs']:
        start, length = run['start'], run['length']
        # use sor and eor
        chars = [{'type':run['sor']}] + storage['chars'][start:start+length] +\
                [{'type':run['eor']}]
        total_chars = len(chars)

        seq_start = None
        for idx in range(total_chars):
            _ch = chars[idx]
            if _ch['type'] in ('B', 'S', 'WS', 'ON'):
                # N1. A sequence of neutrals takes the direction of the
                # surrounding strong text if the text on both sides has the same
                # direction. European and Arabic numbers act as if they were R
                # in terms of their influence on neutrals. Start-of-level-run
                # (sor) and end-of-level-run (eor) are used at level run
                # boundaries.
                if seq_start is None:
                    seq_start = idx
                    prev_bidi_type = chars[idx-1]['type']
            else:
                if seq_start is not None:
                    next_bidi_type = chars[idx]['type']

                    if prev_bidi_type in ('AN', 'EN'):
                        prev_bidi_type = 'R'

                    if next_bidi_type in ('AN', 'EN'):
                        next_bidi_type = 'R'

                    for seq_idx in range(seq_start, idx):
                        if prev_bidi_type == next_bidi_type:
                            chars[seq_idx]['type'] = prev_bidi_type
                        else:
                            # N2. Any remaining neutrals take the embedding
                            # direction. The embedding direction for the given
                            # neutral character is derived from its embedding
                            # level: L if the character is set to an even level,
                            # and R if the level is odd.
                            chars[seq_idx]['type'] = \
                                _embedding_direction(chars[seq_idx]['level'])

                    seq_start = None

    if debug:
        debug_storage(storage)

def resolve_implicit_levels(storage, debug):
    """Resolving implicit levels (I1, I2)

    See: http://unicode.org/reports/tr9/#Resolving_Implicit_Levels

    """
    for run in storage['runs']:
        start, length = run['start'], run['length']
        chars = storage['chars'][start:start+length]

        for _ch in chars:
            # only those types are allowed at this stage
            assert _ch['type'] in ('L', 'R', 'EN', 'AN'),\
                    '%s not allowed here' % _ch['type']

            if _embedding_direction(_ch['level']) == 'L':
                # I1. For all characters with an even (left-to-right) embedding
                # direction, those of type R go up one level and those of type
                # AN or EN go up two levels.
                if _ch['type'] == 'R':
                    _ch['level'] += 1
                elif _ch['type'] != 'L':
                    _ch['level'] += 2
            else:
                # I2. For all characters with an odd (right-to-left) embedding
                # direction, those of type L, EN or AN  go up one level.
                if _ch['type'] != 'R':
                    _ch['level'] += 1

    if debug:
        debug_storage(storage, runs=True)

def reverse_contiguous_sequence(chars, line_start, line_end, highest_level,
                                lowest_odd_level):
    """L2. From the highest level found in the text to the lowest odd
    level on each line, including intermediate levels not actually
    present in the text, reverse any contiguous sequence of characters
    that are at that level or higher.

    """
    for level in range(highest_level, lowest_odd_level-1, -1):
        _start = _end = None

        for run_idx in range(line_start, line_end+1):
            run_ch = chars[run_idx]

            if run_ch['level'] >= level:
                if _start is None:
                    _start = _end = run_idx
                else:
                    _end = run_idx
            else:
                if _end:
                    chars[_start:+_end+1] = \
                            reversed(chars[_start:+_end+1])
                    _start = _end = None

        # anything remaining ?
        if _start is not None:
            chars[_start:+_end+1] = \
                reversed(chars[_start:+_end+1])


def reorder_resolved_levels(storage, debug):
    """L1 and L2 rules"""

    # Applies L1.

    should_reset = True
    chars = storage['chars']

    for _ch in chars[::-1]:
        # L1. On each line, reset the embedding level of the following
        # characters to the paragraph embedding level:
        if _ch['orig'] in ('B', 'S'):
            # 1. Segment separators,
            # 2. Paragraph separators,
            _ch['level'] = storage['base_level']
            should_reset = True
        elif should_reset and _ch['orig'] in ('BN', 'WS'):
            # 3. Any sequence of whitespace characters preceding a segment
            # separator or paragraph separator
            # 4. Any sequence of white space characters at the end of the
            # line.
            _ch['level'] = storage['base_level']
        else:
            should_reset = False

    max_len = len(chars)

    # L2 should be per line
    # Calculates highest level and loweset odd level on the fly.

    line_start = line_end = 0
    highest_level = 0
    lowest_odd_level = EXPLICIT_LEVEL_LIMIT

    for idx in range(max_len):
        _ch = chars[idx]

        # calc the levels
        char_level = _ch['level']
        if char_level > highest_level:
            highest_level = char_level

        if char_level % 2 and char_level < lowest_odd_level:
            lowest_odd_level = char_level

        if _ch['orig'] == 'B' or idx == max_len -1:
            line_end = idx
            # omit line breaks
            if _ch['orig'] == 'B':
                line_end -= 1

            reverse_contiguous_sequence(chars, line_start, line_end,
                                        highest_level, lowest_odd_level)

            # reset for next line run
            line_start = idx+1
            highest_level = 0
            lowest_odd_level = EXPLICIT_LEVEL_LIMIT

    if debug:
        debug_storage(storage)


def apply_mirroring(storage, debug):
    """Applies L4: mirroring

    See: http://unicode.org/reports/tr9/#L4

    """
    # L4. A character is depicted by a mirrored glyph if and only if (a) the
    # resolved directionality of that character is R, and (b) the
    # Bidi_Mirrored property value of that character is true.
    for _ch in storage['chars']:
        unichar = _ch['ch']
        if mirrored(unichar) and \
                     _embedding_direction(_ch['level']) == 'R':
            _ch['ch'] = MIRRORED.get(unichar, unichar)

    if debug:
        debug_storage(storage)

def get_empty_storage():
    """Return an empty storage skeleton, usable for testing"""
    return {
        'base_level': None,
        'base_dir' : None,
        'chars': [],
        'runs' : deque(),
    }


def get_display(unicode_or_str, encoding='utf-8', upper_is_rtl=False,
                base_dir=None, debug=False):
    """Accepts unicode or string. In case it's a string, `encoding`
    is needed as it works on unicode ones (default:"utf-8").

    Set `upper_is_rtl` to True to treat upper case chars as strong 'R'
    for debugging (default: False).

    Set `base_dir` to 'L' or 'R' to override the calculated base_level.

    Set `debug` to True to display (using sys.stderr) the steps taken with the
    algorithm.

    Returns the display layout, either as unicode or `encoding` encoded
    string.

    """
    storage = get_empty_storage()

    # utf-8 ? we need unicode
    if isinstance(unicode_or_str, str):
        text = unicode_or_str
        decoded = False
    else:
        text = unicode_or_str.decode(encoding)
        decoded = True

    if base_dir is None:
        base_level = get_base_level(text, upper_is_rtl)
    else:
        base_level = PARAGRAPH_LEVELS[base_dir]

    storage['base_level'] = base_level
    storage['base_dir'] = ('L', 'R')[base_level]

    get_embedding_levels(text, storage, upper_is_rtl, debug)
    explicit_embed_and_overrides(storage, debug)
    resolve_weak_types(storage, debug)
    resolve_neutral_types(storage, debug)
    resolve_implicit_levels(storage, debug)
    reorder_resolved_levels(storage, debug)
    apply_mirroring(storage, debug)

    chars = storage['chars']
    display = u''.join([_ch['ch'] for _ch in chars])

    if decoded:
        return display.encode(encoding)
    else:
        return display

########NEW FILE########
__FILENAME__ = arabic_reshaper
# -*- coding: utf-8 -*-

# This work is licensed under the GNU Public License (GPL).
# To view a copy of this license, visit http://www.gnu.org/copyleft/gpl.html

# Written by Abd Allah Diab (mpcabd)
# Email: mpcabd ^at^ gmail ^dot^ com
# Website: http://mpcabd.igeex.biz

# Ported and tweaked from Java to Python, from Better Arabic Reshaper [https://github.com/agawish/Better-Arabic-Reshaper/]

import re

DEFINED_CHARACTERS_ORGINAL_ALF_UPPER_MDD 		= u'\u0622'
DEFINED_CHARACTERS_ORGINAL_ALF_UPPER_HAMAZA		= u'\u0623'
DEFINED_CHARACTERS_ORGINAL_ALF_LOWER_HAMAZA 		= u'\u0625'
DEFINED_CHARACTERS_ORGINAL_ALF 				= u'\u0627'
DEFINED_CHARACTERS_ORGINAL_LAM				= u'\u0644'

LAM_ALEF_GLYPHS = [
	[u'\u3BA6', u'\uFEF6', u'\uFEF5'],
	[u'\u3BA7', u'\uFEF8', u'\uFEF7'],
	[u'\u0627', u'\uFEFC', u'\uFEFB'],
	[u'\u0625', u'\uFEFA', u'\uFEF9']
]

HARAKAT = [
	u'\u0600', u'\u0601', u'\u0602', u'\u0603', u'\u0606', u'\u0607', u'\u0608', u'\u0609',
	u'\u060A', u'\u060B', u'\u060D', u'\u060E', u'\u0610', u'\u0611', u'\u0612', u'\u0613',
	u'\u0614', u'\u0615', u'\u0616', u'\u0617', u'\u0618', u'\u0619', u'\u061A', u'\u061B',
	u'\u061E', u'\u061F', u'\u0621', u'\u063B', u'\u063C', u'\u063D', u'\u063E', u'\u063F',
	u'\u0640', u'\u064B', u'\u064C', u'\u064D', u'\u064E', u'\u064F', u'\u0650', u'\u0651',
	u'\u0652', u'\u0653', u'\u0654', u'\u0655', u'\u0656', u'\u0657', u'\u0658', u'\u0659',
	u'\u065A', u'\u065B', u'\u065C', u'\u065D', u'\u065E', u'\u0660', u'\u066A', u'\u066B',
	u'\u066C', u'\u066F', u'\u0670', u'\u0672', u'\u06D4', u'\u06D5', u'\u06D6', u'\u06D7',
	u'\u06D8', u'\u06D9', u'\u06DA', u'\u06DB', u'\u06DC', u'\u06DF', u'\u06E0', u'\u06E1',
	u'\u06E2', u'\u06E3', u'\u06E4', u'\u06E5', u'\u06E6', u'\u06E7', u'\u06E8', u'\u06E9',
	u'\u06EA', u'\u06EB', u'\u06EC', u'\u06ED', u'\u06EE', u'\u06EF', u'\u06D6', u'\u06D7',
	u'\u06D8', u'\u06D9', u'\u06DA', u'\u06DB', u'\u06DC', u'\u06DD', u'\u06DE', u'\u06DF',
	u'\u06F0', u'\u06FD', u'\uFE70', u'\uFE71', u'\uFE72', u'\uFE73', u'\uFE74', u'\uFE75',
	u'\uFE76', u'\uFE77', u'\uFE78', u'\uFE79', u'\uFE7A', u'\uFE7B', u'\uFE7C', u'\uFE7D',
	u'\uFE7E', u'\uFE7F', u'\uFC5E', u'\uFC5F', u'\uFC60', u'\uFC61', u'\uFC62', u'\uFC63'
]

ARABIC_GLYPHS = {
	u'\u0622' : [u'\u0622', u'\uFE81', u'\uFE81', u'\uFE82', u'\uFE82', 2],
	u'\u0623' : [u'\u0623', u'\uFE83', u'\uFE83', u'\uFE84', u'\uFE84', 2],
	u'\u0624' : [u'\u0624', u'\uFE85', u'\uFE85', u'\uFE86', u'\uFE86', 2],
	u'\u0625' : [u'\u0625', u'\uFE87', u'\uFE87', u'\uFE88', u'\uFE88', 2],
	u'\u0626' : [u'\u0626', u'\uFE89', u'\uFE8B', u'\uFE8C', u'\uFE8A', 4],
	u'\u0627' : [u'\u0627', u'\u0627', u'\u0627', u'\uFE8E', u'\uFE8E', 2],
	u'\u0628' : [u'\u0628', u'\uFE8F', u'\uFE91', u'\uFE92', u'\uFE90', 4],
	u'\u0629' : [u'\u0629', u'\uFE93', u'\uFE93', u'\uFE94', u'\uFE94', 2],
	u'\u062A' : [u'\u062A', u'\uFE95', u'\uFE97', u'\uFE98', u'\uFE96', 4],
	u'\u062B' : [u'\u062B', u'\uFE99', u'\uFE9B', u'\uFE9C', u'\uFE9A', 4],
	u'\u062C' : [u'\u062C', u'\uFE9D', u'\uFE9F', u'\uFEA0', u'\uFE9E', 4],
	u'\u062D' : [u'\u062D', u'\uFEA1', u'\uFEA3', u'\uFEA4', u'\uFEA2', 4],
	u'\u062E' : [u'\u062E', u'\uFEA5', u'\uFEA7', u'\uFEA8', u'\uFEA6', 4],
	u'\u062F' : [u'\u062F', u'\uFEA9', u'\uFEA9', u'\uFEAA', u'\uFEAA', 2],
	u'\u0630' : [u'\u0630', u'\uFEAB', u'\uFEAB', u'\uFEAC', u'\uFEAC', 2],
	u'\u0631' : [u'\u0631', u'\uFEAD', u'\uFEAD', u'\uFEAE', u'\uFEAE', 2],
	u'\u0632' : [u'\u0632', u'\uFEAF', u'\uFEAF', u'\uFEB0', u'\uFEB0', 2],
	u'\u0633' : [u'\u0633', u'\uFEB1', u'\uFEB3', u'\uFEB4', u'\uFEB2', 4],
	u'\u0634' : [u'\u0634', u'\uFEB5', u'\uFEB7', u'\uFEB8', u'\uFEB6', 4],
	u'\u0635' : [u'\u0635', u'\uFEB9', u'\uFEBB', u'\uFEBC', u'\uFEBA', 4],
	u'\u0636' : [u'\u0636', u'\uFEBD', u'\uFEBF', u'\uFEC0', u'\uFEBE', 4],
	u'\u0637' : [u'\u0637', u'\uFEC1', u'\uFEC3', u'\uFEC4', u'\uFEC2', 4],
	u'\u0638' : [u'\u0638', u'\uFEC5', u'\uFEC7', u'\uFEC8', u'\uFEC6', 4],
	u'\u0639' : [u'\u0639', u'\uFEC9', u'\uFECB', u'\uFECC', u'\uFECA', 4],
	u'\u063A' : [u'\u063A', u'\uFECD', u'\uFECF', u'\uFED0', u'\uFECE', 4],
	u'\u0641' : [u'\u0641', u'\uFED1', u'\uFED3', u'\uFED4', u'\uFED2', 4],
	u'\u0642' : [u'\u0642', u'\uFED5', u'\uFED7', u'\uFED8', u'\uFED6', 4],
	u'\u0643' : [u'\u0643', u'\uFED9', u'\uFEDB', u'\uFEDC', u'\uFEDA', 4],
	u'\u0644' : [u'\u0644', u'\uFEDD', u'\uFEDF', u'\uFEE0', u'\uFEDE', 4],
	u'\u0645' : [u'\u0645', u'\uFEE1', u'\uFEE3', u'\uFEE4', u'\uFEE2', 4],
	u'\u0646' : [u'\u0646', u'\uFEE5', u'\uFEE7', u'\uFEE8', u'\uFEE6', 4],
	u'\u0647' : [u'\u0647', u'\uFEE9', u'\uFEEB', u'\uFEEC', u'\uFEEA', 4],
	u'\u0648' : [u'\u0648', u'\uFEED', u'\uFEED', u'\uFEEE', u'\uFEEE', 2],
	u'\u0649' : [u'\u0649', u'\uFEEF', u'\uFEEF', u'\uFEF0', u'\uFEF0', 2],
	u'\u0671' : [u'\u0671', u'\u0671', u'\u0671', u'\uFB51', u'\uFB51', 2],
	u'\u064A' : [u'\u064A', u'\uFEF1', u'\uFEF3', u'\uFEF4', u'\uFEF2', 4],
	u'\u066E' : [u'\u066E', u'\uFBE4', u'\uFBE8', u'\uFBE9', u'\uFBE5', 4],
	u'\u06AA' : [u'\u06AA', u'\uFB8E', u'\uFB90', u'\uFB91', u'\uFB8F', 4],
	u'\u06C1' : [u'\u06C1', u'\uFBA6', u'\uFBA8', u'\uFBA9', u'\uFBA7', 4],
	u'\u06E4' : [u'\u06E4', u'\u06E4', u'\u06E4', u'\u06E4', u'\uFEEE', 2]
}

ARABIC_GLYPHS_LIST = [
	[u'\u0622', u'\uFE81', u'\uFE81', u'\uFE82', u'\uFE82', 2],
	[u'\u0623', u'\uFE83', u'\uFE83', u'\uFE84', u'\uFE84', 2],
	[u'\u0624', u'\uFE85', u'\uFE85', u'\uFE86', u'\uFE86', 2],
	[u'\u0625', u'\uFE87', u'\uFE87', u'\uFE88', u'\uFE88', 2],
	[u'\u0626', u'\uFE89', u'\uFE8B', u'\uFE8C', u'\uFE8A', 4],
	[u'\u0627', u'\u0627', u'\u0627', u'\uFE8E', u'\uFE8E', 2],
	[u'\u0628', u'\uFE8F', u'\uFE91', u'\uFE92', u'\uFE90', 4],
	[u'\u0629', u'\uFE93', u'\uFE93', u'\uFE94', u'\uFE94', 2],
	[u'\u062A', u'\uFE95', u'\uFE97', u'\uFE98', u'\uFE96', 4],
	[u'\u062B', u'\uFE99', u'\uFE9B', u'\uFE9C', u'\uFE9A', 4],
	[u'\u062C', u'\uFE9D', u'\uFE9F', u'\uFEA0', u'\uFE9E', 4],
	[u'\u062D', u'\uFEA1', u'\uFEA3', u'\uFEA4', u'\uFEA2', 4],
	[u'\u062E', u'\uFEA5', u'\uFEA7', u'\uFEA8', u'\uFEA6', 4],
	[u'\u062F', u'\uFEA9', u'\uFEA9', u'\uFEAA', u'\uFEAA', 2],
	[u'\u0630', u'\uFEAB', u'\uFEAB', u'\uFEAC', u'\uFEAC', 2],
	[u'\u0631', u'\uFEAD', u'\uFEAD', u'\uFEAE', u'\uFEAE', 2],
	[u'\u0632', u'\uFEAF', u'\uFEAF', u'\uFEB0', u'\uFEB0', 2],
	[u'\u0633', u'\uFEB1', u'\uFEB3', u'\uFEB4', u'\uFEB2', 4],
	[u'\u0634', u'\uFEB5', u'\uFEB7', u'\uFEB8', u'\uFEB6', 4],
	[u'\u0635', u'\uFEB9', u'\uFEBB', u'\uFEBC', u'\uFEBA', 4],
	[u'\u0636', u'\uFEBD', u'\uFEBF', u'\uFEC0', u'\uFEBE', 4],
	[u'\u0637', u'\uFEC1', u'\uFEC3', u'\uFEC4', u'\uFEC2', 4],
	[u'\u0638', u'\uFEC5', u'\uFEC7', u'\uFEC8', u'\uFEC6', 4],
	[u'\u0639', u'\uFEC9', u'\uFECB', u'\uFECC', u'\uFECA', 4],
	[u'\u063A', u'\uFECD', u'\uFECF', u'\uFED0', u'\uFECE', 4],
	[u'\u0641', u'\uFED1', u'\uFED3', u'\uFED4', u'\uFED2', 4],
	[u'\u0642', u'\uFED5', u'\uFED7', u'\uFED8', u'\uFED6', 4],
	[u'\u0643', u'\uFED9', u'\uFEDB', u'\uFEDC', u'\uFEDA', 4],
	[u'\u0644', u'\uFEDD', u'\uFEDF', u'\uFEE0', u'\uFEDE', 4],
	[u'\u0645', u'\uFEE1', u'\uFEE3', u'\uFEE4', u'\uFEE2', 4],
	[u'\u0646', u'\uFEE5', u'\uFEE7', u'\uFEE8', u'\uFEE6', 4],
	[u'\u0647', u'\uFEE9', u'\uFEEB', u'\uFEEC', u'\uFEEA', 4],
	[u'\u0648', u'\uFEED', u'\uFEED', u'\uFEEE', u'\uFEEE', 2],
	[u'\u0649', u'\uFEEF', u'\uFEEF', u'\uFEF0', u'\uFEF0', 2],
	[u'\u0671', u'\u0671', u'\u0671', u'\uFB51', u'\uFB51', 2],
	[u'\u064A', u'\uFEF1', u'\uFEF3', u'\uFEF4', u'\uFEF2', 4],
	[u'\u066E', u'\uFBE4', u'\uFBE8', u'\uFBE9', u'\uFBE5', 4],
	[u'\u06AA', u'\uFB8E', u'\uFB90', u'\uFB91', u'\uFB8F', 4],
	[u'\u06C1', u'\uFBA6', u'\uFBA8', u'\uFBA9', u'\uFBA7', 4],
]

def get_reshaped_glyph(target, location):
	if target in ARABIC_GLYPHS:
		return ARABIC_GLYPHS[target][location]
	else:
		return target
		
def get_glyph_type(target):
	if target in ARABIC_GLYPHS:
		return ARABIC_GLYPHS[target][5]
	else:
		return 2
		
def is_haraka(target):
	return target in HARAKAT
		
def replace_lam_alef(unshaped_word):
	list_word = list(unshaped_word)
	letter_before = u''
	for i in range(len(unshaped_word)):
		if not is_haraka(unshaped_word[i]) and unshaped_word[i] != DEFINED_CHARACTERS_ORGINAL_LAM:
			letter_before = unshaped_word[i]

		if unshaped_word[i] == DEFINED_CHARACTERS_ORGINAL_LAM:
			candidate_lam = unshaped_word[i]
			lam_position = i
			haraka_position = i + 1
			
			while haraka_position < len(unshaped_word) and is_haraka(unshaped_word[haraka_position]):
				haraka_position += 1
				
			if haraka_position < len(unshaped_word):
				if lam_position > 0 and get_glyph_type(letter_before) > 2:
					lam_alef = get_lam_alef(list_word[haraka_position], candidate_lam, False)
				else:
					lam_alef = get_lam_alef(list_word[haraka_position], candidate_lam, True)
				if lam_alef != '':
					list_word[lam_position] = lam_alef
					list_word[haraka_position] = u' '
			
	return u''.join(list_word).replace(u' ', u'')
		
def get_lam_alef(candidate_alef, candidate_lam, is_end_of_word):
	shift_rate = 1
	reshaped_lam_alef = u''
	if is_end_of_word:
		shift_rate += 1
	
	if DEFINED_CHARACTERS_ORGINAL_LAM == candidate_lam:
		if DEFINED_CHARACTERS_ORGINAL_ALF_UPPER_MDD == candidate_alef:
			reshaped_lam_alef = LAM_ALEF_GLYPHS[0][shift_rate]
		
		if DEFINED_CHARACTERS_ORGINAL_ALF_UPPER_HAMAZA == candidate_alef:
			reshaped_lam_alef = LAM_ALEF_GLYPHS[1][shift_rate]
		
		if DEFINED_CHARACTERS_ORGINAL_ALF == candidate_alef:
			reshaped_lam_alef = LAM_ALEF_GLYPHS[2][shift_rate]
		
		if DEFINED_CHARACTERS_ORGINAL_ALF_LOWER_HAMAZA == candidate_alef:
			reshaped_lam_alef = LAM_ALEF_GLYPHS[3][shift_rate]
	
	return reshaped_lam_alef

class DecomposedWord(object):
	def __init__(self, word):
		self.stripped_harakat = []
		self.harakat_positions = []
		self.stripped_regular_letters = []
		self.letters_position = []

		for i in range(len(word)):
			c = word[i]
			if is_haraka(c):
				self.harakat_positions.append(i)
				self.stripped_harakat.append(c)
			else:
				self.letters_position.append(i)
				self.stripped_regular_letters.append(c)

	def reconstruct_word(self, reshaped_word):
		l = list(u'\0' * (len(self.stripped_harakat) + len(reshaped_word)))
		for i in range(len(self.letters_position)):
			l[self.letters_position[i]] = reshaped_word[i]
		for i in range(len(self.harakat_positions)):
			l[self.harakat_positions[i]] = self.stripped_harakat[i]
		return u''.join(l)

def get_reshaped_word(unshaped_word):
	unshaped_word = replace_lam_alef(unshaped_word)
	decomposed_word = DecomposedWord(unshaped_word)
	result = u''
	if decomposed_word.stripped_regular_letters:
		result = reshape_it(u''.join(decomposed_word.stripped_regular_letters))
	return decomposed_word.reconstruct_word(result)

def reshape_it(unshaped_word):
	if not unshaped_word:
		return u''
	if len(unshaped_word) == 1:
		return get_reshaped_glyph(unshaped_word[0], 1)
	reshaped_word = []
	for i in range(len(unshaped_word)):
		before = False
		after = False
		if i == 0:
			after = get_glyph_type(unshaped_word[i]) == 4
		elif i == len(unshaped_word) - 1:
			before = get_glyph_type(unshaped_word[i - 1]) == 4
		else:
			after = get_glyph_type(unshaped_word[i]) == 4
			before = get_glyph_type(unshaped_word[i - 1]) == 4
		if after and before:
			reshaped_word.append(get_reshaped_glyph(unshaped_word[i], 3))
		elif after and not before:
			reshaped_word.append(get_reshaped_glyph(unshaped_word[i], 2))
		elif not after and before:
			reshaped_word.append(get_reshaped_glyph(unshaped_word[i], 4))
		elif not after and not before:
			reshaped_word.append(get_reshaped_glyph(unshaped_word[i], 1))

	return u''.join(reshaped_word)


def is_arabic_character(target):
	return target in ARABIC_GLYPHS or target in HARAKAT
	
def get_words(sentence):
	if sentence:
		return re.split('\\s', sentence)
	return []
	
def has_arabic_letters(word):
	for c in word:
		if is_arabic_character(c):
			return True
	return False

def is_arabic_word(word):
	for c in word:
		if not is_arabic_character(c):
			return False
	return True
	
def get_words_from_mixed_word(word):
	temp_word = u''
	words = []
	for c in word:
		if is_arabic_character(c):
			if temp_word and not is_arabic_word(temp_word):
				words.append(temp_word)
				temp_word = c
			else:
				temp_word += c
		else:
			if temp_word and is_arabic_word(temp_word):
				words.append(temp_word)
				temp_word = c
			else:
				temp_word += c
	if temp_word:
		words.append(temp_word)
	return words
	
def reshape(text):
	if text:
		lines = re.split('\\r?\\n', text)
		for i in range(len(lines)):
			lines[i] = reshape_sentence(lines[i])
		return u'\n'.join(lines)
	return u''
	
def reshape_sentence(sentence):
	words = get_words(sentence)
	for i in range(len(words)):
		word = words[i]
		if has_arabic_letters(word):
			if is_arabic_word(word):
				words[i] = get_reshaped_word(word)
			else:
				mixed_words = get_words_from_mixed_word(word)
				for j in range(len(mixed_words)):
					mixed_words[j] = get_reshaped_word(mixed_words[j])
				words[i] = u''.join(mixed_words)
	return u' '.join(words)

########NEW FILE########
__FILENAME__ = mirror
# This file is part of python-bidi
#
# python-bidi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2008-2010 Yaacov Zamir <kzamir_a_walla.co.il>,
# Meir kriheli <meir@mksoft.co.il>
"""Mirrored chars"""

# Can't seem to get this data from python's unicode data, so this is imported
# from http://www.unicode.org/Public/UNIDATA/BidiMirroring.txt
MIRRORED = {
u'\u0028': u'\u0029', # LEFT PARENTHESIS
u'\u0029': u'\u0028', # RIGHT PARENTHESIS
u'\u003C': u'\u003E', # LESS-THAN SIGN
u'\u003E': u'\u003C', # GREATER-THAN SIGN
u'\u005B': u'\u005D', # LEFT SQUARE BRACKET
u'\u005D': u'\u005B', # RIGHT SQUARE BRACKET
u'\u007B': u'\u007D', # LEFT CURLY BRACKET
u'\u007D': u'\u007B', # RIGHT CURLY BRACKET
u'\u00AB': u'\u00BB', # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
u'\u00BB': u'\u00AB', # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
u'\u0F3A': u'\u0F3B', # TIBETAN MARK GUG RTAGS GYON
u'\u0F3B': u'\u0F3A', # TIBETAN MARK GUG RTAGS GYAS
u'\u0F3C': u'\u0F3D', # TIBETAN MARK ANG KHANG GYON
u'\u0F3D': u'\u0F3C', # TIBETAN MARK ANG KHANG GYAS
u'\u169B': u'\u169C', # OGHAM FEATHER MARK
u'\u169C': u'\u169B', # OGHAM REVERSED FEATHER MARK
u'\u2039': u'\u203A', # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
u'\u203A': u'\u2039', # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
u'\u2045': u'\u2046', # LEFT SQUARE BRACKET WITH QUILL
u'\u2046': u'\u2045', # RIGHT SQUARE BRACKET WITH QUILL
u'\u207D': u'\u207E', # SUPERSCRIPT LEFT PARENTHESIS
u'\u207E': u'\u207D', # SUPERSCRIPT RIGHT PARENTHESIS
u'\u208D': u'\u208E', # SUBSCRIPT LEFT PARENTHESIS
u'\u208E': u'\u208D', # SUBSCRIPT RIGHT PARENTHESIS
u'\u2208': u'\u220B', # ELEMENT OF
u'\u2209': u'\u220C', # NOT AN ELEMENT OF
u'\u220A': u'\u220D', # SMALL ELEMENT OF
u'\u220B': u'\u2208', # CONTAINS AS MEMBER
u'\u220C': u'\u2209', # DOES NOT CONTAIN AS MEMBER
u'\u220D': u'\u220A', # SMALL CONTAINS AS MEMBER
u'\u2215': u'\u29F5', # DIVISION SLASH
u'\u223C': u'\u223D', # TILDE OPERATOR
u'\u223D': u'\u223C', # REVERSED TILDE
u'\u2243': u'\u22CD', # ASYMPTOTICALLY EQUAL TO
u'\u2252': u'\u2253', # APPROXIMATELY EQUAL TO OR THE IMAGE OF
u'\u2253': u'\u2252', # IMAGE OF OR APPROXIMATELY EQUAL TO
u'\u2254': u'\u2255', # COLON EQUALS
u'\u2255': u'\u2254', # EQUALS COLON
u'\u2264': u'\u2265', # LESS-THAN OR EQUAL TO
u'\u2265': u'\u2264', # GREATER-THAN OR EQUAL TO
u'\u2266': u'\u2267', # LESS-THAN OVER EQUAL TO
u'\u2267': u'\u2266', # GREATER-THAN OVER EQUAL TO
u'\u2268': u'\u2269', # [BEST FIT] LESS-THAN BUT NOT EQUAL TO
u'\u2269': u'\u2268', # [BEST FIT] GREATER-THAN BUT NOT EQUAL TO
u'\u226A': u'\u226B', # MUCH LESS-THAN
u'\u226B': u'\u226A', # MUCH GREATER-THAN
u'\u226E': u'\u226F', # [BEST FIT] NOT LESS-THAN
u'\u226F': u'\u226E', # [BEST FIT] NOT GREATER-THAN
u'\u2270': u'\u2271', # [BEST FIT] NEITHER LESS-THAN NOR EQUAL TO
u'\u2271': u'\u2270', # [BEST FIT] NEITHER GREATER-THAN NOR EQUAL TO
u'\u2272': u'\u2273', # [BEST FIT] LESS-THAN OR EQUIVALENT TO
u'\u2273': u'\u2272', # [BEST FIT] GREATER-THAN OR EQUIVALENT TO
u'\u2274': u'\u2275', # [BEST FIT] NEITHER LESS-THAN NOR EQUIVALENT TO
u'\u2275': u'\u2274', # [BEST FIT] NEITHER GREATER-THAN NOR EQUIVALENT TO
u'\u2276': u'\u2277', # LESS-THAN OR GREATER-THAN
u'\u2277': u'\u2276', # GREATER-THAN OR LESS-THAN
u'\u2278': u'\u2279', # [BEST FIT] NEITHER LESS-THAN NOR GREATER-THAN
u'\u2279': u'\u2278', # [BEST FIT] NEITHER GREATER-THAN NOR LESS-THAN
u'\u227A': u'\u227B', # PRECEDES
u'\u227B': u'\u227A', # SUCCEEDS
u'\u227C': u'\u227D', # PRECEDES OR EQUAL TO
u'\u227D': u'\u227C', # SUCCEEDS OR EQUAL TO
u'\u227E': u'\u227F', # [BEST FIT] PRECEDES OR EQUIVALENT TO
u'\u227F': u'\u227E', # [BEST FIT] SUCCEEDS OR EQUIVALENT TO
u'\u2280': u'\u2281', # [BEST FIT] DOES NOT PRECEDE
u'\u2281': u'\u2280', # [BEST FIT] DOES NOT SUCCEED
u'\u2282': u'\u2283', # SUBSET OF
u'\u2283': u'\u2282', # SUPERSET OF
u'\u2284': u'\u2285', # [BEST FIT] NOT A SUBSET OF
u'\u2285': u'\u2284', # [BEST FIT] NOT A SUPERSET OF
u'\u2286': u'\u2287', # SUBSET OF OR EQUAL TO
u'\u2287': u'\u2286', # SUPERSET OF OR EQUAL TO
u'\u2288': u'\u2289', # [BEST FIT] NEITHER A SUBSET OF NOR EQUAL TO
u'\u2289': u'\u2288', # [BEST FIT] NEITHER A SUPERSET OF NOR EQUAL TO
u'\u228A': u'\u228B', # [BEST FIT] SUBSET OF WITH NOT EQUAL TO
u'\u228B': u'\u228A', # [BEST FIT] SUPERSET OF WITH NOT EQUAL TO
u'\u228F': u'\u2290', # SQUARE IMAGE OF
u'\u2290': u'\u228F', # SQUARE ORIGINAL OF
u'\u2291': u'\u2292', # SQUARE IMAGE OF OR EQUAL TO
u'\u2292': u'\u2291', # SQUARE ORIGINAL OF OR EQUAL TO
u'\u2298': u'\u29B8', # CIRCLED DIVISION SLASH
u'\u22A2': u'\u22A3', # RIGHT TACK
u'\u22A3': u'\u22A2', # LEFT TACK
u'\u22A6': u'\u2ADE', # ASSERTION
u'\u22A8': u'\u2AE4', # TRUE
u'\u22A9': u'\u2AE3', # FORCES
u'\u22AB': u'\u2AE5', # DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
u'\u22B0': u'\u22B1', # PRECEDES UNDER RELATION
u'\u22B1': u'\u22B0', # SUCCEEDS UNDER RELATION
u'\u22B2': u'\u22B3', # NORMAL SUBGROUP OF
u'\u22B3': u'\u22B2', # CONTAINS AS NORMAL SUBGROUP
u'\u22B4': u'\u22B5', # NORMAL SUBGROUP OF OR EQUAL TO
u'\u22B5': u'\u22B4', # CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
u'\u22B6': u'\u22B7', # ORIGINAL OF
u'\u22B7': u'\u22B6', # IMAGE OF
u'\u22C9': u'\u22CA', # LEFT NORMAL FACTOR SEMIDIRECT PRODUCT
u'\u22CA': u'\u22C9', # RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT
u'\u22CB': u'\u22CC', # LEFT SEMIDIRECT PRODUCT
u'\u22CC': u'\u22CB', # RIGHT SEMIDIRECT PRODUCT
u'\u22CD': u'\u2243', # REVERSED TILDE EQUALS
u'\u22D0': u'\u22D1', # DOUBLE SUBSET
u'\u22D1': u'\u22D0', # DOUBLE SUPERSET
u'\u22D6': u'\u22D7', # LESS-THAN WITH DOT
u'\u22D7': u'\u22D6', # GREATER-THAN WITH DOT
u'\u22D8': u'\u22D9', # VERY MUCH LESS-THAN
u'\u22D9': u'\u22D8', # VERY MUCH GREATER-THAN
u'\u22DA': u'\u22DB', # LESS-THAN EQUAL TO OR GREATER-THAN
u'\u22DB': u'\u22DA', # GREATER-THAN EQUAL TO OR LESS-THAN
u'\u22DC': u'\u22DD', # EQUAL TO OR LESS-THAN
u'\u22DD': u'\u22DC', # EQUAL TO OR GREATER-THAN
u'\u22DE': u'\u22DF', # EQUAL TO OR PRECEDES
u'\u22DF': u'\u22DE', # EQUAL TO OR SUCCEEDS
u'\u22E0': u'\u22E1', # [BEST FIT] DOES NOT PRECEDE OR EQUAL
u'\u22E1': u'\u22E0', # [BEST FIT] DOES NOT SUCCEED OR EQUAL
u'\u22E2': u'\u22E3', # [BEST FIT] NOT SQUARE IMAGE OF OR EQUAL TO
u'\u22E3': u'\u22E2', # [BEST FIT] NOT SQUARE ORIGINAL OF OR EQUAL TO
u'\u22E4': u'\u22E5', # [BEST FIT] SQUARE IMAGE OF OR NOT EQUAL TO
u'\u22E5': u'\u22E4', # [BEST FIT] SQUARE ORIGINAL OF OR NOT EQUAL TO
u'\u22E6': u'\u22E7', # [BEST FIT] LESS-THAN BUT NOT EQUIVALENT TO
u'\u22E7': u'\u22E6', # [BEST FIT] GREATER-THAN BUT NOT EQUIVALENT TO
u'\u22E8': u'\u22E9', # [BEST FIT] PRECEDES BUT NOT EQUIVALENT TO
u'\u22E9': u'\u22E8', # [BEST FIT] SUCCEEDS BUT NOT EQUIVALENT TO
u'\u22EA': u'\u22EB', # [BEST FIT] NOT NORMAL SUBGROUP OF
u'\u22EB': u'\u22EA', # [BEST FIT] DOES NOT CONTAIN AS NORMAL SUBGROUP
u'\u22EC': u'\u22ED', # [BEST FIT] NOT NORMAL SUBGROUP OF OR EQUAL TO
u'\u22ED': u'\u22EC', # [BEST FIT] DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
u'\u22F0': u'\u22F1', # UP RIGHT DIAGONAL ELLIPSIS
u'\u22F1': u'\u22F0', # DOWN RIGHT DIAGONAL ELLIPSIS
u'\u22F2': u'\u22FA', # ELEMENT OF WITH LONG HORIZONTAL STROKE
u'\u22F3': u'\u22FB', # ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
u'\u22F4': u'\u22FC', # SMALL ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
u'\u22F6': u'\u22FD', # ELEMENT OF WITH OVERBAR
u'\u22F7': u'\u22FE', # SMALL ELEMENT OF WITH OVERBAR
u'\u22FA': u'\u22F2', # CONTAINS WITH LONG HORIZONTAL STROKE
u'\u22FB': u'\u22F3', # CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
u'\u22FC': u'\u22F4', # SMALL CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
u'\u22FD': u'\u22F6', # CONTAINS WITH OVERBAR
u'\u22FE': u'\u22F7', # SMALL CONTAINS WITH OVERBAR
u'\u2308': u'\u2309', # LEFT CEILING
u'\u2309': u'\u2308', # RIGHT CEILING
u'\u230A': u'\u230B', # LEFT FLOOR
u'\u230B': u'\u230A', # RIGHT FLOOR
u'\u2329': u'\u232A', # LEFT-POINTING ANGLE BRACKET
u'\u232A': u'\u2329', # RIGHT-POINTING ANGLE BRACKET
u'\u2768': u'\u2769', # MEDIUM LEFT PARENTHESIS ORNAMENT
u'\u2769': u'\u2768', # MEDIUM RIGHT PARENTHESIS ORNAMENT
u'\u276A': u'\u276B', # MEDIUM FLATTENED LEFT PARENTHESIS ORNAMENT
u'\u276B': u'\u276A', # MEDIUM FLATTENED RIGHT PARENTHESIS ORNAMENT
u'\u276C': u'\u276D', # MEDIUM LEFT-POINTING ANGLE BRACKET ORNAMENT
u'\u276D': u'\u276C', # MEDIUM RIGHT-POINTING ANGLE BRACKET ORNAMENT
u'\u276E': u'\u276F', # HEAVY LEFT-POINTING ANGLE QUOTATION MARK ORNAMENT
u'\u276F': u'\u276E', # HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT
u'\u2770': u'\u2771', # HEAVY LEFT-POINTING ANGLE BRACKET ORNAMENT
u'\u2771': u'\u2770', # HEAVY RIGHT-POINTING ANGLE BRACKET ORNAMENT
u'\u2772': u'\u2773', # LIGHT LEFT TORTOISE SHELL BRACKET
u'\u2773': u'\u2772', # LIGHT RIGHT TORTOISE SHELL BRACKET
u'\u2774': u'\u2775', # MEDIUM LEFT CURLY BRACKET ORNAMENT
u'\u2775': u'\u2774', # MEDIUM RIGHT CURLY BRACKET ORNAMENT
u'\u27C3': u'\u27C4', # OPEN SUBSET
u'\u27C4': u'\u27C3', # OPEN SUPERSET
u'\u27C5': u'\u27C6', # LEFT S-SHAPED BAG DELIMITER
u'\u27C6': u'\u27C5', # RIGHT S-SHAPED BAG DELIMITER
u'\u27C8': u'\u27C9', # REVERSE SOLIDUS PRECEDING SUBSET
u'\u27C9': u'\u27C8', # SUPERSET PRECEDING SOLIDUS
u'\u27D5': u'\u27D6', # LEFT OUTER JOIN
u'\u27D6': u'\u27D5', # RIGHT OUTER JOIN
u'\u27DD': u'\u27DE', # LONG RIGHT TACK
u'\u27DE': u'\u27DD', # LONG LEFT TACK
u'\u27E2': u'\u27E3', # WHITE CONCAVE-SIDED DIAMOND WITH LEFTWARDS TICK
u'\u27E3': u'\u27E2', # WHITE CONCAVE-SIDED DIAMOND WITH RIGHTWARDS TICK
u'\u27E4': u'\u27E5', # WHITE SQUARE WITH LEFTWARDS TICK
u'\u27E5': u'\u27E4', # WHITE SQUARE WITH RIGHTWARDS TICK
u'\u27E6': u'\u27E7', # MATHEMATICAL LEFT WHITE SQUARE BRACKET
u'\u27E7': u'\u27E6', # MATHEMATICAL RIGHT WHITE SQUARE BRACKET
u'\u27E8': u'\u27E9', # MATHEMATICAL LEFT ANGLE BRACKET
u'\u27E9': u'\u27E8', # MATHEMATICAL RIGHT ANGLE BRACKET
u'\u27EA': u'\u27EB', # MATHEMATICAL LEFT DOUBLE ANGLE BRACKET
u'\u27EB': u'\u27EA', # MATHEMATICAL RIGHT DOUBLE ANGLE BRACKET
u'\u27EC': u'\u27ED', # MATHEMATICAL LEFT WHITE TORTOISE SHELL BRACKET
u'\u27ED': u'\u27EC', # MATHEMATICAL RIGHT WHITE TORTOISE SHELL BRACKET
u'\u27EE': u'\u27EF', # MATHEMATICAL LEFT FLATTENED PARENTHESIS
u'\u27EF': u'\u27EE', # MATHEMATICAL RIGHT FLATTENED PARENTHESIS
u'\u2983': u'\u2984', # LEFT WHITE CURLY BRACKET
u'\u2984': u'\u2983', # RIGHT WHITE CURLY BRACKET
u'\u2985': u'\u2986', # LEFT WHITE PARENTHESIS
u'\u2986': u'\u2985', # RIGHT WHITE PARENTHESIS
u'\u2987': u'\u2988', # Z NOTATION LEFT IMAGE BRACKET
u'\u2988': u'\u2987', # Z NOTATION RIGHT IMAGE BRACKET
u'\u2989': u'\u298A', # Z NOTATION LEFT BINDING BRACKET
u'\u298A': u'\u2989', # Z NOTATION RIGHT BINDING BRACKET
u'\u298B': u'\u298C', # LEFT SQUARE BRACKET WITH UNDERBAR
u'\u298C': u'\u298B', # RIGHT SQUARE BRACKET WITH UNDERBAR
u'\u298D': u'\u2990', # LEFT SQUARE BRACKET WITH TICK IN TOP CORNER
u'\u298E': u'\u298F', # RIGHT SQUARE BRACKET WITH TICK IN BOTTOM CORNER
u'\u298F': u'\u298E', # LEFT SQUARE BRACKET WITH TICK IN BOTTOM CORNER
u'\u2990': u'\u298D', # RIGHT SQUARE BRACKET WITH TICK IN TOP CORNER
u'\u2991': u'\u2992', # LEFT ANGLE BRACKET WITH DOT
u'\u2992': u'\u2991', # RIGHT ANGLE BRACKET WITH DOT
u'\u2993': u'\u2994', # LEFT ARC LESS-THAN BRACKET
u'\u2994': u'\u2993', # RIGHT ARC GREATER-THAN BRACKET
u'\u2995': u'\u2996', # DOUBLE LEFT ARC GREATER-THAN BRACKET
u'\u2996': u'\u2995', # DOUBLE RIGHT ARC LESS-THAN BRACKET
u'\u2997': u'\u2998', # LEFT BLACK TORTOISE SHELL BRACKET
u'\u2998': u'\u2997', # RIGHT BLACK TORTOISE SHELL BRACKET
u'\u29B8': u'\u2298', # CIRCLED REVERSE SOLIDUS
u'\u29C0': u'\u29C1', # CIRCLED LESS-THAN
u'\u29C1': u'\u29C0', # CIRCLED GREATER-THAN
u'\u29C4': u'\u29C5', # SQUARED RISING DIAGONAL SLASH
u'\u29C5': u'\u29C4', # SQUARED FALLING DIAGONAL SLASH
u'\u29CF': u'\u29D0', # LEFT TRIANGLE BESIDE VERTICAL BAR
u'\u29D0': u'\u29CF', # VERTICAL BAR BESIDE RIGHT TRIANGLE
u'\u29D1': u'\u29D2', # BOWTIE WITH LEFT HALF BLACK
u'\u29D2': u'\u29D1', # BOWTIE WITH RIGHT HALF BLACK
u'\u29D4': u'\u29D5', # TIMES WITH LEFT HALF BLACK
u'\u29D5': u'\u29D4', # TIMES WITH RIGHT HALF BLACK
u'\u29D8': u'\u29D9', # LEFT WIGGLY FENCE
u'\u29D9': u'\u29D8', # RIGHT WIGGLY FENCE
u'\u29DA': u'\u29DB', # LEFT DOUBLE WIGGLY FENCE
u'\u29DB': u'\u29DA', # RIGHT DOUBLE WIGGLY FENCE
u'\u29F5': u'\u2215', # REVERSE SOLIDUS OPERATOR
u'\u29F8': u'\u29F9', # BIG SOLIDUS
u'\u29F9': u'\u29F8', # BIG REVERSE SOLIDUS
u'\u29FC': u'\u29FD', # LEFT-POINTING CURVED ANGLE BRACKET
u'\u29FD': u'\u29FC', # RIGHT-POINTING CURVED ANGLE BRACKET
u'\u2A2B': u'\u2A2C', # MINUS SIGN WITH FALLING DOTS
u'\u2A2C': u'\u2A2B', # MINUS SIGN WITH RISING DOTS
u'\u2A2D': u'\u2A2E', # PLUS SIGN IN LEFT HALF CIRCLE
u'\u2A2E': u'\u2A2D', # PLUS SIGN IN RIGHT HALF CIRCLE
u'\u2A34': u'\u2A35', # MULTIPLICATION SIGN IN LEFT HALF CIRCLE
u'\u2A35': u'\u2A34', # MULTIPLICATION SIGN IN RIGHT HALF CIRCLE
u'\u2A3C': u'\u2A3D', # INTERIOR PRODUCT
u'\u2A3D': u'\u2A3C', # RIGHTHAND INTERIOR PRODUCT
u'\u2A64': u'\u2A65', # Z NOTATION DOMAIN ANTIRESTRICTION
u'\u2A65': u'\u2A64', # Z NOTATION RANGE ANTIRESTRICTION
u'\u2A79': u'\u2A7A', # LESS-THAN WITH CIRCLE INSIDE
u'\u2A7A': u'\u2A79', # GREATER-THAN WITH CIRCLE INSIDE
u'\u2A7D': u'\u2A7E', # LESS-THAN OR SLANTED EQUAL TO
u'\u2A7E': u'\u2A7D', # GREATER-THAN OR SLANTED EQUAL TO
u'\u2A7F': u'\u2A80', # LESS-THAN OR SLANTED EQUAL TO WITH DOT INSIDE
u'\u2A80': u'\u2A7F', # GREATER-THAN OR SLANTED EQUAL TO WITH DOT INSIDE
u'\u2A81': u'\u2A82', # LESS-THAN OR SLANTED EQUAL TO WITH DOT ABOVE
u'\u2A82': u'\u2A81', # GREATER-THAN OR SLANTED EQUAL TO WITH DOT ABOVE
u'\u2A83': u'\u2A84', # LESS-THAN OR SLANTED EQUAL TO WITH DOT ABOVE RIGHT
u'\u2A84': u'\u2A83', # GREATER-THAN OR SLANTED EQUAL TO WITH DOT ABOVE LEFT
u'\u2A8B': u'\u2A8C', # LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN
u'\u2A8C': u'\u2A8B', # GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN
u'\u2A91': u'\u2A92', # LESS-THAN ABOVE GREATER-THAN ABOVE DOUBLE-LINE EQUAL
u'\u2A92': u'\u2A91', # GREATER-THAN ABOVE LESS-THAN ABOVE DOUBLE-LINE EQUAL
u'\u2A93': u'\u2A94', # LESS-THAN ABOVE SLANTED EQUAL ABOVE GREATER-THAN ABOVE SLANTED EQUAL
u'\u2A94': u'\u2A93', # GREATER-THAN ABOVE SLANTED EQUAL ABOVE LESS-THAN ABOVE SLANTED EQUAL
u'\u2A95': u'\u2A96', # SLANTED EQUAL TO OR LESS-THAN
u'\u2A96': u'\u2A95', # SLANTED EQUAL TO OR GREATER-THAN
u'\u2A97': u'\u2A98', # SLANTED EQUAL TO OR LESS-THAN WITH DOT INSIDE
u'\u2A98': u'\u2A97', # SLANTED EQUAL TO OR GREATER-THAN WITH DOT INSIDE
u'\u2A99': u'\u2A9A', # DOUBLE-LINE EQUAL TO OR LESS-THAN
u'\u2A9A': u'\u2A99', # DOUBLE-LINE EQUAL TO OR GREATER-THAN
u'\u2A9B': u'\u2A9C', # DOUBLE-LINE SLANTED EQUAL TO OR LESS-THAN
u'\u2A9C': u'\u2A9B', # DOUBLE-LINE SLANTED EQUAL TO OR GREATER-THAN
u'\u2AA1': u'\u2AA2', # DOUBLE NESTED LESS-THAN
u'\u2AA2': u'\u2AA1', # DOUBLE NESTED GREATER-THAN
u'\u2AA6': u'\u2AA7', # LESS-THAN CLOSED BY CURVE
u'\u2AA7': u'\u2AA6', # GREATER-THAN CLOSED BY CURVE
u'\u2AA8': u'\u2AA9', # LESS-THAN CLOSED BY CURVE ABOVE SLANTED EQUAL
u'\u2AA9': u'\u2AA8', # GREATER-THAN CLOSED BY CURVE ABOVE SLANTED EQUAL
u'\u2AAA': u'\u2AAB', # SMALLER THAN
u'\u2AAB': u'\u2AAA', # LARGER THAN
u'\u2AAC': u'\u2AAD', # SMALLER THAN OR EQUAL TO
u'\u2AAD': u'\u2AAC', # LARGER THAN OR EQUAL TO
u'\u2AAF': u'\u2AB0', # PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
u'\u2AB0': u'\u2AAF', # SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
u'\u2AB3': u'\u2AB4', # PRECEDES ABOVE EQUALS SIGN
u'\u2AB4': u'\u2AB3', # SUCCEEDS ABOVE EQUALS SIGN
u'\u2ABB': u'\u2ABC', # DOUBLE PRECEDES
u'\u2ABC': u'\u2ABB', # DOUBLE SUCCEEDS
u'\u2ABD': u'\u2ABE', # SUBSET WITH DOT
u'\u2ABE': u'\u2ABD', # SUPERSET WITH DOT
u'\u2ABF': u'\u2AC0', # SUBSET WITH PLUS SIGN BELOW
u'\u2AC0': u'\u2ABF', # SUPERSET WITH PLUS SIGN BELOW
u'\u2AC1': u'\u2AC2', # SUBSET WITH MULTIPLICATION SIGN BELOW
u'\u2AC2': u'\u2AC1', # SUPERSET WITH MULTIPLICATION SIGN BELOW
u'\u2AC3': u'\u2AC4', # SUBSET OF OR EQUAL TO WITH DOT ABOVE
u'\u2AC4': u'\u2AC3', # SUPERSET OF OR EQUAL TO WITH DOT ABOVE
u'\u2AC5': u'\u2AC6', # SUBSET OF ABOVE EQUALS SIGN
u'\u2AC6': u'\u2AC5', # SUPERSET OF ABOVE EQUALS SIGN
u'\u2ACD': u'\u2ACE', # SQUARE LEFT OPEN BOX OPERATOR
u'\u2ACE': u'\u2ACD', # SQUARE RIGHT OPEN BOX OPERATOR
u'\u2ACF': u'\u2AD0', # CLOSED SUBSET
u'\u2AD0': u'\u2ACF', # CLOSED SUPERSET
u'\u2AD1': u'\u2AD2', # CLOSED SUBSET OR EQUAL TO
u'\u2AD2': u'\u2AD1', # CLOSED SUPERSET OR EQUAL TO
u'\u2AD3': u'\u2AD4', # SUBSET ABOVE SUPERSET
u'\u2AD4': u'\u2AD3', # SUPERSET ABOVE SUBSET
u'\u2AD5': u'\u2AD6', # SUBSET ABOVE SUBSET
u'\u2AD6': u'\u2AD5', # SUPERSET ABOVE SUPERSET
u'\u2ADE': u'\u22A6', # SHORT LEFT TACK
u'\u2AE3': u'\u22A9', # DOUBLE VERTICAL BAR LEFT TURNSTILE
u'\u2AE4': u'\u22A8', # VERTICAL BAR DOUBLE LEFT TURNSTILE
u'\u2AE5': u'\u22AB', # DOUBLE VERTICAL BAR DOUBLE LEFT TURNSTILE
u'\u2AEC': u'\u2AED', # DOUBLE STROKE NOT SIGN
u'\u2AED': u'\u2AEC', # REVERSED DOUBLE STROKE NOT SIGN
u'\u2AF7': u'\u2AF8', # TRIPLE NESTED LESS-THAN
u'\u2AF8': u'\u2AF7', # TRIPLE NESTED GREATER-THAN
u'\u2AF9': u'\u2AFA', # DOUBLE-LINE SLANTED LESS-THAN OR EQUAL TO
u'\u2AFA': u'\u2AF9', # DOUBLE-LINE SLANTED GREATER-THAN OR EQUAL TO
u'\u2E02': u'\u2E03', # LEFT SUBSTITUTION BRACKET
u'\u2E03': u'\u2E02', # RIGHT SUBSTITUTION BRACKET
u'\u2E04': u'\u2E05', # LEFT DOTTED SUBSTITUTION BRACKET
u'\u2E05': u'\u2E04', # RIGHT DOTTED SUBSTITUTION BRACKET
u'\u2E09': u'\u2E0A', # LEFT TRANSPOSITION BRACKET
u'\u2E0A': u'\u2E09', # RIGHT TRANSPOSITION BRACKET
u'\u2E0C': u'\u2E0D', # LEFT RAISED OMISSION BRACKET
u'\u2E0D': u'\u2E0C', # RIGHT RAISED OMISSION BRACKET
u'\u2E1C': u'\u2E1D', # LEFT LOW PARAPHRASE BRACKET
u'\u2E1D': u'\u2E1C', # RIGHT LOW PARAPHRASE BRACKET
u'\u2E20': u'\u2E21', # LEFT VERTICAL BAR WITH QUILL
u'\u2E21': u'\u2E20', # RIGHT VERTICAL BAR WITH QUILL
u'\u2E22': u'\u2E23', # TOP LEFT HALF BRACKET
u'\u2E23': u'\u2E22', # TOP RIGHT HALF BRACKET
u'\u2E24': u'\u2E25', # BOTTOM LEFT HALF BRACKET
u'\u2E25': u'\u2E24', # BOTTOM RIGHT HALF BRACKET
u'\u2E26': u'\u2E27', # LEFT SIDEWAYS U BRACKET
u'\u2E27': u'\u2E26', # RIGHT SIDEWAYS U BRACKET
u'\u2E28': u'\u2E29', # LEFT DOUBLE PARENTHESIS
u'\u2E29': u'\u2E28', # RIGHT DOUBLE PARENTHESIS
u'\u3008': u'\u3009', # LEFT ANGLE BRACKET
u'\u3009': u'\u3008', # RIGHT ANGLE BRACKET
u'\u300A': u'\u300B', # LEFT DOUBLE ANGLE BRACKET
u'\u300B': u'\u300A', # RIGHT DOUBLE ANGLE BRACKET
u'\u300C': u'\u300D', # [BEST FIT] LEFT CORNER BRACKET
u'\u300D': u'\u300C', # [BEST FIT] RIGHT CORNER BRACKET
u'\u300E': u'\u300F', # [BEST FIT] LEFT WHITE CORNER BRACKET
u'\u300F': u'\u300E', # [BEST FIT] RIGHT WHITE CORNER BRACKET
u'\u3010': u'\u3011', # LEFT BLACK LENTICULAR BRACKET
u'\u3011': u'\u3010', # RIGHT BLACK LENTICULAR BRACKET
u'\u3014': u'\u3015', # LEFT TORTOISE SHELL BRACKET
u'\u3015': u'\u3014', # RIGHT TORTOISE SHELL BRACKET
u'\u3016': u'\u3017', # LEFT WHITE LENTICULAR BRACKET
u'\u3017': u'\u3016', # RIGHT WHITE LENTICULAR BRACKET
u'\u3018': u'\u3019', # LEFT WHITE TORTOISE SHELL BRACKET
u'\u3019': u'\u3018', # RIGHT WHITE TORTOISE SHELL BRACKET
u'\u301A': u'\u301B', # LEFT WHITE SQUARE BRACKET
u'\u301B': u'\u301A', # RIGHT WHITE SQUARE BRACKET
u'\uFE59': u'\uFE5A', # SMALL LEFT PARENTHESIS
u'\uFE5A': u'\uFE59', # SMALL RIGHT PARENTHESIS
u'\uFE5B': u'\uFE5C', # SMALL LEFT CURLY BRACKET
u'\uFE5C': u'\uFE5B', # SMALL RIGHT CURLY BRACKET
u'\uFE5D': u'\uFE5E', # SMALL LEFT TORTOISE SHELL BRACKET
u'\uFE5E': u'\uFE5D', # SMALL RIGHT TORTOISE SHELL BRACKET
u'\uFE64': u'\uFE65', # SMALL LESS-THAN SIGN
u'\uFE65': u'\uFE64', # SMALL GREATER-THAN SIGN
u'\uFF08': u'\uFF09', # FULLWIDTH LEFT PARENTHESIS
u'\uFF09': u'\uFF08', # FULLWIDTH RIGHT PARENTHESIS
u'\uFF1C': u'\uFF1E', # FULLWIDTH LESS-THAN SIGN
u'\uFF1E': u'\uFF1C', # FULLWIDTH GREATER-THAN SIGN
u'\uFF3B': u'\uFF3D', # FULLWIDTH LEFT SQUARE BRACKET
u'\uFF3D': u'\uFF3B', # FULLWIDTH RIGHT SQUARE BRACKET
u'\uFF5B': u'\uFF5D', # FULLWIDTH LEFT CURLY BRACKET
u'\uFF5D': u'\uFF5B', # FULLWIDTH RIGHT CURLY BRACKET
u'\uFF5F': u'\uFF60', # FULLWIDTH LEFT WHITE PARENTHESIS
u'\uFF60': u'\uFF5F', # FULLWIDTH RIGHT WHITE PARENTHESIS
u'\uFF62': u'\uFF63', # [BEST FIT] HALFWIDTH LEFT CORNER BRACKET
u'\uFF63': u'\uFF62', # [BEST FIT] HALFWIDTH RIGHT CORNER BRACKET
}

########NEW FILE########
__FILENAME__ = tests
# This file is part of python-bidi
#
# python-bidi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2008-2010 Yaacov Zamir <kzamir_a_walla.co.il>,
# Meir kriheli <meir@mksoft.co.il>
"""BiDi algorithm unit tests"""

import unittest
from bidi.algorithm import get_display, get_empty_storage, get_embedding_levels

class TestBidiAlgorithm(unittest.TestCase):
    "Tests the bidi algorithm (based on GNU fribidi ones)"

    def test_surrogate(self):
        """Test for storage and base levels in case of surrogate pairs"""

        storage = get_empty_storage()

        text = u'HELLO \U0001d7f612'
        get_embedding_levels(text, storage, upper_is_rtl=True)

        # should return 9, not 10 even in --with-unicode=ucs2
        self.assertEqual(len(storage['chars']), 9)

        # Is the expected result ? should be EN
        _ch = storage['chars'][6]
        self.assertEqual(_ch['ch'], u'\U0001d7f6')
        self.assertEqual(_ch['type'], 'EN')

        display = get_display(text, upper_is_rtl=True)
        self.assertEqual(display, u'\U0001d7f612 OLLEH')

    def test_implict_with_upper_is_rtl(self):
        '''Implicit tests'''

        tests = (
            (u'car is THE CAR in arabic', u'car is RAC EHT in arabic'),
            (u'CAR IS the car IN ENGLISH', u'HSILGNE NI the car SI RAC'),
            (u'he said "IT IS 123, 456, OK"', u'he said "KO ,456 ,123 SI TI"'),
            (u'he said "IT IS (123, 456), OK"', u'he said "KO ,(456 ,123) SI TI"'),
            (u'he said "IT IS 123,456, OK"', u'he said "KO ,123,456 SI TI"'),
            (u'he said "IT IS (123,456), OK"', u'he said "KO ,(123,456) SI TI"'),
            (u'HE SAID "it is 123, 456, ok"', u'"it is 123, 456, ok" DIAS EH'),
            (u'<H123>shalom</H123>', u'<123H/>shalom<123H>'),
            (u'<h123>SAALAM</h123>', u'<h123>MALAAS</h123>'),
            (u'HE SAID "it is a car!" AND RAN', u'NAR DNA "!it is a car" DIAS EH'),
            (u'HE SAID "it is a car!x" AND RAN', u'NAR DNA "it is a car!x" DIAS EH'),
            (u'SOLVE 1*5 1-5 1/5 1+5', u'1+5 1/5 1-5 5*1 EVLOS'),
            (u'THE RANGE IS 2.5..5', u'5..2.5 SI EGNAR EHT'),
            (u'-2 CELSIUS IS COLD', u'DLOC SI SUISLEC 2-'),
        )

        for storage, display in tests:
            self.assertEqual(get_display(storage, upper_is_rtl=True), display)

    def test_override_base_dir(self):
        """Tests overriding the base paragraph direction"""

        # normaly the display should be :MOLAHS be since we're overriding the
        # base dir the colon should be at the end of the display
        storage = u'SHALOM:'
        display = u'MOLAHS:'

        self.assertEqual(get_display(storage, upper_is_rtl=True, base_dir='L'), display)



    def test_output_encoding(self):
        """Make sure the display is in the same encdoing as the incoming text"""

        storage = '\xf9\xec\xe5\xed'        # Hebrew word shalom in cp1255
        display = '\xed\xe5\xec\xf9'

        self.assertEqual(get_display(storage, encoding='cp1255'), display)


    def test_explicit_with_upper_is_rtl(self):
        """Explicit tests"""
        tests = (
            (u'this is _LJUST_o', u'this is JUST'),
            (u'a _lsimple _RteST_o th_oat', u'a simple TSet that'),
            (u'HAS A _LPDF missing', u'PDF missing A SAH'),
            (u'AnD hOw_L AbOuT, 123,987 tHiS_o', u'w AbOuT, 123,987 tHiSOh DnA'),
            (u'a GOOD - _L_oTEST.', u'a TSET - DOOG.'),
            (u'here_L is_o_o_o _R a good one_o', u'here is eno doog a'),
            (u'THE _rbest _lONE and', u'best ENO and EHT'),
            (u'A REAL BIG_l_o BUG!', u'!GUB GIB LAER A'),
            (u'a _L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_L_Rbug', u'a gub'),
            (u'AN ARABIC _l_o 123-456 NICE ONE!', u'!ENO ECIN 456-123  CIBARA NA'),
            (u'AN ARABIC _l _o 123-456 PAIR', u'RIAP   123-456 CIBARA NA'),
            (u'this bug 67_r_o89 catched!', u'this bug 6789 catched!'),
        )

        # adopt fribidi's CapRtl encoding
        mappings = {
            u'_>': u"\u200E",
            u'_<': u"\u200F",
            u'_l': u"\u202A",
            u'_r': u"\u202B",
            u'_o': u"\u202C",
            u'_L': u"\u202D",
            u'_R': u"\u202E",
            u'__': '_',
        }

        for storage, display in tests:
            for key, val in mappings.items():
                storage = storage.replace(key, val)
            self.assertEqual(get_display(storage, upper_is_rtl=True), display)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = rtl
import sublime, sublime_plugin, sys

sys.path.append( 'bidi' )
try:

    # Python 3

    from .bidi.arabic_reshaper import reshape
    from .bidi.algorithm import get_display
except ValueError:

    # Python 2

    from bidi.arabic_reshaper import reshape
    from bidi.algorithm import get_display

class bidiCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		region = sublime.Region(0, self.view.size())
		txt = self.view.substr(region)
		reshaped_text = reshape(txt)
		bdiText = get_display(reshaped_text)
		self.view.replace(edit, region, bdiText)

########NEW FILE########
