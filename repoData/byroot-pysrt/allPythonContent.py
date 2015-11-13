__FILENAME__ = mvyskoc_merge
#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright mvyskoc (https://github.com/mvyskoc)

# This script mix 2 subtitles files in different languages in one file
# to allow multiple people with different language to watch a movie together
# or to help someone to learn a foreign language

# See https://github.com/byroot/pysrt/issues/17 for more detailed information

import sys
import getopt
from pysrt import SubRipFile
from pysrt import SubRipItem
from pysrt import SubRipTime


def join_lines(txtsub1, txtsub2):
    if (len(txtsub1) > 0) & (len(txtsub2) > 0):
        return txtsub1 + '\n' + txtsub2
    else:
        return txtsub1 + txtsub2


def find_subtitle(subtitle, from_t, to_t, lo=0):
    i = lo
    while (i < len(subtitle)):
        if (subtitle[i].start >= to_t):
            break

        if (subtitle[i].start <= from_t) & (to_t  <= subtitle[i].end):
            return subtitle[i].text, i
        i += 1

    return "", i



def merge_subtitle(sub_a, sub_b, delta):
    out = SubRipFile()
    intervals = [item.start.ordinal for item in sub_a]
    intervals.extend([item.end.ordinal for item in sub_a])
    intervals.extend([item.start.ordinal for item in sub_b])
    intervals.extend([item.end.ordinal for item in sub_b])
    intervals.sort()

    j = k = 0
    for i in xrange(1, len(intervals)):
        start = SubRipTime.from_ordinal(intervals[i-1])
        end = SubRipTime.from_ordinal(intervals[i])

        if (end-start) > delta:
            text_a, j = find_subtitle(sub_a, start, end, j)
            text_b, k = find_subtitle(sub_b, start, end, k)

            text = join_lines(text_a, text_b)
            if len(text) > 0:
                item = SubRipItem(0, start, end, text)
                out.append(item)

    out.clean_indexes()
    return out

def usage():
    print "Usage: ./srtmerge [options] lang1.srt lang2.srt out.srt"
    print
    print "Options:"
    print "  -d <milliseconds>         The shortest time length of the one subtitle"
    print "  --delta=<milliseconds>    default: 500"
    print "  -e <encoding>             Encoding of input and output files."
    print "  --encoding=<encoding>     default: utf_8"


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hd:e:', ["help", "encoding=", "delta="])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    #Settings default values
    delta = SubRipTime(milliseconds=500)
    encoding="utf_8"
    #-

    if len(args) <> 3:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-d", "--delta"):
            delta = SubRipTime(milliseconds=int(a))
        elif o in ("-e", "--encoding"):
            encoding = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()

    subs_a = SubRipFile.open(args[0], encoding=encoding)
    subs_b = SubRipFile.open(args[1], encoding=encoding)
    out = merge_subtitle(subs_a, subs_b, delta)
    out.save(args[2], encoding=encoding)

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = commands
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-all

import os
import re
import sys
import codecs
import shutil
import argparse
from textwrap import dedent

from chardet import detect
from pysrt import SubRipFile, SubRipTime, VERSION_STRING


def underline(string):
    return "\033[4m%s\033[0m" % string


class TimeAwareArgumentParser(argparse.ArgumentParser):

    RE_TIME_REPRESENTATION = re.compile(r'^\-?(\d+[hms]{0,2}){1,4}$')

    def parse_args(self, args=None, namespace=None):
        time_index = -1
        for index, arg in enumerate(args):
            match = self.RE_TIME_REPRESENTATION.match(arg)
            if match:
                time_index = index
                break

        if time_index >= 0:
            args.insert(time_index, '--')

        return super(TimeAwareArgumentParser, self).parse_args(args, namespace)


class SubRipShifter(object):

    BACKUP_EXTENSION = '.bak'
    RE_TIME_STRING = re.compile(r'(\d+)([hms]{0,2})')
    UNIT_RATIOS = {
        'ms': 1,
        '': SubRipTime.SECONDS_RATIO,
        's': SubRipTime.SECONDS_RATIO,
        'm': SubRipTime.MINUTES_RATIO,
        'h': SubRipTime.HOURS_RATIO,
    }
    DESCRIPTION = dedent("""\
        Srt subtitle editor

        It can either shift, split or change the frame rate.
    """)
    TIMESTAMP_HELP = "A timestamp in the form: [-][Hh][Mm]S[s][MSms]"
    SHIFT_EPILOG = dedent("""\

        Examples:
            1 minute and 12 seconds foreward (in place):
                $ srt -i shift 1m12s movie.srt

            half a second foreward:
                $ srt shift 500ms movie.srt > othername.srt

            1 second and half backward:
                $ srt -i shift -1s500ms movie.srt

            3 seconds backward:
                $ srt -i shift -3 movie.srt
    """)
    RATE_EPILOG = dedent("""\

        Examples:
            Convert 23.9fps subtitles to 25fps:
                $ srt -i rate 23.9 25 movie.srt
    """)
    LIMITS_HELP = "Each parts duration in the form: [Hh][Mm]S[s][MSms]"
    SPLIT_EPILOG = dedent("""\

        Examples:
            For a movie in 2 parts with the first part 48 minutes and 18 seconds long:
                $ srt split 48m18s movie.srt
                => creates movie.1.srt and movie.2.srt

            For a movie in 3 parts of 20 minutes each:
                $ srt split 20m 20m movie.srt
                => creates movie.1.srt, movie.2.srt and movie.3.srt
    """)
    FRAME_RATE_HELP = "A frame rate in fps (commonly 23.9 or 25)"
    ENCODING_HELP = dedent("""\
        Change file encoding. Useful for players accepting only latin1 subtitles.
        List of supported encodings: http://docs.python.org/library/codecs.html#standard-encodings
    """)
    BREAK_EPILOG = dedent("""\
        Break lines longer than defined length
    """)
    LENGTH_HELP = "Maximum number of characters per line"

    def __init__(self):
        self.output_file_path = None

    def build_parser(self):
        parser = TimeAwareArgumentParser(description=self.DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('-i', '--in-place', action='store_true', dest='in_place',
            help="Edit file in-place, saving a backup as file.bak (do not works for the split command)")
        parser.add_argument('-e', '--output-encoding', metavar=underline('encoding'), action='store', dest='output_encoding',
            type=self.parse_encoding, help=self.ENCODING_HELP)
        parser.add_argument('-v', '--version', action='version', version='%%(prog)s %s' % VERSION_STRING)
        subparsers = parser.add_subparsers(title='commands')

        shift_parser = subparsers.add_parser('shift', help="Shift subtitles by specified time offset", epilog=self.SHIFT_EPILOG, formatter_class=argparse.RawTextHelpFormatter)
        shift_parser.add_argument('time_offset', action='store', metavar=underline('offset'),
            type=self.parse_time, help=self.TIMESTAMP_HELP)
        shift_parser.set_defaults(action=self.shift)

        rate_parser = subparsers.add_parser('rate', help="Convert subtitles from a frame rate to another", epilog=self.RATE_EPILOG, formatter_class=argparse.RawTextHelpFormatter)
        rate_parser.add_argument('initial', action='store', type=float, help=self.FRAME_RATE_HELP)
        rate_parser.add_argument('final', action='store', type=float, help=self.FRAME_RATE_HELP)
        rate_parser.set_defaults(action=self.rate)

        split_parser = subparsers.add_parser('split', help="Split a file in multiple parts", epilog=self.SPLIT_EPILOG, formatter_class=argparse.RawTextHelpFormatter)
        split_parser.add_argument('limits', action='store', nargs='+', type=self.parse_time, help=self.LIMITS_HELP)
        split_parser.set_defaults(action=self.split)

        break_parser = subparsers.add_parser('break', help="Break long lines", epilog=self.BREAK_EPILOG, formatter_class=argparse.RawTextHelpFormatter)
        break_parser.add_argument('length', action='store', type=int, help=self.LENGTH_HELP)
        break_parser.set_defaults(action=self.break_lines)

        parser.add_argument('file', action='store')

        return parser

    def run(self, args):
        self.arguments = self.build_parser().parse_args(args)
        if self.arguments.in_place:
            self.create_backup()
        self.arguments.action()

    def parse_time(self, time_string):
        negative = time_string.startswith('-')
        if negative:
            time_string = time_string[1:]
        ordinal = sum(int(value) * self.UNIT_RATIOS[unit] for value, unit
                        in self.RE_TIME_STRING.findall(time_string))
        return -ordinal if negative else ordinal

    def parse_encoding(self, encoding_name):
        try:
            codecs.lookup(encoding_name)
        except LookupError as error:
            raise argparse.ArgumentTypeError(error.message)
        return encoding_name

    def shift(self):
        self.input_file.shift(milliseconds=self.arguments.time_offset)
        self.input_file.write_into(self.output_file)

    def rate(self):
        ratio = self.arguments.final / self.arguments.initial
        self.input_file.shift(ratio=ratio)
        self.input_file.write_into(self.output_file)

    def split(self):
        limits = [0] + self.arguments.limits + [self.input_file[-1].end.ordinal + 1]
        base_name, extension = os.path.splitext(self.arguments.file)
        for index, (start, end) in enumerate(zip(limits[:-1], limits[1:])):
            file_name = '%s.%s%s' % (base_name, index + 1, extension)
            part_file = self.input_file.slice(ends_after=start, starts_before=end)
            part_file.shift(milliseconds=-start)
            part_file.clean_indexes()
            part_file.save(path=file_name, encoding=self.output_encoding)

    def create_backup(self):
        backup_file = self.arguments.file + self.BACKUP_EXTENSION
        if not os.path.exists(backup_file):
            shutil.copy2(self.arguments.file, backup_file)
        self.output_file_path = self.arguments.file
        self.arguments.file = backup_file

    def break_lines(self):
        split_re = re.compile(r'(.{,%i})(?:\s+|$)' % self.arguments.length)
        for item in self.input_file:
            item.text = '\n'.join(split_re.split(item.text)[1::2])
        self.input_file.write_into(self.output_file)

    @property
    def output_encoding(self):
        return self.arguments.output_encoding or self.input_file.encoding

    @property
    def input_file(self):
        if not hasattr(self, '_source_file'):
            with open(self.arguments.file, 'rb') as f:
                content = f.read()
                encoding = detect(content).get('encoding')
                encoding = self.normalize_encoding(encoding)

            self._source_file = SubRipFile.open(self.arguments.file,
                encoding=encoding, error_handling=SubRipFile.ERROR_LOG)
        return self._source_file

    @property
    def output_file(self):
        if not hasattr(self, '_output_file'):
            if self.output_file_path:
                self._output_file = codecs.open(self.output_file_path, 'w+', encoding=self.output_encoding)
            else:
                self._output_file = sys.stdout
        return self._output_file

    def normalize_encoding(self, encoding):
        return encoding.lower().replace('-', '_')


def main():
    SubRipShifter().run(sys.argv[1:])

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = comparablemixin
class ComparableMixin(object):
    def _compare(self, other, method):
        try:
            return method(self._cmpkey(), other._cmpkey())
        except (AttributeError, TypeError):
            # _cmpkey not implemented, or return different type,
            # so I can't compare with "other".
            return NotImplemented

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)

########NEW FILE########
__FILENAME__ = compat

import sys

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = (_ver[0] == 2)

#: Python 3.x?
is_py3 = (_ver[0] == 3)

from io import open as io_open

if is_py2:
    basestring = basestring
    str = unicode
    open = io_open
elif is_py3:
    basestring = (str, bytes)
    str = str
    open = open

########NEW FILE########
__FILENAME__ = srtexc
"""
Exception classes
"""


class Error(Exception):
    """
    Pysrt's base exception
    """
    pass


class InvalidTimeString(Error):
    """
    Raised when parser fail on bad formated time strings
    """
    pass


class InvalidItem(Error):
    """
    Raised when parser fail to parse a sub title item
    """
    pass


class InvalidIndex(InvalidItem):
    """
    Raised when parser fail to parse a sub title index
    """
    pass

########NEW FILE########
__FILENAME__ = srtfile
# -*- coding: utf-8 -*-
import os
import sys
import codecs

try:
    from collections import UserList
except ImportError:
    from UserList import UserList

from itertools import chain
from copy import copy

from pysrt.srtexc import Error
from pysrt.srtitem import SubRipItem
from pysrt.compat import str

BOMS = ((codecs.BOM_UTF32_LE, 'utf_32_le'),
        (codecs.BOM_UTF32_BE, 'utf_32_be'),
        (codecs.BOM_UTF16_LE, 'utf_16_le'),
        (codecs.BOM_UTF16_BE, 'utf_16_be'),
        (codecs.BOM_UTF8, 'utf_8'))
CODECS_BOMS = dict((codec, str(bom, codec)) for bom, codec in BOMS)
BIGGER_BOM = max(len(bom) for bom, encoding in BOMS)


class SubRipFile(UserList, object):
    """
    SubRip file descriptor.

    Provide a pure Python mapping on all metadata.

    SubRipFile(items, eol, path, encoding)

    items -> list of SubRipItem. Default to [].
    eol -> str: end of line character. Default to linesep used in opened file
        if any else to os.linesep.
    path -> str: path where file will be saved. To open an existant file see
        SubRipFile.open.
    encoding -> str: encoding used at file save. Default to utf-8.
    """
    ERROR_PASS = 0
    ERROR_LOG = 1
    ERROR_RAISE = 2

    DEFAULT_ENCODING = 'utf_8'

    def __init__(self, items=None, eol=None, path=None, encoding='utf-8'):
        UserList.__init__(self, items or [])
        self._eol = eol
        self.path = path
        self.encoding = encoding

    def _get_eol(self):
        return self._eol or os.linesep

    def _set_eol(self, eol):
        self._eol = self._eol or eol

    eol = property(_get_eol, _set_eol)

    def slice(self, starts_before=None, starts_after=None, ends_before=None,
              ends_after=None):
        """
        slice([starts_before][, starts_after][, ends_before][, ends_after]) \
-> SubRipFile clone

        All arguments are optional, and should be coercible to SubRipTime
        object.

        It reduce the set of subtitles to those that match match given time
        constraints.

        The returned set is a clone, but still contains references to original
        subtitles. So if you shift this returned set, subs contained in the
        original SubRipFile instance will be altered too.

        Example:
            >>> subs.slice(ends_after={'seconds': 20}).shift(seconds=2)
        """
        clone = copy(self)

        if starts_before:
            clone.data = (i for i in clone.data if i.start < starts_before)
        if starts_after:
            clone.data = (i for i in clone.data if i.start > starts_after)
        if ends_before:
            clone.data = (i for i in clone.data if i.end < ends_before)
        if ends_after:
            clone.data = (i for i in clone.data if i.end > ends_after)

        clone.data = list(clone.data)
        return clone

    def at(self, timestamp=None, **kwargs):
        """
        at(timestamp) -> SubRipFile clone

        timestamp argument should be coercible to SubRipFile object.

        A specialization of slice. Return all subtiles visible at the
        timestamp mark.

        Example:
            >>> subs.at((0, 0, 20, 0)).shift(seconds=2)
            >>> subs.at(seconds=20).shift(seconds=2)
        """
        time = timestamp or kwargs
        return self.slice(starts_before=time, ends_after=time)

    def shift(self, *args, **kwargs):
        """shift(hours, minutes, seconds, milliseconds, ratio)

        Shift `start` and `end` attributes of each items of file either by
        applying a ratio or by adding an offset.

        `ratio` should be either an int or a float.
        Example to convert subtitles from 23.9 fps to 25 fps:
        >>> subs.shift(ratio=25/23.9)

        All "time" arguments are optional and have a default value of 0.
        Example to delay all subs from 2 seconds and half
        >>> subs.shift(seconds=2, milliseconds=500)
        """
        for item in self:
            item.shift(*args, **kwargs)

    def clean_indexes(self):
        """
        clean_indexes()

        Sort subs and reset their index attribute. Should be called after
        destructive operations like split or such.
        """
        self.sort()
        for index, item in enumerate(self):
            item.index = index + 1

    @property
    def text(self):
        return '\n'.join(i.text for i in self)

    @classmethod
    def open(cls, path='', encoding=None, error_handling=ERROR_PASS):
        """
        open([path, [encoding]])

        If you do not provide any encoding, it can be detected if the file
        contain a bit order mark, unless it is set to utf-8 as default.
        """
        source_file, encoding = cls._open_unicode_file(path, claimed_encoding=encoding)
        new_file = cls(path=path, encoding=encoding)
        new_file.read(source_file, error_handling=error_handling)
        source_file.close()
        return new_file

    @classmethod
    def from_string(cls, source, **kwargs):
        """
        from_string(source, **kwargs) -> SubRipFile

        `source` -> a unicode instance or at least a str instance encoded with
        `sys.getdefaultencoding()`
        """
        error_handling = kwargs.pop('error_handling', None)
        new_file = cls(**kwargs)
        new_file.read(source.splitlines(True), error_handling=error_handling)
        return new_file

    def read(self, source_file, error_handling=ERROR_PASS):
        """
        read(source_file, [error_handling])

        This method parse subtitles contained in `source_file` and append them
        to the current instance.

        `source_file` -> Any iterable that yield unicode strings, like a file
            opened with `codecs.open()` or an array of unicode.
        """
        self.eol = self._guess_eol(source_file)
        self.extend(self.stream(source_file, error_handling=error_handling))
        return self

    @classmethod
    def stream(cls, source_file, error_handling=ERROR_PASS):
        """
        stream(source_file, [error_handling])

        This method yield SubRipItem instances a soon as they have been parsed
        without storing them. It is a kind of SAX parser for .srt files.

        `source_file` -> Any iterable that yield unicode strings, like a file
            opened with `codecs.open()` or an array of unicode.

        Example:
            >>> import pysrt
            >>> import codecs
            >>> file = codecs.open('movie.srt', encoding='utf-8')
            >>> for sub in pysrt.stream(file):
            ...     sub.text += "\nHello !"
            ...     print unicode(sub)
        """
        string_buffer = []
        for index, line in enumerate(chain(source_file, '\n')):
            if line.strip():
                string_buffer.append(line)
            else:
                source = string_buffer
                string_buffer = []
                if source and all(source):
                    try:
                        yield SubRipItem.from_lines(source)
                    except Error as error:
                        error.args += (''.join(source), )
                        cls._handle_error(error, error_handling, index)

    def save(self, path=None, encoding=None, eol=None):
        """
        save([path][, encoding][, eol])

        Use initial path if no other provided.
        Use initial encoding if no other provided.
        Use initial eol if no other provided.
        """
        path = path or self.path
        encoding = encoding or self.encoding

        save_file = codecs.open(path, 'w+', encoding=encoding)
        self.write_into(save_file, eol=eol)
        save_file.close()

    def write_into(self, output_file, eol=None):
        """
        write_into(output_file [, eol])

        Serialize current state into `output_file`.

        `output_file` -> Any instance that respond to `write()`, typically a
        file object
        """
        output_eol = eol or self.eol

        for item in self:
            string_repr = str(item)
            if output_eol != '\n':
                string_repr = string_repr.replace('\n', output_eol)
            output_file.write(string_repr)
            # Only add trailing eol if it's not already present.
            # It was kept in the SubRipItem's text before but it really
            # belongs here. Existing applications might give us subtitles
            # which already contain a trailing eol though.
            if not string_repr.endswith(2 * output_eol):
                output_file.write(output_eol)

    @classmethod
    def _guess_eol(cls, string_iterable):
        first_line = cls._get_first_line(string_iterable)
        for eol in ('\r\n', '\r', '\n'):
            if first_line.endswith(eol):
                return eol
        return os.linesep

    @classmethod
    def _get_first_line(cls, string_iterable):
        if hasattr(string_iterable, 'tell'):
            previous_position = string_iterable.tell()

        try:
            first_line = next(iter(string_iterable))
        except StopIteration:
            return ''
        if hasattr(string_iterable, 'seek'):
            string_iterable.seek(previous_position)

        return first_line

    @classmethod
    def _detect_encoding(cls, path):
        file_descriptor = open(path, 'rb')
        first_chars = file_descriptor.read(BIGGER_BOM)
        file_descriptor.close()

        for bom, encoding in BOMS:
            if first_chars.startswith(bom):
                return encoding

        # TODO: maybe a chardet integration
        return cls.DEFAULT_ENCODING

    @classmethod
    def _open_unicode_file(cls, path, claimed_encoding=None):
        encoding = claimed_encoding or cls._detect_encoding(path)
        source_file = codecs.open(path, 'rU', encoding=encoding)

        # get rid of BOM if any
        possible_bom = CODECS_BOMS.get(encoding, None)
        if possible_bom:
            file_bom = source_file.read(len(possible_bom))
            if not file_bom == possible_bom:
                source_file.seek(0)  # if not rewind
        return source_file, encoding

    @classmethod
    def _handle_error(cls, error, error_handling, index):
        if error_handling == cls.ERROR_RAISE:
            error.args = (index, ) + error.args
            raise error
        if error_handling == cls.ERROR_LOG:
            name = type(error).__name__
            sys.stderr.write('PySRT-%s(line %s): \n' % (name, index))
            sys.stderr.write(error.args[0].encode('ascii', 'replace'))
            sys.stderr.write('\n')

########NEW FILE########
__FILENAME__ = srtitem
# -*- coding: utf-8 -*-
"""
SubRip's subtitle parser
"""

from pysrt.srtexc import InvalidItem, InvalidIndex
from pysrt.srttime import SubRipTime
from pysrt.comparablemixin import ComparableMixin
from pysrt.compat import str, is_py2
import re


class SubRipItem(ComparableMixin):
    """
    SubRipItem(index, start, end, text, position)

    index -> int: index of item in file. 0 by default.
    start, end -> SubRipTime or coercible.
    text -> unicode: text content for item.
    position -> unicode: raw srt/vtt "display coordinates" string
    """
    ITEM_PATTERN = str('%s\n%s --> %s%s\n%s\n')
    TIMESTAMP_SEPARATOR = '-->'

    def __init__(self, index=0, start=None, end=None, text='', position=''):
        try:
            self.index = int(index)
        except (TypeError, ValueError):  # try to cast as int, but it's not mandatory
            self.index = index

        self.start = SubRipTime.coerce(start or 0)
        self.end = SubRipTime.coerce(end or 0)
        self.position = str(position)
        self.text = str(text)

    @property
    def duration(self):
        return self.end - self.start

    @property
    def text_without_tags(self):
        RE_TAG = re.compile(r'<[^>]*?>')
        return RE_TAG.sub('', self.text)

    @property
    def characters_per_second(self):
        characters_count = len(self.text_without_tags.replace('\n', ''))
        try:
            return characters_count / (self.duration.ordinal / 1000.0)
        except ZeroDivisionError:
            return 0.0

    def __str__(self):
        position = ' %s' % self.position if self.position.strip() else ''
        return self.ITEM_PATTERN % (self.index, self.start, self.end,
                                    position, self.text)
    if is_py2:
        __unicode__ = __str__

        def __str__(self):
            raise NotImplementedError('Use unicode() instead!')

    def _cmpkey(self):
        return (self.start, self.end)

    def shift(self, *args, **kwargs):
        """
        shift(hours, minutes, seconds, milliseconds, ratio)

        Add given values to start and end attributes.
        All arguments are optional and have a default value of 0.
        """
        self.start.shift(*args, **kwargs)
        self.end.shift(*args, **kwargs)

    @classmethod
    def from_string(cls, source):
        return cls.from_lines(source.splitlines(True))

    @classmethod
    def from_lines(cls, lines):
        if len(lines) < 2:
            raise InvalidItem()
        lines = [l.rstrip() for l in lines]
        index = None
        if cls.TIMESTAMP_SEPARATOR not in lines[0]:
            index = lines.pop(0)
        start, end, position = cls.split_timestamps(lines[0])
        body = '\n'.join(lines[1:])
        return cls(index, start, end, body, position)

    @classmethod
    def split_timestamps(cls, line):
        timestamps = line.split(cls.TIMESTAMP_SEPARATOR)
        if len(timestamps) != 2:
            raise InvalidItem()
        start, end_and_position = timestamps
        end_and_position = end_and_position.lstrip().split(' ', 1)
        end = end_and_position[0]
        position = end_and_position[1] if len(end_and_position) > 1 else ''
        return (s.strip() for s in (start, end, position))

########NEW FILE########
__FILENAME__ = srttime
# -*- coding: utf-8 -*-
"""
SubRip's time format parser: HH:MM:SS,mmm
"""
import re
from datetime import time

from pysrt.srtexc import InvalidTimeString
from pysrt.comparablemixin import ComparableMixin
from pysrt.compat import str, basestring


class TimeItemDescriptor(object):
    # pylint: disable-msg=R0903
    def __init__(self, ratio, super_ratio=0):
        self.ratio = int(ratio)
        self.super_ratio = int(super_ratio)

    def _get_ordinal(self, instance):
        if self.super_ratio:
            return instance.ordinal % self.super_ratio
        return instance.ordinal

    def __get__(self, instance, klass):
        if instance is None:
            raise AttributeError
        return self._get_ordinal(instance) // self.ratio

    def __set__(self, instance, value):
        part = self._get_ordinal(instance) - instance.ordinal % self.ratio
        instance.ordinal += value * self.ratio - part


class SubRipTime(ComparableMixin):
    TIME_PATTERN = '%02d:%02d:%02d,%03d'
    TIME_REPR = 'SubRipTime(%d, %d, %d, %d)'
    RE_TIME_SEP = re.compile(r'\:|\.|\,')
    RE_INTEGER = re.compile(r'^(\d+)')
    SECONDS_RATIO = 1000
    MINUTES_RATIO = SECONDS_RATIO * 60
    HOURS_RATIO = MINUTES_RATIO * 60

    hours = TimeItemDescriptor(HOURS_RATIO)
    minutes = TimeItemDescriptor(MINUTES_RATIO, HOURS_RATIO)
    seconds = TimeItemDescriptor(SECONDS_RATIO, MINUTES_RATIO)
    milliseconds = TimeItemDescriptor(1, SECONDS_RATIO)

    def __init__(self, hours=0, minutes=0, seconds=0, milliseconds=0):
        """
        SubRipTime(hours, minutes, seconds, milliseconds)

        All arguments are optional and have a default value of 0.
        """
        super(SubRipTime, self).__init__()
        self.ordinal = hours * self.HOURS_RATIO \
                     + minutes * self.MINUTES_RATIO \
                     + seconds * self.SECONDS_RATIO \
                     + milliseconds

    def __repr__(self):
        return self.TIME_REPR % tuple(self)

    def __str__(self):
        if self.ordinal < 0:
            # Represent negative times as zero
            return str(SubRipTime.from_ordinal(0))
        return self.TIME_PATTERN % tuple(self)

    def _compare(self, other, method):
        return super(SubRipTime, self)._compare(self.coerce(other), method)

    def _cmpkey(self):
        return self.ordinal

    def __add__(self, other):
        return self.from_ordinal(self.ordinal + self.coerce(other).ordinal)

    def __iadd__(self, other):
        self.ordinal += self.coerce(other).ordinal
        return self

    def __sub__(self, other):
        return self.from_ordinal(self.ordinal - self.coerce(other).ordinal)

    def __isub__(self, other):
        self.ordinal -= self.coerce(other).ordinal
        return self

    def __mul__(self, ratio):
        return self.from_ordinal(int(round(self.ordinal * ratio)))

    def __imul__(self, ratio):
        self.ordinal = int(round(self.ordinal * ratio))
        return self

    @classmethod
    def coerce(cls, other):
        """
        Coerce many types to SubRipTime instance.
        Supported types:
          - str/unicode
          - int/long
          - datetime.time
          - any iterable
          - dict
        """
        if isinstance(other, SubRipTime):
            return other
        if isinstance(other, basestring):
            return cls.from_string(other)
        if isinstance(other, int):
            return cls.from_ordinal(other)
        if isinstance(other, time):
            return cls.from_time(other)
        try:
            return cls(**other)
        except TypeError:
            return cls(*other)

    def __iter__(self):
        yield self.hours
        yield self.minutes
        yield self.seconds
        yield self.milliseconds

    def shift(self, *args, **kwargs):
        """
        shift(hours, minutes, seconds, milliseconds)

        All arguments are optional and have a default value of 0.
        """
        if 'ratio' in kwargs:
            self *= kwargs.pop('ratio')
        self += self.__class__(*args, **kwargs)

    @classmethod
    def from_ordinal(cls, ordinal):
        """
        int -> SubRipTime corresponding to a total count of milliseconds
        """
        return cls(milliseconds=int(ordinal))

    @classmethod
    def from_string(cls, source):
        """
        str/unicode(HH:MM:SS,mmm) -> SubRipTime corresponding to serial
        raise InvalidTimeString
        """
        items = cls.RE_TIME_SEP.split(source)
        if len(items) != 4:
            raise InvalidTimeString
        return cls(*(cls.parse_int(i) for i in items))

    @classmethod
    def parse_int(cls, digits):
        try:
            return int(digits)
        except ValueError:
            match = cls.RE_INTEGER.match(digits)
            if match:
                return int(match.group())
            return 0

    @classmethod
    def from_time(cls, source):
        """
        datetime.time -> SubRipTime corresponding to time object
        """
        return cls(hours=source.hour, minutes=source.minute,
            seconds=source.second, milliseconds=source.microsecond // 1000)

    def to_time(self):
        """
        Convert SubRipTime instance into a pure datetime.time object
        """
        return time(self.hours, self.minutes, self.seconds,
                    self.milliseconds * 1000)

########NEW FILE########
__FILENAME__ = version
VERSION = (1, 0, 1)
VERSION_STRING = '.'.join(str(i) for i in VERSION)

########NEW FILE########
__FILENAME__ = cStringIO
raise ImportError


########NEW FILE########
__FILENAME__ = test_srtfile
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import codecs
from datetime import time
import unittest
import random
from io import StringIO

file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.abspath(file_path))

import pysrt
from pysrt import SubRipFile, SubRipItem, SubRipTime
from pysrt.compat import str, open


class TestOpen(unittest.TestCase):

    def setUp(self):
        self.static_path = os.path.join(file_path, 'tests', 'static')
        self.utf8_path = os.path.join(self.static_path, 'utf-8.srt')
        self.windows_path = os.path.join(self.static_path, 'windows-1252.srt')
        self.invalid_path = os.path.join(self.static_path, 'invalid.srt')

    def test_utf8(self):
        self.assertEqual(len(pysrt.open(self.utf8_path)), 1332)
        self.assertEqual(pysrt.open(self.utf8_path).encoding, 'utf_8')
        self.assertRaises(UnicodeDecodeError, pysrt.open,
            self.windows_path)

    def test_windows1252(self):
        srt_file = pysrt.open(self.windows_path, encoding='windows-1252')
        self.assertEqual(len(srt_file), 1332)
        self.assertEqual(srt_file.eol, '\r\n')
        self.assertRaises(UnicodeDecodeError, pysrt.open,
            self.utf8_path, encoding='ascii')

    def test_error_handling(self):
        self.assertRaises(pysrt.Error, pysrt.open, self.invalid_path,
            error_handling=SubRipFile.ERROR_RAISE)


class TestFromString(unittest.TestCase):

    def setUp(self):
        self.static_path = os.path.join(file_path, 'tests', 'static')
        self.utf8_path = os.path.join(self.static_path, 'utf-8.srt')
        self.windows_path = os.path.join(self.static_path, 'windows-1252.srt')
        self.invalid_path = os.path.join(self.static_path, 'invalid.srt')
        self.temp_path = os.path.join(self.static_path, 'temp.srt')

    def test_utf8(self):
        unicode_content = codecs.open(self.utf8_path, encoding='utf_8').read()
        self.assertEqual(len(pysrt.from_string(unicode_content)), 1332)
        self.assertRaises(UnicodeDecodeError, open(self.windows_path).read)

    def test_windows1252(self):
        srt_string = codecs.open(self.windows_path, encoding='windows-1252').read()
        srt_file = pysrt.from_string(srt_string, encoding='windows-1252', eol='\r\n')
        self.assertEqual(len(srt_file), 1332)
        self.assertEqual(srt_file.eol, '\r\n')
        self.assertRaises(UnicodeDecodeError, pysrt.open,
            self.utf8_path, encoding='ascii')


class TestSerialization(unittest.TestCase):

    def setUp(self):
        self.static_path = os.path.join(file_path, 'tests', 'static')
        self.utf8_path = os.path.join(self.static_path, 'utf-8.srt')
        self.windows_path = os.path.join(self.static_path, 'windows-1252.srt')
        self.invalid_path = os.path.join(self.static_path, 'invalid.srt')
        self.temp_path = os.path.join(self.static_path, 'temp.srt')

    def test_compare_from_string_and_from_path(self):
        unicode_content = codecs.open(self.utf8_path, encoding='utf_8').read()
        iterator = zip(pysrt.open(self.utf8_path),
            pysrt.from_string(unicode_content))
        for file_item, string_item in iterator:
            self.assertEqual(str(file_item), str(string_item))

    def test_save(self):
        srt_file = pysrt.open(self.windows_path, encoding='windows-1252')
        srt_file.save(self.temp_path, eol='\n', encoding='utf-8')
        self.assertEqual(bytes(open(self.temp_path, 'rb').read()),
                          bytes(open(self.utf8_path, 'rb').read()))
        os.remove(self.temp_path)

    def test_eol_conversion(self):
        input_file = open(self.windows_path, 'rU', encoding='windows-1252')
        input_file.read()
        self.assertEqual(input_file.newlines, '\r\n')

        srt_file = pysrt.open(self.windows_path, encoding='windows-1252')
        srt_file.save(self.temp_path, eol='\n')

        output_file = open(self.temp_path, 'rU', encoding='windows-1252')
        output_file.read()
        self.assertEqual(output_file.newlines, '\n')


class TestSlice(unittest.TestCase):

    def setUp(self):
        self.file = pysrt.open(os.path.join(file_path, 'tests', 'static',
            'utf-8.srt'))

    def test_slice(self):
        self.assertEqual(len(self.file.slice(ends_before=(1, 2, 3, 4))), 872)
        self.assertEqual(len(self.file.slice(ends_after=(1, 2, 3, 4))), 460)
        self.assertEqual(len(self.file.slice(starts_before=(1, 2, 3, 4))),
                          873)
        self.assertEqual(len(self.file.slice(starts_after=(1, 2, 3, 4))),
                          459)

    def test_at(self):
        self.assertEquals(len(self.file.at((0, 0, 31, 0))), 1)
        self.assertEquals(len(self.file.at(seconds=31)), 1)


class TestShifting(unittest.TestCase):

    def test_shift(self):
        srt_file = SubRipFile([SubRipItem()])
        srt_file.shift(1, 1, 1, 1)
        self.assertEqual(srt_file[0].end, (1, 1, 1, 1))
        srt_file.shift(ratio=2)
        self.assertEqual(srt_file[0].end, (2, 2, 2, 2))


class TestText(unittest.TestCase):

    def test_single_item(self):
        srt_file = SubRipFile([
            SubRipItem(1, {'seconds': 1}, {'seconds': 2}, 'Hello')
        ])
        self.assertEquals(srt_file.text, 'Hello')

    def test_multiple_item(self):
        srt_file = SubRipFile([
            SubRipItem(1, {'seconds': 0}, {'seconds': 3}, 'Hello'),
            SubRipItem(1, {'seconds': 1}, {'seconds': 2}, 'World !')
        ])
        self.assertEquals(srt_file.text, 'Hello\nWorld !')


class TestDuckTyping(unittest.TestCase):

    def setUp(self):
        self.duck = SubRipFile()

    def test_act_as_list(self):
        self.assertTrue(iter(self.duck))

        def iter_over_file():
            try:
                for item in self.duck:
                    pass
            except:
                return False
            return True
        self.assertTrue(iter_over_file())
        self.assertTrue(hasattr(self.duck, '__getitem__'))
        self.assertTrue(hasattr(self.duck, '__setitem__'))
        self.assertTrue(hasattr(self.duck, '__delitem__'))


class TestEOLProperty(unittest.TestCase):

    def setUp(self):
        self.file = SubRipFile()

    def test_default_value(self):
        self.assertEqual(self.file.eol, os.linesep)
        srt_file = SubRipFile(eol='\r\n')
        self.assertEqual(srt_file.eol, '\r\n')

    def test_set_eol(self):
        self.file.eol = '\r\n'
        self.assertEqual(self.file.eol, '\r\n')


class TestCleanIndexes(unittest.TestCase):

    def setUp(self):
        self.file = pysrt.open(os.path.join(file_path, 'tests', 'static',
            'utf-8.srt'))

    def test_clean_indexes(self):
        random.shuffle(self.file)
        for item in self.file:
            item.index = random.randint(0, 1000)
        self.file.clean_indexes()
        self.assertEqual([i.index for i in self.file],
                          list(range(1, len(self.file) + 1)))
        for first, second in zip(self.file[:-1], self.file[1:]):
            self.assertTrue(first <= second)


class TestBOM(unittest.TestCase):
    "In response of issue #6 https://github.com/byroot/pysrt/issues/6"

    def setUp(self):
        self.base_path = os.path.join(file_path, 'tests', 'static')

    def __test_encoding(self, encoding):
        srt_file = pysrt.open(os.path.join(self.base_path, encoding))
        self.assertEqual(len(srt_file), 7)
        self.assertEqual(srt_file[0].index, 1)

    def test_utf8(self):
        self.__test_encoding('bom-utf-8.srt')

    def test_utf16le(self):
        self.__test_encoding('bom-utf-16-le.srt')

    def test_utf16be(self):
        self.__test_encoding('bom-utf-16-be.srt')

    def test_utf32le(self):
        self.__test_encoding('bom-utf-32-le.srt')

    def test_utf32be(self):
        self.__test_encoding('bom-utf-32-be.srt')


class TestIntegration(unittest.TestCase):
    """
    Test some borderlines features found on
    http://ale5000.altervista.org/subtitles.htm
    """

    def setUp(self):
        self.base_path = os.path.join(file_path, 'tests', 'static')

    def test_length(self):
        path = os.path.join(self.base_path, 'capability_tester.srt')
        file = pysrt.open(path)
        self.assertEqual(len(file), 37)

    def test_empty_file(self):
        file = pysrt.open('/dev/null', error_handling=SubRipFile.ERROR_RAISE)
        self.assertEqual(len(file), 0)

    def test_blank_lines(self):
        items = list(pysrt.stream(['\n'] * 20, error_handling=SubRipFile.ERROR_RAISE))
        self.assertEqual(len(items), 0)

    def test_missing_indexes(self):
        items = pysrt.open(os.path.join(self.base_path, 'no-indexes.srt'))
        self.assertEquals(len(items), 7)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_srtitem
#!/usr/bin/env python

import os
import sys
from datetime import time
import unittest

file_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(file_path))

from pysrt import SubRipItem, SubRipTime, InvalidItem
from pysrt.compat import basestring
from pysrt.compat import str


class TestAttributes(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem()

    def test_has_id(self):
        self.assertTrue(hasattr(self.item, 'index'))
        self.assertTrue(isinstance(self.item.index, int))

    def test_has_content(self):
        self.assertTrue(hasattr(self.item, 'text'))
        self.assertTrue(isinstance(self.item.text, basestring))

    def test_has_start(self):
        self.assertTrue(hasattr(self.item, 'start'))
        self.assertTrue(isinstance(self.item.start, SubRipTime))

    def test_has_end(self):
        self.assertTrue(hasattr(self.item, 'end'))
        self.assertTrue(isinstance(self.item.end, SubRipTime))


class TestDuration(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)

    def test_duration(self):
        self.assertEqual(self.item.duration, (0, 0, 20, 0))


class TestCPS(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)

    def test_characters_per_second(self):
        self.assertEqual(self.item.characters_per_second, 0.65)

    def test_text_change(self):
        self.item.text = "Hello world !\nHello world again !"
        self.assertEqual(self.item.characters_per_second, 1.6)

    def test_zero_duration(self):
        self.item.start.shift(seconds = 20)
        self.assertEqual(self.item.characters_per_second, 0.0)

    def test_tags(self):
	    self.item.text = '<b>bold</b>, <i>italic</i>, <u>underlined</u>\n' + \
	    '<font color="#ff0000">red text</font>' + \
	    ', <b>one,<i> two,<u> three</u></i></b>'
	    self.assertEqual(self.item.characters_per_second, 2.45)


class TestTagRemoval(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)

    def test_italics_tag(self):
        self.item.text = "<i>Hello world !</i>"
        self.assertEqual(self.item.text_without_tags,'Hello world !')
        
    def test_bold_tag(self):
        self.item.text = "<b>Hello world !</b>"
        self.assertEqual(self.item.text_without_tags,'Hello world !')

    def test_underline_tag(self):
        self.item.text = "<u>Hello world !</u>"
        self.assertEqual(self.item.text_without_tags,'Hello world !')

    def test_color_tag(self):
        self.item.text = '<font color="#ff0000">Hello world !</font>'
        self.assertEqual(self.item.text_without_tags,'Hello world !')

    def test_all_tags(self):
        self.item.text = '<b>Bold</b>, <i>italic</i>, <u>underlined</u>\n' + \
        '<font color="#ff0000">red text</font>' + \
        ', <b>one,<i> two,<u> three</u></i></b>.'
        self.assertEqual(self.item.text_without_tags,'Bold, italic, underlined' + \
                '\nred text, one, two, three.')


class TestShifting(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)

    def test_shift_up(self):
        self.item.shift(1, 2, 3, 4)
        self.assertEqual(self.item.start, (1, 3, 3, 4))
        self.assertEqual(self.item.end, (1, 3, 23, 4))
        self.assertEqual(self.item.duration, (0, 0, 20, 0))
        self.assertEqual(self.item.characters_per_second, 0.65)

    def test_shift_down(self):
        self.item.shift(5)
        self.item.shift(-1, -2, -3, -4)
        self.assertEqual(self.item.start, (3, 58, 56, 996))
        self.assertEqual(self.item.end, (3, 59, 16, 996))
        self.assertEqual(self.item.duration, (0, 0, 20, 0))
        self.assertEqual(self.item.characters_per_second, 0.65)

    def test_shift_by_ratio(self):
        self.item.shift(ratio=2)
        self.assertEqual(self.item.start, {'minutes': 2})
        self.assertEqual(self.item.end, {'minutes': 2, 'seconds': 40})
        self.assertEqual(self.item.duration, (0, 0, 40, 0))
        self.assertEqual(self.item.characters_per_second, 0.325)


class TestOperators(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)

    def test_cmp(self):
        self.assertEqual(self.item, self.item)


class TestSerialAndParsing(unittest.TestCase):

    def setUp(self):
        self.item = SubRipItem(1, text="Hello world !")
        self.item.shift(minutes=1)
        self.item.end.shift(seconds=20)
        self.string = '1\n00:01:00,000 --> 00:01:20,000\nHello world !\n'
        self.bad_string = 'foobar'
        self.coordinates = ('1\n00:01:00,000 --> 00:01:20,000 X1:000 X2:000 '
                                'Y1:050 Y2:100\nHello world !\n')
        self.vtt = ('1\n00:01:00,000 --> 00:01:20,000 D:vertical A:start '
                                'L:12%\nHello world !\n')
        self.string_index = 'foo\n00:01:00,000 --> 00:01:20,000\nHello !\n'
        self.dots = '1\n00:01:00.000 --> 00:01:20.000\nHello world !\n'
        self.no_index = '00:01:00,000 --> 00:01:20,000\nHello world !\n'
        self.junk_after_timestamp = ('1\n00:01:00,000 --> 00:01:20,000?\n'
                                'Hello world !\n')

    def test_serialization(self):
        self.assertEqual(str(self.item), self.string)

    def test_from_string(self):
        self.assertEqual(SubRipItem.from_string(self.string), self.item)
        self.assertRaises(InvalidItem, SubRipItem.from_string,
            self.bad_string)

    def test_coordinates(self):
        item = SubRipItem.from_string(self.coordinates)
        self.assertEqual(item, self.item)
        self.assertEqual(item.position, 'X1:000 X2:000 Y1:050 Y2:100')

    def test_vtt_positioning(self):
        vtt = SubRipItem.from_string(self.vtt)
        self.assertEqual(vtt.position, 'D:vertical A:start L:12%')
        self.assertEqual(vtt.index, 1)
        self.assertEqual(vtt.text, 'Hello world !')

    def test_idempotence(self):
        vtt = SubRipItem.from_string(self.vtt)
        self.assertEqual(str(vtt), self.vtt)
        item = SubRipItem.from_string(self.coordinates)
        self.assertEqual(str(item), self.coordinates)

    def test_dots(self):
        self.assertEqual(SubRipItem.from_string(self.dots), self.item)

    # Bug reported in https://github.com/byroot/pysrt/issues/16
    def test_paring_error(self):
        self.assertRaises(InvalidItem, SubRipItem.from_string, '1\n'
            '00:01:00,000 -> 00:01:20,000 X1:000 X2:000 '
            'Y1:050 Y2:100\nHello world !\n')

    def test_string_index(self):
        item = SubRipItem.from_string(self.string_index)
        self.assertEquals(item.index, 'foo')
        self.assertEquals(item.text, 'Hello !')

    def test_no_index(self):
        item = SubRipItem.from_string(self.no_index)
        self.assertEquals(item.index, None)
        self.assertEquals(item.text, 'Hello world !')

    def test_junk_after_timestamp(self):
        item = SubRipItem.from_string(self.junk_after_timestamp)
        self.assertEquals(item, self.item)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_srttime
#!/usr/bin/env python

import os
import sys
from datetime import time
import unittest

file_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(file_path))

from pysrt import SubRipTime, InvalidTimeString


class TestSimpleTime(unittest.TestCase):

    def setUp(self):
        self.time = SubRipTime()

    def test_default_value(self):
        self.assertEqual(self.time.ordinal, 0)

    def test_micro_seconds(self):
        self.time.milliseconds = 1
        self.assertEqual(self.time.milliseconds, 1)
        self.time.hours += 42
        self.assertEqual(self.time.milliseconds, 1)
        self.time.milliseconds += 1000
        self.assertEqual(self.time.seconds, 1)

    def test_seconds(self):
        self.time.seconds = 1
        self.assertEqual(self.time.seconds, 1)
        self.time.hours += 42
        self.assertEqual(self.time.seconds, 1)
        self.time.seconds += 60
        self.assertEqual(self.time.minutes, 1)

    def test_minutes(self):
        self.time.minutes = 1
        self.assertEqual(self.time.minutes, 1)
        self.time.hours += 42
        self.assertEqual(self.time.minutes, 1)
        self.time.minutes += 60
        self.assertEqual(self.time.hours, 43)

    def test_hours(self):
        self.time.hours = 1
        self.assertEqual(self.time.hours, 1)
        self.time.minutes += 42
        self.assertEqual(self.time.hours, 1)

    def test_shifting(self):
        self.time.shift(1, 1, 1, 1)
        self.assertEqual(self.time, (1, 1, 1, 1))

    def test_descriptor_from_class(self):
        self.assertRaises(AttributeError, lambda: SubRipTime.hours)


class TestTimeParsing(unittest.TestCase):
    KNOWN_VALUES = (
        ('00:00:00,000', (0, 0, 0, 0)),
        ('00:00:00,001', (0, 0, 0, 1)),
        ('00:00:02,000', (0, 0, 2, 0)),
        ('00:03:00,000', (0, 3, 0, 0)),
        ('04:00:00,000', (4, 0, 0, 0)),
        ('12:34:56,789', (12, 34, 56, 789)),
    )

    def test_parsing(self):
        for time_string, time_items in self.KNOWN_VALUES:
            self.assertEqual(time_string, SubRipTime(*time_items))

    def test_serialization(self):
        for time_string, time_items in self.KNOWN_VALUES:
            self.assertEqual(time_string, str(SubRipTime(*time_items)))

    def test_negative_serialization(self):
        self.assertEqual('00:00:00,000', str(SubRipTime(-1, 2, 3, 4)))

    def test_invalid_time_string(self):
        self.assertRaises(InvalidTimeString, SubRipTime.from_string, 'hello')


class TestCoercing(unittest.TestCase):

    def test_from_tuple(self):
        self.assertEqual((0, 0, 0, 0), SubRipTime())
        self.assertEqual((0, 0, 0, 1), SubRipTime(milliseconds=1))
        self.assertEqual((0, 0, 2, 0), SubRipTime(seconds=2))
        self.assertEqual((0, 3, 0, 0), SubRipTime(minutes=3))
        self.assertEqual((4, 0, 0, 0), SubRipTime(hours=4))
        self.assertEqual((1, 2, 3, 4), SubRipTime(1, 2, 3, 4))

    def test_from_dict(self):
        self.assertEqual(dict(), SubRipTime())
        self.assertEqual(dict(milliseconds=1), SubRipTime(milliseconds=1))
        self.assertEqual(dict(seconds=2), SubRipTime(seconds=2))
        self.assertEqual(dict(minutes=3), SubRipTime(minutes=3))
        self.assertEqual(dict(hours=4), SubRipTime(hours=4))
        self.assertEqual(dict(hours=1, minutes=2, seconds=3, milliseconds=4),
            SubRipTime(1, 2, 3, 4))

    def test_from_time(self):
        time_obj = time(1, 2, 3, 4000)
        self.assertEqual(SubRipTime(1, 2, 3, 4), time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 5) >= time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 3) <= time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 0) != time_obj)
        self.assertEqual(SubRipTime(1, 2, 3, 4).to_time(), time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 5).to_time() >= time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 3).to_time() <= time_obj)
        self.assertTrue(SubRipTime(1, 2, 3, 0).to_time() != time_obj)

    def test_from_ordinal(self):
        self.assertEqual(SubRipTime.from_ordinal(3600000), {'hours': 1})
        self.assertEqual(SubRipTime(1), 3600000)


class TestOperators(unittest.TestCase):

    def setUp(self):
        self.time = SubRipTime(1, 2, 3, 4)

    def test_add(self):
        self.assertEqual(self.time + (1, 2, 3, 4), (2, 4, 6, 8))

    def test_iadd(self):
        self.time += (1, 2, 3, 4)
        self.assertEqual(self.time, (2, 4, 6, 8))

    def test_sub(self):
        self.assertEqual(self.time - (1, 2, 3, 4), 0)

    def test_isub(self):
        self.time -= (1, 2, 3, 4)
        self.assertEqual(self.time, 0)

    def test_mul(self):
        self.assertEqual(self.time * 2,  SubRipTime(2, 4, 6, 8))
        self.assertEqual(self.time * 0.5,  (0, 31, 1, 502))

    def test_imul(self):
        self.time *= 2
        self.assertEqual(self.time,  (2, 4, 6, 8))
        self.time *= 0.5
        self.assertEqual(self.time, (1, 2, 3, 4))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
