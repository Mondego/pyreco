__FILENAME__ = cdiff
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Term based tool to view *colored*, *incremental* diff in a *Git/Mercurial/Svn*
workspace or from stdin, with *side by side* and *auto pager* support. Requires
python (>= 2.5.0) and ``less``.
"""

META_INFO = {
    'version'     : '0.9.3',
    'license'     : 'BSD-3',
    'author'      : 'Matthew Wang',
    'email'       : 'mattwyl(@)gmail(.)com',
    'url'         : 'https://github.com/ymattw/cdiff',
    'keywords'    : 'colored incremental side-by-side diff',
    'description' : ('View colored, incremental diff in a workspace or from '
                     'stdin, with side by side and auto pager support')
}

import sys

if sys.hexversion < 0x02050000:
    raise SystemExit("*** Requires python >= 2.5.0")    # pragma: no cover

# Python < 2.6 does not have next()
try:
    next
except NameError:
    def next(obj): return obj.next()

import os
import re
import signal
import subprocess
import select
import difflib


try:
    unicode
except NameError:
    unicode = str


COLORS = {
    'reset'         : '\x1b[0m',
    'underline'     : '\x1b[4m',
    'reverse'       : '\x1b[7m',
    'red'           : '\x1b[31m',
    'green'         : '\x1b[32m',
    'yellow'        : '\x1b[33m',
    'blue'          : '\x1b[34m',
    'magenta'       : '\x1b[35m',
    'cyan'          : '\x1b[36m',
    'lightred'      : '\x1b[1;31m',
    'lightgreen'    : '\x1b[1;32m',
    'lightyellow'   : '\x1b[1;33m',
    'lightblue'     : '\x1b[1;34m',
    'lightmagenta'  : '\x1b[1;35m',
    'lightcyan'     : '\x1b[1;36m',
}


# Keys for revision control probe, diff and log with diff
VCS_INFO = {
    'Git': {
        'probe' : ['git', 'rev-parse'],
        'diff'  : ['git', 'diff', '--no-ext-diff'],
        'log'   : ['git', 'log', '--patch'],
    },
    'Mercurial': {
        'probe' : ['hg', 'summary'],
        'diff'  : ['hg', 'diff'],
        'log'   : ['hg', 'log', '--patch'],
    },
    'Svn': {
        'probe' : ['svn', 'info'],
        'diff'  : ['svn', 'diff'],
        'log'   : ['svn', 'log', '--diff', '--use-merge-history'],
    },
}


def colorize(text, start_color, end_color='reset'):
    return COLORS[start_color] + text + COLORS[end_color]


class Hunk(object):

    def __init__(self, hunk_headers, hunk_meta, old_addr, new_addr):
        self._hunk_headers = hunk_headers
        self._hunk_meta = hunk_meta
        self._old_addr = old_addr   # tuple (start, offset)
        self._new_addr = new_addr   # tuple (start, offset)
        self._hunk_list = []        # list of tuple (attr, line)

    def append(self, hunk_line):
        """hunk_line is a 2-element tuple: (attr, text), where attr is:
                '-': old, '+': new, ' ': common
        """
        self._hunk_list.append(hunk_line)

    def mdiff(self):
        r"""The difflib._mdiff() function returns an interator which returns a
        tuple: (from line tuple, to line tuple, boolean flag)

        from/to line tuple -- (line num, line text)
            line num -- integer or None (to indicate a context separation)
            line text -- original line text with following markers inserted:
                '\0+' -- marks start of added text
                '\0-' -- marks start of deleted text
                '\0^' -- marks start of changed text
                '\1' -- marks end of added/deleted/changed text

        boolean flag -- None indicates context separation, True indicates
            either "from" or "to" line contains a change, otherwise False.
        """
        return difflib._mdiff(self._get_old_text(), self._get_new_text())

    def _get_old_text(self):
        out = []
        for (attr, line) in self._hunk_list:
            if attr != '+':
                out.append(line)
        return out

    def _get_new_text(self):
        out = []
        for (attr, line) in self._hunk_list:
            if attr != '-':
                out.append(line)
        return out


class UnifiedDiff(object):

    def __init__(self, headers, old_path, new_path, hunks):
        self._headers = headers
        self._old_path = old_path
        self._new_path = new_path
        self._hunks = hunks

    def is_old_path(self, line):
        return line.startswith('--- ')

    def is_new_path(self, line):
        return line.startswith('+++ ')

    def is_hunk_meta(self, line):
        """Minimal valid hunk meta is like '@@ -1 +1 @@', note extra chars
        might occur after the ending @@, e.g. in git log.  '## ' usually
        indicates svn property changes in output from `svn log --diff`
        """
        return (line.startswith('@@ -') and line.find(' @@') >= 8) or \
               (line.startswith('## -') and line.find(' ##') >= 8)

    def parse_hunk_meta(self, hunk_meta):
        # @@ -3,7 +3,6 @@
        a = hunk_meta.split()[1].split(',')   # -3 7
        if len(a) > 1:
            old_addr = (int(a[0][1:]), int(a[1]))
        else:
            # @@ -1 +1,2 @@
            old_addr = (int(a[0][1:]), 0)

        b = hunk_meta.split()[2].split(',')   # +3 6
        if len(b) > 1:
            new_addr = (int(b[0][1:]), int(b[1]))
        else:
            # @@ -0,0 +1 @@
            new_addr = (int(b[0][1:]), 0)

        return (old_addr, new_addr)

    def parse_hunk_line(self, line):
        return (line[0], line[1:])

    def is_old(self, line):
        """Exclude old path and header line from svn log --diff output, allow
        '----' likely to see in diff from yaml file
        """
        return line.startswith('-') and not self.is_old_path(line) and \
            not re.match(r'^-{72}$', line.rstrip())

    def is_new(self, line):
        return line.startswith('+') and not self.is_new_path(line)

    def is_common(self, line):
        return line.startswith(' ')

    def is_eof(self, line):
        # \ No newline at end of file
        # \ No newline at end of property
        return line.startswith(r'\ No newline at end of')

    def is_only_in_dir(self, line):
        return line.startswith('Only in ')

    def is_binary_differ(self, line):
        return re.match('^Binary files .* differ$', line.rstrip())


class PatchStream(object):

    def __init__(self, diff_hdl):
        self._diff_hdl = diff_hdl
        self._stream_header_size = 0
        self._stream_header = []

        # Test whether stream is empty by read 1 line
        line = self._diff_hdl.readline()
        if not line:
            self._is_empty = True
        else:
            self._stream_header.append(line)
            self._stream_header_size += 1
            self._is_empty = False

    def is_empty(self):
        return self._is_empty

    def read_stream_header(self, stream_header_size):
        """Returns a small chunk for patch type detect, suppose to call once"""
        for i in range(1, stream_header_size):
            line = self._diff_hdl.readline()
            if not line:
                break
            self._stream_header.append(line)
            self._stream_header_size += 1
        return self._stream_header

    def __iter__(self):
        for line in self._stream_header:
            yield line
        for line in self._diff_hdl:
            yield line


class PatchStreamForwarder(object):
    """A blocking stream forwarder use `select` and line buffered mode.  Feed
    input stream to a diff format translator and read output stream from it.
    Note input stream is non-seekable, and upstream has eaten some lines.
    """
    def __init__(self, istream, translator):
        assert isinstance(istream, PatchStream)
        assert isinstance(translator, subprocess.Popen)
        self._istream = iter(istream)
        self._in = translator.stdin
        self._out = translator.stdout

    def _can_read(self, timeout=0):
        return select.select([self._out.fileno()], [], [], timeout)[0]

    def _forward_line(self):
        try:
            line = next(self._istream)
            self._in.write(line)
        except StopIteration:
            self._in.close()

    def __iter__(self):
        while True:
            if self._can_read():
                line = self._out.readline()
                if line:
                    yield line
                else:
                    return
            elif not self._in.closed:
                self._forward_line()


class DiffParser(object):

    def __init__(self, stream):

        header = [decode(line) for line in stream.read_stream_header(100)]
        size = len(header)

        if size >= 4 and (header[0].startswith('*** ') and
                          header[1].startswith('--- ') and
                          header[2].rstrip() == '***************' and
                          header[3].startswith('*** ') and
                          header[3].rstrip().endswith(' ****')):
            # For context diff, try use `filterdiff` to translate it to unified
            # format and provide a new stream
            #
            self._type = 'context'
            try:
                # Use line buffered mode so that to readline() in block mode
                self._translator = subprocess.Popen(
                    ['filterdiff', '--format=unified'], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, bufsize=1)
            except OSError:
                raise SystemExit('*** Context diff support depends on '
                                 'filterdiff')
            self._stream = PatchStreamForwarder(stream, self._translator)
            return

        for n in range(size):
            if header[n].startswith('--- ') and (n < size - 1) and \
                    header[n+1].startswith('+++ '):
                self._type = 'unified'
                self._stream = stream
                break
        else:
            # `filterdiff` translates unknown diff to nothing, fall through to
            # unified diff give cdiff a chance to show everything as headers
            #
            sys.stderr.write("*** unknown format, fall through to 'unified'\n")
            self._type = 'unified'
            self._stream = stream

    def get_diff_generator(self):
        """parse all diff lines, construct a list of UnifiedDiff objects"""
        diff = UnifiedDiff([], None, None, [])
        headers = []

        for line in self._stream:
            line = decode(line)

            if diff.is_old_path(line):
                # FIXME: '--- ' breaks here, better to probe next line
                if diff._old_path and diff._new_path and diff._hunks:
                    # See a new diff, yield previous diff if exists
                    yield diff
                diff = UnifiedDiff(headers, line, None, [])
                headers = []

            elif diff.is_new_path(line) and diff._old_path:
                diff._new_path = line

            elif diff.is_hunk_meta(line):
                hunk_meta = line
                try:
                    old_addr, new_addr = diff.parse_hunk_meta(hunk_meta)
                except (IndexError, ValueError):
                    raise RuntimeError('invalid hunk meta: %s' % hunk_meta)
                hunk = Hunk(headers, hunk_meta, old_addr, new_addr)
                headers = []
                diff._hunks.append(hunk)

            elif diff._hunks and not headers and (diff.is_old(line) or
                                                  diff.is_new(line) or
                                                  diff.is_common(line)):
                diff._hunks[-1].append(diff.parse_hunk_line(line))

            elif diff.is_eof(line):
                # ignore
                pass

            elif diff.is_only_in_dir(line) or \
                    diff.is_binary_differ(line):
                # 'Only in foo:' and 'Binary files ... differ' are considered
                # as separate diffs, so yield current diff, then this line
                #
                if diff._old_path and diff._new_path and diff._hunks:
                    # Current diff is comppletely constructed
                    yield diff
                headers.append(line)
                yield UnifiedDiff(headers, '', '', [])
                headers = []
                diff = UnifiedDiff([], None, None, [])

            else:
                # All other non-recognized lines are considered as headers or
                # hunk headers respectively
                #
                headers.append(line)

        # Validate and yield the last patch set if it is not yielded yet
        if diff._old_path:
            assert diff._new_path is not None
            if diff._hunks:
                assert len(diff._hunks[-1]._hunk_meta) > 0
                assert len(diff._hunks[-1]._hunk_list) > 0
            yield diff

        if headers:
            # Tolerate dangling headers, just yield a UnifiedDiff object with
            # only header lines
            #
            yield UnifiedDiff(headers, '', '', [])


class DiffMarker(object):

    def markup(self, diffs, side_by_side=False, width=0):
        """Returns a generator"""
        if side_by_side:
            for diff in diffs:
                for line in self._markup_side_by_side(diff, width):
                    yield line
        else:
            for diff in diffs:
                for line in self._markup_traditional(diff):
                    yield line

    def _markup_traditional(self, diff):
        """Returns a generator"""
        for line in diff._headers:
            yield self._markup_header(line)

        yield self._markup_old_path(diff._old_path)
        yield self._markup_new_path(diff._new_path)

        for hunk in diff._hunks:
            for hunk_header in hunk._hunk_headers:
                yield self._markup_hunk_header(hunk_header)
            yield self._markup_hunk_meta(hunk._hunk_meta)
            for old, new, changed in hunk.mdiff():
                if changed:
                    if not old[0]:
                        # The '+' char after \x00 is kept
                        # DEBUG: yield 'NEW: %s %s\n' % (old, new)
                        line = new[1].strip('\x00\x01')
                        yield self._markup_new(line)
                    elif not new[0]:
                        # The '-' char after \x00 is kept
                        # DEBUG: yield 'OLD: %s %s\n' % (old, new)
                        line = old[1].strip('\x00\x01')
                        yield self._markup_old(line)
                    else:
                        # DEBUG: yield 'CHG: %s %s\n' % (old, new)
                        yield self._markup_old('-') + \
                            self._markup_mix(old[1], 'red')
                        yield self._markup_new('+') + \
                            self._markup_mix(new[1], 'green')
                else:
                    yield self._markup_common(' ' + old[1])

    def _markup_side_by_side(self, diff, width):
        """Returns a generator"""
        wrap_char = colorize('>', 'lightmagenta')

        def _normalize(line):
            return line.replace(
                '\t', ' ' * 8).replace('\n', '').replace('\r', '')

        def _fit_with_marker(text, markup_fn, width, pad=False):
            """Wrap or pad input pure text, then markup"""
            if len(text) > width:
                return markup_fn(text[:(width - 1)]) + wrap_char
            elif pad:
                pad_len = width - len(text)
                return '%s%*s' % (markup_fn(text), pad_len, '')
            else:
                return markup_fn(text)

        def _fit_with_marker_mix(text, base_color, width, pad=False):
            """Wrap or pad input text which contains mdiff tags, markup at the
            meantime, note only left side need to set `pad`
            """
            out = [COLORS[base_color]]
            count = 0
            tag_re = re.compile(r'\x00[+^-]|\x01')

            while text and count < width:
                if text.startswith('\x00-'):    # del
                    out.append(COLORS['reverse'] + COLORS[base_color])
                    text = text[2:]
                elif text.startswith('\x00+'):  # add
                    out.append(COLORS['reverse'] + COLORS[base_color])
                    text = text[2:]
                elif text.startswith('\x00^'):  # change
                    out.append(COLORS['underline'] + COLORS[base_color])
                    text = text[2:]
                elif text.startswith('\x01'):   # reset
                    out.append(COLORS['reset'] + COLORS[base_color])
                    text = text[1:]
                else:
                    # FIXME: utf-8 wchar might break the rule here, e.g.
                    # u'\u554a' takes double width of a single letter, also
                    # this depends on your terminal font.  I guess audience of
                    # this tool never put that kind of symbol in their code :-)
                    #
                    out.append(text[0])
                    count += 1
                    text = text[1:]

            if count == width and tag_re.sub('', text):
                # Was stripped: output fulfil and still has normal char in text
                out[-1] = COLORS['reset'] + wrap_char
            elif count < width and pad:
                pad_len = width - count
                out.append('%s%*s' % (COLORS['reset'], pad_len, ''))
            else:
                out.append(COLORS['reset'])

            return ''.join(out)

        # Set up line width
        if width <= 0:
            width = 80

        # Set up number width, note last hunk might be empty
        try:
            (start, offset) = diff._hunks[-1]._old_addr
            max1 = start + offset - 1
            (start, offset) = diff._hunks[-1]._new_addr
            max2 = start + offset - 1
        except IndexError:
            max1 = max2 = 0
        num_width = max(len(str(max1)), len(str(max2)))

        # Setup lineno and line format
        left_num_fmt = colorize('%%(left_num)%ds' % num_width, 'yellow')
        right_num_fmt = colorize('%%(right_num)%ds' % num_width, 'yellow')
        line_fmt = left_num_fmt + ' %(left)s ' + COLORS['reset'] + \
            right_num_fmt + ' %(right)s\n'

        # yield header, old path and new path
        for line in diff._headers:
            yield self._markup_header(line)
        yield self._markup_old_path(diff._old_path)
        yield self._markup_new_path(diff._new_path)

        # yield hunks
        for hunk in diff._hunks:
            for hunk_header in hunk._hunk_headers:
                yield self._markup_hunk_header(hunk_header)
            yield self._markup_hunk_meta(hunk._hunk_meta)
            for old, new, changed in hunk.mdiff():
                if old[0]:
                    left_num = str(hunk._old_addr[0] + int(old[0]) - 1)
                else:
                    left_num = ' '

                if new[0]:
                    right_num = str(hunk._new_addr[0] + int(new[0]) - 1)
                else:
                    right_num = ' '

                left = _normalize(old[1])
                right = _normalize(new[1])

                if changed:
                    if not old[0]:
                        left = '%*s' % (width, ' ')
                        right = right.lstrip('\x00+').rstrip('\x01')
                        right = _fit_with_marker(
                            right, self._markup_new, width)
                    elif not new[0]:
                        left = left.lstrip('\x00-').rstrip('\x01')
                        left = _fit_with_marker(left, self._markup_old, width)
                        right = ''
                    else:
                        left = _fit_with_marker_mix(left, 'red', width, 1)
                        right = _fit_with_marker_mix(right, 'green', width)
                else:
                    left = _fit_with_marker(
                        left, self._markup_common, width, 1)
                    right = _fit_with_marker(right, self._markup_common, width)
                yield line_fmt % {
                    'left_num': left_num,
                    'left': left,
                    'right_num': right_num,
                    'right': right
                }

    def _markup_header(self, line):
        return colorize(line, 'cyan')

    def _markup_old_path(self, line):
        return colorize(line, 'yellow')

    def _markup_new_path(self, line):
        return colorize(line, 'yellow')

    def _markup_hunk_header(self, line):
        return colorize(line, 'lightcyan')

    def _markup_hunk_meta(self, line):
        return colorize(line, 'lightblue')

    def _markup_common(self, line):
        return colorize(line, 'reset')

    def _markup_old(self, line):
        return colorize(line, 'lightred')

    def _markup_new(self, line):
        return colorize(line, 'lightgreen')

    def _markup_mix(self, line, base_color):
        del_code = COLORS['reverse'] + COLORS[base_color]
        add_code = COLORS['reverse'] + COLORS[base_color]
        chg_code = COLORS['underline'] + COLORS[base_color]
        rst_code = COLORS['reset'] + COLORS[base_color]
        line = line.replace('\x00-', del_code)
        line = line.replace('\x00+', add_code)
        line = line.replace('\x00^', chg_code)
        line = line.replace('\x01', rst_code)
        return colorize(line, base_color)


def markup_to_pager(stream, opts):
    """Pipe unified diff stream to pager (less).

    Note: have to create pager Popen object before the translator Popen object
    in PatchStreamForwarder, otherwise the `stdin=subprocess.PIPE` would cause
    trouble to the translator pipe (select() never see EOF after input stream
    ended), most likely python bug 12607 (http://bugs.python.org/issue12607)
    which was fixed in python 2.7.3.

    See issue #30 (https://github.com/ymattw/cdiff/issues/30) for more
    information.
    """
    pager_cmd = ['less']
    if not os.getenv('LESS'):
        # Args stolen from git source: github.com/git/git/blob/master/pager.c
        pager_cmd.extend(['-FRSX'])
    pager = subprocess.Popen(
        pager_cmd, stdin=subprocess.PIPE, stdout=sys.stdout)

    diffs = DiffParser(stream).get_diff_generator()
    marker = DiffMarker()
    color_diff = marker.markup(diffs, side_by_side=opts.side_by_side,
                               width=opts.width)

    for line in color_diff:
        pager.stdin.write(line.encode('utf-8'))

    pager.stdin.close()
    pager.wait()


def check_command_status(arguments):
    """Return True if command returns 0."""
    try:
        return subprocess.call(
            arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
    except OSError:
        return False


def revision_control_diff(args):
    """Return diff from revision control system."""
    for _, ops in VCS_INFO.items():
        if check_command_status(ops['probe']):
            return subprocess.Popen(
                ops['diff'] + args, stdout=subprocess.PIPE).stdout


def revision_control_log(args):
    """Return log from revision control system."""
    for _, ops in VCS_INFO.items():
        if check_command_status(ops['probe']):
            return subprocess.Popen(
                ops['log'] + args, stdout=subprocess.PIPE).stdout


def decode(line):
    """Decode UTF-8 if necessary."""
    if isinstance(line, unicode):
        return line

    for encoding in ['utf-8', 'latin1']:
        try:
            return line.decode(encoding)
        except UnicodeDecodeError:
            pass

    return '*** cdiff: undecodable bytes ***\n'


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from optparse import (OptionParser, BadOptionError, AmbiguousOptionError,
                          OptionGroup)

    class PassThroughOptionParser(OptionParser):
        """Stop parsing on first unknown option (e.g. --cached, -U10) and pass
        them down.  Note the `opt_str` in exception object does not give us
        chance to take the full option back, e.g. for '-U10' it will only
        contain '-U' and the '10' part will be lost.  Ref: http://goo.gl/IqY4A
        (on stackoverflow).  My hack is to try parse and insert a '--' in place
        and parse again.  Let me know if someone has better solution.
        """
        def _process_args(self, largs, rargs, values):
            left = largs[:]
            right = rargs[:]
            try:
                OptionParser._process_args(self, left, right, values)
            except (BadOptionError, AmbiguousOptionError):
                parsed_num = len(rargs) - len(right) - 1
                rargs.insert(parsed_num, '--')
            OptionParser._process_args(self, largs, rargs, values)

    supported_vcs = sorted(VCS_INFO.keys())

    usage = """%prog [options] [file|dir ...]"""
    parser = PassThroughOptionParser(
        usage=usage, description=META_INFO['description'],
        version='%%prog %s' % META_INFO['version'])
    parser.add_option(
        '-s', '--side-by-side', action='store_true',
        help='enable side-by-side mode')
    parser.add_option(
        '-w', '--width', type='int', default=80, metavar='N',
        help='set text width for side-by-side mode, default is 80')
    parser.add_option(
        '-l', '--log', action='store_true',
        help='show log with changes from revision control')
    parser.add_option(
        '-c', '--color', default='auto', metavar='M',
        help="""colorize mode 'auto' (default), 'always', or 'never'""")

    # Hack: use OptionGroup text for extra help message after option list
    option_group = OptionGroup(
        parser, "Note", ("Option parser will stop on first unknown option "
                         "and pass them down to underneath revision control"))
    parser.add_option_group(option_group)

    opts, args = parser.parse_args()

    if opts.log:
        diff_hdl = revision_control_log(args)
        if not diff_hdl:
            sys.stderr.write(('*** Not in a supported workspace, supported '
                              'are: %s\n') % ', '.join(supported_vcs))
            return 1
    elif sys.stdin.isatty():
        diff_hdl = revision_control_diff(args)
        if not diff_hdl:
            sys.stderr.write(('*** Not in a supported workspace, supported '
                              'are: %s\n\n') % ', '.join(supported_vcs))
            parser.print_help()
            return 1
    else:
        diff_hdl = (sys.stdin.buffer if hasattr(sys.stdin, 'buffer')
                    else sys.stdin)

    stream = PatchStream(diff_hdl)

    # Don't let empty diff pass thru
    if stream.is_empty():
        return 0

    if opts.color == 'always' or \
            (opts.color == 'auto' and sys.stdout.isatty()):
        markup_to_pager(stream, opts)
    else:
        # pipe out stream untouched to make sure it is still a patch
        byte_output = (sys.stdout.buffer if hasattr(sys.stdout, 'buffer')
                       else sys.stdout)
        for line in stream:
            byte_output.write(line)

    if diff_hdl is not sys.stdin:
        diff_hdl.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())

# vim:set et sts=4 sw=4 tw=79:

########NEW FILE########
__FILENAME__ = test_cdiff
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit test for cdiff"""

import sys
if sys.hexversion < 0x02050000:
    raise SystemExit("*** Requires python >= 2.5.0")    # pragma: no cover

import unittest
import tempfile
import subprocess
import os

sys.path.insert(0, '')
import cdiff


class Sequential(object):
    """A non-seekable iterator, mock of file object"""

    def __init__(self, items):
        self._items = items
        self._index = 0

    def __iter__(self):
        while True:
            try:
                item = self._items[self._index]
            except IndexError:
                raise StopIteration
            yield item
            self._index += 1

    def readline(self):
        try:
            item = self._items[self._index]
        except IndexError:
            return ''
        self._index += 1
        return item


class PatchStreamTest(unittest.TestCase):

    def test_is_empty(self):
        stream = cdiff.PatchStream(Sequential([]))
        self.assertTrue(stream.is_empty())

        stream = cdiff.PatchStream(Sequential(['hello', 'world']))
        self.assertFalse(stream.is_empty())

    def test_read_stream_header(self):
        stream = cdiff.PatchStream(Sequential([]))
        self.assertEqual(stream.read_stream_header(1), [])

        items = ['hello', 'world', 'again']

        stream = cdiff.PatchStream(Sequential(items))
        self.assertEqual(stream.read_stream_header(2), items[:2])

        stream = cdiff.PatchStream(Sequential(items))
        self.assertEqual(stream.read_stream_header(4), items[:])

    def test_iter_after_read_stream_header(self):
        items = ['hello', 'world', 'again', 'and', 'again']
        stream = cdiff.PatchStream(Sequential(items))

        _ = stream.read_stream_header(2)
        out = list(stream)
        self.assertEqual(out, items)


class DecodeTest(unittest.TestCase):

    def test_normal(self):
        utext = 'hello'.encode('utf-8')
        self.assertEqual('hello', cdiff.decode(utext))

    def test_latin_1(self):
        text = '\x80\x02q\x01(U'
        if sys.version_info[0] == 2:
            decoded_text = text.decode('latin-1')
        else:
            decoded_text = text
        self.assertEqual(decoded_text, cdiff.decode(text))


class HunkTest(unittest.TestCase):

    def test_get_old_text(self):
        hunk = cdiff.Hunk([], '@@ -1,2 +1,2 @@', (1, 2), (1, 2))
        hunk.append(('-', 'foo\n'))
        hunk.append(('+', 'bar\n'))
        hunk.append((' ', 'common\n'))
        self.assertEqual(hunk._get_old_text(), ['foo\n', 'common\n'])

    def test_get_new_text(self):
        hunk = cdiff.Hunk([], '@@ -1,2 +1,2 @@', (1, 2), (1, 2))
        hunk.append(('-', 'foo\n'))
        hunk.append(('+', 'bar\n'))
        hunk.append((' ', 'common\n'))
        self.assertEqual(hunk._get_new_text(), ['bar\n', 'common\n'])


class DiffMarkupTest(unittest.TestCase):

    def _init_diff(self):
        """Return a minimal diff contains all required samples
            header
            --- old
            +++ new
            hunk header
            @@ -1,4 +1,4 @@
            -hhello
            +helloo
            +spammm
             world
            -garb
            -Again
            +again
        """

        hunk = cdiff.Hunk(['hunk header\n'], '@@ -1,4 +1,4 @@\n',
                          (1, 4), (1, 4))
        hunk.append(('-', 'hhello\n'))
        hunk.append(('+', 'helloo\n'))
        hunk.append(('+', 'spammm\n'))
        hunk.append((' ', 'world\n'))
        hunk.append(('-', 'garb\n'))
        hunk.append(('-', 'Again\n'))
        hunk.append(('+', 'again\n'))
        diff = cdiff.UnifiedDiff(['header\n'], '--- old\n', '+++ new\n', [hunk])
        return diff

    def test_markup_mix(self):
        marker = cdiff.DiffMarker()
        line = 'foo \x00-del\x01 \x00+add\x01 \x00^chg\x01 bar'
        base_color = 'red'
        self.assertEqual(
            marker._markup_mix(line, base_color),
            '\x1b[31mfoo \x1b[7m\x1b[31mdel\x1b[0m\x1b[31m '
            '\x1b[7m\x1b[31madd\x1b[0m\x1b[31m '
            '\x1b[4m\x1b[31mchg\x1b[0m\x1b[31m bar\x1b[0m')

    def test_markup_traditional_hunk_header(self):
        hunk = cdiff.Hunk(['hunk header\n'], '@@ -0 +0 @@\n', (0, 0), (0, 0))
        diff = cdiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = cdiff.DiffMarker()

        out = list(marker._markup_traditional(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[1;36mhunk header\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;34m@@ -0 +0 @@\n\x1b[0m')

    def test_markup_traditional_old_changed(self):
        hunk = cdiff.Hunk([], '@@ -1 +0,0 @@\n', (1, 0), (0, 0))
        hunk.append(('-', 'spam\n'))
        diff = cdiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = cdiff.DiffMarker()

        out = list(marker._markup_traditional(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[1;34m@@ -1 +0,0 @@\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;31m-spam\n\x1b[0m')

    def test_markup_traditional_new_changed(self):
        hunk = cdiff.Hunk([], '@@ -0,0 +1 @@\n', (0, 0), (1, 0))
        hunk.append(('+', 'spam\n'))
        diff = cdiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = cdiff.DiffMarker()

        out = list(marker._markup_traditional(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[1;34m@@ -0,0 +1 @@\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;32m+spam\n\x1b[0m')

    def test_markup_traditional_both_changed(self):
        hunk = cdiff.Hunk([], '@@ -1,2 +1,2 @@\n', (1, 2), (1, 2))
        hunk.append(('-', 'hella\n'))
        hunk.append(('+', 'hello\n'))
        hunk.append((' ', 'common\n'))
        diff = cdiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = cdiff.DiffMarker()

        out = list(marker._markup_traditional(diff))
        self.assertEqual(len(out), 6)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[1;34m@@ -1,2 +1,2 @@\n\x1b[0m')
        self.assertEqual(
            out[3],
            '\x1b[1;31m-\x1b[0m\x1b[31mhell'
            '\x1b[4m\x1b[31ma\x1b[0m\x1b[31m\n\x1b[0m')
        self.assertEqual(
            out[4],
            '\x1b[1;32m+\x1b[0m\x1b[32mhell'
            '\x1b[4m\x1b[32mo\x1b[0m\x1b[32m\n\x1b[0m')
        self.assertEqual(out[5], '\x1b[0m common\n\x1b[0m')

    def test_markup_side_by_side_padded(self):
        diff = self._init_diff()
        marker = cdiff.DiffMarker()

        out = list(marker._markup_side_by_side(diff, 7))
        self.assertEqual(len(out), 10)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[1;34m@@ -1,4 +1,4 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mh\x1b[0m\x1b[31mhello\x1b[0m  '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32mo\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m '
            '\x1b[0m         '
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[1;32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m   '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[1;31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[4m\x1b[31mA\x1b[0m\x1b[31mgain\x1b[0m   '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[4m\x1b[32ma\x1b[0m\x1b[32mgain\x1b[0m\n')

    def test_markup_side_by_side_neg_width(self):
        diff = self._init_diff()
        marker = cdiff.DiffMarker()
        out = list(marker._markup_side_by_side(diff, -1))
        self.assertEqual(len(out), 10)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[1;34m@@ -1,4 +1,4 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mh\x1b[0m\x1b[31mhello\x1b[0m ' +
            (' ' * 74) +
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32mo\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m '
            '\x1b[0m  ' + (' ' * 80) +
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[1;32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m ' + (' ' * 75) +
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[1;31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[4m\x1b[31mA\x1b[0m\x1b[31mgain\x1b[0m ' +
            (' ' * 75) +
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[4m\x1b[32ma\x1b[0m\x1b[32mgain\x1b[0m\n')

    def test_markup_side_by_side_off_by_one(self):
        diff = self._init_diff()
        marker = cdiff.DiffMarker()
        out = list(marker._markup_side_by_side(diff, 6))
        self.assertEqual(len(out), 10)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[1;34m@@ -1,4 +1,4 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mh\x1b[0m\x1b[31mhello\x1b[0m '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32mo\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m \x1b[0m        '
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[1;32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m  '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[1;31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[4m\x1b[31mA\x1b[0m\x1b[31mgain\x1b[0m  '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[4m\x1b[32ma\x1b[0m\x1b[32mgain\x1b[0m\n')

    def test_markup_side_by_side_wrapped(self):
        diff = self._init_diff()
        marker = cdiff.DiffMarker()
        out = list(marker._markup_side_by_side(diff, 5))
        self.assertEqual(len(out), 10)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[1;36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[1;34m@@ -1,4 +1,4 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mh\x1b[0m\x1b[31mhel\x1b[0m\x1b[1;35m>\x1b[0m '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhell\x1b[0m\x1b[1;35m>\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m \x1b[0m       '
            '\x1b[0m\x1b[33m2\x1b[0m '
            ''
            '\x1b[1;32mspam\x1b[0m\x1b[1;35m>\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[1;31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[4m\x1b[31mA\x1b[0m\x1b[31mgain\x1b[0m '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[4m\x1b[32ma\x1b[0m\x1b[32mgain\x1b[0m\n')


class UnifiedDiffTest(unittest.TestCase):

    diff = cdiff.UnifiedDiff(None, None, None, None)

    def test_is_hunk_meta_normal(self):
        self.assertTrue(self.diff.is_hunk_meta('@@ -1 +1 @@'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo\n'))
        self.assertTrue(
            self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo\r\n'))

    def test_is_hunk_meta_svn_prop(self):
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##'))
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##\n'))
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##\r\n'))

    def test_is_hunk_meta_neg(self):
        self.assertFalse(self.diff.is_hunk_meta('@@ -1 + @@'))
        self.assertFalse(self.diff.is_hunk_meta('@@ -this is not a hunk meta'))
        self.assertFalse(self.diff.is_hunk_meta('## -this is not either'))

    def test_parse_hunk_meta_normal(self):
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3,7 +3,6 @@'),
                         ((3, 7), (3, 6)))

    def test_parse_hunk_meta_missing(self):
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3 +3,6 @@'),
                         ((3, 0), (3, 6)))
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3,7 +3 @@'),
                         ((3, 7), (3, 0)))
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3 +3 @@'),
                         ((3, 0), (3, 0)))

    def test_parse_hunk_meta_svn_prop(self):
        self.assertEqual(self.diff.parse_hunk_meta('## -0,0 +1 ##'),
                         ((0, 0), (1, 0)))

    def test_is_old(self):
        self.assertTrue(self.diff.is_old('-hello world'))
        self.assertTrue(self.diff.is_old('----'))            # yaml

    def test_is_old_neg(self):
        self.assertFalse(self.diff.is_old('--- considered as old path'))
        self.assertFalse(self.diff.is_old('-' * 72))         # svn log --diff

    def test_is_new(self):
        self.assertTrue(self.diff.is_new('+hello world'))
        self.assertTrue(self.diff.is_new('++++hello world'))

    def test_is_new_neg(self):
        self.assertFalse(self.diff.is_new('+++ considered as new path'))


class DiffParserTest(unittest.TestCase):

    def test_type_detect_unified(self):
        patch = """\
spam
--- a
+++ b
@@ -1,2 +1,2 @@
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertEqual(parser._type, 'unified')

    def test_type_detect_context(self):
        patch = """\
*** /path/to/original timestamp
--- /path/to/new timestamp
***************
*** 1,1 ****
--- 1,2 ----
+ This is an important
  This part of the
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertEqual(parser._type, 'context')

    def test_type_detect_neg(self):
        patch = """\
spam
--- a
spam
+++ b

"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertEqual(parser._type, 'unified')

    def test_parse_invalid_hunk_meta(self):
        patch = """\
spam
--- a
+++ b
spam
@@ -a,a +0 @@
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertRaises(RuntimeError, list, parser.get_diff_generator())

    def test_parse_dangling_header(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
spam
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._headers), 1)
        self.assertEqual(out[1]._headers[0], 'spam\n')
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._hunks), 0)

    def test_parse_missing_new_path(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertRaises(AssertionError, list, parser.get_diff_generator())

    def test_parse_missing_hunk_meta(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
+++ d
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._headers), 0)
        self.assertEqual(out[1]._old_path, '--- c\n')
        self.assertEqual(out[1]._new_path, '+++ d\n')
        self.assertEqual(len(out[1]._hunks), 0)

    def test_parse_missing_hunk_list(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
+++ d
@@ -1,2 +1,2 @@
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        self.assertRaises(AssertionError, list, parser.get_diff_generator())

    def test_parse_only_in_dir(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Only in foo: foo
--- c
+++ d
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._headers, ['Only in foo: foo\n'])
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_only_in_dir_at_last(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Only in foo: foo
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._headers, ['Only in foo: foo\n'])

    def test_parse_binary_differ_diff_ru(self):
        patch = """\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Binary files a/1.pdf and b/1.pdf differ
--- c
+++ d
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._headers), 1)
        self.assertTrue(out[1]._headers[0].startswith('Binary files'))
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_binary_differ_git(self):
        patch = """\
diff --git a/foo b/foo
index 529d8a3..ad71911 100755
--- a/foo
+++ b/foo
@@ -1,2 +1,2 @@
-foo
+bar
 common
diff --git a/example.pdf b/example.pdf
index 1eacfd8..3696851 100644
Binary files a/example.pdf and b/example.pdf differ
diff --git a/bar b/bar
index 529e8a3..ad71921 100755
--- a/bar
+++ b/bar
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)

        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._headers), 3)
        self.assertTrue(out[1]._headers[2].startswith('Binary files'))
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_svn_prop(self):
        patch = """\
--- a
+++ b
Added: svn:executable
## -0,0 +1 ##
+*
\\ No newline at end of property
Added: svn:keywords
## -0,0 +1 ##
+Id
"""
        items = patch.splitlines(True)
        stream = cdiff.PatchStream(Sequential(items))
        parser = cdiff.DiffParser(stream)
        out = list(parser.get_diff_generator())
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]._hunks), 2)

        hunk = out[0]._hunks[1]
        self.assertEqual(hunk._hunk_headers, ['Added: svn:keywords\n'])
        self.assertEqual(hunk._hunk_list, [('+', 'Id\n')])


class MainTest(unittest.TestCase):

    def setUp(self):
        self._cwd = os.getcwd()
        self._ws = tempfile.mkdtemp(prefix='test_cdiff')
        self._non_ws = tempfile.mkdtemp(prefix='test_cdiff')
        cmd = ('cd %s; git init; git config user.name me; '
               'git config user.email me@example.org') % self._ws
        subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
        self._change_file('init')

    def tearDown(self):
        os.chdir(self._cwd)
        cmd = ['/bin/rm', '-rf', self._ws, self._non_ws]
        subprocess.call(cmd)

    def _change_file(self, text):
        cmd = ['/bin/sh', '-c',
               'cd %s; echo "%s" > foo' % (self._ws, text)]
        subprocess.call(cmd)

    def _commit_file(self):
        cmd = ['/bin/sh', '-c',
               'cd %s; git add foo; git commit foo -m update' % self._ws]
        subprocess.call(cmd, stdout=subprocess.PIPE)

    def test_read_diff(self):
        sys.argv = sys.argv[:1]
        self._change_file('read_diff')

        os.chdir(self._ws)
        ret = cdiff.main()
        os.chdir(self._cwd)
        self.assertEqual(ret, 0)

    def test_read_diff_neg(self):
        sys.argv = sys.argv[:1]
        os.chdir(self._non_ws)
        ret = cdiff.main()
        os.chdir(self._cwd)
        self.assertNotEqual(ret, 0)

    def test_read_log(self):
        sys.argv = [sys.argv[0], '--log']
        self._change_file('read_log')
        self._commit_file()

        os.chdir(self._ws)
        ret = cdiff.main()
        os.chdir(self._cwd)
        self.assertEqual(ret, 0)

    def test_read_log_neg(self):
        sys.argv = [sys.argv[0], '--log']
        os.chdir(self._non_ws)
        ret = cdiff.main()
        os.chdir(self._cwd)
        self.assertNotEqual(ret, 0)


if __name__ == '__main__':
    unittest.main()

# vim:set et sts=4 sw=4 tw=80:

########NEW FILE########
