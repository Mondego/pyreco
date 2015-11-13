__FILENAME__ = edit
# Borrowed from SublimeXiKi
# https://github.com/lunixbochs/SublimeXiki/blob/st3/edit.py

import sublime
import sublime_plugin
from sys import version_info
PY3K = version_info >= (3, 0, 0)

try:
    sublime.edit_storage
except AttributeError:
    sublime.edit_storage = {}


class EditStep:
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = args

    def run(self, view, edit):
        if self.cmd == 'callback':
            return self.args[0](view, edit)

        funcs = {
            'insert': view.insert,
            'erase': view.erase,
            'replace': view.replace,
        }
        func = funcs.get(self.cmd)
        if func:
            func(edit, *self.args)


class Edit:
    def __init__(self, view):
        self.view = view
        self.steps = []

    def step(self, cmd, *args):
        step = EditStep(cmd, *args)
        self.steps.append(step)

    def insert(self, point, string):
        self.step('insert', point, string)

    def erase(self, region):
        self.step('erase', region)

    def replace(self, region, string):
        self.step('replace', region, string)

    def callback(self, func):
        self.step('callback', func)

    def run(self, view, edit):
        for step in self.steps:
            step.run(view, edit)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        view = self.view
        if not PY3K:
            edit = view.begin_edit()
            self.run(view, edit)
            view.end_edit(edit)
        else:
            key = str(hash(tuple(self.steps)))
            sublime.edit_storage[key] = self.run
            view.run_command('worksheet_apply_edit', {'key': key})


class WorksheetApplyEditCommand(sublime_plugin.TextCommand):
    def run(self, edit, key):
        sublime.edit_storage.pop(key)(self.view, edit)

########NEW FILE########
__FILENAME__ = badness
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from .chardata import (SCRIPT_MAP, SINGLE_BYTE_WEIRDNESS,
    WINDOWS_1252_GREMLINS)

import sys
if sys.hexversion >= 0x03000000:
    unichr = chr

CONSISTENT_SCRIPTS_RE = re.compile(r'([A-Za-z])(\1+)')
LETTER_SEGMENTS_RE = re.compile(r'([A-Za-z]+)')
LOWERCASE_RE = re.compile(r'([a-z])')
DOUBLE_WEIRD_RE = re.compile(r'(WW+)')
GREMLINS_RE = re.compile('[' +
    ''.join([unichr(codepoint) for codepoint in WINDOWS_1252_GREMLINS])
    + ']')

WEIRD_CHARACTER_RES = []
for i in range(5):
    chars = [unichr(codepoint) for codepoint in range(0x80, 0x100)
             if SINGLE_BYTE_WEIRDNESS[codepoint] > i]
    WEIRD_CHARACTER_RES.append(re.compile('[' + ''.join(chars) + ']'))

def num_consistent_scripts(scriptdata):
    """
    Count the number of times two adjacent letters are in the same script.

    Uses a "scriptdata" string as input, not the actual text.

    >>> num_consistent_scripts('LL AAA.')
    3
    >>> num_consistent_scripts('LLAAA ...')
    3
    >>> num_consistent_scripts('LAL')
    0
    >>> num_consistent_scripts('..LLL..')
    2
    >>> num_consistent_scripts('LWWW')
    2
    """
    matches = CONSISTENT_SCRIPTS_RE.findall(scriptdata)
    total = 0
    for first, rest in matches:
        total += len(rest)
    return total


def num_inconsistent_scripts(scriptdata):
    """
    Count the number of times two adjacent letters are in different scripts,
    or are both marked as 'weird'.

    Uses a "scriptdata" string as input, not the actual text.

    >>> num_inconsistent_scripts('LL AAA.')
    0
    >>> num_inconsistent_scripts('LLAAA ...')
    1
    >>> num_inconsistent_scripts('LAL')
    2
    >>> num_inconsistent_scripts('..LLL..')
    0
    >>> num_inconsistent_scripts('LWWW')
    3
    """
    # First, count the number of times two letters are adjacent
    letter_segments = LETTER_SEGMENTS_RE.findall(scriptdata)
    adjacent_letters = 0
    for seg in letter_segments:
        adjacent_letters += len(seg) - 1

    # Then subtract out the number of times the scripts are consistent,
    # but first add back in adjacent weird characters
    double_weird_segments = DOUBLE_WEIRD_RE.findall(scriptdata)
    for seg in double_weird_segments:
        adjacent_letters += len(seg) - 1

    return adjacent_letters - num_consistent_scripts(scriptdata)


def script_obscurity(scriptdata):
    """
    Count the number of characters in obscure scripts. Characters in very
    obscure scripts count twice as much.

    >>> script_obscurity('LWWW')
    0
    >>> script_obscurity('Llkzz')
    6
    """
    return len(LOWERCASE_RE.findall(scriptdata)) + scriptdata.count('z')


def character_weirdness(text):
    """
    Sum the weirdness of all the single-byte characters in this text.

    >>> character_weirdness('test')
    0
    >>> character_weirdness('wúút')
    0
    >>> character_weirdness('\x81\x81')
    10
    """
    total = 0
    for weird_re in WEIRD_CHARACTER_RES:
        found = weird_re.findall(text)
        total += len(found)
    return total


def text_badness(text):
    """
    Count the total badness of a string, which helps to determine when an
    encoding has gone wrong.

    Obvious problems (badness = 100):
    - The replacement character \ufffd, indicating a decoding error
    - Unassigned or private-use Unicode characters

    Very weird things (badness = 10):
    - Adjacent letters from two different scripts
    - Letters adjacent to obscure single-byte symbols
    - Obscure single-byte symbols adjacent to each other
    - Improbable control characters, such as 0x81

    Moderately weird things:
    - Improbable single-byte characters, such as ƒ or ¬
    - Letters in somewhat rare scripts (they'll still probably look better than
      they would in the wrong encoding)
    """
    scriptdata = text.translate(SCRIPT_MAP)
    badness = character_weirdness(text) + script_obscurity(scriptdata)
    badness += 10 * num_inconsistent_scripts(scriptdata)
    badness += 100 * scriptdata.count('?')
    return badness

########NEW FILE########
__FILENAME__ = chardata
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unicodedata
import sys
if sys.hexversion >= 0x03000000:
    unichr = chr

# Start with an inventory of "gremlins", which are characters from all over
# Unicode that Windows has instead assigned to the control characters
# 0x80-0x9F. We might encounter them in their Unicode forms and have to figure
# out what they were originally.

WINDOWS_1252_GREMLINS = [
    # adapted from http://effbot.org/zone/unicode-gremlins.htm
    0x0152,  # LATIN CAPITAL LIGATURE OE
    0x0153,  # LATIN SMALL LIGATURE OE
    0x0160,  # LATIN CAPITAL LETTER S WITH CARON
    0x0161,  # LATIN SMALL LETTER S WITH CARON
    0x0178,  # LATIN CAPITAL LETTER Y WITH DIAERESIS
    0x017E,  # LATIN SMALL LETTER Z WITH CARON
    0x017D,  # LATIN CAPITAL LETTER Z WITH CARON
    0x0192,  # LATIN SMALL LETTER F WITH HOOK
    0x02C6,  # MODIFIER LETTER CIRCUMFLEX ACCENT
    0x02DC,  # SMALL TILDE
    0x2013,  # EN DASH
    0x2014,  # EM DASH
    0x201A,  # SINGLE LOW-9 QUOTATION MARK
    0x201C,  # LEFT DOUBLE QUOTATION MARK
    0x201D,  # RIGHT DOUBLE QUOTATION MARK
    0x201E,  # DOUBLE LOW-9 QUOTATION MARK
    0x2018,  # LEFT SINGLE QUOTATION MARK
    0x2019,  # RIGHT SINGLE QUOTATION MARK
    0x2020,  # DAGGER
    0x2021,  # DOUBLE DAGGER
    0x2022,  # BULLET
    0x2026,  # HORIZONTAL ELLIPSIS
    0x2030,  # PER MILLE SIGN
    0x2039,  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    0x203A,  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    0x20AC,  # EURO SIGN
    0x2122,  # TRADE MARK SIGN
]

# a list of Unicode characters that might appear in Windows-1252 text
WINDOWS_1252_CODEPOINTS = list(range(256)) + WINDOWS_1252_GREMLINS

# Rank the characters typically represented by a single byte -- that is, in
# Latin-1 or Windows-1252 -- by how weird it would be to see them in running
# text.
#
#   0 = not weird at all
#   1 = rare punctuation or rare letter that someone could certainly
#       have a good reason to use. All Windows-1252 gremlins are at least
#       weirdness 1.
#   2 = things that probably don't appear next to letters or other
#       symbols, such as math or currency symbols
#   3 = obscure symbols that nobody would go out of their way to use
#       (includes symbols that were replaced in ISO-8859-15)
#   4 = why would you use this?
#   5 = unprintable control character
#
# The Portuguese letter Ã (0xc3) is marked as weird because it would usually
# appear in the middle of a word in actual Portuguese, and meanwhile it
# appears in the mis-encodings of many common characters.

SINGLE_BYTE_WEIRDNESS = (
#   0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
    5, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0, 5, 5, 5, 5, 5,  # 0x00
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,  # 0x10
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x20
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x30
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x40
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x50
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0x60
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5,  # 0x70
    2, 5, 1, 4, 1, 1, 3, 3, 4, 3, 1, 1, 1, 5, 1, 5,  # 0x80
    5, 1, 1, 1, 1, 3, 1, 1, 4, 1, 1, 1, 1, 5, 1, 1,  # 0x90
    1, 0, 2, 2, 3, 2, 4, 2, 4, 2, 2, 0, 3, 1, 1, 4,  # 0xa0
    2, 2, 3, 3, 4, 3, 3, 2, 4, 4, 4, 0, 3, 3, 3, 0,  # 0xb0
    0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xc0
    1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xd0
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xe0
    1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0,  # 0xf0
)

# Pre-cache the Unicode data saying which of these first 256 characters are
# letters. We'll need it often.
SINGLE_BYTE_LETTERS = [
    unicodedata.category(unichr(i)).startswith('L')
    for i in range(256)
]

# Create a fast mapping that converts a Unicode string to a string describing
# its character classes, particularly the scripts its letters are in.
#
# Capital letters represent groups of commonly-used scripts:
#   L = Latin
#   E = several East Asian scripts including hanzi, kana, and Hangul
#   C = Cyrillic
#   etc.
#
# Lowercase letters represent rare scripts.
# . represents non-letters.
# Whitespace represents whitespace.
# ? represents errors.
#
# Astral characters pass through unmodified; we don't count them as script
# conflicts. They are probably intentional.

SCRIPT_LETTERS = {
    'LATIN': 'L',
    'CJK': 'E',
    'ARABIC': 'A',
    'CYRILLIC': 'C',
    'GREEK': 'G',
    'HEBREW': 'H',
    'KATAKANA': 'E',
    'HIRAGANA': 'E',
    'HIRAGANA-KATAKANA': 'E',
    'HANGUL': 'E',
    'DEVANAGARI': 'D',
    'THAI': 'T',
    'FULLWIDTH': 'E',
    'MASCULINE': 'L',
    'FEMININE': 'L',
    'MODIFIER': '.',
    'HALFWIDTH': 'E',
    'BENGALI': 'b',
    'LAO': 'l',
    'KHMER': 'k',
    'TELUGU': 't',
    'MALAYALAM': 'm',
    'SINHALA': 's',
    'TAMIL': 'a',
    'GEORGIAN': 'g',
    'ARMENIAN': 'r',
    'KANNADA': 'n',  # mostly used for looks of disapproval
}


SCRIPT_MAP = {}

for codepoint in range(0x10000):
    char = unichr(codepoint)
    if unicodedata.category(char).startswith('L'):
        try:
            name = unicodedata.name(char)
            script = name.split()[0]
            if script in SCRIPT_LETTERS:
                SCRIPT_MAP[codepoint] = SCRIPT_LETTERS[script]
            else:
                SCRIPT_MAP[codepoint] = 'z'
        except ValueError:
            # it's unfortunate that this gives subtly different results
            # on Python 2.6, which is confused about the Unicode 5.1
            # Chinese range. It knows they're letters but it has no idea
            # what they are named.
            #
            # This could be something to fix in the future, or maybe we
            # just stop supporting Python 2.6 eventually.
            SCRIPT_MAP[codepoint] = 'z'
    elif unicodedata.category(char).startswith('Z'):
        SCRIPT_MAP[codepoint] = ' '
    elif unicodedata.category(char) in ('Cn', 'Co'):
        SCRIPT_MAP[codepoint] = '?'
    else:
        SCRIPT_MAP[codepoint] = '.'

SCRIPT_MAP[0x09] = ' '
SCRIPT_MAP[0x0a] = '\n'
SCRIPT_MAP[0xfffd] = '?'

# mark weird extended characters as their own script
for codepoint in range(0x100):
    if SINGLE_BYTE_WEIRDNESS[codepoint] >= 2:
        SCRIPT_MAP[codepoint] = 'W'

# A translate mapping that will strip all control characters except \t and \n.
# This incidentally has the effect of normalizing Windows \r\n line endings to
# Unix \n line endings.
CONTROL_CHARS = {}
for i in range(256):
    if unicodedata.category(unichr(i)) == 'Cc':
        CONTROL_CHARS[i] = None

CONTROL_CHARS[ord('\t')] = '\t'
CONTROL_CHARS[ord('\n')] = '\n'

########NEW FILE########
__FILENAME__ = cli
from ftfy import fix_file
import codecs

import sys
ENCODE_STDOUT = (sys.hexversion < 0x03000000)


def main():
    """
    Run ftfy as a command-line utility. (Requires Python 2.7 or later, or
    the 'argparse' module.)
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', help='file to transcode')

    args = parser.parse_args()

    # Why open in Latin-1? Because it at least won't make encoding problems
    # worse, and we're about to make things better.
    file = codecs.open(args.filename, encoding='latin-1')
    for line in fix_file(file):
        if ENCODE_STDOUT:
            sys.stdout.write(line.encode('utf-8'))
        else:
            sys.stdout.write(line)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_unicode
# -*- coding: utf-8 -*-
from ftfy import fix_bad_encoding, WINDOWS_1252_GREMLINS
import unicodedata

# Most single-character strings which have been misencoded should be restored.
def test_all_bmp_characters():
    for index in xrange(0xa0, 0xfffd):
        char = unichr(index)
        # Exclude code points that are not assigned
        if unicodedata.category(char) not in ('Co', 'Cn'):
            garble = char.encode('utf-8').decode('latin-1')
            assert fix_bad_encoding(garble) == char

phrases = [
    u"\u201CI'm not such a fan of Charlotte Brontë\u2026\u201D",
    u"\u201CI'm not such a fan of Charlotte Brontë\u2026\u201D",
    u"\u2039ALLÍ ESTÁ\u203A",
    u"\u2014ALLÍ ESTÁ\u2014",
    u"AHÅ™, the new sofa from IKEA®",
    #u"\u2014a radius of 10 Å\u2014",
]
# These phrases should not be erroneously "fixed"
def test_valid_phrases():
    for phrase in phrases:
        print phrase
        yield check_phrase, phrase
        # make it not just confirm based on the opening punctuation
        yield check_phrase, phrase[1:]

def check_phrase(text):
    assert fix_bad_encoding(text) == text, text


########NEW FILE########
__FILENAME__ = killableprocess
# killableprocess - subprocesses which can be reliably killed
#
# Parts of this module are copied from the subprocess.py file contained
# in the Python distribution.
#
# Copyright (c) 2003-2004 by Peter Astrand <astrand@lysator.liu.se>
#
# Additions and modifications written by Benjamin Smedberg
# <benjamin@smedbergs.us> are Copyright (c) 2006 by the Mozilla Foundation
# <http://www.mozilla.org/>
#
# More Modifications
# Copyright (c) 2006-2007 by Mike Taylor <bear@code-bear.com>
# Copyright (c) 2007-2008 by Mikeal Rogers <mikeal@mozilla.com>
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of the
# author not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""killableprocess - Subprocesses which can be reliably killed

This module is a subclass of the builtin "subprocess" module. It allows
processes that launch subprocesses to be reliably killed on Windows (via the Popen.kill() method.

It also adds a timeout argument to Wait() for a limited period of time before
forcefully killing the process.

Note: On Windows, this module requires Windows 2000 or higher (no support for
Windows 95, 98, or NT 4.0). It also requires ctypes, which is bundled with
Python 2.5+ or available from http://python.net/crew/theller/ctypes/
"""

import subprocess
import sys
import os
import time
import datetime
import types

try:
    from subprocess import CalledProcessError
except ImportError:
    # Python 2.4 doesn't implement CalledProcessError
    class CalledProcessError(Exception):
        """This exception is raised when a process run by check_call() returns
        a non-zero exit status. The exit status will be stored in the
        returncode attribute."""
        def __init__(self, returncode, cmd):
            self.returncode = returncode
            self.cmd = cmd
        def __str__(self):
            return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)

mswindows = (sys.platform == "win32")
py2 = (sys.version_info[0] == 2)

if mswindows:
    from . import winprocess
else:
    import signal

def call(*args, **kwargs):
    waitargs = {}
    if "timeout" in kwargs:
        waitargs["timeout"] = kwargs.pop("timeout")

    return Popen(*args, **kwargs).wait(**waitargs)

def check_call(*args, **kwargs):
    """Call a program with an optional timeout. If the program has a non-zero
    exit status, raises a CalledProcessError."""

    retcode = call(*args, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = args[0]
        raise CalledProcessError(retcode, cmd)

if not mswindows:
    def DoNothing(*args):
        pass

class Popen(subprocess.Popen):
    kill_called = False
    if mswindows:
        if py2:
            def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines, startupinfo,
                           creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
                return self._execute_child_compat(args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines, startupinfo,
                           creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite)
        else:
            def _execute_child(self, args, executable, preexec_fn, close_fds,
                               pass_fds,
                               cwd, env,
                               startupinfo,
                               creationflags, shell,
                               p2cread, p2cwrite,
                               c2pread, c2pwrite,
                               errread, errwrite,
                               unused_restore_signals, unused_start_new_session):
                return self._execute_child_compat(args, executable, preexec_fn, close_fds,
                           cwd, env, True, startupinfo,
                           creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite)


    if mswindows:
        def _execute_child_compat(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines, startupinfo,
                           creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            if not isinstance(args, str):
                args = subprocess.list2cmdline(args)

            # Always or in the create new process group
            creationflags |= winprocess.CREATE_NEW_PROCESS_GROUP

            if startupinfo is None:
                startupinfo = winprocess.STARTUPINFO()

            if None not in (p2cread, c2pwrite, errwrite):
                startupinfo.dwFlags |= winprocess.STARTF_USESTDHANDLES

                startupinfo.hStdInput = int(p2cread)
                startupinfo.hStdOutput = int(c2pwrite)
                startupinfo.hStdError = int(errwrite)
            if shell:
                startupinfo.dwFlags |= winprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = winprocess.SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = comspec + " /c " + args

            # determine if we can create create a job
            canCreateJob = winprocess.CanCreateJobObject()

            # set process creation flags
            creationflags |= winprocess.CREATE_SUSPENDED
            creationflags |= winprocess.CREATE_UNICODE_ENVIRONMENT
            if canCreateJob:
                creationflags |= winprocess.CREATE_BREAKAWAY_FROM_JOB

            # create the process
            hp, ht, pid, tid = winprocess.CreateProcess(
                executable, args,
                None, None, # No special security
                1, # Must inherit handles!
                creationflags,
                winprocess.EnvironmentBlock(env),
                cwd, startupinfo)
            self._child_created = True
            self._handle = int(hp)
            self._thread = ht
            self.pid = pid
            self.tid = tid
            
            if canCreateJob:
                # We create a new job for this process, so that we can kill
                # the process and any sub-processes
                self._job = winprocess.CreateJobObject()
                winprocess.AssignProcessToJobObject(self._job, int(hp))
            else:
                self._job = None

            winprocess.ResumeThread(int(ht))
            ht.Close()

            if p2cread is not None and p2cread != -1:
                p2cread.Close()
            if c2pwrite is not None and c2pwrite != -1:
                c2pwrite.Close()
            if errwrite is not None and errwrite != -1:
                errwrite.Close()
            time.sleep(.1)

    def kill(self, group=True):
        """Kill the process. If group=True, all sub-processes will also be killed."""
        self.kill_called = True
        if mswindows:
            if group and self._job:
                winprocess.TerminateJobObject(self._job, 127)
            else:
                try:
                    winprocess.TerminateProcess(self._handle, 127)
                except:
                    # TODO: better error handling here
                    pass
            self.returncode = 127
        else:
            if group:
                try:
                    os.killpg(self.pid, signal.SIGKILL)
                except: pass
            else:
                os.kill(self.pid, signal.SIGKILL)
            super(Popen, self).kill()
            self.returncode = -9

    def wait(self, timeout=None, group=True):
        """Wait for the process to terminate. Returns returncode attribute.
        If timeout seconds are reached and the process has not terminated,
        it will be forcefully killed. If timeout is -1, wait will not
        time out."""

        if timeout is not None:
            # timeout is now in milliseconds
            timeout = timeout * 1000

        if self.returncode is not None:
            return self.returncode

        starttime = datetime.datetime.now()

        if mswindows:
            if timeout is None:
                timeout = -1
            rc = winprocess.WaitForSingleObject(self._handle, timeout)

            if rc != winprocess.WAIT_TIMEOUT:
                def check():
                    now = datetime.datetime.now()
                    diff = now - starttime
                    if (diff.seconds * 1000 * 1000 + diff.microseconds) < (timeout * 1000):
                        if self._job:
                            if (winprocess.QueryInformationJobObject(self._job, 8)['BasicInfo']['ActiveProcesses'] > 0):
                                return True
                        else:
                            return True
                    return False
                while check():
                    time.sleep(.5)

            now = datetime.datetime.now()
            diff = now - starttime
            if (diff.seconds * 1000 * 1000 + diff.microseconds) > (timeout * 1000):
                self.kill(group)
            else:
                self.returncode = winprocess.GetExitCodeProcess(self._handle)
        else:
            if (sys.platform == 'linux2') or (sys.platform in ('sunos5', 'solaris')):
                def group_wait(timeout):
                    try:
                        os.waitpid(self.pid, 0)
                    except OSError as e:
                        pass # If wait has already been called on this pid, bad things happen
                    return self.returncode
            elif sys.platform == 'darwin':
                def group_wait(timeout):
                    try:
                        count = 0
                        if timeout is None and self.kill_called:
                            timeout = 10 # Have to set some kind of timeout or else this could go on forever
                        if timeout is None:
                            while 1:
                                os.killpg(self.pid, signal.SIG_DFL)
                        while ((count * 2) <= timeout):
                            os.killpg(self.pid, signal.SIG_DFL)
                            # count is increased by 500ms for every 0.5s of sleep
                            time.sleep(.5); count += 500
                    except OSError:
                        return self.returncode

            if timeout is None:
                if group is True:
                    return group_wait(timeout)
                else:
                    subprocess.Popen.wait(self)
                    return self.returncode

            returncode = False

            now = datetime.datetime.now()
            diff = now - starttime
            while (diff.seconds * 1000 * 1000 + diff.microseconds) < (timeout * 1000) and ( returncode is False ):
                if group is True:
                    return group_wait(timeout)
                else:
                    if subprocess.poll() is not None:
                        returncode = self.returncode
                time.sleep(.5)
                now = datetime.datetime.now()
                diff = now - starttime
            return self.returncode

        return self.returncode
    # We get random maxint errors from subprocesses __del__
    __del__ = lambda self: None

def setpgid_preexec_fn():
    os.setpgid(0, 0)

def runCommand(cmd, **kwargs):
    if sys.platform != "win32":
        return Popen(cmd, preexec_fn=setpgid_preexec_fn, **kwargs)
    else:
        return Popen(cmd, **kwargs)

########NEW FILE########
__FILENAME__ = qijo
from ctypes import c_void_p, POINTER, sizeof, Structure, windll, WinError, WINFUNCTYPE, addressof, c_size_t, c_ulong
from ctypes.wintypes import BOOL, BYTE, DWORD, HANDLE, LARGE_INTEGER

LPVOID = c_void_p
LPDWORD = POINTER(DWORD)
SIZE_T = c_size_t
ULONG_PTR = POINTER(c_ulong)

# A ULONGLONG is a 64-bit unsigned integer.
# Thus there are 8 bytes in a ULONGLONG.
# XXX why not import c_ulonglong ?
ULONGLONG = BYTE * 8

class IO_COUNTERS(Structure):
    # The IO_COUNTERS struct is 6 ULONGLONGs.
    # TODO: Replace with non-dummy fields.
    _fields_ = [('dummy', ULONGLONG * 6)]

class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(Structure):
    _fields_ = [('TotalUserTime', LARGE_INTEGER),
                ('TotalKernelTime', LARGE_INTEGER),
                ('ThisPeriodTotalUserTime', LARGE_INTEGER),
                ('ThisPeriodTotalKernelTime', LARGE_INTEGER),
                ('TotalPageFaultCount', DWORD),
                ('TotalProcesses', DWORD),
                ('ActiveProcesses', DWORD),
                ('TotalTerminatedProcesses', DWORD)]

class JOBOBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION(Structure):
    _fields_ = [('BasicInfo', JOBOBJECT_BASIC_ACCOUNTING_INFORMATION),
                ('IoInfo', IO_COUNTERS)]

# see http://msdn.microsoft.com/en-us/library/ms684147%28VS.85%29.aspx
class JOBOBJECT_BASIC_LIMIT_INFORMATION(Structure):
    _fields_ = [('PerProcessUserTimeLimit', LARGE_INTEGER),
                ('PerJobUserTimeLimit', LARGE_INTEGER),
                ('LimitFlags', DWORD),
                ('MinimumWorkingSetSize', SIZE_T),
                ('MaximumWorkingSetSize', SIZE_T),
                ('ActiveProcessLimit', DWORD),
                ('Affinity', ULONG_PTR),
                ('PriorityClass', DWORD),
                ('SchedulingClass', DWORD)
                ]

# see http://msdn.microsoft.com/en-us/library/ms684156%28VS.85%29.aspx
class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(Structure):
    _fields_ = [('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', SIZE_T),
                ('JobMemoryLimit', SIZE_T),
                ('PeakProcessMemoryUsed', SIZE_T),
                ('PeakJobMemoryUsed', SIZE_T)]

# XXX Magical numbers like 8 should be documented
JobObjectBasicAndIoAccountingInformation = 8

# ...like magical number 9 comes from
# http://community.flexerasoftware.com/archive/index.php?t-181670.html
# I wish I had a more canonical source
JobObjectExtendedLimitInformation = 9

class JobObjectInfo(object):
    mapping = { 'JobObjectBasicAndIoAccountingInformation': 8,
                'JobObjectExtendedLimitInformation': 9
                }
    structures = { 8: JOBOBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION,
                   9: JOBOBJECT_EXTENDED_LIMIT_INFORMATION
                   }
    def __init__(self, _class):
        if isinstance(_class, str):
            assert _class in self.mapping, 'Class should be one of %s; you gave %s' % (self.mapping, _class)
            _class = self.mapping[_class]
        assert _class in self.structures, 'Class should be one of %s; you gave %s' % (self.structures, _class)
        self.code = _class
        self.info = self.structures[_class]()
    

QueryInformationJobObjectProto = WINFUNCTYPE(
    BOOL,        # Return type
    HANDLE,      # hJob
    DWORD,       # JobObjectInfoClass
    LPVOID,      # lpJobObjectInfo
    DWORD,       # cbJobObjectInfoLength
    LPDWORD      # lpReturnLength
    )

QueryInformationJobObjectFlags = (
    (1, 'hJob'),
    (1, 'JobObjectInfoClass'),
    (1, 'lpJobObjectInfo'),
    (1, 'cbJobObjectInfoLength'),
    (1, 'lpReturnLength', None)
    )

_QueryInformationJobObject = QueryInformationJobObjectProto(
    ('QueryInformationJobObject', windll.kernel32),
    QueryInformationJobObjectFlags
    )

class SubscriptableReadOnlyStruct(object):
    def __init__(self, struct):
        self._struct = struct

    def _delegate(self, name):
        result = getattr(self._struct, name)
        if isinstance(result, Structure):
            return SubscriptableReadOnlyStruct(result)
        return result

    def __getitem__(self, name):
        match = [fname for fname, ftype in self._struct._fields_
                 if fname == name]
        if match:
            return self._delegate(name)
        raise KeyError(name)

    def __getattr__(self, name):
        return self._delegate(name)

def QueryInformationJobObject(hJob, JobObjectInfoClass):
    jobinfo = JobObjectInfo(JobObjectInfoClass)
    result = _QueryInformationJobObject(
        hJob=hJob,
        JobObjectInfoClass=jobinfo.code,
        lpJobObjectInfo=addressof(jobinfo.info),
        cbJobObjectInfoLength=sizeof(jobinfo.info)
        )
    if not result:
        raise WinError()
    return SubscriptableReadOnlyStruct(jobinfo.info)

def test_qijo():
    from .killableprocess import Popen

    popen = Popen('c:\\windows\\notepad.exe')

    try:
        result = QueryInformationJobObject(0, 8)
        raise AssertionError('throw should occur')
    except WindowsError as e:
        pass

    try:
        result = QueryInformationJobObject(0, 1)
        raise AssertionError('throw should occur')
    except NotImplementedError as e:
        pass

    result = QueryInformationJobObject(popen._job, 8)
    if result['BasicInfo']['ActiveProcesses'] != 1:
        raise AssertionError('expected ActiveProcesses to be 1')
    popen.kill()

    result = QueryInformationJobObject(popen._job, 8)
    if result.BasicInfo.ActiveProcesses != 0:
        raise AssertionError('expected ActiveProcesses to be 0')

########NEW FILE########
__FILENAME__ = winprocess
# A module to expose various thread/process/job related structures and
# methods from kernel32
#
# The MIT License
#
# Copyright (c) 2003-2004 by Peter Astrand <astrand@lysator.liu.se>
#
# Additions and modifications written by Benjamin Smedberg
# <benjamin@smedbergs.us> are Copyright (c) 2006 by the Mozilla Foundation
# <http://www.mozilla.org/>
#
# More Modifications
# Copyright (c) 2006-2007 by Mike Taylor <bear@code-bear.com>
# Copyright (c) 2007-2008 by Mikeal Rogers <mikeal@mozilla.com>
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of the
# author not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from ctypes import c_void_p, POINTER, sizeof, Structure, windll, WinError, WINFUNCTYPE
from ctypes.wintypes import BOOL, BYTE, DWORD, HANDLE, LPCWSTR, LPWSTR, UINT, WORD
from .qijo import QueryInformationJobObject

LPVOID = c_void_p
LPBYTE = POINTER(BYTE)
LPDWORD = POINTER(DWORD)
LPBOOL = POINTER(BOOL)

def ErrCheckBool(result, func, args):
    """errcheck function for Windows functions that return a BOOL True
    on success"""
    if not result:
        raise WinError()
    return args


# AutoHANDLE

class AutoHANDLE(HANDLE):
    """Subclass of HANDLE which will call CloseHandle() on deletion."""
    
    CloseHandleProto = WINFUNCTYPE(BOOL, HANDLE)
    CloseHandle = CloseHandleProto(("CloseHandle", windll.kernel32))
    CloseHandle.errcheck = ErrCheckBool
    
    def Close(self):
        if self.value and self.value != HANDLE(-1).value:
            self.CloseHandle(self)
            self.value = 0
    
    def __del__(self):
        self.Close()

    def __int__(self):
        return self.value

def ErrCheckHandle(result, func, args):
    """errcheck function for Windows functions that return a HANDLE."""
    if not result:
        raise WinError()
    return AutoHANDLE(result)

# PROCESS_INFORMATION structure

class PROCESS_INFORMATION(Structure):
    _fields_ = [("hProcess", HANDLE),
                ("hThread", HANDLE),
                ("dwProcessID", DWORD),
                ("dwThreadID", DWORD)]

    def __init__(self):
        Structure.__init__(self)
        
        self.cb = sizeof(self)

LPPROCESS_INFORMATION = POINTER(PROCESS_INFORMATION)

# STARTUPINFO structure

class STARTUPINFO(Structure):
    _fields_ = [("cb", DWORD),
                ("lpReserved", LPWSTR),
                ("lpDesktop", LPWSTR),
                ("lpTitle", LPWSTR),
                ("dwX", DWORD),
                ("dwY", DWORD),
                ("dwXSize", DWORD),
                ("dwYSize", DWORD),
                ("dwXCountChars", DWORD),
                ("dwYCountChars", DWORD),
                ("dwFillAttribute", DWORD),
                ("dwFlags", DWORD),
                ("wShowWindow", WORD),
                ("cbReserved2", WORD),
                ("lpReserved2", LPBYTE),
                ("hStdInput", HANDLE),
                ("hStdOutput", HANDLE),
                ("hStdError", HANDLE)
                ]
LPSTARTUPINFO = POINTER(STARTUPINFO)

SW_HIDE                 = 0

STARTF_USESHOWWINDOW    = 0x01
STARTF_USESIZE          = 0x02
STARTF_USEPOSITION      = 0x04
STARTF_USECOUNTCHARS    = 0x08
STARTF_USEFILLATTRIBUTE = 0x10
STARTF_RUNFULLSCREEN    = 0x20
STARTF_FORCEONFEEDBACK  = 0x40
STARTF_FORCEOFFFEEDBACK = 0x80
STARTF_USESTDHANDLES    = 0x100

# EnvironmentBlock

class EnvironmentBlock:
    """An object which can be passed as the lpEnv parameter of CreateProcess.
    It is initialized with a dictionary."""

    def __init__(self, dict):
        if not dict:
            self._as_parameter_ = None
        else:
            values = ["%s=%s" % (key, value)
                      for (key, value) in dict.items()]
            values.append("")
            self._as_parameter_ = LPCWSTR("\0".join(values))
        
# CreateProcess()

CreateProcessProto = WINFUNCTYPE(BOOL,                  # Return type
                                 LPCWSTR,               # lpApplicationName
                                 LPWSTR,                # lpCommandLine
                                 LPVOID,                # lpProcessAttributes
                                 LPVOID,                # lpThreadAttributes
                                 BOOL,                  # bInheritHandles
                                 DWORD,                 # dwCreationFlags
                                 LPVOID,                # lpEnvironment
                                 LPCWSTR,               # lpCurrentDirectory
                                 LPSTARTUPINFO,         # lpStartupInfo
                                 LPPROCESS_INFORMATION  # lpProcessInformation
                                 )

CreateProcessFlags = ((1, "lpApplicationName", None),
                      (1, "lpCommandLine"),
                      (1, "lpProcessAttributes", None),
                      (1, "lpThreadAttributes", None),
                      (1, "bInheritHandles", True),
                      (1, "dwCreationFlags", 0),
                      (1, "lpEnvironment", None),
                      (1, "lpCurrentDirectory", None),
                      (1, "lpStartupInfo"),
                      (2, "lpProcessInformation"))

def ErrCheckCreateProcess(result, func, args):
    ErrCheckBool(result, func, args)
    # return a tuple (hProcess, hThread, dwProcessID, dwThreadID)
    pi = args[9]
    return AutoHANDLE(pi.hProcess), AutoHANDLE(pi.hThread), pi.dwProcessID, pi.dwThreadID

CreateProcess = CreateProcessProto(("CreateProcessW", windll.kernel32),
                                   CreateProcessFlags)
CreateProcess.errcheck = ErrCheckCreateProcess

# flags for CreateProcess
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_DEFAULT_ERROR_MODE = 0x04000000
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400

# flags for job limit information
# see http://msdn.microsoft.com/en-us/library/ms684147%28VS.85%29.aspx
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000

# XXX these flags should be documented
DEBUG_ONLY_THIS_PROCESS = 0x00000002
DEBUG_PROCESS = 0x00000001
DETACHED_PROCESS = 0x00000008

# CreateJobObject()

CreateJobObjectProto = WINFUNCTYPE(HANDLE,             # Return type
                                   LPVOID,             # lpJobAttributes
                                   LPCWSTR             # lpName
                                   )

CreateJobObjectFlags = ((1, "lpJobAttributes", None),
                        (1, "lpName", None))

CreateJobObject = CreateJobObjectProto(("CreateJobObjectW", windll.kernel32),
                                       CreateJobObjectFlags)
CreateJobObject.errcheck = ErrCheckHandle

# AssignProcessToJobObject()

AssignProcessToJobObjectProto = WINFUNCTYPE(BOOL,      # Return type
                                            HANDLE,    # hJob
                                            HANDLE     # hProcess
                                            )
AssignProcessToJobObjectFlags = ((1, "hJob"),
                                 (1, "hProcess"))
AssignProcessToJobObject = AssignProcessToJobObjectProto(
    ("AssignProcessToJobObject", windll.kernel32),
    AssignProcessToJobObjectFlags)
AssignProcessToJobObject.errcheck = ErrCheckBool

# GetCurrentProcess()
# because os.getPid() is way too easy
GetCurrentProcessProto = WINFUNCTYPE(HANDLE    # Return type
                                     )
GetCurrentProcessFlags = ()
GetCurrentProcess = GetCurrentProcessProto(
    ("GetCurrentProcess", windll.kernel32),
    GetCurrentProcessFlags)
GetCurrentProcess.errcheck = ErrCheckHandle

# IsProcessInJob()
try:
    IsProcessInJobProto = WINFUNCTYPE(BOOL,     # Return type
                                      HANDLE,   # Process Handle
                                      HANDLE,   # Job Handle
                                      LPBOOL      # Result
                                      )
    IsProcessInJobFlags = ((1, "ProcessHandle"),
                           (1, "JobHandle", HANDLE(0)),
                           (2, "Result"))
    IsProcessInJob = IsProcessInJobProto(
        ("IsProcessInJob", windll.kernel32),
        IsProcessInJobFlags)
    IsProcessInJob.errcheck = ErrCheckBool 
except AttributeError:
    # windows 2k doesn't have this API
    def IsProcessInJob(process):
        return False


# ResumeThread()

def ErrCheckResumeThread(result, func, args):
    if result == -1:
        raise WinError()

    return args

ResumeThreadProto = WINFUNCTYPE(DWORD,      # Return type
                                HANDLE      # hThread
                                )
ResumeThreadFlags = ((1, "hThread"),)
ResumeThread = ResumeThreadProto(("ResumeThread", windll.kernel32),
                                 ResumeThreadFlags)
ResumeThread.errcheck = ErrCheckResumeThread

# TerminateProcess()

TerminateProcessProto = WINFUNCTYPE(BOOL,   # Return type
                                    HANDLE, # hProcess
                                    UINT    # uExitCode
                                    )
TerminateProcessFlags = ((1, "hProcess"),
                         (1, "uExitCode", 127))
TerminateProcess = TerminateProcessProto(
    ("TerminateProcess", windll.kernel32),
    TerminateProcessFlags)
TerminateProcess.errcheck = ErrCheckBool

# TerminateJobObject()

TerminateJobObjectProto = WINFUNCTYPE(BOOL,   # Return type
                                      HANDLE, # hJob
                                      UINT    # uExitCode
                                      )
TerminateJobObjectFlags = ((1, "hJob"),
                           (1, "uExitCode", 127))
TerminateJobObject = TerminateJobObjectProto(
    ("TerminateJobObject", windll.kernel32),
    TerminateJobObjectFlags)
TerminateJobObject.errcheck = ErrCheckBool

# WaitForSingleObject()

WaitForSingleObjectProto = WINFUNCTYPE(DWORD,  # Return type
                                       HANDLE, # hHandle
                                       DWORD,  # dwMilliseconds
                                       )
WaitForSingleObjectFlags = ((1, "hHandle"),
                            (1, "dwMilliseconds", -1))
WaitForSingleObject = WaitForSingleObjectProto(
    ("WaitForSingleObject", windll.kernel32),
    WaitForSingleObjectFlags)

INFINITE = -1
WAIT_TIMEOUT = 0x0102
WAIT_OBJECT_0 = 0x0
WAIT_ABANDONED = 0x0080

# GetExitCodeProcess()

GetExitCodeProcessProto = WINFUNCTYPE(BOOL,    # Return type
                                      HANDLE,  # hProcess
                                      LPDWORD, # lpExitCode
                                      )
GetExitCodeProcessFlags = ((1, "hProcess"),
                           (2, "lpExitCode"))
GetExitCodeProcess = GetExitCodeProcessProto(
    ("GetExitCodeProcess", windll.kernel32),
    GetExitCodeProcessFlags)
GetExitCodeProcess.errcheck = ErrCheckBool

def CanCreateJobObject():
    currentProc = GetCurrentProcess()
    if IsProcessInJob(currentProc):
        jobinfo = QueryInformationJobObject(HANDLE(0), 'JobObjectExtendedLimitInformation')
        limitflags = jobinfo['BasicLimitInformation']['LimitFlags']
        return bool(limitflags & JOB_OBJECT_LIMIT_BREAKAWAY_OK) or bool(limitflags & JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK)
    else:
        return True

### testing functions

def parent():
    print('Starting parent')
    currentProc = GetCurrentProcess()
    if IsProcessInJob(currentProc):
        print("You should not be in a job object to test")
        sys.exit(1)
    assert CanCreateJobObject()
    print('File: %s' % __file__)
    command = [sys.executable, __file__, '-child']
    print('Running command: %s' % command)
    process = Popen(command)
    process.kill()
    code = process.returncode
    print('Child code: %s' % code)
    assert code == 127
        
def child():
    print('Starting child')
    currentProc = GetCurrentProcess()
    injob = IsProcessInJob(currentProc)
    print("Is in a job?: %s" % injob)
    can_create = CanCreateJobObject()
    print('Can create job?: %s' % can_create)
    process = Popen('c:\\windows\\notepad.exe')
    assert process._job
    jobinfo = QueryInformationJobObject(process._job, 'JobObjectExtendedLimitInformation')
    print('Job info: %s' % jobinfo)
    limitflags = jobinfo['BasicLimitInformation']['LimitFlags']
    print('LimitFlags: %s' % limitflags)
    process.kill()

########NEW FILE########
__FILENAME__ = pexpect
"""Pexpect is a Python module for spawning child applications and controlling
them automatically. Pexpect can be used for automating interactive applications
such as ssh, ftp, passwd, telnet, etc. It can be used to a automate setup
scripts for duplicating software package installations on different servers. It
can be used for automated software testing. Pexpect is in the spirit of Don
Libes' Expect, but Pexpect is pure Python. Other Expect-like modules for Python
require TCL and Expect or require C extensions to be compiled. Pexpect does not
use C, Expect, or TCL extensions. It should work on any platform that supports
the standard Python pty module. The Pexpect interface focuses on ease of use so
that simple tasks are easy.

There are two main interfaces to the Pexpect system; these are the function,
run() and the class, spawn. The spawn class is more powerful. The run()
function is simpler than spawn, and is good for quickly calling program. When
you call the run() function it executes a given program and then returns the
output. This is a handy replacement for os.system().

For example::

    pexpect.run('ls -la')

The spawn class is the more powerful interface to the Pexpect system. You can
use this to spawn a child program then interact with it by sending input and
expecting responses (waiting for patterns in the child's output).

For example::

    child = pexpect.spawn('scp foo myname@host.example.com:.')
    child.expect ('Password:')
    child.sendline (mypassword)

This works even for commands that ask for passwords or other input outside of
the normal stdio streams. For example, ssh reads input directly from the TTY
device which bypasses stdin.

Credits: Noah Spurrier, Richard Holden, Marco Molteni, Kimberley Burchett,
Robert Stone, Hartmut Goebel, Chad Schroeder, Erick Tryzelaar, Dave Kirby, Ids
vander Molen, George Todd, Noel Taylor, Nicolas D. Cesar, Alexander Gattin,
Jacques-Etienne Baudoux, Geoffrey Marshall, Francisco Lourenco, Glen Mabey,
Karthik Gurusamy, Fernando Perez, Corey Minyard, Jon Cohen, Guillaume
Chazarain, Andrew Ryan, Nick Craig-Wood, Andrew Stone, Jorgen Grahn, John
Spiegel, Jan Grant, Shane Kerr and Thomas Kluyver. Let me know if I forgot anyone.

Pexpect is free, open source, and all that good stuff.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Pexpect Copyright (c) 2010 Noah Spurrier
http://pexpect.sourceforge.net/
"""

try:
    import os, sys, time
    import select
    import re
    import struct
    import types
    import errno
    import traceback
    import signal
except ImportError as e:
    raise ImportError (str(e) + """
A critical module was not found. Probably this operating system does not
support it. Pexpect is intended for UNIX-like operating systems.""")
try:
    # Linux ST2 doesn't package the resource module so ... uh ...
    import resource
except:
    pass

try:
    import pty
    import tty
    import termios
    import fcntl
except ImportError:
    pass

try:
    # Linux ST2 doesn't package the resource module so ... uh ...
    import resource
except:
    pass

__version__ = '2.5.1'
version = __version__
version_info = (2,5,1)
__all__ = ['ExceptionPexpect', 'EOF', 'TIMEOUT', 'spawn', 'spawnb', 'run', 'which',
    'split_command_line', '__version__']

PY3K = sys.version_info >= (3, 0, 0)

if PY3K:
    def u(s):
        return s

    string_types = str,
    text_type = str
    binary_type = bytes

    Iterator = object
else:
    def u(s):
        return unicode(s, 'unicode_escape')

    string_types = basestring,
    text_type = unicode
    binary_type = str

    class Iterator(object):
        def next(self):
            return type(self).__next__(self)


# Exception classes used by this module.
class ExceptionPexpect(Exception):

    """Base class for all exceptions raised by this module.
    """

    def __init__(self, value):

        self.value = value

    def __str__(self):

        return str(self.value)

    def get_trace(self):

        """This returns an abbreviated stack trace with lines that only concern
        the caller. In other words, the stack trace inside the Pexpect module
        is not included. """

        tblist = traceback.extract_tb(sys.exc_info()[2])
        #tblist = filter(self.__filter_not_pexpect, tblist)
        tblist = [item for item in tblist if self.__filter_not_pexpect(item)]
        tblist = traceback.format_list(tblist)
        return ''.join(tblist)

    def __filter_not_pexpect(self, trace_list_item):

        """This returns True if list item 0 the string 'pexpect.py' in it. """

        if trace_list_item[0].find('pexpect.py') == -1:
            return True
        else:
            return False

class EOF(ExceptionPexpect):

    """Raised when EOF is read from a child. This usually means the child has exited."""

class TIMEOUT(ExceptionPexpect):

    """Raised when a read time exceeds the timeout. """

##class TIMEOUT_PATTERN(TIMEOUT):
##    """Raised when the pattern match time exceeds the timeout.
##    This is different than a read TIMEOUT because the child process may
##    give output, thus never give a TIMEOUT, but the output
##    may never match a pattern.
##    """
##class MAXBUFFER(ExceptionPexpect):
##    """Raised when a scan buffer fills before matching an expected pattern."""

def _cast_bytes(s, enc):
    if isinstance(s, string_types):
        return s.encode(enc)
    return s

def _cast_unicode(s, enc):
    if isinstance(s, binary_type):
        return s.decode(enc)
    return s

re_type = type(re.compile(''))

def run (command, timeout=-1, withexitstatus=False, events=None, extra_args=None,
         logfile=None, cwd=None, env=None, encoding='utf-8'):

    """
    This function runs the given command; waits for it to finish; then
    returns all output as a string. STDERR is included in output. If the full
    path to the command is not given then the path is searched.

    Note that lines are terminated by CR/LF (\\r\\n) combination even on
    UNIX-like systems because this is the standard for pseudo ttys. If you set
    'withexitstatus' to true, then run will return a tuple of (command_output,
    exitstatus). If 'withexitstatus' is false then this returns just
    command_output.

    The run() function can often be used instead of creating a spawn instance.
    For example, the following code uses spawn::

        from pexpect import *
        child = spawn('scp foo myname@host.example.com:.')
        child.expect ('(?i)password')
        child.sendline (mypassword)

    The previous code can be replace with the following::

        from pexpect import *
        run ('scp foo myname@host.example.com:.', events={'(?i)password': mypassword})

    Examples
    ========

    Start the apache daemon on the local machine::

        from pexpect import *
        run ("/usr/local/apache/bin/apachectl start")

    Check in a file using SVN::

        from pexpect import *
        run ("svn ci -m 'automatic commit' my_file.py")

    Run a command and capture exit status::

        from pexpect import *
        (command_output, exitstatus) = run ('ls -l /bin', withexitstatus=1)

    Tricky Examples
    ===============

    The following will run SSH and execute 'ls -l' on the remote machine. The
    password 'secret' will be sent if the '(?i)password' pattern is ever seen::

        run ("ssh username@machine.example.com 'ls -l'", events={'(?i)password':'secret\\n'})

    This will start mencoder to rip a video from DVD. This will also display
    progress ticks every 5 seconds as it runs. For example::

        from pexpect import *
        def print_ticks(d):
            print d['event_count'],
        run ("mencoder dvd://1 -o video.avi -oac copy -ovc copy", events={TIMEOUT:print_ticks}, timeout=5)

    The 'events' argument should be a dictionary of patterns and responses.
    Whenever one of the patterns is seen in the command out run() will send the
    associated response string. Note that you should put newlines in your
    string if Enter is necessary. The responses may also contain callback
    functions. Any callback is function that takes a dictionary as an argument.
    The dictionary contains all the locals from the run() function, so you can
    access the child spawn object or any other variable defined in run()
    (event_count, child, and extra_args are the most useful). A callback may
    return True to stop the current run process otherwise run() continues until
    the next event. A callback may also return a string which will be sent to
    the child. 'extra_args' is not used by directly run(). It provides a way to
    pass data to a callback function through run() through the locals
    dictionary passed to a callback."""

    if timeout == -1:
        child = spawn(command, maxread=2000, logfile=logfile, cwd=cwd, env=env,
                      encoding=encoding)
    else:
        child = spawn(command, timeout=timeout, maxread=2000, logfile=logfile,
                      cwd=cwd, env=env, encoding=encoding)
    if events is not None:
        patterns = list(events.keys())
        responses = list(events.values())
    else:
        patterns=None # We assume that EOF or TIMEOUT will save us.
        responses=None
    child_result_list = []
    event_count = 0
    while 1:
        try:
            index = child.expect (patterns)
            if isinstance(child.after, string_types):
                child_result_list.append(child.before + child.after)
            else: # child.after may have been a TIMEOUT or EOF, so don't cat those.
                child_result_list.append(child.before)
            if isinstance(responses[index], string_types):
                child.send(responses[index])
            elif type(responses[index]) is types.FunctionType:
                callback_result = responses[index](locals())
                sys.stdout.flush()
                if isinstance(callback_result, string_types):
                    child.send(callback_result)
                elif callback_result:
                    break
            else:
                raise TypeError ('The callback must be a string or function type.')
            event_count = event_count + 1
        except TIMEOUT as e:
            child_result_list.append(child.before)
            break
        except EOF as e:
            child_result_list.append(child.before)
            break
    child_result = child._empty_buffer.join(child_result_list)
    if withexitstatus:
        child.close()
        return (child_result, child.exitstatus)
    else:
        return child_result

class spawnb(Iterator):
    """Use this class to start and control child applications with a pure-bytes
    interface."""

    _buffer_type = binary_type
    def _cast_buffer_type(self, s):
        return _cast_bytes(s, self.encoding)
    _empty_buffer = b''
    _pty_newline = b'\r\n'

    # Some code needs this to exist, but it's mainly for the spawn subclass.
    encoding = 'utf-8'

    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None,
                 logfile=None, cwd=None, env=None):

        """This is the constructor. The command parameter may be a string that
        includes a command and any arguments to the command. For example::

            child = pexpect.spawn ('/usr/bin/ftp')
            child = pexpect.spawn ('/usr/bin/ssh user@example.com')
            child = pexpect.spawn ('ls -latr /tmp')

        You may also construct it with a list of arguments like so::

            child = pexpect.spawn ('/usr/bin/ftp', [])
            child = pexpect.spawn ('/usr/bin/ssh', ['user@example.com'])
            child = pexpect.spawn ('ls', ['-latr', '/tmp'])

        After this the child application will be created and will be ready to
        talk to. For normal use, see expect() and send() and sendline().

        Remember that Pexpect does NOT interpret shell meta characters such as
        redirect, pipe, or wild cards (>, |, or *). This is a common mistake.
        If you want to run a command and pipe it through another command then
        you must also start a shell. For example::

            child = pexpect.spawn('/bin/bash -c "ls -l | grep LOG > log_list.txt"')
            child.expect(pexpect.EOF)

        The second form of spawn (where you pass a list of arguments) is useful
        in situations where you wish to spawn a command and pass it its own
        argument list. This can make syntax more clear. For example, the
        following is equivalent to the previous example::

            shell_cmd = 'ls -l | grep LOG > log_list.txt'
            child = pexpect.spawn('/bin/bash', ['-c', shell_cmd])
            child.expect(pexpect.EOF)

        The maxread attribute sets the read buffer size. This is maximum number
        of bytes that Pexpect will try to read from a TTY at one time. Setting
        the maxread size to 1 will turn off buffering. Setting the maxread
        value higher may help performance in cases where large amounts of
        output are read back from the child. This feature is useful in
        conjunction with searchwindowsize.

        The searchwindowsize attribute sets the how far back in the incomming
        seach buffer Pexpect will search for pattern matches. Every time
        Pexpect reads some data from the child it will append the data to the
        incomming buffer. The default is to search from the beginning of the
        imcomming buffer each time new data is read from the child. But this is
        very inefficient if you are running a command that generates a large
        amount of data where you want to match The searchwindowsize does not
        effect the size of the incomming data buffer. You will still have
        access to the full buffer after expect() returns.

        The logfile member turns on or off logging. All input and output will
        be copied to the given file object. Set logfile to None to stop
        logging. This is the default. Set logfile to sys.stdout to echo
        everything to standard output. The logfile is flushed after each write.

        Example log input and output to a file::

            child = pexpect.spawn('some_command')
            fout = file('mylog.txt','w')
            child.logfile = fout

        Example log to stdout::

            child = pexpect.spawn('some_command')
            child.logfile = sys.stdout

        The logfile_read and logfile_send members can be used to separately log
        the input from the child and output sent to the child. Sometimes you
        don't want to see everything you write to the child. You only want to
        log what the child sends back. For example::

            child = pexpect.spawn('some_command')
            child.logfile_read = sys.stdout

        To separately log output sent to the child use logfile_send::

            self.logfile_send = fout

        The delaybeforesend helps overcome a weird behavior that many users
        were experiencing. The typical problem was that a user would expect() a
        "Password:" prompt and then immediately call sendline() to send the
        password. The user would then see that their password was echoed back
        to them. Passwords don't normally echo. The problem is caused by the
        fact that most applications print out the "Password" prompt and then
        turn off stdin echo, but if you send your password before the
        application turned off echo, then you get your password echoed.
        Normally this wouldn't be a problem when interacting with a human at a
        real keyboard. If you introduce a slight delay just before writing then
        this seems to clear up the problem. This was such a common problem for
        many users that I decided that the default pexpect behavior should be
        to sleep just before writing to the child application. 1/20th of a
        second (50 ms) seems to be enough to clear up the problem. You can set
        delaybeforesend to 0 to return to the old behavior. Most Linux machines
        don't like this to be below 0.03. I don't know why.

        Note that spawn is clever about finding commands on your path.
        It uses the same logic that "which" uses to find executables.

        If you wish to get the exit status of the child you must call the
        close() method. The exit or signal status of the child will be stored
        in self.exitstatus or self.signalstatus. If the child exited normally
        then exitstatus will store the exit return code and signalstatus will
        be None. If the child was terminated abnormally with a signal then
        signalstatus will store the signal value and exitstatus will be None.
        If you need more detail you can also read the self.status member which
        stores the status returned by os.waitpid. You can interpret this using
        os.WIFEXITED/os.WEXITSTATUS or os.WIFSIGNALED/os.TERMSIG. """

        try:
            self.STDIN_FILENO = pty.STDIN_FILENO
            self.STDOUT_FILENO = pty.STDOUT_FILENO
            self.STDERR_FILENO = pty.STDERR_FILENO
        except:
            pass

        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

        self.searcher = None
        self.ignorecase = False
        self.before = None
        self.after = None
        self.match = None
        self.match_index = None
        self.terminated = True
        self.exitstatus = None
        self.signalstatus = None
        self.status = None # status returned by os.waitpid
        self.flag_eof = False
        self.pid = None
        self.child_fd = -1 # initially closed
        self.timeout = timeout
        self.delimiter = EOF
        self.logfile = logfile
        self.logfile_read = None # input from child (read_nonblocking)
        self.logfile_send = None # output to send (send, sendline)
        self.maxread = maxread # max bytes to read at one time into buffer
        self.buffer = self._empty_buffer # This is the read buffer. See maxread.
        self.searchwindowsize = searchwindowsize # Anything before searchwindowsize point is preserved, but not searched.
        # Most Linux machines don't like delaybeforesend to be below 0.03 (30 ms).
        self.delaybeforesend = 0.05 # Sets sleep time used just before sending data to child. Time in seconds.
        self.delayafterclose = 0.1 # Sets delay in close() method to allow kernel time to update process status. Time in seconds.
        self.delayafterterminate = 0.1 # Sets delay in terminate() method to allow kernel time to update process status. Time in seconds.
        self.softspace = False # File-like object.
        self.name = '<' + repr(self) + '>' # File-like object.
        self.closed = True # File-like object.
        self.cwd = cwd
        self.env = env
        self.__irix_hack = (sys.platform.lower().find('irix')>=0) # This flags if we are running on irix
        # Solaris uses internal __fork_pty(). All others use pty.fork().
        if 'solaris' in sys.platform.lower() or 'sunos5' in sys.platform.lower():
            self.use_native_pty_fork = False
        else:
            self.use_native_pty_fork = True


        # allow dummy instances for subclasses that may not use command or args.
        if command is None:
            self.command = None
            self.args = None
            self.name = '<pexpect factory incomplete>'
        else:
            self._spawn (command, args)

    def __del__(self):

        """This makes sure that no system resources are left open. Python only
        garbage collects Python objects. OS file descriptors are not Python
        objects, so they must be handled explicitly. If the child file
        descriptor was opened outside of this class (passed to the constructor)
        then this does not close it. """

        if not self.closed:
            # It is possible for __del__ methods to execute during the
            # teardown of the Python VM itself. Thus self.close() may
            # trigger an exception because os.close may be None.
            # -- Fernando Perez
            try:
                self.close()
            except:
                pass

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object. """

        s = []
        s.append(repr(self))
        s.append('version: ' + __version__)
        s.append('command: ' + str(self.command))
        s.append('args: ' + str(self.args))
        s.append('searcher: ' + str(self.searcher))
        s.append('buffer (last 100 chars): ' + str(self.buffer)[-100:])
        s.append('before (last 100 chars): ' + str(self.before)[-100:])
        s.append('after: ' + str(self.after))
        s.append('match: ' + str(self.match))
        s.append('match_index: ' + str(self.match_index))
        s.append('exitstatus: ' + str(self.exitstatus))
        s.append('flag_eof: ' + str(self.flag_eof))
        s.append('pid: ' + str(self.pid))
        s.append('child_fd: ' + str(self.child_fd))
        s.append('closed: ' + str(self.closed))
        s.append('timeout: ' + str(self.timeout))
        s.append('delimiter: ' + str(self.delimiter))
        s.append('logfile: ' + str(self.logfile))
        s.append('logfile_read: ' + str(self.logfile_read))
        s.append('logfile_send: ' + str(self.logfile_send))
        s.append('maxread: ' + str(self.maxread))
        s.append('ignorecase: ' + str(self.ignorecase))
        s.append('searchwindowsize: ' + str(self.searchwindowsize))
        s.append('delaybeforesend: ' + str(self.delaybeforesend))
        s.append('delayafterclose: ' + str(self.delayafterclose))
        s.append('delayafterterminate: ' + str(self.delayafterterminate))
        return '\n'.join(s)

    def _spawn(self,command,args=[]):

        """This starts the given command in a child process. This does all the
        fork/exec type of stuff for a pty. This is called by __init__. If args
        is empty then command will be parsed (split on spaces) and args will be
        set to parsed arguments. """

        # The pid and child_fd of this object get set by this method.
        # Note that it is difficult for this method to fail.
        # You cannot detect if the child process cannot start.
        # So the only way you can tell if the child process started
        # or not is to try to read from the file descriptor. If you get
        # EOF immediately then it means that the child is already dead.
        # That may not necessarily be bad because you may haved spawned a child
        # that performs some task; creates no stdout output; and then dies.

        # If command is an int type then it may represent a file descriptor.
        if type(command) == type(0):
            raise ExceptionPexpect ('Command is an int type. If this is a file descriptor then maybe you want to use fdpexpect.fdspawn which takes an existing file descriptor instead of a command string.')

        if type (args) != type([]):
            raise TypeError ('The argument, args, must be a list.')

        if args == []:
            self.args = split_command_line(command)
            self.command = self.args[0]
        else:
            self.args = args[:] # work with a copy
            self.args.insert (0, command)
            self.command = command

        command_with_path = which(self.command)
        if command_with_path is None:
            raise ExceptionPexpect ('The command was not found or was not executable: %s.' % self.command)
        self.command = command_with_path
        self.args[0] = self.command

        self.name = '<' + ' '.join (self.args) + '>'

        assert self.pid is None, 'The pid member should be None.'
        assert self.command is not None, 'The command member should not be None.'

        if self.use_native_pty_fork:
            try:
                self.pid, self.child_fd = pty.fork()
            except OSError as e:
                raise ExceptionPexpect('Error! pty.fork() failed: ' + str(e))
        else: # Use internal __fork_pty
            self.pid, self.child_fd = self.__fork_pty()

        if self.pid == 0: # Child
            try:
                self.child_fd = sys.stdout.fileno() # used by setwinsize()
                self.setwinsize(24, 80)
            except:
                # Some platforms do not like setwinsize (Cygwin).
                # This will cause problem when running applications that
                # are very picky about window size.
                # This is a serious limitation, but not a show stopper.
                pass
            # Do not allow child to inherit open file descriptors from parent.
            try:
                max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            except:
                max_fd = int(os.popen("ulimit -Sn").read().strip())
            for i in range (3, max_fd):
                try:
                    os.close (i)
                except OSError:
                    pass

            # I don't know why this works, but ignoring SIGHUP fixes a
            # problem when trying to start a Java daemon with sudo
            # (specifically, Tomcat).
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            if self.cwd is not None:
                os.chdir(self.cwd)
            if self.env is None:
                os.execv(self.command, self.args)
            else:
                os.execvpe(self.command, self.args, self.env)

        # Parent
        self.terminated = False
        self.closed = False

    def __fork_pty(self):

        """This implements a substitute for the forkpty system call. This
        should be more portable than the pty.fork() function. Specifically,
        this should work on Solaris.

        Modified 10.06.05 by Geoff Marshall: Implemented __fork_pty() method to
        resolve the issue with Python's pty.fork() not supporting Solaris,
        particularly ssh. Based on patch to posixmodule.c authored by Noah
        Spurrier::

            http://mail.python.org/pipermail/python-dev/2003-May/035281.html

        """

        parent_fd, child_fd = os.openpty()
        if parent_fd < 0 or child_fd < 0:
            raise ExceptionPexpect("Error! Could not open pty with os.openpty().")

        pid = os.fork()
        if pid < 0:
            raise ExceptionPexpect("Error! Failed os.fork().")
        elif pid == 0:
            # Child.
            os.close(parent_fd)
            self.__pty_make_controlling_tty(child_fd)

            os.dup2(child_fd, 0)
            os.dup2(child_fd, 1)
            os.dup2(child_fd, 2)

            if child_fd > 2:
                os.close(child_fd)
        else:
            # Parent.
            os.close(child_fd)

        return pid, parent_fd

    def __pty_make_controlling_tty(self, tty_fd):

        """This makes the pseudo-terminal the controlling tty. This should be
        more portable than the pty.fork() function. Specifically, this should
        work on Solaris. """

        child_name = os.ttyname(tty_fd)

        # Disconnect from controlling tty. Harmless if not already connected.
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
            if fd >= 0:
                os.close(fd)
        except:
            # Already disconnected. This happens if running inside cron.
            pass

        os.setsid()

        # Verify we are disconnected from controlling tty
        # by attempting to open it again.
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
            if fd >= 0:
                os.close(fd)
                raise ExceptionPexpect("Error! Failed to disconnect from controlling tty. It is still possible to open /dev/tty.")
        except:
            # Good! We are disconnected from a controlling tty.
            pass

        # Verify we can open child pty.
        fd = os.open(child_name, os.O_RDWR);
        if fd < 0:
            raise ExceptionPexpect("Error! Could not open child pty, " + child_name)
        else:
            os.close(fd)

        # Verify we now have a controlling tty.
        fd = os.open("/dev/tty", os.O_WRONLY)
        if fd < 0:
            raise ExceptionPexpect("Error! Could not open controlling tty, /dev/tty")
        else:
            os.close(fd)

    def fileno (self):   # File-like object.

        """This returns the file descriptor of the pty for the child.
        """

        return self.child_fd

    def close (self, force=True):   # File-like object.

        """This closes the connection with the child application. Note that
        calling close() more than once is valid. This emulates standard Python
        behavior with files. Set force to True if you want to make sure that
        the child is terminated (SIGKILL is sent if the child ignores SIGHUP
        and SIGINT). """

        if not self.closed:
            self.flush()
            os.close (self.child_fd)
            time.sleep(self.delayafterclose) # Give kernel time to update process status.
            if self.isalive():
                if not self.terminate(force):
                    raise ExceptionPexpect ('close() could not terminate the child using terminate()')
            self.child_fd = -1
            self.closed = True
            #self.pid = None

    def flush (self):   # File-like object.

        """This does nothing. It is here to support the interface for a
        File-like object. """

        pass

    def isatty (self):   # File-like object.

        """This returns True if the file descriptor is open and connected to a
        tty(-like) device, else False. """

        return os.isatty(self.child_fd)

    def waitnoecho (self, timeout=-1):

        """This waits until the terminal ECHO flag is set False. This returns
        True if the echo mode is off. This returns False if the ECHO flag was
        not set False before the timeout. This can be used to detect when the
        child is waiting for a password. Usually a child application will turn
        off echo mode when it is waiting for the user to enter a password. For
        example, instead of expecting the "password:" prompt you can wait for
        the child to set ECHO off::

            p = pexpect.spawn ('ssh user@example.com')
            p.waitnoecho()
            p.sendline(mypassword)

        If timeout==-1 then this method will use the value in self.timeout.
        If timeout==None then this method to block until ECHO flag is False.
        """

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            if not self.getecho():
                return True
            if timeout < 0 and timeout is not None:
                return False
            if timeout is not None:
                timeout = end_time - time.time()
            time.sleep(0.1)

    def getecho (self):

        """This returns the terminal echo mode. This returns True if echo is
        on or False if echo is off. Child applications that are expecting you
        to enter a password often set ECHO False. See waitnoecho(). """

        attr = termios.tcgetattr(self.child_fd)
        if attr[3] & termios.ECHO:
            return True
        return False

    def setecho (self, state):

        """This sets the terminal echo mode on or off. Note that anything the
        child sent before the echo will be lost, so you should be sure that
        your input buffer is empty before you call setecho(). For example, the
        following will work as expected::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.expect (['1234'])
            p.expect (['1234'])
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['abcd'])
            p.expect (['wxyz'])

        The following WILL NOT WORK because the lines sent before the setecho
        will be lost::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['1234'])
            p.expect (['1234'])
            p.expect (['abcd'])
            p.expect (['wxyz'])
        """

        self.child_fd
        attr = termios.tcgetattr(self.child_fd)
        if state:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO
        # I tried TCSADRAIN and TCSAFLUSH, but these were inconsistent
        # and blocked on some platforms. TCSADRAIN is probably ideal if it worked.
        termios.tcsetattr(self.child_fd, termios.TCSANOW, attr)

    def read_nonblocking (self, size = 1, timeout = -1):

        """This reads at most size bytes from the child application. It
        includes a timeout. If the read does not complete within the timeout
        period then a TIMEOUT exception is raised. If the end of file is read
        then an EOF exception will be raised. If a log file was set using
        setlog() then all data will also be written to the log file.

        If timeout is None then the read may block indefinitely. If timeout is -1
        then the self.timeout value is used. If timeout is 0 then the child is
        polled and if there was no data immediately ready then this will raise
        a TIMEOUT exception.

        The timeout refers only to the amount of time to read at least one
        character. This is not effected by the 'size' parameter, so if you call
        read_nonblocking(size=100, timeout=30) and only one character is
        available right away then one character will be returned immediately.
        It will not wait for 30 seconds for another 99 characters to come in.

        This is a wrapper around os.read(). It uses select.select() to
        implement the timeout. """

        if self.closed:
            raise ValueError ('I/O operation on closed file in read_nonblocking().')

        if timeout == -1:
            timeout = self.timeout

        # Note that some systems such as Solaris do not give an EOF when
        # the child dies. In fact, you can still try to read
        # from the child_fd -- it will block forever or until TIMEOUT.
        # For this case, I test isalive() before doing any reading.
        # If isalive() is false, then I pretend that this is the same as EOF.
        if not self.isalive():
            r,w,e = self.__select([self.child_fd], [], [], 0) # timeout of 0 means "poll"
            if not r:
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Braindead platform.')
        elif self.__irix_hack:
            # This is a hack for Irix. It seems that Irix requires a long delay before checking isalive.
            # This adds a 2 second delay, but only when the child is terminated.
            r, w, e = self.__select([self.child_fd], [], [], 2)
            if not r and not self.isalive():
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Pokey platform.')

        r,w,e = self.__select([self.child_fd], [], [], timeout)

        if not r:
            if not self.isalive():
                # Some platforms, such as Irix, will claim that their processes are alive;
                # then timeout on the select; and then finally admit that they are not alive.
                self.flag_eof = True
                raise EOF ('End of File (EOF) in read_nonblocking(). Very pokey platform.')
            else:
                raise TIMEOUT ('Timeout exceeded in read_nonblocking().')

        if self.child_fd in r:
            try:
                s = os.read(self.child_fd, size)
            except OSError as e: # Linux does this
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Exception style platform.')
            if s == b'': # BSD style
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Empty string style platform.')

            s2 = self._cast_buffer_type(s)
            if self.logfile is not None:
                self.logfile.write(s2)
                self.logfile.flush()
            if self.logfile_read is not None:
                self.logfile_read.write(s2)
                self.logfile_read.flush()

            return s

        raise ExceptionPexpect ('Reached an unexpected state in read_nonblocking().')

    def read (self, size = -1):         # File-like object.
        """This reads at most "size" bytes from the file (less if the read hits
        EOF before obtaining size bytes). If the size argument is negative or
        omitted, read all data until EOF is reached. The bytes are returned as
        a string object. An empty string is returned when EOF is encountered
        immediately. """

        if size == 0:
            return self._empty_buffer
        if size < 0:
            self.expect (self.delimiter) # delimiter default is EOF
            return self.before

        # I could have done this more directly by not using expect(), but
        # I deliberately decided to couple read() to expect() so that
        # I would catch any bugs early and ensure consistant behavior.
        # It's a little less efficient, but there is less for me to
        # worry about if I have to later modify read() or expect().
        # Note, it's OK if size==-1 in the regex. That just means it
        # will never match anything in which case we stop only on EOF.
        if isinstance(self._buffer_type, binary_type):
            pat = ('.{%d}' % size).encode('ascii')
        else:
            pat = '.{%d}' % size
        cre = re.compile(pat, re.DOTALL)
        index = self.expect ([cre, self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.after ### self.before should be ''. Should I assert this?
        return self.before

    def readline(self, size = -1):
        """This reads and returns one entire line. A trailing newline is kept
        in the string, but may be absent when a file ends with an incomplete
        line. Note: This readline() looks for a \\r\\n pair even on UNIX
        because this is what the pseudo tty device returns. So contrary to what
        you may expect you will receive the newline as \\r\\n. An empty string
        is returned when EOF is hit immediately. Currently, the size argument is
        mostly ignored, so this behavior is not standard for a file-like
        object. If size is 0 then an empty string is returned. """

        if size == 0:
            return self._empty_buffer
        index = self.expect ([self._pty_newline, self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.before + self._pty_newline
        return self.before

    def __iter__ (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        return self

    def __next__ (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        result = self.readline()
        if result == self._empty_buffer:
            raise StopIteration
        return result

    def readlines (self, sizehint = -1):    # File-like object.

        """This reads until EOF using readline() and returns a list containing
        the lines thus read. The optional "sizehint" argument is ignored. """

        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def write(self, s):   # File-like object.

        """This is similar to send() except that there is no return value.
        """

        self.send (s)

    def writelines (self, sequence):   # File-like object.

        """This calls write() for each element in the sequence. The sequence
        can be any iterable object producing strings, typically a list of
        strings. This does not add line separators There is no return value.
        """

        for s in sequence:
            self.write (s)

    def send(self, s):

        """This sends a string to the child process. This returns the number of
        bytes written. If a log file was set then the data is also written to
        the log. """

        time.sleep(self.delaybeforesend)

        s2 = self._cast_buffer_type(s)
        if self.logfile is not None:
            self.logfile.write(s2)
            self.logfile.flush()
        if self.logfile_send is not None:
            self.logfile_send.write(s2)
            self.logfile_send.flush()
        c = os.write (self.child_fd, _cast_bytes(s, self.encoding))
        return c

    def sendline(self, s=''):

        """This is like send(), but it adds a line feed (os.linesep). This
        returns the number of bytes written. """

        n = self.send (s)
        n = n + self.send (os.linesep)
        return n

    def sendcontrol(self, char):

        """This sends a control character to the child such as Ctrl-C or
        Ctrl-D. For example, to send a Ctrl-G (ASCII 7)::

            child.sendcontrol('g')

        See also, sendintr() and sendeof().
        """

        char = char.lower()
        a = ord(char)
        if a>=97 and a<=122:
            a = a - ord('a') + 1
            return self.send (chr(a))
        d = {'@':0, '`':0,
            '[':27, '{':27,
            '\\':28, '|':28,
            ']':29, '}': 29,
            '^':30, '~':30,
            '_':31,
            '?':127}
        if char not in d:
            return 0
        return self.send (chr(d[char]))

    def sendeof(self):

        """This sends an EOF to the child. This sends a character which causes
        the pending parent output buffer to be sent to the waiting child
        program without waiting for end-of-line. If it is the first character
        of the line, the read() in the user program returns 0, which signifies
        end-of-file. This means to work as expected a sendeof() has to be
        called at the beginning of a line. This method does not send a newline.
        It is the responsibility of the caller to ensure the eof is sent at the
        beginning of a line. """

        ### Hmmm... how do I send an EOF?
        ###C  if ((m = write(pty, *buf, p - *buf)) < 0)
        ###C      return (errno == EWOULDBLOCK) ? n : -1;
        #fd = sys.stdin.fileno()
        #old = termios.tcgetattr(fd) # remember current state
        #attr = termios.tcgetattr(fd)
        #attr[3] = attr[3] | termios.ICANON # ICANON must be set to recognize EOF
        #try: # use try/finally to ensure state gets restored
        #    termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        #    if hasattr(termios, 'CEOF'):
        #        os.write (self.child_fd, '%c' % termios.CEOF)
        #    else:
        #        # Silly platform does not define CEOF so assume CTRL-D
        #        os.write (self.child_fd, '%c' % 4)
        #finally: # restore state
        #    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if hasattr(termios, 'VEOF'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VEOF]
        else:
            # platform does not define VEOF so assume CTRL-D
            char = chr(4)
        self.send(char)

    def sendintr(self):

        """This sends a SIGINT to the child. It does not require
        the SIGINT to be the first character on a line. """

        if hasattr(termios, 'VINTR'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VINTR]
        else:
            # platform does not define VINTR so assume CTRL-C
            char = chr(3)
        self.send (char)

    def eof (self):

        """This returns True if the EOF exception was ever raised.
        """

        return self.flag_eof

    def terminate(self, force=False):

        """This forces a child process to terminate. It starts nicely with
        SIGHUP and SIGINT. If "force" is True then moves onto SIGKILL. This
        returns True if the child was terminated. This returns False if the
        child could not be terminated. """

        if not self.isalive():
            return True
        try:
            self.kill(signal.SIGHUP)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGCONT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGINT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            if force:
                self.kill(signal.SIGKILL)
                time.sleep(self.delayafterterminate)
                if not self.isalive():
                    return True
                else:
                    return False
            return False
        except OSError as e:
            # I think there are kernel timing issues that sometimes cause
            # this to happen. I think isalive() reports True, but the
            # process is dead to the kernel.
            # Make one last attempt to see if the kernel is up to date.
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            else:
                return False

    def wait(self):

        """This waits until the child exits. This is a blocking call. This will
        not read any data from the child, so this will block forever if the
        child has unread output and has terminated. In other words, the child
        may have printed output then called exit(); but, technically, the child
        is still alive until its output is read. """

        if self.isalive():
            pid, status = os.waitpid(self.pid, 0)
        else:
            raise ExceptionPexpect ('Cannot wait for dead child process.')
        self.exitstatus = os.WEXITSTATUS(status)
        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('Wait was called for a child process that is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return self.exitstatus

    def isalive(self):

        """This tests if the child process is running or not. This is
        non-blocking. If the child was terminated then this will read the
        exitstatus or signalstatus of the child. This returns True if the child
        process appears to be running or False if not. It can take literally
        SECONDS for Solaris to return the right status. """

        if self.terminated:
            return False

        if self.flag_eof:
            # This is for Linux, which requires the blocking form of waitpid to get
            # status of a defunct process. This is super-lame. The flag_eof would have
            # been set in read_nonblocking(), so this should be safe.
            waitpid_options = 0
        else:
            waitpid_options = os.WNOHANG

        try:
            pid, status = os.waitpid(self.pid, waitpid_options)
        except OSError as e: # No child processes
            if e.errno == errno.ECHILD:
                raise ExceptionPexpect ('isalive() encountered condition where "terminated" is 0, but there was no child process. Did someone else call waitpid() on our process?')
            else:
                raise e

        # I have to do this twice for Solaris. I can't even believe that I figured this out...
        # If waitpid() returns 0 it means that no child process wishes to
        # report, and the value of status is undefined.
        if pid == 0:
            try:
                pid, status = os.waitpid(self.pid, waitpid_options) ### os.WNOHANG) # Solaris!
            except OSError as e: # This should never happen...
                if e[0] == errno.ECHILD:
                    raise ExceptionPexpect ('isalive() encountered condition that should never happen. There was no child process. Did someone else call waitpid() on our process?')
                else:
                    raise e

            # If pid is still 0 after two calls to waitpid() then
            # the process really is alive. This seems to work on all platforms, except
            # for Irix which seems to require a blocking call on waitpid or select, so I let read_nonblocking
            # take care of this situation (unfortunately, this requires waiting through the timeout).
            if pid == 0:
                return True

        if pid == 0:
            return True

        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('isalive() encountered condition where child process is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return False

    def kill(self, sig):

        """This sends the given signal to the child application. In keeping
        with UNIX tradition it has a misleading name. It does not necessarily
        kill the child unless you send the right signal. """

        # Same as os.kill, but the pid is given for you.
        if self.isalive():
            os.kill(self.pid, sig)

    def compile_pattern_list(self, patterns):

        """This compiles a pattern-string or a list of pattern-strings.
        Patterns must be a StringType, EOF, TIMEOUT, SRE_Pattern, or a list of
        those. Patterns may also be None which results in an empty list (you
        might do this if waiting for an EOF or TIMEOUT condition without
        expecting any pattern).

        This is used by expect() when calling expect_list(). Thus expect() is
        nothing more than::

             cpl = self.compile_pattern_list(pl)
             return self.expect_list(cpl, timeout)

        If you are using expect() within a loop it may be more
        efficient to compile the patterns first and then call expect_list().
        This avoid calls in a loop to compile_pattern_list()::

             cpl = self.compile_pattern_list(my_pattern)
             while some_condition:
                ...
                i = self.expect_list(clp, timeout)
                ...
        """

        if patterns is None:
            return []
        if not isinstance(patterns, list):
            patterns = [patterns]

        compile_flags = re.DOTALL # Allow dot to match \n
        if self.ignorecase:
            compile_flags = compile_flags | re.IGNORECASE
        compiled_pattern_list = []
        for p in patterns:
            if isinstance(p, (binary_type, text_type)):
                p = self._cast_buffer_type(p)
                compiled_pattern_list.append(re.compile(p, compile_flags))
            elif p is EOF:
                compiled_pattern_list.append(EOF)
            elif p is TIMEOUT:
                compiled_pattern_list.append(TIMEOUT)
            elif type(p) is re_type:
                p = self._prepare_regex_pattern(p)
                compiled_pattern_list.append(p)
            else:
                raise TypeError ('Argument must be one of StringTypes, EOF, TIMEOUT, SRE_Pattern, or a list of those type. %s' % str(type(p)))

        return compiled_pattern_list

    def _prepare_regex_pattern(self, p):
        "Recompile unicode regexes as bytes regexes. Overridden in subclass."
        if isinstance(p.pattern, text_type):
            p = re.compile(p.pattern.encode('utf-8'), p.flags &~ re.UNICODE)
        return p

    def expect(self, pattern, timeout = -1, searchwindowsize=-1):

        """This seeks through the stream until a pattern is matched. The
        pattern is overloaded and may take several types. The pattern can be a
        StringType, EOF, a compiled re, or a list of any of those types.
        Strings will be compiled to re types. This returns the index into the
        pattern list. If the pattern was not a list this returns index 0 on a
        successful match. This may raise exceptions for EOF or TIMEOUT. To
        avoid the EOF or TIMEOUT exceptions add EOF or TIMEOUT to the pattern
        list. That will cause expect to match an EOF or TIMEOUT condition
        instead of raising an exception.

        If you pass a list of patterns and more than one matches, the first match
        in the stream is chosen. If more than one pattern matches at that point,
        the leftmost in the pattern list is chosen. For example::

            # the input is 'foobar'
            index = p.expect (['bar', 'foo', 'foobar'])
            # returns 1 ('foo') even though 'foobar' is a "better" match

        Please note, however, that buffering can affect this behavior, since
        input arrives in unpredictable chunks. For example::

            # the input is 'foobar'
            index = p.expect (['foobar', 'foo'])
            # returns 0 ('foobar') if all input is available at once,
            # but returs 1 ('foo') if parts of the final 'bar' arrive late

        After a match is found the instance attributes 'before', 'after' and
        'match' will be set. You can see all the data read before the match in
        'before'. You can see the data that was matched in 'after'. The
        re.MatchObject used in the re match will be in 'match'. If an error
        occurred then 'before' will be set to all the data read so far and
        'after' and 'match' will be None.

        If timeout is -1 then timeout will be set to the self.timeout value.

        A list entry may be EOF or TIMEOUT instead of a string. This will
        catch these exceptions and return the index of the list entry instead
        of raising the exception. The attribute 'after' will be set to the
        exception type. The attribute 'match' will be None. This allows you to
        write code like this::

                index = p.expect (['good', 'bad', pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    do_something()
                elif index == 1:
                    do_something_else()
                elif index == 2:
                    do_some_other_thing()
                elif index == 3:
                    do_something_completely_different()

        instead of code like this::

                try:
                    index = p.expect (['good', 'bad'])
                    if index == 0:
                        do_something()
                    elif index == 1:
                        do_something_else()
                except EOF:
                    do_some_other_thing()
                except TIMEOUT:
                    do_something_completely_different()

        These two forms are equivalent. It all depends on what you want. You
        can also just expect the EOF if you are waiting for all output of a
        child to finish. For example::

                p = pexpect.spawn('/bin/ls')
                p.expect (pexpect.EOF)
                print p.before

        If you are trying to optimize for speed then see expect_list().
        """

        compiled_pattern_list = self.compile_pattern_list(pattern)
        return self.expect_list(compiled_pattern_list, timeout, searchwindowsize)

    def expect_list(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This takes a list of compiled regular expressions and returns the
        index into the pattern_list that matched the child output. The list may
        also contain EOF or TIMEOUT (which are not compiled regular
        expressions). This method is similar to the expect() method except that
        expect_list() does not recompile the pattern list on every call. This
        may help if you are trying to optimize for speed, otherwise just use
        the expect() method.  This is called by expect(). If timeout==-1 then
        the self.timeout value is used. If searchwindowsize==-1 then the
        self.searchwindowsize value is used. """

        return self.expect_loop(searcher_re(pattern_list), timeout, searchwindowsize)

    def expect_exact(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This is similar to expect(), but uses plain string matching instead
        of compiled regular expressions in 'pattern_list'. The 'pattern_list'
        may be a string; a list or other sequence of strings; or TIMEOUT and
        EOF.

        This call might be faster than expect() for two reasons: string
        searching is faster than RE matching and it is possible to limit the
        search to just the end of the input buffer.

        This method is also useful when you don't want to have to worry about
        escaping regular expression characters that you want to match."""

        if isinstance(pattern_list, (binary_type, text_type)) or pattern_list in (TIMEOUT, EOF):
            pattern_list = [pattern_list]
        return self.expect_loop(searcher_string(pattern_list), timeout, searchwindowsize)

    def expect_loop(self, searcher, timeout = -1, searchwindowsize = -1):

        """This is the common loop used inside expect. The 'searcher' should be
        an instance of searcher_re or searcher_string, which describes how and what
        to search for in the input.

        See expect() for other arguments, return value and exceptions. """

        self.searcher = searcher

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout
        if searchwindowsize == -1:
            searchwindowsize = self.searchwindowsize

        try:
            incoming = self.buffer
            freshlen = len(incoming)
            while True: # Keep reading until exception or return.
                index = searcher.search(incoming, freshlen, searchwindowsize)
                if index >= 0:
                    self.buffer = incoming[searcher.end : ]
                    self.before = incoming[ : searcher.start]
                    self.after = incoming[searcher.start : searcher.end]
                    self.match = searcher.match
                    self.match_index = index
                    return self.match_index
                # No match at this point
                if timeout is not None and timeout < 0:
                    raise TIMEOUT ('Timeout exceeded in expect_any().')
                # Still have time left, so read more data
                c = self.read_nonblocking (self.maxread, timeout)
                freshlen = len(c)
                time.sleep (0.0001)
                incoming = incoming + c
                if timeout is not None:
                    timeout = end_time - time.time()
        except EOF as e:
            self.buffer = self._empty_buffer
            self.before = incoming
            self.after = EOF
            index = searcher.eof_index
            if index >= 0:
                self.match = EOF
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise EOF (str(e) + '\n' + str(self))
        except TIMEOUT as e:
            self.buffer = incoming
            self.before = incoming
            self.after = TIMEOUT
            index = searcher.timeout_index
            if index >= 0:
                self.match = TIMEOUT
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise TIMEOUT (str(e) + '\n' + str(self))
        except:
            self.before = incoming
            self.after = None
            self.match = None
            self.match_index = None
            raise

    def getwinsize(self):

        """This returns the terminal window size of the child tty. The return
        value is a tuple of (rows, cols). """

        TIOCGWINSZ = getattr(termios, 'TIOCGWINSZ', 1074295912)
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(self.fileno(), TIOCGWINSZ, s)
        return struct.unpack('HHHH', x)[0:2]

    def setwinsize(self, r, c):

        """This sets the terminal window size of the child tty. This will cause
        a SIGWINCH signal to be sent to the child. This does not change the
        physical window size. It changes the size reported to TTY-aware
        applications like vi or curses -- applications that respond to the
        SIGWINCH signal. """

        # Check for buggy platforms. Some Python versions on some platforms
        # (notably OSF1 Alpha and RedHat 7.1) truncate the value for
        # termios.TIOCSWINSZ. It is not clear why this happens.
        # These platforms don't seem to handle the signed int very well;
        # yet other platforms like OpenBSD have a large negative value for
        # TIOCSWINSZ and they don't have a truncate problem.
        # Newer versions of Linux have totally different values for TIOCSWINSZ.
        # Note that this fix is a hack.
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735: # L is not required in Python >= 2.2.
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.
        # Note, assume ws_xpixel and ws_ypixel are zero.
        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self.fileno(), TIOCSWINSZ, s)

    def interact(self, escape_character = b'\x1d', input_filter = None, output_filter = None):

        """This gives control of the child process to the interactive user (the
        human at the keyboard). Keystrokes are sent to the child process, and
        the stdout and stderr output of the child process is printed. This
        simply echos the child stdout and child stderr to the real stdout and
        it echos the real stdin to the child stdin. When the user types the
        escape_character this method will stop. The default for
        escape_character is ^]. This should not be confused with ASCII 27 --
        the ESC character. ASCII 29 was chosen for historical merit because
        this is the character used by 'telnet' as the escape character. The
        escape_character will not be sent to the child process.

        You may pass in optional input and output filter functions. These
        functions should take a string and return a string. The output_filter
        will be passed all the output from the child process. The input_filter
        will be passed all the keyboard input from the user. The input_filter
        is run BEFORE the check for the escape_character.

        Note that if you change the window size of the parent the SIGWINCH
        signal will not be passed through to the child. If you want the child
        window size to change when the parent's window size changes then do
        something like the following example::

            import pexpect, struct, fcntl, termios, signal, sys
            def sigwinch_passthrough (sig, data):
                s = struct.pack("HHHH", 0, 0, 0, 0)
                a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ , s))
                global p
                p.setwinsize(a[0],a[1])
            p = pexpect.spawn('/bin/bash') # Note this is global and used in sigwinch_passthrough.
            signal.signal(signal.SIGWINCH, sigwinch_passthrough)
            p.interact()
        """

        # Flush the buffer.
        if PY3K:
            self.stdout.write(_cast_unicode(self.buffer, self.encoding))
        else:
            self.stdout.write(self.buffer)
        self.stdout.flush()
        self.buffer = self._empty_buffer
        mode = tty.tcgetattr(self.STDIN_FILENO)
        tty.setraw(self.STDIN_FILENO)
        try:
            self.__interact_copy(escape_character, input_filter, output_filter)
        finally:
            tty.tcsetattr(self.STDIN_FILENO, tty.TCSAFLUSH, mode)

    def __interact_writen(self, fd, data):

        """This is used by the interact() method.
        """

        while data != b'' and self.isalive():
            n = os.write(fd, data)
            data = data[n:]

    def __interact_read(self, fd):

        """This is used by the interact() method.
        """

        return os.read(fd, 1000)

    def __interact_copy(self, escape_character = None, input_filter = None, output_filter = None):

        """This is used by the interact() method.
        """

        while self.isalive():
            r,w,e = self.__select([self.child_fd, self.STDIN_FILENO], [], [])
            if self.child_fd in r:
                data = self.__interact_read(self.child_fd)
                if output_filter: data = output_filter(data)
                if self.logfile is not None:
                    self.logfile.write (data)
                    self.logfile.flush()
                os.write(self.STDOUT_FILENO, data)
            if self.STDIN_FILENO in r:
                data = self.__interact_read(self.STDIN_FILENO)
                if input_filter: data = input_filter(data)
                i = data.rfind(escape_character)
                if i != -1:
                    data = data[:i]
                    self.__interact_writen(self.child_fd, data)
                    break
                self.__interact_writen(self.child_fd, data)

    def __select (self, iwtd, owtd, ewtd, timeout=None):

        """This is a wrapper around select.select() that ignores signals. If
        select.select raises a select.error exception and errno is an EINTR
        error then it is ignored. Mainly this is used to ignore sigwinch
        (terminal resize). """

        # if select() is interrupted by a signal (errno==EINTR) then
        # we loop back and enter the select() again.
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            try:
                return select.select (iwtd, owtd, ewtd, timeout)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    # if we loop back we have to subtract the amount of time we already waited.
                    if timeout is not None:
                        timeout = end_time - time.time()
                        if timeout < 0:
                            return ([],[],[])
                else: # something else caused the select.error, so this really is an exception
                    raise

class spawn(spawnb):
    """This is the main class interface for Pexpect. Use this class to start
    and control child applications."""

    _buffer_type = text_type
    def _cast_buffer_type(self, s):
        return _cast_unicode(s, self.encoding)
    _empty_buffer = u('')
    _pty_newline = u('\r\n')

    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None,
                 logfile=None, cwd=None, env=None, encoding='utf-8'):
        super(spawn, self).__init__(command, args, timeout=timeout, maxread=maxread,
                    searchwindowsize=searchwindowsize, logfile=logfile, cwd=cwd, env=env)
        self.encoding = encoding

    def _prepare_regex_pattern(self, p):
        "Recompile bytes regexes as unicode regexes."
        if isinstance(p.pattern, binary_type):
            p = re.compile(p.pattern.decode(self.encoding), p.flags)
        return p

    def read_nonblocking(self, size=1, timeout=-1):
        return super(spawn, self).read_nonblocking(size=size, timeout=timeout)\
                                    .decode(self.encoding)

    read_nonblocking.__doc__ = spawnb.read_nonblocking.__doc__


##############################################################################
# End of spawn class
##############################################################################

class searcher_string (object):

    """This is a plain string search helper for the spawn.expect_any() method.
    This helper class is for speed. For more powerful regex patterns
    see the helper class, searcher_re.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the matching string itself

    """

    def __init__(self, strings):

        """This creates an instance of searcher_string. This argument 'strings'
        may be a list; a sequence of strings; or the EOF or TIMEOUT types. """

        self.eof_index = -1
        self.timeout_index = -1
        self._strings = []
        for n, s in enumerate(strings):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._strings.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (ns[0],'    %d: "%s"' % ns) for ns in self._strings ]
        ss.append((-1,'searcher_string:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        return '\n'.join(a[1] for a in ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the search
        strings.  'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before. It helps to avoid
        searching the same, possibly big, buffer over and over again.

        See class spawn for the 'searchwindowsize' argument.

        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, this returns -1. """

        absurd_match = len(buffer)
        first_match = absurd_match

        # 'freshlen' helps a lot here. Further optimizations could
        # possibly include:
        #
        # using something like the Boyer-Moore Fast String Searching
        # Algorithm; pre-compiling the search through a list of
        # strings into something that can scan the input once to
        # search for all N strings; realize that if we search for
        # ['bar', 'baz'] and the input is '...foo' we need not bother
        # rescanning until we've read three more bytes.
        #
        # Sadly, I don't know enough about this interesting topic. /grahn

        for index, s in self._strings:
            if searchwindowsize is None:
                # the match, if any, can only be in the fresh data,
                # or at the very end of the old data
                offset = -(freshlen+len(s))
            else:
                # better obey searchwindowsize
                offset = -searchwindowsize
            n = buffer.find(s, offset)
            if n >= 0 and n < first_match:
                first_match = n
                best_index, best_match = index, s
        if first_match == absurd_match:
            return -1
        self.match = best_match
        self.start = first_match
        self.end = self.start + len(self.match)
        return best_index

class searcher_re (object):

    """This is regular expression string search helper for the
    spawn.expect_any() method. This helper class is for powerful
    pattern matching. For speed, see the helper class, searcher_string.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the re.match object returned by a succesful re.search

    """

    def __init__(self, patterns):

        """This creates an instance that searches for 'patterns' Where
        'patterns' may be a list or other sequence of compiled regular
        expressions, or the EOF or TIMEOUT types."""

        self.eof_index = -1
        self.timeout_index = -1
        self._searches = []
        for n, s in enumerate(patterns):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._searches.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (n,'    %d: re.compile("%s")' % (n,str(s.pattern))) for n,s in self._searches]
        ss.append((-1,'searcher_re:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        return '\n'.join(a[1] for a in ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the regular
        expressions. 'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before.

        See class spawn for the 'searchwindowsize' argument.

        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, returns -1."""

        absurd_match = len(buffer)
        first_match = absurd_match
        # 'freshlen' doesn't help here -- we cannot predict the
        # length of a match, and the re module provides no help.
        if searchwindowsize is None:
            searchstart = 0
        else:
            searchstart = max(0, len(buffer)-searchwindowsize)
        for index, s in self._searches:
            match = s.search(buffer, searchstart)
            if match is None:
                continue
            n = match.start()
            if n < first_match:
                first_match = n
                the_match = match
                best_index = index
        if first_match == absurd_match:
            return -1
        self.start = first_match
        self.match = the_match
        self.end = self.match.end()
        return best_index

def which (filename):

    """This takes a given filename; tries to find it in the environment path;
    then checks if it is executable. This returns the full path to the filename
    if found and executable. Otherwise this returns None."""

    # Special case where filename already contains a path.
    if os.path.dirname(filename) != '':
        if os.access (filename, os.X_OK):
            return filename

    if 'PATH' not in os.environ or os.environ['PATH'] == '':
        p = os.defpath
    else:
        p = os.environ['PATH']

    pathlist = p.split(os.pathsep)

    for path in pathlist:
        f = os.path.join(path, filename)
        if os.access(f, os.X_OK):
            return f
    return None

def split_command_line(command_line):

    """This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """

    arg_list = []
    arg = ''

    # Constants to name the states we can be in.
    state_basic = 0
    state_esc = 1
    state_singlequote = 2
    state_doublequote = 3
    state_whitespace = 4 # The state of consuming whitespace between commands.
    state = state_basic

    for c in command_line:
        if state == state_basic or state == state_whitespace:
            if c == '\\': # Escape the next character
                state = state_esc
            elif c == r"'": # Handle single quote
                state = state_singlequote
            elif c == r'"': # Handle double quote
                state = state_doublequote
            elif c.isspace():
                # Add arg to arg_list if we aren't in the middle of whitespace.
                if state == state_whitespace:
                    None # Do nothing.
                else:
                    arg_list.append(arg)
                    arg = ''
                    state = state_whitespace
            else:
                arg = arg + c
                state = state_basic
        elif state == state_esc:
            arg = arg + c
            state = state_basic
        elif state == state_singlequote:
            if c == r"'":
                state = state_basic
            else:
                arg = arg + c
        elif state == state_doublequote:
            if c == r'"':
                state = state_basic
            else:
                arg = arg + c

    if arg != '':
        arg_list.append(arg)
    return arg_list

# vi:set sr et ts=4 sw=4 ft=python :

########NEW FILE########
__FILENAME__ = repl
import re
import os
from functools import reduce

from . import PY3K, POSIX, PLATFORM


if POSIX:
    from . import pexpect
    spawn = pexpect.spawn
else:
    from . import winpexpect as pexpect
    spawn = pexpect.winspawn

from .ftfy import fix_text

repl_base = os.path.abspath(os.path.dirname(__file__))


def _merge_env(env):
    new_env = os.environ.copy()
    if not env:
        return new_env
    env = env.copy()
    # interpolate then merge
    for k, v in list(env.items()):
        env[k] = str(v).format(**new_env)
    new_env.update(env)
    return new_env


def _plat_repl_def(repl_def):
    for k, v in list(repl_def.items()):
        if isinstance(v, dict):
            repl_def[k] = v.get(PLATFORM)
    return repl_def


def get_repl(language, repl_def):
    repl_def = _plat_repl_def(repl_def)
    if "cmd" not in repl_def:
        raise ReplStartError("No worksheet REPL found for " + language)
    repl_def["env"] = _merge_env(repl_def.get("env"))
    return Repl(
        repl_def.pop("cmd").format(repl_base=repl_base),
        **repl_def
    )


class ReplResult():
    def __init__(self, text="",
                 is_timeout=False,
                 is_eof=False,
                 is_error=False):
        if len(text.strip()) > 0:
            text += "\n"
        self.text = text
        self.is_timeout = is_timeout
        self.is_eof = is_eof
        self.is_error = is_error

    def __str__(self):
        return self.text

    @property
    def terminates(self):
        return self.is_timeout or self.is_eof or self.is_error


class ReplStartError(Exception):
    pass


class ReplCloseError(Exception):
    pass


class Repl():
    def __init__(self, cmd, prompt, prefix, error=[], ignore=[], timeout=10, cwd=None,
                 env=None, strip_echo=True):
        self.repl = spawn(cmd, timeout=timeout, cwd=cwd, env=env)
        base_prompt = [pexpect.EOF, pexpect.TIMEOUT]
        self.prompt = base_prompt + self.repl.compile_pattern_list(prompt)
        self.prefix = prefix
        self.error = [re.compile(prefix + x) for x in error]
        self.ignore = [re.compile(x) for x in ignore]
        self.strip_echo = strip_echo
        index = self.repl.expect_list(self.prompt)
        if self.prompt[index] in [pexpect.EOF, pexpect.TIMEOUT]:
            raise ReplStartError("Could not start " + cmd)

    def correspond(self, input):
        if self.should_ignore(input):
            return ReplResult()
        prefix = self.prefix
        self.repl.send(re.sub("\t", " ", input))
        index = self.repl.expect_list(self.prompt)
        if self.prompt[index] == pexpect.TIMEOUT:
            # Timeout
            return ReplResult(prefix + "Execution timed out.", is_timeout=True)
        else:
            # For multiline statements additional newline is needed. See #26 issue
            start_index = 1 if len(input.strip()) else 0
            # Regular prompt - need to check for error
            result_list = [
                prefix + line
                for line in fix_text(self.repl.before).split("\n")
                if len(line.strip())
            ]
            if self.strip_echo:
                result_list = result_list[start_index:]
            result_str = "\n".join(result_list)
            is_eof = self.prompt[index] == pexpect.EOF
            if is_eof:
                result_str = "\n".join([result_str, prefix + " [exit]"])
            return ReplResult(result_str,
                              is_error=self.is_error(result_str),
                              is_eof=is_eof)

    def should_ignore(self, str):
        return self._match_one(self.ignore, str)

    def is_error(self, str):
        return self._match_one(self.error, str)

    def _match_one(self, regexes, str):
        return reduce(
            lambda acc, pattern: acc or pattern.match(str) is not None,
            regexes, False)

    def close(self, tries=0, max_retries=3):
        try:
            # sometimes the process (*ahem* java) takes a little too long to
            # close, so take 3 tries.
            self.repl.close(force=True)
        except pexpect.ExceptionPexpect as e:
            # wasn't closed, try again
            tries += 1
            if tries >= max_retries:
                raise ReplCloseError(e.message)
            else:
                self.close(tries, max_retries)
        except OSError as e:
            # Already closed - we're done.
            pass

########NEW FILE########
__FILENAME__ = repl_thread
import threading


class ReplThread(threading.Thread):
    def __init__(self, repl, str):
        self.repl = repl
        self.str = str
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        self.result = self.repl.correspond(self.str)

########NEW FILE########
__FILENAME__ = winpexpect
import itertools
import locale
import os
import subprocess
import sys
import time

from collections import namedtuple
from threading import Thread


PY3K = sys.version_info[0] == 3

if PY3K:
    from queue import Queue, Empty
else:
    from Queue import Queue, Empty

from .killableprocess import Popen, STARTUPINFO, STARTF_USESHOWWINDOW
from .pexpect import spawn, ExceptionPexpect, TIMEOUT, EOF


def split_command_line(cmdline):
    """Split a command line into a command and its arguments according to
    the rules of the Microsoft C runtime."""
    # http://msdn.microsoft.com/en-us/library/ms880421
    s_free, s_in_quotes, s_in_escape = range(3)
    state = namedtuple('state', ('current', 'previous', 'escape_level', 'argument'))
    state.current = s_free
    state.previous = s_free
    state.argument = []
    result = []
    for c in itertools.chain(cmdline, ['EOI']):  # Mark End of Input
        if state.current == s_free:
            if c == '"':
                state.current = s_in_quotes
                state.previous = s_free
            elif c == '\\':
                state.current = s_in_escape
                state.previous = s_free
                state.escape_count = 1
            elif c in (' ', '\t', 'EOI'):
                if state.argument or state.previous != s_free:
                    result.append(''.join(state.argument))
                    del state.argument[:]
            else:
                state.argument.append(c)
        elif state.current == s_in_quotes:
            if c == '"':
                state.current = s_free
                state.previous = s_in_quotes
            elif c == '\\':
                state.current = s_in_escape
                state.previous = s_in_quotes
                state.escape_count = 1
            else:
                state.argument.append(c)
        elif state.current == s_in_escape:
            if c == '\\':
                state.escape_count += 1
            elif c == '"':
                nbs, escaped_delim = divmod(state.escape_count, 2)
                state.argument.append(nbs * '\\')
                if escaped_delim:
                    state.argument.append('"')
                    state.current = state.previous
                else:
                    if state.previous == s_in_quotes:
                        state.current = s_free
                    else:
                        state.current = s_in_quotes
                state.previous = s_in_escape
            else:
                state.argument.append(state.escape_count * '\\')
                state.argument.append(c)
                state.current = state.previous
                state.previous = s_in_escape
    if state.current != s_free:
        raise ValueError('Illegal command line.')
    return result


def which(executable):
    if os.path.dirname(executable):
        return executable
    paths = os.environ.get('PATH', '').split(os.pathsep)
    exts = os.environ.get('PATHEXT', '.EXE').split(os.pathsep)
    (base, ext) = os.path.splitext(executable)
    if ext:
        exts = [ext]
    for path in paths:
        for ext in exts:
            filepath = os.path.join(path, base + ext)
            if os.path.isfile(filepath) and os.access(filepath, os.X_OK):
                return filepath
    return None

class winspawn(spawn):
    """This is the main class interface for Pexpect. Use this class to start
    and control child applications."""
    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None,
                 logfile=None, cwd=None, env=None, encoding='utf-8'):
        self.reader_queue = Queue()
        super(winspawn, self).__init__(command, args, timeout=timeout, maxread=maxread,
                                       searchwindowsize=searchwindowsize, logfile=logfile,
                                       cwd=cwd, env=env, encoding=encoding)

    def _spawn(self, command, args=None):
        """Start the child process. If args is empty, command will be parsed
        according to the rules of the MS C runtime, and args will be set to
        the parsed args."""
        if not isinstance(command, list):
            cmd = split_command_line(command)
        else:
            cmd = command
        executable = which(cmd[0])
        if executable:
            cmd[0] = executable

        # Create the pipes
        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESHOWWINDOW
        startupinfo.wShowWindow |= 1  # SW_SHOWNORMAL

        if not PY3K:  # Python 2.x, Popen cannot handle unicode path and args correctly
            encoding = locale.getpreferredencoding()
            if isinstance(executable, unicode):
                executable = executable.encode(encoding)
            if isinstance(args, unicode):
                args = args.encode(encoding)

        self.popen = Popen(cmd,
                           startupinfo=startupinfo,
                           creationflags=0x8000000,  # CREATE_NO_WINDOW
                           bufsize=1,
                           cwd=self.cwd,
                           env=self.env,
                           stderr=subprocess.STDOUT,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)

        # Start up the I/O threads
        self.pid = self.popen.pid
        self.child_fd = self.popen.stdin.fileno()  # for pexpect

        self.terminated = False
        self.closed = False

        self.stdout_reader = Thread(target=self._child_reader, args=(self.reader_queue,))
        self.stdout_reader.daemon = True
        self.stdout_reader.start()

    def _child_reader(self, queue):
        while True:
            try:
                b = self.popen.stdout.read(1)
                if len(b) == 0:
                    queue.put(None)
                    break
                queue.put(b)
            except:
                break

    def close(self, force=True):   # File-like object.
        if not self.closed:
            time.sleep(self.delayafterclose)  # Give kernel time to update process status.
            if self.isalive():
                if not self.terminate(force):
                    raise ExceptionPexpect('close() could not terminate the child using terminate()')
            self.child_fd = -1
            self.closed = True

    def waitnoecho(self, timeout=-1):
        raise NotImplementedError()

    def getecho(self):
        raise NotImplementedError()

    def setecho(self, state):
        raise NotImplementedError()

    def sendeof(self):
        # CTRL-Z
        char = chr(26)
        self.send(char)

    def sendintr(self):
        # platform does not define VINTR so assume CTRL-C
        char = chr(3)
        self.send(char)

    def terminate(self, force=False):
        if not self.isalive():
            return True
        try:
            self.kill(0)
        except:
            # I think there are kernel timing issues that sometimes cause
            # this to happen. I think isalive() reports True, but the
            # process is dead to the kernel.
            # Make one last attempt to see if the kernel is up to date.
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            else:
                return False

    def wait(self):
        if not self.isalive():
            raise ExceptionPexpect('Cannot wait for dead child process.')
        self.exitstatus = self.popen.wait()
        self.terminated = True
        return self.exitstatus

    def isalive(self):
        if self.terminated:
            return False

        exitstatus = self.popen.poll()
        if exitstatus is None:
            return True

        self.exitstatus = exitstatus
        self.terminated = True
        return False

    def kill(self, sig):
        if self.isalive():
            self.popen.kill()

    def read_nonblocking(self, size=1, timeout=-1):
        if self.closed:
            raise ValueError('I/O operation on closed file in read_nonblocking().')

        if timeout == -1:
            timeout = self.timeout

        if not self.isalive():
            self.flag_eof = True
            raise EOF('End Of File (EOF) in read_nonblocking(). Braindead platform.')

        q = self.reader_queue

        # Check first byte timeout
        try:
            s = q.get(True, timeout)
            if s is None:
                self.flag_eof = True
                raise EOF('End of File (EOF) in read_nonblocking().')
        except Empty:
            if not self.isalive():
                self.flag_eof = True
                raise EOF('End of File (EOF) in read_nonblocking(). Very pokey platform.')
            else:
                raise TIMEOUT('Timeout exceeded in read_nonblocking().')

        if len(s) < size:
            while True:
                try:
                    b = q.get_nowait()
                    if b is None:
                        self.flag_eof = True
                        raise EOF('End of File (EOF) in read_nonblocking().')
                    s += b
                except Empty:
                    break
                if len(s) == size:
                    break

        s2 = self._cast_buffer_type(s)
        if self.logfile is not None:
            self.logfile.write(s2)
            self.logfile.flush()
        if self.logfile_read is not None:
            self.logfile_read.write(s2)
            self.logfile_read.flush()
        return s2

    def getwinsize(self):
        raise NotImplementedError()

    def setwinsize(self, r, c):
        raise NotImplementedError()

    def interact(self, escape_character=b'\x1d', input_filter=None, output_filter=None):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = worksheet
import sublime
import sublime_plugin
import os
from sys import version_info
PY3K = version_info >= (3, 0, 0)
if PY3K:
    from .edit import Edit
    from . import repl
else:
    from edit import Edit
    import repl


if sublime.platform() != 'windows':
    # Make sure /usr/local/bin is on the path
    exec_path = os.getenv('PATH', '').split(os.pathsep)
    if not "/usr/local/bin" in exec_path:
        os.environ["PATH"] = os.pathsep.join(exec_path + ["/usr/local/bin"])


class WorksheetCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.load_settings()
        try:
            language = self.get_language()
            default_def = self.get_repl_settings()
            repl_defs = self.settings.get("worksheet_languages")
            project_repl_defs = self.project_settings.get("worksheet_languages", {})
            repl_def = dict(
                list(default_def) + list(project_repl_defs.get(language, repl_defs.get(language, {})).items()))
            filename = self.view.file_name()
            if filename is not None:
                repl_def["cwd"] = os.path.dirname(filename)
            self.repl = repl.get_repl(language, repl_def)
        except repl.ReplStartError as e:
            return sublime.error_message(str(e))
        self.remove_previous_results(edit)

    def load_settings(self):
        self.settings = sublime.load_settings("worksheet.sublime-settings")
        self.timeout = self.settings.get("worksheet_timeout")

    def get_repl_settings(self):
        default_def = self.settings.get("worksheet_defaults")
        if not hasattr(self, "project_settings"):
            self.project_settings = {}
        project_def = self.project_settings.get("worksheet_defaults", {})
        settings = []
        for key, setting in default_def.items():
            settings.append((key, project_def.get(key, setting)))
        return settings

    def get_language(self):
        return self.view.settings().get("syntax").split('/')[-1].split('.')[0]

    def remove_previous_results(self, edit):
        if not PY3K:
            edit = self.view.begin_edit("remove_previous_results")
        for region in reversed(self.view.find_all("^" + self.repl.prefix)):
            self.view.erase(edit, self.view.full_line(region))
        if not PY3K:
            self.view.end_edit(edit)

    def ensure_trailing_newline(self, edit):
        eof = self.view.size()
        if len(self.view.substr(self.view.line(eof)).strip()) is not 0:
            self.view.insert(edit, eof, "\n")

    def process_line(self, start):
        line = self.view.full_line(start)
        line_text = self.view.substr(line)
        if "\n" in line_text:
            self.view.add_regions("worksheet", list([line]), "string")
            self.set_status("Sending 1 line to %(language)s REPL.")
            self.queue_thread(
                repl.ReplThread(self.repl, line_text),
                line.end(),
            ).start()
        else:
            self.cleanup()

    def queue_thread(self, thread, start):
        sublime.set_timeout(lambda: self.handle_thread(thread, start), 5)
        return thread

    def handle_thread(self, thread, next_start):
        if thread.is_alive():
            self.handle_running_thread(thread, next_start)
        else:
            self.handle_finished_thread(thread, next_start)

    def handle_running_thread(self, thread, next_start):
        self.set_status("Waiting for %(language)s REPL.")
        self.queue_thread(thread, next_start)

    def handle_finished_thread(self, thread, next_start):
        self.view.add_regions("worksheet", list(), "string")
        result = thread.result
        self.insert(result, next_start)
        next_start += len(str(result))
        if not result.terminates:
            self.process_line(next_start)
        else:
            self.cleanup()

    def insert(self, text, start):
        with Edit(self.view) as edit:
            edit.insert(start, str(text))

    def set_status(self, msg, key="worksheet"):
        self.view.set_status(key, msg % {"language": self.get_language()})

    def cleanup(self):
        self.set_status('')
        try:
            self.repl.close()
        except repl.ReplCloseError as e:
            sublime.error_message(
                "Could not close the REPL:\n" + str(e))


class WorksheetEvalCommand(WorksheetCommand):
    def run(self, edit):
        WorksheetCommand.run(self, edit)
        self.ensure_trailing_newline(edit)
        self.process_line(0)


class WorksheetClearCommand(WorksheetCommand):
    def run(self, edit):
        WorksheetCommand.run(self, edit)

########NEW FILE########
