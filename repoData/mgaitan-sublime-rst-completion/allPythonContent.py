__FILENAME__ = footnotes
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
import re

DEFINITION_KEY = 'footnote-definitions'
REFERENCE_KEY = 'footnote-references'
REFERENCE_REGEX = r'\[(\d+)\]\_'
DEFINITION_REGEX = r"^\.\.\s\[(\d+)\]"


def get_id(txt):
    return re.findall(r'\d+', txt)[0]


def get_footnote_references(view):
    ids = {}
    for ref in view.get_regions(REFERENCE_KEY):
        view.substr(view.line(ref))
        if not re.match(DEFINITION_REGEX, view.substr(view.line(ref))):
            id = get_id(view.substr(ref))
            if id in ids:
                ids[id].append(ref)
            else:
                ids[id] = [ref]
    return ids


def get_footnote_definition_markers(view):
    ids = {}
    for defn in view.get_regions(DEFINITION_KEY):
        id = get_id(view.substr(defn))
        ids[id] = defn
    return ids


def get_footnote_identifiers(view):
    ids = get_footnote_references(view).keys()
    ids.sort()
    return ids


def get_last_footnote_marker(view):
    ids = sorted([int(a) for a in get_footnote_identifiers(view) if a.isdigit()])
    if len(ids):
        return int(ids[-1])
    else:
        return 0


def get_next_footnote_marker(view):
    return get_last_footnote_marker(view) + 1


def is_footnote_definition(view):
    line = view.substr(view.line(view.sel()[-1]))
    return re.match(DEFINITION_REGEX, line)


def is_footnote_reference(view):
    refs = view.get_regions(REFERENCE_KEY)
    for ref in refs:
        if ref.contains(view.sel()[0]):
            return True
    return False


def strip_trailing_whitespace(view, edit):
    tws = view.find('\s+\Z', 0)
    if tws:
        view.erase(edit, tws)


class Footnotes(sublime_plugin.EventListener):
    def update_footnote_data(self, view):
        view.add_regions(REFERENCE_KEY,
                         view.find_all(REFERENCE_REGEX),
                         '', 'cross',
                         )
        view.add_regions(DEFINITION_KEY,
                         view.find_all(DEFINITION_REGEX),
                         '',
                         'cross',
                         )

    def on_modified(self, view):
        self.update_footnote_data(view)

    def on_load(self, view):
        self.update_footnote_data(view)


class MagicFootnotesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if (is_footnote_definition(self.view)):
            self.view.run_command('go_to_footnote_reference')
        elif (is_footnote_reference(self.view)):
            self.view.run_command('go_to_footnote_definition')
        else:
            self.view.run_command('insert_footnote')

    def is_enabled(self):
        return bool(self.view.sel())


class InsertFootnoteCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        edit = self.view.begin_edit()
        startloc = self.view.sel()[-1].end()
        markernum = get_next_footnote_marker(self.view)
        if bool(self.view.size()):
            targetloc = self.view.find('(\s|$)', startloc).begin()
        else:
            targetloc = 0
        self.view.insert(edit, targetloc, '[%s]_' % markernum)
        self.view.insert(edit, self.view.size(), '\n.. [%s] ' % markernum)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(self.view.size()))
        self.view.end_edit(edit)
        self.view.show(self.view.size())

    def is_enabled(self):
        return bool(self.view.sel())


class MarkFootnotes(sublime_plugin.EventListener):
    def update_footnote_data(self, view):
        view.add_regions(REFERENCE_KEY, view.find_all(REFERENCE_REGEX), '', 'cross', sublime.HIDDEN)
        view.add_regions(DEFINITION_KEY, view.find_all(DEFINITION_REGEX), '', 'cross', sublime.HIDDEN)

    def on_modified(self, view):
        self.update_footnote_data(view)

    def on_load(self, view):
        self.update_footnote_data(view)


class GoToFootnoteReferenceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        refs = get_footnote_references(self.view)
        match = is_footnote_definition(self.view)
        if match:
            target = match.groups()[0]
            self.view.sel().clear()
            note = refs[target][0]
            point = sublime.Region(note.end(), note.end())
            self.view.sel().add(point)
            self.view.show(note)

    def is_enabled(self):
        return bool(self.view.sel())


class GoToFootnoteDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        defs = get_footnote_definition_markers(self.view)
        regions = self.view.get_regions(REFERENCE_KEY)

        sel = self.view.sel()
        if len(sel) == 1:
            target = None
            selreg = sel[0]

            for region in regions:
                # cursor beetwen the brackects
                #  ·[X]·_
                if selreg.intersects(region):
                    target = self.view.substr(region)[1:-2]
            if not target:
                # cursor is just after the underscore: [X]_·
                try:
                    a = self.view.find(REFERENCE_REGEX, sel[0].end() - 4)
                    target = self.view.substr(a)[1:-2]
                except:
                    pass
            if target:
                self.view.sel().clear()
                point = defs[target].end() + 1
                ref = sublime.Region(point, point)
                self.view.sel().add(ref)
                self.view.show(defs[target])

    def is_enabled(self):
        return bool(self.view.sel())

########NEW FILE########
__FILENAME__ = headers
import sublime
import sublime_plugin
import re
from collections import namedtuple
# py3 import compatibility. Better way to do this?
try:
    from .helpers import BaseBlockCommand
except ValueError:
    from helpers import BaseBlockCommand    # NOQA


# reference:
#   http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#sections
ADORNMENTS = r"""[!\"#$%&'\\()*+,\-./:;<=>?@\[\]\^_`{|}~]"""
PATTERN_RE = re.compile(r"^(%s*)\n(.+)\n(%s+)" % (ADORNMENTS, ADORNMENTS), re.MULTILINE)

Header = namedtuple('Header', "level start end adornment title raw idx")


class RstHeaderTree(object):
    # based on sphinx's header conventions
    DEFAULT_HEADERS = '** = - ^ " + ~ # \' :'.split()

    def __init__(self, text):
        # add a ficticius break as first line
        # to allow catching a very first header without overline.
        # This imply any position returned (Header.start, Header.end)
        # must be decremented one character

        self.headers = self._parse('\n' + text)
        self._text_lenght = len(text)

    def _parse(self, text):
        """
        Given a chunk of restructuredText, returns a list of tuples
        (level, start, end, adornment, title, raw) for each header found.


        level: int (zero-based). the "weight" of the header.
        start: index where the header starts
        end: index where the header ends
        adornment: one (just underlined) or two char
                    (over and underline) string
                    that represent the adornment,
        title: the parsed title
        raw : the raw parsed header text, including breaks.

        """

        candidates = PATTERN_RE.findall(text)
        headers = []
        levels = []
        idx = 0

        for over, title, under in candidates:
            # validate.
            if ((over == '' or over == under) and len(under) >= len(title)
                    and len(set(under)) == 1):
                # encode the adornment of the header to calculate its level
                adornment = under[0] * (2 if over else 1)
                if adornment not in levels:
                    levels.append(adornment)
                level = levels.index(adornment)
                raw = (over + '\n' if over else '') + title + '\n' + under
                start = text.find(raw) - 1  # see comment on __init__
                end = start + len(raw)
                h = Header(level, start, end, adornment, title, raw, idx)
                idx += 1
                headers.append(h)
        return headers

    def belong_to(self, pos):
        """
        given a cursor position, return the deeper header
        that contains it
        """
        match = []
        for h in self.headers:
            start, end = self.region(h)
            if start <= pos <= end:
                match.append(h)
        try:
            return sorted(match, key=lambda h: h.level, reverse=True)[0]
        except IndexError:
            return None

    def region(self, header):
        """
        determines the (start, end) region under the given header
        A region ends when a header of the same or higher level
        (i.e lower number) is found or at the EOF
        """

        try:
            index = self.headers.index(header)
        except ValueError:
            return

        start = header.start
        if index == len(self.headers) - 1:     # last header
            return (start, self._text_lenght)

        for next_h in self.headers[index + 1:]:
            if next_h.level <= header.level:
                return (start, next_h.start - 1)

        return (start, self._text_lenght)

    def _index(self, header, same_or_high=False):
        """
        helper method that returns the absolute index
        of the header in the tree or a filteredr tree
        If same_or_high is true, only move to headline with the same level
        or higher level.

        returns (index, headers)
        """
        if same_or_high:
            headers = [h for h in self.headers
                       if h.level <= header.level]
        else:
            headers = self.headers[:]
        return headers.index(header), headers

    def next(self, header, same_or_high=False):
        """
        given a header returns the closer header
        (down direction)
        """
        index, headers = self._index(header, same_or_high)
        try:
            return headers[index + 1]
        except IndexError:
            return None

    def prev(self, header, same_or_high=False, offset=-1):
        """same than next, but in reversed direction
        """
        index, headers = self._index(header, same_or_high)
        if index == 0:
            return None
        return headers[index + offset]

    def levels(self):
        """ returns the heading adornment map"""
        _levels = RstHeaderTree.DEFAULT_HEADERS.copy()
        for h in self.headers:
            _levels[h.level] = h.adornment
        levels = []
        for adornment in _levels:
            if adornment not in levels:
                levels.append(adornment)
        for adornment in RstHeaderTree.DEFAULT_HEADERS:
            if adornment not in levels:
                if len(adornment) == 2:
                    levels.insert(0, adornment)
                else:
                    levels.append(adornment)
        return levels

    @classmethod
    def make_header(cls, title, adornment, force_overline=False):
        title = title.rstrip()
        title_lenght = len(title.lstrip())
        indent_lenght = len(title) - title_lenght
        strike = adornment[0] * (title_lenght + indent_lenght * 2)
        if force_overline or len(adornment) == 2:
            result = strike + '\n' + title + '\n' + strike + '\n'
        else:
            result = title + '\n' + strike + '\n'
        return result


class HeaderChangeLevelCommand(sublime_plugin.TextCommand):
    """
    increase or decrease the header level,
    The level markup is autodetected from the document,
    and use sphinx's convention by default.
    """
    views = {}

    def run(self, edit, offset=-1):
        vid = self.view.id()
        HeaderChangeLevelEvent.listen.pop(vid, None)

        cursor_pos = self.view.sel()[0].begin()
        region = sublime.Region(0, self.view.size())
        tree = RstHeaderTree(self.view.substr(region))

        parent = tree.belong_to(cursor_pos)

        is_in_header = parent.start <= cursor_pos <= parent.end
        if not is_in_header:
            return

        idx, levels = HeaderChangeLevelCommand.views.get(vid, (None, None))
        if idx != parent.idx:
            levels = tree.levels()
            HeaderChangeLevelCommand.views[vid] = (parent.idx, levels)

        try:
            level = levels.index(parent.adornment)
            if level + offset < 0:
                return
            adornment = levels[level + offset]
        except IndexError:
            return

        new_header = RstHeaderTree.make_header(parent.title, adornment)
        hregion = sublime.Region(parent.start, parent.end + 1)

        try:
            self.view.replace(edit, hregion, new_header)
        finally:
            def callback():
                HeaderChangeLevelEvent.listen[vid] = True
            sublime.set_timeout(callback, 0)


class HeaderChangeLevelEvent(sublime_plugin.EventListener):
    listen = {}

    def on_modified(self, view):
        vid = view.id()
        if HeaderChangeLevelEvent.listen.get(vid):
            del HeaderChangeLevelCommand.views[vid]
            del HeaderChangeLevelEvent.listen[vid]


class HeadlineMoveCommand(sublime_plugin.TextCommand):
    # briefly inspired on the code of Muchenxuan Tong in
    # https://github.com/demon386/SmartMarkdown

    def run(self, edit, forward=True, same_or_high=True):
        """Move between headlines, forward or backward.

        If same_or_high is true, only move to headline with the same level
        or higher level.

        """
        cursor_pos = self.view.sel()[0].begin()
        region = sublime.Region(0, self.view.size())
        tree = RstHeaderTree(self.view.substr(region))
        parent = tree.belong_to(cursor_pos)

        if forward:
            h = tree.next(parent, same_or_high)
        else:
            is_in_header = parent.start <= cursor_pos <= parent.end
            offset = -1 if is_in_header else 0
            h = tree.prev(parent, same_or_high, offset)
        if h:
            self.jump_to(h.end - len(h.raw.split('\n')[-1]) - 1)

    def jump_to(self, pos):
        region = sublime.Region(pos, pos)
        self.view.sel().clear()
        self.view.sel().add(region)
        self.view.show(region)


class SmartFoldingCommand(sublime_plugin.TextCommand):
    """Smart folding is used to fold / unfold headline at the point.

    It's designed to bind to TAB key, and if the current line is not
    a headline, a \t would be inserted.

    """
    def run(self, edit):

        cursor_pos = self.view.sel()[0].begin()
        region = sublime.Region(0, self.view.size())
        tree = RstHeaderTree(self.view.substr(region))
        parent = tree.belong_to(cursor_pos)
        is_in_header = parent.start <= cursor_pos <= parent.end
        if is_in_header:
            start, end = tree.region(parent)
            start += len(parent.raw) + 1
            region = sublime.Region(start, end)
            if any([i.contains(region) for i in
                    self.view.folded_regions()]):
                self.view.unfold(region)
            else:
                self.view.fold(region)
        else:
            for r in self.view.sel():
                self.view.insert(edit, r.a, '\t')
                self.view.show(r)


class SmartHeaderCommand(BaseBlockCommand):
    def run(self, edit):
        for region in self.view.sel():
            region, lines, indent = self.get_block_bounds()
            head_lines = len(lines)
            adornment_char = lines[-1][0]

            if (head_lines not in (2, 3) or
                    head_lines == 3 and lines[-3][0] != adornment_char):
                # invalid header
                return

            title = lines[-2]
            force_overline = head_lines == 3
            result = RstHeaderTree.make_header(title, adornment_char, force_overline)
            self.view.replace(edit, region, result)

########NEW FILE########
__FILENAME__ = helpers
import re

from sublime import Region
import sublime_plugin


class LineIndexError(Exception):
    pass


class BaseBlockCommand(sublime_plugin.TextCommand):
    def _get_row_text(self, row):

        if row < 0 or row > self.view.rowcol(self.view.size())[0]:
            raise LineIndexError('Cannot find table bounds.')

        point = self.view.text_point(row, 0)
        region = self.view.line(point)
        text = self.view.substr(region)
        return text

    def get_cursor_position(self):
        return self.view.rowcol(self.view.sel()[0].begin())

    def get_block_bounds(self):
        """given the cursor position as started point,
           returns the limits and indentation"""
        row, col = self.get_cursor_position()
        upper = lower = row

        try:
            while self._get_row_text(upper - 1).strip():
                upper -= 1
        except LineIndexError:
            pass
        else:
            upper += 1

        try:
            while self._get_row_text(lower + 1).strip():
                lower += 1
        except LineIndexError:
            pass
        else:
            lower -= 1

        block_region = Region(self.view.text_point(upper - 1, 0),
                              self.view.text_point(lower + 2, 0))
        lines = [self.view.substr(region) for region in self.view.lines(block_region)]
        try:
            row_text = self._get_row_text(upper - 1)
        except LineIndexError:
            row_text = ''
        indent = re.match('^(\s*).*$', row_text).group(1)
        return block_region, lines, indent

########NEW FILE########
__FILENAME__ = indent_list_item
import re

import sublime
import sublime_plugin


class IndentListItemCommand(sublime_plugin.TextCommand):
    bullet_pattern = r'([-+*]|([(]?(\d+|#|[a-y]|[A-Y]|[MDCLXVImdclxvi]+))([).]))'
    bullet_pattern_re = re.compile(bullet_pattern)
    line_pattern_re = re.compile(r'^\s*' + bullet_pattern)
    spaces_re = re.compile(r'^\s*')

    def run(self, edit, reverse=False):
        for region in self.view.sel():
            if region.a != region.b:
                continue

            line = self.view.line(region)
            line_content = self.view.substr(line)

            new_line = line_content

            m = self.line_pattern_re.match(new_line)
            if not m:
                return

            # Determine how to indent (tab or spaces)
            tab_str = self.view.settings().get('tab_size', 4) * ' '
            sep_str = ' ' if m.group(4) else ''

            prev_line = self.view.line(sublime.Region(line.begin() - 1, line.begin() - 1))
            prev_line_content = self.view.substr(prev_line)

            prev_prev_line = self.view.line(sublime.Region(prev_line.begin() - 1, prev_line.begin() - 1))
            prev_prev_line_content = self.view.substr(prev_prev_line)

            if not reverse:
                # Do the indentation
                new_line = self.bullet_pattern_re.sub(tab_str + sep_str + r'\1', new_line)

                # Insert the new item
                if prev_line_content:
                    new_line = '\n' + new_line

            else:
                if not new_line.startswith(tab_str):
                    continue
                # Do the unindentation
                new_line = re.sub(tab_str + sep_str + self.bullet_pattern, r'\1', new_line)

                # Insert the new item
                if prev_line_content:
                    new_line = '\n' + new_line
                else:
                    prev_spaces = self.spaces_re.match(prev_prev_line_content).group(0)
                    spaces = self.spaces_re.match(new_line).group(0)
                    if prev_spaces == spaces:
                        line = sublime.Region(line.begin() - 1, line.end())

            endings = ['.', ')']

            # Transform the bullet to the next/previous bullet type
            if self.view.settings().get('list_indent_auto_switch_bullet', True):
                bullets = self.view.settings().get('list_indent_bullets', ['*', '-', '+'])

                def change_bullet(m):
                    bullet = m.group(1)
                    try:
                        return bullets[(bullets.index(bullet) + (1 if not reverse else -1)) % len(bullets)]
                    except ValueError:
                        pass
                    n = m.group(2)
                    ending = endings[(endings.index(m.group(4)) + (1 if not reverse else -1)) % len(endings)]
                    if n.isdigit():
                        return '${1:a}' + ending
                    elif n != '#':
                        return '${1:0}' + ending
                    return m.group(2) + ending
                new_line = self.bullet_pattern_re.sub(change_bullet, new_line)

            self.view.replace(edit, line, '')
            self.view.run_command('insert_snippet', {'contents': new_line})

    def is_enabled(self):
        return bool(self.view.score_selector(self.view.sel()[0].a, 'text.restructuredtext'))

########NEW FILE########
__FILENAME__ = lists
# -*- coding: utf-8 -*-

"""Smart list is used to automatially continue the current list."""
# Author: Muchenxuan Tong <demon386@gmail.com>

# Original from https://github.com/demon386/SmartMarkdown with this patch:
# https://github.com/vovkkk/SmartMarkdown/commit/bb1bb76179771212c1f21883d9b64d0a299fc98c
# roman number conversion from Mark Pilgrim's "Dive into Python"

# Modified by Martín Gaitán <gaitan@gmail.com>

import re

import sublime
import sublime_plugin
try:
    from .helpers import BaseBlockCommand
except ValueError:
    from helpers import BaseBlockCommand    # NOQA



ORDER_LIST_PATTERN = re.compile(r"(\s*[(]?)(\d+|[a-y]|[A-Y])([.)]\s+)(.*)")
UNORDER_LIST_PATTERN = re.compile(r"(\s*(?:[-+|*]+|[(]?#[).]))(\s+)\S+")
EMPTY_LIST_PATTERN = re.compile(r"(\s*)([-+*]|[(]?(?:\d+|[a-y]|[A-Y]|#|[MDCLXVImdclxvi]+)[.)])(\s+)$")
NONLIST_PATTERN = re.compile(r"(\s*[>|%]+)(\s+)\S?")
ROMAN_PATTERN = re.compile(r"(\s*[(]?)(M{0,4}CM|CD|D?C{0,3}XC|XL|L?X{0,3}IX|IV|V?I{0,3})([.)]\s+)(.*)",
                           re.IGNORECASE)
#Define digit mapping
ROMAN_MAP = (('M', 1000),
             ('CM', 900),
             ('D', 500),
             ('CD', 400),
             ('C', 100),
             ('XC', 90),
             ('L', 50),
             ('XL', 40),
             ('X', 10),
             ('IX', 9),
             ('V', 5),
             ('IV', 4),
             ('I', 1))

#Define exceptions
class RomanError(Exception): pass
class NotIntegerError(RomanError): pass
class InvalidRomanNumeralError(RomanError): pass


def to_roman(n):
    """convert integer to Roman numeral"""
    if not (0 < n < 5000):
        raise Exception("number out of range (must be 1..4999)")
    result = ""
    for numeral, integer in ROMAN_MAP:
        while n >= integer:
            result += numeral
            n -= integer
    return result

def from_roman(s):
    """convert Roman numeral to integer"""
    result = 0
    index = 0
    for numeral, integer in ROMAN_MAP:
        while s[index:index + len(numeral)] == numeral:
            result += integer
            index += len(numeral)
    return result


class SmartListCommand(BaseBlockCommand):


    def run(self, edit):

        def update_ordered_list(lines):
            new_lines = []
            next_num = None
            kind = lambda a: a
            for line in lines:
                match = ORDER_LIST_PATTERN.match(line)
                if not match:
                    new_lines.append(line)
                    continue
                new_line = match.group(1) + \
                              (kind(next_num) or match.group(2)) + \
                              match.group(3) + match.group(4)
                new_lines.append(new_line)

                if not next_num:
                    try:
                        next_num = int(match.group(2))
                        kind = str
                    except ValueError:
                        next_num = ord(match.group(2))
                        kind = chr
                next_num += 1
            return new_lines

        def update_roman_list(lines):
            new_lines = []
            next_num = None
            kind = lambda a: a
            for line in lines:
                match = ROMAN_PATTERN.match(line)
                if not match:
                    new_lines.append(line)
                    continue
                new_line = match.group(1) + \
                              (kind(next_num) or match.group(2)) + \
                              match.group(3) + match.group(4)
                new_lines.append(new_line)

                if not next_num:
                    actual = match.group(2)
                    next_num = from_roman(actual.upper())

                    if actual == actual.lower():
                        kind = lambda a: to_roman(a).lower()
                    else:
                        kind = to_roman
                next_num += 1
            return new_lines



        for region in self.view.sel():
            line_region = self.view.line(region)
            # the content before point at the current line.
            before_point_region = sublime.Region(line_region.a,
                                                 region.a)
            before_point_content = self.view.substr(before_point_region)
            # Disable smart list when folded.
            folded = False
            for i in self.view.folded_regions():
                if i.contains(before_point_region):
                    self.view.insert(edit, region.a, '\n')
                    folded = True
            if folded:
                break

            match = EMPTY_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + \
                              re.sub(r'\S', ' ', str(match.group(2))) + \
                              match.group(3)
                self.view.erase(edit, before_point_region)
                self.view.insert(edit, line_region.a, insert_text)
                break

            match = ROMAN_PATTERN.match(before_point_content)
            if match:
                actual = match.group(2)
                next_num = to_roman(from_roman(actual.upper()) + 1)
                if actual == actual.lower():
                    next_num = next_num.lower()

                insert_text = match.group(1) + \
                              next_num + \
                              match.group(3)
                self.view.insert(edit, region.a, "\n" + insert_text)

                # backup the cursor position
                pos = self.view.sel()[0].a

                # update the whole list
                region, lines, indent = self.get_block_bounds()
                new_list = update_roman_list(lines)
                self.view.replace(edit, region, '\n'.join(new_list) + '\n')
                # restore the cursor position
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(pos, pos))
                self.view.show(pos)

                break


            match = ORDER_LIST_PATTERN.match(before_point_content)
            if match:
                try:
                    next_num = str(int(match.group(2)) + 1)
                except ValueError:
                    next_num = chr(ord(match.group(2)) + 1)

                insert_text = match.group(1) + \
                              next_num + \
                              match.group(3)
                self.view.insert(edit, region.a, "\n" + insert_text)

                # backup the cursor position
                pos = self.view.sel()[0].a

                # update the whole list
                region, lines, indent = self.get_block_bounds()
                new_list = update_ordered_list(lines)
                self.view.replace(edit, region, '\n'.join(new_list) + '\n')
                # restore the cursor position
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(pos, pos))
                self.view.show(pos)
                break

            match = UNORDER_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + match.group(2)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            match = NONLIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + match.group(2)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            self.view.insert(edit, region.a, '\n' + \
                             re.sub(r'\S+\s*', '', before_point_content))
        self.adjust_view()

    def adjust_view(self):
        for region in self.view.sel():
            self.view.show(region)

########NEW FILE########
__FILENAME__ = render
import sublime
import sublime_plugin
import webbrowser
import tempfile
import os
import re
import os.path
import sys
import subprocess


class RenderRstCommand(sublime_plugin.TextCommand):

    TARGETS = ['html (pandoc)', 'html (rst2html)', 'pdf (pandoc)',
               'pdf (rst2pdf)', 'odt (pandoc)', 'odt (rst2odt)',
               'docx (pandoc)']

    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)
        path_pieces = os.environ['PATH'].split(":")
        new_path = []
        
        def append_path(bit):
           if bit != "" and bit not in new_path:
                new_path.append(bit) 

        for bit in path_pieces:
            append_path(bit)

        settings = sublime.load_settings('sublime-rst-completion.sublime-settings');

        for bit in settings.get('command_path', []):
            append_path(bit)

        os.environ['PATH'] = ":".join(new_path)


    def is_enabled(self):
        return True

    def is_visible(self):
        return True

    def run(self, edit):
        if not hasattr(self, 'targets'):
            self.targets = RenderRstCommand.TARGETS[:]
        self.view.window().show_quick_panel(self.targets, self.convert,
                                            sublime.MONOSPACE_FONT)

    def convert(self, target_index):
        if target_index == -1:
            # canceled
            return
        target, tool = re.match(r"(.*) \((.*)\)",
                                self.targets[target_index]).groups()

        # update targets: last used turns the first option
        self.targets.insert(0, self.targets.pop(target_index))
        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'UTF-8'
        elif encoding == 'Western (Windows 1252)':
            encoding = 'windows-1252'
        contents = self.view.substr(sublime.Region(0, self.view.size()))
        contents = contents.encode(encoding)

        file_name = self.view.file_name()
        if file_name:
            os.chdir(os.path.dirname(file_name))

        # write buffer to temporary file
        # This is useful because it means we don't need to save the buffer
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=".rst") as tmp_rst:
            tmp_rst.write(contents)

        # output file...
        suffix = "." + target
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=suffix) as output:
            output.close()
            output_name = output.name

        self.run_tool(tmp_rst.name, output_name, tool)
        self.open_result(output_name, target)

    def run_tool(self, infile, outfile, tool):
        if tool in ("pandoc", "rst2pdf"):
            cmd = [tool, infile, "-o", outfile]
        else:
            cmd = ["%s.py" % tool, infile, outfile]

        try:
            if sys.platform == "win32":
                subprocess.call(cmd, shell=True)
            else:
                subprocess.call(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        except Exception as e:
            sublime.error_message("Fail to generate output.\n{0}".format(e))

    def open_result(self, outfile, target):
        if target == "html":
            webbrowser.open_new_tab(outfile)
        elif sys.platform == "win32":
            os.startfile(outfile)
        elif "mac" in sys.platform or "darwin" in sys.platform:
            os.system("open %s" % outfile)
            print(outfile)
        elif "posix" in sys.platform or "linux" in sys.platform:
            os.system("xdg-open %s" % outfile)

########NEW FILE########
__FILENAME__ = simpleformat
import sublime
import sublime_plugin


class SurroundCommand(sublime_plugin.TextCommand):
    """
    Base class to surround the selection with text.
    """
    surround = ''

    def run(self, edit):
        for sel in self.view.sel():
            len_surround = len(self.surround)
            sel_str = self.view.substr(sel)
            rsel = sublime.Region(sel.begin() - len_surround, sel.end() + len_surround)
            rsel_str = self.view.substr(rsel)
            if sel_str[:len_surround] == self.surround and sel_str[-len_surround:] == self.surround:
                replacement = sel_str[len_surround:-len_surround]
            else:
                replacement = "%s%s%s" % (self.surround, sel_str, self.surround)
            if rsel_str == replacement:
                self.view.sel().subtract(sel)
                self.view.replace(edit, rsel, sel_str)
                self.view.sel().add(sublime.Region(rsel.begin(), rsel.begin() + len(sel_str)))
            else:
                self.view.replace(edit, sel, replacement)


class StrongemphasisCommand(SurroundCommand):
    surround = "**"


class EmphasisCommand(SurroundCommand):
    surround = "*"


class LiteralCommand(SurroundCommand):
    surround = "``"


class SubstitutionCommand(SurroundCommand):
    surround = "|"

########NEW FILE########
__FILENAME__ = tables
# -*- coding: utf-8 -*-

"""
This is a SublimeText 2 adaptation of `Vincent Driessen's vim-rst-tables` [1]_ code
by Martín Gaitán <gaitan@gmail.com>

.. [1]: https://github.com/nvie/vim-rst-tables

Usage
-----

1. Set reStructuredText as syntax (or open a .rst)
2. Create some kind of table outline::

      This is paragraph text *before* the table.

      Column 1  Column 2
      Foo  Put two (or more) spaces as a field separator.
      Bar  Even very very long lines like these are fine, as long as you do not put in line endings here.
      Qux  This is the last line.

      This is paragraph text *after* the table.

2. Put your cursor somewhere in the content to convert as table.

3. Press ``ctrl+t`` (to create the table).  The output will look something like
   this::

      This is paragraph text *before* the table.

      +----------+---------------------------------------------------------+
      | Column 1 | Column 2                                                |
      +==========+=========================================================+
      | Foo      | Put two (or more) spaces as a field separator.          |
      +----------+---------------------------------------------------------+
      | Bar      | Even very very long lines like these are fine, as long  |
      |          | as you do not put in line endings here.                 |
      +----------+---------------------------------------------------------+
      | Qux      | This is the last line.                                  |
      +----------+---------------------------------------------------------+

      This is paragraph text *after* the table.

.. tip::

   Change something in the output table and run ``ctrl+t`` again: Magically,
   it will be fixed.

   And ``ctrl+r+t`` reflows the table fixing the current column width.
"""

import re
import textwrap
try:
    from .helpers import BaseBlockCommand
except ValueError:
    from helpers import BaseBlockCommand    # NOQA


class TableCommand(BaseBlockCommand):

    def get_withs(self, lines):
        return None

    def get_result(self, indent, table, widths):
        result = '\n'.join(draw_table(indent, table, widths))
        result += '\n'
        return result

    def run(self, edit):
        region, lines, indent = self.get_block_bounds()
        table = parse_table(lines)
        widths = self.get_withs(lines)
        result = self.get_result(indent, table, widths)
        self.view.replace(edit, region, result)


class FlowtableCommand(TableCommand):

    def get_withs(self, lines):
        return get_column_widths_from_border_spec(lines)


class BaseMergeCellsCommand(BaseBlockCommand):

    def get_column_index(self, raw_line, col_position):
        """given the raw line and the column col cursor position,
           return the table column index to merge"""
        return raw_line[:col_position].count('|')


class MergeCellsDownCommand(BaseMergeCellsCommand):
    offset = 1

    def run(self, edit):
        region, lines, indent= self.get_block_bounds()
        raw_table = self.view.substr(region).split('\n')
        begin = self.view.rowcol(region.begin())[0]
        # end = self.view.rowcol(region.end())[0]
        cursor = self.get_cursor_position()
        actual_line = raw_table[cursor[0] - begin]
        col = self.get_column_index(actual_line, cursor[1])
        sep_line = raw_table[cursor[0] + self.offset - begin]
        new_sep_line = self.update_sep_line(sep_line, col)
        raw_table[cursor[0] + self.offset - begin] = indent + new_sep_line
        result = '\n'.join(raw_table)
        self.view.replace(edit, region, result)


    def update_sep_line(self, original, col):
        segments = original.strip().split('+')
        segments[col] = ' ' * len(segments[col])
        new_sep_line = '+'.join(segments)
        # replace ghost ``+``
        new_sep_line = re.sub('(^\+ )|( \+ )|( \+)$',
                              lambda m: m.group().replace('+', '|'),
                              new_sep_line)
        return new_sep_line

class MergeCellsUpCommand(MergeCellsDownCommand):
    offset = -1


class MergeCellsRightCommand(BaseMergeCellsCommand):
    offset = 0

    def run(self, edit):
        region, lines, indent= self.get_block_bounds()
        raw_table = self.view.substr(region).split('\n')
        begin = self.view.rowcol(region.begin())[0]
        # end = self.view.rowcol(region.end())[0]
        cursor = self.get_cursor_position()
        actual_line = raw_table[cursor[0] - begin]
        col = self.get_column_index(actual_line, cursor[1])
        separator_indexes = [match.start() for match in
                             re.finditer(re.escape('|'), actual_line)]
        actual_line = list(actual_line)
        actual_line[separator_indexes[col + self.offset]] = ' '
        actual_line = ''.join(actual_line)
        raw_table[cursor[0] - begin] = actual_line
        result = '\n'.join(raw_table)
        self.view.replace(edit, region, result)


class MergeCellsLeftCommand(MergeCellsRightCommand):
    offset = -1




def join_rows(rows, sep='\n'):
    """Given a list of rows (a list of lists) this function returns a
    flattened list where each the individual columns of all rows are joined
    together using the line separator.

    """
    output = []
    for row in rows:
        # grow output array, if necessary
        if len(output) <= len(row):
            for i in range(len(row) - len(output)):
                output.extend([[]])

        for i, field in enumerate(row):
            field_text = field.strip()
            if field_text:
                output[i].append(field_text)
    return [sep.join(lines) for lines in output]


def line_is_separator(line):
    return re.match('^[\t +=-]+$', line)


def has_line_seps(raw_lines):
    for line in raw_lines:
        if line_is_separator(line):
            return True
    return False


def partition_raw_lines(raw_lines):
    """Partitions a list of raw input lines so that between each partition, a
    table row separator can be placed.

    """
    if not has_line_seps(raw_lines):
        return [[x] for x in raw_lines]

    curr_part = []
    parts = [curr_part]
    for line in raw_lines:
        if line_is_separator(line):
            curr_part = []
            parts.append(curr_part)
        else:
            curr_part.append(line)

    # remove any empty partitions (typically the first and last ones)
    return [x for x in parts if x]


def unify_table(table):
    """Given a list of rows (i.e. a table), this function returns a new table
    in which all rows have an equal amount of columns.  If all full column is
    empty (i.e. all rows have that field empty), the column is removed.

    """
    max_fields = max([len(row) for row in table])
    empty_cols = [True] * max_fields
    output = []
    for row in table:
        curr_len = len(row)
        if curr_len < max_fields:
            row += [''] * (max_fields - curr_len)
        output.append(row)

        # register empty columns (to be removed at the end)
        for i in range(len(row)):
            if row[i].strip():
                empty_cols[i] = False

    # remove empty columns from all rows
    table = output
    output = []
    for row in table:
        cols = []
        for i in range(len(row)):
            should_remove = empty_cols[i]
            if not should_remove:
                cols.append(row[i])
        output.append(cols)

    return output


def split_table_row(row_string):
    if row_string.find("|") >= 0:
        # first, strip off the outer table drawings
        row_string = re.sub(r'^\s*\||\|\s*$', '', row_string)
        return re.split(r'\s*\|\s*', row_string.strip())
    return re.split(r'\s\s+', row_string.rstrip())


def parse_table(raw_lines):
    row_partition = partition_raw_lines(raw_lines)
    lines = []
    for row_string in row_partition:
        lines.append(join_rows([split_table_row(cell) for cell in row_string]))
    return unify_table(lines)


def table_line(widths, header=False):
    if header:
        linechar = '='
    else:
        linechar = '-'
    sep = '+'
    parts = []
    for width in widths:
        parts.append(linechar * width)
    if parts:
        parts = [''] + parts + ['']
    return sep.join(parts)


def get_field_width(field_text):
    return max([len(s) for s in field_text.split('\n')])


def split_row_into_lines(row):
    row = [field.split('\n') for field in row]
    height = max([len(field_lines) for field_lines in row])
    turn_table = []
    for i in range(height):
        fields = []
        for field_lines in row:
            if i < len(field_lines):
                fields.append(field_lines[i])
            else:
                fields.append('')
        turn_table.append(fields)
    return turn_table


def get_column_widths(table):
    widths = []
    for row in table:
        num_fields = len(row)
        # dynamically grow
        if num_fields >= len(widths):
            widths.extend([0] * (num_fields - len(widths)))
        for i in range(num_fields):
            field_text = row[i]
            field_width = get_field_width(field_text)
            widths[i] = max(widths[i], field_width)
    return widths


def get_column_widths_from_border_spec(slice):
    border = None
    for row in slice:
        if line_is_separator(row):
            border = row.strip()
            break

    if border is None:
        raise RuntimeError('Cannot reflow this table. Top table border not found.')

    left = right = None
    if border[0] == '+':
        left = 1
    if border[-1] == '+':
        right = -1
    return [max(0, len(drawing) - 2) for drawing in border[left:right].split('+')]


def pad_fields(row, widths):
    """Pads fields of the given row, so each field lines up nicely with the
    others.

    """
    widths = [(' %-' + str(w) + 's ') for w in widths]

    # Pad all fields using the calculated widths
    new_row = []
    for i in range(len(row)):
        col = row[i]
        col = widths[i] % col.strip()
        new_row.append(col)
    return new_row


def reflow_row_contents(row, widths):
    new_row = []
    for i, field in enumerate(row):
        wrapped_lines = textwrap.wrap(field.replace('\n', ' '), widths[i])
        new_row.append("\n".join(wrapped_lines))
    return new_row


def draw_table(indent, table, manual_widths=None):
    if table == []:
        return []

    if manual_widths is None:
        col_widths = get_column_widths(table)
    else:
        col_widths = manual_widths

    # Reserve room for the spaces
    sep_col_widths = [(col + 2) for col in col_widths]
    header_line = table_line(sep_col_widths, header=True)
    normal_line = table_line(sep_col_widths, header=False)

    output = [indent + normal_line]
    first = True
    for row in table:

        if manual_widths:
            row = reflow_row_contents(row, manual_widths)

        row_lines = split_row_into_lines(row)

        # draw the lines (num_lines) for this row
        for row_line in row_lines:
            row_line = pad_fields(row_line, col_widths)
            output.append(indent + "|".join([''] + row_line + ['']))

        # then, draw the separator
        if first:
            output.append(indent + header_line)
            first = False
        else:
            output.append(indent + normal_line)

    return output

########NEW FILE########
